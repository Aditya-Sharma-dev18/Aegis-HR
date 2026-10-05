from pydantic import BaseModel,Field
from typing import Literal, Optional

class routequery(BaseModel):
    """ 
    decides where to send the users query based on the question 
    
    """
    datasource:str=Field(...,description="Given a user question, choose to route it to 'KB' for internal HR/company policies, or 'web' for general world knowledge."   )


class gradedocuments(BaseModel):
    """Boolean score for relevance check on retrieved documents."""
    binary_score: str = Field(
        ...,
        description="Documents are relevant to the question, 'yes' or 'no'"
    )
   