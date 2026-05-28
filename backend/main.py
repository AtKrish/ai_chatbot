import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from fastapi import FastAPI
from backend.routes.chat import router as chat_router

app = FastAPI()

app.include_router(chat_router)