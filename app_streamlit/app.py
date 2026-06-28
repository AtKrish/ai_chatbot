import os
import streamlit as st
from langchain_community.vectorstores import FAISS
from models.embeddings import embeddings
from utils.pdf_loader import load_pdfs
from services.rag_pipeline import ask_question
from config import PDF_FOLDER, INDEX_PATH

st.title("💬 AI IT Support Assistant")

# Ensure folder exists
os.makedirs(INDEX_PATH, exist_ok=True)

# Initialize session
if "vector_db" not in st.session_state:
    if os.path.exists(os.path.join(INDEX_PATH, "index.faiss")):
        st.session_state.vector_db = FAISS.load_local(
            INDEX_PATH,
            embeddings,
            allow_dangerous_deserialization=True
        )
        st.success("Loaded existing vector DB")
    else:
        st.warning("Creating vector DB...")
        docs = load_pdfs(PDF_FOLDER)

        if not docs:
            st.error("No documents found!")
            st.stop()

        db = FAISS.from_documents(docs, embeddings)
        db.save_local(INDEX_PATH)

        st.session_state.vector_db = db
        st.success("Vector DB created!")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

user_input = st.text_input("Enter your issue:")

if st.button("Ask") and user_input:
    response = ask_question(
        st.session_state.vector_db,
        user_input,
        st.session_state.chat_history
    )

    st.session_state.chat_history.append({
        "user": user_input,
        "ai": response
    })

for chat in st.session_state.chat_history:
    st.write(f"🧑‍💻 You: {chat['user']}")
    st.write(f"🤖 AI: {chat['ai']}")