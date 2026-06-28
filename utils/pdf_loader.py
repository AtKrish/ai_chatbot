import os
import fitz
from langchain_text_splitters import CharacterTextSplitter
from langchain_core.documents import Document
from utils.metadata import extract_metadata


def load_pdfs(folder_path):
    documents = []

    for file in os.listdir(folder_path):
        if not file.endswith(".pdf"):
            continue

        try:
            path = os.path.join(folder_path, file)
            print(f"Processing: {file}")

            doc = fitz.open(path)

            text = ""
            for page in doc:
                page_text = page.get_text("text")
                
                # fallback if empty
                if not isinstance(page_text, str) or not page_text.strip():
                    page_blocks = page.get_text("blocks")
                    page_text = " ".join([str(b) for b in page_blocks])

                text += page_text

            # ✅ Clean text
            text = text.replace("\n\n", "\n").strip()

            if not text:
                print(f"Skipped empty file: {file}")
                continue

            # ✅ Extract metadata
            metadata = extract_metadata(file, text)

            # ✅ Split text
            splitter = CharacterTextSplitter(
                chunk_size=800,
                chunk_overlap=150
            )
            chunks = splitter.split_text(text)

            # ✅ Convert to documents
            for chunk in chunks:
                documents.append(
                    Document(
                        page_content=chunk,
                        metadata=metadata
                    )
                )

        except Exception as e:
            print(f"Error processing {file}: {e}")

    print(f"Total documents created: {len(documents)}")

    return documents