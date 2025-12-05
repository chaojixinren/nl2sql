"""
Script to download and setup Chinook sample database.
Chinook is a sample database available for SQL Server, Oracle, MySQL, etc.
We use the SQLite version for M2 testing.
"""
import sys
import urllib.request
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Project root
project_root = Path(__file__).parent.parent
data_dir = project_root / "data"

# Chinook SQLite database URL
CHINOOK_URL = "https://github.com/lerocha/chinook-database/raw/master/ChinookDatabase/DataSources/Chinook_Sqlite.sqlite"
DB_PATH = data_dir / "chinook.db"


def download_chinook():
    """Download Chinook database from GitHub."""
    print("=== Chinook Database Setup ===\n")

    # Create data directory if not exists
    data_dir.mkdir(exist_ok=True)
    print(f"✓ Data directory: {data_dir}")

    # Check if database already exists
    if DB_PATH.exists():
        print(f"✓ Database already exists: {DB_PATH}")
        print(f"  File size: {DB_PATH.stat().st_size / 1024:.2f} KB")
        return True

    # Download database
    print(f"\nDownloading Chinook database...")
    print(f"  URL: {CHINOOK_URL}")
    print(f"  Destination: {DB_PATH}")

    try:
        urllib.request.urlretrieve(CHINOOK_URL, DB_PATH)
        print(f"✓ Download complete!")
        print(f"  File size: {DB_PATH.stat().st_size / 1024:.2f} KB")
        return True

    except Exception as e:
        print(f"✗ Download failed: {e}")
        return False


def verify_database():
    """Verify database is accessible and show basic info."""
    import sqlite3

    print(f"\nVerifying database...")

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get table names
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table'
            ORDER BY name
        """)
        tables = [row[0] for row in cursor.fetchall()]

        print(f"✓ Database is valid")
        print(f"  Tables: {len(tables)}")
        for table in tables:
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"    - {table}: {count} rows")

        cursor.close()
        conn.close()

        return True

    except Exception as e:
        print(f"✗ Verification failed: {e}")
        return False


if __name__ == "__main__":
    # Download database
    if download_chinook():
        # Verify database
        verify_database()

        print(f"\n{'='*50}")
        print("Setup complete!")
        print(f"{'='*50}")
        print(f"\nDatabase location: {DB_PATH}")
        print(f"You can now run: python graphs/base_graph.py")
    else:
        print(f"\n{'='*50}")
        print("Setup failed!")
        print(f"{'='*50}")
        sys.exit(1)
