from __future__ import print_function
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

import socket
import pickle
import os.path
import sqlite3

SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly']
DEFAULT_PATH = os.path.join(os.path.dirname(__file__), 'drive_database.db')

def db_connect(db_path=DEFAULT_PATH):
    con = sqlite3.connect(db_path)
    return con

def main():
    socket.setdefaulttimeout(60000)
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('drive', 'v3', credentials=creds)

    sqlite_insert_query = """INSERT INTO drive_files
                          (kind,id,name,mimeType,spaces,webViewLink,createdTime,owners,shared,ownedByMe,quotaBytesUsed) 
                          VALUES (:kind,:id,:name,:mimeType,:spaces,:webViewLink,:createdTime,:owners,:shared,:ownedByMe,:quotaBytesUsed);"""
    drive_files_sql = """
    CREATE TABLE if not exists drive_files (
        kind text NOT NULL,
        id text NOT NULL,
        name text NOT NULL,
        mimeType text NOT NULL,
        spaces text NOT NULL,
        webViewLink text NOT NULL,
        createdTime text NOT NULL,
        owners text NOT NULL,
        shared text NOT NULL,
        ownedByMe text NOT NULL,
        quotaBytesUsed  text NOT NULL)"""

    try: 
        con = db_connect() 
        cursor = con.cursor() 
        cursor.execute(drive_files_sql)
        con.commit()
        cursor.close()
    except sqlite3.Error as error:
        print("Failed to insert data into sqlite table", error)
    finally:
        if (con):
           con.close()      
    
    page_token = None
    while True:
        results = service.files().list(supportsTeamDrives=True,
                                       includeTeamDriveItems=True,
                                       pageSize=1000,
                                       fields="nextPageToken, files(kind,id,name,mimeType,spaces,webViewLink,createdTime,owners/emailAddress,shared,ownedByMe,quotaBytesUsed)").execute()

        items = results.get('files', [])
        try:
           con = db_connect() 
           cursor = con.cursor()
           cursor.executemany(sqlite_insert_query, [dict([a, str(x)] for a, x in b.items()) for b in items])
           
           con.commit()
           print("Total", cursor.rowcount, "Records inserted successfully into drive_files table")
           cursor.close()
        except sqlite3.Error as error:
           cursor._executed
           print("Failed to insert data into sqlite table", error)
        finally:
           if (con):
               con.close()           
        
        page_token = results.get('nextPageToken', None)
        if page_token is None:
            print("No more results")
            break
        
if __name__ == '__main__':
    main()
