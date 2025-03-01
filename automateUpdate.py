import time, os, re, configparser, sys, logging, glob
from pathlib import Path
from playwright.sync_api import sync_playwright
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s]: %(message)s',
    handlers=[
        logging.FileHandler('dashboardupdate.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()
logging.info('STARTING')

# Define variables (read from script.conf)
config = configparser.ConfigParser()
config.read('script.conf')
servicePointURL = config['ServicePoint']['URL']
spUsername = config['ServicePoint']['username']
spPassword = config['ServicePoint']['password']
tableauUsername = config['Tableau']['email']
tableauPassword = config['Tableau']['password']
driveDashboardID = config['Google Drive']['fileID']
dashboardURL = config['Tableau']['dashboardURL']
artFileRegEx = config['Google Drive']['fileRegEx']
downloads_path = str(Path.home() / 'Downloads')
tableauLogin = dashboardURL + '?authMode=signIn'


# Start playwright browser
browser = sync_playwright().start().chromium.launch(headless=False)  # Set to True for headless mode

# Authenticate to Google Drive with Service Account
gauth = GoogleAuth()
gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name('service_account.json', ["https://www.googleapis.com/auth/drive"])
drive = GoogleDrive(gauth)
upload = drive.CreateFile({'id': driveDashboardID})
    
context = browser.new_context()  # Create a new browser context
wscs = context.new_page()       # Open a new tab

# Navigate to the login page
wscs.goto(servicePointURL)

# Fill in the login form
wscs.fill('#formfield-login', spUsername)
wscs.fill('#formfield-password', spPassword)

# Click the login button
wscs.click('#LoginView\\.fbtn_submit')

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
    password_inputs.nth(0).fill(temporaryPassword)  # Current password
    password_inputs.nth(1).fill(spPassword)        # New password
    password_inputs.nth(2).fill(spPassword)        # Confirm new password
    wscs.click('#UserProfileChangePasswordPopup\\.save-button')
    wscs.click('UserProfilePopup\\.exit-button')
    wscs.wait_for_selector('.popupContent', state='hidden', timeout=5000)
    wscs.wait_for_load_state('load')
      
      

except:
  wscs.wait_for_selector('.pending-requests', state='hidden', timeout=60000)
  wscs.wait_for_load_state('load')

with context.expect_page() as bo_page:
  wscs.click('.query-business-object-icon')
  
sapbo_page = bo_page.value
sapbo_page.wait_for_load_state('load')
sapbo_page.wait_for_selector('#launchpadFrame')
outer_frame = sapbo_page.frame_locator('#launchpadFrame')
sapbo = outer_frame.frame_locator('//iframe[@name="servletBridgeIframe"]')

try:
  sapbo.locator('.help4-footer .help4-close').click()
except Exception as e:
  print(e)
  pass
sapbo.locator('#Inbox-title-inner').click()
try:
  sapbo_page.wait_for_load_state('networkidle', timeout=10000)
except:
  pass
reports = sapbo.locator('.sapMLIBActionable').element_handles()
if len(reports) == 0:
  logging.error('No reports found')
  browser.close()
  sys.exit(1)
for rnum, report in enumerate(reports):
  #title needs to be the value of the contained class .sapMSLITitle
  title = report.query_selector('.sapMSLITitle').text_content().strip()
  logging.info(f'Report {rnum + 1} is: {title}')
  if bool(re.match(artFileRegEx, title)):
      logging.info('Match found!')
      report.click()
      try:
        sapbo_page.wait_for_load_state('networkidle', timeout=5)
      except:
        report.click()
        pass
      time.sleep(1)
      with sapbo_page.expect_download() as download_info:
        sapbo.locator('//button//bdi[text()="View"]').click()
      filename = re.sub(r':', '-', title) + '.xlsx'
      download_info.value.save_as(downloads_path + '/' + filename)
      logging.info(f'Downloaded {filename}')
      break
      
upload = drive.CreateFile({'id': driveDashboardID})
upload.SetContentFile(downloads_path + '/' + filename)
upload.Upload()
logging.info('Uploaded File Name: %s, mimeType: %s' % (upload['title'], upload['mimeType']))

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
      logging.error(f'Refresh Button not found. Exiting...')
      browser.close()
      sys.exit(1)
      break
    else:
      logging.info('Refresh Button not found, retrying...')
      continue