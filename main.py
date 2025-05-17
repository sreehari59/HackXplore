from google import genai
# from google.genai import GenerateContentConfig
from google.genai.types import (
    FunctionDeclaration,
    GenerateContentConfig)
from utils import req_response_schema, capacitor_schema, inductor_schema, resistor_schema
from dotenv import load_dotenv
import os
import json

load_dotenv() 

PROJECT_ID = "compact-record-199318"
LOCATION = "us-central1"
model_id = "gemini-2.0-flash-exp" 
zoom_val = 3.0
batch_size = 10
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
response_data = []

input_data = [
    "RES., 5.9kΩ, 1%, 1/10W, 0603, AEC-Q200 R21 ERJ-3EKF5901V PANASONIC",
    "HV Capacitor /10nF/3kV/2220 10nF_3kV_2220 Vishay HV2220Y103KXMATHV HV2220Y103KXHATHV 8 712, IND.",
    "2uH, PWR, 20%, Ø 0.840mΩ, 19 x19.3mm, AEC-Q200"
]

prompt = f""" You are an expert electronic engineer who know about the electonic components and their datasheet.
Firstly understand the component and based on it fill the values. 
For the given string {input_data} map it properly.
Note: 
1. Each index of the list is a electronic component that index 0 is one electonic component, index 2 is another electonic component
2. There are {len(input_data)} components in the list
"""

list_response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=prompt,
    config=GenerateContentConfig(
          response_mime_type="application/json",
          response_schema=capacitor_schema,
      )
)
response_data = json.loads(list_response.text)
print(list_response.text)
print("======")


for index, i in enumerate(response_data):
    # prompt = f""" You are an expert electronic engineer who know about the electonic components and their datasheet.
    #     Firstly understand the component and based on it fill the values. 
    #     For the given string {i} map it properly.
    #     """

    # response = client.models.generate_content(
    #     model="gemini-2.0-flash",
    #     contents=prompt,
    #     config=GenerateContentConfig(
    #         response_mime_type="application/json",
    #         response_schema=capacitor_schema,
    #     )
    # )
    # response_data = json.loads(response.text)
    # print(response_data)
    # print(i)
    if i["Product_Group"] == "capacitor":

        print(i["Product_Group"])
        capacitor_prompt = f""" You are an expert electronic engineer who know about the electonic components and their datasheet.
        Given is information about Capactior understand the given string {input_data[index]} and based on the understanding map the values.
        """

        capacitor_response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=capacitor_prompt,
        config=GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=capacitor_schema,
            )
        )
        print(capacitor_response.text)

    elif i["Product_Group"] == "inductor":
        print(i["Product_Group"])
        inductor_prompt = f""" You are an expert electronic engineer who know about the electonic components and their datasheet.
        Given is information about Inductor understand the given string {input_data[index]} and based on the understanding map the values.
        """

        inductor_response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=inductor_prompt,
        config=GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=inductor_schema,
            )
        )

        print(inductor_response.text)
    
    else:
        print(i["Product_Group"])
        resistor_prompt = f""" You are an expert electronic engineer who know about the electonic components and their datasheet.
        Given is information about Resistor understand the given string {input_data[index]} and based on the understanding map the values.
        """

        resistor_response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=resistor_prompt,
        config=GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=resistor_schema,
            )
        )

        print(resistor_response.text)

