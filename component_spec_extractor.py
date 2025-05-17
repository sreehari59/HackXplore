#!/usr/bin/env python3
import os
import json
import requests
import re
from bs4 import BeautifulSoup
from openai import OpenAI, AzureOpenAI
from dotenv import load_dotenv
import sys

# Load environment variables from .env file if it exists
load_dotenv()

# Set API keys from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AZURE_API_KEY = os.getenv("AZURE_API_KEY")
AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT")
AZURE_API_VERSION = os.getenv("AZURE_API_VERSION") or "2023-05-15"
SERPAPI_KEY = os.getenv("SERP_API_KEY")

# Replace URL-encoded characters if present
if OPENAI_API_KEY and '%' in OPENAI_API_KEY:
    import urllib.parse
    OPENAI_API_KEY = urllib.parse.unquote(OPENAI_API_KEY)

# Set the flag for using Azure OpenAI
USE_AZURE_OPENAI = True if AZURE_API_KEY and AZURE_ENDPOINT else False

def check_api_keys():
    """Check if required API keys are available."""
    missing_keys = []
    if not OPENAI_API_KEY and not AZURE_API_KEY:
        missing_keys.append("OPENAI_API_KEY or AZURE_API_KEY")
    if not SERPAPI_KEY:
        missing_keys.append("SERP_API_KEY")
    
    if missing_keys:
        print("⚠️ Missing API key(s):", ", ".join(missing_keys))
        print("Please set these environment variables in a .env file or your environment.")
        print("  1. Create a .env file in the project directory")
        print("  2. Add the following lines (replacing with your actual keys):")
        print("     OPENAI_API_KEY=your_openai_api_key")
        print("     SERP_API_KEY=your_serpapi_key")
        print(" OR for Azure OpenAI:")
        print("     AZURE_API_KEY=your_azure_api_key")
        print("     AZURE_ENDPOINT=your_azure_endpoint")
        print("     AZURE_API_VERSION=your_azure_api_version")
        return False
    return True

def get_openai_client():
    """Get the appropriate OpenAI client based on available API keys."""
    from openai import OpenAI, AzureOpenAI
    
    if USE_AZURE_OPENAI:
        return AzureOpenAI(
            api_key=AZURE_API_KEY,
            api_version=AZURE_API_VERSION,
            azure_endpoint=AZURE_ENDPOINT
        )
    else:
        return OpenAI(api_key=OPENAI_API_KEY)

def google_search(query):
    """Perform a Google search using SerpAPI."""
    url = "https://serpapi.com/search"
    params = {
        "engine": "google",
        "q": query,
        "api_key": SERPAPI_KEY
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise exception for HTTP errors
        return response.json().get("organic_results", [])
    except requests.exceptions.RequestException as e:
        print(f"❌ Error performing search: {e}")
        return []

def extract_product_page_content(url):
    """Extract text content from a product page URL."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()
            
        # Get text content
        text = soup.get_text(separator=' ', strip=True)
        return text[:5000]  # Limit to 5000 characters
    except Exception as e:
        return f"Error fetching content: {e}"

def parse_part_number(part_number):
    """
    Step 1: Parse the part number using GPT-4 to identify component type and key specs.
    """
    print(f"Step 1: Parsing part number {part_number}")
    
    client = get_openai_client()
    
    prompt = f"""
Given the part number {part_number}, tell me:
- The manufacturer
- The full product description
- Key electrical specs (resistance/capacitance/inductance, tolerance, power/voltage rating, package size)
- Component type (resistor, capacitor, inductor, etc.)

Respond in JSON format with these fields:
{{
  "manufacturer": "Company name",
  "description": "Full product description",
  "component_type": "resistor/capacitor/inductor/etc.",
  "specs": {{
    // Component-specific specs
  }}
}}
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        part_info = json.loads(content)
        
        print(f"✓ Identified component: {part_info['description']}")
        return part_info
    except Exception as e:
        print(f"❌ Error parsing part number: {e}")
        # Return basic information based on part number patterns
        return {
            "manufacturer": "Unknown",
            "description": f"Component {part_number}",
            "component_type": identify_component_type(part_number),
            "specs": {}
        }

def search_datasheet_and_extract_specs(part_number, initial_info):
    """
    Step 2: Search for datasheet and product information, then extract detailed specs.
    """
    print(f"Step 2: Searching for datasheet and specs for {part_number}")
    
    # Create targeted search query with site-specific restrictions
    component_type = initial_info.get("component_type", "").lower()
    manufacturer = initial_info.get("manufacturer", "").lower()
    
    search_query = f"{part_number} datasheet"
    
    # Add manufacturer if known and not "unknown"
    if manufacturer and manufacturer.lower() != "unknown":
        search_query += f" {manufacturer}"
    
    # Add component type if known
    if component_type in ["resistor", "capacitor", "inductor", "ic", "integrated circuit"]:
        search_query += f" {component_type}"
    
    # Add site-specific restrictions
    search_query += " site:digikey.com OR site:mouser.com OR site:octopart.com"
    if manufacturer and manufacturer.lower() != "unknown":
        search_query += f" OR site:{manufacturer.lower().replace(' ', '')}.com"
    
    print(f"  Search query: {search_query}")
    search_results = google_search(search_query)
    
    if not search_results:
        print("❌ No search results found")
        return initial_info
    
    # Get the top result
    top_result = search_results[0]
    page_url = top_result.get("link")
    print(f"  Found page: {page_url}")
    
    # Extract content from the page
    page_content = extract_product_page_content(page_url)
    
    # Use GPT to extract structured specifications
    client = get_openai_client()
    
    prompt = f"""
Extract detailed technical specifications for the electronic component {part_number} from this product page content.
Component type is: {component_type}
Initial information: {json.dumps(initial_info)}

Raw page content:
{page_content}

Extract all available technical specifications and return in this JSON format:
{{
  "part_number": "{part_number}",
  "manufacturer": "Company name",
  "component_type": "resistor/capacitor/inductor/etc.",
  "specs": {{
    // All specifications with their values and units
    // For resistors: resistance, tolerance, power rating, etc.
    // For capacitors: capacitance, voltage rating, tolerance, etc.
    // For inductors: inductance, current rating, tolerance, etc.
  }},
  "datasheet_url": "URL to datasheet if found in the content",
  "product_url": "{page_url}"
}}

Include all available specs even if not explicitly mentioned in the example above.
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        specs = json.loads(content)
        
        # Check if we found a datasheet URL
        if not specs.get("datasheet_url") and "datasheet" in page_url.lower():
            specs["datasheet_url"] = page_url
        
        print(f"✓ Extracted specifications for {part_number}")
        return specs
    except Exception as e:
        print(f"❌ Error extracting specifications: {e}")
        # Return the initial info with the page URL
        initial_info["product_url"] = page_url
        return initial_info

def find_wurth_alternative(part_number, component_info):
    """
    Step 3: Search for and analyze a Würth Elektronik alternative.
    """
    print(f"Step 3: Finding Würth Elektronik alternative for {part_number}")
    
    component_type = component_info.get("component_type", "").lower()
    specs = component_info.get("specs", {})
    
    # Build a targeted search query for Würth alternatives
    search_terms = []
    
    # Add component_type
    if component_type:
        search_terms.append(component_type)
    
    # Add key specs based on component type
    if component_type == "resistor":
        resistance = specs.get("resistance", "")
        if resistance:
            search_terms.append(resistance)
        
        power_rating = specs.get("power_rating", "")
        if power_rating:
            search_terms.append(power_rating)
    
    elif component_type == "capacitor":
        capacitance = specs.get("capacitance", "")
        if capacitance:
            search_terms.append(capacitance)
        
        voltage = specs.get("voltage_rating", "")
        if voltage:
            search_terms.append(voltage)
    
    elif component_type == "inductor":
        inductance = specs.get("inductance", "")
        if inductance:
            search_terms.append(inductance)
        
        current = specs.get("current_rating", "")
        if current:
            search_terms.append(current)
    
    # Add package size
    package = specs.get("package", "") or specs.get("size", "")
    if package:
        search_terms.append(package)
    
    # Create the search query
    search_query = " ".join(search_terms)
    search_query = f"Würth Elektronik {search_query} site:we-online.com OR site:digikey.com OR site:mouser.com"
    
    print(f"  Search query: {search_query}")
    search_results = google_search(search_query)
    
    if not search_results:
        print("❌ No Würth alternatives found")
        return None
    
    # Get the top results
    wurth_parts = []
    
    for result in search_results[:3]:  # Look at top 3 results
        title = result.get("title", "")
        snippet = result.get("snippet", "")
        link = result.get("link", "")
        
        if "würth" in title.lower() or "würth" in snippet.lower() or "we-online" in link.lower():
            # Extract potential part numbers
            # Pattern 1: Look for 9-12 digit numbers (common Würth part format)
            parts = re.findall(r'(\d{9,12})', title + " " + snippet)
            
            # Pattern 2: Look for numbers with WCAP or WE- prefixes
            wcap_parts = re.findall(r'(WCAP-\w+)', title + " " + snippet)
            we_parts = re.findall(r'(WE-\w+)', title + " " + snippet)
            
            # Pattern 3: Look for URLs with part numbers
            url_parts = re.findall(r'/([0-9]{9,12})(?:\.|/|$)', link)
            
            all_parts = parts + url_parts + wcap_parts + we_parts
            
            for part in all_parts:
                if len(part) > 5:  # Avoid too short matches
                    if not any(p.get("part_number") == part for p in wurth_parts):
                        wurth_parts.append({
                            "part_number": part,
                            "url": link,
                            "description": snippet[:100]
                        })
    
    if not wurth_parts:
        print("❌ No Würth part numbers identified")
        return None
    
    print(f"  Found {len(wurth_parts)} potential Würth alternatives")
    
    # Analyze the best match using GPT
    client = get_openai_client()
    
    # Get content for the top Würth part
    top_wurth_part = wurth_parts[0]
    wurth_part_number = top_wurth_part["part_number"]
    wurth_url = top_wurth_part["url"]
    
    # Extract content from the Würth part page
    wurth_content = extract_product_page_content(wurth_url)
    
    prompt = f"""
Compare this Würth Elektronik part ({wurth_part_number}) with the original component ({part_number}).

Original component information:
{json.dumps(component_info, indent=2)}

Würth part page content:
{wurth_content}

Extract technical specifications for the Würth part and determine if it's a suitable replacement.
Analyze compatibility and match quality based on electrical characteristics and physical properties.

Return your analysis in this JSON format:
{{
  "wurth_part": "{wurth_part_number}",
  "manufacturer": "Würth Elektronik",
  "description": "Full description of the Würth part",
  "specs": {{
    // All specifications with values and units
  }},
  "datasheet": "URL to datasheet if found",
  "distributor_links": ["URLs to distributors"],
  "match_quality": "Exact Match/Good Match/Partial Match/Poor Match",
  "compatibility_notes": "Explanation of compatibility or differences"
}}
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        wurth_alternative = json.loads(content)
        
        # Add the URL to the result if not already present
        if "datasheet" not in wurth_alternative or not wurth_alternative["datasheet"]:
            wurth_alternative["datasheet"] = wurth_url
        
        # If no distributor links, add the original URL
        if "distributor_links" not in wurth_alternative or not wurth_alternative["distributor_links"]:
            wurth_alternative["distributor_links"] = [wurth_url]
        
        print(f"✓ Analyzed Würth alternative: {wurth_part_number}")
        return wurth_alternative
    except Exception as e:
        print(f"❌ Error analyzing Würth alternative: {e}")
        # Return basic information
        return {
            "wurth_part": wurth_part_number,
            "manufacturer": "Würth Elektronik",
            "description": top_wurth_part.get("description", ""),
            "url": wurth_url,
            "match_quality": "Unknown (analysis failed)",
            "compatibility_notes": "Error during analysis"
        }

def create_match_report(part_number, component_info, wurth_alternative):
    """
    Step 4: Create a structured match report in the specified format.
    """
    print("Step 4: Creating match report")
    
    # Extract relevant specs from component_info
    specs = component_info.get("specs", {})
    component_type = component_info.get("component_type", "").lower()
    
    # Prepare input specs based on component type
    input_specs = {
        "manufacturer": component_info.get("manufacturer", "Unknown")
    }
    
    if component_type == "resistor":
        input_specs.update({
            "resistance": specs.get("resistance", "N/A"),
            "power_rating": specs.get("power_rating", "N/A"),
            "package": specs.get("package", "") or specs.get("size", "N/A"),
            "tolerance": specs.get("tolerance", "N/A")
        })
    elif component_type == "capacitor":
        input_specs.update({
            "capacitance": specs.get("capacitance", "N/A"),
            "voltage_rating": specs.get("voltage_rating", "N/A"),
            "package": specs.get("package", "") or specs.get("size", "N/A"),
            "tolerance": specs.get("tolerance", "N/A")
        })
    elif component_type == "inductor":
        input_specs.update({
            "inductance": specs.get("inductance", "N/A"),
            "current_rating": specs.get("current_rating", "N/A"),
            "package": specs.get("package", "") or specs.get("size", "N/A"),
            "tolerance": specs.get("tolerance", "N/A")
        })
    else:
        # Generic case
        for key, value in specs.items():
            input_specs[key] = value
    
    # Prepare matched replacement if available
    if wurth_alternative:
        matched_replacement = {
            "manufacturer": "Würth Elektronik",
            "part_number": wurth_alternative.get("wurth_part", ""),
            "datasheet": wurth_alternative.get("datasheet", ""),
            "link": wurth_alternative.get("distributor_links", [""])[0]
        }
        
        match_quality = wurth_alternative.get("match_quality", "")
    else:
        matched_replacement = {
            "manufacturer": "Würth Elektronik",
            "part_number": "No match found",
            "datasheet": "",
            "link": ""
        }
        
        match_quality = "No Match"
    
    # Create the final report
    report = {
        "input_part_number": part_number,
        "input_specs": input_specs,
        "matched_replacement": matched_replacement,
        "match_quality": match_quality
    }
    
    # Add compatibility notes if available
    if wurth_alternative and "compatibility_notes" in wurth_alternative:
        report["compatibility_notes"] = wurth_alternative["compatibility_notes"]
    
    return report

def identify_component_type(part_number):
    """Identify the type of component based on the part number pattern."""
    part = part_number.upper()
    
    # Common component type patterns
    if re.match(r'^(CRCW|RC|ERJ|R|WR|WSLP|WSL)', part):
        return "resistor"
    elif re.match(r'^(C|CC|CL|GRM|WCAP|CGA|UMA)', part):
        return "capacitor"
    elif re.match(r'^(L|LQG|MLF|LQW|SPM|WE-|744)', part):
        return "inductor"
    elif re.match(r'^(AD|LM|NE|MAX|TL|LT)', part):
        return "integrated circuit"
    else:
        # Generic approach: check for common component indicators
        if 'CAP' in part or any(x in part for x in ['F', 'NF', 'PF', 'UF']):
            return "capacitor"
        elif 'IND' in part or 'COIL' in part or 'H' in part:
            return "inductor"
        elif 'RES' in part or 'OHM' in part or any(x in part for x in ['K', 'R', 'OHM']):
            return "resistor"
        elif 'IC' in part or 'MCU' in part or 'CPU' in part:
            return "integrated circuit"
        else:
            return "electronic component"  # Generic fallback

def process_part_number(part_number):
    """
    Process a part number through the 4-step workflow to find a Würth alternative.
    """
    print(f"\n=== 🔍 Processing: {part_number} ===\n")
    
    try:
        # Step 1: Parse the part number
        initial_info = parse_part_number(part_number)
        
        # Step 2: Search for datasheet and extract detailed specs
        detailed_specs = search_datasheet_and_extract_specs(part_number, initial_info)
        
        # Step 3: Find Würth alternative
        wurth_alternative = find_wurth_alternative(part_number, detailed_specs)
        
        # Step 4: Create match report
        match_report = create_match_report(part_number, detailed_specs, wurth_alternative)
        
        # Return the formatted result
        return json.dumps(match_report, indent=2)
    
    except Exception as e:
        print(f"❌ Error processing part: {e}")
        return json.dumps({
            "error": f"Error processing part number {part_number}: {str(e)}",
            "input_part_number": part_number
        })

def main():
    """Main function to run the component replacement finder."""
    print("📋 Würth Elektronik Component Replacement Finder")
    print("-----------------------------------")
    print("This tool uses AI to find Würth Elektronik alternatives for electronic components.")
    
    # Check API keys
    if not check_api_keys():
        return
    
    # Report API choice
    if USE_AZURE_OPENAI:
        print("Using Azure OpenAI API")
    else:
        print("Using standard OpenAI API")
    
    while True:
        # Get part number from user
        print("\nEnter a part number to search (or 'exit' to quit):")
        part_number = input("> ").strip()
        
        # Check if user wants to exit
        if part_number.lower() in ["exit", "quit", "q"]:
            print("Exiting... Goodbye!")
            break
            
        if not part_number:
            print("Please enter a valid part number.")
            continue
        
        # Process the part number
        try:
            print("\nProcessing your request...")
            result = process_part_number(part_number)
            print("\nRESULTS:")
            print(result)
            
            # Ask if user wants to search for another part
            print("\nSearch for another part? (y/n)")
            if input("> ").lower().strip() != "y":
                print("Exiting... Goodbye!")
                break
                
        except Exception as e:
            print(f"\n❌ Error processing part: {e}")
            print("Please try again with a different part number.")


if __name__ == "__main__":
    main() 