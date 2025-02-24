# import spacy
import re
import pandas as pd
from rapidfuzz import process, fuzz

# # Load spaCy model
# nlp = spacy.load("en_core_web_sm")

# Load car data for predefined options
car_data = pd.read_csv('Data/dashboard_data.csv')

# Predefined lists for matching, converting all to strings
possible_makes = [str(make) for make in car_data['Make'].unique().tolist()]
possible_models = [str(model) for model in car_data['Model'].unique().tolist()]
possible_fuel_types = ["Petrol", "Diesel", "Electric", "Hybrid"]
possible_locations = [str(location) for location in car_data['Location'].unique().tolist()]

# Helper function to match keywords directly
def direct_match(input_text, possible_values):
    if isinstance(input_text, str):
        for value in possible_values:
            if isinstance(value, str) and value.lower() in input_text.lower():
                return value
    return None

# Refined extraction for make, with fallback to fuzzy matching
def extract_make(input_text):
    make = direct_match(input_text, possible_makes)
    if make is None:
        result = process.extractOne(input_text, possible_makes, scorer=fuzz.token_set_ratio, score_cutoff=75)
        make = result[0] if result else None
    return make

# Enhanced model extraction with stricter exact matching
def extract_model(input_text):
    # Handle cases with both "Series" and standalone models
    series_match = re.search(r"(\d\s?Series|VXi|ZXi|LXi)", input_text, re.IGNORECASE)
    if series_match:
        return series_match.group(0).strip()
    
    # Default to direct and fuzzy matching if no specific patterns found
    model = direct_match(input_text, possible_models)
    if model is None:
        result = process.extractOne(input_text, possible_models, scorer=fuzz.token_set_ratio, score_cutoff=75)
        model = result[0] if result else None
    return model

# Direct keyword search for fuel types
def extract_fuel_type(input_text):
    return direct_match(input_text, possible_fuel_types)

# Improved location extraction with pattern-based matching
def extract_location(input_text):
    # Attempt to match locations directly
    location = direct_match(input_text, possible_locations)
    if location:
        return location

    # Fallback with relaxed fuzzy matching for unique cases
    result = process.extractOne(input_text, possible_locations, scorer=fuzz.token_set_ratio, score_cutoff=50)
    return result[0] if result else None

def extract_year(input_text):
    match = re.search(r"\b(19|20)\d{2}\b", input_text)
    return int(match.group()) if match else None

def extract_odometer(input_text):
    match = re.search(r"\b\d+\s*(?:km|kilometers?)\b", input_text, re.IGNORECASE)
    return int(re.sub(r"[^\d]", "", match.group())) if match else None

def extract_variant(input_text, make, model):
    cleaned_text = input_text
    if make:
        cleaned_text = re.sub(make, "", cleaned_text, flags=re.IGNORECASE)
    if model:
        cleaned_text = re.sub(model, "", cleaned_text, flags=re.IGNORECASE)
    return cleaned_text.strip()

def extract_trim_level(variant):
    if variant:
        if "Sport" in variant:
            return "Sport"
        elif "Luxury Line" in variant:
            return "Luxury"
        elif "LWB" in variant:
            return "LWB"
    return "Base"

def extract_power_indicator(variant):
    if variant:
        if "4MATIC" in variant:
            return "4MATIC"
        elif "GT" in variant:
            return "GT"
    return "Standard"

def extract_features(company, model, variant, year, odometer_reading, fuel_type, location):
    # Extract features in order
    make = extract_make(company)
    model = extract_model(model)
    fuel_type = extract_fuel_type(fuel_type)
    location = extract_location(location)
    year = extract_year(year)
    odometer = odometer_reading
    variant = extract_variant(variant, make, model)

    # Print extracted values for debugging
    print(f"Extracted Make: {make}")
    print(f"Extracted Model: {model}")
    print(f"Extracted Fuel Type: {fuel_type}")
    print(f"Extracted Location: {location}")
    print(f"Extracted Year: {year}")
    print(f"Extracted Odometer: {odometer}")
    print(f"Extracted Variant: {variant}")
    
    # Combine extracted features with keys matching expected DataFrame columns
    features = {
        "Make": make,
        "Model": model,
        "Fuel Type": fuel_type,
        "Location": location,
        "year": year,
        "Kilometers Driven": odometer,
        "Trim Level": extract_trim_level(variant),
        "Power Indicator": extract_power_indicator(variant)
    }

    print("Final Extracted Features:", features)
    return features