from models.llm import llm

def improve_query(query):
    prompt = f"""
Rewrite the user's message as one concise knowledge-base search query.
Preserve KB numbers, incident numbers, product names, and error messages exactly.
Return only the rewritten search query. Do not answer the question and do not use Markdown.

User Query:
{query}
"""
    return llm.invoke(prompt).strip()
