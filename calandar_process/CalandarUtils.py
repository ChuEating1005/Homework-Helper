from datetime import datetime, timezone, timedelta
import os.path

from GoogleCalandarInterface import GoogleCalandarInterface
from dotenv import load_dotenv
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
        self.tasks = []
    
    def initialize(self, pinecone_index_name):
        self.initialized = True
        self.llm = OpenAIHandler(
            PINECONE_API_KEY, 
            PINECONE_ENVIRONMENT, 
            pinecone_index_name,
            OPENAI_API_KEY,
            MODEL_NAME
        )
        self.pinecone_index_name = pinecone_index_name
    
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
    def get_homework_deadline(self, homework: str) -> datetime:
        llm = OpenAIHandler(
            PINECONE_API_KEY, 
            PINECONE_ENVIRONMENT, 
            self.pinecone_index_name,
            OPENAI_API_KEY,
            MODEL_NAME
        )
        
        response = llm.handle_conversation('What is the deadline of ' + homework + '?. Reply with only Month/Date, in format such as "2/28"')
        
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
        calandar = GoogleCalandarInterface()
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
            
    
# if __name__ == '__main__':
#     calandar = CalandarUtils()    
#     print(calandar.estimate_task_time("Numeric Method"))
#     print('---')
#     for i in calandar.tasks:
#         print(i)        
#     print('---')
#     calandar.add_to_calandar()
    