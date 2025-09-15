import streamlit as st
import chromadb
from chromadb.utils import embedding_functions
import pandas as pd
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

st.set_page_config(layout="wide")
st.title("Semantic Log Analysis Dashboard")

@st.cache_resource
def init_chroma_client():
    try:
        client = chromadb.HttpClient(host='chroma', port=8000)
        return client
    except Exception as e:
        st.error(f"Failed to connect to ChromaDB: {e}")
        return None

# --- Main App ---
chroma_client = init_chroma_client()

if not chroma_client:
    st.warning("ChromaDB client not available. Cannot proceed.")
    st.stop()

collection = chroma_client.get_or_create_collection(
                name="log_embeddings",
                embedding_function=embedding_gemma
            )

# --- Search Section ---
st.header("Log Search")
search_query = st.text_input("Enter a log message to search for similar logs:", value="the input value 'xxx' is invalid.")

if st.button("Search"):
    if not search_query.strip():
        st.warning("Please enter a search query.")
    else:
        if search_query:
            st.write("### Search Results")
            try:
                results = collection.query(
                    query_texts=[search_query],
                    n_results=10,
                )

                if not results or not results['documents'][0]:
                    st.write("No similar logs found.")
                else:
                    threshold = 1.0
                    filtered_indices = [i for i, distance in enumerate(results['distances'][0]) if distance < threshold]
                    filtered_documents = [doc for i, doc in enumerate(results['documents'][0]) if i in filtered_indices]
                    filtered_metadatas = [meta for i, meta in enumerate(results['metadatas'][0]) if i in filtered_indices]
                    filtered_distances = [dist for i, dist in enumerate(results['distances'][0]) if i in filtered_indices]
                    if not filtered_documents:
                        st.write("No similar logs found within the distance threshold.")
                    else:
                        results_df = pd.DataFrame(filtered_metadatas)
                        results_df['distance'] = filtered_distances
                        results_df['message'] = filtered_documents
                        results_df = results_df.sort_values(by='distance').reset_index(drop=True)
                        st.dataframe(results_df[['distance', 'timestamp', 'level', 'message', 'service']])

            except Exception as e:
                st.error(f"An error occurred during search: {e}")

# --- Latest Logs Section ---
st.header("Latest Logs")
if st.button("Refresh Latest Logs"):
    st.cache_data.clear()

try:
    log_data = collection.get(include=["metadatas"], limit=100)
    if log_data and log_data['metadatas']:
        df = pd.DataFrame(log_data['metadatas'])
        st.dataframe(df)
    else:
        st.write("No logs found in the database.")
except Exception as e:
    st.error(f"Could not fetch logs: {e}")
