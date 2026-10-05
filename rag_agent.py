import os
from pathlib import Path
import sys

import chromadb
from dotenv import load_dotenv
from google import genai


PROJECT_ROOT = Path(__file__).resolve().parent
CHROMA_DIR = PROJECT_ROOT / "chroma_db"
COLLECTION_NAME = "restaurant_policies"

load_dotenv(PROJECT_ROOT / ".env")


def retrieve_documents(question: str, limit: int = 3) -> list[dict]:
    if not CHROMA_DIR.exists():
        raise FileNotFoundError(
            "chroma_db missing hai. Pehle ingest.py chalao."
        )

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_collection(name=COLLECTION_NAME)

    if collection.count() == 0:
        raise RuntimeError("Chroma collection empty hai.")

    results = collection.query(
        query_texts=[question],
        n_results=min(limit, collection.count()),
    )

    matches = []

    for text, metadata in zip(
        results["documents"][0],
        results["metadatas"][0],
    ):
        matches.append({
            "text": text,
            "source": metadata["source"],
            "page": metadata["page"],
        })

    return matches


def ask_rag(question: str) -> dict:
    matches = retrieve_documents(question)

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY .env mein nahi mili.")

    context = "\n\n".join(
        f"Source: {item['source']}, page {item['page']}\n"
        f"Text: {item['text']}"
        for item in matches
    )

    prompt = f"""
    Answer the user's question using ONLY the document extracts below.

    If the extracts do not contain the answer, say:
    "I could not find this information in the provided documents."

    Give a short, clear answer. Do not invent policy details.
    Mention the source filename and page number.

    DOCUMENT EXTRACTS:
    {context}

    USER QUESTION:
    {question}
    """

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt,
    )

    if not response.text:
        raise RuntimeError("Gemini ne answer return nahi kiya.")

    return {
        "answer": response.text.strip(),
        "sources": [
            f"{item['source']} (page {item['page']})"
            for item in matches
        ],
    }


if __name__ == "__main__":
    question = "When should a food quality complaint be reported?"

    print("QUESTION:", question)
    matches = retrieve_documents(question)

    print("\nRETRIEVED DOCUMENT TEXT:")
    for item in matches:
        print(f"\nSource: {item['source']}, page {item['page']}")
        print(item["text"])

    # Gemini test sirf --answer dene par chalega.
    if "--answer" in sys.argv:
        print("\nGENERATED ANSWER:")
        print(ask_rag(question)["answer"])