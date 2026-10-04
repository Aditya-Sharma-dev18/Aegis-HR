from langgraph.graph import StateGraph,START,END
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.rag.retriever import get_secure_reteriver
from app.rag.state import State
from app.core.config import settings

def retrieve(state:State):
    """
    This function retrieves relevant documents based on the user's clearance and the question asked.
    It uses a secure retriever to ensure that users only access documents they are authorized to view.
    """

    question=state["question"]
    clearance=state["user_clearnce"]
    # Create a secure retriever based on the user's clearance level
    retriever = get_secure_reteriver(state.user_clearnce)
    
    # Retrieve documents using the retriever
    retriever = get_secure_reteriver(user_clearance=clearance)
    
    # Retrieve documents based on the question and the user's clearance level
    documents = retriever.invoke(question)
   

    return {"documents": documents,"question":question}


def generate(state:State):
    """
    This function generates an answer based on the retrieved documents and the user's question.
    It uses a language model to generate a response, ensuring that the answer is relevant and accurate.
    """

    question=state["question"]
    documents=state["documents"]


   # 1. Combine document chunks into one text block
    docs_text="\n".join([doc.page_content for doc in documents])
    
    # Create a language model for generating answers
    model = ChatGroq(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY.get_secret_value(),
        
    )

    #create a prompt template for the language model
    prompt = PromptTemplate(
        template="""You are Aegis-HR, a secure enterprise AI assistant. 
        Answer the question based ONLY on the provided context. If the answer is not in the context, say "I do not have clearance or information to answer this."
        
        Context: {context}
        
        Question: {question}
        Answer:""",
        input_variables=["context", "question"]
    )

    chain=prompt | model |StrOutputParser()
    answer=chain.invoke({"context":docs_text,"question":question})
    return {"generation": answer}


workflow = StateGraph(State)

# Add our two nodes
workflow.add_node("retrieve", retrieve)
workflow.add_node("generate", generate)

# Define the flow (Start -> Retrieve -> Generate -> End)
workflow.set_entry_point("retrieve")
workflow.add_edge("retrieve", "generate")
workflow.add_edge("generate", END)

# Compile the brain
rag_app = workflow.compile()




      
   