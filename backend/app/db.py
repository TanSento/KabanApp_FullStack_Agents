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
        CREATE TABLE IF NOT EXISTS card_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id TEXT NOT NULL REFERENCES cards(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            body TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS board_labels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            board_id INTEGER NOT NULL REFERENCES boards(id),
            name TEXT NOT NULL,
            color TEXT NOT NULL DEFAULT '#6366f1'
        );
        CREATE TABLE IF NOT EXISTS card_labels (
            card_id TEXT NOT NULL REFERENCES cards(id),
            label_id INTEGER NOT NULL REFERENCES board_labels(id),
            PRIMARY KEY (card_id, label_id)
        );
    """)
    # Migrations for existing databases
    for sql in [
        "ALTER TABLE cards ADD COLUMN due_date TEXT",
        "ALTER TABLE cards ADD COLUMN priority TEXT NOT NULL DEFAULT 'none'",
    ]:
        try:
            conn.execute(sql)
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists


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
        """SELECT c.id, c.column_id, c.title, c.details, c.position,
                  c.due_date, c.priority
           FROM cards c
           JOIN columns col ON c.column_id = col.id
           WHERE col.board_id = ?
           ORDER BY c.position""",
        (board_id,),
    ).fetchall()

    cards_by_column: dict[str, list[str]] = {}
    cards: dict[str, dict] = {}
    for row in cards_rows:
        card = {
            "id": row["id"],
            "title": row["title"],
            "details": row["details"],
            "due_date": row["due_date"],
            "priority": row["priority"] or "none",
        }
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


def create_card(conn: sqlite3.Connection, board_id: int, column_id: str, card_id: str, title: str, details: str = "", due_date: str | None = None, priority: str = "none", commit: bool = True) -> bool:
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
        "INSERT INTO cards (id, column_id, title, details, position, due_date, priority) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (card_id, column_id, title, details, max_pos + 1, due_date, priority),
    )
    if commit:
        conn.commit()
    return True


def update_card(conn: sqlite3.Connection, board_id: int, card_id: str, title: str, details: str, due_date: str | None = None, priority: str = "none", commit: bool = True) -> bool:
    cur = conn.execute(
        """UPDATE cards SET title = ?, details = ?, due_date = ?, priority = ?
           WHERE id = ? AND column_id IN (SELECT id FROM columns WHERE board_id = ?)""",
        (title, details, due_date, priority, card_id, board_id),
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


def reorder_columns(conn: sqlite3.Connection, board_id: int, column_ids: list[str]) -> bool:
    """Reorder columns by providing the desired order of column IDs."""
    existing = conn.execute(
        "SELECT id FROM columns WHERE board_id = ?", (board_id,)
    ).fetchall()
    existing_ids = {row["id"] for row in existing}
    if set(column_ids) != existing_ids:
        return False
    for position, col_id in enumerate(column_ids):
        conn.execute(
            "UPDATE columns SET position = ? WHERE id = ? AND board_id = ?",
            (position, col_id, board_id),
        )
    conn.commit()
    return True


def get_labels(conn: sqlite3.Connection, board_id: int) -> list[dict]:
    """Get all labels for a board."""
    rows = conn.execute(
        "SELECT id, name, color FROM board_labels WHERE board_id = ? ORDER BY id",
        (board_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def create_label(conn: sqlite3.Connection, board_id: int, name: str, color: str) -> dict:
    cur = conn.execute(
        "INSERT INTO board_labels (board_id, name, color) VALUES (?, ?, ?)",
        (board_id, name, color),
    )
    conn.commit()
    row = conn.execute("SELECT id, name, color FROM board_labels WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


def delete_label(conn: sqlite3.Connection, board_id: int, label_id: int) -> bool:
    cur = conn.execute(
        "DELETE FROM board_labels WHERE id = ? AND board_id = ?",
        (label_id, board_id),
    )
    conn.commit()
    return cur.rowcount > 0


def get_card_labels(conn: sqlite3.Connection, board_id: int, card_id: str) -> list[dict] | None:
    """Get labels for a specific card. Returns None if card doesn't belong to board."""
    card = conn.execute(
        """SELECT c.id FROM cards c
           JOIN columns col ON c.column_id = col.id
           WHERE c.id = ? AND col.board_id = ?""",
        (card_id, board_id),
    ).fetchone()
    if not card:
        return None
    rows = conn.execute(
        """SELECT bl.id, bl.name, bl.color
           FROM card_labels cl
           JOIN board_labels bl ON cl.label_id = bl.id
           WHERE cl.card_id = ?
           ORDER BY bl.id""",
        (card_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def set_card_label(conn: sqlite3.Connection, board_id: int, card_id: str, label_id: int) -> bool:
    """Add a label to a card. Returns False if card or label not found in board."""
    card = conn.execute(
        """SELECT c.id FROM cards c JOIN columns col ON c.column_id = col.id
           WHERE c.id = ? AND col.board_id = ?""",
        (card_id, board_id),
    ).fetchone()
    label = conn.execute(
        "SELECT id FROM board_labels WHERE id = ? AND board_id = ?",
        (label_id, board_id),
    ).fetchone()
    if not card or not label:
        return False
    conn.execute(
        "INSERT OR IGNORE INTO card_labels (card_id, label_id) VALUES (?, ?)",
        (card_id, label_id),
    )
    conn.commit()
    return True


def remove_card_label(conn: sqlite3.Connection, board_id: int, card_id: str, label_id: int) -> bool:
    card = conn.execute(
        """SELECT c.id FROM cards c JOIN columns col ON c.column_id = col.id
           WHERE c.id = ? AND col.board_id = ?""",
        (card_id, board_id),
    ).fetchone()
    if not card:
        return False
    cur = conn.execute(
        "DELETE FROM card_labels WHERE card_id = ? AND label_id = ?",
        (card_id, label_id),
    )
    conn.commit()
    return cur.rowcount > 0


def get_comments(conn: sqlite3.Connection, board_id: int, card_id: str) -> list[dict]:
    """Get comments for a card, verifying the card belongs to the board."""
    card = conn.execute(
        """SELECT c.id FROM cards c
           JOIN columns col ON c.column_id = col.id
           WHERE c.id = ? AND col.board_id = ?""",
        (card_id, board_id),
    ).fetchone()
    if not card:
        return None  # type: ignore
    rows = conn.execute(
        """SELECT cc.id, cc.body, cc.created_at, u.username
           FROM card_comments cc
           JOIN users u ON cc.user_id = u.id
           WHERE cc.card_id = ?
           ORDER BY cc.created_at ASC""",
        (card_id,),
    ).fetchall()
    return [{"id": r["id"], "body": r["body"], "created_at": r["created_at"], "username": r["username"]} for r in rows]


def add_comment(conn: sqlite3.Connection, board_id: int, card_id: str, user_id: int, body: str) -> dict | None:
    """Add a comment to a card. Returns comment dict or None if card not found."""
    card = conn.execute(
        """SELECT c.id FROM cards c
           JOIN columns col ON c.column_id = col.id
           WHERE c.id = ? AND col.board_id = ?""",
        (card_id, board_id),
    ).fetchone()
    if not card:
        return None
    cur = conn.execute(
        "INSERT INTO card_comments (card_id, user_id, body) VALUES (?, ?, ?)",
        (card_id, user_id, body),
    )
    conn.commit()
    row = conn.execute(
        """SELECT cc.id, cc.body, cc.created_at, u.username
           FROM card_comments cc JOIN users u ON cc.user_id = u.id
           WHERE cc.id = ?""",
        (cur.lastrowid,),
    ).fetchone()
    return {"id": row["id"], "body": row["body"], "created_at": row["created_at"], "username": row["username"]}


def delete_comment(conn: sqlite3.Connection, board_id: int, card_id: str, comment_id: int, user_id: int) -> bool:
    """Delete a comment. Returns False if not found or not owned by user."""
    cur = conn.execute(
        """DELETE FROM card_comments
           WHERE id = ? AND card_id = ? AND user_id = ?
             AND card_id IN (
               SELECT c.id FROM cards c
               JOIN columns col ON c.column_id = col.id
               WHERE col.board_id = ?
             )""",
        (comment_id, card_id, user_id, board_id),
    )
    conn.commit()
    return cur.rowcount > 0


def search_cards(conn: sqlite3.Connection, board_id: int, query: str) -> list[dict]:
    """Search cards by title or details within a board."""
    rows = conn.execute(
        """SELECT c.id, c.title, c.details, c.column_id, c.due_date, c.priority
           FROM cards c
           JOIN columns col ON c.column_id = col.id
           WHERE col.board_id = ?
             AND (LOWER(c.title) LIKE LOWER(?) OR LOWER(c.details) LIKE LOWER(?))
           ORDER BY c.position""",
        (board_id, f"%{query}%", f"%{query}%"),
    ).fetchall()
    return [dict(row) for row in rows]


def get_board_stats(conn: sqlite3.Connection, board_id: int) -> dict:
    """Return summary statistics for a board."""
    total = conn.execute(
        "SELECT COUNT(*) AS n FROM cards WHERE column_id IN (SELECT id FROM columns WHERE board_id = ?)",
        (board_id,),
    ).fetchone()["n"]

    by_priority = {}
    for row in conn.execute(
        """SELECT COALESCE(priority, 'none') AS priority, COUNT(*) AS n
           FROM cards WHERE column_id IN (SELECT id FROM columns WHERE board_id = ?)
           GROUP BY priority""",
        (board_id,),
    ).fetchall():
        by_priority[row["priority"]] = row["n"]

    today = __import__("datetime").date.today().isoformat()
    overdue = conn.execute(
        """SELECT COUNT(*) AS n FROM cards
           WHERE column_id IN (SELECT id FROM columns WHERE board_id = ?)
             AND due_date IS NOT NULL AND due_date < ?""",
        (board_id, today),
    ).fetchone()["n"]

    return {"total": total, "by_priority": by_priority, "overdue": overdue}


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
