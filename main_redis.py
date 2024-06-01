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
    RedisChatMessageHistory,
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
REDIS_URL = os.getenv("REDIS_URL")
MODEL = "text-embedding-3-small"
openai.api_key = OPENAI_API_KEY


def create_index(user_id):
    pinecone = PineconeClient(api_key=PINECONE_API_KEY)
    index_name = user_id + "db"
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

def create_memory(user_id):
    # Create a redis chat message history
    history = RedisChatMessageHistory(
        session_id=user_id, 
        url=REDIS_URL
    )
    
    # Create a conversation buffer memory
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        input_key="input",
        return_messages=True,
        chat_memory=history,
    )
    return memory

def create_chain(vectorStore, memory):
    model = ChatOpenAI(
        model="gpt-3.5-turbo-1106",
        temperature=0.4
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system","""
            Goal: You are an efficient homework assistant, helping users complete their homework, providing relevant information and suggestions, and effectively interacting with Notion and Google Calendar.
            Main Functions:
            1. Answer Questions: Answer users' questions about homework, including theoretical explanations, tool usage, references, etc.
            2. Provide Tools and Website Recommendations: Recommend suitable tools, websites, and references based on homework requirements.
            3. Time Management: Read the user's Google Calendar events, suggest the best time to complete homework, and add related tasks to the calendar.
            4. Record and Manage: Write Q&A records and to-do items into Notion for easy user viewing and management.
            Requirements:
            1. Accurate Answers to Users' Questions: The model needs to have sufficient knowledge to answer various homework-related questions.
            2. Recommend Relevant Resources: Provide users with the necessary tools, websites, references, etc., to help them complete their homework.
            3. Effective Time Management: Suggest reasonable time to complete homework based on the user's schedule and record tasks in the calendar and Notion.
            4. Integrate APIs: Implement integration with Notion and Google Calendar APIs for data reading and writing operations."""),
        ("system", "Answer the user's questions based on the context: {context}"),
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
    return response["answer"]["text"]

def refresh_memory(memory):
    memory.clear()

def main():
    user_id = input("Enter your user ID: ")
    index = create_index(user_id)
    memory = create_memory(user_id)
    embeddings = OpenAIEmbeddings(model=MODEL, openai_api_key=OPENAI_API_KEY)
    vectorStore = Pinecone.from_existing_index(index_name=user_id + "db", embedding=embeddings)

    chain = create_chain(vectorStore, memory)
    refresh_memory(memory)
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
            print("Assistant:", response)

if __name__ == "__main__":
    main()