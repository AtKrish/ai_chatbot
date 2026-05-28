from models.llm import llm

def improve_query(query):
    prompt = f"""
Rewrite the IT issue clearly with better technical detail.

User Input:
{query}

Improved Query:
"""
    return llm.invoke(prompt).strip()