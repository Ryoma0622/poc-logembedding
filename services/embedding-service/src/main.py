from fastapi import FastAPI, Body
from pydantic import BaseModel
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any
import time
import traceback
import os

HF_TOKEN = os.getenv("HUGGING_FACE_CHROMA_TOKEN")

try:
    embedding_gemma = embedding_functions.HuggingFaceEmbeddingFunction(
        api_key=HF_TOKEN,
        model_name="google/embedding-gemma-300m"
    )
except Exception as e:
    print(f"Embedding Functionの初期化中にエラーが発生しました: {e}")
    exit()

class Query(BaseModel):
    text: str

app = FastAPI()

# Initialize ChromaDB client with retry logic
def init_chroma_client():
    retries = 5
    delay = 10 # seconds
    for i in range(retries):
        try:
            client = chromadb.HttpClient(host='chroma', port=8000)
            client.get_or_create_collection(
                name="log_embeddings",
                embedding_function=embedding_gemma
            )
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
collection = chroma_client.get_or_create_collection(
                name="log_embeddings",
                embedding_function=embedding_gemma
            )

@app.post("/embed")
def embed_log(payload: List[Dict[str, Any]] = Body(...)):
    try:
        documents_to_add = []
        metadatas_to_add = []
        ids_to_add = []

        for i, log in enumerate(payload):
            message = log.get("message")
            if not message:
                continue

            metadata = {
                "timestamp": log.get("asctime", ""),
                "level": log.get("levelname", ""),
                "service": log.get("service", "unknown"),
                "message": message
            }

            documents_to_add.append(message)
            metadatas_to_add.append(metadata)
            ids_to_add.append(f"{log.get('asctime', '')}-{i}-{message[:10]}")

        if documents_to_add:
            collection.add(
                documents=documents_to_add,
                metadatas=metadatas_to_add,
                ids=ids_to_add
            )

        return {"status": "processed", "count": len(documents_to_add)}

    except Exception as e:
        print(f"Failed to process batch of logs. Error: {e}")
        print("--- Traceback ---")
        print(traceback.format_exc())
        print("-----------------")
        return {"status": "error", "detail": str(e)}

@app.get("/health")
def health_check():
    return {"status": "ok"}
