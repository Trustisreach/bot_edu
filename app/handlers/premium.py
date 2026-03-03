# app/handlers/premium.py
from aiogram import Router, F
from aiogram.types import CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, distinct
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import logging

from app.models import Product, Payment
from app.keyboards import (
    premium_menu, products_list, technologies_list,
    payment_keyboard, back_button
)
from app.robokassa import robokassa
from app.s3 import s3
from app.config import settings
from datetime import datetime

router = Router()
logger = logging.getLogger(__name__)


class PaymentState(StatesGroup):
    waiting_payment = State()


# === Отправка файла ===

async def send_product_file(callback: CallbackQuery, product: Product):
    """Отправка файла — сначала пробуем напрямую, потом через ссылку"""
    try:
        file_bytes = await s3.get_file(settings.S3_BUCKET_PREMIUM, product.s3_key)
        filename = product.s3_key.split('/')[-1]
        document = BufferedInputFile(file_bytes, filename=filename)
        await callback.message.answer_document(
            document,
            caption=f"📦 {product.name}\n\nСпасибо за покупку!"
        )
        
    except Exception as e:
        logger.warning(f"Direct file send failed: {e}, trying presigned URL")
        
        try:
            url = await s3.get_presigned_url(settings.S3_BUCKET_PREMIUM, product.s3_key)
            await callback.message.answer(
                f"📦 **{product.name}**\n\n"
                f"Спасибо за покупку!\n\n"
                f"[📥 Нажмите чтобы скачать]({url})\n\n"
                f"_Ссылка действительна 1 час_",
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            
        except Exception as e2:
            logger.error(f"Presigned URL failed too: {e2}")
            await callback.message.answer(
                "❌ Ошибка загрузки файла.\n"
                "Пожалуйста, напишите в поддержку — мы отправим файл вручную."
            )


# === Премиум меню ===

@router.callback_query(F.data == "premium")
async def show_premium(callback: CallbackQuery):
    await callback.message.edit_text(
        "⭐ **Премиум материалы**\n\n"
        "📖 **Гайды** — подробные руководства\n"
        "💼 **Кейсы** — практические примеры\n\n"
        "Выберите категорию:",
        reply_markup=premium_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()


# === Гайды ===

@router.callback_query(F.data == "cat:guide")
async def show_guides(callback: CallbackQuery, session: AsyncSession):
    result = await session.execute(
        select(Product).where(
            Product.category == "guide",
            Product.is_active == True
        ).order_by(Product.name)
    )
    products = result.scalars().all()
    
    if not products:
        await callback.message.edit_text(
            "📭 Пока нет гайдов",
            reply_markup=back_button("premium")
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        "📖 **Гайды**\n\nВыберите гайд:",
        reply_markup=products_list(products, "premium"),
        parse_mode="Markdown"
    )
    await callback.answer()


# === Кейсы — выбор технологии ===

@router.callback_query(F.data == "cat:case")
async def show_case_technologies(callback: CallbackQuery, session: AsyncSession):
    result = await session.execute(
        select(distinct(Product.technology)).where(
            Product.category == "case",
            Product.is_active == True,
            Product.technology.isnot(None)
        )
    )
    technologies = [row[0] for row in result.fetchall() if row[0]]
    
    if not technologies:
        await callback.message.edit_text(
            "📭 Пока нет кейсов",
            reply_markup=back_button("premium")
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        "💼 **Кейсы**\n\nВыберите технологию:",
        reply_markup=technologies_list(technologies),
        parse_mode="Markdown"
    )
    await callback.answer()


# === Кейсы по технологии ===

@router.callback_query(F.data.startswith("tech:"))
async def show_cases_by_tech(callback: CallbackQuery, session: AsyncSession):
    technology = callback.data.split(":", 1)[1]
    
    result = await session.execute(
        select(Product).where(
            Product.category == "case",
            Product.technology == technology,
            Product.is_active == True
        ).order_by(Product.name)
    )
    products = result.scalars().all()
    
    if not products:
        await callback.message.edit_text(
            f"📭 Нет кейсов по {technology}",
            reply_markup=back_button("cat:case")
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        f"💼 **Кейсы: {technology}**\n\nВыберите кейс:",
        reply_markup=products_list(products, "cat:case"),
        parse_mode="Markdown"
    )
    await callback.answer()


# === Просмотр продукта и оплата ===

@router.callback_query(F.data.startswith("product:"))
async def show_product(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    product_id = int(callback.data.split(":")[1])
    product = await session.get(Product, product_id)
    
    if not product:
        await callback.answer("Продукт не найден", show_alert=True)
        return
    
    telegram_id = callback.from_user.id
    
    # Проверяем, может уже оплачено
    result = await session.execute(
        select(Payment).where(
            Payment.telegram_id == telegram_id,
            Payment.product_id == product_id,
            Payment.status == "success"
        ).limit(1)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        await callback.answer("✅ Уже оплачено! Отправляю файл...")
        await send_product_file(callback, product)
        return
    
    # Проверяем, есть ли pending платёж
    result = await session.execute(
        select(Payment).where(
            Payment.telegram_id == telegram_id,
            Payment.product_id == product_id,
            Payment.status == "pending"
        ).limit(1)
    )
    pending_payment = result.scalar_one_or_none()
    
    if pending_payment:
        payment = pending_payment
    else:
        payment = Payment(
            telegram_id=telegram_id,
            transaction_id=str(uuid.uuid4()),
            product_id=product_id,
            amount=product.price,
            status="pending",
            check_count=0
        )
        session.add(payment)
        await session.commit()
        await session.refresh(payment)
    
    await state.update_data(payment_id=payment.id, product_id=product_id)
    await state.set_state(PaymentState.waiting_payment)
    
    payment_url = robokassa.generate_payment_link(
        amount=product.price,
        invoice_id=payment.id,
        description=f"Покупка: {product.name}"
    )
    
    emoji = "📖" if product.category == "guide" else "💼"
    back_to = "cat:guide" if product.category == "guide" else "cat:case"
    
    await callback.message.edit_text(
        f"{emoji} **{product.name}**\n\n"
        f"💰 Стоимость: **{product.price}₽**\n\n"
        f"Нажмите «Оплатить» для перехода к оплате.\n"
        f"После оплаты нажмите «Проверить оплату» или подождите — "
        f"файл придёт автоматически.",
        reply_markup=payment_keyboard(payment_url, back_to),
        parse_mode="Markdown"
    )
    await callback.answer()


# === Проверка оплаты вручную ===

@router.callback_query(F.data == "check_payment", PaymentState.waiting_payment)
async def check_payment_manual(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    data = await state.get_data()
    payment_id = data.get("payment_id")
    product_id = data.get("product_id")
    
    if not payment_id:
        await callback.answer("Платёж не найден", show_alert=True)
        return
    
    await callback.answer("🔄 Проверяю оплату...")
    
    status = await robokassa.check_payment_status(payment_id)
    
    if status['paid']:
        payment = await session.get(Payment, payment_id)
        if payment and payment.status == "pending":
            payment.status = "success"
            payment.paid_at = datetime.utcnow()
            await session.commit()
        
        product = await session.get(Product, product_id)
        if product:
            await state.clear()
            await callback.message.edit_text("✅ **Оплата подтверждена!**", parse_mode="Markdown")
            await send_product_file(callback, product)
    else:
        await callback.message.answer(
            "⏳ Оплата пока не поступила.\n\n"
            "Если вы уже оплатили, подождите 1-2 минуты и попробуйте снова."
        )


@router.callback_query(F.data == "check_payment")
async def check_payment_no_state(callback: CallbackQuery):
    await callback.answer("Выберите продукт заново", show_alert=True)