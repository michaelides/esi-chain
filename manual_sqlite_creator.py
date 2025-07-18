#!/usr/bin/env python3
"""
Manual Database Creator for Chainlit SQLite
Run this script to manually create the database schema.
"""

import sqlite3
import os
import sys

def create_database_sync(db_path: str = "chainlit_app.db"):
    """Create the database schema using synchronous SQLite."""
    
    # SQLite-compatible schema
    schema_sql = """
    -- Enable foreign keys
    PRAGMA foreign_keys = ON;
    
    -- Users table
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        identifier TEXT NOT NULL UNIQUE,
        metadata TEXT NOT NULL,
        createdAt TEXT
    );
    
    -- Threads table
    CREATE TABLE IF NOT EXISTS threads (
        id TEXT PRIMARY KEY,
        createdAt TEXT,
        name TEXT,
        userId TEXT,
        userIdentifier TEXT,
        tags TEXT,
        metadata TEXT,
        FOREIGN KEY (userId) REFERENCES users(id) ON DELETE CASCADE
    );
    
    -- Steps table
    CREATE TABLE IF NOT EXISTS steps (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        threadId TEXT NOT NULL,
        parentId TEXT,
        streaming INTEGER NOT NULL,
        waitForAnswer INTEGER,
        isError INTEGER,
        metadata TEXT,
        tags TEXT,
        input TEXT,
        output TEXT,
        createdAt TEXT,
        command TEXT,
        start TEXT,
        end TEXT,
        generation TEXT,
        showInput TEXT,
        language TEXT,
        indent INTEGER,
        defaultOpen INTEGER,
        FOREIGN KEY (threadId) REFERENCES threads(id) ON DELETE CASCADE
    );
    
    -- Elements table
    CREATE TABLE IF NOT EXISTS elements (
        id TEXT PRIMARY KEY,
        threadId TEXT,
        type TEXT,
        url TEXT,
        chainlitKey TEXT,
        name TEXT NOT NULL,
        display TEXT,
        objectKey TEXT,
        size TEXT,
        page INTEGER,
        language TEXT,
        forId TEXT,
        mime TEXT,
        props TEXT,
        FOREIGN KEY (threadId) REFERENCES threads(id) ON DELETE CASCADE
    );
    
    -- Feedbacks table
    CREATE TABLE IF NOT EXISTS feedbacks (
        id TEXT PRIMARY KEY,
        forId TEXT NOT NULL,
        threadId TEXT NOT NULL,
        value INTEGER NOT NULL,
        comment TEXT,
        FOREIGN KEY (threadId) REFERENCES threads(id) ON DELETE CASCADE
    );
    
    -- Create indexes for better performance
    CREATE INDEX IF NOT EXISTS idx_users_identifier ON users(identifier);
    CREATE INDEX IF NOT EXISTS idx_threads_userId ON threads(userId);
    CREATE INDEX IF NOT EXISTS idx_threads_userIdentifier ON threads(userIdentifier);
    CREATE INDEX IF NOT EXISTS idx_steps_threadId ON steps(threadId);
    CREATE INDEX IF NOT EXISTS idx_steps_parentId ON steps(parentId);
    CREATE INDEX IF NOT EXISTS idx_elements_threadId ON elements(threadId);
    CREATE INDEX IF NOT EXISTS idx_elements_forId ON elements(forId);
    CREATE INDEX IF NOT EXISTS idx_feedbacks_threadId ON feedbacks(threadId);
    CREATE INDEX IF NOT EXISTS idx_feedbacks_forId ON feedbacks(forId);
    """
    
    try:
        # Connect to database (creates file if it doesn't exist)
        conn = sqlite3.connect(db_path)
        
        # Execute the schema
        conn.executescript(schema_sql)
        
        # Verify tables were created
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print(f"✅ Database created successfully: {db_path}")
        print(f"📊 Tables created: {[table[0] for table in tables]}")
        
        # Check if tables have expected structure
        for table_name in ['users', 'threads', 'steps', 'elements', 'feedbacks']:
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            print(f"📋 {table_name}: {len(columns)} columns")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        return False

def inspect_database(db_path: str = "chainlit_app.db"):
    """Inspect the database contents."""
    if not os.path.exists(db_path):
        print(f"❌ Database file {db_path} does not exist")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check table counts
        tables = ['users', 'threads', 'steps', 'elements', 'feedbacks']
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"📊 {table}: {count} rows")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error inspecting database: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = "chainlit_app.db"
    
    print(f"🔧 Creating Chainlit SQLite database: {db_path}")
    
    if create_database_sync(db_path):
        print(f"\n🔍 Database inspection:")
        inspect_database(db_path)
        print(f"\n✅ Ready to use! Run your Chainlit app with: chainlit run app.py")
    else:
        print("❌ Failed to create database")
        sys.exit(1)