from fastapi import FastAPI, Body
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import chromadb
from typing import List, Dict, Any
import time

class Query(BaseModel):
    text: str

app = FastAPI()

# Load the sentence-transformer model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Initialize ChromaDB client with retry logic
def init_chroma_client():
    retries = 5
    delay = 10 # seconds
    for i in range(retries):
        try:
            client = chromadb.HttpClient(host='chroma', port=8000)
            client.get_or_create_collection(name="test-connection")
            print("Successfully connected to ChromaDB.")
            return client
        except Exception as e:
            print(f"Could not connect to ChromaDB (attempt {i+1}/{retries}): {e}")
            if i < retries - 1:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print("Failed to connect to ChromaDB after several retries.")
                raise

chroma_client = init_chroma_client()
collection = chroma_client.get_or_create_collection(name="log_embeddings")

@app.post("/embed-query")
def embed_query(query: Query):
    embedding = model.encode(query.text)
    return {"embedding": embedding.tolist()}

@app.post("/embed")
def embed_log(payload: List[Dict[str, Any]] = Body(...)):
    messages = [log.get("message") for log in payload if log.get("message")]
    if not messages:
        return {"status": "no valid messages to process"}

    try:
        embeddings = model.encode(messages)

        documents_to_add = []
        metadatas_to_add = []
        ids_to_add = []

        for i, log in enumerate(payload):
            if not log.get("message"):
                continue

            metadata = {
                "timestamp": log.get("asctime", ""),
                "level": log.get("levelname", ""),
                "service": log.get("service", "unknown"),
                "message": log.get("message")
            }

            documents_to_add.append(log.get("message"))
            metadatas_to_add.append(metadata)
            ids_to_add.append(f"{log.get('asctime', '')}-{i}-{log.get('message')[:10]}")

        if documents_to_add:
            collection.add(
                embeddings=embeddings.tolist(),
                documents=documents_to_add,
                metadatas=metadatas_to_add,
                ids=ids_to_add
            )

        return {"status": "processed", "count": len(documents_to_add)}

    except Exception as e:
        print(f"Failed to process batch of logs. Error: {e}")
        return {"status": "error", "detail": str(e)}

@app.get("/health")
def health_check():
    return {"status": "ok"}
