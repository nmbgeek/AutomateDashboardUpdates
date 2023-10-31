# AutomateDashboardUpdates

This is a simple Python script that downloads a Business Object Report from Community Services, uploads to Google Drive, and then requests a data refresh from Tableau. This script assumes you have a scheduled Business Objects Report with a unique name and that your Tableau Dashboard is set to use Google Sheets as its data source. For my purposes I have setup a report to run after our nightly rebuild with a unique name and have this script scheduled to run early in the morning for a regular update to my Tableau dashboard. This script also incorporates a RegEx of the report name. This insures that the most recent matching report is downloaded and that the wrong file is not uploaded to Google Drive which would break the Tableau dashboard.

**DO NOT INCLUDE ANY PII in your ART report or in Tableau Public. I would recommend setting this to run on a secure Virtual Machine using a scheduled task.**!

## Prerequisites

1. **[Python 3.13](https://www.python.org/downloads/)**
   (Make sure to add to PATH and restart computer.)

2. **Choose Firefox or Chrome:** Firefox seems more reliable. You will need to edit and uncomment the main Py file to switch to chrome.
   - Webdriver is now handled by webdriver_manager package!
3. **Python Dependencies:** Quick install - After adding Python to PATH and restarting computer open command prompt and run: `pip install selenium pydrive2 webdriver_manager`
   - [Selenium](https://github.com/baijum/selenium-python)
   - [PyDrive2](https://github.com/iterative/PyDrive2)
   - [webdriver-manager](https://pypi.org/project/webdriver-manager/)

## Setup Google Drive API v2 credentials:

Drive API requires OAuth2.0 for authentication. PyDrive makes your life much easier by handling complex authentication steps for you.

1. Go to [Google APIs Console](https://console.developers.google.com/iam-admin/projects) and create a new project. (https://console.developers.google.com/iam-admin/projects)
2. Search for ‘Google Drive API’, select the entry, and click ‘Enable’.
3. Select ‘Credentials’ from the left menu, click ‘Create Credentials’, select ‘OAuth client ID’.
4. Now, the product name and consent screen need to be set -> click ‘Configure consent screen’ and follow the instructions. Once finished:
5. Select ‘Application type’ to be 'Desktop'.
6. Enter an appropriate name.
7. Click ‘Save’.
8. Note the "Client ID" and "Client secret" for `gAuthSettings.yaml`

## Clone this repository to your computer.

- Update `script.conf` with SP URL, Drive File ID, login credentials, and your filename RegEx.
- In `gAuthSettings.yaml` Update the 'client_id' and 'client_secret' values from the credentials you created in Google API Console. PyDrive OAuth Documentation here: https://pythonhosted.org/PyDrive/oauth.html#sample-settings-yaml

## First Run

The first time you run `automateUpdate.py` you will be prompted to visit a URL where you will authenticate and allow access for your automation to use the Google Drive API. After doing this the credentials.json is created or updated and you will not have to re-authenticate on each subsequent run.

## Scheduled Task

Open Task Scheduler and create a new task to run as the current user. Set the trigger to your desired run time. Before business hours or you could also create an account just for running this task. For action select 'start a program'. Program will be the path to your python.exe such as `c:\python\python313\python.exe`. Additional arguments will be the path to your automateUpdate.py such as `c:\myScripts\automateUpdate.py`and Start In will be the path to the folder containing the automateUpdate.py such as `c:\myScripts`. If there are any spaces in your path you may need to wrap the entire string in quotes such as "c:\my scripts\automateUpdates.py".

## Shortcut Option

You can also create a shortcut for manually running. The Target for my example would combine both the location for python.exe and the argument of the .py file. Then use the directory of the .py file for the Start In.
