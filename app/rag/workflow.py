from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.output_parsers import StrOutputParser
from langchain_tavily import TavilySearch
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate

from app.schemas import routequery, gradedocuments
from app.rag.retriever import get_secure_vectorstore
from app.rag.state import State
from app.core.config import settings


# ==========================================
# 1. LLM & CHAIN DEFINITIONS (Module-level, no I/O)
# ==========================================
model = ChatGroq(
    model="openai/gpt-oss-120b",
    api_key=settings.GROQ_API_KEY,
)

question_router = model.with_structured_output(routequery)
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

generate_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are Aegis-HR, a secure enterprise AI assistant. "
               "Answer the question based ONLY on the provided context. If the context doesn't contain the answer, say 'I cannot answer this.'\n\n"
               "Context:\n{context}"),
    ("human", "{question}")
])
generate_chain = generate_prompt | model | StrOutputParser()


# ==========================================
# 2. ASYNC GRAPH NODES
# ==========================================
async def retrieve(state: State):
    """Node: Fetch from Pinecone with RBAC Security"""
    print("---NODE: RETRIEVE FROM PINECONE---")
    question = state.get("question", "")
    clearance = state.get("user_clearance", 1)

    vectorstore = get_secure_vectorstore()
    rbac_filter = {"clearance": {"$lte": clearance}}

    # Async similarity search — does NOT block the event loop
    documents = await vectorstore.asimilarity_search(
        query=question,
        k=3,
        filter=rbac_filter
    )

    trace = state.get("trace", [])[:]  # Copy to avoid mutating shared state
    trace.append("Searched Pinecone KB")

    return {"kb_docs": documents, "question": question, "trace": trace, "source_used": "Knowledge Base"}


async def web_search(state: State):
    """Node: Performs an async web search via Tavily"""
    print("---NODE: WEB SEARCH---")
    question = state.get("question", "")
    trace = state.get("trace", [])[:]
    trace.append("Web search step completed")

    tool = TavilySearch(
        max_results=5,
        include_answers=True,
        include_raw_content=True,
        api_key=settings.TAVILY_API_KEY.get_secret_value()
    )
    docs = await tool.ainvoke({"query": question})

    web_results = "\n".join(
        d.get("content", "") for d in docs if isinstance(d, dict) and d.get("content")
    )
    web_docs = [Document(page_content=web_results)] if web_results else []

    return {"web_docs": web_docs, "trace": trace, "source_used": "Web"}


async def grade_documents(state: State):
    """Node: Grades KB documents for relevance"""
    print("---NODE: GRADE KB DOCUMENTS---")
    question = state.get("question", "")
    documents = state.get("kb_docs", [])
    trace = state.get("trace", [])[:]
    filtered_docs = []

    for doc in documents:
        score = await grader_chain.ainvoke({"document": doc.page_content, "question": question})
        if score.binary_score == "yes":
            filtered_docs.append(doc)
        else:
            print("Document filtered out due to irrelevance")

    if not filtered_docs:
        print("---DECISION: ALL DOCS WEAK, SWITCH TO WEB---")
        trace.append("KB docs were irrelevant. Switching to Web.")
        return {"kb_docs": [], "kb_grade": "weak", "trace": trace}
    else:
        trace.append("KB docs passed grading.")
        return {"kb_docs": filtered_docs, "kb_grade": "good", "trace": trace}


async def grade_web_documents(state: State):
    """Node: Grades web search results for relevance"""
    print("---NODE: GRADE WEB DOCUMENTS---")
    question = state.get("question", "")
    documents = state.get("web_docs", [])
    trace = state.get("trace", [])[:]
    filtered_docs = []

    for doc in documents:
        score = await grader_chain.ainvoke({"document": doc.page_content, "question": question})
        if score.binary_score == "yes":
            filtered_docs.append(doc)

    if not filtered_docs:
        print("---DECISION: WEB DOCS ALSO WEAK, GO TO FALLBACK---")
        trace.append("Web docs were irrelevant. Moving to Fallback.")
        return {"web_docs": [], "web_grade": "weak", "trace": trace}
    else:
        trace.append("Web docs passed grading.")
        return {"web_docs": filtered_docs, "web_grade": "good", "trace": trace}


async def fallback_generate(state: State):
    """Node: Fallback Answer when both KB and Web fail"""
    print("---NODE: FALLBACK ANSWER---")
    fallback_text = ("I do not have sufficient information in the secure Knowledge Base "
                     "or the open Web to answer this question accurately.")
    return {"generation": f"{fallback_text} \n\n*(Source: Fallback)*"}


async def generate(state: State):
    """Node: Generate Final Answer from graded documents"""
    print("---NODE: GENERATE ANSWER---")
    question = state.get("question", "")
    # Try KB docs first; if empty (web flow), use web_docs
    documents = state.get("kb_docs", []) or state.get("web_docs", [])
    source = state.get("source_used", "Unknown")

    if not documents:
        return {"generation": "I do not have clearance or information to answer this."}

    docs_text = "\n".join([doc.page_content for doc in documents])

    # Async LLM call — does NOT block the event loop
    answer = await generate_chain.ainvoke({"context": docs_text, "question": question})

    final_answer = f"{answer} \n\n*(Source: {source})*"
    return {"generation": final_answer}


# ==========================================
# 3. ROUTING FUNCTIONS (Conditional Edges)
# ==========================================
async def route_question(state: State):
    """Routes the user's question to KB or Web Search"""
    question = state.get("question", "")
    source = await router_chain.ainvoke({"question": question})
    if source.datasource == "web":
        return "web_search"
    else:
        return "retrieve_kb"


def decide_to_generate(state: State):
    """Grader Logic for KB: Generate or fallback to Web?"""
    if state.get("kb_grade", "") == "good":
        return "generate"
    else:
        return "web_search"


def decide_web_generation(state: State):
    """Grader Logic for Web: Generate or Fallback?"""
    if state.get("web_grade") == "weak":
        return "fallback"
    else:
        return "generate"


# ==========================================
# 4. BUILD THE AGENTIC GRAPH (Uncompiled)
# ==========================================
def build_rag_app(checkpointer=None):
    """
    Builds and compiles the LangGraph workflow.
    Accepts an optional checkpointer (e.g., AsyncPostgresSaver) for memory.
    Called from FastAPI lifespan to inject the async checkpointer.
    """
    workflow = StateGraph(State)

    # Add all Nodes
    workflow.add_node("retrieve_kb", retrieve)
    workflow.add_node("grade_documents", grade_documents)
    workflow.add_node("web_search", web_search)
    workflow.add_node("grade_web_documents", grade_web_documents)
    workflow.add_node("fallback", fallback_generate)
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

    # Web Flow
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

    return workflow.compile(checkpointer=checkpointer)
