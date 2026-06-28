import os
import re
import streamlit as st
import fitz  # PyMuPDF

from langchain_ollama import OllamaLLM
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import CharacterTextSplitter
from langchain_core.documents import Document

# ------------------------
# CONFIG
# ------------------------
PDF_FOLDER = "data"
INDEX_PATH = "faiss_index"

# ------------------------
# INIT MODELS
# ------------------------
llm = OllamaLLM(model="mistral")

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# ------------------------
# SESSION STATE INIT
# ------------------------
if "vector_db" not in st.session_state:
    st.session_state.vector_db = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ------------------------
# METADATA EXTRACTION
# ------------------------
def extract_metadata(filename, text):
    kb_match = re.search(r'\bKB\d+\b', filename + " " + text)
    inc_match = re.search(r'\bINC\d+\b', filename + " " + text)

    return {
        "kb_id": kb_match.group() if kb_match else "NOT AVAILABLE",
        "ticket_id": inc_match.group() if inc_match else "NOT AVAILABLE",
        "source": filename
    }

# ------------------------
# LOAD PDFs
# ------------------------
def load_pdfs(folder_path):
    documents = []

    for file in os.listdir(folder_path):
        if file.endswith(".pdf"):
            file_path = os.path.join(folder_path, file)

            doc = fitz.open(file_path)
            text = ""

            for page in doc:
                page_text = page.get_text("text")
                text += page_text

            text = text.replace("\n\n", "\n")

            metadata = extract_metadata(file, text)

            splitter = CharacterTextSplitter(
                chunk_size=800,
                chunk_overlap=150
            )

            chunks = splitter.split_text(text)

            for chunk in chunks:
                documents.append(
                    Document(
                        page_content=chunk,
                        metadata=metadata
                    )
                )

    return documents

# ------------------------
# CREATE / LOAD VECTOR DB
# ------------------------
def create_vector_db():
    docs = load_pdfs(PDF_FOLDER)
    vector_db = FAISS.from_documents(docs, embeddings)
    vector_db.save_local(INDEX_PATH)
    return vector_db

def load_vector_db():
    return FAISS.load_local(
        INDEX_PATH,
        embeddings,
        allow_dangerous_deserialization=True
    )

# ------------------------
# ADD NEW KB
# ------------------------
def add_new_kb(uploaded_file, vector_db):
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")

    text = ""
    for page in doc:
        page_text = page.get_text("text")
        text += page_text

    text = text.replace("\n\n", "\n")

    metadata = extract_metadata(uploaded_file.name, text)

    splitter = CharacterTextSplitter(chunk_size=800, chunk_overlap=150)
    chunks = splitter.split_text(text)

    new_docs = [
        Document(page_content=chunk, metadata=metadata)
        for chunk in chunks
    ]

    vector_db.add_documents(new_docs)
    vector_db.save_local(INDEX_PATH)

# ------------------------
# QUERY IMPROVEMENT
# ------------------------
def improve_query(user_query):
    prompt = f"""
Rewrite the IT issue clearly with better technical detail.

User Input:
{user_query}

Improved Query:
"""
    return llm.invoke(prompt).strip()

# ------------------------
# RAG WITH CHAT MEMORY
# ------------------------
def ask_question(vector_db, user_query):

    improved_query = improve_query(user_query)

    results = vector_db.similarity_search(improved_query, k=3)

    if not results:
        return "No relevant KB found."

    context = "\n\n".join([
        f"[KB: {doc.metadata.get('kb_id','NOT AVAILABLE')} | "
        f"Ticket: {doc.metadata.get('ticket_id','NOT AVAILABLE')}]\n"
        f"{doc.page_content}"
        for doc in results
    ])

    history = "\n".join([
        f"User: {chat['user']}\nAI: {chat['ai']}"
        for chat in st.session_state.chat_history[-3:]
    ])

    prompt = f"""
You are an IT support assistant.

Conversation History:
{history}

Context:
{context}

User Issue:
{user_query}

Instructions:
- Continue the conversation naturally
- Use previous context if relevant
- Provide clear step-by-step solution
- If KB or Ticket not available, say "NOT AVAILABLE"

Answer:
"""

    response = llm.invoke(prompt)

    # Save chat
    st.session_state.chat_history.append({
        "user": user_query,
        "ai": response
    })

    return response

# ------------------------
# STREAMLIT UI
# ------------------------
st.set_page_config(page_title="Enterprise KB AI Chat")

st.title("💬 Enterprise KB AI Assistant")

# Load DB
if st.session_state.vector_db is None:
    if os.path.exists(INDEX_PATH):
        st.session_state.vector_db = load_vector_db()
    else:
        with st.spinner("Indexing KB articles..."):
            st.session_state.vector_db = create_vector_db()
        st.success("KB Indexed!")

# Upload new KB
uploaded_file = st.file_uploader("Upload new KB article", type=["pdf"])

if uploaded_file:
    add_new_kb(uploaded_file, st.session_state.vector_db)
    st.success("New KB added successfully!")

# Display chat history
for chat in st.session_state.chat_history:
    st.chat_message("user").write(chat["user"])
    st.chat_message("assistant").write(chat["ai"])

# Chat input
user_input = st.chat_input("Describe your issue...")

if user_input:
    st.chat_message("user").write(user_input)

    with st.spinner("Analyzing..."):
        response = ask_question(st.session_state.vector_db, user_input)

    st.chat_message("assistant").write(response)
