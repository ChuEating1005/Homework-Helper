#from openai import OpenAI
from langchain_openai import ChatOpenAI
#from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain.memory import ConversationBufferMemory
#load_dotenv()
import os
llm = None
memory = None

def initialize_openai():
    global llm, memory
    if llm is None:
        openai_api_key = os.getenv('OPENAI_API_KEY')
        llm = ChatOpenAI(model="gpt-3.5-turbo", openai_api_key=openai_api_key)
        memory = ConversationBufferMemory()
        
def process_pdf_file(file_path):
    #initialize_openai()
    loader = PyPDFLoader(file_path)
    pdf_text= loader.load_and_split()
    combined_input = pdf_text[0].page_content 
    memory.chat_memory.add_user_message(combined_input)
    response = llm.invoke(str(memory.chat_memory.messages) + "\n這篇文章的大綱是什麼,用繁體中文回答").content  +"\nhistory:"+ str(memory.chat_memory.messages)
    memory.chat_memory.add_ai_message(response)
    return response

def handle_conversation(input_text):
    #initialize_openai()
    memory.chat_memory.add_user_message(input_text)
    response = llm.invoke(memory.chat_memory.messages).content +"\nhistory:"+ str(memory.chat_memory.messages)
    
    memory.chat_memory.add_ai_message(response)
    return response

def clear_memory():
    memory.clear()
