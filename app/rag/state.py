from typing import Any, Dict, List, Optional, TypedDict
from pydantic import BaseModel
from langchain_core.documents import Document

class State(TypedDict, total=False):
    """ 
    Represents the state of the application, including user information and other relevant data.
    """
    question:str
    generation:str
    user_clearance:int
    user_department:str
    documents:List[Document]
    web_fallback:bool
