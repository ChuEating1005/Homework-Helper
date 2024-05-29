import os
import re
import openai
#from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Pinecone
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableParallel, RunnablePassthrough, RunnableLambda
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pinecone import Pinecone as PineconeClient
from langchain.chains.history_aware_retriever import create_history_aware_retriever
from langchain_core.messages import HumanMessage, AIMessage
from langchain.schema import Document
import requests

# Load environment variables
#load_dotenv()

class LineBotHandler:
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

    # Define a function to create embeddings
    def create_embeddings(self,texts):
        openai.api_key = self.OPENAI_API_KEY
        embeddings_list = []
        for text in texts:
            res = openai.Embedding.create(input=[text.page_content], engine=self.MODEL)
            embeddings_list.append(res['data'][0]['embedding'])
        return embeddings_list

    def find_match(self,input_text, num, index):
        input_em = self.create_embeddings([Document(page_content=input_text, metadata={})])
        result = index.query(vector=input_em[0], top_k=num, include_metadata=True)
        matches = result['matches']
        matched_texts = "\n".join([match['metadata']['text'] for match in matches])
        return matched_texts

    def create_chain(self,vectorStore):
        model = ChatOpenAI(
            model="gpt-3.5-turbo-1106",
            temperature=0.4
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", "Answer the user's questions based on the context: {context}"),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}")
        ])

        # Define the RAG chain
        chain = create_stuff_documents_chain(
            llm=model,
            prompt=prompt
        )

        retriever = vectorStore.as_retriever(search_kwargs={"k": 3})

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
        pinecone = PineconeClient(api_key=self.PINECONE_API_KEY, environment=self.PINECONE_ENVIRONMENT)
        index = pinecone.Index(self.PINECONE_INDEX_NAME)
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

    def process_chat(self,chain, question, chat_history):
        print(self.chat_history)
        response = chain.invoke({
            "chat_history": chat_history,
            "input": question,
        })
        return response["answer"]
    def handle_conversation(self,user_input):
        # query = "Assignment 3 有什麼問題？"
        # context = find_match(query)
        # # print("Context:", context)
        # context_docs = [Document(page_content=text, metadata={}) for text in context.split("\n")]
        # answer = chain.invoke({"context": context_docs, "question": query})
        # print(answer)
        embeddings = OpenAIEmbeddings(model=self.MODEL, openai_api_key=self.OPENAI_API_KEY)
        vectorStore = Pinecone.from_existing_index(index_name=self.PINECONE_INDEX_NAME, embedding=embeddings)
        chain = self.create_chain(vectorStore)
        response = self.process_chat(chain, user_input, self.chat_history)
        self.chat_history.append(HumanMessage(content=user_input))
        self.chat_history.append(AIMessage(content=response))
        return response