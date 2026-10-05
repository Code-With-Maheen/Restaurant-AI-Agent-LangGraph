# Restaurant AI Agent

A Streamlit application that answers restaurant questions using a single LangGraph workflow.

## Features

- **SQL Agent:** Sales summaries, menu prices and recipes.
- **PDF RAG Agent:** Policy and SOP answers with source references.
- Daily, monthly, yearly and relative-date reports.
- Revenue, estimated food cost and gross profit in PKR.

## Tech Stack

Python 3.12 · Streamlit · LangGraph · Google Gemini · SQLite · Chroma

## Dataset

Fictional sample covering **2025–2027**:
- 7,000 sales lines
- 3,500 orders
- 30 menu items with recipes

## Setup

Install dependencies:

```powershell
pip install streamlit langgraph google-genai python-dotenv chromadb pypdf reportlab onnxruntime
```

Create `.env`:

```dotenv
GEMINI_API_KEY=your_api_key
GEMINI_MODEL=your_available_model_id
```

With the sample database and PDFs in place, run:

```powershell
python ingest.py
python -m streamlit run app.py
```

## Example Questions

- What were total sales in 2025?
- Show yesterday’s sales.
- What is the price of 2 Chicken Tikka and 2 Fries?
- Show the Chicken Biryani recipe.
- When should a food quality complaint be reported?

## Limitations

Data and ingredient costs are fictional. Gross profit is estimated; net profit requires operating expenses. AI-generated answers may need verification.

