import json
import re
import pandas as pd
import os

def is_row_empty(row):
    # Helper to check if a row is completely empty (NaN, 'nan', or blank strings)
    for val in row:
        if pd.isna(val):
            continue
        if isinstance(val, str) and val.strip().lower() == 'nan':
            continue
        if isinstance(val, str) and val.strip() == '':
            continue
        return False
    return True

def read_file_values(df):
    # ext = os.path.splitext(file_path)[1].lower()

    # Read raw data without header to detect first real header row
    # if ext in ['.xlsx', '.xls']:
    #     df = pd.read_excel(file_path, header=None)
    # elif ext == '.csv':
    #     df = pd.read_csv(file_path, header=None)
    # else:
    #     raise ValueError(f"Unsupported file extension: {ext}")

    # Find the first row that is not empty (to set as header)
    # first_non_empty_idx = None
    # for i, row in df.iterrows():
    #     if not is_row_empty(row):
    #         first_non_empty_idx = i + 1
    #         break
    # if first_non_empty_idx is None:
    #     raise ValueError("No non-empty rows found in file")

    # # Re-read file with header set properly
    # if ext in ['.xlsx', '.xls']:
    #     df = pd.read_excel(file_path, header=first_non_empty_idx)
    # else:
    #     df = pd.read_csv(file_path, header=first_non_empty_idx)

    # Convert all values to strings
    df = df.astype(str)

    # Filter out any rows that are fully empty or all 'nan' anywhere in the dataframe
    def row_is_not_empty_string(row):
        for val in row:
            val_clean = val.strip().lower()
            if val_clean != '' and val_clean != 'nan':
                return True
        return False

    filtered_rows = df[df.apply(row_is_not_empty_string, axis=1)]

    # Join each row into a single string separated by space
    rows_as_strings = filtered_rows.apply(lambda row: ' '.join(row), axis=1).tolist()

    return rows_as_strings

def is_same_or_larger_dimensions(candidate_row, reference_row):
  """
    This code is exectued when there is no exact match of Length, Width & Height.
    Goal : Want to find capacitors in df_capacitors(Wurth) that are equal or larger in all three dimensions.

    reference_row : It would be the user input value 
    candidate_row : It would be the row from the Wurth dataframe

    Returns false :
      1. When the input requirement has Value , but the Wurth product is missing 
      2. If the size of any ["Length (mm)", "Width (mm)", "Height (mm)"] is smaller than Wurth

            True : If candidate is same or larger in all dimensions.
  """
  for dim in ["Length (mm)", "Width (mm)", "Height (mm)"]:
      ref_val = reference_row[dim]
      cand_val = candidate_row[dim]

      # If reference has a value and candidate doesn't => fail
      if pd.notna(ref_val):
          if pd.isna(cand_val) or cand_val < ref_val:
              return False
  return True


def read_capacitance_dump():
    try:
      with open("database/capacitors_dump.json", encoding="utf-8") as f:
        # Load the JSON data from the file object
        data = json.load(f)
        
      df_capacitors = pd.DataFrame(data)
      print("Successfully read capacitors_dump.json into a DataFrame.")
      print(df_capacitors.columns)
      # print(df_capacitors.head()) # Display the first few rows
      print(df_capacitors["Operating_Temperature (°C)"])
      df_capacitors["Minimum_Operating_Temperature"] = df_capacitors.iloc[:,15].apply(
        lambda x: x[0] if isinstance(x, list) and len(x) == 2 else None
      )

      df_capacitors["Maximum_Operating_Temperature"] = df_capacitors.iloc[:,15].apply(
            lambda x: x[1] if isinstance(x, list) and len(x) == 2 else None
      )

        # Optionally, drop the original column
      df_capacitors.drop(columns=["Operating_Temperature (°C)"], inplace=True)

      column_rename_map = {
          'Order_Code': 'manufacturer_part_number',
          'Product_Unit': 'component_type',
          'Product_Group': 'component_type',
          'Product_Family': 'component_type',
          'Rated_Voltage (V)': 'Rated_Voltage',
          'Capacitance (µF)': 'Capacitance',
          'Diameter (mm)': 'Width_or_Diameter',
          'Length (mm)': 'Length',
          'Size_Code': 'Case_Code',
          'Tolerance_Capacitance (±%)': 'Tolerance',
          'Width (mm)': 'Width_or_Diameter',
          'Ceramic_Type': 'Dielectric_Material_or_Temperature_Coefficient',
          'Rate_Voltage (V)': 'Rated_Voltage',
          'Rated_Voltage_1 (V)': 'Rated_Voltage',
          'Rated_Voltage_2 (V)': 'Rated_Voltage',
          'Minimum_Operating_Temperature': 'Minimum_Operating_Temperature',
          'Maximum_Operating_Temperature': 'Maximum_Operating_Temperature'
        }

      df_capacitors.rename(columns=column_rename_map, inplace=True)

    except FileNotFoundError:
        print("Error: capacitors_dump.json not found.")
    except Exception as e:
        print(f"An error occurred while reading the JSON file: {e}")

    #Replace the Tempature  into maximum & minimum
    # Split the list into two new columns
    # df_capacitors.rename(columns={"Operating_Temperature (Â°C": "Operating_Temperature (°C)"}, inplace=True)

    return df_capacitors


def core_capacitance_constraints_match(target: dict, df_capacitors: pd.DataFrame) -> pd.DataFrame:
    """
    Filters capacitors from df_capacitors that match the core constraints from the target:
    Capacitance, Rated Voltage, Length, Width_or_Diameter, (optionally Height).
    
    If exact match not found, allows slight tolerance on physical dimensions.
    
    Parameters:
    - target: dict containing target specs
    - df_capacitors: DataFrame with capacitor data

    Returns:
    - DataFrame with matched capacitors
    """
    print(target.keys())
    # Strict match filters
    capacitance_match = df_capacitors[
        (df_capacitors["Capacitance"] == target["key_electrical_specs"]["Capacitance"]) |
        (df_capacitors["Capacitance"].isna() & pd.isna(target["key_electrical_specs"]["Capacitance"]))
    ]

    rated_voltage_match = df_capacitors[
        (df_capacitors["Rated_Voltage"] >= target["key_electrical_specs"]["Rated_Voltage"]) |
        (df_capacitors["Rated_Voltage"].isna() & pd.isna(target["key_electrical_specs"]["Rated_Voltage"]))
    ]

    length_match = df_capacitors[
        (df_capacitors["Length"] == target["key_electrical_specs"]["Length"]) |
        (df_capacitors["Length"].isna() & pd.isna(target["key_electrical_specs"]["Length"]))
    ]

    width_match = df_capacitors[
        (df_capacitors["Width_or_Diameter"] == target["key_electrical_specs"]["Width_or_Diameter"]) |
        (df_capacitors["Width_or_Diameter"].isna() & pd.isna(target["key_electrical_specs"]["Width_or_Diameter"]))
    ]

    # Optional if Height is available
    height_match = df_capacitors[
        (df_capacitors.get("Height", pd.Series([None]*len(df_capacitors))) == target["key_electrical_specs"].get("Height")) |
        (df_capacitors.get("Height").isna() & pd.isna(target["key_electrical_specs"].get("Height")))
    ] if "Height" in df_capacitors.columns else df_capacitors.copy()

    # Convert to sets of part numbers
    set_capacitance = set(capacitance_match["manufacturer_part_number"])
    set_voltage = set(rated_voltage_match["manufacturer_part_number"])
    set_length = set(length_match["manufacturer_part_number"])
    set_width = set(width_match["manufacturer_part_number"])
    set_height = set(height_match["manufacturer_part_number"])

    # Strict intersection
    strict_matches = set_capacitance & set_voltage & set_length & set_width & set_height
    matches = df_capacitors[df_capacitors["manufacturer_part_number"].isin(strict_matches)]

    print(f"Debug: Number of strict matches: {len(matches)}")

    if len(matches) > 0:
        print(matches)
        return matches

    # Relaxed comparison on physical dimensions
    print("Info: No strict match found, applying relaxed dimension constraints.")

    # Filter where only capacitance and rated voltage match
    base_filtered_codes = set_capacitance & set_voltage
    base_filtered_df = df_capacitors[df_capacitors["manufacturer_part_number"].isin(base_filtered_codes)]

    # Apply relaxed comparison using is_same_or_larger_dimensions
    relaxed_filtered_df = base_filtered_df[
        base_filtered_df.apply(lambda row: is_same_or_larger_dimensions(row, target), axis=1)
    ]

    print(f"Debug: Number of relaxed matches: {len(relaxed_filtered_df)}")
    print(relaxed_filtered_df)
    return relaxed_filtered_df

def optional_capacitance_constraints_match(target, df_capacitors):
  """

  
  """
  # Check for the Optional constraints
  tolerance_capacitance_match = df_capacitors[(df_capacitors["Tolerance_Capacitance (±%)"] <= target["Tolerance_Capacitance (±%)"]) |(df_capacitors["Tolerance_Capacitance (±%)"].isna() & pd.isna(target["Tolerance_Capacitance (±%)"]))]
  operating_temperature_minimum = df_capacitors[(df_capacitors["Minimum_Operating_Temperature"] <= target["Minimum_Operating_Temperature"]) |(df_capacitors["Minimum_Operating_Temperature"].isna() & pd.isna(target["Minimum_Operating_Temperature"]))]
  operating_temperature_maximum = df_capacitors[(df_capacitors["Maximum_Operating_Temperature"] >= target["Maximum_Operating_Temperature"]) |(df_capacitors["Maximum_Operating_Temperature"].isna() & pd.isna(target["Maximum_Operating_Temperature"]))]
  #dielectric_material_match = df_capacitors[(df_capacitors["Dielectric"] >= target["Dielectric"]) |(df_capacitors["Dielectric"].isna() & pd.isna(target["Dielectric"]))]


  # Convert DataFrames to sets of Order_Code for easy intersection
                              
  set_tolerance_capacitance_match = set(tolerance_capacitance_match['Order_Code'])
  set_operating_temperature_minimum = set(operating_temperature_minimum['Order_Code'])
  set_operating_temperature_minimum = set(operating_temperature_maximum['Order_Code'])

  print(set_tolerance_capacitance_match,set_operating_temperature_minimum,set_operating_temperature_minimum)

  # Find the intersection of the three sets. If there is a match it returns the Order_Code
  order_codes = set_tolerance_capacitance_match.intersection(set_operating_temperature_minimum,set_operating_temperature_minimum)
  
  matches = df_capacitors[df_capacitors["Order_Code"].isin(order_codes)]
  print(matches)
  return matches

def read_resistor_dump():
    try:

      with open("database/resistors_dump.json") as f:
        # Load the JSON data from the file object
        data = json.load(f)
        
      df_resistors = pd.DataFrame(data)
      print("Successfully read capacitors_dump.json into a DataFrame.")
      print(df_resistors.head()) # Display the first few rows

    except FileNotFoundError:
        print("Error: capacitors_dump.json not found.")
    except Exception as e:
        print(f"An error occurred while reading the JSON file: {e}")


    # Split the list into two new columns
    df_resistors["Minimum_Operating_Temperature"] = df_resistors['Temperature_Coefficient_of_Resistance_Range (ppm/°C)'].apply(
        lambda x: x[0] if isinstance(x, list) and len(x) == 2 else None
    )

    df_resistors["Maximum_Operating_Temperature"] = df_resistors['Temperature_Coefficient_of_Resistance_Range (ppm/°C)'].apply(
        lambda x: x[1] if isinstance(x, list) and len(x) == 2 else None
    )

    # Optionally, drop the original column
    df_resistors.drop(columns=["Temperature_Coefficient_of_Resistance_Range (ppm/°C)"], inplace=True)

    return df_resistors

def is_same_or_larger_dimensions(candidate_row, reference_row):
    """
    For fallback matching: checks if candidate is same or larger in all dimensions.
    """
    for dim in ["Length (mm)", "Width (mm)", "Height (mm)"]:
        ref_val = reference_row[dim]
        cand_val = candidate_row[dim]

        if pd.notna(ref_val):
            if pd.isna(cand_val) or cand_val < ref_val:
                return False
    return True

def core_resistor_constraints_match(target, df_resistors):
    """
    Apply core constraints to resistor dataset to find exact or fallback matches.
    """
    resistance_match = df_resistors[
        (df_resistors["Resistance (Ohm)"] == target["Resistance (Ohm)"]) |
        (df_resistors["Resistance (Ohm)"].isna() & pd.isna(target["Resistance (Ohm)"]))
    ]
    power_match = df_resistors[
        (df_resistors["Rated_Power (W)"] >= target["Rated_Power (W)"]) |
        (df_resistors["Rated_Power (W)"].isna() & pd.isna(target["Rated_Power (W)"]))
    ]
    length_match = df_resistors[
        (df_resistors["Length (mm)"] == target["Length (mm)"]) |
        (df_resistors["Length (mm)"].isna() & pd.isna(target["Length (mm)"]))
    ]
    width_match = df_resistors[
        (df_resistors["Width (mm)"] == target["Width (mm)"]) |
        (df_resistors["Width (mm)"].isna() & pd.isna(target["Width (mm)"]))
    ]
    height_match = df_resistors[
        (df_resistors["Height (mm)"] == target["Height (mm)"]) |
        (df_resistors["Height (mm)"].isna() & pd.isna(target["Height (mm)"]))
    ]

    sets = [set(df["Order_Code"]) for df in [resistance_match, power_match, length_match, width_match, height_match]]
    order_codes = set.intersection(*sets)
    matches = df_resistors[df_resistors["Order_Code"].isin(order_codes)]

    if len(matches) > 0:
        print(f"Exact matches found: {len(matches)}")
        return matches

    print("No exact match found. Applying fallback size logic.")

    # Apply fallback: match Resistance & Power, allow dimensions >=
    core_codes = set(resistance_match["Order_Code"]).intersection(set(power_match["Order_Code"]))
    filtered_df = df_resistors[df_resistors["Order_Code"].isin(core_codes)]

    filtered_df = filtered_df[filtered_df.apply(lambda row: is_same_or_larger_dimensions(row, target), axis=1)]
    return filtered_df

def optional_resistor_constraints_match(target, df_resistors):
    """
    Apply optional constraints to further refine matches in resistor dataset.
    """
    # Convert the tolerance column to numeric, coercing errors to NaN
    df_resistors['Tolerance_Resistane (%/Ohm)_numeric'] = pd.to_numeric(
        df_resistors["Tolerance_Resistane (%/Ohm)"], errors='coerce'
    )

    tolerance_match = df_resistors[
        (df_resistors['Tolerance_Resistane (%/Ohm)_numeric'] <= target["Tolerance_Resistane (%/Ohm)"]) |
        (df_resistors['Tolerance_Resistane (%/Ohm)_numeric'].isna() & pd.isna(target["Tolerance_Resistane (%/Ohm)"]))
    ]

    # temp_coeff_match = df_resistors[
    #     (df_resistors["Temperature_Coefficient (ppm/°C)"] == target["Temperature_Coefficient (ppm/°C)"]) |
    #     (df_resistors["Temperature_Coefficient (ppm/°C)"].isna() & pd.isna(target["Temperature_Coefficient (ppm/°C)"]))
    # ]

    temp_min_match = df_resistors[
        (df_resistors["Minimum_Operating_Temperature"] <= target["Minimum_Operating_Temperature"]) |
        (df_resistors["Minimum_Operating_Temperature"].isna() & pd.isna(target["Minimum_Operating_Temperature"]))
    ]
    temp_max_match = df_resistors[
        (df_resistors["Maximum_Operating_Temperature"] >= target["Maximum_Operating_Temperature"]) |
        (df_resistors["Maximum_Operating_Temperature"].isna() & pd.isna(target["Maximum_Operating_Temperature"])) 
    ]

    sets = [set(df["Order_Code"]) for df in [tolerance_match,  temp_min_match, temp_max_match]] #Add  temp_coeff_match to list
    order_codes = set.intersection(*sets)
    matches = df_resistors[df_resistors["Order_Code"].isin(order_codes)]

    # Optionally drop the temporary numeric column if no longer needed outside this function
    # df_resistors.drop(columns=['Tolerance_Resistane (%/Ohm)_numeric'], inplace=True)

    return matches

def extract_json(text):
    # Use regex to extract JSON block from mixed content
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        json_str = match.group(0)
        try:
            data = json.loads(json_str)
            return data
        except json.JSONDecodeError as e:
            print("JSON parsing failed:", e)
    else:
        print("No JSON found in input.")
    return None

req_response_schema =   {
    "type": "array",
    "items":{
        "type": "object",
        "properties": {
          "Manufacturer_Name": {
              "type": "string",
              "description": "Name of the manufacturer",
              "default": ""
          },
          "Manufacturer_Part_Number": {
              "type": "string",
              "description": "Manufacturer's part number"
          },
          "Product_Group": {
              "type": "string",
              "description": "Type of electronic component",
              "enum": [
                "capacitor",
                "inductor",
                "resistor"
              ]
          }
        },
        "required": [
        "Product_Group"
        ]
    }
}

capacitor_schema = {
    "type": "array",
    "items":{
        "type": "object",
        "properties": {
          "Manufacturer_Name": {
              "type": "string",
              "description": "Name of the manufacturer",
              "default": ""
          },
          "Manufacturer_Part_Number": {
              "type": "string",
              "description": "Manufacturer's part number"
          },
          "Product_Group": {
              "type": "string",
              "description": "Type of electronic component",
              "enum": [
                "capacitor",
                "inductor",
                "resistor"
              ]
          },
          "Capacitance": {
              "type": "string",
              "description": "Capacitance value",
          },
          "Rated_Voltage": {
              "type": "string",
              "description": "Rated voltage",
          },
          "Case_Code_or_Dimensions": {
              "type": "string",
              "description": "Case code or physical dimensions",
          },
          "Tolerance": {
              "type": "string",
              "description": "Tolerance of the capacitance value",
          },
          "Dielectric_Material_or_Temperature_Coefficient": {
              "type": "string",
              "description": "Dielectric material or temperature coefficient",
          },
          "Minimum_Operating_Temperature": {
              "type": "string",
              "description": "Minimum operating temperature",
          },
          "Maximum_Operating_Temperature": {
              "type": "string",
              "description": "Maximum operating temperature",
          }
        },
        "required": [
          "Product_Group"
        ]
    }
}


inductor_schema = {
    "type": "array",
    "items":{
        "type": "object",
        "properties": {
          "Manufacturer_Name": {
              "type": "string",
              "description": "Name of the manufacturer",
              "default": ""
          },
          "Manufacturer_Part_Number": {
              "type": "string",
              "description": "Manufacturer's part number"
          },
          "Product_Group": {
              "type": "string",
              "description": "Type of electronic component",
              "enum": [
                "capacitor",
                "inductor",
                "resistor"
              ]
          },
          "Inductance": {
              "type": "string",
              "description": "Inductance value",
          },
          "Rated_Current": {
              "type": "string",
              "description": "Rated current",
          },
          "Case_Code_or_Dimensions": {
              "type": "string",
              "description": "Case code or physical dimensions",
          },
          "Tolerance": {
              "type": "string",
              "description": "Tolerance of the capacitance value",
          },
          "Shielding": {
              "type": "string",
              "description": "Shielding type (e.g., shielded, unshielded)",
          },
          "DC_Resistance":{
              "type": "string",
              "description": "DC resistance"
          },
          "Minimum_Operating_Temperature": {
              "type": "string",
              "description": "Minimum operating temperature",
          },
          "Maximum_Operating_Temperature": {
              "type": "string",
              "description": "Maximum operating temperature",
          }
        },
        "required": [
          "Product_Group"
        ]
    }
}

resistor_schema = {
    "type": "array",
    "items":{
        "type": "object",
        "properties": {
          "Manufacturer_Name": {
              "type": "string",
              "description": "Name of the manufacturer",
              "default": ""
          },
          "Manufacturer_Part_Number": {
              "type": "string",
              "description": "Manufacturer's part number"
          },
          "Product_Group": {
              "type": "string",
              "description": "Type of electronic component",
              "enum": [
                "capacitor",
                "inductor",
                "resistor"
              ]
          },
          "Resistance": {
              "type": "string",
              "description": "Resistance value",
          },
          "Power_Rating": {
              "type": "string",
              "description": "Power Rating value",
          },
          "Case_Code_or_Dimensions": {
              "type": "string",
              "description": "Case code or physical dimensions",
          },
          "Tolerance": {
              "type": "string",
              "description": "Tolerance of the capacitance value",
          },
          "Temperature_Coefficient": {
              "type": "string",
              "description": "Temperature coefficient",
          },
          "Minimum_Operating_Temperature": {
              "type": "string",
              "description": "Minimum operating temperature",
          },
          "Maximum_Operating_Temperature": {
              "type": "string",
              "description": "Maximum operating temperature",
          }
        },
        "required": [
          "Product_Group"
        ]
    }
}