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

## Database Inspection

To inspect the database while the app is running:

```bash
# List all users and passwords
docker exec pm_antigravity-app-1 python3 -c "
import sqlite3
c = sqlite3.connect('/app/data/kanban.db')
rows = c.execute('SELECT id, username, password FROM users').fetchall()
print(f'{len(rows)} users:')
for r in rows:
    print(f'  {r[0]}: {r[1]} -> {r[2]}')
"

# Count users only
docker exec pm_antigravity-app-1 python3 -c "
import sqlite3
c = sqlite3.connect('/app/data/kanban.db')
print(c.execute('SELECT COUNT(*) FROM users').fetchone()[0], 'users')
"
```

Note: passwords are stored as plain text for the default `user` account and SHA-256 hashed for registered users.

## Project Structure

- `frontend/`: The Next.js frontend codebase, compiled to static files during Docker build.
- `backend/`: The FastAPI application logic and SQLite database structure.
- `docs/`: Design documents, database schemas, and architectural plans.
- `scripts/`: Platform-specific start and stop orchestration scripts.
