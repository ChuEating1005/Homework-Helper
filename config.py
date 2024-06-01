import os
import dotenv

dotenv.load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LINEBOT_API_KEY = os.getenv('LINE_BOT_API_KEY')
LINEBOT_HANDLER = os.getenv('LINE_BOT_HANDLER')
MODEL_NAME = "text-embedding-3-small"
REDIS_HOST = os.getenv('REDIS_HOST')
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')
REDIS_PORT = os.getenv('REDIS_PORT')
REDIS_URL = os.getenv('REDIS_URL')