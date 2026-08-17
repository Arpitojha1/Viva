import asyncio
import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()

async def fix():
    import sqlalchemy as sa
    from app.database import engine
    async with engine.begin() as conn:
        try:
            await conn.execute(sa.text(
                "ALTER TABLE questions DROP CONSTRAINT questions_difficulty_check"
            ))
        except Exception:
            pass
        await conn.execute(sa.text(
            "ALTER TABLE questions ADD CONSTRAINT questions_difficulty_check CHECK (difficulty IN ('Fundamentals', 'Intermediate', 'Advanced'))"
        ))
        print('OK: DB constraint fixed')

asyncio.run(fix())
