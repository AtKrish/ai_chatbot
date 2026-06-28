from langchain_ollama import OllamaLLM
from config import MODEL_NAME

llm = OllamaLLM(
    model=MODEL_NAME,
    num_ctx=2048,
    num_predict=220,
    temperature=0.1,
    keep_alive="10m",
)
