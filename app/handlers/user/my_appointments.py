from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from datetime import datetime
import aiosqlite
from app.config import DB_PATH


router = Router()


@router.message(F.text == "Мои записи")
async def show_my_appointments(message: Message):
    await show_my_appointments_for_user(message.from_user.id, message)


# === 1. Кнопка "Мои записи" ===
async def show_my_appointments_for_user(telegram_id: int, target_message: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        cursor = await db.execute('''
            SELECT a.id, a.date, a.time, m.name
            FROM appointments a
            JOIN masters m ON a.master_id = m.id
            JOIN users u ON a.user_id = u.id
            WHERE u.telegram_id = ?
            ORDER BY a.date, a.time
        ''', (telegram_id,))
        appointments = [
            (app_id, date, time, master)
            for app_id, date, time, master in await cursor.fetchall()
            if datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M") > datetime.now()
        ]

    if not appointments:
        await target_message.answer("📭 У вас пока нет активных записей.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{datetime.strptime(date, '%Y-%m-%d').strftime('%d.%m.%Y')} в {time} • {master}",
            callback_data=f"view_appointment_{app_id}"
        )]
        for app_id, date, time, master in appointments
    ])

    await target_message.answer("🗓 Ваши записи:", reply_markup=keyboard)


# === 2. Просмотр информации о записи ===
@router.callback_query(F.data.startswith("view_appointment_"))
async def view_appointment(callback: CallbackQuery, state: FSMContext):
    appointment_id = int(callback.data.split("_")[-1])
    await state.update_data(current_appointment_id=appointment_id)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        cursor = await db.execute('''
            SELECT a.date, a.time, m.name, s.name, s.description, s.price, s.duration, s.photo
            FROM appointments a
            JOIN masters m ON a.master_id = m.id
            JOIN master_services s ON a.service_id = s.id
            WHERE a.id = ?
        ''', (appointment_id,))
        row = await cursor.fetchone()

    if not row:
        await callback.answer("❌ Запись не найдена.", show_alert=True)
        return

    date, time, master_name, service_name, desc, price, duration, photo = row
    formatted_date = datetime.strptime(date, '%Y-%m-%d').strftime('%d.%m.%Y')
    caption = (
        f"📌 *Информация о записи*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🗓 *Дата:* `{formatted_date}`\n"
        f"⏰ *Время:* `{time}`\n"
        f"👤 *Мастер:* {master_name}\n"
        f"💇‍♀️ *Услуга:* {service_name}\n"
        f"💰 *Цена:* `{price}₽`\n"
        f"⏱️ *Длительность:* `{duration} мин`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"*Описание:*\n"
        f"{desc}"
    )

    buttons = [
        [InlineKeyboardButton(text="◀ Назад", callback_data="back_to_my_appointments")],
        [InlineKeyboardButton(text="❌ Отменить запись", callback_data="cancel_my_appointment")]
    ]

    await callback.message.delete()

    if photo:
        await callback.message.answer_photo(
            photo=photo,
            caption=caption,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    else:
        await callback.message.answer(
            text=caption,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )

    await callback.answer()


# === 3. Вернуться ко всем записям ===
@router.callback_query(F.data == "back_to_my_appointments")
async def back_to_my_appointments(callback: CallbackQuery):
    await callback.message.delete()
    await show_my_appointments_for_user(callback.from_user.id, callback.message)
    await callback.answer()


# === 4. Отмена записи ===
@router.callback_query(F.data == "cancel_my_appointment")
async def cancel_my_appointment(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    appointment_id = data.get("current_appointment_id")

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        await db.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
        await db.commit()

    await state.clear()
    await callback.message.delete()

    await callback.message.answer("❌ Ваша запись была успешно отменена.")

    # Показываем оставшиеся записи
    await show_my_appointments_for_user(callback.from_user.id, callback.message)

    await callback.answer()
