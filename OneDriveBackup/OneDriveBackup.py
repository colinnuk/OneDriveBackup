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

    settings = setup(client)

    # purge extra folders first - this is light work and OneDrive does this very quickly. Copying folders below takes ages!
    purge_folders(client, settings)

    copy_folders(client, settings['BackupFolders'])
    
    sys.exit()

def purge_folders(client, settings):
    # this method will purge the oldest backups from each backup top level folder, so that the number of folders doesn't exceed BackupsToKeep
    if 'BackupsToKeep' not in settings: 
        return
    split_folders = settings['BackupFolders'].split(',')
    for folder_id in split_folders:
        try:
            top_level_backup_folder = client.item(drive='me', path='OneDriveBackup/' + folder_id).get()
            backup_folders = client.item(drive='me', id=top_level_backup_folder.id).children.request(order_by='lastModifiedDateTime asc').get()
            num_backups_to_delete = len(backup_folders) - int(settings['BackupsToKeep'])
            if num_backups_to_delete < len(backup_folders):
                for i, item in enumerate(backup_folders):
                    if i < num_backups_to_delete:
                        logging.info('Deleting backup for ' + folder_id + ', dated ' + item.created_date_time.strftime('%Y%m%d %H%M'))
                        client.item(drive='me', id=item.id).delete()
        except onedrivesdk.error.OneDriveError as e:
            if e.code == 'itemNotFound':
                logging.info('Top level folder for ' + folder_id + ' not found, so not purging backups')
            else:
                raise e

def copy_folders(client, backup_folders):
    split_folders = backup_folders.split(',')
    for folder_id in split_folders:
        copy_folder(client, folder_id)


def copy_folder(client, folder_id):
    if folder_id == '':
        return
    
    try:
        top_level_backup_folder = client.item(drive='me', path='OneDriveBackup/' + folder_id).get()
        # if we have a corresponding top level folder then check when it was last backed up, if nothing has changed since the last backup then we just return
        # top level folder is the ID of the real folder that is backed up, and it contains folders whose names are the delta tokens of the folder when the backup was created
        most_recent_backup = client.item(drive='me', id=top_level_backup_folder.id).children.request(top=1, order_by='lastModifiedDateTime desc').get()
        if most_recent_backup:
            modified_items = client.item(drive='me', id=folder_id).delta(most_recent_backup[0].name).get()
            if not modified_items:
                logging.info('No modified items in ' + folder_id + ' - not backing this folder up')
                return
    except onedrivesdk.error.OneDriveError as e:
        if e.code == 'itemNotFound':
            # create the top level backup folder if it was not found - date level folders will be stored in here
            new_folder_item = onedrivesdk.Item()
            new_folder_item.name = folder_id
            new_folder_item.folder = onedrivesdk.Folder()
            top_level_backup_folder = client.item(drive='me', path='OneDriveBackup').children.add(new_folder_item)
        else:
            raise e

    # get the latest delta token to use as our folder name
    #    this enumerates the current state of the folder with a token we can use to query OneDrive again to see if any files have been modified
    delta_token = client.item(drive='me', id=folder_id).delta('latest').get()
    parent_ref = onedrivesdk.ItemReference()
    parent_ref.id = top_level_backup_folder.id
    logging.info('Copy folder id ' + folder_id + ' into folder id ' + top_level_backup_folder.id + ' as ' + delta_token.token)
    copy_operation = client.item(drive='me', id=folder_id).copy(name=delta_token.token, parent_reference=parent_ref).post()
    copy_operation._completed = True # Need to use this rather than _stop_poll_on_thread() until https://github.com/OneDrive/onedrive-sdk-python/pull/31 is merged

def get_settings():
    settings = {}
    lines = [line.strip() for line in open(get_settings_path())]
    for l in lines:
        split_line = l.split('=')
        settings[split_line[0]] = split_line[1]

    #if the settings file doesn't contain the below items we need to quit
    if 'BackupFolders' not in settings:
        logging.critical('Invalid settings file; should contain "BackupFolders" key')
        sys.exit()

    #if 'BackupsToKeep' is present, but not an integer, we need to quit
    if 'BackupsToKeep' in settings:
        if not is_int(settings['BackupsToKeep']):
            logging.critical('Invalid settings file; "BackupsToKeep" is not an integer')
            sys.exit()            

    return settings

def setup(client):
    # try and download our settings file /OneDriveBackup/settings to our app storage, if it doesn't exist then create and upload it
    onedrivebackup_folder = client.item(drive='me', path='OneDriveBackup').children.get()
    for item in onedrivebackup_folder:
        if item.name == 'settings':
            client.item(drive='me', id=item.id).download(get_settings_path())

    if not os.path.isfile(get_settings_path()):
        edit_settings(client)

    return get_settings()

def edit_settings(client):
    with open(get_settings_path(), 'w') as settings:
        settings.write('BackupFolders=')
        # get all the root's children so user can select which folders to backup - ignore the 'OneDriveBackup' folder
        folders = client.item(drive='me', id='root').children.get()
        for folder in folders:
            if folder.name != 'OneDriveBackup' and input('Do you want to include folder "' + folder.name + '" in the backup? Yes=Y\t') == 'Y':
                settings.write(folder.id + ',')

        backups_to_keep = input('How many backups do you want to keep?\t')
        if is_int(backups_to_keep) and int(backups_to_keep) != 0:
            settings.write('\nBackupsToKeep=' + backups_to_keep)
        settings.close()
        uploaded_item = client.item(drive='me', path='OneDriveBackup').children['settings'].upload(get_settings_path())
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
