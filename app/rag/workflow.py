from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.tools.tavily_search import TavilySearchResults
from app.rag.retriever import get_secure_reteriver 
from app.schemas import routequery,gradedocuments
from app.rag.retriever import get_secure_vectorstore
from app.rag.state import State
from langchain_core.documents import Document
from app.core.config import settings
from langchain_core.prompts import ChatPromptTemplate
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool
import os

model= ChatGroq(
    model="openai/gpt-oss-120b",
    api_key=settings.GROQ_API_KEY,
   )


question_router=model.with_structured_output(routequery)


router_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert at routing a user question to a vectorstore or web search. "
               "The vectorstore contains documents related to HR policies, leave, severance, and employee benefits. "
               "Use the vectorstore for questions on these topics. Otherwise, use web-search."),
    ("human", "{question}")
])
router_chain = router_prompt | question_router

retrieval_grader = model.with_structured_output(gradedocuments)
grader_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a grader assessing relevance of a retrieved document to a user question. "
               "If the document contains keyword(s) or semantic meaning related to the user question, grade it as relevant. "
               "It does not need to be a stringent test. The goal is to filter out erroneous retrievals. \n"
               "Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question."),
    ("human", "Retrieved document: \n\n {document} \n\n User question: {question}")
])
grader_chain = grader_prompt | retrieval_grader


def retrieve(state: State):
    """Node 3: Fetch from Pinecone with RBAC Security"""
    print("---NODE: RETRIEVE FROM PINECONE---")
    question = state.get("question", "")
    clearance = state.get("user_clearance", 1) 
    
    # Get the vectorstore and query it directly (bypassing the buggy retriever class)
    vectorstore = get_secure_vectorstore()
    rbac_filter = {"clearance": {"$lte": clearance}}
    
    documents = vectorstore.similarity_search(
        query=question, 
        k=3, 
        filter=rbac_filter
    )
    
    trace = state.get("trace", [])
    trace.append("Searched Pinecone KB")
    
    return {"kb_docs": documents, "question": question, "trace": trace, "source_used": "Knowledge Base"}
       
def web_search(state:State):
    """ 
    Performs a web search based on the user's question and applies a relevance grading step.
    """
    question=state.get("question","")
    trace=state.get("trace",[])
    trace.append("web search step completed")
    tool=TavilSearchResults(max_results=5,include_answers=True,include_raw_content=True)
    docs=tool.invoke({"query":question})
    web_results="/n".join(d["content"] for d in docs)
    web_docs=[Document(page_content=web_results)]


def grade_documents(state:State):
    """
    Grades the retrieved documents for relevance to the user's question.
    """
    question = state.get("question","")
    documents = state.get("kb_docs",[])
    trace=state.get("trace",[])
    filtered_docs=[]
    for doc in documents:
        score=grader_chain.invoke({"document":doc.page_content,"question":question})
        grade=score.binary_score
        if grade=="yes":
            filtered_docs.append(doc)
        else:
            print(f"Document filtered out due to irrelevance")

    if not filtered_docs:
        print("---DECISION: ALL DOCS WEAK, SWITCH TO WEB---")
        trace.append("KB docs were irrelevant. Switching to Web.")
        return {"kb_docs": [], "kb_grade": "weak", "trace": trace}
    else:
        trace.append("KB docs passed grading.")
        return {"kb_docs": filtered_docs, "kb_grade": "good", "trace": trace}


def grade_web_documents(state:State):
    """
    Grades the web search results for relevance to the user's question.
    """
    question = state.get("question","")
    documents = state.get("web_docs",[])
    trace=state.get("trace",[])
    filtered_docs=[]
    for doc in documents:
        score=grader_chain.invoke({"document":doc.page_content,"question":question})
        grade=score.binary_score
        if grade=="yes":
            filtered_docs.append(doc)
    if not filtered_docs:
        print("---DECISION: WEB DOCS ALSO WEAK, GO TO FALLBACK---")
        trace.append("Web docs were irrelevant. Moving to Fallback.")
        return {"web_docs": [], "web_grade": "weak", "trace": trace}
    else:
        trace.append("Web docs passed grading.")
        return {"web_docs": filtered_docs, "web_grade": "good", "trace": trace}


def fallback_generate(state: State):
    """Node 9: Fallback Answer when both KB and Web fail"""
    print("---NODE: FALLBACK ANSWER---")
    trace = state.get("trace", [])
    trace.append("Generated Fallback Answer")
    
    fallback_text = "I do not have sufficient information in the secure Knowledge Base or the open Web to answer this question accurately."
    return {"generation": f"{fallback_text} \n\n*(Source: Fallback)*"}


def decide_web_generation(state: State):
    """Grader Logic for Web: Generate or Fallback?"""
    print("---CONDITIONAL EDGE: DECIDE WEB NEXT STEP---")
    if state.get("web_grade") == "weak":
        print("-> Decision: Fallback Answer")
        return "fallback"
    else:
        print("-> Decision: Generate Answer from Web")
        return "generate"



def generate(state: State):
    """Node 7 & 8: Generate Final Answer"""
    print("---NODE: GENERATE ANSWER---")
    question = state.get("question", "")
    documents = state.get("kb_docs", [])
    source = state.get("source_used", "Unknown")

    if not documents:
        return {"generation": "I do not have clearance or information to answer this."}

    docs_text = "\n".join([doc.page_content for doc in documents])
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are Aegis-HR, a secure enterprise AI assistant. "
                   "Answer the question based ONLY on the provided context. If the context doesn't contain the answer, say 'I cannot answer this.'\n\n"
                   "Context:\n{context}"),
        ("human", "{question}")
    ])
    
    chain = prompt | model | StrOutputParser()
    answer = chain.invoke({"context": docs_text, "question": question})
    
    # Append the source to the answer so the user knows where it came from
    final_answer = f"{answer} \n\n*(Source: {source})*"
    
    return {"generation": final_answer}


def route_question(state:State):
    """
    Routes the user's question to either the knowledge base or web search based on the content of the question.
    """
    question = state.get("question","")
    source=router_chain.invoke({"question": question})
    if source.datasource=="web":
        return "web_search"
    else:
        return "retrieve_kb"

def decide_to_generate(state:State):
    """ 
    Decides whether to generate an answer based on the graded documents.
    """
    if state.get("kb_grade","")=="good":
        return "generate"
    else:
        return "web_search"




# ==========================================
# 4. BUILD THE AGENTIC GRAPH
# ==========================================
workflow = StateGraph(State)

# Add all Nodes
workflow.add_node("retrieve_kb", retrieve)
workflow.add_node("grade_documents", grade_documents)
workflow.add_node("web_search", web_search)
workflow.add_node("grade_web_documents", grade_web_documents) # Naya Node
workflow.add_node("fallback", fallback_generate)              # Naya Node
workflow.add_node("generate", generate)

# Routing Edge from Start
workflow.set_conditional_entry_point(
    route_question,
    {
        "retrieve_kb": "retrieve_kb",
        "web_search": "web_search"
    }
)

# KB Flow
workflow.add_edge("retrieve_kb", "grade_documents")
workflow.add_conditional_edges(
    "grade_documents",
    decide_to_generate,
    {
        "web_search": "web_search",
        "generate": "generate"
    }
)

# Web Flow (Ab seedha generate nahi jayega, pehle grade hoga)
workflow.add_edge("web_search", "grade_web_documents")
workflow.add_conditional_edges(
    "grade_web_documents",
    decide_web_generation,
    {
        "fallback": "fallback",
        "generate": "generate"
    }
)

# End points
workflow.add_edge("generate", END)
workflow.add_edge("fallback", END)




DB_URI = settings.DATABASE_URL
connection_pool = ConnectionPool(
    conninfo=DB_URI,
    max_size=20,
    kwargs={"autocommit": True}
)
memory = PostgresSaver(connection_pool)
memory.setup()
rag_app = workflow.compile(checkpointer=memory)








