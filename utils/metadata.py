import re

def extract_metadata(filename, text):
    kb_match = re.search(r'\bKB\d+\b', filename + " " + text)
    inc_match = re.search(r'\bINC\d+\b', filename + " " + text)
    author_match = re.search(r'Authored by\s+(.+)', text)
    modified_match = re.search(r'Last modified\s+(.+)', text)

    return {
        "kb_id": kb_match.group() if kb_match else "NOT AVAILABLE",
        "ticket_id": inc_match.group() if inc_match else "NOT AVAILABLE",
        "source": filename,
        "author": author_match.group(1).strip() if author_match else "NOT AVAILABLE",
        "last_modified": modified_match.group(1).strip() if modified_match else "NOT AVAILABLE"
    }
