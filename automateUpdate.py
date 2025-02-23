import time, os, re, configparser, sys, logging, glob
from pathlib import Path
from playwright.sync_api import sync_playwright
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials

# Configure logging to stdout for docker
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout) 
    ]
)

logger = logging.getLogger()
logging.info("STARTING SCRIPT")

# Define variables (read from script.conf)
config = configparser.ConfigParser()
config.read('/app/script.conf')
WSCSURL = config['WSCS']['URL']
spUsername = config['WSCS']['username']
spPassword = config['WSCS']['password']
tableauUsername = config['Tableau']['email']
tableauPassword = config['Tableau']['password']
driveDashboardID = config['Google Drive']['fileID']
dashboardURL = config['Tableau']['dashboardURL']
artFileRegEx = config['Google Drive']['fileRegEx']
tableauLogin = dashboardURL + '?authMode=signIn'
downloads_path = '/app/downloads'
Path(downloads_path).mkdir(parents=True, exist_ok=True)
# Define screenshot directory
#screenshot_path = Path("/app/screenshots")
#screenshot_path.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists


# Start playwright Firefox browser
browser = sync_playwright().start().firefox.launch(
    headless=True,          # Show browser UI
    slow_mo=500,             # Slow down actions by 500ms
    args=["--no-sandbox","--disable-gpu"],   # Required for Docker/CI
)
# For Chromium - Very flakey !
# browser = sync_playwright().start().chromium.launch(
#     channel="chromium",
#     headless=True,          # Show browser UI
#     slow_mo=500,             # Slow down actions by 500ms
#     args=["--no-sandbox","--disable-gpu"],   # Required for Docker/CI
# )

# Authenticate to Google Drive with Service Account.  Do this first to make sure it works.
gauth = GoogleAuth()
gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name('/app/service_account.json', ["https://www.googleapis.com/auth/drive"])
drive = GoogleDrive(gauth)
upload = drive.CreateFile({'id': driveDashboardID})
    


# Create a new browser context and page.  Go to WSCS
context = browser.new_context()
wscs = context.new_page()
wscs.goto(WSCSURL)

# Fill in the login form
wscs.fill('#formfield-login', spUsername)
wscs.fill('#formfield-password', spPassword)

# Click the login button
wscs.click('#LoginView\\.fbtn_submit')

# Make sure password isn't expired. If so set a new one and change it back.
try:
  wscs.wait_for_selector('//*[contains(text(), "Password has expired")]', timeout=500)
  if wscs.locator('//*[contains(text(), "Password has expired")]').is_visible():
    temporaryPassword = spPassword + '!'
    wscs.fill('#formfield-password', temporaryPassword)
    wscs.fill('#formfield-password2', temporaryPassword)
    wscs.click('#LoginView\\.fbtn_submit')
    wscs.wait_for_load_state('load')
    wscs.wait_for_selector('.pending-requests', state='hidden', timeout=60000)
    wscs.click('.sp5-authpanel .manage-accounts')
    wscs.click('#UserProfilePopup\\.changePassword-button')
    password_inputs = wscs.locator('.gwt-PasswordTextBox')
    password_inputs.nth(0).fill(temporaryPassword) 
    password_inputs.nth(1).fill(spPassword)       
    password_inputs.nth(2).fill(spPassword)       
    wscs.click('#UserProfileChangePasswordPopup\\.save-button')
    wscs.click('UserProfilePopup\\.exit-button')
    wscs.wait_for_selector('.popupContent', state='hidden', timeout=5000)
    wscs.wait_for_load_state('load')

except:
  # If password isn't expired continue and wait for WSCS to load
  wscs.wait_for_selector('.pending-requests', state='hidden', timeout=60000)
  wscs.wait_for_load_state('load')


with context.expect_page() as bo_page:
  wscs.click('.query-business-object-icon')

#logging.info('Navigating to SAP Business Objects')
sapbo_page = bo_page.value
sapbo_page.wait_for_load_state('load', timeout=60000)
sapbo_page.wait_for_selector('#launchpadFrame', state='attached')
logging.info('SAP Business Objects Loaded')
outer_frame = sapbo_page.frame_locator('#launchpadFrame')
outer_frame.locator('//iframe[@name="servletBridgeIframe"]').wait_for(state='attached', timeout=60000)
sapbo = outer_frame.frame_locator('//iframe[@name="servletBridgeIframe"]')
#logging.info('SAP Business Objects Frame Loaded')
# Wait for 30 seconds before getting all elements with IDs
#logging.info("Waiting for 10 seconds...")
try:
  sapbo_page.wait_for_load_state('load', timeout=60000)
except:
  logging.info("SAP Business Objects Wait For Load Timed Out")
  sapbo_page.wait_for_timeout(10000)
  pass
#time.sleep(10)  # Pause execution for 30 seconds
# Take a screenshot of the full page
#sapbo_page.screenshot(path=str(screenshot_path / "bo_loaded.png"))
    
try:
  sapbo.locator('.help4-footer .help4-close').wait_for(state='visible', timeout=30000)
  help_close = sapbo.locator('.help4-footer .help4-close')
  if help_close.is_visible():
    help_close.click()
    #logging.info('Help window closed')
except Exception as e:
  pass
try:
  sapbo.locator('#Inbox-title-inner').wait_for(state='visible', timeout=30000)
except:
  logging.info("Inbox button timed out")
sapbo.locator('#Inbox-title-inner').click()
try:
  sapbo_page.wait_for_load_state('load', timeout=30000)
except:
  logging.info("Inbox Load Timed Out")
  sapbo_page.wait_for_timeout(10000)
  pass
#Wait for content to populate:
sapbo.locator('.sapMLIBActionable').first.wait_for(state='visible', timeout=10000)
sapbo_page.wait_for_timeout(3000)
# Take a screenshot of the full page
#sapbo_page.screenshot(path=str(screenshot_path / "inbox_page.png"))
reports = sapbo.locator('.sapMLIBActionable').element_handles()
if len(reports) == 0:
  logging.error('No reports found')
  browser.close()
  sys.exit(1)
for rnum, report in enumerate(reports):
  # Get report names and download matching report
  title = report.query_selector('.sapMSLITitle').text_content().strip()
  logging.info(f'Report {rnum + 1} is: {title}')
  if bool(re.match(artFileRegEx, title)):
      logging.info('Match found!')
      report.click()
      try:
        sapbo_page.wait_for_load_state('networkidle', timeout=3000)
      except:
        report.click()
        pass
      sapbo_page.wait_for_timeout(5000)
      with sapbo_page.expect_download() as download_info:
        sapbo.locator('//button//bdi[text()="View"]').click()
      filename = re.sub(r':', '-', title) + '.xlsx'
      download_info.value.save_as(downloads_path + '/' + filename)
      logging.info(f'Downloaded {filename}')
      break

# Upload file to Google Drive
upload = drive.CreateFile({'id': driveDashboardID})
upload.SetContentFile(downloads_path + '/' + filename)
upload.Upload()
logging.info('Uploaded File Name: %s, mimeType: %s' % (upload['title'], upload['mimeType']))

# Login to Tableau and Refresh Dashboard
tableau = context.new_page()
tableau.goto(tableauLogin)
tableau.fill('#email', tableauUsername)
tableau.fill('#password', tableauPassword)
tableau.click('#signInButton')
tableau.wait_for_url('**/discover')
i = 2
while i > 0:
  try:
    tableau.goto(dashboardURL)
    tableau.wait_for_load_state('load')
    tableau.click('//button[text()="Request Data Refresh"]')
    tableau.wait_for_load_state('networkidle')
    logging.info('Data Refresh Requested')
    i = 0
    browser.close()
    sys.exit(0)
    break
  except Exception as e:
    print(e)
    i -= 1
    if i == 0:
      logging.error('Refresh Button not found. Exiting...')
      browser.close()
      sys.exit(1)
      break
    else:
      logging.info('Refresh Button not found, retrying...')
      continue