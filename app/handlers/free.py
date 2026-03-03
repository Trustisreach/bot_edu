# app/handlers/free.py
from aiogram import Router, F
from aiogram.types import CallbackQuery, BufferedInputFile
from app.keyboards import files_list, back_button
from app.s3 import s3
from app.config import settings

router = Router()

# Кэш файлов
free_files_cache: list[dict] = []


@router.callback_query(F.data == "free")
async def show_free_materials(callback: CallbackQuery):
    global free_files_cache
    
    await callback.answer("⏳ Загружаю...")
    
    try:
        free_files_cache = await s3.list_files(settings.S3_BUCKET_FREE)
        
        if not free_files_cache:
            await callback.message.edit_text(
                "📭 Пока нет бесплатных материалов",
                reply_markup=back_button()
            )
            return
        
        await callback.message.edit_text(
            f"📚 **Бесплатные материалы** ({len(free_files_cache)})",
            reply_markup=files_list(free_files_cache),
            parse_mode="Markdown"
        )
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка: {e}", reply_markup=back_button())


@router.callback_query(F.data.startswith("free_dl:"))
async def download_free_file(callback: CallbackQuery):
    index = int(callback.data.split(":")[1])
    
    if index >= len(free_files_cache):
        await callback.answer("Обновите список", show_alert=True)
        return
    
    file_info = free_files_cache[index]
    await callback.answer(f"⏳ Скачиваю...")
    
    try:
        file_bytes = await s3.get_file(settings.S3_BUCKET_FREE, file_info['key'])
        document = BufferedInputFile(file_bytes, filename=file_info['name'])
        await callback.message.answer_document(document, caption=f"📄 {file_info['name']}")
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка: {e}")