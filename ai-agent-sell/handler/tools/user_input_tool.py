from langchain_core.tools import tool, StructuredTool
from pydantic import BaseModel, Field

          
class user_input(BaseModel):
    """Car Price Comparison."""
    company: str = Field(..., description="Company Name")
    model: str = Field(..., description="Car Model")
    variant: str = Field(..., description="Car Variant")
    price : int = Field(..., description="Car Price")
    year : int = Field(..., description="Buying year")
    odometer_reading : int = Field(..., description="Kilometer Driven")
    vehicle_number : str = Field(..., description="Vehicle number") 
    color : str = Field(..., description="Car Color")
    fuel_type : str = Field(..., description="Fuel Type")
    location : str = Field(..., description="Location")

def user_input_tool(company: str, model: str, variant: str, price: int, year : int, odometer_reading : int, vehicle_number : str, color : str, fuel_type : str, location : str) -> bool:
    """
    User Input Tool
    
    It will take this input: company, model, price and variant from the model and Check if the price of the car model is \
    more than the actual car price.
    
    """
    print("Invoked user input tool")
    return {
        'company': company,
        'model': model,
        'variant': variant,
        'price': price,
        'year': year,
        'odometer_reading': odometer_reading,
        'vehicle_number': vehicle_number,
        'color': color,
        'fuel_type': fuel_type,
        'location': location
    }
    

input = StructuredTool.from_function(
        func=user_input_tool,
        name="user_input_tool",
        description="It will take all the car details from user and store it the database",
        args_schema=user_input,
    )
# print(parse_price('Rs. 6.99 Lakh'))