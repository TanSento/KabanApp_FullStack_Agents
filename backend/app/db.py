import hashlib
import sqlite3
import uuid
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "kanban.db"

# Seed data uses suffixes; ensure_board generates IDs prefixed by board_id
SEED_COLUMN_SUFFIXES = [
    ("backlog", "Backlog", 0),
    ("discovery", "Discovery", 1),
    ("progress", "In Progress", 2),
    ("review", "Review", 3),
    ("done", "Done", 4),
]

SEED_CARD_DATA = [
    ("1", "backlog", "Align roadmap themes", "Draft quarterly themes with impact statements and metrics.", 0),
    ("2", "backlog", "Gather customer signals", "Review support tags, sales notes, and churn feedback.", 1),
    ("3", "discovery", "Prototype analytics view", "Sketch initial dashboard layout and key drill-downs.", 0),
    ("4", "progress", "Refine status language", "Standardize column labels and tone across the board.", 0),
    ("5", "progress", "Design card layout", "Add hierarchy and spacing for scanning dense lists.", 1),
    ("6", "review", "QA micro-interactions", "Verify hover, focus, and loading states.", 0),
    ("7", "done", "Ship marketing page", "Final copy approved and asset pack delivered.", 0),
    ("8", "done", "Close onboarding sprint", "Document release notes and share internally.", 1),
]


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


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


def _seed_board(conn: sqlite3.Connection, board_id: int) -> None:
    """Insert default columns and cards for a new board."""
    for col_suffix, col_title, col_pos in SEED_COLUMN_SUFFIXES:
        col_id = f"col-{board_id}-{col_suffix}"
        conn.execute(
            "INSERT INTO columns (id, board_id, title, position) VALUES (?, ?, ?, ?)",
            (col_id, board_id, col_title, col_pos),
        )
    for card_suffix, col_suffix, title, details, position in SEED_CARD_DATA:
        card_id = f"card-{board_id}-{card_suffix}"
        col_id = f"col-{board_id}-{col_suffix}"
        conn.execute(
            "INSERT INTO cards (id, column_id, title, details, position) VALUES (?, ?, ?, ?, ?)",
            (card_id, col_id, title, details, position),
        )


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
        "SELECT id FROM boards WHERE user_id = ? ORDER BY id LIMIT 1", (user_id,)
    ).fetchone()
    if row:
        return row["id"]
    cur = conn.execute(
        "INSERT INTO boards (user_id) VALUES (?)", (user_id,)
    )
    board_id = cur.lastrowid
    _seed_board(conn, board_id)
    conn.commit()
    return board_id


# -- User management --

def get_user_id(conn: sqlite3.Connection, username: str) -> int | None:
    row = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    return row["id"] if row else None


def register_user(conn: sqlite3.Connection, username: str, password: str) -> int | None:
    """Register a new user. Returns user_id or None if username already taken."""
    if not username or not password:
        return None
    existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if existing:
        return None
    password_hash = _hash_password(password)
    cur = conn.execute(
        "INSERT INTO users (username, password) VALUES (?, ?)",
        (username, password_hash),
    )
    conn.commit()
    return cur.lastrowid


def authenticate_user(conn: sqlite3.Connection, username: str, password: str) -> int | None:
    """Verify credentials against DB. Returns user_id or None."""
    row = conn.execute(
        "SELECT id, password FROM users WHERE username = ?", (username,)
    ).fetchone()
    if not row:
        return None
    stored = row["password"]
    # Support both plain-text (legacy seeded user) and hashed passwords
    if stored == password or stored == _hash_password(password):
        return row["id"]
    return None


# -- Board management --

def get_boards(conn: sqlite3.Connection, user_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT id, title FROM boards WHERE user_id = ? ORDER BY id",
        (user_id,),
    ).fetchall()
    return [{"id": row["id"], "title": row["title"]} for row in rows]


def create_board(conn: sqlite3.Connection, user_id: int, title: str) -> int:
    """Create a new board with default columns. Returns board_id."""
    cur = conn.execute(
        "INSERT INTO boards (user_id, title) VALUES (?, ?)", (user_id, title)
    )
    board_id = cur.lastrowid
    _seed_board(conn, board_id)
    conn.commit()
    return board_id


def rename_board(conn: sqlite3.Connection, board_id: int, user_id: int, title: str) -> bool:
    cur = conn.execute(
        "UPDATE boards SET title = ? WHERE id = ? AND user_id = ?",
        (title, board_id, user_id),
    )
    conn.commit()
    return cur.rowcount > 0


def delete_board(conn: sqlite3.Connection, board_id: int, user_id: int) -> bool:
    board = conn.execute(
        "SELECT id FROM boards WHERE id = ? AND user_id = ?", (board_id, user_id)
    ).fetchone()
    if not board:
        return False
    conn.execute(
        "DELETE FROM cards WHERE column_id IN (SELECT id FROM columns WHERE board_id = ?)",
        (board_id,),
    )
    conn.execute("DELETE FROM columns WHERE board_id = ?", (board_id,))
    conn.execute("DELETE FROM boards WHERE id = ?", (board_id,))
    conn.commit()
    return True


# -- Column management --

def create_column(conn: sqlite3.Connection, board_id: int, title: str, commit: bool = True) -> str | None:
    """Create a new column. Returns the new column_id or None if board not found."""
    board = conn.execute("SELECT id FROM boards WHERE id = ?", (board_id,)).fetchone()
    if not board:
        return None
    max_pos = conn.execute(
        "SELECT COALESCE(MAX(position), -1) AS mp FROM columns WHERE board_id = ?",
        (board_id,),
    ).fetchone()["mp"]
    col_id = f"col-{board_id}-{uuid.uuid4().hex[:8]}"
    conn.execute(
        "INSERT INTO columns (id, board_id, title, position) VALUES (?, ?, ?, ?)",
        (col_id, board_id, title, max_pos + 1),
    )
    if commit:
        conn.commit()
    return col_id


def delete_column(conn: sqlite3.Connection, board_id: int, column_id: str, commit: bool = True) -> bool:
    col = conn.execute(
        "SELECT id FROM columns WHERE id = ? AND board_id = ?", (column_id, board_id)
    ).fetchone()
    if not col:
        return False
    conn.execute("DELETE FROM cards WHERE column_id = ?", (column_id,))
    conn.execute("DELETE FROM columns WHERE id = ?", (column_id,))
    if commit:
        conn.commit()
    return True


# -- Board data --

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

    old_col = card["column_id"]
    conn.execute(
        "UPDATE cards SET position = position - 1 WHERE column_id = ? AND position > (SELECT position FROM cards WHERE id = ?)",
        (old_col, card_id),
    )
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
    conn.execute(
        "DELETE FROM cards WHERE column_id IN (SELECT id FROM columns WHERE board_id = ?)",
        (board_id,),
    )
    conn.execute("DELETE FROM columns WHERE board_id = ?", (board_id,))

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
