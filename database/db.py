# Filename: database/db.py
import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from database.models import Base

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set. Supabase URL requires 'postgresql+asyncpg://...' format.")

# Monolithic အားလျော်စွာ Pool ပြန်လည်အသုံးပြုပါမည် (pool_pre_ping သည် connection ပြတ်တောက်မှုကို ကာကွယ်ပေးသည်)
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True 
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables verified.")
    except Exception as e:
        logger.error(f"Error initializing DB: {e}")
        raise