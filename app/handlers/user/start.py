from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart

from app.keyboards import main_kb, main_admin_kb
from app.config import ADMINS

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        f"*{message.from_user.first_name}*, хочешь узнать, где мы находимся, "
        "познакомиться с мастерами и прочувствовать атмосферу? Жми *«О нас»* 📍✨\n\n"
        "Есть вопросы? Пиши в *поддержку* 💬💙\n\n"
        "Готов\\(а\\) записаться? Выбирай услугу и бронируй время в *«Услугах»* 💅✂️",
        reply_markup=main_kb,
        parse_mode="MarkdownV2"
    )
    if message.from_user.id in ADMINS:
        await message.answer(f"Вы авторизовались как администратор!", reply_markup=main_admin_kb)
