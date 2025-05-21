import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from app.states.admin_states import AdminStates
from aiogram.fsm.context import FSMContext
from app.keyboards import get_service_management_kb, inline_services

from app.config import DB_PATH

router = Router()


@router.message(F.text == "Управление услугами")
async def service_management(message: Message, state: FSMContext):
    await state.set_state(AdminStates.in_service_management)
    await message.answer(
        "Управление услугами. Выберите действие:",
        reply_markup=get_service_management_kb()
    )


# Добавление услуги
@router.callback_query(AdminStates.in_service_management, F.data == "add_service")
async def add_service_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.Services.add_service)
    await callback.message.edit_text(
        "Введите название новой услуги:",
        reply_markup=await inline_services(add_back_button=True)
    )


@router.message(AdminStates.Services.add_service, F.text)
async def save_new_service(message: Message, state: FSMContext):

    service_name = message.text.strip().title()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        cursor = await db.execute(
            "SELECT id FROM services WHERE LOWER(name) = LOWER(?)",
            (service_name,)
        )
        existing_service = await cursor.fetchone()

        if existing_service:
            await message.answer(
                f"❌ Ошибка: услуга «{service_name}» уже существует!\n"
                "Введите другое название:",
                reply_markup=await inline_services(add_back_button=True)
            )
            return

        await db.execute(
                "INSERT INTO services (name) VALUES (?)",
                (service_name,)
            )
        await db.commit()
        await message.answer(
                f"✅ Услуга «{service_name}» успешно добавлена!",
                reply_markup=get_service_management_kb()
            )
        await state.set_state(AdminStates.in_service_management)


# Удаление услуги
@router.callback_query(AdminStates.in_service_management, F.data == "delete_service")
async def delete_service_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.Services.delete_service)
    services_kb = await inline_services(add_back_button=True)
    await callback.message.edit_text(
        "Выберите услугу для удаления:",
        reply_markup=services_kb
    )


@router.callback_query(AdminStates.Services.delete_service, F.data.startswith("service_"))
async def process_delete_service(callback: CallbackQuery, state: FSMContext):
    service_id = callback.data.split("_")[1]

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        await db.execute("DELETE FROM services WHERE id = ?", (service_id,))
        await db.commit()

    await callback.message.edit_text(
        "Услуга удалена. Что дальше?",
        reply_markup=get_service_management_kb()
    )
    await state.set_state(AdminStates.in_service_management)


# Редактирование услуги
@router.callback_query(AdminStates.in_service_management, F.data == "edit_service")
async def edit_service_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.Services.edit_service)
    services_kb = await inline_services(add_back_button=True)
    await callback.message.edit_text(
        "Выберите услугу для редактирования:",
        reply_markup=services_kb
    )


@router.callback_query(AdminStates.Services.edit_service, F.data.startswith("service_"))
async def select_service_to_edit(callback: CallbackQuery, state: FSMContext):
    service_id = callback.data.split("_")[1]

    await state.update_data(service_id=service_id)
    await state.set_state(AdminStates.Services.edit_service_name)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        cursor = await db.execute("SELECT name FROM services WHERE id = ?", (service_id,))
        service_name = (await cursor.fetchone())[0]

    await callback.message.edit_text(
        f"Текущее название услуги: «{service_name}»\n"
        "Введите новое название:",
        reply_markup=await inline_services(add_back_button=True)  # Кнопка "Назад"
    )


@router.message(AdminStates.Services.edit_service_name, F.text)
async def save_edited_service(message: Message, state: FSMContext):

    new_name = message.text.strip().title()
    data = await state.get_data()
    service_id = data['service_id']

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        cursor = await db.execute(
            "SELECT id FROM services WHERE LOWER(name) = LOWER(?) AND id != ?",
            (new_name, service_id)
        )
        existing_service = await cursor.fetchone()

        if existing_service:
            await message.answer(
                f"❌ Ошибка: услуга «{new_name}» уже существует!\n"
                "Введите другое название:",
                reply_markup=await inline_services(add_back_button=True)
            )
            return

        await db.execute(
            "UPDATE services SET name = ? WHERE id = ?",
            (new_name, service_id)
        )
        await db.commit()

    await message.answer(
        f"✅ Услуга успешно изменена на «{new_name}»!",
        reply_markup=get_service_management_kb()
    )
    await state.set_state(AdminStates.in_service_management)


@router.callback_query(F.data == "cancel_action_service")
async def cancel_action_service(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.in_service_management)
    await callback.message.edit_text(
        "Управление услугами:",
        reply_markup=get_service_management_kb()
    )
