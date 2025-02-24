from langchain_core.tools import tool, StructuredTool
from pydantic import BaseModel, Field
from elasticsearch import Elasticsearch
from config.index import ELK_CLOUD_ID, ELASTIC_API_KEY, ELK_CAR_ENGINE

elastic_search_client = Elasticsearch(
    cloud_id=ELK_CLOUD_ID,
    api_key=ELASTIC_API_KEY
)
          
class vehicle_existence_check_input(BaseModel):
    """It will check if the vehicle number exist in our database using vehicle number."""
    vehicle_number : str = Field(..., description="Vehicle number") 
    
def vehicle_existence_check(vehicle_number : str) -> str:
    """
    Vehice Existence Check Tool
    
    It will check if the vehicle number exist in our database using vehicle plate number
    
    """
    
    query = {
        "bool": {
            "must": [
                { "match": { "vin": vehicle_number}},
                {"match": {"sold": False}}
            ]
        }
    }
    
    try:
        response = elastic_search_client.search(index=ELK_CAR_ENGINE, query=query)  
        print("response:", response)
        if response["hits"]["total"]["value"] > 0:
            return f"Vehicle number {vehicle_number} exists in the database."
        else:
            return f"Vehicle number {vehicle_number} does not exist in the database."

    except Exception as e:
        return f"An error occurred while searching in database: {str(e)}"

vehicle_existence = StructuredTool.from_function(
        func=vehicle_existence_check,
        name="vehicle_existence_check",
        description="It will check if the vehicle number exist in our database using vehicle number",
        args_schema=vehicle_existence_check_input,
    )