import os

from langchain_pinecone import PineconeVectorStore
from app.core.config import settings
from pinecone import Pinecone
from langchain_cohere import CohereEmbeddings

def get_secure_reteriver(user_clearance:int):
    """
    Creates a retriever that strictly filters documents based on the user's clearance.
    An employee (Level 1) will NEVER see Level 5 documents.
    """
    # Initialize Cohere Embeddings
    embeddings = CohereEmbeddings(cohere_api_key=settings.COHERE_API_KEY.get_secret_value(), model="embed-english-v3.0")

    # Initialize Pinecone
    vectorstore=PineconeVectorStore(index_name=settings.PINECONE_INDEX_NAME, embedding=embeddings, pinecone_api_key=settings.PINECONE_API_KEY.get_secret_value())

    #
    rbac_filter={
        "clearance": {"$lte": user_clearance}

    }
    return vectorstore.as_retriever(search_kwargs={"k":3,"filter": rbac_filter})

