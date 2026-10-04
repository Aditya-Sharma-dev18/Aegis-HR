from typing import Any, Dict, List, Optional
from pydantic import BaseModel

class State(BaseModel):
    """ 
    Represents the state of the application, including user information and other relevant data.
    """
    question:str
    answer:str
    user_clearnce:int
    user_department:str
    documents:List[Documents]
    web_fallback:bool
