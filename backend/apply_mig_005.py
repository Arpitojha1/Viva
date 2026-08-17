import asyncio
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv("C:\\Users\\Arpit\\Viva\\backend\\.env")

async def main():
    db_url = os.environ.get("DATABASE_URL").replace("postgresql+asyncpg", "postgresql")
    conn = await asyncpg.connect(db_url)
    
    with open("C:\\Users\\Arpit\\Viva\\backend\\migrations\\005_question_bank.sql", "r") as f:
        sql = f.read()
        
    await conn.execute(sql)
    print("Migration 005 applied successfully!")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
