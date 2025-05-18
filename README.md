# HackXplore

## 🚧🔧 The Painpoint

Managing a Bill of Materials (BOM) manually is time-consuming ⏳ and prone to costly errors ❌. Engineers and procurement teams often face inconsistent data, obsolete parts ⚠️, and complex supplier variations, leading to delays 🚫 and supply chain headaches 📉. Without automation, sourcing and validating components becomes a bottleneck in product development.


## 🚀 WEMA - Würth Electronics Matching Assistant

WEMA (Würth Electronics Matching Assistant) is an end-to-end solution designed to standardize your Bill of Materials (BOM) and intelligently suggest Würth Electronics components as alternatives to competitor parts. 🧠⚙️

Powered by a network of intelligent agents — from standardization agents to web search agents — WEMA ensures a smooth and efficient part-matching process.

✨ Key Features:
🔄 BOM Standardization
🤖 AI-Powered Component Matching
🔍 Explainable AI: Understand why a component was recommended — because transparency matters.
☁️ Cloud Native: Deployed on Microsoft Azure for scalability and reliability.
🤝 Seamless Integration: Upload BOMs and get instant suggestions via Microsoft Teams, Slack, or Telegram!

WEMA is built for engineers, by engineers — to simplify, accelerate, and optimize component selection. 🛠️📈

# Tech Stack
- Azure
- Python
- Flask
- OpenAI
- Gemini
- BeautifulSoup
- N8N

## Installation 
Please use the below steps to run the back end code
- Clone the repository
- Create an environment and activate it
- Install the required packages:
   ```
   pip install -r requirements.txt
   ```
- Create `.env` file and update the:
`
SERP_API_KEY=
AZURE_ENDPOINT=
AZURE_API_VERSION=
AZURE_API_KEY=
GEMINI_API_KEY=
OPENAI_API_KEY=
`
You can get API keys from:
- OpenAI: https://platform.openai.com/api-keys
- SerpAPI: https://serpapi.com/
- Gemini: https://aistudio.google.com/apikey

For the Front end please find the link [here](https://github.com/jordibernandi/hackxplore_fe)

## Usage

Run the script directly:
```
python app.py
```

This will start an interactive session where you can:
1. Enter any electronic component part number
2. Specify optional filter criteria (voltage, capacitance, package)
3. Get detailed specifications and Würth Elektronik alternatives

The tool will search for the component datasheet, extract specifications, and automatically suggest Würth alternatives with matching characteristics.

## Example Output

The script will output structured JSON data for each component, including:
- Part Number
- Manufacturer Name
- Electrical specifications
- Dimensions

## Troubleshooting

If you encounter issues:
1. Check that your API keys are correctly set in the `.env` file
2. Ensure you have an active internet connection
3. Verify the OpenAI API is operational
4. Check SerpAPI usage limits 
