import os
from datetime import datetime
from contextlib import contextmanager
from typing import Optional
from urllib.parse import urlparse

# Check if we're using PostgreSQL (Railway) or SQLite (local)
DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    # PostgreSQL on Railway
    import psycopg2
    from psycopg2.extras import RealDictCursor
    USE_POSTGRES = True
    print("Using PostgreSQL database")
else:
    # SQLite for local development
    import sqlite3
    USE_POSTGRES = False
    DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'chat_history.db')
    print("Using SQLite database")


def get_db_connection():
    """Create a database connection."""
    if USE_POSTGRES:
        # Parse the DATABASE_URL
        result = urlparse(DATABASE_URL)
        conn = psycopg2.connect(
            database=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port
        )
        return conn
    else:
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


def dict_from_row(row, cursor=None):
    """Convert database row to dictionary."""
    if USE_POSTGRES:
        return dict(row) if row else None
    else:
        return dict(row) if row else None


def init_db():
    """Initialize the database with required tables."""
    with get_db() as conn:
        if USE_POSTGRES:
            cursor = conn.cursor()
            
            # Conversations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    bot_id TEXT DEFAULT 'meliksah',
                    title TEXT DEFAULT 'New Chat',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Messages table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    response_time INTEGER DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                )
            ''')
            
            # Create index
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_messages_conversation 
                ON messages(conversation_id)
            ''')
        else:
            cursor = conn.cursor()
            
            # Conversations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    bot_id TEXT DEFAULT 'meliksah',
                    title TEXT DEFAULT 'New Chat',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Add bot_id column if it doesn't exist
            try:
                cursor.execute('ALTER TABLE conversations ADD COLUMN bot_id TEXT DEFAULT "meliksah"')
            except sqlite3.OperationalError:
                pass
            
            # Messages table
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
            
            # Add response_time column if it doesn't exist
            try:
                cursor.execute('ALTER TABLE messages ADD COLUMN response_time INTEGER DEFAULT NULL')
            except sqlite3.OperationalError:
                pass
            
            # Create index
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_messages_conversation 
                ON messages(conversation_id)
            ''')
        
        print("Database initialized successfully!")


# Conversation operations
def create_conversation(conversation_id: str, title: str = "New Chat", bot_id: str = "meliksah") -> dict:
    """Create a new conversation."""
    with get_db() as conn:
        if USE_POSTGRES:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        if USE_POSTGRES:
            cursor.execute(
                'INSERT INTO conversations (id, bot_id, title, created_at, updated_at) VALUES (%s, %s, %s, %s, %s)',
                (conversation_id, bot_id, title, now, now)
            )
        else:
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
        if USE_POSTGRES:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute('SELECT * FROM conversations WHERE id = %s', (conversation_id,))
        else:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM conversations WHERE id = ?', (conversation_id,))
        
        row = cursor.fetchone()
        return dict(row) if row else None


def get_all_conversations() -> list:
    """Get all conversations ordered by most recent."""
    with get_db() as conn:
        if USE_POSTGRES:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute('''
                SELECT c.*, 
                       (SELECT content FROM messages WHERE conversation_id = c.id ORDER BY created_at DESC LIMIT 1) as last_message
                FROM conversations c 
                ORDER BY c.updated_at DESC
            ''')
        else:
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
        if USE_POSTGRES:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute('''
                SELECT c.*, 
                       (SELECT content FROM messages WHERE conversation_id = c.id ORDER BY created_at DESC LIMIT 1) as last_message
                FROM conversations c 
                WHERE c.bot_id = %s
                ORDER BY c.updated_at DESC
            ''', (bot_id,))
        else:
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
        if USE_POSTGRES:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE conversations SET title = %s, updated_at = %s WHERE id = %s',
                (title, datetime.now().isoformat(), conversation_id)
            )
        else:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?',
                (title, datetime.now().isoformat(), conversation_id)
            )


def update_conversation_timestamp(conversation_id: str):
    """Update the timestamp of a conversation."""
    with get_db() as conn:
        if USE_POSTGRES:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE conversations SET updated_at = %s WHERE id = %s',
                (datetime.now().isoformat(), conversation_id)
            )
        else:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE conversations SET updated_at = ? WHERE id = ?',
                (datetime.now().isoformat(), conversation_id)
            )


def delete_conversation(conversation_id: str):
    """Delete a conversation and all its messages."""
    with get_db() as conn:
        if USE_POSTGRES:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM messages WHERE conversation_id = %s', (conversation_id,))
            cursor.execute('DELETE FROM conversations WHERE id = %s', (conversation_id,))
        else:
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
        if USE_POSTGRES:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        if USE_POSTGRES:
            cursor.execute(
                'INSERT INTO messages (conversation_id, role, content, response_time, created_at) VALUES (%s, %s, %s, %s, %s) RETURNING id',
                (conversation_id, role, content, response_time, now)
            )
            message_id = cursor.fetchone()['id']
            
            cursor.execute(
                'UPDATE conversations SET updated_at = %s WHERE id = %s',
                (now, conversation_id)
            )
            
            cursor.execute(
                'SELECT COUNT(*) as count FROM messages WHERE conversation_id = %s',
                (conversation_id,)
            )
            if cursor.fetchone()['count'] == 1 and role == 'user':
                title = content[:50] + '...' if len(content) > 50 else content
                cursor.execute(
                    'UPDATE conversations SET title = %s WHERE id = %s',
                    (title, conversation_id)
                )
        else:
            cursor.execute(
                'INSERT INTO messages (conversation_id, role, content, response_time, created_at) VALUES (?, ?, ?, ?, ?)',
                (conversation_id, role, content, response_time, now)
            )
            message_id = cursor.lastrowid
            
            cursor.execute(
                'UPDATE conversations SET updated_at = ? WHERE id = ?',
                (now, conversation_id)
            )
            
            cursor.execute(
                'SELECT COUNT(*) as count FROM messages WHERE conversation_id = ?',
                (conversation_id,)
            )
            if cursor.fetchone()['count'] == 1 and role == 'user':
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
        if USE_POSTGRES:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                'SELECT * FROM messages WHERE conversation_id = %s ORDER BY created_at ASC',
                (conversation_id,)
            )
        else:
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
        if USE_POSTGRES:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM messages WHERE conversation_id = %s', (conversation_id,))
        else:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM messages WHERE conversation_id = ?', (conversation_id,))


# Initialize database on module import
if __name__ == '__main__':
    init_db()
    print("Database setup complete!")
