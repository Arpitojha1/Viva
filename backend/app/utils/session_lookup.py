from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import Session

async def get_session_by_token(token: str, db: AsyncSession) -> Session:
    result = await db.execute(select(Session).where(Session.public_token == token))
    session = result.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
