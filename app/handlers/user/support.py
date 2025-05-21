from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from app.config import ADMIN_USERNAME

router = Router()


@router.message(F.text == "Поддержка")
async def support_handler(message: Message):
    if ADMIN_USERNAME:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text="💬 Написать администратору",
                    url=f"https://t.me/{ADMIN_USERNAME}"
                )]
            ]
        )
        await message.answer(
            "Если у вас возникли вопросы или нужна помощь — нажмите кнопку ниже, чтобы связаться с администратором:",
            reply_markup=keyboard
        )
    else:
        await message.answer("К сожалению, контакт администратора не настроен.")
