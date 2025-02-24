import logging
from elasticsearch import Elasticsearch
from langchain_elasticsearch import ElasticsearchStore, SparseVectorStrategy
from config.Constants import ELSER_MODEL, ELASTIC_CLOUD_ID, ELASTIC_API_KEY,ES_VECTOR_INDEX


elasticsearch_client = Elasticsearch(
    cloud_id=ELASTIC_CLOUD_ID,
    api_key=ELASTIC_API_KEY,
    request_timeout=200
)

store = ElasticsearchStore(
    es_connection=elasticsearch_client,
    index_name=ES_VECTOR_INDEX,
    strategy=SparseVectorStrategy(model_id=ELSER_MODEL),
)


