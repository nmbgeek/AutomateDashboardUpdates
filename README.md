# AutomateDashboardUpdates

This is a simple Python script that downloads a Business Object Report from Community Services, uploads to Google Drive, and then requests a data refresh from Tableau. This script assumes you have a scheduled Business Objects Report with a unique name and that your Tableau Dashboard is set to use Google Sheets as its data source. For my purposes I have setup a report to run after our nightly rebuild with a unique name and have this script scheduled to run early in the morning for a regular update to my Tableau dashboard. This script also incorporates a RegEx of the report name. This insures that the most recent matching report is downloaded and that the wrong file is not uploaded to Google Drive which would break the Tableau dashboard.

This version runs completely headless using a docker container.

**DO NOT INCLUDE ANY PII in your ART report or in Tableau Public. I would recommend setting this to run on a secure Virtual Machine using a scheduled task.**!

## Prerequisites

1. **Docker** [docker.com](https://www.docker.com/) - Recommend running on a dedicated system. If running on Windows you will want to be sure to disable sleep, hybrid sleep, and hibernation.
2. **Clone/Download Repository** Using git cli or the zip download option to get the required files and place them in a folder on your computer or server that will run this script.
3. **Setup Service Account for Google Drive** Create a Google Cloud Console project and Service Account per the directions below. Rename the downloaded file to service_account.json and place it in this directory that you just cloned.
4. **Update Configuration** Update `script.conf.sample` and rename to `script.conf` with WSCS URL and credentials, Drive File ID, Tableau Dashboard URL and login credentials, and your filename RegEx.
5. **Run Docker** `docker compose up -d` from the command line in this directory will run the docker. By default the script runs at 6:00AM Eastern. In the docker-compose.yaml these values can be updated.

## Setup Google Drive API v2 credentials:

Drive API is set to use a Service Account for authentication. The service account will be setup for access to files shared with it from Google Drive. Keep this file protected.

1. Go to [Google APIs Console](https://console.developers.google.com/iam-admin/projects) and create a new project. (https://console.developers.google.com/iam-admin/projects)
2. Search for ‘Google Drive API’, select the entry, and click ‘Enable’.
3. Select ‘Credentials’ from the left menu, click ‘Create Credentials’, select ‘OAuth client ID’.
4. In the Service Accounts section select 'Manage service accounts'
5. Click 'Create Service Account'. For name put a descriptive name such as 'Dashboard Updates'. Copy the email address that is created just below the id.
6. Click 'Create and Continue' and then click 'Done'. No additional permissions need to be added. You should be returned to a list which has the service account you just created.
7. Click the service account that you just created and navigate to the 'Keys' tab.
8. Select 'ADD KEY' and then 'JSON' and the click 'CREATE'.
9. A .json is file is automatically downloaded. Place the .json file in the folder of this repository and rename it to `service_account.json`.
10. In your Google Drive where the Tableau dashboard is linked either share the containing folder or the file with the service account email you just created with Editor permissions.

## Google Drive File ID

To find your Google Drive File ID navigate to the excel file in your Google Drive. In the URL for the file you will find the File ID which is the combination of numbers and letters found in the url like this: https://docs.google.com/spreadsheets/d/ **_ThisIsTheFileID_** /edit
