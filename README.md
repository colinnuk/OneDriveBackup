# OneDriveBackup
Python Script to automatically backup selected folders to another location within OneDrive. I mainly made this to prevent ransomware, and it runs on my pi every day (with a cron job). This way my files get backed up without either my desktop or laptop being turned on/connected to the internet. Folders are only copied if changes are detected in them.

## Installation
A client_secret.txt file needs to be created, with a client secret that's been generated at https://dev.onedrive.com/app-registration.htm
This file should take the form of AppID:Secret on one line.

Run the script using at least Python 3.4, and will also require the onedrivesdk (>= 1.0.5) to be installed in your Python environment. Use pip to install this: pip install onedrivesdk 

## Usage
All required settings are stored locally in the user's home dir (either %APPDATA%\OneDriveBackup on Windows or ~/.OneDriveBackup on Unix-like) once the client_secret.txt file is created, so the script just needs to be run as the correct user and it will automatically connect to OneDrive and perform the backup.

Settings are stored on OneDrive in the "OneDriveBackup" folder. It's recommended that you don't sync this with your computers.