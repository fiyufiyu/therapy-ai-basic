import sqlite3
from datetime import datetime
from contextlib import contextmanager
from typing import Optional, List, Dict
import json
import os

DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'chat_history.db')

def get_db_connection():
    """Create a database connection."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_db():
    """Initialize the database with required tables."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Conversations table - stores chat sessions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                bot_id TEXT DEFAULT 'meliksah',
                title TEXT DEFAULT 'New Chat',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Add bot_id column if it doesn't exist (for existing databases)
        try:
            cursor.execute('ALTER TABLE conversations ADD COLUMN bot_id TEXT DEFAULT "meliksah"')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Messages table - stores individual messages
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                response_time INTEGER DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        ''')
        
        # Add response_time column if it doesn't exist (for existing databases)
        try:
            cursor.execute('ALTER TABLE messages ADD COLUMN response_time INTEGER DEFAULT NULL')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Create index for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_messages_conversation 
            ON messages(conversation_id)
        ''')
        
        print("Database initialized successfully!")

# Conversation operations
def create_conversation(conversation_id: str, title: str = "New Chat", bot_id: str = "meliksah") -> dict:
    """Create a new conversation."""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute(
            'INSERT INTO conversations (id, bot_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)',
            (conversation_id, bot_id, title, now, now)
        )
        return {
            'id': conversation_id,
            'bot_id': bot_id,
            'title': title,
            'created_at': now,
            'updated_at': now
        }

def get_conversation(conversation_id: str) -> Optional[dict]:
    """Get a conversation by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM conversations WHERE id = ?', (conversation_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

def get_all_conversations() -> list:
    """Get all conversations ordered by most recent."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT c.*, 
                   (SELECT content FROM messages WHERE conversation_id = c.id ORDER BY created_at DESC LIMIT 1) as last_message
            FROM conversations c 
            ORDER BY c.updated_at DESC
        ''')
        return [dict(row) for row in cursor.fetchall()]

def get_conversations_by_bot(bot_id: str) -> list:
    """Get all conversations for a specific bot ordered by most recent."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT c.*, 
                   (SELECT content FROM messages WHERE conversation_id = c.id ORDER BY created_at DESC LIMIT 1) as last_message
            FROM conversations c 
            WHERE c.bot_id = ?
            ORDER BY c.updated_at DESC
        ''', (bot_id,))
        return [dict(row) for row in cursor.fetchall()]

def update_conversation_title(conversation_id: str, title: str):
    """Update the title of a conversation."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?',
            (title, datetime.now().isoformat(), conversation_id)
        )

def update_conversation_timestamp(conversation_id: str):
    """Update the timestamp of a conversation."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE conversations SET updated_at = ? WHERE id = ?',
            (datetime.now().isoformat(), conversation_id)
        )

def delete_conversation(conversation_id: str):
    """Delete a conversation and all its messages."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM messages WHERE conversation_id = ?', (conversation_id,))
        cursor.execute('DELETE FROM conversations WHERE id = ?', (conversation_id,))

# Message operations
def add_message(conversation_id: str, role: str, content: str, response_time: int = None, bot_id: str = "meliksah") -> dict:
    """Add a message to a conversation."""
    # Ensure conversation exists
    if not get_conversation(conversation_id):
        create_conversation(conversation_id, bot_id=bot_id)
    
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute(
            'INSERT INTO messages (conversation_id, role, content, response_time, created_at) VALUES (?, ?, ?, ?, ?)',
            (conversation_id, role, content, response_time, now)
        )
        message_id = cursor.lastrowid
        
        # Update conversation timestamp
        cursor.execute(
            'UPDATE conversations SET updated_at = ? WHERE id = ?',
            (now, conversation_id)
        )
        
        # Auto-generate title from first user message
        cursor.execute(
            'SELECT COUNT(*) as count FROM messages WHERE conversation_id = ?',
            (conversation_id,)
        )
        if cursor.fetchone()['count'] == 1 and role == 'user':
            # First message - use it as title (truncated)
            title = content[:50] + '...' if len(content) > 50 else content
            cursor.execute(
                'UPDATE conversations SET title = ? WHERE id = ?',
                (title, conversation_id)
            )
        
        return {
            'id': message_id,
            'conversation_id': conversation_id,
            'role': role,
            'content': content,
            'response_time': response_time,
            'created_at': now
        }

def get_messages(conversation_id: str) -> list:
    """Get all messages for a conversation."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC',
            (conversation_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

def get_messages_for_api(conversation_id: str) -> list:
    """Get messages in format suitable for OpenAI API."""
    messages = get_messages(conversation_id)
    return [{'role': m['role'], 'content': m['content']} for m in messages]

def clear_messages(conversation_id: str):
    """Clear all messages from a conversation."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM messages WHERE conversation_id = ?', (conversation_id,))

# Initialize database on module import
if __name__ == '__main__':
    init_db()
    print("Database setup complete!")

