import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv("C:\\Users\\Arpit\\Viva\\backend\\.env")

async def main():
    db_url = os.environ.get("DATABASE_URL").replace("postgresql+asyncpg", "postgresql")
    conn = await asyncpg.connect(db_url)
    
    print("\n--- Latest answers ---")
    rows = await conn.fetch("SELECT id, question_id, numeric_score, quality_score FROM answers ORDER BY id DESC LIMIT 5;")
    for r in rows:
        print(f"id={r['id']}, numeric_score={r['numeric_score']}, quality_score={r['quality_score']}")
        
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
