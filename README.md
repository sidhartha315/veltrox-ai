# Veltrox AI — Intelligent Knowledge & Task Assistant

Veltrox AI is a Generative AI-powered chatbot that answers general questions
and uses Retrieval-Augmented Generation (RAG) to answer questions about
uploaded PDF documents.

## Features

- AI-powered conversational chatbot
- PDF document upload and text extraction
- Text chunking and embedding generation
- Semantic retrieval using ChromaDB
- Context-aware responses using a local LLM
- REST API built with FastAPI

## Technology Stack

- Python
- FastAPI
- Ollama
- Llama 3.2 (1B)
- nomic-embed-text
- ChromaDB
- PyPDF
- HTML, CSS, JavaScript

## Architecture

PDF Upload → Text Extraction → Chunking → Embeddings
→ ChromaDB → Relevant Context Retrieval → LLM Response

## Project Structure

    veltrox-ai/
    ├── backend/
    │   ├── main.py
    │   └── requirements.txt
    ├── frontend/
    │   ├── index.html
    │   ├── script.js
    │   └── style.css
    ├── .gitignore
    └── README.md

## Prerequisites

- Python 3.10 or newer
- Ollama
- Git

## Setup

### 1. Clone the repository

    git clone https://github.com/sidhartha315/veltrox-ai.git
    cd veltrox-ai

### 2. Install Ollama models

    ollama pull llama3.2:1b
    ollama pull nomic-embed-text

### 3. Install Python dependencies

    pip install -r backend/requirements.txt

### 4. Configure environment variables

Create a .env file in the backend directory with:

    OLLAMA_BASE_URL=http://localhost:11434
    OLLAMA_MODEL=llama3.2:1b
    OLLAMA_EMBED_MODEL=nomic-embed-text

Keep .env private. Never commit credentials or private documents.

### 5. Start the backend

From the project root, run:

    python -m uvicorn backend.main:app

### 6. Start the frontend

Open a separate terminal:

    cd frontend
    python -m http.server 5500

Open http://127.0.0.1:5500/index.html in your browser.

Ensure Ollama is running before starting the chatbot.

## Future Improvements

- Faster response generation
- Improved document retrieval
- Conversation memory
- AI agent and tool integration
- Deployment with a permanent public URL

## Author

Rachamalla Sidhartha

GitHub: https://github.com/sidhartha315