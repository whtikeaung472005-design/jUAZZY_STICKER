# Filename: bot/keyboards.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📦 My Sticker Pack", callback_data="action_mypack")],
            [InlineKeyboardButton(text="❓ အသုံးပြုနည်း (Help)", callback_data="action_help")]
        ]
    )