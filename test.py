from sentence_transformers import SentenceTransformer
import os

token = os.getenv("HUGGING_FACE_CHROMA_TOKEN")
print(token)
model = SentenceTransformer(token=token, model_name_or_path="google/embeddinggemma-300m")

sentences = [
    "That is a happy person",
    "That is a happy dog",
    "That is a very happy person",
    "Today is a sunny day"
]
embeddings = model.encode(sentences)

similarities = model.similarity(embeddings, embeddings)
print(similarities.shape)
