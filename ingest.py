from pathlib import Path

import chromadb
from pypdf import PdfReader


PROJECT_ROOT = Path(__file__).resolve().parent
DOCUMENTS_DIR = PROJECT_ROOT / "data" / "documents"
CHROMA_DIR = PROJECT_ROOT / "chroma_db"
COLLECTION_NAME = "restaurant_policies"


def split_text(text, chunk_size=450, overlap=70):
    """Text ko overlapping chunks mein divide karta hai."""
    text = " ".join(text.split())
    chunks = []

    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])

        if end == len(text):
            break

        start = end - overlap

    return chunks


def main():
    pdf_files = sorted(DOCUMENTS_DIR.glob("*.pdf"))

    if not pdf_files:
        raise FileNotFoundError(
            f"No PDF files found in: {DOCUMENTS_DIR}"
        )

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    # Dobara run karne par duplicate chunks nahi banenge.
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME
    )

    ids = []
    documents = []
    metadatas = []

    for pdf_path in pdf_files:
        reader = PdfReader(str(pdf_path))

        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""

            if not text.strip():
                print(
                    f"Warning: no text found in "
                    f"{pdf_path.name}, page {page_number}"
                )
                continue

            chunks = split_text(text)

            for chunk_number, chunk in enumerate(chunks, start=1):
                ids.append(
                    f"{pdf_path.stem}_p{page_number}_c{chunk_number}"
                )
                documents.append(chunk)
                metadatas.append({
                    "source": pdf_path.name,
                    "page": page_number,
                    "chunk": chunk_number,
                })

        print(f"Read: {pdf_path.name}")

    if not documents:
        raise RuntimeError(
            "PDFs se text extract nahi hua. Files check karo."
        )

    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
    )

    print(f"Indexed chunks: {len(documents)}")
    print(f"Collection count: {collection.count()}")
    print(f"Chroma location: {CHROMA_DIR}")

    question = "When can a customer report a food quality complaint?"
    results = collection.query(
        query_texts=[question],
        n_results=2,
    )

    print("\nTEST QUESTION:", question)

    for document, metadata in zip(
        results["documents"][0],
        results["metadatas"][0],
    ):
        print(
            f"\nSource: {metadata['source']}, "
            f"page {metadata['page']}"
        )
        print(f"Relevant text: {document}")

    print("\nPhase 4 retrieval check PASSED.")


if __name__ == "__main__":
    main()