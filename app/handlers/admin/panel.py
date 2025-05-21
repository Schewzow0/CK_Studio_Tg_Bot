from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from app.config import ADMINS
from app.keyboards import admin_panel_kb, main_admin_kb

router = Router()


@router.message(F.text == "Админ-панель")
async def admin_panel(message: Message):
    if message.from_user.id in ADMINS:
        await message.answer("Вы вошли в админ-панель", reply_markup=admin_panel_kb)
    else:
        await message.reply("Я тебя не понимаю. Выбери, пожалуйста, один из пунктов меню")


@router.callback_query(F.data == "cancel_management")
async def cancel_management(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(
        "Возврат в админ-панель",
        reply_markup=admin_panel_kb
    )


@router.message(F.text == "Назад")
async def admin_back_handler(message: Message):
    if message.from_user.id in ADMINS:
        await message.answer("Вы вернулись в главное меню", reply_markup=main_admin_kb)
