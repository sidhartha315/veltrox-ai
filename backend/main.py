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
    version="1.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "https://angle-brands-displays-replication.trycloudflare.com",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# CHROMADB
# =========================================================

chroma_client = chromadb.PersistentClient(
    path="./chroma_db"
)

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
        "llm_model": OLLAMA_MODEL,
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
            "llm_model": OLLAMA_MODEL,
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
# DOCUMENT LIST
# =========================================================

@app.get("/documents")
def documents():

    try:

        result = collection.get(
            include=["documents", "metadatas"]
        )

        return {
            "count": collection.count(),
            "documents": result.get("documents", []),
            "metadatas": result.get("metadatas", [])
        }

    except Exception as e:

        return {
            "error": True,
            "detail": str(e)
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
# NORMAL CHAT
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

    # -----------------------------------------------------
    # 1. Convert question into embedding
    # -----------------------------------------------------

    question_embedding = create_embedding(message)


    # -----------------------------------------------------
    # 2. Check documents
    # -----------------------------------------------------

    document_count = collection.count()

    if document_count == 0:

        return normal_chat(message)


    # -----------------------------------------------------
    # 3. Retrieve relevant chunks
    # -----------------------------------------------------

    results = collection.query(

        query_embeddings=[
            question_embedding
        ],

        n_results=min(
            5,
            document_count
        )
    )


    documents = results.get(
        "documents",
        [[]]
    )[0]


    distances = results.get(
        "distances",
        [[]]
    )[0]


    # -----------------------------------------------------
    # DEBUG INFORMATION
    # -----------------------------------------------------

    print("\n================ RAG SEARCH ================")

    print("QUESTION:")
    print(message)

    print("\nRETRIEVED CHUNKS:")

    for i, document in enumerate(documents):

        distance = (
            distances[i]
            if i < len(distances)
            else "N/A"
        )

        print(
            f"\n--- CHUNK {i + 1} "
            f"(distance: {distance}) ---"
        )

        print(document[:500])

    print("\n============================================\n")


    # -----------------------------------------------------
    # 4. No useful documents
    # -----------------------------------------------------

    if not documents:

        return normal_chat(message)


    # -----------------------------------------------------
    # 5. Combine retrieved context
    # -----------------------------------------------------

    context_parts = []

    for i, document in enumerate(documents):

        context_parts.append(
            f"""
DOCUMENT CHUNK {i + 1}:

{document}
"""
        )


    context = "\n".join(
        context_parts
    )


    # -----------------------------------------------------
    # 6. RAG PROMPT
    # -----------------------------------------------------

    prompt = f"""
You are Veltrox AI, an intelligent knowledge and task assistant.

The user uploaded a personal document.

Your job is to answer questions using the document context
provided below.

================ DOCUMENT CONTEXT ================

{context}

================ END DOCUMENT CONTEXT =============


USER QUESTION:

{message}


IMPORTANT RULES:

1. Carefully search ALL provided document chunks before answering.

2. If the answer exists anywhere in the document context,
   answer using that information.

3. Do not say that information is missing just because it
   is not present in the first chunk.

4. Do not invent personal information.

5. For questions about the user's education, projects,
   skills, CGPA, college, certifications, or experience,
   use the uploaded document.

6. If the requested information genuinely does not exist
   in the provided document context, say:

   "I couldn't find that information in the uploaded document."

7. Give a direct and concise answer.

8. When explaining a project, include the project name,
   purpose, technologies, and important details if they
   are available in the document.

ANSWER:
"""


    # -----------------------------------------------------
    # 7. Generate answer using Ollama
    # -----------------------------------------------------

    response = ollama_client.chat(
    model=OLLAMA_MODEL,
    messages=[
        {
            "role": "user",
            "content": prompt
        }
    ],
    options={
        "num_predict": 40,
        "num_ctx": 1024,
        "temperature": 0.3 
    }
)


    return response["message"]["content"]
# =========================================================
# CHAT API
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

        print(
            "CHAT ERROR:",
            repr(e)
        )

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

        # -------------------------------------------------
        # Check file type
        # -------------------------------------------------

        if not file.filename.lower().endswith(".pdf"):

            return {
                "error": True,
                "message": "Please upload a PDF file."
            }


        # -------------------------------------------------
        # Read PDF
        # -------------------------------------------------

        reader = PdfReader(file.file)

        text = ""


        for page in reader.pages:

            page_text = page.extract_text()

            if page_text:

                text += page_text + "\n"


        # -------------------------------------------------
        # Check extracted text
        # -------------------------------------------------

        if not text.strip():

            return {
                "error": True,
                "message":
                "Could not extract text from this PDF."
            }


        # -------------------------------------------------
        # Remove old chunks of same file
        # -------------------------------------------------

        existing = collection.get(
            where={
                "filename": file.filename
            }
        )

        existing_ids = existing.get(
            "ids",
            []
        )


        if existing_ids:

            collection.delete(
                ids=existing_ids
            )


        # -------------------------------------------------
        # Improved chunking
        # -------------------------------------------------

        chunk_size = 1200
        overlap = 200

        chunks = []

        start = 0


        while start < len(text):

            end = start + chunk_size

            chunk = text[
                start:end
            ].strip()


            if chunk:

                chunks.append(chunk)


            start = end - overlap


        # -------------------------------------------------
        # Create embeddings + store
        # -------------------------------------------------

        for index, chunk in enumerate(chunks):

            embedding = create_embedding(
                chunk
            )


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
                        "filename":
                        file.filename,

                        "chunk":
                        index
                    }
                ]
            )


        # -------------------------------------------------
        # Success
        # -------------------------------------------------

        return {

            "error": False,

            "filename":
            file.filename,

            "pages":
            len(reader.pages),

            "chunks":
            len(chunks),
            "message":
            "PDF uploaded and stored successfully."
        }


    except Exception as e:

        print(
            "UPLOAD ERROR:",
            repr(e)
        )

        return {

            "error": True,

            "detail":
            str(e)
        }


# =========================================================
# CLEAR DOCUMENTS
# =========================================================

@app.delete("/clear-documents")
def clear_documents():

    try:

        existing = collection.get()

        ids = existing.get(
            "ids",
            []
        )


        if ids:

            collection.delete(
                ids=ids
            )


        return {
            "message":
            "All uploaded documents were cleared."
        }


    except Exception as e:

        return {
            "error": True,
            "detail": str(e)
        }