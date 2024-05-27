#from openai import OpenAI
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
load_dotenv()

llm = OpenAI(temperature=0)
memory = ConversationBufferMemory()
template = """你是一個友善的學習助理，你接下來會跟使用者來對話。

對話記錄：
{history}

使用者新訊息： {question}
你的回應："""

prompt = PromptTemplate.from_template(template)
# 初始化 LLMChain 並將記憶體與其連接
conversation = LLMChain(
    llm=llm,
    prompt=prompt,
    verbose=True,
    memory=memory
)

while True:
    question = input()
    conversation({
    'question': question
    })
# llm = ChatOpenAI()
# loader = PyPDFLoader("test.pdf")
# pdf_text= loader.load_and_split()
#user_question = input("請輸入你的問題: ")
#combined_input = pdf_text[0].page_content + "\n這段文字的大綱" 
#response = llm.invoke(combined_input).content
#print("AI 回應:", response)
# while(True):
#     print("input:")
#     question = input()
#     print("\noutput:")
#     print(llm.invoke(question).content)
#     if question  == "0":
#         break

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

    




