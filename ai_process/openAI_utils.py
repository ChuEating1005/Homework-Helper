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
from redis_get.redis_db import RedisHandler
from config import REDIS_HOST,REDIS_PORT,REDIS_PASSWORD,REDIS_URL
# Load environment variables
#load_dotenv()

class OpenAIHandler:
    def __init__(self, pinecone_api_key, pinecone_environment, pinecone_index_name, openai_api_key, model_name):
        print("init")
        # Get environment variables
        self.PINECONE_API_KEY = pinecone_api_key
        self.PINECONE_ENVIRONMENT = pinecone_environment,
        self.PINECONE_INDEX_NAME = pinecone_index_name
        self.OPENAI_API_KEY = openai_api_key
        self.MODEL = model_name
        self.chat_history = []
        
    def preprocess_text(self,text):
        # Replace consecutive spaces, newlines and tabs
        text = re.sub(r'\s+', ' ', text)
        return text

    def create_index(self):
        pinecone = PineconeClient(api_key=self.PINECONE_API_KEY)
        index_name = self.PINECONE_INDEX_NAME
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
    def create_memory(self,user_id):
        # Create a redis chat message history
        redis_handler = RedisHandler(host=REDIS_HOST,port = REDIS_PORT,password=REDIS_PASSWORD)
        name = redis_handler.get_user_name(user_id)
        history = RedisChatMessageHistory(
            session_id=name, 
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
    def create_memory(self,user_id):
        # Create a redis chat message history
        redis_handler = RedisHandler(host=REDIS_HOST,port = REDIS_PORT,password=REDIS_PASSWORD)
        name = redis_handler.get_user_name(user_id)
        history = RedisChatMessageHistory(
            session_id=name, 
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
    
    def create_chain(self,vectorStore, memory):
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

    def upload_pdf(self,pdf_path, chunk_size=1000, chunk_overlap=100):
        embeddings = OpenAIEmbeddings(model=self.MODEL, openai_api_key=self.OPENAI_API_KEY)
        
        index = self.create_index()
        # Loading
        loader = PyPDFLoader(pdf_path)
        data = loader.load()
        # Chunking
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        documents = text_splitter.split_documents(data)
        # Embedding
        embeddings_list = [embeddings.embed_query(document.page_content) for document in documents]
        # Uploading
        records = [
            {"id": f"{pdf_path}_{i}", "values": value, "metadata": {"source": pdf_path, "chunk": i, "text": doc.page_content}}
            for i, (value, doc) in enumerate(zip(embeddings_list, documents))
        ]
        index.upsert(vectors=records)

    def process_chat(self,chain, question):
        response = chain.invoke({
            "input": question
        })
        return response["answer"]["text"]

    def refresh_memory(self,user_id):
        memory = self.create_memory(user_id)
        memory.clear()
        
    def handle_conversation(self,user_id,user_input):
        # query = "Assignment 3 有什麼問題？"
        # context = find_match(query)
        # # print("Context:", context)
        # context_docs = [Document(page_content=text, metadata={}) for text in context.split("\n")]
        # answer = chain.invoke({"context": context_docs, "question": query})
        # print(answer)
        index = self.create_index()
        memory = self.create_memory(user_id)
        embeddings = OpenAIEmbeddings(model=self.MODEL, openai_api_key=self.OPENAI_API_KEY)
        vectorStore = Pinecone.from_existing_index(index_name=self.PINECONE_INDEX_NAME, embedding=embeddings)
        chain = self.create_chain(vectorStore, memory)
        response = self.process_chat(chain, user_input)
        return response