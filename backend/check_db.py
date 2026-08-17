import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv("C:\\Users\\Arpit\\Viva\\backend\\.env")

async def main():
    db_url = os.environ.get("DATABASE_URL").replace("postgresql+asyncpg", "postgresql")
    
    conn = await asyncpg.connect(db_url)
    
    print("--- resumes columns ---")
    rows = await conn.fetch("SELECT column_name FROM information_schema.columns WHERE table_name = 'resumes' ORDER BY column_name;")
    for r in rows:
        print(r['column_name'])
        
    print("\n--- sessions columns ---")
    rows = await conn.fetch("SELECT column_name FROM information_schema.columns WHERE table_name = 'sessions' ORDER BY column_name;")
    for r in rows:
        print(r['column_name'])
        
    print("\n--- public tables ---")
    rows = await conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;")
    for r in rows:
        print(r['table_name'])
        
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
