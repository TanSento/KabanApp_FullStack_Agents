# Kanban Studio

A minimal Project Management MVP web application featuring a fast Next.js frontend, a FastAPI backend using SQLite, all packaged into a Docker container. The application includes a Kanban board with drag-and-drop support, session authentication, and an AI chat running on OpenRouter for intelligent board manipulation.

## Technical Stack

- Frontend: Next.js 16 (React 19), Tailwind CSS 4, @dnd-kit
- Backend: Python 3.13, FastAPI, SQLite
- Infrastructure: Docker, Docker Compose
- AI Integration: OpenRouter with openai/gpt-oss-120b

## Prerequisites

- Docker and Docker Compose
- OpenRouter API key

## Setup

1. Create a `.env` file in the root directory and add your OpenRouter API key:
   OPENROUTER_API_KEY=your_openrouter_api_key

2. Start the application using the scripts provided for your OS:
   - Mac: `./scripts/start_mac.sh`
   - Linux: `./scripts/start_linux.sh`
   - Windows: `.\scripts\start_windows.ps1`

3. The application will be available at `http://localhost:8000`.
   Log in with the hardcoded credentials:
   - Username: `user`
   - Password: `password`

4. To stop the application:
   - Mac: `./scripts/stop_mac.sh`
   - Linux: `./scripts/stop_linux.sh`
   - Windows: `.\scripts\start_windows.ps1`

## Project Structure

- `frontend/`: The Next.js frontend codebase, compiled to static files during Docker build.
- `backend/`: The FastAPI application logic and SQLite database structure.
- `docs/`: Design documents, database schemas, and architectural plans.
- `scripts/`: Platform-specific start and stop orchestration scripts.
