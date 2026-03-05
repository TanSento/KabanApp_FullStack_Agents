import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "kanban.db"

SEED_COLUMNS = [
    ("col-backlog", "Backlog", 0),
    ("col-discovery", "Discovery", 1),
    ("col-progress", "In Progress", 2),
    ("col-review", "Review", 3),
    ("col-done", "Done", 4),
]

SEED_CARDS = [
    ("card-1", "col-backlog", "Align roadmap themes", "Draft quarterly themes with impact statements and metrics.", 0),
    ("card-2", "col-backlog", "Gather customer signals", "Review support tags, sales notes, and churn feedback.", 1),
    ("card-3", "col-discovery", "Prototype analytics view", "Sketch initial dashboard layout and key drill-downs.", 0),
    ("card-4", "col-progress", "Refine status language", "Standardize column labels and tone across the board.", 0),
    ("card-5", "col-progress", "Design card layout", "Add hierarchy and spacing for scanning dense lists.", 1),
    ("card-6", "col-review", "QA micro-interactions", "Verify hover, focus, and loading states.", 0),
    ("card-7", "col-done", "Ship marketing page", "Final copy approved and asset pack delivered.", 0),
    ("card-8", "col-done", "Close onboarding sprint", "Document release notes and share internally.", 1),
]


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS boards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            title TEXT NOT NULL DEFAULT 'My Board'
        );
        CREATE TABLE IF NOT EXISTS columns (
            id TEXT PRIMARY KEY,
            board_id INTEGER NOT NULL REFERENCES boards(id),
            title TEXT NOT NULL,
            position INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS cards (
            id TEXT PRIMARY KEY,
            column_id TEXT NOT NULL REFERENCES columns(id),
            title TEXT NOT NULL,
            details TEXT NOT NULL DEFAULT '',
            position INTEGER NOT NULL
        );
    """)


def ensure_user(conn: sqlite3.Connection, username: str, password: str) -> int:
    row = conn.execute(
        "SELECT id FROM users WHERE username = ?", (username,)
    ).fetchone()
    if row:
        return row["id"]
    cur = conn.execute(
        "INSERT INTO users (username, password) VALUES (?, ?)",
        (username, password),
    )
    conn.commit()
    return cur.lastrowid


def ensure_board(conn: sqlite3.Connection, user_id: int) -> int:
    row = conn.execute(
        "SELECT id FROM boards WHERE user_id = ?", (user_id,)
    ).fetchone()
    if row:
        return row["id"]
    cur = conn.execute(
        "INSERT INTO boards (user_id) VALUES (?)", (user_id,)
    )
    board_id = cur.lastrowid
    for col_id, title, position in SEED_COLUMNS:
        conn.execute(
            "INSERT INTO columns (id, board_id, title, position) VALUES (?, ?, ?, ?)",
            (col_id, board_id, title, position),
        )
    for card_id, col_id, title, details, position in SEED_CARDS:
        conn.execute(
            "INSERT INTO cards (id, column_id, title, details, position) VALUES (?, ?, ?, ?, ?)",
            (card_id, col_id, title, details, position),
        )
    conn.commit()
    return board_id


def get_board(conn: sqlite3.Connection, board_id: int) -> dict:
    cols = conn.execute(
        "SELECT id, title FROM columns WHERE board_id = ? ORDER BY position",
        (board_id,),
    ).fetchall()

    cards_rows = conn.execute(
        """SELECT c.id, c.column_id, c.title, c.details, c.position
           FROM cards c
           JOIN columns col ON c.column_id = col.id
           WHERE col.board_id = ?
           ORDER BY c.position""",
        (board_id,),
    ).fetchall()

    cards_by_column: dict[str, list[str]] = {}
    cards: dict[str, dict] = {}
    for row in cards_rows:
        card = {"id": row["id"], "title": row["title"], "details": row["details"]}
        cards[row["id"]] = card
        cards_by_column.setdefault(row["column_id"], []).append(row["id"])

    columns = []
    for col in cols:
        columns.append({
            "id": col["id"],
            "title": col["title"],
            "cardIds": cards_by_column.get(col["id"], []),
        })

    return {"columns": columns, "cards": cards}


def rename_column(conn: sqlite3.Connection, board_id: int, column_id: str, title: str, commit: bool = True) -> bool:
    cur = conn.execute(
        "UPDATE columns SET title = ? WHERE id = ? AND board_id = ?",
        (title, column_id, board_id),
    )
    if commit:
        conn.commit()
    return cur.rowcount > 0


def create_card(conn: sqlite3.Connection, board_id: int, column_id: str, card_id: str, title: str, details: str = "", commit: bool = True) -> bool:
    col = conn.execute(
        "SELECT id FROM columns WHERE id = ? AND board_id = ?",
        (column_id, board_id),
    ).fetchone()
    if not col:
        return False
    max_pos = conn.execute(
        "SELECT COALESCE(MAX(position), -1) AS mp FROM cards WHERE column_id = ?",
        (column_id,),
    ).fetchone()["mp"]
    conn.execute(
        "INSERT INTO cards (id, column_id, title, details, position) VALUES (?, ?, ?, ?, ?)",
        (card_id, column_id, title, details, max_pos + 1),
    )
    if commit:
        conn.commit()
    return True


def update_card(conn: sqlite3.Connection, board_id: int, card_id: str, title: str, details: str, commit: bool = True) -> bool:
    cur = conn.execute(
        """UPDATE cards SET title = ?, details = ?
           WHERE id = ? AND column_id IN (SELECT id FROM columns WHERE board_id = ?)""",
        (title, details, card_id, board_id),
    )
    if commit:
        conn.commit()
    return cur.rowcount > 0


def delete_card(conn: sqlite3.Connection, board_id: int, card_id: str, commit: bool = True) -> bool:
    cur = conn.execute(
        """DELETE FROM cards
           WHERE id = ? AND column_id IN (SELECT id FROM columns WHERE board_id = ?)""",
        (card_id, board_id),
    )
    if commit:
        conn.commit()
    return cur.rowcount > 0


def move_card(conn: sqlite3.Connection, board_id: int, card_id: str, target_column_id: str, position: int, commit: bool = True) -> bool:
    # Verify card and target column belong to this board
    card = conn.execute(
        """SELECT c.id, c.column_id FROM cards c
           JOIN columns col ON c.column_id = col.id
           WHERE c.id = ? AND col.board_id = ?""",
        (card_id, board_id),
    ).fetchone()
    if not card:
        return False
    target_col = conn.execute(
        "SELECT id FROM columns WHERE id = ? AND board_id = ?",
        (target_column_id, board_id),
    ).fetchone()
    if not target_col:
        return False

    # Remove from old position
    old_col = card["column_id"]
    conn.execute(
        "UPDATE cards SET position = position - 1 WHERE column_id = ? AND position > (SELECT position FROM cards WHERE id = ?)",
        (old_col, card_id),
    )
    # Insert at new position
    conn.execute(
        "UPDATE cards SET position = position + 1 WHERE column_id = ? AND position >= ?",
        (target_column_id, position),
    )
    conn.execute(
        "UPDATE cards SET column_id = ?, position = ? WHERE id = ?",
        (target_column_id, position, card_id),
    )
    if commit:
        conn.commit()
    return True


def bulk_update(conn: sqlite3.Connection, board_id: int, board_data: dict) -> None:
    """Replace the entire board state. Used for AI-driven batch changes."""
    # Delete existing cards and columns for this board
    conn.execute(
        "DELETE FROM cards WHERE column_id IN (SELECT id FROM columns WHERE board_id = ?)",
        (board_id,),
    )
    conn.execute("DELETE FROM columns WHERE board_id = ?", (board_id,))

    # Insert new columns and cards
    for pos, col in enumerate(board_data["columns"]):
        conn.execute(
            "INSERT INTO columns (id, board_id, title, position) VALUES (?, ?, ?, ?)",
            (col["id"], board_id, col["title"], pos),
        )
        for card_pos, card_id in enumerate(col["cardIds"]):
            card = board_data["cards"][card_id]
            conn.execute(
                "INSERT INTO cards (id, column_id, title, details, position) VALUES (?, ?, ?, ?, ?)",
                (card_id, col["id"], card["title"], card.get("details", ""), card_pos),
            )
    conn.commit()
