import os
from typing import List
from langchain_pinecone import PineconeVectorStore
from langchain_cohere import CohereEmbeddings
from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

from app.core.config import settings


def get_secure_vectorstore():
    """
    Returns the Pinecone vector store instance directly.
    """
    # Initialize Cohere Embeddings
    embeddings = CohereEmbeddings(
        cohere_api_key=settings.COHERE_API_KEY.get_secret_value(),
        model="embed-english-v3.0"
    )
    
    # Initialize Pinecone
    vectorstore = PineconeVectorStore(
        index_name=settings.PINECONE_INDEX_NAME, 
        embedding=embeddings, 
        pinecone_api_key=settings.PINECONE_API_KEY.get_secret_value()
    )
    
    return vectorstore


def run_bm25_search(query: str, candidate_docs: List[Document], top_k: int = 10) -> List[Document]:
    """
    Runs BM25 lexical scoring over RBAC-filtered candidate documents and merges
    lexical rank with dense semantic rank using Reciprocal Rank Fusion (RRF).
    """
    if not candidate_docs:
        return []

    # Tokenize corpus and query
    tokenized_corpus = [doc.page_content.lower().split() for doc in candidate_docs]
    tokenized_query = query.lower().split()

    bm25 = BM25Okapi(tokenized_corpus)
    bm25_scores = bm25.get_scores(tokenized_query)

    # Sort indices by BM25 lexical score (highest first)
    bm25_ranked_indices = sorted(
        range(len(candidate_docs)),
        key=lambda i: bm25_scores[i],
        reverse=True
    )

    # Reciprocal Rank Fusion (RRF) combining Dense Rank + BM25 Rank
    rrf_scores = {}
    k_constant = 60

    for dense_rank, doc_idx in enumerate(range(len(candidate_docs))):
        rrf_scores[doc_idx] = rrf_scores.get(doc_idx, 0.0) + 1.0 / (k_constant + dense_rank + 1)

    for lexical_rank, doc_idx in enumerate(bm25_ranked_indices):
        rrf_scores[doc_idx] = rrf_scores.get(doc_idx, 0.0) + 1.0 / (k_constant + lexical_rank + 1)

    # Return top_k documents sorted by fused RRF score
    fused_indices = sorted(rrf_scores.keys(), key=lambda i: rrf_scores[i], reverse=True)[:top_k]
    return [candidate_docs[i] for i in fused_indices]