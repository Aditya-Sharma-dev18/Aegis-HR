import os
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from langchain_community.embeddings import CohereEmbeddings
from langchain_core.documents import Document
from langchain_community.vectorstores import Pinecone as PineconeVectorStore

# Load environment variables
load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")

print("🚀 Starting Enterprise RBAC Ingestion...")

# 1. Initialize Pinecone
pc = Pinecone(api_key=PINECONE_API_KEY)

# Create the index automatically if it doesn't exist (FDE automation)
if PINECONE_INDEX_NAME not in pc.list_indexes().names():
    print(f"📦 Creating new Pinecone index: {PINECONE_INDEX_NAME}")
    pc.create_index(
        name=PINECONE_INDEX_NAME,
        dimension=1024, # Cohere embedding dimension
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )
else:
    print(f"✅ Index {PINECONE_INDEX_NAME} already exists.")

# 2. Setup Cohere Embeddings
# We use Cohere for embeddings because it is incredibly fast and production-ready
embeddings = CohereEmbeddings(cohere_api_key=COHERE_API_KEY, model="embed-english-v3.0")

# 3. Create Sample HR Documents with RBAC Metadata (The Digital Locks)
hr_documents = [
    # General Policy - Visible to everyone (Clearance Level 1)
    Document(
        page_content="Every employee is entitled to 20 days of paid annual leave. Sick leave is capped at 10 days per year.",
        metadata={"source": "employee_handbook", "clearance": 1, "department": "all"}
    ),
    Document(
        page_content="The company follows a hybrid work model. Employees can work remotely for 2 days a week.",
        metadata={"source": "employee_handbook", "clearance": 1, "department": "all"}
    ),
    
    # HR Admin Policy - Visible only to HR (Clearance Level 4)
    Document(
        page_content="If an employee is on a Performance Improvement Plan (PIP), their annual bonus is automatically forfeited.",
        metadata={"source": "hr_runbook", "clearance": 4, "department": "hr"}
    ),
    
    # Executive Policy - Visible only to C-Suite/Board (Clearance Level 5)
    Document(
        page_content="In the event of an acquisition, the CEO and Board members will receive accelerated vesting of 100% of their stock options.",
        metadata={"source": "executive_severance", "clearance": 5, "department": "board"}
    )
]

# 4. Upload to Pinecone
print("🔒 Tagging documents with RBAC metadata and uploading to Pinecone...")
vectorstore = PineconeVectorStore.from_documents(
    documents=hr_documents,
    embedding=embeddings,
    index_name=PINECONE_INDEX_NAME
)

print("✅ Ingestion Complete! Data is now secured with digital locks in Pinecone.")