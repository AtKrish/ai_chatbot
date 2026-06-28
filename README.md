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


C:\Users\H314512\Documents\My_app_phase1
├── .env
├── config.py
├── README.md
├── requirements.txt
├── test.py
├── uvicorn*.log / .pid files
├── .vscode
│   └── settings.json
├── app_streamlit
│   └── app.py
├── backend
│   ├── __init__.py
│   ├── main.py
│   └── routes
│       ├── __init__.py
│       └── chat.py
├── data
│   ├── INC2881482 – How to fix Mnemonics KB0128377.pdf
│   ├── KB0122449.pdf
│   ├── KB0126921.pdf
│   ├── KB0129671.pdf
│   └── KB0131367.pdf
├── frontend
│   ├── index.html
│   ├── script.js
│   └── styles.css
├── models
│   ├── __init__.py
│   ├── embeddings.py
│   └── llm.py
├── services
│   ├── __init__.py
│   ├── cache.py
│   ├── query_rewrite.py
│   └── rag_pipeline.py
├── utils
│   ├── __init__.py
│   ├── metadata.py
│   └── pdf_loader.py
└── vector_db
    ├── index.faiss
    ├── index.pkl
    └── faiss_index
        ├── index.faiss
        └── index.pkl
