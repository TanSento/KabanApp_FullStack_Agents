# Database Design

## Overview

SQLite database with four tables. Created automatically on first startup if it does not exist.

## Schema

```
users
  id        INTEGER PRIMARY KEY AUTOINCREMENT
  username  TEXT NOT NULL UNIQUE
  password  TEXT NOT NULL

boards
  id        INTEGER PRIMARY KEY AUTOINCREMENT
  user_id   INTEGER NOT NULL -> users(id)
  title     TEXT NOT NULL DEFAULT 'My Board'

columns
  id        TEXT PRIMARY KEY          -- matches frontend IDs like "col-backlog"
  board_id  INTEGER NOT NULL -> boards(id)
  title     TEXT NOT NULL
  position  INTEGER NOT NULL          -- ordering within the board

cards
  id        TEXT PRIMARY KEY          -- matches frontend IDs like "card-1"
  column_id TEXT NOT NULL -> columns(id)
  title     TEXT NOT NULL
  details   TEXT NOT NULL DEFAULT ''
  position  INTEGER NOT NULL          -- ordering within the column
```

## Relationships

```
users 1--* boards
boards 1--* columns (ordered by position)
columns 1--* cards (ordered by position)
```

For the MVP, each user has exactly one board, but the schema supports multiple boards for future expansion.

## Key Design Decisions

- **TEXT primary keys for columns/cards**: The frontend generates IDs like `col-backlog` and `card-abc123`. Using TEXT keys means the database IDs match the frontend directly -- no mapping needed.
- **position column**: Integer field on both `columns` and `cards` to maintain drag-and-drop ordering. Moving a card updates positions within the affected column(s).
- **password storage**: For MVP, stored as plain text (hardcoded `user`/`password`). A future iteration would use hashed passwords.

## Migration Strategy

For the MVP, the database is created from scratch on first startup (no migration tooling). Tables are created via `CREATE TABLE IF NOT EXISTS` statements in the app initialization code. If the schema needs to change during development, the simplest approach is to delete the SQLite file and let it be recreated.

## API Response Shape

The `GET /api/board` endpoint will return data matching the frontend `BoardData` type:

```json
{
  "columns": [
    { "id": "col-backlog", "title": "Backlog", "cardIds": ["card-1", "card-2"] }
  ],
  "cards": {
    "card-1": { "id": "card-1", "title": "...", "details": "..." }
  }
}
```

The database rows are assembled into this shape at query time by joining `columns` and `cards`, ordered by their `position` fields.
