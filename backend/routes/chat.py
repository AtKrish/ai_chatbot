import os

from fastapi import APIRouter, HTTPException, Query as FastAPIQuery
from fastapi.responses import FileResponse
from pydantic import BaseModel
from config import INDEX_PATH, PDF_FOLDER
from services.rag_pipeline import ask_question

router = APIRouter()

class Query(BaseModel):
    query: str

# dummy in-memory
chat_history = []
vector_db = None


def get_vector_db():
    global vector_db

    if vector_db is None:
        index_file = os.path.join(INDEX_PATH, "index.faiss")
        from langchain_community.vectorstores import FAISS
        from models.embeddings import embeddings

        if os.path.exists(index_file):
            vector_db = FAISS.load_local(
                INDEX_PATH,
                embeddings,
                allow_dangerous_deserialization=True
            )
        else:
            from utils.pdf_loader import load_pdfs

            docs = load_pdfs(PDF_FOLDER)
            if not docs:
                raise HTTPException(
                    status_code=503,
                    detail=f"No PDF content found in {PDF_FOLDER}."
                )

            os.makedirs(INDEX_PATH, exist_ok=True)
            vector_db = FAISS.from_documents(docs, embeddings)
            vector_db.save_local(INDEX_PATH)

    return vector_db


@router.post("/ask")
def ask(q: Query):
    result = ask_question(get_vector_db(), q.query, chat_history, include_articles=True)
    answer = result["answer"]

    chat_history.append({"user": q.query, "ai": answer})

    return result


@router.get("/kb/{source:path}")
def get_kb_article(source: str, download: bool = FastAPIQuery(False)):
    pdf_root = os.path.abspath(PDF_FOLDER)
    requested_path = os.path.abspath(os.path.join(pdf_root, source))

    if not requested_path.startswith(pdf_root + os.sep):
        raise HTTPException(status_code=400, detail="Invalid KB article path.")

    if not os.path.isfile(requested_path):
        raise HTTPException(status_code=404, detail="KB article not found.")

    if not requested_path.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF KB articles can be served.")

    disposition = "attachment" if download else "inline"
    return FileResponse(
        requested_path,
        media_type="application/pdf",
        filename=os.path.basename(requested_path),
        content_disposition_type=disposition,
    )
