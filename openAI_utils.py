#from openai import OpenAI
from langchain_openai import ChatOpenAI
#from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain.memory import ConversationBufferMemory
#load_dotenv()
import os
memory = ConversationBufferMemory()
openai_api_key = os.getenv('OPENAI_API_KEY')
llm = ChatOpenAI(model="gpt-3.5-turbo", openai_api_key=openai_api_key)

def process_pdf_file(file_path):
    loader = PyPDFLoader(file_path)
    pdf_text= loader.load_and_split()
    combined_input = pdf_text[0].page_content 
    memory.chat_memory.add_user_message(combined_input)
    response = llm.invoke(memory.get_messages()).content + "\n這篇文章的大綱是什麼,用繁體中文回答"
    memory.chat_memory.add_ai_message(response)
    return response

def handle_conversation(input_text):
    memory.chat_memory.add_user_message(input_text)
    response = llm.invoke(memory.get_messages()).content
    memory.chat_memory.add_ai_message(response)
    return response

def clear_memory():
    memory.clear()
# llm = ChatOpenAI()
# while(True):
#     print("input:")
#     question = input()
#     print("\noutput:")
#     print(llm.invoke(question).content)
#     if question  == "0":
#         break

#llm.invoke("Hello, world!")

# client = OpenAI()


# conversation_history = []  # 存储对话历史
# conversation_history.append(pdf_text[0].page_content)
# while True:
#     print("input:")
#     question = input()
    
#     if question == "0":
#         break
    
#     # 将先前的对话历史添加到messages中
#     messages = [{"role": "user", "content": q} for q in conversation_history]
#     messages.append({"role": "user", "content": question})
    
#     completion = client.chat.completions.create(
#         model="gpt-3.5-turbo",
#         messages=messages
#     )
    
#     # 存储模型的响应以便下次循环使用
#     response = completion.choices[0].message.content
#     conversation_history.append(response)
    
#     print(response)

    




