# app/keyboards.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📚 Бесплатные материалы", callback_data="free"))
    builder.row(InlineKeyboardButton(text="⭐ Премиум материалы", callback_data="premium"))
    return builder.as_markup()


def premium_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📖 Гайды", callback_data="cat:guide"))
    builder.row(InlineKeyboardButton(text="💼 Кейсы", callback_data="cat:case"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="menu"))
    return builder.as_markup()


def back_button(to: str = "menu") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data=to))
    return builder.as_markup()


def files_list(files: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i, file in enumerate(files):
        builder.row(InlineKeyboardButton(
            text=f"📄 {file['name']}", 
            callback_data=f"free_dl:{i}"
        ))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="menu"))
    return builder.as_markup()


def technologies_list(technologies: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for tech in technologies:
        builder.row(InlineKeyboardButton(
            text=f"🔧 {tech}",
            callback_data=f"tech:{tech}"
        ))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="premium"))
    return builder.as_markup()


def products_list(products: list, back_to: str = "premium") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for p in products:
        emoji = "📖" if p.category == "guide" else "💼"
        builder.row(InlineKeyboardButton(
            text=f"{emoji} {p.name} — {p.price}₽",
            callback_data=f"product:{p.id}"
        ))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data=back_to))
    return builder.as_markup()


def payment_keyboard(payment_url: str, back_to: str = "premium") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💳 Оплатить", url=payment_url))
    builder.row(InlineKeyboardButton(text="🔄 Проверить оплату", callback_data="check_payment"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data=back_to))
    return builder.as_markup()