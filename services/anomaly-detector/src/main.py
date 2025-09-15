import time
import chromadb
from chromadb.utils import embedding_functions
import numpy as np
from sklearn.cluster import DBSCAN
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

print("Anomaly detector starting...")

# Initialize ChromaDB client with retry logic
def init_chroma_client():
    retries = 5
    delay = 10 # seconds
    for i in range(retries):
        try:
            client = chromadb.HttpClient(host='chroma', port=8000)
            # Try a basic operation to check the connection
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

def run_detection_cycle():
    print("Running anomaly detection cycle...")
    try:
        collection = chroma_client.get_or_create_collection(
                name="log_embeddings",
                embedding_function=embedding_gemma
            )
        # Get all vectors from Chroma
        results = collection.get(include=["embeddings", "metadatas"])
        embeddings = results.get('embeddings')

        if embeddings is None or len(embeddings) < 2:
            print("Not enough data to perform clustering.")
            return

        print(f"Retrieved {len(embeddings)} embeddings.")

        # Perform DBSCAN clustering
        dbscan = DBSCAN(eps=0.5, min_samples=5, metric="cosine")
        clusters = dbscan.fit_predict(np.array(embeddings))

        # -1 indicates an anomaly (noise)
        anomalies = np.where(clusters == -1)[0]

        print(f"Found {len(anomalies)} anomalies.")

        for i in anomalies:
            print(f"  - Anomaly detected: {results['metadatas'][i]}")

    except Exception as e:
        print(f"An error occurred during detection cycle: {e}")

if __name__ == "__main__":
    while True:
        run_detection_cycle()
        print("Waiting for 10 seconds before next cycle...")
        time.sleep(10)
