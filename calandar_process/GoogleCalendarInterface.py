from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
import json
from CalandarUtils import HomeworkTask
from datetime import datetime, timezone, timedelta
from config import CLIENT_ID, PROJECT_ID, AUTH_URI, TOKEN_URI ,AUTH_PROVIDER_URI,CLIENT_SECRET,REDIRECT_URIS
class GoogleCalendarInterface():
    def __init__(self):
        SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
        
        creds = None
        data = {
            "installed": {
                "client_id": CLIENT_ID,
                "project_id": PROJECT_ID,
                "auth_uri": AUTH_URI,
                "token_uri": TOKEN_URI,
                "auth_provider_x509_cert_url": AUTH_PROVIDER_URI,
                "client_secret": CLIENT_SECRET,
                "redirect_uris": [REDIRECT_URIS]
            }
        }

        try:
            with open("calandarAPI/credentials.json", 'w') as json_file:
                json.dump(data, json_file, indent=4)
        except Exception as e:
            print("Failed to write to file:", e)
            
        # Try to get credentials from cache
        if os.path.exists("calandarAPI/token.json"):
            creds = Credentials.from_authorized_user_file("calandarAPI/token.json", SCOPES)
            
        # Request user to give credential if not found
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file("calandarAPI/credentials.json", SCOPES)
                creds = flow.run_local_server(port=0)
                
        # Save the credentials for the next run
        with open("calandarAPI/token.json", "w") as token:
            token.write(creds.to_json())

        # Building the calandar service
        try:
            service = build("calendar", "v3", credentials=creds)
            self.service = service            
        except HttpError as error:
            print(f"An error occurred: {error}")
    
    #return (start time, end time) of events before deadline
    def get_events_time_before(self, deadline: datetime) -> list:
        events_result = (
            self.service.events().list(
                calendarId="primary",
                maxResults=10,
                timeMin=datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z",
                timeMax=deadline.astimezone(timezone.utc).replace(tzinfo=None).isoformat() + "Z",
                singleEvents=True,
                orderBy="startTime",
            ).execute()
        )
        events = events_result.get("items", [])
        
        return [(datetime.fromisoformat(event['start']['dateTime']).replace(tzinfo=None), datetime.fromisoformat(event['end']['dateTime']).replace(tzinfo=None)) for event in events]
    
    # startTime: Time when the event begins in current time zone
    def add_event(self, startTime: datetime, task: HomeworkTask):
        endTime = startTime + timedelta(minutes=task.duration)
        event = {
            'summary': "[Homework Helper] " + task.source_pdf,
            'description': task.description,
            'start': {
                'dateTime': startTime.astimezone(timezone.utc).replace(tzinfo=None).isoformat(),
                'timeZone': 'Etc/UTC'
            },
            'end': {
                'dateTime': endTime.astimezone(timezone.utc).replace(tzinfo=None).isoformat(),
                'timeZone': 'Etc/UTC'
            },
        }

        event = self.service.events().insert(calendarId='primary', body=event).execute()