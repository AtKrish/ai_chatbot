import streamlit as st
from langchain_community.vectorstores import FAISS
from models.embeddings import embeddings
from services.rag_pipeline import ask_question
from utils.pdf_loader import load_pdfs
from config import PDF_FOLDER, INDEX_PATH
import os

st.title("💬 KB AI Assistant")

if "vector_db" not in st.session_state:
    if os.path.exists(INDEX_PATH):
        st.session_state.vector_db = FAISS.load_local(
            INDEX_PATH,
            embeddings,
            allow_dangerous_deserialization=True
        )
    else:
        docs = load_pdfs(PDF_FOLDER)
        db = FAISS.from_documents(docs, embeddings)
        db.save_local(INDEX_PATH)
        st.session_state.vector_db = db

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

user_input = st.chat_input("Describe your issue...")

if user_input:
    st.chat_message("user").write(user_input)

    response = ask_question(
        st.session_state.vector_db,
        user_input,
        st.session_state.chat_history
    )

    st.session_state.chat_history.append({
        "user": user_input,
        "ai": response
    })

    st.chat_message("assistant").write(response)