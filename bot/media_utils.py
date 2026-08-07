# Filename: bot/media_utils.py
import asyncio
import os
import tempfile
import logging
from aiogram import Bot
from aiogram.types import FSInputFile
from sqlalchemy import select
from database.db import AsyncSessionLocal
from database.models import User

logger = logging.getLogger(__name__)

# SECURITY CONSTRAINT: Render (512MB RAM) အတွက် တစ်ပြိုင်နက် FFmpeg (၃) ခုထက် ပိုမ Run စေရန် Memory Safeguard ထည့်ထားခြင်း။
MEDIA_PROCESSING_SEMAPHORE = asyncio.Semaphore(3)

async def convert_video(input_path: str, output_path: str) -> bool:
    try:
        command = [
            "ffmpeg", "-t", "3", "-i", input_path,
            "-vf", "scale='if(gt(iw,ih),512,-2)':'if(gt(iw,ih),-2,512)'",
            "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p",
            "-b:v", "256K", "-fs", "256000", "-r", "30", "-an", "-y", output_path
        ]
        process = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        _, stderr = await process.communicate()
        if process.returncode != 0:
            logger.error(f"FFmpeg video error: {stderr.decode()}")
            return False
        return True
    except Exception as e:
        logger.error(f"Video conversion exception: {e}")
        return False

async def convert_photo(input_path: str, output_path: str) -> bool:
    try:
        command = [
            "ffmpeg", "-i", input_path,
            "-vf", "scale='if(gt(iw,ih),512,-1)':'if(gt(iw,ih),-1,512)'",
            "-c:v", "libwebp", "-lossless", "0", "-qscale", "80", "-y", output_path
        ]
        process = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        _, stderr = await process.communicate()
        if process.returncode != 0:
            logger.error(f"FFmpeg photo error: {stderr.decode()}")
            return False
        return True
    except Exception as e:
        logger.error(f"Photo conversion exception: {e}")
        return False

async def process_media_task(bot: Bot, file_id: str, file_unique_id: str, user_id: int, chat_id: int, message_id: int, is_video: bool):
    """Semaphore အသုံးပြု၍ OOM Crash မဖြစ်အောင် တန်းစီလုပ်ဆောင်မည့် ပင်မ Media လုပ်ငန်းစဉ်"""
    async with MEDIA_PROCESSING_SEMAPHORE:
        with tempfile.TemporaryDirectory() as tmpdir:
            ext = "mp4" if is_video else "jpg"
            out_ext = "webm" if is_video else "webp"
            input_path = os.path.join(tmpdir, f"input_{file_unique_id}.{ext}")
            output_path = os.path.join(tmpdir, f"output_{file_unique_id}.{out_ext}")

            try:
                # 1. Download
                file_info = await bot.get_file(file_id)
                await bot.download_file(file_info.file_path, destination=input_path)

                # 2. Convert
                success = await convert_video(input_path, output_path) if is_video else await convert_photo(input_path, output_path)
                if not success:
                    await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="❌ ပြောင်းလဲရာတွင် အမှားအယွင်း ဖြစ်ပေါ်ခဲ့ပါသည်။")
                    return

                await bot.send_chat_action(chat_id=chat_id, action="choose_sticker")

                # 3. Database & Sticker Pack Logic
                async with AsyncSessionLocal() as session:
                    result = await session.execute(select(User).where(User.id == user_id))
                    user = result.scalar_one_or_none()
                    user_name = user.name if user else 'User'

                    bot_info = await bot.get_me()
                    bot_username = bot_info.username
                    
                    prefix = "user" if is_video else "img"
                    pack_name = f"{prefix}_{user_id}_by_{bot_username}"
                    
                    if is_video and not user.sticker_pack_name:
                        user.sticker_pack_name = pack_name
                        await session.commit()

                # 4. Upload to Telegram
                sticker_file = FSInputFile(output_path)
                format_type = "video" if is_video else "static"
                emoji = ["🎬"] if is_video else ["🖼️"]
                
                try:
                    await bot.add_sticker_to_set(user_id=user_id, name=pack_name, sticker={"sticker": sticker_file, "format": format_type, "emoji_list": emoji})
                except Exception as e:
                    logger.info(f"Pack not found or invalid, creating new one: {e}")
                    title = f"Video Stickers for {user_name}" if is_video else f"Photo Stickers for {user_name}"
                    await bot.create_new_sticker_set(
                        user_id=user_id, name=pack_name, title=title,
                        stickers=[{"sticker": sticker_file, "format": format_type, "emoji_list": emoji}],
                        sticker_format=format_type
                    )

                sticker_set = await bot.get_sticker_set(name=pack_name)
                new_sticker = sticker_set.stickers[-1]
                
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
                await bot.send_sticker(chat_id=chat_id, sticker=new_sticker.file_id)
                await bot.send_message(chat_id=chat_id, text=f"✅ Sticker အသစ်ရရှိပါပြီ!\n👉 t.me/addstickers/{pack_name}")

            except Exception as e:
                logger.error(f"Error in task pipeline: {e}")
                await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="❌ စနစ်ချို့ယွင်းမှု ဖြစ်ပေါ်ခဲ့ပါသည်။")
