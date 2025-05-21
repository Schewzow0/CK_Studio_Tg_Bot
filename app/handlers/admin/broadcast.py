from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from app.states.admin_states import AdminStates
from app.config import DB_PATH
import aiosqlite

router = Router()


def get_cancel_broadcast_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить рассылку", callback_data="cancel_broadcast")]
        ]
    )


# Старт рассылки
@router.message(F.text == "Сделать рассылку")
async def start_broadcast(message: Message, state: FSMContext):
    await state.set_state(AdminStates.Broadcast.start_broadcast)
    await message.answer(
        "✉️ Введите сообщение для рассылки. Можно прикрепить фото.\n\nЧтобы отменить, нажмите кнопку ниже.",
        reply_markup=get_cancel_broadcast_kb()
    )


# Обработка inline-кнопки отмены
@router.callback_query(F.data == "cancel_broadcast", AdminStates.Broadcast.start_broadcast)
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Рассылка отменена.")
    await callback.answer()


# Получаем текст/фото и делаем рассылку
@router.message(AdminStates.Broadcast.start_broadcast)
async def process_broadcast(message: Message, state: FSMContext):
    await state.clear()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        cursor = await db.execute("SELECT telegram_id FROM users")
        users = await cursor.fetchall()

    success = 0
    fail = 0

    for (user_id,) in users:
        try:
            if message.photo:
                await message.bot.send_photo(
                    chat_id=user_id,
                    photo=message.photo[-1].file_id,
                    caption=message.caption or '',
                )
            else:
                await message.bot.send_message(chat_id=user_id, text=message.text)
            success += 1
        except Exception:
            fail += 1

    await message.answer(
        f"📬 Рассылка завершена!\n\n✅ Доставлено: {success}\n\n❌ Ошибок: {fail}"
    )
