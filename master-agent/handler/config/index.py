import os

OPENAI_API_KEY=os.getenv("OPEN_API_KEY")
ELK_CLOUD_ID = os.getenv("ELK_CLOUD_ID")
ELASTIC_API_KEY=os.getenv("ELASTIC_API_KEY")
ELK_USERNAME=os.getenv("ELK_USERNAME")
ELK_PASSWORD=os.getenv("ELK_PASSWORD")
ELK_CAR_ENGINE=os.getenv("ELK_CAR_ENGINE")
ELK_AGENT_ENGINE=os.getenv("ELK_AGENT_ENGINE")
ELK_USER_ENGINE=os.getenv("ELK_USER_ENGINE")
TEST_ENV=os.getenv("TEST_ENV")
USER_TABLE="users"
SUBSCRIPTIONS_TABLE="subscriptions"
CARS_TABLE="cars"
CURRENT_ENV= os.getenv("CURRENT_ENV")
PROD_URL = os.getenv("PROD_URL")
DEV_URL = os.getenv("DEV_URL")
AI_MODEL = os.getenv("AI_MODEL")
AI_IMAGE_MODEL = os.getenv("AI_IMAGE_MODEL")
S3_DEV_URL = os.getenv("S3_DEV_URL")
S3_PROD_URL = os.getenv("S3_PROD_URL")
STEP_FUNC_ARN_DEV=os.getenv("STEP_FUNC_ARN_DEV")
STEP_FUNC_ARN_PROD=os.getenv("STEP_FUNC_ARN_PROD")
S3_BUCKET_NAME_DEV=os.getenv("S3_BUCKET_NAME_DEV")
S3_BUCKET_NAME_PROD=os.getenv("S3_BUCKET_NAME_PROD")



S3_BUCKET_NAME =S3_BUCKET_NAME_DEV if CURRENT_ENV == "dev" else S3_BUCKET_NAME_PROD
S3_URL = S3_DEV_URL if CURRENT_ENV == "dev" else S3_PROD_URL
CAR_FEATURED_IMAGE_URL ="assets/subscriptions/car/subscription_featured.jpg"
CAR_POPULAR_IMAGE_URL ="assets/subscriptions/car/subscription_popular.jpg"
CAR_CERTIFIED_IMAGE_URL ="assets/subscriptions/car/subscription_certified.jpg"