# HackXplore

# Component Specification Extractor

This tool extracts technical specifications for electronic components by:
1. Searching for component datasheets online
2. Extracting content from the search results
3. Using AI to summarize specifications in a structured format

## Installation

1. Clone the repository
2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

## Configuration

Create a `.env` file in the project root with your API keys:
```
# OpenAI API Key - required for specification summarization
OPENAI_API_KEY=your_openai_api_key_here

# SerpAPI Key - required for Google search functionality
SERPAPI_KEY=your_serpapi_key_here
```

You can get API keys from:
- OpenAI: https://platform.openai.com/api-keys
- SerpAPI: https://serpapi.com/

## Usage

Run the script directly:
```
python component_spec_extractor.py
```

This will start an interactive session where you can:
1. Enter any electronic component part number
2. Specify optional filter criteria (voltage, capacitance, package)
3. Get detailed specifications and Würth Elektronik alternatives

The tool will search for the component datasheet, extract specifications, and automatically suggest Würth alternatives with matching characteristics.

## Customization

You can modify the script to:
- Process different part numbers
- Change the filter criteria
- Adjust the prompt sent to the OpenAI API
- Format the output differently

## Example Output

The script will output structured JSON data for each component, including:
- Part Number
- Manufacturer
- Electrical specifications
- Package size
- Applications
- Alternative parts
- And more

## Troubleshooting

If you encounter issues:
1. Check that your API keys are correctly set in the `.env` file
2. Ensure you have an active internet connection
3. Verify the OpenAI API is operational
4. Check SerpAPI usage limits 
