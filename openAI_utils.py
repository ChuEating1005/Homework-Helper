#from openai import OpenAI
from langchain_openai import ChatOpenAI
#from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain.memory import ConversationBufferMemory
#load_dotenv()
import os
from app import llm, user_memory  # 导入全局变量
def get_user_memory(user_id):
    if user_id not in user_memory:
        user_memory[user_id] = ConversationBufferMemory()
    return user_memory[user_id]
        
def process_pdf_file(user_id,file_path):
    memory = get_user_memory(user_id)
    loader = PyPDFLoader(file_path)
    pdf_text= loader.load_and_split()
    combined_input = pdf_text[0].page_content 
    memory.chat_memory.add_user_message(combined_input)
    response = llm.invoke(str(memory.chat_memory.messages) + "\n這篇文章的大綱是什麼,用繁體中文回答").content  +"\nhistory:"+ str(memory.chat_memory.messages)
    memory.chat_memory.add_ai_message(response)
    return response

def handle_conversation(user_id,input_text):
    memory = get_user_memory(user_id)
    memory.chat_memory.add_user_message(input_text)
    response = llm.invoke(memory.chat_memory.messages).content +"\nhistory:"+ str(memory.chat_memory.messages)
    
    memory.chat_memory.add_ai_message(response)
    return response

def clear_memory(user_id):
    memory = get_user_memory(user_id)
    memory.chat_memory.clear()
