# Filename: database/db.py
import os
import logging
import ssl
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from database.models import Base

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set.")

# ---------------------------------------------------------
# SECURITY & INFRASTRUCTURE FIX: SSL Validation Bypass
# Supabase Pooler ၏ Self-signed Certificate ကို ကျော်ဖြတ်ရန်
# ---------------------------------------------------------
custom_ssl_context = ssl.create_default_context()
custom_ssl_context.check_hostname = False
custom_ssl_context.verify_mode = ssl.CERT_NONE

# Clean Architecture: Session Mode (Port 5432) ကို သုံးမည်ဖြစ်၍ Caching များကို ပိတ်ရန် မလိုတော့ပါ
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    connect_args={
        "ssl": custom_ssl_context
    } 
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
        logger.info("Database tables verified successfully.")
    except Exception as e:
        logger.error(f"Error initializing DB: {e}")
        raise
