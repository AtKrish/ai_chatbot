import re

def extract_metadata(filename, text):
    kb_match = re.search(r'\bKB\d+\b', filename + " " + text)
    inc_match = re.search(r'\bINC\d+\b', filename + " " + text)

    return {
        "kb_id": kb_match.group() if kb_match else "NOT AVAILABLE",
        "ticket_id": inc_match.group() if inc_match else "NOT AVAILABLE",
        "source": filename
    }