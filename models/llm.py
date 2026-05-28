from langchain_ollama import OllamaLLM
from config import MODEL_NAME

llm = OllamaLLM(model=MODEL_NAME, num_ctx=512)