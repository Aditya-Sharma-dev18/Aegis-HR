from typing import Any, Dict, List, Optional, TypedDict
from pydantic import BaseModel
from langchain_core.documents import Document

class State(TypedDict, total=False):
    """ 
    Represents the state of the application, including user information and other relevant data.
    """
    question:str
    current_query:str
    kb_docs:List[Document]
    kb_grade:str
    web_grade:str
    answer:str
    source_used:str
    trace:List[str]
    citations:str
    retry_count:int







