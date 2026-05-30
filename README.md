# ai_chatbot
http://localhost:8000/widget
uvicorn backend.main:app --reload --port 8001
uvicorn backend.main:app --reload

py -3.11 -m venv venv311
venv311\Scripts\activate
pip install -r requirements.txt

🧠 FINAL ARCHITECTURE
Frontend (HTML/JS)
        ↓
FastAPI (/ask)
        ↓
RAG Pipeline
        ↓
FAISS (PDF knowledge)
        ↓
Ollama (LLM)
