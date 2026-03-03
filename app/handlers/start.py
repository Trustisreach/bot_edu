# app/handlers/start.py
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from app.keyboards import main_menu

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "Здесь вы найдёте обучающие материалы:\n\n"
        "📚 **Бесплатные** — доступны сразу\n"
        "⭐ **Премиум** — гайды и кейсы по подписке",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "menu")
async def show_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🏠 **Главное меню**\n\nВыберите раздел:",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()