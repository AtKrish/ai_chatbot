from services.query_rewrite import improve_query
from models.llm import llm

def ask_question(vector_db, user_query, chat_history):

    improved_query = improve_query(user_query)

    results = vector_db.similarity_search(improved_query, k=3)

    context = "\n\n".join([
        f"[KB: {doc.metadata.get('kb_id')} | Ticket: {doc.metadata.get('ticket_id')}]\n{doc.page_content}"
        for doc in results
    ])

    history = "\n".join([
        f"User: {chat['user']}\nAI: {chat['ai']}"
        for chat in chat_history[-3:]
    ])

    prompt = f"""
You are an IT support assistant.

Conversation History:
{history}

Context:
{context}

User Issue:
{user_query}

Provide clear step-by-step solution.
"""

    return llm.invoke(prompt)