# Homework Helper

## Overview
The Homework Helper is a line bot homework assistant. We allow the user to upload their PDF files, and ask questions about the given PDF.
The server is connect to gpt-3.5-turbo, and will answer users with the answer the model generated.
Also, we use RAG architecture to design this LLM application, 

## Installation

### Python Environment

Python version: Python 3.12.3

```
pip install -r requirements.txt
```

### Environment Variables

Setup the following environment variables:

- PINECONE_API_KEY
- PINECONE_ENVIRONMENT
- OPENAI_API_KEY
- LINE_BOT_API_KEY
- LINE_BOT_HANDLER
- REDIS_HOST
- REDIS_PASSWORD
- REDIS_PORT
- REDIS_URL
- CLIENT_ID
- PROJECT_ID
- AUTH_URI
- TOKEN_URI
- AUTH_PROVIDER_URI
- CLIENT_SECRET
- REDIRECT_URIS

## Usage

Set up a HTTPS server environment and run
```
python3 app.py
```
