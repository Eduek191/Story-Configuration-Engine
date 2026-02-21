import aiosqlite
from pathlib import Path

DATABASE_PATH = Path(__file__).parent.parent / "database.db"


async def init_database():
    """Initialize SQLite database with schema"""

    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Manuscripts table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS manuscripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                word_count INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Characters table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS characters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manuscript_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                mentions INTEGER DEFAULT 0,
                first_appearance INTEGER,
                attributes TEXT,
                relationships TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (manuscript_id) REFERENCES manuscripts(id) ON DELETE CASCADE
            )
        """)

        # Source references table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS source_references (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER NOT NULL,
                sentence TEXT NOT NULL,
                paragraph INTEGER,
                context TEXT,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
        """)

        # Timeline events table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS timeline_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manuscript_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                description TEXT NOT NULL,
                timestamp TEXT,
                paragraph INTEGER,
                characters_involved TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (manuscript_id) REFERENCES manuscripts(id) ON DELETE CASCADE
            )
        """)

        # Inconsistencies table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS inconsistencies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manuscript_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                severity TEXT NOT NULL,
                description TEXT NOT NULL,
                evidence TEXT,
                suggestion TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (manuscript_id) REFERENCES manuscripts(id) ON DELETE CASCADE
            )
        """)

        # Create indexes for better query performance
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_characters_manuscript ON characters(manuscript_id)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_timeline_manuscript ON timeline_events(manuscript_id)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_inconsistencies_manuscript ON inconsistencies(manuscript_id)"
        )

        await db.commit()
        print("Database initialized successfully")


async def get_db():
    """Get database connection"""
    db = await aiosqlite.connect(DATABASE_PATH)
    try:
        yield db
    finally:
        await db.close()