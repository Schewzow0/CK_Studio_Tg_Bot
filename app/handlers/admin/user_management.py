from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from app.states.admin_states import AdminStates
from app.config import DB_PATH
from app.keyboards import admin_panel_kb, get_user_management_kb

import aiosqlite

router = Router()


# --- Кнопка "Управление пользователями" ---
@router.message(F.text == "Управление пользователями")
async def in_manage_user_prompt(message: Message, state: FSMContext):
    await state.set_state(AdminStates.in_manage_user)
    await message.answer("Введите ID пользователя для управления (блокировка / разблокировка):")


# --- Обработка ID пользователя ---
@router.message(AdminStates.in_manage_user, F.text.regexp(r"^\d+$"))
async def show_user_management_options(message: Message, state: FSMContext):
    user_id = int(message.text.strip())
    await state.update_data(target_user_id=user_id)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        cursor = await db.execute(
            "SELECT name, phone, is_blocked FROM users WHERE id = ?", (user_id,)
        )
        result = await cursor.fetchone()

    if not result:
        await state.clear()
        await message.answer("❌ Пользователь с таким ID не найден.", reply_markup=admin_panel_kb)
        return

    name, phone, is_blocked = result
    status = "🚫 Заблокирован" if is_blocked else "✅ Активен"

    await message.answer(
        f"*Пользователь ID:* `{user_id}`\n"
        f"*Имя:* {name}\n"
        f"*Телефон:* `{phone}`\n"
        f"*Статус:* {status}\n\n"
        f"Выберите действие:",
        reply_markup=get_user_management_kb(),
        parse_mode="Markdown"
    )


# --- Заблокировать ---
@router.callback_query(F.data == "block_user", AdminStates.in_manage_user)
async def block_user(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = data["target_user_id"]

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        cursor = await db.execute("SELECT is_blocked FROM users WHERE id = ?", (user_id,))
        current_status = (await cursor.fetchone())[0]
        if current_status == 1:
            await callback.answer("Пользователь уже заблокирован.", show_alert=True)
            return

        await db.execute("UPDATE users SET is_blocked = 1 WHERE id = ?", (user_id,))

        await db.execute("DELETE FROM appointments WHERE user_id = ?", (user_id,))

        await db.commit()

    await state.clear()
    await callback.message.edit_text(f"✅ Пользователь ID {user_id} заблокирован, все его записи удалены.")
    await callback.message.answer("Выберите действие:", reply_markup=admin_panel_kb)
    await callback.answer()


# --- Разблокировать ---
@router.callback_query(F.data == "unblock_user", AdminStates.in_manage_user)
async def unblock_user(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = data["target_user_id"]

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        cursor = await db.execute("SELECT is_blocked FROM users WHERE id = ?", (user_id,))
        current_status = (await cursor.fetchone())[0]
        if current_status == 0:
            await callback.answer("Пользователь уже активен.", show_alert=True)
            return
        await db.execute("UPDATE users SET is_blocked = 0 WHERE id = ?", (user_id,))
        await db.commit()

    await state.clear()
    await callback.message.edit_text(f"✅ Пользователь ID {user_id} успешно разблокирован.")
    await callback.message.answer("Выберите действие:", reply_markup=admin_panel_kb)
    await callback.answer()


# --- Назад в админ-панель ---
@router.callback_query(F.data == "admin_back_to_menu", AdminStates.in_manage_user)
async def back_to_admin_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Вы вернулись в админ-панель.", reply_markup=None)
    await callback.message.answer("Выберите действие:", reply_markup=admin_panel_kb)
    await callback.answer()
