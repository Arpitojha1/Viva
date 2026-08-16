"""
Run the database migration against Supabase.
Usage: python scripts/run_migration.py
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")


async def run_migration():
    import asyncpg

    raw_url = os.environ.get("DATABASE_URL", "")
    if not raw_url:
        print("ERROR: DATABASE_URL not set in .env")
        sys.exit(1)

    # Convert SQLAlchemy URL format to raw asyncpg format
    db_url = raw_url.replace("postgresql+asyncpg://", "postgresql://")
    print(f"Connecting to Supabase...")

    try:
        conn = await asyncpg.connect(db_url, timeout=20)
        print("✓ Connected to database")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        print("\nTroubleshooting:")
        print("  - Verify DATABASE_URL in .env is correct")
        print("  - Ensure using port 5432 (not 6543)")
        print("  - Check Supabase project is not paused")
        sys.exit(1)

    migration_path = Path(__file__).parent.parent / "migrations" / "001_initial_schema.sql"
    with open(migration_path, "r") as f:
        sql = f.read()

    print("Running migration...")
    try:
        await conn.execute(sql)
        print("✓ Migration executed successfully")
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        await conn.close()
        sys.exit(1)

    # Verify tables
    tables = await conn.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
    )
    table_names = [t["tablename"] for t in tables]
    print(f"✓ Tables in database: {table_names}")

    expected = {"users", "resumes", "sessions", "chunks", "chunk_sources", "ingested_books", "questions", "answers"}
    missing = expected - set(table_names)
    if missing:
        print(f"✗ Missing tables: {missing}")
    else:
        print("✓ All expected tables present")

    # Check pgvector extension
    ext = await conn.fetchrow(
        "SELECT extname FROM pg_extension WHERE extname = 'vector'"
    )
    if ext:
        print("✓ pgvector extension is active")
    else:
        print("✗ pgvector extension NOT found — run: CREATE EXTENSION IF NOT EXISTS vector;")

    await conn.close()
    print("\n✓ Checkpoint 0 DB verification complete")


if __name__ == "__main__":
    asyncio.run(run_migration())
