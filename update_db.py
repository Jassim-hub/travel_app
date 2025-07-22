"""
Script to update the database with bot fields.
Run this once to add the new columns to existing inquiries table.
"""
import sqlite3
import os

def update_database():
    # Path to your database
    db_path = os.path.join('instance', 'travel_app.db')
    
    if not os.path.exists(db_path):
        print("Database not found. Make sure the app has been run at least once.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Add bot processing columns if they don't exist
        bot_columns = [
            "ALTER TABLE inquiry ADD COLUMN bot_processed BOOLEAN DEFAULT 0",
            "ALTER TABLE inquiry ADD COLUMN bot_confidence REAL",
            "ALTER TABLE inquiry ADD COLUMN bot_response_sent BOOLEAN DEFAULT 0", 
            "ALTER TABLE inquiry ADD COLUMN requires_human_review BOOLEAN DEFAULT 0"
        ]
        
        for sql in bot_columns:
            try:
                cursor.execute(sql)
                print(f"✅ Added column: {sql.split('ADD COLUMN')[1].split()[0]}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    print(f"⚠️  Column already exists: {sql.split('ADD COLUMN')[1].split()[0]}")
                else:
                    print(f"❌ Error: {e}")
        
        conn.commit()
        print("\n🎉 Database update completed!")
        
    except Exception as e:
        print(f"❌ Error updating database: {e}")
        conn.rollback()
    
    finally:
        conn.close()

if __name__ == "__main__":
    update_database()
