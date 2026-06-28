import hashlib
import re


def normalize_query(query: str) -> str:
    return re.sub(r"\s+", " ", query.strip().lower())


def query_hash(query: str) -> str:
    return hashlib.sha256(normalize_query(query).encode("utf-8")).hexdigest()


def query_cache_key(query: str) -> str:
    return f"rag:query:{query_hash(query)}"


def retrieval_cache_key(query: str) -> str:
    return f"rag:retrieval:{query_hash(query)}"


def response_cache_key(query: str) -> str:
    return f"rag:response:{query_hash(query)}"


def kb_metadata_cache_key(kb_id: str) -> str:
    return f"rag:kb_metadata:{kb_id.strip().upper()}"
