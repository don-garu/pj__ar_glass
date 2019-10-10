from __future__ import print_function
import pickle
import os.path
import base64

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = 'https://www.googleapis.com/auth/gmail.readonly'

def main():
    creds = None

    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'my_credentials.json', SCOPES
            )
            creds = flow.run_console()
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    service = build('gmail', 'v1', credentials=creds)

    # Call the Gmail API to fetch INBOX
    results = service.users().messages().list(userId='me', labelIds = ['UNREAD']).execute()
    messages = results.get('messages', [])

    if not messages:
        print('No messages found.')
    else:
        print('Message snippets:')
        for message in messages:
#            print(message['payload']['headers']['name'] +  ' : ' + message['payload']['headers']['value'])
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            for test in msg['payload']['headers']:
                if test['name'] == "Subject":
                    print(test)
            if 'parts' in msg['payload'].keys():
                print(base64.b64decode(msg['payload']['parts'][0]['body']['data']))
#                print(msg['payload']['body']['data'])
            #print(msg['payload']['body'])
#            print(msg['payload']['headers'][0])
#            print(msg['payload']['headers'][1])
#            print(msg['payload']['headers'][3])

if __name__ == '__main__':
    main()
