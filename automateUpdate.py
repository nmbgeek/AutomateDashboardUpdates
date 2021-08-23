#!python3

#  Import packages
import time, os, re, configparser
from selenium import webdriver
from pydrive2.auth import GoogleAuth
from selenium.common.exceptions import NoSuchElementException   
from pydrive2.drive import GoogleDrive
from pathlib import Path

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

options = webdriver.ChromeOptions()
options.add_argument("start-maximized")
options.add_experimental_option('excludeSwitches', ['enable-logging'])

#Uncomment this to enable using the default or a custom chrome profile otherwise Selenium will launch a new temporary profile instance.
#AppDataProfile = str(Path.home()) + "\\AppData\\Local\\Google\\Chrome\\User Data\\ #You can create a custom chrome profile to store credentials in and update its path here.  Note that if Chrome profile instance is already opened Chrome Selenium driver will fail.  May move this to the config file eventually.
#DefaultProfile = "--user-data-dir=" + AppDataProfile
#options.add_argument(DefaultProfile) 

# Authenticate with Google Drive API
gauth = GoogleAuth(settings_file='gAuthSettings.yaml')

# Try to load saved client credentials
gauth.LoadCredentialsFile()
if gauth.credentials is None:
    auth_url = gauth.GetAuthUrl() # Create authentication url user needs to visit
    print ('Please visit ' + auth_url)
    print ('Enter verification code:')
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

def upload_file_to_drive(file_id, local_path):
    """Overwrites the existing Google drive file."""
    update_file = drive.CreateFile({'id': file_id})
    update_file.SetContentFile(local_path)
    update_file.Upload()
    print('Uploaded File Name: %s, mimeType: %s' % (update_file['title'], update_file['mimeType']))

def getDownLoadedFileName(waitTime):
    driver.execute_script("window.open()")
    # switch to new tab
    driver.switch_to.window(driver.window_handles[-1])
    # navigate to chrome downloads
    driver.get('chrome://downloads')
    # define the endTime
    endTime = time.time()+waitTime
    while True:
        try:
            # get downloaded percentage
            downloadPercentage = driver.execute_script(
                "return document.querySelector('downloads-manager').shadowRoot.querySelector('#downloadsList downloads-item').shadowRoot.querySelector('#progress').value")
            # check if downloadPercentage is 100 (otherwise the script will keep waiting)
            if downloadPercentage == 100:
                # return the file name once the download is completed
                return driver.execute_script("return document.querySelector('downloads-manager').shadowRoot.querySelector('#downloadsList downloads-item').shadowRoot.querySelector('div#content  #file-link').text")
        except:
            pass
        time.sleep(1)
        if time.time() > endTime:
            break

def loginTableau():
    if check_exists_by_xpath('//*[@id="root"]/div/header/div/div[2]/div/a[8]/button'):
        signInButton = driver.find_element_by_xpath('//*[@id="root"]/div/header/div/div[2]/div/a[8]/button')
        signInButton.click()
        # Find login fields
        tUsernameInput = driver.find_element_by_css_selector('#email')
        tPasswordInput = driver.find_element_by_css_selector('#password')
        tLoginButton = driver.find_element_by_xpath('/html/body/div[4]/div/div/div/div/form/div[4]/button')
        # Send credentials and login
        tUsernameInput.send_keys(tableauUsername)
        tPasswordInput.send_keys(tableauPassword)
        tLoginButton.click()
        time.sleep(3)  

#Try/Except will run script.  If there is an error it will be printed and Selenium web driver will be exited.
try:
    driver = webdriver.Chrome(options=options)
    driver.get(servicePointURL)

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

    # Wait for page to load.  Could not get "Connect to ART" button to be found and click properly
    time.sleep(8)

    # Redirect to ART Reports
    artURL = servicePointURL + '/com.bowmansystems.sp5.core.ServicePoint/index.html#reportsART'
    driver.get(artURL)

    # Load ART Inbox
    artInbox = driver.find_element_by_xpath('//*[@id="applicationContentPanel"]/tbody/tr/td/table/tbody/tr[3]/td/table/tbody/tr/td/table/tbody/tr[2]/td/table/tbody/tr[3]/td/table/tbody/tr[2]/td/table/tbody/tr/td/table/tbody/tr[1]/td[1]/div/div[2]/img')
    artInbox.click()
    time.sleep(2)

    # View last report information
    lastReport = driver.find_element_by_xpath('//*[@id="applicationContentPanel"]/tbody/tr/td/table/tbody/tr[3]/td/table/tbody/tr/td/table/tbody/tr[2]/td/table/tbody/tr[3]/td/table/tbody/tr[2]/td/table/tbody/tr/td/table/tbody/tr[2]/td[2]/table/tbody/tr[1]/td[2]/img')
    lastReport.click()
    time.sleep(2)

    # Download last report
    downloadButton = driver.find_element_by_xpath('/html/body/div[5]/div/table/tbody/tr[2]/td[2]/table/tbody/tr[3]/td/table/tbody/tr/td/table/tbody/tr[2]/td/table/tbody/tr/td[1]/div/div')
    downloadButton.click()

    # Call method to get downloaded file name and store download path
    DownloadedFileName = getDownLoadedFileName(60)
    downloads_path = str(Path.home() / "Downloads")
    fullDownloadPath = os.path.join(downloads_path, DownloadedFileName)
    print(fullDownloadPath + " has completed downloading.")
    driver.switch_to.window(driver.window_handles[0])

    # Logout of ServicePoint
    logOut = driver.find_element_by_xpath('//*[@id="navigation-link.logout"]')
    logOut.click()

    # Check that file downloaded is the correct one for dashboard
    if bool(re.match(artFileRegEx, DownloadedFileName)) == False:
        print('Find name does not match the regex:' + artFileRegEx)
        print('Quitting!')
        driver.quit()
        quit()

    # Update Dashboard File
    upload_file_to_drive(driveDashboardID, fullDownloadPath)

    #Go to Tableauu
    driver.get(dashboardURL)

    #Reduce implicit wait time because Tableau is much quicker.
    driver.implicitly_wait(5)
    time.sleep(3)

    #Check if logged in and do so if needed.
    if not check_exists_by_xpath('//*[@id="root"]/div/header/div/div[2]/div/div/img'):
        loginTableau()

    #Refresh page to reveal data refresh button
    time.sleep(3)

    # Find and click Refresh Button.  Attempts 3 times.
    i = 3
    while i > 0:
        if check_exists_by_xpath('//*[@id="root"]/div/div[2]/div[3]/div[2]/div[2]/div[2]/button'):
            tRefreshButton = driver.find_element_by_xpath('//*[@id="root"]/div/div[2]/div[3]/div[2]/div[2]/div[2]/button')
            tRefreshButton.click()
            print('Tableau data refresh requested')
            i = 0
        else:
            i -= 1
            print('No Tableau data refresh button found.  Has it been recently refreshed?  Trying ' + str(i) + ' more times.')
            driver.refresh()
            time.sleep(5)

    #Close Chrome
    driver.quit()

except Exception as e:
    #Print error and exit Selenium Chrome
    print('A problem has occurred from the Problematic code: ', e)
    driver.quit()
