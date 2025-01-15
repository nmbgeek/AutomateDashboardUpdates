#!python3

#  Import packages
import time, os, re, configparser, sys, logging, glob
from selenium import webdriver
from pydrive2.auth import GoogleAuth
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, TimeoutException   
from selenium.webdriver.common.keys import Keys
from pydrive2.drive import GoogleDrive
from pathlib import Path
from webdriver_manager.core.logger import set_logger
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type, after


#Start Firefox
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
##Optional With Profile Version with path formatted as example:
#profile = webdriver.FirefoxProfile("C:\\Users\\admin\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles\\08fk25r3.default")
#driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), profile=profile)
driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()))
#End Firefox

##Start Chrome
#from selenium import webdriver
#from selenium.webdriver.chrome.service import Service as ChromeService
#from webdriver_manager.chrome import ChromeDriverManager
#options = webdriver.ChromeOptions()
#options.add_argument("start-maximized")
#options.add_experimental_option('excludeSwitches', ['enable-logging'])
###Uncomment the below double comments to enable using the default or a custom chrome profile otherwise Selenium will launch a new temporary profile instance.
##AppDataProfile = str(Path.home()) + "\\AppData\\Local\\Google\\Chrome\\User Data\\ #You can create a custom chrome profile to store credentials in and update its path here.  Note that if Chrome profile instance is already opened Chrome Selenium driver will fail.  May move this to the config file eventually.
##DefaultProfile = "--user-data-dir=" + AppDataProfile
##options.add_argument(DefaultProfile) 
#driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()),options=options)
##End Chrome

##Other Browser Configs at https://pypi.org/project/webdriver-manager/

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    handlers=[
        logging.FileHandler("dashboardupdate.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()
set_logger(logger)
logging.info('STARTING')

action = webdriver.ActionChains(driver)

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
downloads_path = str(Path.home() / "Downloads")
signIn = dashboardURL + '?authMode=signIn'

#Define global variables
filename = ""


# Try to load saved client credentials
def googleAuth():
    # Authenticate with Google Drive API
    gauth = GoogleAuth(settings_file='gAuthSettings.yaml')
    gauth.LoadCredentialsFile()
    if gauth.credentials is None:
        auth_url = gauth.GetAuthUrl() # Create authentication url user needs to visit
        logging.info ('Please visit ' + auth_url)
        logging.info ('Enter verification code:')
        code = input()
        gauth.Auth(code) # Authorize and build service from the code
        gauth.SaveCredentialsFile()
    elif gauth.access_token_expired:
        # Refresh them if expired
        gauth.Refresh()
    else:
        # Initialize the saved creds
        gauth.Authorize()
    return GoogleDrive(gauth)

def check_exists(by_strategy, value, timeout=5):
    try:
        WebDriverWait(driver, timeout).until(EC.visibility_of_element_located((by_strategy, value)))
        return True
    except (NoSuchElementException, TimeoutException):
        return False

def get_element(by_strategy, value, timeout=5):
    try:
        return WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by_strategy, value)))
    except:
        logging.error(f"Unable to find element: {value}")
        quit()
        
@retry(
    stop=stop_after_attempt(3),  # Retry up to 3 times
    wait=wait_fixed(2),          # Wait 2 seconds between retries
    retry=retry_if_exception_type(Exception),  # Retry on any exception
)

def click_element(by_strategy, value, timeout=5):
    try:
        WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by_strategy, value))).click()
    except Exception as e:
        logging.error(f"Failed to click element: {value} - {e}")
        raise  # Reraise the exception to trigger retry

def checkAlerts():
    try:
        alert = driver.switch_to.alert
        alert.accept()
    except:
        pass

def upload_file_to_drive(drive, file_id, local_path):
    """Overwrites the existing Google drive file."""
    update_file = drive.CreateFile({'id': file_id})
    update_file.SetContentFile(local_path)
    update_file.Upload()
    logging.info('Uploaded File Name: %s, mimeType: %s' % (update_file['title'], update_file['mimeType']))

def loginTableau():
    driver.get(signIn)
    # Login if not logged in
    time.sleep(2)
    if check_exists(By.ID, 'email', 10):
        # Send credentials and login
        get_element(By.ID, 'email').send_keys(tableauUsername)
        get_element(By.ID, 'password').send_keys(tableauPassword)
        get_element(By.ID, 'password').send_keys(Keys.ENTER)
    time.sleep(5)  
    driver.get(dashboardURL)

def sp5Login():
    driver.get(servicePointURL)
    logging.info("Attempting Login")

    # Maximium wait time to find elements in seconds (ServicePoint can be slowwww)
    driver.implicitly_wait(10)

    # Login to Service Point
    get_element(By.ID, 'formfield-login').send_keys(spUsername)
    get_element(By.ID, 'formfield-password').send_keys(spPassword)
    click_element(By.ID, 'LoginView.fbtn_submit')
    
    #Check if password expired
    if check_exists(By.XPATH, "//*[contains(text(), 'Password has expired')]"):
        logging.info("Password Changed - Updating and Changing It Back")
        temporaryPassword = spPassword + "!"
        passwordInput2 = get_element(By.ID, 'formfield-password2')
        passwordInput2.send_keys(temporaryPassword)
        get_element(By.ID, 'formfield-password').send_keys(temporaryPassword)
        click_element(By.ID, 'LoginView.fbtn_submit')
        click_element(By.XPATH, '//*[@id="LoginView.fbtn_submit"]/div')
        if check_exists(By.CLASS_NAME, "sp5-authpanel-right"):
            click_element(By.XPATH, "/html/body/table[2]/tbody/tr[1]/td/table/tbody/tr/td/table/tbody/tr/td[3]/table/tbody/tr/td/table/tbody/tr[1]/td[3]/span")
            click_element(By.ID, 'UserProfilePopup.changePassword-button')
            passwordInputs = driver.find_elements(By.CLASS_NAME, "gwt-PasswordTextBox")
            passwordInputs[0].send_keys(temporaryPassword)
            passwordInputs[1].send_keys(spPassword)
            passwordInputs[2].send_keys(spPassword)
            click_element(By.ID, 'UserProfileChangePasswordPopup.save-button')
            click_element(By.ID, 'UserProfilePopup.exit-button')
    
def artDownload():
    click_element(By.CLASS_NAME, 'query-business-object-icon')
    logging.info("Switch to business objects tab and wait to load")
    time.sleep(5)
    driver.switch_to.window(driver.window_handles[-1])
    logging.info(driver.title)
    iframe = get_element(By.ID, 'launchpadFrame', 30)
    driver.switch_to.frame(iframe)
    subframe = get_element(By.XPATH, "//iframe[@name='servletBridgeIframe']", 30)
    driver.switch_to.frame(subframe)
    logging.info('Remove banner if present')    
    if(check_exists(By.CLASS_NAME,'help4-footer', 20)):
        click_element(By.CLASS_NAME, 'help4-close')
    logging.info('Trying to click Inbox...')
    click_element(By.ID, 'Inbox-title-inner',30)

    check_exists(By.CLASS_NAME, 'sapMLIBActionable', 30)
    WebDriverWait(driver, 20).until(
        lambda d: next(
            (el for el in d.find_elements(By.CLASS_NAME, 'sapMLIBActionable') if re.match(artFileRegEx, el.text)),
            None
        )
    )
    reports = driver.find_elements(By.CLASS_NAME, 'sapMLIBActionable')
    for rnum, report in enumerate(reports):
        logging.info('Report '+ str(rnum+1) +' is: ' + report.text)
        if bool(re.match(artFileRegEx, report.text)):
            title = report.find_element(By.CLASS_NAME, 'sapMSLITitle')
            logging.info('Match found!')
            click_element(By.XPATH, "//ul[@id='__list3-listUl']/li["+ str(rnum+1) +"]")
            click_element(By.XPATH, "//button//bdi[text()='View']")
            filename = re.sub(r':', '-', title.text) + '.xlsx'
            return filename
    logging.warning('No matching report found!  Exiting.')
    driver.quit()
    sys.exit()

def wait_for_download(filename, timeout=30):
    """
    Waits for a fully downloaded, non-zero-byte file in the download directory.

    Args:
        filename (str): The expected file name (without suffix like (1)).
        timeout (int): Maximum wait time in seconds.

    Returns:
        str: The full path of the downloaded file.

    Raises:
        TimeoutError: If the file doesn't download within the timeout.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        # Check for the main file and any potential duplicates
        downloaded_files = glob.glob(os.path.join(downloads_path, f"{filename}*"))
        
        # Find the first non-zero-byte file
        for file_path in downloaded_files:
            if not file_path.endswith(".part") and os.path.getsize(file_path) > 0:
                return file_path  # Return the correct file path
        
        time.sleep(1)  # Wait before checking again

    raise TimeoutError(f"File {filename} was not downloaded within {timeout} seconds.")      

def getDownload(drive, file):
    logging.info('Waiting on download')
    # Call method to get downloaded file name and store download path
    downloadedFileName = wait_for_download(file)
    filename = os.path.basename(downloadedFileName)
    logging.info(filename + " has completed downloading.")
    #driver.switch_to.window(driver.window_handles[0]) #from chrome method
    
    # Check that file downloaded is the correct one for dashboard
    if bool(re.match(artFileRegEx, filename)) == False:
        logging.warning('Find name does not match the regex:' + artFileRegEx)
        print('Quitting!')
        driver.quit()
        sys.exit()
    upload_file_to_drive(drive, driveDashboardID, downloadedFileName)
        
def logoutSp5():
    # Logout of ServicePoint
    checkAlerts()
    driver.switch_to.window(driver.window_handles[0])
    click_element(By.ID, 'navigation-link.logout')
    checkAlerts()

@retry(
    stop=stop_after_attempt(3),  # Retry up to 3 times
    wait=wait_fixed(2),          # Wait 2 seconds between retries
    retry=retry_if_exception_type(Exception),  # Retry on any exception
)   
def refreshTableau():    # Find and click Refresh Button.  numTimes = number of attempts.
    try:
        click_element(By.XPATH, '//button[text()="Request Data Refresh"]')
        logging.info('Tableau data refresh requested')
    except:
        logging.info('No Tableau data refresh button found.  Has it been recently refreshed?  Trying again.')
        driver.get(dashboardURL)
        raise
    
    

def main():
    drive = googleAuth() #Make sure Google Auth credentials are ok before downloading report
    sp5Login()
    download = artDownload()
    getDownload(drive, download) #finds and downloads report and uploads to google drive
    logoutSp5()
    loginTableau() 
    refreshTableau() # Find and click Refresh Button.  Attempts 3 times.
    driver.quit() #Close Browser

#Try/Except will run script.  If there is an error it will be printed and Selenium web driver will be exited.
try:
    main()
    logging.info('COMPLETED')
except Exception as e:
    logging.critical(e, exc_info=True)
    driver.quit()