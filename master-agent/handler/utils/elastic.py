from elasticsearch import Elasticsearch
from config.index import ELK_CLOUD_ID,ELK_USERNAME,ELK_PASSWORD


# Create an Elasticsearch client
client = Elasticsearch(
    cloud_id=ELK_CLOUD_ID,
    basic_auth=(ELK_USERNAME, ELK_PASSWORD)
)

