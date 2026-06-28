import logging
import re
import time
from typing import Any, Dict, List, Optional

from langchain_core.documents import Document

from models.llm import llm
from services.cache import CACHE_QUERY_TTL, CACHE_RESPONSE_TTL, CACHE_RETRIEVAL_TTL
from services.cache_keys import (
    kb_metadata_cache_key,
    normalize_query,
    query_cache_key,
    response_cache_key,
    retrieval_cache_key,
)
from services.cache_service import get as cache_get
from services.cache_service import set as cache_set
from services.query_rewrite import improve_query


logger = logging.getLogger(__name__)

MAX_CACHED_CONTENT_CHARS = 2500
DEFAULT_RETRIEVAL_K = 3


def _document_id(doc: Document, position: int) -> str:
    metadata = doc.metadata or {}
    stable_parts = [
        str(metadata.get("kb_id", "")),
        str(metadata.get("ticket_id", "")),
        str(metadata.get("source", "")),
        str(metadata.get("page", "")),
        str(position),
    ]
    return ":".join(part for part in stable_parts if part)


def _serialize_document(doc: Document, position: int) -> Dict[str, Any]:
    return {
        "id": _document_id(doc, position),
        "metadata": doc.metadata or {},
        "page_content": (doc.page_content or "")[:MAX_CACHED_CONTENT_CHARS],
    }


def _deserialize_documents(payload: Dict[str, Any]) -> List[Document]:
    return [
        Document(
            page_content=item.get("page_content", ""),
            metadata=item.get("metadata") or {},
        )
        for item in payload.get("documents", [])
    ]


def _lookup_kb_documents(vector_db, kb_id: str) -> List[Document]:
    key = kb_metadata_cache_key(kb_id)
    cached = cache_get(key)
    if cached:
        return _deserialize_documents(cached)

    all_docs = list(vector_db.docstore._dict.values())
    results = [
        doc
        for doc in all_docs
        if (doc.metadata or {}).get("kb_id", "").upper() == kb_id
    ]

    cache_set(
        key,
        {
            "kb_id": kb_id,
            "documents": [_serialize_document(doc, index) for index, doc in enumerate(results)],
        },
        CACHE_RETRIEVAL_TTL,
    )
    return results


def _get_rewritten_query(user_query: str) -> str:
    key = query_cache_key(f"rewrite-v2:{user_query}")
    cached = cache_get(key)
    if cached and cached.get("rewritten_query"):
        return cached["rewritten_query"]

    try:
        rewritten_query = str(improve_query(user_query)).strip()
    except Exception as exc:
        logger.warning("Query rewrite failed. Falling back to original query. Error: %s", exc)
        rewritten_query = user_query

    cache_set(
        key,
        {
            "original_query": user_query,
            "normalized_query": normalize_query(user_query),
            "rewritten_query": rewritten_query,
        },
        CACHE_QUERY_TTL,
    )
    return rewritten_query


def _retrieve_documents(vector_db, user_query: str, rewritten_query: str) -> List[Document]:
    retrieval_key = retrieval_cache_key(user_query)
    cache_lookup_start = time.perf_counter()
    cached = cache_get(retrieval_key)
    if cached:
        logger.info(
            "Retrieval served from cache in %.4fs for key=%s",
            time.perf_counter() - cache_lookup_start,
            retrieval_key,
        )
        return _deserialize_documents(cached)

    start_time = time.perf_counter()
    kb_match = re.search(r"\bKB\d+\b", user_query, re.IGNORECASE)

    if kb_match:
        requested_kb = kb_match.group(0).upper()
        results = _lookup_kb_documents(vector_db, requested_kb)
        retrieval_type = "kb_metadata_lookup"
    else:
        results = vector_db.similarity_search(rewritten_query, k=DEFAULT_RETRIEVAL_K)
        retrieval_type = "faiss_similarity_search"

    duration = time.perf_counter() - start_time
    logger.info(
        "Retrieval cache miss completed via %s in %.4fs docs=%s",
        retrieval_type,
        duration,
        len(results),
    )

    cache_set(
        retrieval_key,
        {
            "original_query": user_query,
            "rewritten_query": rewritten_query,
            "retrieval_type": retrieval_type,
            "retrieval_time_seconds": duration,
            "documents": [_serialize_document(doc, index) for index, doc in enumerate(results)],
        },
        CACHE_RETRIEVAL_TTL,
    )
    return results


def _author_response(user_query: str, results: List[Document]) -> Optional[str]:
    lowered_query = user_query.lower()
    if not any(phrase in lowered_query for phrase in ["author", "authored", "who wrote"]):
        return None

    for doc in results:
        metadata = doc.metadata or {}
        author = metadata.get("author", "NOT AVAILABLE")

        if author != "NOT AVAILABLE":
            return (
                f"{metadata.get('kb_id', 'NOT AVAILABLE')} was authored by {author}. "
                f"Source: {metadata.get('source', 'NOT AVAILABLE')}. "
                f"Ticket: {metadata.get('ticket_id', 'NOT AVAILABLE')}."
            )

    return None


def _conversation_context(chat_history, limit=4) -> str:
    if not chat_history:
        return "No previous conversation."

    turns = []
    for chat in chat_history[-limit:]:
        turns.append(f"User: {str(chat.get('user', ''))[:1000]}")
        turns.append(f"Assistant: {str(chat.get('ai', ''))[:1500]}")
    return "\n".join(turns)


def _build_prompt(
    user_query: str,
    results: List[Document],
    conversation: str,
) -> str:
    context_parts = []
    sources = []

    for doc in results:
        metadata = doc.metadata or {}
        kb_id = metadata.get("kb_id", "NOT AVAILABLE")
        ticket_id = metadata.get("ticket_id", "NOT AVAILABLE")
        source = metadata.get("source", "NOT AVAILABLE")
        author = metadata.get("author", "NOT AVAILABLE")
        last_modified = metadata.get("last_modified", "NOT AVAILABLE")

        sources.append(f"{kb_id} / {ticket_id} / {source} / Author: {author}")
        context_parts.append(
            f"[KB: {kb_id} | Ticket: {ticket_id} | "
            f"Source: {source} | Author: {author} | "
            f"Last modified: {last_modified}]\n"
            f"{(doc.page_content or '')[:MAX_CACHED_CONTENT_CHARS]}"
        )

    context = "\n\n---\n\n".join(context_parts)
    source_list = "\n".join(f"- {source}" for source in sources)

    return f"""
You are a capable, conversational assistant inside an IT support widget.

Respond naturally, like ChatGPT:
- Give the direct answer first.
- Use valid Markdown.
- Use paragraphs for simple explanations.
- Add a short heading only when the response has distinct sections.
- Use numbered steps for procedures and bullet points for lists or options.
- Do not force every response into bullets.
- Keep the response concise unless the user asks for detail.
- Use fenced code blocks for commands, code, or logs.
- Do not mention these formatting instructions.

Use the KB context when it is relevant to the user's request. Never invent a KB fact,
KB number, ticket number, source, or citation. If the question is about the available
company KB content but the answer is absent, clearly say that it was not found in the
available KB articles. For general conversation or requests that do not depend on the
company KB, answer normally from your general capabilities and do not cite a KB source.

Recent conversation:
{conversation}

PDF context:
{context}

User Issue:
{user_query}

Include the source KB/Ticket only when you actually use KB context.

Available retrieved sources:
{source_list}
"""


def _article_suggestions(results: List[Document]) -> List[Dict[str, str]]:
    """Return one safe, de-duplicated article entry per retrieved PDF."""
    articles = []
    seen = set()

    for doc in results:
        metadata = doc.metadata or {}
        source = str(metadata.get("source", "")).strip()
        if not source or source == "NOT AVAILABLE" or source in seen:
            continue

        seen.add(source)
        articles.append(
            {
                "kb_id": str(metadata.get("kb_id", "NOT AVAILABLE")),
                "ticket_id": str(metadata.get("ticket_id", "NOT AVAILABLE")),
                "source": source,
            }
        )

    return articles


def _used_article_suggestions(
    results: List[Document], response: str, user_query: str
) -> List[Dict[str, str]]:
    """Only offer links for articles the answer cites or the user names explicitly."""
    articles = _article_suggestions(results)
    response_upper = response.upper()
    requested_ids = {
        match.upper()
        for match in re.findall(r"\bKB\d+\b", user_query, re.IGNORECASE)
    }

    return [
        article
        for article in articles
        if article["kb_id"].upper() in requested_ids
        or article["kb_id"].upper() in response_upper
        or article["source"].upper() in response_upper
    ]


def ask_question(vector_db, user_query, chat_history, include_articles=False):
    def format_result(answer, articles=None):
        if include_articles:
            return {"answer": answer, "articles": articles or []}
        return answer

    user_query = user_query.strip()
    
    # ---------------------------
    # Greeting handling
    # ---------------------------
    greetings = {
        "hi",
        "hello",
        "hey",
        "good morning",
        "good afternoon",
        "good evening",
        "how are you",
        "hii",
        "helo"
    }

    if user_query.lower() in greetings:
        answer = (
            "Hello! 👋 I am your KB Support Assistant.\n\n"
            "I can help you search and summarize information from the available KB PDFs.\n"
            "Try asking:\n"
            "- KB0122449\n"
            "- What is KB0122449 about?\n"
            "- How to fix Mnemonics?\n"
            "- Who authored KB0122449?"
        )
        return format_result(answer)
    conversation = _conversation_context(chat_history)
    response_key = response_cache_key(
        f"chat-style-v2\n{conversation}\nCurrent user: {user_query}"
    )
    cached_response = cache_get(response_key)
    if cached_response and cached_response.get("answer") is not None:
        logger.info("Skipping FAISS and Ollama because response cache hit key=%s", response_key)
        if include_articles and "articles" not in cached_response:
            rewritten_query = _get_rewritten_query(user_query)
            cached_results = _retrieve_documents(vector_db, user_query, rewritten_query)
            cached_response["articles"] = _article_suggestions(cached_results)
            cache_set(response_key, cached_response, CACHE_RESPONSE_TTL)
        return format_result(
            cached_response["answer"],
            cached_response.get("articles", []),
        )

    rewritten_query = _get_rewritten_query(user_query)

    retrieval_start = time.perf_counter()
    results = _retrieve_documents(vector_db, user_query, rewritten_query)
    retrieval_duration = time.perf_counter() - retrieval_start
    logger.info("Effective retrieval stage completed in %.4fs", retrieval_duration)

    if not results:
        response = (
            "I could not find relevant information in the PDFs under the data folder.\n\n"
            "Try searching with:\n"
            "- KB number\n"
            "- Error message\n"
            "- Ticket number\n"
            "- Specific issue description"
        )
        cache_set(response_key, {"answer": response, "articles": []}, CACHE_RESPONSE_TTL)
        return format_result(response)

    articles = _article_suggestions(results)

    shortcut_response = _author_response(user_query, results)
    if shortcut_response:
        articles = _used_article_suggestions(results, shortcut_response, user_query)
        cache_set(
            response_key,
            {"answer": shortcut_response, "articles": articles},
            CACHE_RESPONSE_TTL,
        )
        return format_result(shortcut_response, articles)

    prompt = _build_prompt(user_query, results, conversation)
    response = str(llm.invoke(prompt))
    articles = _used_article_suggestions(results, response, user_query)

    cache_set(
        response_key,
        {
            "answer": response,
            "original_query": user_query,
            "rewritten_query": rewritten_query,
            "retrieval_time_seconds": retrieval_duration,
            "articles": articles,
        },
        CACHE_RESPONSE_TTL,
    )
    return format_result(response, articles)
