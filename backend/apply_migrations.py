import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv("C:\\Users\\Arpit\\Viva\\backend\\.env")

async def apply_migration(conn, file_path):
    print(f"Applying {file_path}...")
    with open(file_path, "r", encoding="utf-8") as f:
        sql = f.read()
    sql = sql.lstrip('\ufeff')
    try:
        await conn.execute(sql)
        print("Success.")
    except Exception as e:
        print(f"Error applying: {str(e)}")

async def main():
    db_url = os.environ.get("DATABASE_URL").replace("postgresql+asyncpg", "postgresql")
    conn = await asyncpg.connect(db_url)
    
    await apply_migration(conn, "C:\\Users\\Arpit\\Viva\\backend\\migrations\\002_schema_fixes.sql")
    await apply_migration(conn, "C:\\Users\\Arpit\\Viva\\backend\\migrations\\003_session_public_token.sql")
    await apply_migration(conn, "C:\\Users\\Arpit\\Viva\\backend\\migrations\\004_resume_content_hash.sql")
    
    print("\n--- Verifying answers columns ---")
    rows = await conn.fetch("SELECT column_name FROM information_schema.columns WHERE table_name = 'answers' AND table_schema = 'public' ORDER BY column_name;")
    for r in rows:
        print(r['column_name'])
        
    print("\n--- Verifying resumes columns ---")
    rows = await conn.fetch("SELECT column_name FROM information_schema.columns WHERE table_name = 'resumes' AND table_schema = 'public' ORDER BY column_name;")
    for r in rows:
        print(r['column_name'])
        
    print("\n--- Verifying sessions columns ---")
    rows = await conn.fetch("SELECT column_name FROM information_schema.columns WHERE table_name = 'sessions' AND table_schema = 'public' ORDER BY column_name;")
    for r in rows:
        print(r['column_name'])
        
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
