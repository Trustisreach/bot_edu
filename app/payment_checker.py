# app/payment_checker.py
import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy import select
from aiogram import Bot
from aiogram.types import BufferedInputFile

from app.database import async_session
from app.models import Payment, Product
from app.robokassa import robokassa
from app.s3 import s3
from app.config import settings

logger = logging.getLogger(__name__)


async def send_product_to_user(bot: Bot, telegram_id: int, product: Product):
    """Отправляет файл продукта пользователю"""
    try:
        file_bytes = await s3.get_file(settings.S3_BUCKET_PREMIUM, product.s3_key)
        filename = product.s3_key.split('/')[-1]
        document = BufferedInputFile(file_bytes, filename=filename)
        
        await bot.send_message(
            chat_id=telegram_id,
            text="✅ **Оплата получена!**\n\nОтправляю ваш файл...",
            parse_mode="Markdown"
        )
        
        await bot.send_document(
            chat_id=telegram_id,
            document=document,
            caption=f"📦 {product.name}\n\nСпасибо за покупку!"
        )
        
        logger.info(f"File sent to user {telegram_id}: {product.name}")
        
    except Exception as e:
        logger.error(f"Error sending file to {telegram_id}: {e}")
        await bot.send_message(
            chat_id=telegram_id,
            text="✅ Оплата получена, но произошла ошибка при отправке файла.\nНапишите в поддержку."
        )


async def check_pending_payments(bot: Bot):
    """Фоновая задача: проверяет pending платежи"""
    logger.info("Payment checker started")
    
    while True:
        await asyncio.sleep(settings.PAYMENT_CHECK_INTERVAL)
        
        try:
            async with async_session() as session:
                # Берём только pending платежи
                result = await session.execute(
                    select(Payment).where(Payment.status == "pending")
                )
                payments = result.scalars().all()
                
                if not payments:
                    continue
                
                logger.info(f"Checking {len(payments)} pending payments...")
                
                now = datetime.utcnow()
                max_age = timedelta(hours=settings.PAYMENT_MAX_AGE_HOURS)
                
                for payment in payments:
                    # Проверяем лимиты
                    is_too_old = (now - payment.created_at) > max_age
                    is_too_many_checks = payment.check_count >= settings.PAYMENT_MAX_CHECKS
                    
                    if is_too_old or is_too_many_checks:
                        logger.info(
                            f"Payment {payment.id} expired: "
                            f"age={now - payment.created_at}, "
                            f"checks={payment.check_count}"
                        )
                        payment.status = "expired"
                        await session.commit()
                        continue
                    
                    # Увеличиваем счётчик проверок
                    payment.check_count += 1
                    
                    logger.info(
                        f"Checking payment id={payment.id}, "
                        f"amount={payment.amount}, "
                        f"check #{payment.check_count}"
                    )
                    
                    status = await robokassa.check_payment_status(payment.id)
                    
                    if status['paid']:
                        logger.info(f"Payment {payment.id} is PAID!")
                        payment.status = "success"
                        payment.paid_at = datetime.utcnow()
                        await session.commit()
                        
                        product = await session.get(Product, payment.product_id)
                        if product:
                            await send_product_to_user(bot, payment.telegram_id, product)
                    else:
                        # Сохраняем увеличенный счётчик
                        await session.commit()
                        logger.debug(
                            f"Payment {payment.id} not paid: {status.get('reason')}"
                        )
                    
                    # Пауза между проверками
                    await asyncio.sleep(1)
                    
        except Exception as e:
            logger.error(f"Error in payment checker: {e}", exc_info=True)