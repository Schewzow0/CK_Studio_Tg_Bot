from aiogram import Router, F
from aiogram.types import (
    CallbackQuery, Message, BufferedInputFile
)
from aiogram.fsm.context import FSMContext
from app.states.admin_states import AdminStates
from app.config import DB_PATH
from app.keyboards import admin_panel_kb, get_export_menu_kb

import aiosqlite
import io
from openpyxl import Workbook

router = Router()


# --- Хендлер по кнопке "Выгрузка данных" из текстовой клавиатуры ---
@router.message(F.text == "Выгрузка данных")
async def admin_export_menu_from_text(message: Message, state: FSMContext):
    await state.set_state(AdminStates.in_data_export)
    await message.answer(
        "Что вы хотите выгрузить?",
        reply_markup=get_export_menu_kb()
    )


# --- Хендлер: выгрузка клиентов ---
@router.callback_query(F.data == "export_users", AdminStates.in_data_export)
async def export_users(callback: CallbackQuery):
    wb = Workbook()
    ws = wb.active
    ws.title = "Клиенты"
    ws.append(["ID", "Telegram ID", "Имя", "Телефон"])

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        cursor = await db.execute("SELECT id, telegram_id, name, phone FROM users")
        async for row in cursor:
            ws.append(row)

    file_stream = io.BytesIO()
    wb.save(file_stream)
    file_stream.seek(0)

    file = BufferedInputFile(file_stream.read(), filename="clients.xlsx")
    await callback.message.answer_document(
        file, caption="📋 Клиенты успешно выгружены.",
        reply_markup=get_export_menu_kb()
    )
    await callback.answer()


# --- Хендлер: выгрузка записей ---
@router.callback_query(F.data == "export_appointments", AdminStates.in_data_export)
async def export_appointments(callback: CallbackQuery):
    wb = Workbook()
    ws = wb.active
    ws.title = "Записи"
    ws.append(["ID", "ID клиента", "Клиент", "Мастер", "Услуга", "Дата", "Время", "Длительность (мин)"])

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        cursor = await db.execute('''
            SELECT a.id, a.user_id, u.name, m.name, s.name, a.date, a.time, a.duration
            FROM appointments a
            JOIN users u ON a.user_id = u.id
            JOIN masters m ON a.master_id = m.id
            JOIN master_services s ON a.service_id = s.id
        ''')
        async for row in cursor:
            ws.append(row)

    file_stream = io.BytesIO()
    wb.save(file_stream)
    file_stream.seek(0)

    file = BufferedInputFile(file_stream.read(), filename="appointments.xlsx")
    await callback.message.answer_document(
        file, caption="📅 Записи успешно выгружены.",
        reply_markup=get_export_menu_kb()
    )
    await callback.answer()


# --- Кнопка "Назад" ---
@router.callback_query(F.data == "admin_back_to_menu", AdminStates.in_data_export)
async def back_to_admin_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Выберите действие:", reply_markup=admin_panel_kb)
    await callback.answer()
