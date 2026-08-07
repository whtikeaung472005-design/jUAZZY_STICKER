# Filename: bot/handlers.py
import os
import asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import User
from bot.keyboards import get_start_keyboard
from bot.media_utils import process_media_task

router = Router()

async def send_mypack_info(user_id: int, message_obj: Message, session: AsyncSession):
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user and user.sticker_pack_name:
        await message_obj.answer(f"📦 သင့်ကိုယ်ပိုင် Sticker Pack လင့်ခ်:\n👉 t.me/addstickers/{user.sticker_pack_name}")
    else:
        await message_obj.answer("❌ သင်သည် Video Sticker တစ်ခုမျှ မဖန်တီးရသေးပါ။ Video အရင်ပို့ပေးပါ။")

@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession):
    user_id = message.from_user.id
    result = await session.execute(select(User).where(User.id == user_id))
    if not result.scalar_one_or_none():
        session.add(User(id=user_id, name=message.from_user.first_name))
        await session.commit()

    image_url = os.getenv("WELCOME_IMAGE_URL")
    caption = "👋 <b>မင်္ဂလာပါ။ Telegram Video/Photo Sticker Bot မှ ကြိုဆိုပါတယ်။</b>\n\n🎬 Video သို့မဟုတ် Photo ကို ပို့ပေးလိုက်ရုံဖြင့် Sticker အဖြစ် အလိုအလျောက် ပြောင်းလဲပေးပါမည်။"
    
    if image_url:
        await message.answer_photo(photo=image_url, caption=caption, reply_markup=get_start_keyboard())
    else:
        await message.answer(text=caption, reply_markup=get_start_keyboard())

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer("❓ <b>အသုံးပြုနည်း လမ်းညွှန်</b>\n၁။ 20MB အောက် Video သို့မဟုတ် Photo ပို့ပါ။\n၂။ Bot မှ Sticker အဖြစ် ပြောင်းလဲပေးပါမည်။")

@router.message(Command("mypack"))
async def cmd_mypack(message: Message, session: AsyncSession):
    await send_mypack_info(message.from_user.id, message, session)

@router.callback_query(F.data == "action_help")
async def callback_help(callback: CallbackQuery):
    await callback.answer()
    await cmd_help(callback.message)

@router.callback_query(F.data == "action_mypack")
async def callback_mypack(callback: CallbackQuery, session: AsyncSession):
    await callback.answer()
    await send_mypack_info(callback.from_user.id, callback.message, session)

@router.message(F.video | F.animation | F.document | F.photo)
async def handle_media(message: Message, bot: Bot):
    is_video = False
    media_obj = None

    if message.photo:
        media_obj = message.photo[-1]
    elif message.video:
        media_obj = message.video
        is_video = True
    elif message.animation:
        media_obj = message.animation
        is_video = True
    elif message.document and message.document.mime_type and message.document.mime_type.startswith('video/'):
        media_obj = message.document
        is_video = True
        
    if not media_obj:
        return await message.answer("❌ ကျေးဇူးပြု၍ Video သို့မဟုတ် Photo ကိုသာ ပို့ပေးပါ။")
        
    if getattr(media_obj, 'file_size', 0) > 20 * 1024 * 1024:
        return await message.answer("❌ File size ကြီးလွန်းပါသည်။ 20MB အောက်သာ လက်ခံပါသည်။")

    processing_msg = await message.answer("⏳ လက်ခံရရှိပါပြီ။ တန်းစီ၍ ပြောင်းလဲပေးနေပါသည်... (ခေတ္တစောင့်ဆိုင်းပေးပါ)")

    # Background Task အဖြစ် Queue (Semaphore) အတွင်းသို့ လွှဲပြောင်းပေးခြင်း
    asyncio.create_task(process_media_task(
        bot=bot, file_id=media_obj.file_id, file_unique_id=media_obj.file_unique_id,
        user_id=message.from_user.id, chat_id=message.chat.id,
        message_id=processing_msg.message_id, is_video=is_video
    ))