# migrate_db.py
from app import create_app, db
from app.models import User
import sqlite3
import os


app = create_app()

def add_missing_columns_and_fix_user_groups():
    with app.app_context():
        # Locate DB
        db_path = "PATH WHERE YOU WANT DATABASE TO BE LOCATED"
        if not os.path.isabs(db_path):
            db_path = os.path.join(os.getcwd(), db_path)
        print(f"Using database at: {db_path}")
        
        # Connect to SQLite with foreign key support
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        
        # Show existing tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [table[0] for table in cursor.fetchall()]
        print(f"Tables: {tables}")
        
        # Email confirmation fields
        user_table = User.__tablename__
        if user_table in tables:
            cursor.execute(f"PRAGMA table_info({user_table})")
            columns = [col[1] for col in cursor.fetchall()]
            print(f"{user_table} columns: {columns}")
            
            if 'email_verified' not in columns:
                print("Adding 'email_verified' column...")
                cursor.execute(f"ALTER TABLE {user_table} ADD COLUMN email_verified BOOLEAN DEFAULT 0")
            
            if 'confirmation_token' not in columns:
                print("Adding 'confirmation_token' column...")
                cursor.execute(f"ALTER TABLE {user_table} ADD COLUMN confirmation_token VARCHAR(100)")
            
            if 'token_created_at' not in columns:
                print("Adding 'token_created_at' column...")
                cursor.execute(f"ALTER TABLE {user_table} ADD COLUMN token_created_at DATETIME")
        else:
            print(f"User table '{user_table}' not found.")
        
        # Drop and recreate user_groups with CASCADE foreign keys
        if 'user_groups' in tables:
            print("Dropping and recreating 'user_groups' with ON DELETE CASCADE...")
            cursor.execute("DROP TABLE user_groups;")
        
        cursor.execute("""
            CREATE TABLE user_groups (
                user_id INTEGER,
                group_id INTEGER,
                is_admin BOOLEAN,
                PRIMARY KEY (user_id, group_id),
                FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
                FOREIGN KEY (group_id) REFERENCES "group"(id) ON DELETE CASCADE
            );
        """)
        print("Table 'user_groups' created with cascading deletes.")
        
        conn.commit()
        conn.close()
        print("Migration complete.")

if __name__ == '__main__':
    add_missing_columns_and_fix_user_groups()
