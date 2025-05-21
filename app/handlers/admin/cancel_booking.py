from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from app.config import DB_PATH
from app.states.admin_states import AdminStates
from app.keyboards import admin_panel_kb

import aiosqlite

router = Router()


# --- Кнопка "Отмена записи" ---
@router.message(F.text == "Отмена записи")
async def prompt_user_id_for_cancel(message: Message, state: FSMContext):
    await state.set_state(AdminStates.in_cancel_booking)
    await message.answer("Введите ID клиента, у которого вы хотите отменить запись:")


# --- Получение записей по ID клиента ---
@router.message(AdminStates.in_cancel_booking, F.text.regexp(r"^\d+$"))
async def show_client_appointments(message: Message, state: FSMContext):
    user_id = int(message.text.strip())
    await state.update_data(cancel_user_id=user_id)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        cursor = await db.execute('''
            SELECT a.id, a.date, a.time, m.name
            FROM appointments a
            JOIN masters m ON a.master_id = m.id
            WHERE a.user_id = ?
            ORDER BY a.date, a.time
        ''', (user_id,))
        appointments = await cursor.fetchall()

    if not appointments:
        await state.clear()
        await message.answer("❌ У клиента нет активных записей.", reply_markup=admin_panel_kb)
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{date} в {time} • {master}",
                callback_data=f"cancel_appointment_{appointment_id}"
            )]
            for appointment_id, date, time, master in appointments
        ] + [[InlineKeyboardButton(text="◀ Назад", callback_data="admin_back_to_menu")]]
    )

    await message.answer("Выберите запись для отмены:", reply_markup=kb)


# --- Обработка отмены записи ---
@router.callback_query(F.data.startswith("cancel_appointment_"), AdminStates.in_cancel_booking)
async def cancel_appointment(callback: CallbackQuery, state: FSMContext):
    appointment_id = int(callback.data.split("_")[-1])

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        await db.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
        await db.commit()

    await state.clear()
    await callback.message.edit_text("✅ Запись успешно отменена.")
    await callback.message.answer("Выберите действие:", reply_markup=admin_panel_kb)
    await callback.answer()


# --- Возврат в админ-панель ---
@router.callback_query(F.data == "admin_back_to_menu", AdminStates.in_cancel_booking)
async def cancel_back_to_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Вы вернулись в админ-панель.", reply_markup=None)
    await callback.message.answer("Выберите действие:", reply_markup=admin_panel_kb)
    await callback.answer()
