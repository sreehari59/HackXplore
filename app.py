import os
import json
import requests
import re
from openai import OpenAI
from dotenv import load_dotenv
import sys
from flask import Flask, jsonify, request
from flask_cors import CORS
from google import genai
from google.genai.types import (
    FunctionDeclaration,
    GenerateContentConfig)
import json
from utils import (req_response_schema, extract_json, read_file_values, is_row_empty,
                    read_capacitance_dump, read_resistor_dump,core_capacitance_constraints_match,
                    optional_capacitance_constraints_match)
from openai import OpenAI
import pandas as pd
from io import BytesIO, StringIO 
load_dotenv()

# Set API keys from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AZURE_API_KEY = os.getenv("AZURE_API_KEY")
AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT")
AZURE_API_VERSION = os.getenv("AZURE_API_VERSION") or "2023-05-15"
SERPAPI_KEY = os.getenv("SERP_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


app = Flask(__name__)
CORS(app)

@app.route('/api/upload-bom', methods=['POST'])
def upload_bom():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400

    files = request.files.getlist('file')

    if not files or all(file.filename == '' for file in files):
        return jsonify({'error': 'No selected file(s)'}), 400

    processed_data = []
    final_output_data = []

    for file in files:
        if file:
            filename = file.filename
            try:
                if filename.endswith(('.xlsx', '.xls')):
                    # Read directly from the FileStorage object using BytesIO
                    excel_data = BytesIO(file.read())
                    df = pd.read_excel(excel_data)
                    print("Dataframe: ",df)
                elif filename.endswith('.csv'):
                    csv_data = file.stream.read().decode('utf-8') # Or other encoding
                    df = pd.read_csv(StringIO(csv_data)) # Use StringIO for string-based CSV
                else:
                    return jsonify({'error': f'Unsupported file type: {filename}'}), 400
                
                input_data = read_file_values(df)

                prompt = f""" You are an expert electronic engineer who know about the electonic components and their datasheet.
                    Firstly understand the component and based on it fill the values. 
                    For the given string {input_data} map it properly.
                    Note: 
                    1. Each index of the list is a electronic component that index 0 is one electonic component, index 2 is another electonic component
                    2. There are {len(input_data)} components in the list
                    """
                client = genai.Client(api_key=GEMINI_API_KEY)
                list_response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt,
                    config=GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=req_response_schema,
                    )
                )
                response_data = json.loads(list_response.text)  
                print(response_data)
                open_ai_client = OpenAI(api_key=OPENAI_API_KEY)
                for index, i in enumerate(response_data):
                    print("The values is:",i["Product_Group"])
                    print("==========")

                    if "Manufacturer_Part_Number" not in i.keys():
                        print("Manufacturer part number is not present")
                        continue
                    else:
                        part_number = i["Manufacturer_Part_Number"]
                        open_ai_prompt = f"""
                            Given the part number {part_number}, tell me:
                            - The manufacturer,
                            - The full product description,
                            - Component type (resistor, capacitor, inductor, etc.),
                            - Key electrical specs:
                            1. For Resistor: 'Resistance', 'Power_Rating', 'Case_Code', 'Length', 'Width', 'Height', 'Tolerance','Temperature_Coefficient', 'Minimum_Operating_Temperature', 'Maximum_Operating_Temperature'
                            2. For Capacitor: 'Capacitance', 'Rated_Voltage', 'Case_Code', 'Length', 'Width_or_Diameter', 'Tolerance','Dielectric_Material_or_Temperature_Coefficient','Minimum_Operating_Temperature', 'Maximum_Operating_Temperature',
                            3. For Inductor: 'Inductance', 'Rated_Current', 'Case_Code', 'Length', 'Width', 'Height', 'Tolerance','Shielding', 'DC_Resistance', 'Minimum_Operating_Temperature', 'Maximum_Operating_Temperature',
                            Important Note: Return only a json file with the manufacturer, manufacturer_part_number, and the key electrical specs
                        """
                        completion = open_ai_client.chat.completions.create(
                            model="gpt-4o-search-preview",
                            web_search_options={},
                            messages=[
                                {
                                    "role": "user",
                                    "content": open_ai_prompt,
                                }
                            ],
                        )

                        print(completion.choices[0].message.content)
                        openai_response_data = extract_json(completion.choices[0].message.content)
                        print("=======")
                        print(openai_response_data)
                        final_output_data.append(openai_response_data)

            except Exception as e:
                return jsonify({'error': f'Error reading file {filename}: {str(e)}'}), 500

    return jsonify(final_output_data), 200

@app.route('/api/recommend_candidates', methods=['POST'])
def recommend_candidates():
    data = request.get_json()
    print("Data in recommend:",data)
    recommends = []
    for i in data:
        temp_val = i
        component_type = i["component_type"]
        part_number = i["manufacturer_part_number"]
        specs = i["key_electrical_specs"]
        if "Capacitor" in component_type:
            criterion1 = "Capacitance equal to (=) " + i["key_electrical_specs"]["Capacitance"]
            criterion2 = "Rated Voltage Greater than or Equal to (>=) " + i["key_electrical_specs"]["Rated_Voltage"]
        elif "Inductor" in component_type:
            criterion1 = "Inductance equal to (=) " + i["key_electrical_specs"]["Inductance"]
            criterion2 = "Rated Currant Greater than or Equal to (>=) " + i["key_electrical_specs"]["Rated_Current"]
        else:
            criterion1 = "Capacitance equal to (=) " + i["key_electrical_specs"]["Resistance"]
            criterion2 = "Power Rating Greater than or Equal to (>=) " + i["key_electrical_specs"]["Power_Rating"]
            
        conditions = [criterion1, criterion2]

        recosys_open_ai_prompt = f"""
            Given the electornic component {component_type} with manufacturer_part_number {part_number} and its key electrical specs {specs}.
            - Find an alternate Wurth Electronic component for based on the following {conditions}
            - Few shot examples:
            1. If a match is found then return a list:
            [
            'wuerth_manufacturer_part_number': '74408943101',
            'reason_why_it_is_a_match': 'It is match since the capacitance was a perfect match'
            ]
            2. If there is no match then return:
            [
                'wuerth_manufacturer_part_number: '',
                'reason_why_it_is_a_match': ''
            ]
            - Return JSON with values for wuerth_manufacturer_part_number, reason_why_it_is_a_match 
                Important Note: Return only a json file with the wuerth_manufacturer_part_number or the closest wuerth_manufacturer_part_number
                , and the reason_why_it_is_a_match
            """
        recosys_open_ai_client = OpenAI(api_key=OPENAI_API_KEY)
        recosys_completion = recosys_open_ai_client.chat.completions.create(
            model="gpt-4o-search-preview",
            web_search_options={},
            messages=[  
                {
                    "role": "user",
                    "content": recosys_open_ai_prompt,
                }
            ],
        )
        recosys_reponse_json = extract_json(recosys_completion.choices[0].message.content)
        if recosys_reponse_json == None:
            print("The json response from websearch:", recosys_reponse_json)
            temp_val.update({"wuerth_manufacturer_part_number" : ''})
            temp_val.update({"reason_why_it_is_a_match" : ''})
        else:
            print("The json response from websearch:", recosys_reponse_json)
            temp_val.update(recosys_reponse_json)
        print(temp_val)
        print("=================")
        # print(recosys_completion.choices[0].message.content)

        recommends.append(temp_val)

    print(recommends)
    return jsonify(recommends)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port="8080")