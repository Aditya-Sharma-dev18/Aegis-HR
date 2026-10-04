from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.rag.retriever import get_secure_reteriver  # Assuming you spelled it 'reteriver' in your file
from app.rag.state import State
from app.core.config import settings

def retrieve(state: State):
    """
    Node 1: Retrieves relevant documents based on the user's clearance.
    """
    print(f"---NODE: RETRIEVE DOCUMENTS--- \nIncoming State: {state}")
    
    # FIX: Use .get() to prevent KeyErrors. Default clearance to 1 (lowest) for safety.
    question = state.get("question", "")
    clearance = state.get("user_clearance", 1) 
    
    # FIX: Removed the buggy duplicate line with 'state.user_clearnce'
    retriever = get_secure_reteriver(user_clearance=clearance)
    
    documents = retriever.invoke(question)
    
    return {"documents": documents, "question": question}


def generate(state: State):
    """
    Node 2: Generates an answer based on the retrieved documents.
    """
    print("---NODE: GENERATE ANSWER---")
    
   
    question = state.get("question", "")
    documents = state.get("documents", [])

    # Enterprise Guardrail: If no documents are found (due to clearance or bad search)
    if not documents:
        return {"generation": "I do not have clearance or information to answer this."}

    # Combine document chunks into one text block
    docs_text = "\n".join([doc.page_content for doc in documents])
    
    model = ChatGroq(
        model="openai/gpt-oss-20b",
        api_key=settings.GROQ_API_KEY.get_secret_value(),
        temperature=0 # Keep it 0 so AI doesn't hallucinate enterprise policies
    )

    prompt = PromptTemplate(
        template="""You are Aegis-HR, a secure enterprise AI assistant. 
        Answer the question based ONLY on the provided context. If the answer is not in the context, say "I do not have clearance or information to answer this."
        
        Context: {context}
        
        Question: {question}
        Answer:""",
        input_variables=["context", "question"]
    )

    chain = prompt | model | StrOutputParser()
    answer = chain.invoke({"context": docs_text, "question": question})
    
    return {"generation": answer}


workflow = StateGraph(State)

# Add our two nodes
workflow.add_node("retrieve", retrieve)
workflow.add_node("generate", generate)

# Define the flow
workflow.set_entry_point("retrieve")
workflow.add_edge("retrieve", "generate")
workflow.add_edge("generate", END)

# Compile the brain
rag_app = workflow.compile()