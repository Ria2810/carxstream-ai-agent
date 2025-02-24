import pickle
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import math
import os

label_encoders = {}
for column in ['Fuel Type', 'Location', 'Make', 'Model', 'Trim Level', 'Power Indicator']:
    with open(f"models_new/{column}_label_encoder.pkl", "rb") as f:
        label_encoders[column] = pickle.load(f)

with open("models_new/scaler.pkl", "rb") as f:
    scaler = pickle.load(f)

model = pickle.load(open("models_new/CatBoost_model.pkl", "rb"))  

def preprocess_input(input_data):
    df = pd.DataFrame([input_data])
    df['Car Age'] = 2024 - df['year']
    df = df.drop(columns=['year'])

    # Apply label encoding
    for column, encoder in label_encoders.items():
        df[column] = encoder.transform(df[column].astype(str))

    # Scale continuous features
    continuous_features = ['Kilometers Driven', 'Car Age']
    df[continuous_features] = scaler.transform(df[continuous_features])
    feature_order = ['Make', 'Model','Kilometers Driven', 'Fuel Type', 'Location', 'Trim Level', 'Power Indicator' , 'Car Age']
    df = df[feature_order]

    return df


def make_prediction(features):
    processed_data = preprocess_input(features) 
    predicted_price_log = model.predict(processed_data) 
    predicted_price = np.expm1(predicted_price_log) 
    rounded_price = math.ceil(predicted_price[0])
    return rounded_price
