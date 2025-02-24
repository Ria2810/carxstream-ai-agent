import pandas as pd
from langchain_core.tools import tool, StructuredTool
from rapidfuzz import process, fuzz
from pydantic import BaseModel, Field
import re

# CSV file paths
json_path = "Data/IndianCarMasterDataOutput.json"  
master = pd.read_json(json_path)

# Parse & Convert the price input to a numeric format
def parse_price(price_input: str) -> int:
    """
    Parses a price input string into a numeric format.
    """
    price = float(price_input.replace('Rs. ', '').replace(' Lakh', '').replace(' Crore', '').strip())
    if 'Lakh' in price_input:
        price *= 100000
    elif 'Crore' in price_input:
        price *= 10000000
    return int(price)

def fuzzy_match(df, company, model, variant, threshold=40):
    """
    Performs fuzzy matching to find the closest match in a DataFrame column.
    """
    choices = list(set(df['Make'].dropna().str.lower().tolist()))
    match, score, _ = process.extractOne(company, choices, scorer=fuzz.token_sort_ratio)
    print(match, score)
    if score < threshold:
        return pd.DataFrame()
    df = df[df['Make'].str.lower() == match]
    
    choices = list(set(df['Model'].dropna().str.lower().tolist()))
    match, score, _= process.extractOne(model, choices, scorer=fuzz.token_sort_ratio)
    print(match, score)
    if score < threshold:
        return pd.DataFrame()
    df = df[df['Model'].str.lower() == match]
    
    choices = list(set(df['Variant'].dropna().str.lower().tolist()))
    match, score, _ = process.extractOne(variant, choices, scorer=fuzz.token_sort_ratio)
    print(match, score)
    if score < threshold:
        return pd.DataFrame()
    return df[df['Variant'].str.lower() == match]
            
class comparison_input(BaseModel):
    """Car Price Comparison."""
    company: str = Field(..., description="Company Name")
    model: str = Field(..., description="Car Model")
    variant: str = Field(..., description="Car Variant")
    price : int = Field(..., description="Car Price")

def comparison_tool(company: str, model: str, variant: str, price: int) -> any:
    """
    Comparison Tool
    
    It will take this input: company, model, price and variant from the model and Check if the price of the car model is \
    more than the actual car price.
    
    """
    
    # Parse and validate input data
    company = company.strip().lower()
    model = model.strip().lower()
    variant = variant.strip().lower()
    # price = price if type(price) is 'int' else parse_price(price)
    car_match = fuzzy_match(master, company, model, variant)
    if car_match.empty:
        return "no data available"
    print("Test:", car_match.iloc[0]['Price'])
    actual_price = parse_price(car_match.iloc[0]['Price'])
    if price > actual_price:
        return True
    else:
        return False

comparison = StructuredTool.from_function(
        func=comparison_tool,
        name="comparison_tool",
        description="It will take this input: company, model, price and variant from the model and Check if the price of the car model is \
        more than the actual car price",
        args_schema=comparison_input,
    )
# print(parse_price('Rs. 6.99 Lakh'))