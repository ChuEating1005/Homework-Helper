from datetime import datetime, timezone, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
from ai_process.openAI_utils import OpenAIHandler
from config import LINEBOT_API_KEY, OPENAI_API_KEY, PINECONE_API_KEY, PINECONE_ENVIRONMENT, MODEL_NAME

class HomeworkTask:
    # description: Short description of a task
    # source_pdf: The task is from which homework pdf
    # duration: How much time it is estimated to finish the task in minutes
    
    def __init__(self, source_pdf: str, description: str, duration: int):        
        self.source_pdf = source_pdf
        self.description = description
        self.duration = duration
    
    def __str__(self) -> str:
        return f"({self.source_pdf}, {self.description}, {self.duration})"

class CalandarUtils:
    def __init__(self):
        self.initialized = False
        self.llm = None
        self.pinecone_index_name = None
        self.user_id = None
        self.tasks = []
    
    def initialize(self, user_id, pinecone_index_name):
        self.initialized = True
        self.llm = OpenAIHandler(
            PINECONE_API_KEY, 
            PINECONE_ENVIRONMENT, 
            pinecone_index_name,
            OPENAI_API_KEY,
            MODEL_NAME
        )
        self.user_id = user_id
        self.pinecone_index_name = pinecone_index_name
    
    # question: A string naming which homework or task is the target
    # return: The string response of estimate time with description
    #   Save a list of HomeworkTask at self.tasks
    def estimate_task_time(self, question: str) -> str:
        response = self.llm.handle_conversation(self.user_id, "Estimate how much time you need to finish \'" + question + "\'. Estimate each task and reply in minutes.")
        formattedResponse = self.llm.handle_conversation(self.user_id, "Format above estimation into \'homework name$$task description$$time taken in minutes, only numbers\'. Seperated by double dollar sign is required. Seperate each task with a new line.")
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
    def get_homework_deadline(self, homework: str) -> datetime:
        llm = OpenAIHandler(
            PINECONE_API_KEY, 
            PINECONE_ENVIRONMENT, 
            self.pinecone_index_name,
            OPENAI_API_KEY,
            MODEL_NAME
        )
        
        response = llm.handle_conversation(self.user_id, 'What is the deadline of ' + homework + '?. Reply with only Month/Date, in format such as "2/28"')
        
        month, date = map(int, response.split('/'))
        
        now = datetime.now()
        year = now.year
        if month < now.month: year += 1 # Deadline is in the next year
        return datetime(year, month, date, 23, 59)
              
    
    # Add self.tasks to the calandar
    def add_to_calandar(self) -> None:
        # Sort task by deadline
        task_deadline = dict()
        for task in self.tasks:
            if task.source_pdf not in task_deadline:
                task_deadline[task.source_pdf] = self.get_homework_deadline(task.source_pdf)
        print(task_deadline)
        self.tasks.sort(key=lambda x: task_deadline[x.source_pdf])
        
        # Decode available time
        calandar = GoogleCalendarInterface()
        occupied_times = calandar.get_events_time_before(task_deadline[self.tasks[-1].source_pdf] + timedelta(days=7))
        occupied_times.append((datetime.now() + timedelta(days=3650), datetime.now() + timedelta(days=3650)))
        
        # Add event         
        curr = datetime.now()
        event_index = 0
        for task in self.tasks:
            while True:
                if curr > occupied_times[event_index][1]:
                    event_index += 1
                elif occupied_times[event_index][0] <= curr and curr < occupied_times[event_index][1]:
                    curr = occupied_times[event_index][1]
                    event_index += 1
                else:
                    currEnd = curr + timedelta(minutes=task.duration)
                    if occupied_times[event_index][0] <= currEnd and currEnd < occupied_times[event_index][1]:
                        curr = occupied_times[event_index][1]
                        event_index += 1
                    else:
                        calandar.add_event(curr, task)
                        curr = currEnd
                        break
class GoogleCalendarInterface():
    def __init__(self):
        SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
        
        creds = None
        # data = {
        #     "installed": {
        #         "client_id": CLIENT_ID,
        #         "project_id": PROJECT_ID,
        #         "auth_uri": AUTH_URI,
        #         "token_uri": TOKEN_URI,
        #         "auth_provider_x509_cert_url": AUTH_PROVIDER_URI,
        #         "client_secret": CLIENT_SECRET,
        #         "redirect_uris": [REDIRECT_URIS]
        #     }
        # }

        # try:
        #     with open("calandarAPI/credentials.json", 'w') as json_file:
        #         json.dump(data, json_file, indent=4)
        # except Exception as e:
        #     print("Failed to write to file:", e)
            
        # Try to get credentials from cache
        if os.path.exists("calandar_process/calandarAPI/token.json"):
            creds = Credentials.from_authorized_user_file("calandar_process/calandarAPI/token.json", SCOPES)
            
        # Request user to give credential if not found
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('calandar_process/calandarAPI/credential_web.json', SCOPES)
                creds = flow.run_local_server(port=0)
                
        # Save the credentials for the next run
        with open("calandar_process/calandarAPI/token.json", "w") as token:
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
    