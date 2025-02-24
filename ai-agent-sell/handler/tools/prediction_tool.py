import pandas as pd
from langchain_core.tools import tool, StructuredTool
from pydantic import BaseModel, Field
import re
from Helper.feature_extraction import extract_features
from Helper.model_utils import make_prediction

          
class prediction_input(BaseModel):
    """Car Price Comparison."""
    company: str = Field(..., description="Company Name")
    model: str = Field(..., description="Car Model")
    variant: str = Field(..., description="Car Variant")
    year : str = Field(..., description="Buying year")
    odometer_reading : int = Field(..., description="Kilometer Driven")
    fuel_type : str = Field(..., description="Fuel Type")
    location : str = Field(..., description="Location")
    
def prediction_tool(company: str, model: str, variant: str, year : str, odometer_reading : int, fuel_type : str, location : str) -> str:
    """
    Prediction Tool
    
    It will take this input: company, model, variant, year, odometer_reading, fuel_type, location and predict the best selling price of the car model \
    
    """
    features = extract_features(company, model, variant, year, odometer_reading, fuel_type, location)
    if None in features.values():
        return "Could not extract all features"  # Could not extract all features
    if features:
        predicted_price = make_prediction(features)
        return f"The estimated price of the car based on the details provided is {predicted_price} Rupees."
    else:
        return "Could not extract all required details. Please provide more information."
    
    

prediction = StructuredTool.from_function(
        func=prediction_tool,
        name="prediction_tool",
        description="It will take the required data for bettter price prediction",
        args_schema=prediction_input,
    )
# print(parse_price('Rs. 6.99 Lakh'))