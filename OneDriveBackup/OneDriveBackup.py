import sys
import platform
import os
import time
import logging
import onedrivesdk
from onedrivesdk.helpers import GetAuthCodeServer

def main():
    os.makedirs(get_app_local_storage_path(), exist_ok=True)
    logging.basicConfig(filename=os.path.join(get_app_local_storage_path(), 'log'), filemode='w', 
        level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
    logging.info('OneDriveBackup started...')
    
    client = auth()

    setup(client)


def copy_folder(client):
    logging.info('Start copy')
    ref = onedrivesdk.ItemReference()
    ref.id = 'EC7CE424F7CB9079!23588'
    copy_operation = client.item(drive="me", id="EC7CE424F7CB9079!19151").copy(name="USAPicsTest", parent_reference=ref).post() # USA Pics
    copy_operation._completed = True # Need to use this rather than _stop_poll_on_thread() until https://github.com/OneDrive/onedrive-sdk-python/pull/31 is merged

def setup(client):
    # try and download our settings file /OneDriveBackup/settings to our app storage, if it doesn't exist then create and upload it
    onedrivebackup_folder = client.item(drive="me", path="OneDriveBackup").children.get()
    for item in onedrivebackup_folder:
        if item.name == "settings":
            client.item(drive="me", id=item.id).download(get_settings_path())

    if not os.path.isfile(get_settings_path()):
        edit_settings(client)

def edit_settings(client):
    with open(get_settings_path(), 'w') as settings:
        settings.write('BackupFolders=')
        # get all the root's children so user can select which folders to backup - ignore the 'OneDriveBackup' folder
        folders = client.item(drive='me', id='root').children.get()
        for folder in folders:
            if folder.name != "OneDriveBackup" and input('Do you want to include folder "' + folder.name + '" in the backup? Yes=Y\t') == 'Y':
                settings.write(folder.id + ',')

        settings.write('\nBackupsToKeep=' + input('How many backups do you want to keep?\t'))
        settings.close()
        uploaded_item = client.item(drive="me", path="OneDriveBackup").children["settings"].upload(get_settings_path())
        logging.info('Updated & uploaded settings')
    

def auth():
    # get the client secret from our text file - register this https://dev.onedrive.com/app-registration.htm
    client_id_secret_str = open('client_secret.txt').read()
    client_id_secret = client_id_secret_str.split(':')
    if len(client_id_secret) != 2:
        logging.critical('client_secret.txt not found in this directory, or it\'s invalid. Form should be: client_id:client_secret')
        logging.critical('client_id & client_secret can be obtained by registering the app at https://dev.onedrive.com/app-registration.htm')
        sys.exit()

    client = onedrivesdk.get_default_client(client_id=client_id_secret[0],
                                            scopes=['wl.signin',
                                            'wl.offline_access',
                                            'onedrive.readwrite'])
    
    # load an existing session or load a new one
    if os.path.isfile(get_session_path()):
        logging.info('Loading previous session file from ' + get_session_path())
        client.auth_provider.load_session(path=get_session_path())
        client.auth_provider.refresh_token()
        logging.info('Token refreshed and session loaded')
        return client
    else:
        return auth_new(client, client_id_secret[1])


def auth_new(client, client_secret):
    logging.info('Authenticating a new user')
    redirect_uri = 'https://login.live.com/oauth20_desktop.srf'
    auth_url = client.auth_provider.get_auth_url(redirect_uri)
    print('Copy the URL into a web browser and authenticate: ' + auth_url)
    
    # take the response URL from the user - only real way of making auth work on machines with no display
    code_url = input('Paste the URL from the address bar here: ')
    code = code_url.split('code=')[1].split('&')[0]

    client.auth_provider.authenticate(code, redirect_uri, client_secret)

    os.makedirs(get_app_local_storage_path(), exist_ok=True)
    with open(get_session_path(), 'w') as f:
        f.close() # close the file straight away - we only create it here

    client.auth_provider.save_session(path=get_session_path())
    logging.info('New user authenticated and session saved to ' + get_session_path())
    return client

def is_int(s):
    try: 
        int(s)
        return True
    except ValueError:
        return False    

def get_session_path():
    return os.path.join(get_app_local_storage_path(), 'session')

def get_settings_path():
    return os.path.join(get_app_local_storage_path(), 'settings')

def get_app_local_storage_path():
    if platform.system() == 'Windows':
        return os.path.expanduser('~') + '\\AppData\\Local\\OneDriveBackup'
    else:
        return os.path.expanduser('~') + '/.OneDriveBackup'


if __name__ == '__main__':
    main()
