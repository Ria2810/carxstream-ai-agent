
from langchain_elasticsearch import ElasticsearchStore
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
from langchain_community.document_loaders.csv_loader import CSVLoader
from elasticsearch import Elasticsearch
from langchain_elasticsearch import ElasticsearchRetriever

dense_vector_field = "vector"
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
def vector_query(search_query: str) -> dict:
    vector = embeddings.embed_query(search_query)  # same embeddings as for indexing
    return {
        "knn": {
            "field": dense_vector_field,
            "query_vector": vector,
            "k": 5,
            "num_candidates": 10,
        }
    }

cars = [
    {
        "car_id": "9f41653d-c2a0-40cf-a82d-701509fa40791710746288159",
        "vin": "KA39CK3830",
        "year": 2007,
        "make": "DC",
        "model": "Avanti",
        "trim": "Standard",
        "mileage": None,
        "body_style": "Coupe",
        "doors": 0,
        "drivetrain": "",
        "fuel_type": "Petrol",
        "exterior_color": "Red",
        "interior_color": "",
        "price": 12000,
        "engine": "1998 cc",
        "odometer": 15113,
        "image": "",
        "location": {"lat": 12.9634, "lon": 77.5855},
        "status": "CAR_IMAGES",
        "transmission": "Manual"
    },
    {
        "car_id": "f0c078ae-722c-446c-8ee2-281603e552f01710847288587",
        "vin": "KA73DK3839",
        "year": 2018,
        "make": "Bentley",
        "model": "Mulsanne",
        "trim": "V8",
        "mileage": None,
        "body_style": "Compact Sedan",
        "doors": 0,
        "drivetrain": "",
        "fuel_type": "Petrol",
        "exterior_color": "Red",
        "interior_color": "",
        "price": 35000,
        "engine": "6752 cc",
        "odometer": 7543,
        "image": "",
        "location": {"lat": 12.9102545, "lon": 77.5892203},
        "status": "CAR_REVIEW_SUBMIT",
        "transmission": "Automatic"
    }
]

def test_ingest():
    vector_store = ElasticsearchStore.from_documents(
        documents=cars,
        es_cloud_id="34c0246426da40fb94b406218f241d14:dXMtZWFzdC0xLmF3cy5mb3VuZC5pbzo0NDMkMzllZjViYzVjZGQyNDk0YTkxMjZlYjI1MDY2MWRlYzUkYWYxNmNhMmU3NzJlNDhhOGFkYzVlZDlkNjNkNmVjYWI=",
        index_name="selling_data_cars",
        embedding=embeddings,
        es_api_key="OW4zQTk1SUJhUnNxM2Z3aDNHdmY6a0VLT29JUlRSOWVUQURta1BKNVZNZw==",
        bulk_kwargs={
                "request_timeout": 120,
            },
    )
# mylist = []
# for doc in res:
#     print(doc.page_content)
# print(res)
test_ingest()
