import sys
import onedrivesdk
from onedrivesdk.helpers import GetAuthCodeServer

def main():
    # get the client secret first
    client_id_secret_str = open('client_secret.txt').read()
    client_id_secret = client_id_secret_str.split(":")
    if len(client_id_secret) != 2:
        print('Client secret not found or invalid. client_secret.txt required in the form: client_id:client_secret')
        sys.exit()

    # authenticate - https://github.com/OneDrive/onedrive-sdk-python
    redirect_uri = 'https://login.live.com/oauth20_desktop.srf'
    client = onedrivesdk.get_default_client(client_id=client_id_secret[0],
                                            scopes=['wl.signin',
                                            'wl.offline_access',
                                            'onedrive.readwrite'])

    auth_url = client.auth_provider.get_auth_url(redirect_uri)
    print('Copy the URL into a web browser and authenticate: ' + auth_url)
    
    # take a response from the user - only real way of making auth work on machines with no display
    code_url = input('Paste the URL from the address bar here: ')
    code = code_url.split('code=')[1].split('&')[0]

    client.auth_provider.authenticate(code, redirect_uri, client_id_secret[1])
    
    items = client.item(drive="me", id="root").children.get()
    for item in items:
        print(item.name)

if __name__ == '__main__':
    main()
