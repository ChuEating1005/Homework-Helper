import os
import re
import openai
from dotenv import load_dotenv
from langchain_community.chat_models import ChatOpenAI
from langchain_community.embeddings import OpenAIEmbeddings
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
load_dotenv()

# Get environment variables
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = "text-embedding-3-small"
openai.api_key = OPENAI_API_KEY

def preprocess_text(text):
    # Replace consecutive spaces, newlines and tabs
    text = re.sub(r'\s+', ' ', text)
    return text

# Define a function to create embeddings
def create_embeddings(texts):
    embeddings_list = []
    for text in texts:
        res = openai.Embedding.create(input=[text.page_content], engine=MODEL)
        embeddings_list.append(res['data'][0]['embedding'])
    return embeddings_list

def find_match(input_text, num, index):
    input_em = create_embeddings([Document(page_content=input_text, metadata={})])
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

def upload_pdf(embeddings, pdf_path, chunk_size=1000, chunk_overlap=100):
    pinecone = PineconeClient(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT)
    index = pinecone.Index(PINECONE_INDEX_NAME)
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

def process_chat(chain, question, chat_history):
    response = chain.invoke({
        "chat_history": chat_history,
        "input": question,
    })
    return response["answer"]

# Example to process and upload PDF, and then query
def main():
    # query = "Assignment 3 有什麼問題？"
    # context = find_match(query)
    # # print("Context:", context)
    # context_docs = [Document(page_content=text, metadata={}) for text in context.split("\n")]
    # answer = chain.invoke({"context": context_docs, "question": query})
    # print(answer)
    embeddings = OpenAIEmbeddings(model=MODEL, openai_api_key=OPENAI_API_KEY)
    vectorStore = Pinecone.from_existing_index(index_name=PINECONE_INDEX_NAME, embedding=embeddings)
    chain = create_chain(vectorStore)
    chat_history = []

    # while True:
    #     user_input = input("You: ")

    #     if user_input.lower() == 'exit':
    #         break

    #     if user_input.lower() == 'upload':
    #         print("Which PDF file do you want to upload?")
    #         for i, pdf_path in enumerate(os.listdir("data")):
    #             print(f"{i+1}. {pdf_path}")
    #         choice = input("Enter the number of the PDF file: ")
    #         pdf_path = os.path.join("data/", os.listdir("data")[int(choice) - 1])
    #         print(pdf_path)
    #         upload_pdf(embeddings, pdf_path)
    #     else:
    #         response = process_chat(chain, user_input, chat_history)
    #         chat_history.append(HumanMessage(content=user_input))
    #         chat_history.append(AIMessage(content=response))
    #         print("Assistant:", response)
    print(type(vectorStore))

if __name__ == "__main__":
    main()