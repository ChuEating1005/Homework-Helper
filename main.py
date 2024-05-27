from openai import OpenAI
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader

load_dotenv()


llm = ChatOpenAI()
loader = PyPDFLoader("test.pdf")
pdf_text= loader.load_and_split()
user_question = input("請輸入你的問題: ")
combined_input = pdf_text[0].page_content + "\n這段文字的大綱" 
response = llm.invoke(combined_input).content
print("AI 回應:", response)
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
# print("input:")
# question = input()
# completion = client.chat.completions.create(
#   model="gpt-3.5-turbo",
#   messages=[
#     {"role": "system", "content": "You are a poetic assistant, skilled in explaining complex programming concepts with creative flair."},
#     {"role": "user", "content": question }
#   ]
# )
# #"Compose a poem that explains the concept of recursion in programming."
# print("\noutput:")
# print(completion.choices[0].message.content)


