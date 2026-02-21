"""
Database layer using SQLite
Handles all database operations for the Story Consistency Engine
"""

import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Any
import json


class Database:
    def __init__(self, db_path: str = "database.db"):
        self.db_path = db_path
        self.conn = None
        self.initialize_connection()

    def initialize_connection(self):
        """Initialize database connection"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def initialize_tables(self):
        """Create all necessary database tables"""
        cursor = self.conn.cursor()

        # Manuscripts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS manuscripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                file_path TEXT,
                status TEXT DEFAULT 'pending',
                word_count INTEGER,
                uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                processed_at DATETIME
            )
        """)

        # Characters table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS characters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manuscript_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                first_mention TEXT,
                mention_count INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (manuscript_id) REFERENCES manuscripts(id) ON DELETE CASCADE
            )
        """)

        # Character attributes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS character_attributes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER NOT NULL,
                attribute_type TEXT NOT NULL,
                attribute_value TEXT NOT NULL,
                source_location TEXT,
                confidence_score REAL,
                first_mentioned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
        """)

        # Character mentions table (for source references)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS character_mentions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER NOT NULL,
                chapter INTEGER,
                paragraph INTEGER,
                sentence_text TEXT,
                context TEXT,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
        """)

        # Timeline events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS timeline_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manuscript_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                description TEXT NOT NULL,
                character_id INTEGER,
                character_name TEXT,
                timestamp TEXT,
                relative_time TEXT,
                chapter INTEGER,
                source_text TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (manuscript_id) REFERENCES manuscripts(id) ON DELETE CASCADE,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE SET NULL
            )
        """)

        # Inconsistencies table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inconsistencies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manuscript_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                severity TEXT NOT NULL,
                description TEXT NOT NULL,
                character_id INTEGER,
                character_name TEXT,
                location1 TEXT,
                location2 TEXT,
                suggested_fix TEXT,
                detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (manuscript_id) REFERENCES manuscripts(id) ON DELETE CASCADE,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE SET NULL
            )
        """)

        # Create indexes for performance
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_characters_manuscript ON characters(manuscript_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_attributes_character ON character_attributes(character_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_timeline_manuscript ON timeline_events(manuscript_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_inconsistencies_manuscript ON inconsistencies(manuscript_id)"
        )

        self.conn.commit()

    def create_manuscript(self, title: str, content: str, file_path: str) -> int:
        """Create a new manuscript record"""
        cursor = self.conn.cursor()
        word_count = len(content.split())

        cursor.execute(
            """
            INSERT INTO manuscripts (title, content, file_path, word_count, status)
            VALUES (?, ?, ?, ?, 'pending')
        """,
            (title, content, file_path, word_count),
        )

        self.conn.commit()
        return cursor.lastrowid

    def update_manuscript_status(self, manuscript_id: int, status: str):
        """Update manuscript processing status"""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE manuscripts 
            SET status = ?, processed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """,
            (status, manuscript_id),
        )
        self.conn.commit()

    def get_manuscript(self, manuscript_id: int) -> Optional[Dict]:
        """Get manuscript by ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM manuscripts WHERE id = ?", (manuscript_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all_manuscripts(self) -> List[Dict]:
        """Get all manuscripts"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, title, status, word_count, uploaded_at FROM manuscripts ORDER BY uploaded_at DESC"
        )
        return [dict(row) for row in cursor.fetchall()]

    def save_character(self, character: Dict, manuscript_id: int) -> int:
        """Save character profile"""
        cursor = self.conn.cursor()

        cursor.execute(
            """
            INSERT INTO characters (manuscript_id, name, first_mention, mention_count)
            VALUES (?, ?, ?, ?)
        """,
            (
                manuscript_id,
                character["name"],
                character.get("first_mention", ""),
                character.get("mention_count", 0),
            ),
        )

        character_id = cursor.lastrowid

        # Save attributes
        for attr in character.get("attributes", []):
            cursor.execute(
                """
                INSERT INTO character_attributes 
                (character_id, attribute_type, attribute_value, source_location, confidence_score)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    character_id,
                    attr["type"],
                    attr["value"],
                    attr.get("source", ""),
                    attr.get("confidence", 1.0),
                ),
            )

        # Save mentions
        for mention in character.get("mentions", []):
            cursor.execute(
                """
                INSERT INTO character_mentions 
                (character_id, chapter, paragraph, sentence_text, context)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    character_id,
                    mention.get("chapter"),
                    mention.get("paragraph"),
                    mention.get("sentence", ""),
                    mention.get("context", ""),
                ),
            )

        self.conn.commit()
        return character_id

    def get_characters(self, manuscript_id: int) -> List[Dict]:
        """Get all characters for a manuscript"""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM characters WHERE manuscript_id = ? ORDER BY mention_count DESC
        """,
            (manuscript_id,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_character_attributes(self, character_id: int) -> List[Dict]:
        """Get all attributes for a character"""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT attribute_type as type, attribute_value as value, 
                   source_location as source, confidence_score as confidence
            FROM character_attributes WHERE character_id = ?
        """,
            (character_id,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_character_mentions(self, character_id: int) -> List[Dict]:
        """Get all mentions of a character"""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT chapter, paragraph, sentence_text, context
            FROM character_mentions WHERE character_id = ?
        """,
            (character_id,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def save_timeline_event(self, event: Dict, manuscript_id: int):
        """Save a timeline event"""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO timeline_events 
            (manuscript_id, event_type, description, character_name, timestamp, 
             relative_time, chapter, source_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                manuscript_id,
                event["type"],
                event["description"],
                event.get("character_name"),
                event.get("timestamp"),
                event.get("relative_time"),
                event.get("chapter"),
                event.get("source_text"),
            ),
        )
        self.conn.commit()

    def get_timeline_events(self, manuscript_id: int) -> List[Dict]:
        """Get all timeline events for a manuscript"""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM timeline_events 
            WHERE manuscript_id = ? 
            ORDER BY id ASC
        """,
            (manuscript_id,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def save_inconsistency(self, inconsistency: Dict, manuscript_id: int):
        """Save a detected inconsistency"""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO inconsistencies 
            (manuscript_id, type, severity, description, character_name, 
             location1, location2, suggested_fix)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                manuscript_id,
                inconsistency["type"],
                inconsistency["severity"],
                inconsistency["description"],
                inconsistency.get("character_name"),
                inconsistency.get("location1"),
                inconsistency.get("location2"),
                inconsistency.get("suggested_fix"),
            ),
        )
        self.conn.commit()

    def get_inconsistencies(
        self, manuscript_id: int, severity: Optional[str] = None
    ) -> List[Dict]:
        """Get all inconsistencies for a manuscript"""
        cursor = self.conn.cursor()

        if severity:
            cursor.execute(
                """
                SELECT * FROM inconsistencies 
                WHERE manuscript_id = ? AND severity = ?
                ORDER BY severity DESC, detected_at DESC
            """,
                (manuscript_id, severity),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM inconsistencies 
                WHERE manuscript_id = ?
                ORDER BY severity DESC, detected_at DESC
            """,
                (manuscript_id,),
            )

        return [dict(row) for row in cursor.fetchall()]

    def get_manuscript_statistics(self, manuscript_id: int) -> Dict:
        """Get statistics for a manuscript"""
        cursor = self.conn.cursor()

        cursor.execute(
            "SELECT COUNT(*) as count FROM characters WHERE manuscript_id = ?",
            (manuscript_id,),
        )
        char_count = cursor.fetchone()["count"]

        cursor.execute(
            "SELECT COUNT(*) as count FROM timeline_events WHERE manuscript_id = ?",
            (manuscript_id,),
        )
        event_count = cursor.fetchone()["count"]

        cursor.execute(
            "SELECT COUNT(*) as count FROM inconsistencies WHERE manuscript_id = ?",
            (manuscript_id,),
        )
        inc_count = cursor.fetchone()["count"]

        return {
            "character_count": char_count,
            "event_count": event_count,
            "inconsistency_count": inc_count,
        }

    def delete_manuscript(self, manuscript_id: int) -> bool:
        """Delete a manuscript and all related data"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM manuscripts WHERE id = ?", (manuscript_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()