from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.tools.tavily_search import TavilySearch
from app.rag.retriever import get_secure_reteriver  
from app.rag.state import State
from app.core.config import settings

model= ChatGroq(
    model="openai/gptoss-120b",
    api_key=settings.OPENAI_API_KEY,
   )

def web_search_tool():
    client=TavilySearch(api_key=settings.TAVILY_API_KEY,max_results=5,include_answers=True,include_raw_content=True)
    return client