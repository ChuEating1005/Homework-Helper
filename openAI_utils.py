#from openai import OpenAI
from langchain_openai import ChatOpenAI
#from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain.memory import ConversationBufferMemory
#load_dotenv()
import os

# 讀取暫存檔的路徑 丟給openAI處理 回傳回應
def process_pdf_file(file_path):
    # 初始化openAI
    openai_api_key = os.getenv('OPENAI_API_KEY')
    llm = ChatOpenAI(model="gpt-3.5-turbo", openai_api_key=openai_api_key)
    loader = PyPDFLoader(file_path)
    pdf_text= loader.load_and_split()
    response = llm.invoke((pdf_text[0].page_content) + "\n這篇文章的大綱是什麼,用繁體中文回答").content  
    return response

# 把對話內容丟給OPENAI回答
def handle_conversation(input_text):
    openai_api_key = os.getenv('OPENAI_API_KEY')
    llm = ChatOpenAI(model="gpt-3.5-turbo", openai_api_key=openai_api_key)
    response = llm.invoke(input_text).content 
    return response
