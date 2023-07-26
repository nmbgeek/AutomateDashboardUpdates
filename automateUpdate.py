#!python3

#  Import packages
import time, os, re, configparser, sys, logging
from selenium import webdriver
from pydrive2.auth import GoogleAuth
from selenium.common.exceptions import NoSuchElementException   
from selenium.webdriver.common.keys import Keys
from pydrive2.drive import GoogleDrive
from pathlib import Path

#create or update log file
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    handlers=[
        logging.FileHandler("dashboardupdate.log"),
        logging.StreamHandler()
    ]
)
logging.getLogger()
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
downloads_path = str(Path.home() / "Downloads")
signIn = dashboardURL + '?authMode=signIn'
filename = "" #left blank for Global usage
driver = webdriver.Firefox()
# Authenticate with Google Drive API
gauth = GoogleAuth(settings_file='gAuthSettings.yaml')

# Try to load saved client credentials
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

drive = GoogleDrive(gauth)

def check_exists_by_xpath(xpath):
    try:
        driver.find_element_by_xpath(xpath)
    except NoSuchElementException:
        return False
    return True

def checkAlerts():
    try:
        alert = driver.switch_to.alert
        alert.accept()
    except:
        pass

def upload_file_to_drive(file_id, local_path):
    """Overwrites the existing Google drive file."""
    update_file = drive.CreateFile({'id': file_id})
    update_file.SetContentFile(local_path)
    update_file.Upload()
    logging.info('Uploaded File Name: %s, mimeType: %s' % (update_file['title'], update_file['mimeType']))

def get_latest_file(name):
    list_of_files = [f for f in os.listdir(downloads_path) if re.search(artFileRegEx, f)]
    list_of_files = [f'{downloads_path}\\{i}' for i in list_of_files]
    latest_file = max(list_of_files, key=os.path.getctime)
    return latest_file

def loginTableau():
    driver.get(signIn)
    time.sleep(2)
    if check_exists_by_xpath('//*[@id="email"]'):
        tUsernameInput = driver.find_element_by_css_selector('#email')
        tPasswordInput = driver.find_element_by_css_selector('#password')
        tUsernameInput.send_keys(tableauUsername)
        tPasswordInput.send_keys(tableauPassword)
        tPasswordInput.send_keys(Keys.ENTER)
    time.sleep(5)  
    driver.get(dashboardURL)
    #Reduce implicit wait time because Tableau is much quicker than SP.
    driver.implicitly_wait(5)

def sp5Login():
    driver.get(servicePointURL)
    logging.info("Attempting Login")
    # Maximium wait time to find elements in seconds (ServicePoint can be slowwww)
    driver.implicitly_wait(60)
    # Find login fields
    usernameInput = driver.find_element_by_xpath('//*[@id="formfield-login"]')
    passwordInput = driver.find_element_by_xpath('//*[@id="formfield-password"]')
    loginButton = driver.find_element_by_xpath('//*[@id="LoginView.fbtn_submit"]/div')

    # Send credentials and login
    usernameInput.send_keys(spUsername)
    passwordInput.send_keys(spPassword)
    loginButton.click()
    
def artDownload():
    time.sleep(10)
    #Click login
    driver.find_element_by_xpath('//*[@id="ServicePointMain"]/tbody/tr[2]/td/div/div/table/tbody/tr/td[3]/table/tbody/tr/td[2]/table/tbody/tr[4]/td/table/tbody/tr/td/div/a/img').click()
    time.sleep(3)
    logging.info("Switch to business objects tab and wait to load")
    driver.switch_to.window(driver.window_handles[-1])
    logging.info(driver.title)
    time.sleep(5)
    iframe = driver.find_element_by_id('launchpadFrame')
    driver.switch_to.frame(iframe)
    time.sleep(8)
    subframe = driver.find_element_by_xpath("//iframe[@name='servletBridgeIframe']")
    driver.switch_to.frame(subframe)
    time.sleep(8)
    logging.info('Trying to click Inbox...')
    driver.find_element_by_id('Inbox-title-inner').click()
    time.sleep(8)
    view = ''
    reports = driver.find_elements_by_class_name('sapMLIBActionable')
    for rnum, report in enumerate(reports):
        logging.info('Report '+ str(rnum+1) +' is: ' + report.text)
        view = ''
        if bool(re.match(artFileRegEx, report.text)):
            logging.info('Match found!')
            view = '/html/body/div[2]/div[2]/div/div[2]/div/section/div/div/div/div/section/div/div/section[1]/div/section/div/div/div/div/div/div/ul/li['+str(rnum+1)+']/div/div/div[1]'
            driver.find_element_by_xpath(view).click()
            time.sleep(3)
            driver.find_element_by_xpath('/html/body/div[2]/div[2]/div/div[2]/div/section/div/div/div/div/section/div/div/section[2]/div/section/div/div/section/div[1]/div[2]/div/button[1]/span/span/bdi').click()
            break
    if not view:
        logging.warning('No matching report found!  Exiting.')
        driver.quit()
        sys.exit()
        
def getDownload():
    time.sleep(10)
    # Call method to get downloaded file name and store download path
    downloadedFileName = get_latest_file(artFileRegEx)
    filename = os.path.basename(downloadedFileName)
    logging.info(filename + " has completed downloading.")
    #driver.switch_to.window(driver.window_handles[0]) #from chrome method
    
    # Check that file downloaded is the correct one for dashboard
    if bool(re.match(artFileRegEx, filename)) == False:
        logging.warning('Find name does not match the regex:' + artFileRegEx)
        print('Quitting!')
        driver.quit()
        sys.exit()
    upload_file_to_drive(driveDashboardID, downloadedFileName)
        
def logoutSp5():    # Logout of ServicePoint
    checkAlerts()
    driver.switch_to.window(driver.window_handles[0])
    logOut = driver.find_element_by_xpath('//*[@id="navigation-link.logout"]')
    logOut.click()
    checkAlerts()
    
def refreshTableau(numTimes):    # Find and click Refresh Button.  numTimes = number of attempts.
    i = numTimes
    while i > 0:
        if not check_exists_by_xpath('//*[@id="root"]/div/header/div/div[2]/div/div/img'):
            loginTableau()
        if check_exists_by_xpath('//button[text()="Request Data Refresh"]'):
            tRefreshButton = driver.find_element_by_xpath('//button[text()="Request Data Refresh"]')
            tRefreshButton.click()
            logging.info('Tableau data refresh requested')
            i = 0
        else:
            i -= 1
            logging.info('No Tableau data refresh button found.  Has it been recently refreshed?  Trying ' + str(i) + ' more times.')
            driver.get(dashboardURL)
            time.sleep(5)

def main():
    sp5Login()
    artDownload()
    getDownload() #finds download and uploads to google drive
    logoutSp5()
    loginTableau()
    refreshTableau(3)# Find and click Refresh Button.  Attempts 3 times.
    driver.quit()#Close Browser

#Try/Except will run script.  If there is an error it will be logged and Selenium web driver will be exited.
try:
    main()
    logging.info('COMPLETED')
except Exception as e:
    logging.critical(e, exc_info=True)
    driver.quit()