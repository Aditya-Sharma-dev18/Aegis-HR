import os
from langchain_pinecone import PineconeVectorStore
from app.core.config import settings
from langchain_cohere import CohereEmbeddings

def get_secure_vectorstore():
    """
    Returns the Pinecone vector store instance directly.
    """
    # Initialize Cohere Embeddings
    embeddings = CohereEmbeddings(cohere_api_key=settings.COHERE_API_KEY.get_secret_value(), model="embed-english-v3.0")
    
    # Initialize Pinecone
    vectorstore = PineconeVectorStore(
        index_name=settings.PINECONE_INDEX_NAME, 
        embedding=embeddings, 
        pinecone_api_key=settings.PINECONE_API_KEY.get_secret_value()
    )
    
    return vectorstore