# Filename: database/db.py
import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from database.models import Base

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set.")

# SSL အလိုအလျောက် ချိတ်ဆက်ပေးရန်နှင့် Connection ကို လုံခြုံစေရန် connect_args ကို အသုံးပြုထားသည်
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    connect_args={"ssl": True} 
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
