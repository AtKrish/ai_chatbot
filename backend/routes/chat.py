from fastapi import APIRouter
from pydantic import BaseModel
from services.rag_pipeline import ask_question
router = APIRouter()

class Query(BaseModel):
    query: str

# dummy in-memory
chat_history = []
vector_db = None

@router.post("/ask")
def ask(q: Query):
    global chat_history, vector_db

    answer = ask_question(vector_db, q.query, chat_history)

    chat_history.append({"user": q.query, "ai": answer})

    return {"answer": answer}