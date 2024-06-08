import datetime
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
from openAI_utils import LineBotHandler
from config import LINEBOT_API_KEY, OPENAI_API_KEY, PINECONE_API_KEY, PINECONE_ENVIRONMENT, PINECONE_INDEX_NAME, MODEL_NAME

class HomeworkTask:
    # description: Short description of a task
    # source_pdf: The task is from which homework pdf
    # duration: How much time it is estimated to finish the task in minutes
    
    def __init__(self, source_pdf: str, description: str, duration: int):        
        self.source_pdf = source_pdf
        self.description = description
        self.duration = duration

class GoogleCalanderInterface:
    def __init__(self):
        SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
        
        creds = None
        # Try to get credentials from cache
        if os.path.exists("calanderAPI/token.json"):
            creds = Credentials.from_authorized_user_file("calanderAPI/token.json", SCOPES)
            
        # Request user to give credential if not found
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file("calanderAPI/credentials.json", SCOPES)
                creds = flow.run_local_server(port=0)
                
        # Save the credentials for the next run
        with open("calanderAPI/token.json", "w") as token:
            token.write(creds.to_json())

        # Building the calander service
        try:
            service = build("calendar", "v3", credentials=creds)
            self.service = service            
        except HttpError as error:
            print(f"An error occurred: {error}")
    
    #return (start time, end time) of events before deadline
    def get_events_time_before(self, deadline: datetime.datetime) -> list:
        events_result = (
            self.service.events().list(
                calendarId="primary",
                maxResults=10,
                timeMin=datetime.datetime.now(datetime.UTC).replace(tzinfo=None).isoformat() + "Z",
                timeMax=deadline.astimezone(datetime.UTC).replace(tzinfo=None).isoformat() + "Z",
                singleEvents=True,
                orderBy="startTime",
            ).execute()
        )
        events = events_result.get("items", [])
        
        return [(event['start']['dateTime'], event['end']['dateTime']) for event in events]
    
    # startTime: Time when the event begins in current time zone
    def add_event(self, startTime: datetime.datetime, task: HomeworkTask):
        endTime = startTime + datetime.timedelta(minutes=task.duration)
        event = {
            'summary': "[Homework Helper] " + task.source_pdf + "作業",
            'description': task.description,
            'start': {
                'dateTime': startTime.astimezone(datetime.UTC).replace(tzinfo=None).isoformat(),
                'timeZone': 'Etc/UTC'
            },
            'end': {
                'dateTime': endTime.astimezone(datetime.UTC).replace(tzinfo=None).isoformat(),
                'timeZone': 'Etc/UTC'
            },
        }

        event = self.service.events().insert(calendarId='primary', body=event).execute()

class CalanderUtils:
    def __init__(self):
        self.llm = LineBotHandler(
            PINECONE_API_KEY, 
            PINECONE_ENVIRONMENT,
            PINECONE_INDEX_NAME,
            OPENAI_API_KEY,
            MODEL_NAME
        )
        
        self.tasks = []
    
    # question: A string naming which homework or task is the target
    # return: The string response of estimate time with description
    #   Save a list of HomeworkTask at self.tasks
    def estimate_task_time(self, question: str) -> str:
        response = self.llm.handle_conversation("Estimate how much time you need to finish '" + question + "'. Estimate each task and reply in minutes.")
        formattedResponse = self.llm.handle_conversation("Format above estimation into 'homework name$$task description$$time taken in minutes, only numbers'. Seperated by double dollar sign is required. Seperate each task with a new line.")
        #print(formattedResponse)
        
        result = []
        for task in formattedResponse.split('\n'):
            temp = task.split('$$')
            try:
                result.append(HomeworkTask(temp[0], temp[1], int(temp[2])))
            except:
                pass
            
        self.tasks = result
        return response
    
    # homework: A single homework
    # return: Deadline of the homework
    def get_homework_deadline(self, homework: str) -> datetime.datetime:
        llm = LineBotHandler(
            PINECONE_API_KEY, 
            PINECONE_ENVIRONMENT,
            PINECONE_INDEX_NAME,
            OPENAI_API_KEY,
            MODEL_NAME
        )
        response = llm.handle_conversation('What is the deadline of ' + homework + '?. Reply in Month/Date')
        
        month, date = map(int, response.split('/'))
        
        now = datetime.datetime.now()
        year = now.year
        if month < now.month: year += 1
        return datetime.datetime(year, month, date, 23, 59)
    
    # Add self.tasks to the calander
    def add_to_calander(self) -> None:
        
        
    
if __name__ == '__main__':
    calander = CalanderUtils()    
    print(calander.estimate_task_time("Numeric method"))
    