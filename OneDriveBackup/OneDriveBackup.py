import sys
import platform
import os
import time
import onedrivesdk
from onedrivesdk.helpers import GetAuthCodeServer

def main():
    client = auth()
    
    items = client.item(drive="me", id="root").children.get()
    for item in items:
        print(item.name)

def auth():
    # load an existing session or load a new one

    # get the client secret from our text file - register this https://dev.onedrive.com/app-registration.htm
    client_id_secret_str = open('client_secret.txt').read()
    client_id_secret = client_id_secret_str.split(":")
    if len(client_id_secret) != 2:
        print('Client secret not found or invalid. client_secret.txt required in the form: client_id:client_secret')
        sys.exit()

    client = onedrivesdk.get_default_client(client_id=client_id_secret[0],
                                            scopes=['wl.signin',
                                            'wl.offline_access',
                                            'onedrive.readwrite'])

    if os.path.isfile(get_session_path()):
        print(get_time() + 'Loading previous session file from ' + get_session_path())
        client.auth_provider.load_session(path=get_session_path())
        client.auth_provider.refresh_token()
        return client
    else:
        return auth_new(client, client_id_secret[1])


def auth_new(client, client_secret):
    redirect_uri = 'https://login.live.com/oauth20_desktop.srf'
    auth_url = client.auth_provider.get_auth_url(redirect_uri)
    print('Copy the URL into a web browser and authenticate: ' + auth_url)
    
    # take the response URL from the user - only real way of making auth work on machines with no display
    code_url = input('Paste the URL from the address bar here: ')
    code = code_url.split('code=')[1].split('&')[0]

    client.auth_provider.authenticate(code, redirect_uri, client_secret)

    os.makedirs(os.path.dirname(get_session_path()), exist_ok=True)
    with open(get_session_path(), 'w') as f:
        f.close() # close the file straight away - we only create it here

    client.auth_provider.save_session(path=get_session_path())
    return client

def get_session_path():
    if platform.system() == 'Windows':
        return os.path.expanduser("~") + '\\AppData\\Local\\OneDriveBackup\\session'
    else:
        return os.path.expanduser("~") + '/.OneDriveBackup/session'

def get_time():
    return time.strftime("%H:%M:%S") + '\t'

if __name__ == '__main__':
    main()
