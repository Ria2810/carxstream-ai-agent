import os

OPENAI_API_KEY=os.getenv("OPEN_API_KEY")
ES_INDEX=os.getenv("ELK_ENGINE")
ES_VECTOR_INDEX=os.getenv("ELK_ENGINE_VECTOR")

ES_INDEX_CHAT_HISTORY =os.getenv("ELK_AGENT_ENGINE")

ELASTIC_CLOUD_ID = os.getenv("ELK_CLOUD_ID")
ELASTIC_API_KEY=os.getenv("ELASTIC_API_KEY")

ELSER_MODEL=os.getenv("ELSER_MODEL")
CURRENT_ENV = os.getenv("CURRENT_ENV")
PROD_URL = os.getenv("PROD_URL")
DEV_URL = os.getenv("DEV_URL")
AI_MODEL = os.getenv("AI_MODEL")