import os
import re
import openai
from dotenv import load_dotenv
from langchain_community.chat_models import ChatOpenAI
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Pinecone
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.chat_message_histories import (
    UpstashRedisChatMessageHistory,
)
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableParallel, RunnablePassthrough, RunnableLambda
from langchain_core.messages import HumanMessage, AIMessage
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain, LLMChain
from langchain.chains.history_aware_retriever import create_history_aware_retriever
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pinecone import Pinecone as PineconeClient, ServerlessSpec
from langchain.schema import Document
from langchain.memory import ConversationBufferMemory
import requests

# Load environment variables
load_dotenv()

# Get environment variables
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
UPSTASH_URL = os.getenv("UPSTASH_URL")
UPSTASH_TOKEN = os.getenv("UPSTASH_TOKEN")
MODEL = "text-embedding-3-small"
openai.api_key = OPENAI_API_KEY


def create_index(user_id):
    pinecone = PineconeClient(api_key=PINECONE_API_KEY)
    index_name = user_id + "db"
    #print(index_name)
    if index_name not in pinecone.list_indexes().names():
        pinecone.create_index(
            name=index_name,
            dimension=1536,
            metric="cosine",
            spec=ServerlessSpec(
                cloud='aws', 
                region='us-east-1'
            ) 
        )
    index = pinecone.Index(index_name)
    return index

# Define a function to create embeddings
def create_embeddings(texts):
    embeddings_list = []
    for text in texts:
        res = openai.Embedding.create(input=[text.page_content], engine=MODEL)
        embeddings_list.append(res['data'][0]['embedding'])
    return embeddings_list

# def find_match(input_text, num, index):
#     input_em = create_embeddings([Document(page_content=input_text, metadata={})])
#     result = index.query(vector=input_em[0], top_k=num, include_metadata=True)
#     matches = result['matches']
#     matched_texts = "\n".join([match['metadata']['text'] for match in matches])
#     return matched_texts

def create_chain(vectorStore):
    model = ChatOpenAI(
        model="gpt-3.5-turbo-1106",
        temperature=0
    )

    history = UpstashRedisChatMessageHistory(
        url=UPSTASH_URL, token=UPSTASH_TOKEN, ttl=500, session_id="chat1"
    )

    memory = ConversationBufferMemory(
        memory_key="chat_history",
        input_key="input",
        return_messages=True,
        chat_memory=history,
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "### Command ###\nAnswer the user's questions based on the context: {context}"),
        ("system","""
            ### Goal ###
            You are an efficient homework assistant, helping users complete their homework, providing relevant information and suggestions, and effectively interacting with Notion and Google Calendar.
            Main Functions:
            1. Answer Questions: Answer users' questions about homework, including theoretical explanations, tool usage, references, etc.
            2. Provide Tools and Website Recommendations: Recommend suitable tools, websites, and references based on homework requirements.
            3. Time Management: Read the user's Google Calendar events, suggest the best time to complete homework, and add related tasks to the calendar.
            4. Record and Manage: Write Q&A records and to-do items into Notion for easy user viewing and management.
            ### Requirements ###
            1. Make sure to access each part or chunk about the homework that is being discussed.
            2. Accurate Answers to Users' Questions: The model needs to have sufficient knowledge to answer various homework-related questions.
            3. Recommend Relevant Resources: Provide users with the necessary tools, websites, references, etc., to help them complete their homework.
            4. Effective Time Management: Suggest reasonable time to complete homework based on the user's schedule and record tasks in the calendar and Notion.
            5. Integrate APIs: Implement integration with Notion and Google Calendar APIs for data reading and writing operations."""),
            
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}")
    ])

    # Define the RAG chain
    chain = LLMChain(
        llm=model,
        prompt=prompt,
        verbose=True,
        memory=memory
    )

    retriever = vectorStore.as_retriever(search_kwargs={"k": 5})

    retriever_prompt = ChatPromptTemplate.from_messages([
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}"),
        ("user", "Given the above conversation, generate a search query to look up in order to get information relevant to the conversation")
    ])
    
    history_aware_retriever = create_history_aware_retriever(
        llm=model,
        retriever=retriever,
        prompt=retriever_prompt
    )

    retrieval_chain = create_retrieval_chain(
        # retriever, Replace with History Aware Retriever
        history_aware_retriever,
        chain
    )

    return retrieval_chain

def upload_pdf(index, embeddings, pdf_path, chunk_size=1000, chunk_overlap=100):
    #pinecone = Pinecone(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT)
    #index = pinecone.Index(PINECONE_INDEX_NAME)
    # Loading
    loader = PyPDFLoader(pdf_path)
    data = loader.load()
    # Chunking
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    documents = text_splitter.split_documents(data)
    # Embedding
    embeddings_list = [embeddings.embed_query(document.page_content) for document in documents]
    # Uploading
    records = [
        {"id": f"{pdf_path}_{i}", "values": value, "metadata": {"source": pdf_path, "chunk": i, "text": doc.page_content}}
        for i, (value, doc) in enumerate(zip(embeddings_list, documents))
    ]
    index.upsert(vectors=records)

def process_chat(chain, question):
    response = chain.invoke({
        "input": question
    })
    #print(response)
    return response["answer"]["text"]

# Example to process and upload PDF, and then query
def main():
    # query = "Assignment 3 有什麼問題？"
    # context = find_match(query)
    # # print("Context:", context)
    # context_docs = [Document(page_content=text, metadata={}) for text in context.split("\n")]
    # answer = chain.invoke({"context": context_docs, "question": query})
    # print(answer)
    user_id = input("Enter your user ID: ")
    index = create_index(user_id)
    embeddings = OpenAIEmbeddings(model=MODEL, openai_api_key=OPENAI_API_KEY)
    vectorStore = Pinecone.from_existing_index(index_name=user_id + "db", embedding=embeddings)

    chain = create_chain(vectorStore)
    # chat_history = []

    while True:
        user_input = input("You: ")

        if user_input.lower() == 'exit':
            break

        if user_input.lower() == 'upload':
            print("Which PDF file do you want to upload?")
            for i, pdf_path in enumerate(os.listdir("data")):
                print(f"{i+1}. {pdf_path}")
            choice = input("Enter the number of the PDF file: ")
            pdf_path = os.path.join("data/", os.listdir("data")[int(choice) - 1])
            print(pdf_path)
            upload_pdf(index, embeddings, pdf_path)
        else:
            response = process_chat(chain, user_input)
            #chat_history.append(HumanMessage(content=user_input))
            #chat_history.append(AIMessage(content=response))
            print("Assistant:", response)

if __name__ == "__main__":
    main()