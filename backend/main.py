import os
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pypdf import PdfReader
import chromadb
import ollama


# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv()

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434"
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "llama3.2:1b"
)

OLLAMA_EMBED_MODEL = os.getenv(
    "OLLAMA_EMBED_MODEL",
    "nomic-embed-text"
)


# =========================================================
# OLLAMA CLIENT
# =========================================================

ollama_client = ollama.Client(
    host=OLLAMA_BASE_URL
)


# =========================================================
# FASTAPI
# =========================================================

app = FastAPI(
    title="Veltrox AI",
    version="1.0.0"
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# CHROMADB
# =========================================================

chroma_client = chromadb.PersistentClient(
    path="./chroma_db"
)

# New collection name so old incompatible embeddings
# do not interfere with this version.
collection = chroma_client.get_or_create_collection(
    name="veltrox_ollama_documents"
)


# =========================================================
# REQUEST MODEL
# =========================================================

class ChatRequest(BaseModel):
    message: str


# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():
    return {
        "status": "success",
        "message": "Veltrox AI backend is running",
        "model": OLLAMA_MODEL,
        "embedding_model": OLLAMA_EMBED_MODEL,
        "documents": collection.count()
    }


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
def health():

    try:

        models = ollama_client.list()

        return {
            "status": "ok",
            "ollama": True,
            "model": OLLAMA_MODEL,
            "embedding_model": OLLAMA_EMBED_MODEL,
            "documents": collection.count(),
            "models": str(models)
        }

    except Exception as e:

        return {
            "status": "error",
            "ollama": False,
            "error": str(e)
        }


# =========================================================
# CREATE EMBEDDING
# =========================================================

def create_embedding(text: str):

    response = ollama_client.embeddings(
        model=OLLAMA_EMBED_MODEL,
        prompt=text
    )

    return response["embedding"]


# =========================================================
# NORMAL OLLAMA CHAT
# =========================================================

def normal_chat(message: str):

    response = ollama_client.chat(
        model=OLLAMA_MODEL,
        messages=[
            {
                "role": "user",
                "content": message
            }
        ]
    )

    return response["message"]["content"]


# =========================================================
# RAG CHAT
# =========================================================

def rag_chat(message: str):

    # Create embedding for user question
    question_embedding = create_embedding(message)

    document_count = collection.count()

    # Safety check
    if document_count == 0:
        return normal_chat(message)
# Search relevant chunks
    results = collection.query(
        query_embeddings=[
            question_embedding
        ],
        n_results=min(3, document_count)
    )

    documents = results.get(
        "documents",
        [[]]
    )[0]

    if not documents:
        return normal_chat(message)

    context = "\n\n".join(documents)

    prompt = f"""
You are Veltrox AI, an intelligent knowledge and task assistant.

The user has uploaded a resume/document.

Use the document information below to answer the user's question.

DOCUMENT INFORMATION:
{context}

USER QUESTION:
{message}

RULES:

1. Answer using the document when the question is about the document.
2. Do not invent personal information.
3. If the requested information is not in the document, say:
   "I couldn't find that information in the uploaded document."
4. Keep the answer clear and useful.
5. If the question is general and unrelated to the document,
   answer normally.
"""

    response = ollama_client.chat(
        model=OLLAMA_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response["message"]["content"]


# =========================================================
# CHAT ENDPOINT
# =========================================================

@app.post("/chat")
def chat(request: ChatRequest):

    message = request.message.strip()

    if not message:

        return {
            "response": "Please enter a message."
        }

    try:

        if collection.count() > 0:

            answer = rag_chat(message)

        else:

            answer = normal_chat(message)

        return {
            "response": answer
        }

    except Exception as e:

        print("CHAT ERROR:", repr(e))

        return {
            "error": True,
            "detail": str(e)
        }


# =========================================================
# PDF UPLOAD
# =========================================================

@app.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...)
):

    try:

        # Check file type
        if not file.filename.lower().endswith(".pdf"):

            return {
                "error": True,
                "message": "Please upload a PDF file."
            }

        # Read PDF
        reader = PdfReader(file.file)

        text = ""

        for page in reader.pages:

            page_text = page.extract_text()

            if page_text:

                text += page_text + "\n"

        # Check extracted text
        if not text.strip():

            return {
                "error": True,
                "message": "Could not extract text from this PDF."
            }

        # =================================================
        # CHUNKING
        # =================================================

        chunk_size = 800
        overlap = 100

        chunks = []

        start = 0

        while start < len(text):

            end = start + chunk_size

            chunk = text[start:end].strip()

            if chunk:

                chunks.append(chunk)

            start = end - overlap

        # =================================================
        # STORE CHUNKS
        # =================================================

        for index, chunk in enumerate(chunks):

            embedding = create_embedding(chunk)

            collection.add(
                ids=[
                    str(uuid.uuid4())
                ],
                embeddings=[
                    embedding
                ],
                documents=[
                    chunk
                ],
                metadatas=[
                    {
                        "filename": file.filename,
                        "chunk": index
                    }
                ]
            )
            return {
            "error": False,
            "filename": file.filename,
            "pages": len(reader.pages),
            "chunks": len(chunks),
            "message": "PDF uploaded and stored successfully."
        }

    except Exception as e:

        print("UPLOAD ERROR:", repr(e))

        return {
            "error": True,
            "detail": str(e)
        }


# =========================================================
# CLEAR DOCUMENTS
# =========================================================

@app.delete("/clear-documents")
def clear_documents():

    global collection

    try:

        existing = collection.get()

        ids = existing.get("ids", [])

        if ids:

            collection.delete(
                ids=ids
            )

        return {
            "message": "All uploaded documents were cleared."
        }

    except Exception as e:

        return {
            "error": True,
            "detail": str(e)
        }