from fastapi import FastAPI, Body
from sentence_transformers import SentenceTransformer
import chromadb
from typing import List, Dict, Any
import time

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

@app.post("/embed")
def embed_log(payload: List[Dict[str, Any]] = Body(...)):
    processed_count = 0
    for log in payload:
        try:
            message = log.get("message", "")
            if not message:
                continue

            embedding = model.encode([message])[0].tolist()

            metadata = {
                "timestamp": log.get("asctime", ""),
                "level": log.get("levelname", ""),
                "service": log.get("service", "unknown"),
                "message": message
            }

            log_id = f"{log.get('asctime', '')}-{processed_count}"

            collection.add(
                embeddings=[embedding],
                documents=[message],
                metadatas=[metadata],
                ids=[log_id]
            )
            processed_count += 1
        except Exception as e:
            print(f"Failed to process and add log: {log}. Error: {e}")

    return {"status": "processed", "count": processed_count}

@app.get("/health")
def health_check():
    return {"status": "ok"}