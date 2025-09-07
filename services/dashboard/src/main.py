import streamlit as st
import chromadb
import pandas as pd
import time

st.set_page_config(layout="wide")
st.title("Semantic Log Analysis Dashboard")

# Initialize ChromaDB client with retry logic
@st.cache_resource
def init_chroma_client():
    retries = 5
    delay = 10 # seconds
    for i in range(retries):
        try:
            client = chromadb.HttpClient(host='chroma', port=8000)
            # Try a basic operation to check the connection
            client.get_or_create_collection(name="test-connection")
            st.success("Successfully connected to ChromaDB.")
            return client
        except Exception as e:
            if i < retries - 1:
                time.sleep(delay)
            else:
                st.error(f"Failed to connect to ChromaDB after {retries} retries: {e}")
                return None

chroma_client = init_chroma_client()

if chroma_client:
    st.header("Latest Logs")
    try:
        collection = chroma_client.get_or_create_collection(name="log_embeddings")
        log_data = collection.get(include=["metadatas"])
        if log_data and log_data['metadatas']:
            df = pd.DataFrame(log_data['metadatas'])
            st.dataframe(df)
        else:
            st.write("No logs found in the database.")
    except Exception as e:
        st.error(f"Could not fetch logs: {e}")

else:
    st.warning("ChromaDB client not available.")

if st.button("Refresh"):
    st.rerun()