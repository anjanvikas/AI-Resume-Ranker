# AI Resume Ranker 🚀

An intelligent, full-stack resume ranking system that leverages semantic embeddings and Large Language Models (LLMs) to automate the candidate screening process.

## 📺 Demo

<video src="https://github.com/anjanvikas/AI-Resume-Ranker/raw/main/uploads/JobrankerDemo.mp4" width="100%" controls></video>

## 🌟 Key Features

- **2-Stage AI Pipeline**: 
    1. **Semantic Screening**: Uses `sentence-transformers` to compute cosine similarity between resumes and job descriptions for rapid initial ranking.
    2. **Deep Evaluation**: Passes top-ranked candidates to **Claude AI (Anthropic)** for rigorous, structured scoring across dimensions like skills match, experience relevance, and achievements.
- **Enterprise-Grade Security**: 
    - **Google OAuth2 Integration** for secure user authentication.
    - **Encrypted Storage**: Per-user Claude API keys are stored using `AES-256 (Fernet)` encryption in the database.
- **Async Processing**: Background job architecture with real-time progress polling for bulk resume analysis.
- **Modern UI/UX**: 
    - Smooth Single-Page Application (SPA) with drag-and-drop file uploads.
    - Dark/Light mode support with user preference persistence.
    - Interactive onboarding tutorial.
- **Developer Ready**: Fully containerized with **Docker** and **Docker Compose**.

## 🛠️ Tech Stack

- **Backend**: Python, FastAPI, Anthropic API, Sentence-Transformers
- **Frontend**: Vanilla JavaScript, CSS3 (Modern Flexbox/Grid)
- **Database**: SQLite with per-user data isolation
- **Security**: Authlib (OAuth2), Cryptography (Fernet)
- **DevOps**: Docker, Docker Compose

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Docker (optional)
- A Google Cloud project (for OAuth login)
- An Anthropic Claude API Key

### Setup Instructions

1. **Clone the repository**:
   ```bash
   git clone https://github.com/anjanvikas/AI-Resume-Ranker.git
   cd AI-Resume-Ranker
   ```

2. **Configure Environment Variables**:
   Copy the example environment file and fill in your credentials.
   ```bash
   cp .env.example .env
   ```
   *Follow the instructions in `.env.example` to set up your Google OAuth client and security keys.*

3. **Run with Docker (Recommended)**:
   ```bash
   docker-compose up --build
   ```
   The app will be available at `http://localhost:8000`.

4. **Run Locally (Development)**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```

## 📊 Pipeline Architecture

1. **Extraction**: Resumes (PDF/DOCX) are parsed and converted to structured text.
2. **Shortlisting**: Resumes are converted into high-dimensional vectors. A cosine similarity score is calculated against the Job Description.
3. **LLM Evaluation**: Claude AI analyzes the shortlisted resumes to provide detailed qualitative feedback, key strengths, gaps, and a composite score.

## 🔒 Security

This application prioritizes security. User-provided LLM keys are encrypted at rest using a dedicated `ENCRYPTION_KEY` that never leaves your environment. Authentication is handled via Google's OpenID Connect, ensuring that user sessions are secure and verified.

---
*Built with ❤️ by Anjan Vikas*
