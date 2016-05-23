import onedrivesdk
from onedrivesdk.helpers import GetAuthCodeServer

#Code from https://github.com/OneDrive/onedrive-sdk-python
redirect_uri = "http://localhost:8080/"
client_secret = ""

client = onedrivesdk.get_default_client(client_id='0000000048196A75',
                                        scopes=['wl.signin',
                                                'wl.offline_access',
                                                'onedrive.readwrite'])

auth_url = client.auth_provider.get_auth_url(redirect_uri)

#this will block until we have the code
code = GetAuthCodeServer.get_auth_code(auth_url, redirect_uri)

client.auth_provider.authenticate(code, redirect_uri, client_secret)