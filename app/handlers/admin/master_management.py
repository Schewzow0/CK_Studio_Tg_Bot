import aiosqlite
import datetime
import calendar

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from app.config import DB_PATH

from app.states.admin_states import AdminStates
from app.database import (get_master_schedule,
                          add_time_off,
                          remove_time_off,
                          get_master_date_exceptions,
                          )
from app.keyboards import (get_master_management_kb,
                           get_cancel_master_kb,
                           inline_masters,
                           get_master_edit_menu_kb,
                           get_edit_master_services_kb,
                           inline_services,
                           inline_master_services,
                           format_duration,
                           inline_schedule_actions,
                           inline_edit_calendar,
                           inline_view_schedule_kb,
                           )

router = Router()


# Управление мастерами
@router.message(F.text == "Управление мастерами")
async def master_management(message: Message, state: FSMContext):
    await state.set_state(AdminStates.in_master_management)
    await message.answer(
        "Управление мастерами. Выберите действие:",
        reply_markup=get_master_management_kb()
    )


# Добавление мастера
@router.callback_query(AdminStates.in_master_management, F.data == "add_master")
async def start_add_master(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.Masters.add_name)
    await callback.message.edit_text(
        "Введите имя мастера:",
        reply_markup=get_cancel_master_kb()
    )


@router.message(AdminStates.Masters.add_name, F.text)
async def process_masters_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AdminStates.Masters.add_about)
    await message.answer(
        "Введите описание мастера:",
        reply_markup=get_cancel_master_kb()
    )


@router.message(AdminStates.Masters.add_about, F.text)
async def process_master_about(message: Message, state: FSMContext):
    await state.update_data(about=message.text)
    await state.set_state(AdminStates.Masters.add_interview)
    await message.answer(
        "Введите интервью с мастером:",
        reply_markup=get_cancel_master_kb()
    )


@router.message(AdminStates.Masters.add_interview, F.text)
async def process_master_interview(message: Message, state: FSMContext):
    await state.update_data(interview=message.text)
    await state.set_state(AdminStates.Masters.add_photo)
    await message.answer(
        "Отправьте фото мастера:",
        reply_markup=get_cancel_master_kb()
    )


@router.message(AdminStates.Masters.add_photo, F.photo)
async def process_master_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        cursor = await db.execute(
            "SELECT id FROM masters WHERE LOWER(name) = LOWER(?)",
            (data['name'],)
        )
        existing_master = await cursor.fetchone()

        if existing_master:
            await message.answer(
                "❌ Мастер с таким именем уже существует!\n"
                "Введите другое имя:",
                reply_markup=get_cancel_master_kb()
            )
            await state.set_state(AdminStates.Masters.add_name)
            return

        # Вставка нового мастера
        await db.execute(
            '''INSERT INTO masters (name, about, interview, photo)
            VALUES (?, ?, ?, ?)''',
            (data['name'], data['about'], data['interview'], photo_id)
        )

        # Получаем ID нового мастера
        cursor = await db.execute("SELECT last_insert_rowid()")
        (master_id,) = await cursor.fetchone()

        # Автоматически добавляем график 5/2 (Пн–Пт = рабочие, Сб–Вс = выходные)
        for weekday in range(7):
            is_working = 1 if weekday < 5 else 0
            await db.execute(
                '''INSERT INTO master_working_days (master_id, weekday, is_working)
                VALUES (?, ?, ?)''',
                (master_id, weekday, is_working)
            )

        await db.commit()

    await message.answer(
        f"✅ Мастер {data['name']} успешно добавлен!",
        reply_markup=get_master_management_kb()
    )
    await state.set_state(AdminStates.in_master_management)


@router.message(AdminStates.Masters.add_photo)
async def wrong_masters_photo(message: Message):
    await message.answer(
        "Пожалуйста, отправьте фото мастера:",
        reply_markup=get_cancel_master_kb()
    )


@router.callback_query(
    StateFilter(
        AdminStates.Masters.add_name,
        AdminStates.Masters.add_about,
        AdminStates.Masters.add_interview,
        AdminStates.Masters.add_photo
    ),
    F.data == "cancel_master_action"
)
async def cancel_add_master(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.in_master_management)
    await callback.message.edit_text(
        "Добавление мастера отменено.",
        reply_markup=get_master_management_kb()
    )


# Удаление мастера
@router.callback_query(AdminStates.in_master_management, F.data == "delete_master")
async def delete_master_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.Masters.delete_master)
    masters_kb = await inline_masters(add_back_button=True)
    await callback.message.edit_text(
        "Выберите мастера для удаления:",
        reply_markup=masters_kb
    )


@router.callback_query(AdminStates.Masters.delete_master, F.data.startswith("master_"))
async def process_delete_master(callback: CallbackQuery, state: FSMContext):
    master_id = callback.data.split("_")[1]

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        await db.execute("DELETE FROM masters WHERE id = ?", (master_id,))
        await db.commit()

    await callback.message.edit_text(
        "Мастер удалён. Что дальше?",
        reply_markup=get_master_management_kb()
    )
    await state.set_state(AdminStates.in_master_management)


@router.callback_query(F.data == "cancel_action_master")
async def cancel_action_master(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.in_master_management)
    await callback.message.edit_text(
        "Управление мастерами:",
        reply_markup=get_master_management_kb()
    )


# Редактирование мастера
@router.callback_query(AdminStates.in_master_management, F.data == "edit_master")
async def edit_master_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.Masters.edit_select_master)
    masters_kb = await inline_masters(add_back_button=True)
    await callback.message.edit_text(
        "Выберите мастера для редактирования:",
        reply_markup=masters_kb
    )


@router.callback_query(AdminStates.Masters.edit_select_master, F.data.startswith("master_"))
async def select_master_to_edit(callback: CallbackQuery, state: FSMContext):
    master_id = callback.data.split("_")[1]
    await state.update_data(master_id=master_id)
    await state.set_state(AdminStates.Masters.edit_select_field)
    await callback.message.edit_text(
        "Что вы хотите отредактировать?",
        reply_markup=get_master_edit_menu_kb()
    )


# Редактирование имени
@router.callback_query(AdminStates.Masters.edit_select_field, F.data == "edit_name")
async def edit_name_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.Masters.edit_name)
    await callback.message.edit_text(
        "Введите новое имя мастера:",
        reply_markup=get_cancel_master_kb()
    )


@router.message(AdminStates.Masters.edit_name, F.text)
async def save_edited_name(message: Message, state: FSMContext):
    data = await state.get_data()
    new_name = message.text.strip().title()
    master_id = data['master_id']

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        cursor = await db.execute(
            "SELECT id FROM masters WHERE LOWER(name) = LOWER(?) AND id != ?",
            (new_name, master_id)
        )
        existing_master = await cursor.fetchone()

        if existing_master:
            await message.answer(
                f"❌ Ошибка: мастер с именем «{new_name}» уже существует!\n"
                "Введите другое имя:"
            )
            return

        await db.execute(
            "UPDATE masters SET name = ? WHERE id = ?",
            (new_name, master_id)
        )
        await db.commit()

    await message.answer(
        f"✅ Имя мастера успешно изменено на «{new_name}»",
        reply_markup=get_master_management_kb()
    )
    await state.set_state(AdminStates.in_master_management)


# Редактирование описания
@router.callback_query(AdminStates.Masters.edit_select_field, F.data == "edit_about")
async def edit_about_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.Masters.edit_about)
    await callback.message.edit_text(
        "Введите новое описание мастера:",
        reply_markup=get_cancel_master_kb()
    )


@router.message(AdminStates.Masters.edit_about, F.text)
async def save_edited_about(message: Message, state: FSMContext):
    data = await state.get_data()
    new_about = message.text.strip()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        await db.execute(
            "UPDATE masters SET about = ? WHERE id = ?",
            (new_about, data['master_id'])
        )
        await db.commit()

    await message.answer(
        "✅ Описание успешно обновлено",
        reply_markup=get_master_management_kb()
    )
    await state.set_state(AdminStates.in_master_management)


# Редактирование интервью
@router.callback_query(AdminStates.Masters.edit_select_field, F.data == "edit_interview")
async def edit_interview_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.Masters.edit_interview)
    await callback.message.edit_text(
        "Введите новое интервью мастера:",
        reply_markup=get_cancel_master_kb()
    )


@router.message(AdminStates.Masters.edit_interview, F.text)
async def save_edited_interview(message: Message, state: FSMContext):
    data = await state.get_data()
    new_interview = message.text.strip()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        await db.execute(
            "UPDATE masters SET interview = ? WHERE id = ?",
            (new_interview, data['master_id'])
        )
        await db.commit()

    await message.answer(
        "✅ Интервью успешно обновлено",
        reply_markup=get_master_management_kb()
    )
    await state.set_state(AdminStates.in_master_management)


# Редактирование фото
@router.callback_query(AdminStates.Masters.edit_select_field, F.data == "edit_photo")
async def edit_photo_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.Masters.edit_photo)
    await callback.message.edit_text(
        "Отправьте новое фото мастера:",
        reply_markup=get_cancel_master_kb()
    )


@router.callback_query(
    StateFilter(
        AdminStates.Masters.edit_select_field,
        AdminStates.Masters.edit_name,
        AdminStates.Masters.edit_about,
        AdminStates.Masters.edit_interview,
        AdminStates.Masters.edit_photo,
        AdminStates.Masters.edit_services_menu,
    ),
    F.data == "cancel_master_action"
)
async def cancel_edit_master(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.in_master_management)
    await callback.message.edit_text(
        "Редактирование мастера отменено.",
        reply_markup=get_master_management_kb()
    )


@router.message(AdminStates.Masters.edit_photo, F.photo)
async def save_edited_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    new_photo = message.photo[-1].file_id

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        await db.execute(
            "UPDATE masters SET photo = ? WHERE id = ?",
            (new_photo, data['master_id'])
        )
        await db.commit()

    await message.answer_photo(
        photo=new_photo,
        caption="✅ Фото успешно обновлено",
        reply_markup=get_master_management_kb()
    )
    await state.set_state(AdminStates.in_master_management)


@router.message(AdminStates.Masters.edit_photo)
async def wrong_photo_format(message: Message):
    await message.answer(
        "Пожалуйста, отправьте фото мастера:",
        reply_markup=get_cancel_master_kb()
    )


# Управление услугами мастера
@router.callback_query(AdminStates.Masters.edit_select_field, F.data == "edit_services")
async def edit_services_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.Masters.edit_services_menu)
    await callback.message.edit_text(
        "Управление услугами мастера:",
        reply_markup=get_edit_master_services_kb()
    )


# Выбор категории услуги
@router.callback_query(AdminStates.Masters.edit_services_menu, F.data == "add_service_to_master")
async def add_service_to_master_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.Masters.add_service_select)
    services_kb = await inline_services(add_back_button=True)
    await callback.message.edit_text(
        "Выберите категорию для новой услуги:",
        reply_markup=services_kb
    )


@router.callback_query(AdminStates.Masters.add_service_select, F.data.startswith("service_"))
async def select_service_for_master(callback: CallbackQuery, state: FSMContext):
    service_id = callback.data.split("_")[1]
    await state.update_data(service_id=service_id)
    await state.set_state(AdminStates.Masters.add_service_name)
    await callback.message.edit_text(
        "Введите название услуги:",
        reply_markup=get_cancel_master_kb()
    )


# Обработка названия услуги
@router.message(AdminStates.Masters.add_service_name, F.text)
async def process_master_service_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.answer("Название не может быть пустым. Введите снова:")
        return

    await state.update_data(service_name=name)
    await state.set_state(AdminStates.Masters.add_service_price)
    await message.answer(
        "Введите цену услуги в рублях (только число):",
        reply_markup=get_cancel_master_kb()
    )


# Обработка цены
@router.message(AdminStates.Masters.add_service_price, F.text)
async def process_master_service_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.strip())
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Неверный формат цены. Введите положительное число:")
        return

    await state.update_data(price=price)
    await state.set_state(AdminStates.Masters.add_service_duration)
    await message.answer(
        "Введите продолжительность услуги в минутах (целое число):",
        reply_markup=get_cancel_master_kb()
    )


# Обработка длительности и сохранение
@router.message(AdminStates.Masters.add_service_duration, F.text)
async def process_service_duration(message: Message, state: FSMContext):
    try:
        duration = int(message.text.strip())
        if duration <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Неверный формат. Введите целое число больше нуля:")
        return

    await state.update_data(duration=duration)
    await state.set_state(AdminStates.Masters.add_service_description)
    await message.answer(
        "Введите подробное описание услуги:",
        reply_markup=get_cancel_master_kb()
    )


@router.message(AdminStates.Masters.add_service_description, F.text)
async def process_service_description(message: Message, state: FSMContext):
    description = message.text.strip()
    if not description:
        await message.answer("Описание не может быть пустым. Введите снова:")
        return

    await state.update_data(description=description)
    await state.set_state(AdminStates.Masters.add_service_photo)
    await message.answer(
        "Отправьте фото услуги:",
        reply_markup=get_cancel_master_kb()
    )


@router.message(AdminStates.Masters.add_service_photo, F.photo)
async def save_service_with_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    data = await state.get_data()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        await db.execute("BEGIN TRANSACTION")

        # 1. Проверка на дубликат
        cursor = await db.execute(
            '''SELECT id FROM master_services 
               WHERE master_id = ? AND service_id = ? AND LOWER(name) = LOWER(?)''',
            (data['master_id'], data['service_id'], data['service_name'])
        )
        if await cursor.fetchone():
            await db.rollback()
            await message.answer(
                "❌ У мастера уже есть такая услуга в этой категории!",
                reply_markup=get_master_management_kb()
            )
            await state.set_state(AdminStates.in_master_management)
            return

        # 2. Проверка связи мастер-категория
        cursor = await db.execute(
            '''SELECT 1 FROM services_masters 
               WHERE master_id = ? AND service_id = ?''',
            (data['master_id'], data['service_id'])
        )
        if not await cursor.fetchone():
            await db.execute(
                '''INSERT INTO services_masters (master_id, service_id)
                   VALUES (?, ?)''',
                (data['master_id'], data['service_id'])
            )

        # 3. Добавление услуги
        await db.execute(
            '''INSERT INTO master_services 
               (master_id, service_id, name, description, price, duration, photo)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (
                data['master_id'],
                data['service_id'],
                data['service_name'],
                data['description'],
                data['price'],
                data['duration'],
                photo_id
            )
        )

        await db.commit()

    # 4. Ответ пользователю
    duration_str = format_duration(data['duration'])
    await message.answer_photo(
        photo=photo_id,
        caption=(
            "✅ Услуга добавлена!\n\n"
            f"📌 {data['service_name']}\n"
            f"💰 Цена: {data['price']} руб.\n"
            f"⏱ Длительность: {duration_str}\n"
            f"📝 Описание: {data['description']}"
        )
    )
    await message.answer(
        text="Что бы вы хотели отредактировать у мастера?",
        reply_markup=get_master_edit_menu_kb()
    )
    await state.set_state(AdminStates.Masters.edit_select_field)


@router.message(AdminStates.Masters.add_service_photo)
async def require_service_photo(message: Message):
    await message.answer(
        "❌ Необходимо отправить фотографию услуги!",
        reply_markup=get_cancel_master_kb()
    )


@router.callback_query(
    StateFilter(
        AdminStates.Masters.add_service_select,
        AdminStates.Masters.add_service_name,
        AdminStates.Masters.add_service_price,
        AdminStates.Masters.add_service_duration,
        AdminStates.Masters.add_service_description,
        AdminStates.Masters.add_service_photo
    ),
    F.data == "cancel_master_action"
)
async def cancel_add_service(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.in_master_management)
    await callback.message.edit_text(
        "Добавление услуги отменено.",
        reply_markup=get_master_management_kb()
    )


# Удаление услуги - выбор
@router.callback_query(AdminStates.Masters.edit_services_menu, F.data == "remove_service_from_master")
async def remove_service_from_master_handler(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    services_kb = await inline_master_services(data['master_id'], add_back_button=True)
    await callback.message.edit_text(
        "Выберите услугу для удаления:",
        reply_markup=services_kb
    )
    await state.set_state(AdminStates.Masters.remove_service_select)


# Непосредственное удаление
@router.callback_query(AdminStates.Masters.remove_service_select, F.data.startswith("master_service_"))
async def process_remove_service(callback: CallbackQuery, state: FSMContext):
    master_service_id = int(callback.data.split("_")[2])

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        # Получаем данные об услуге перед удалением
        cursor = await db.execute(
            '''SELECT ms.id, ms.name, ms.master_id, ms.service_id 
            FROM master_services ms WHERE id = ?''',
            (master_service_id,)
        )
        service_data = await cursor.fetchone()

        if not service_data:
            await callback.answer("❌ Услуга не найдена!")
            return

        service_id, service_name, master_id, category_id = service_data

        # Удаляем саму услугу
        await db.execute(
            "DELETE FROM master_services WHERE id = ?",
            (master_service_id,)
        )

        # Проверяем, остались ли у мастера другие услуги в этой категории
        cursor = await db.execute(
            '''SELECT 1 FROM master_services 
            WHERE master_id = ? AND service_id = ? AND id != ?''',
            (master_id, category_id, master_service_id)
        )
        has_other_services = await cursor.fetchone()

        # Если это была последняя услуга мастера в этой категории - удаляем связь
        if not has_other_services:
            await db.execute(
                '''DELETE FROM services_masters 
                WHERE master_id = ? AND service_id = ?''',
                (master_id, category_id)
            )

        await db.commit()

    await callback.message.edit_text(
        f"✅ Услуга «{service_name}» удалена.",
        reply_markup=get_master_management_kb()
    )
    await state.set_state(AdminStates.in_master_management)


# Возврат в меню редактирования
@router.callback_query(AdminStates.Masters.edit_services_menu, F.data == "back_to_master_edit")
async def back_to_master_edit(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.Masters.edit_select_field)
    await callback.message.edit_text(
        "Что вы хотите отредактировать?",
        reply_markup=get_master_edit_menu_kb()
    )


# График мастера
# 1) Старт: нажали «🗓 Настроить график» в меню мастеров
@router.callback_query(AdminStates.in_master_management, F.data == "configure_schedule")
async def configure_schedule_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.Masters.configure_schedule_select_master)
    kb = await inline_masters(add_back_button=True)
    await callback.message.edit_text(
        "Выберите мастера для настройки/просмотра графика:",
        reply_markup=kb
    )
    await callback.answer()


# 2) После выбора мастера — показываем две кнопки: «Внести изменения» / «Просмотреть»
@router.callback_query(
    AdminStates.Masters.configure_schedule_select_master,
    F.data.startswith("master_")
)
async def schedule_master_chosen(callback: CallbackQuery, state: FSMContext):
    master_id = int(callback.data.split("_", 1)[1])
    await state.update_data(master_id=master_id)
    await state.set_state(AdminStates.Masters.configure_schedule_action)

    kb = inline_schedule_actions(master_id)
    await callback.message.edit_text(
        "Что вы хотите сделать с графиком?",
        reply_markup=kb
    )
    await callback.answer()


# 3a) Просмотр текстового календаря с метками

async def render_schedule_view(callback: CallbackQuery, master_id: int, year: int, month: int):
    working = await get_master_schedule(master_id)
    exceptions = await get_master_date_exceptions(master_id)

    months_ru = {
        1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
        5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
        9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
    }
    weekdays_ru = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

    cal = calendar.monthcalendar(year, month)
    width = 35
    header = f"{months_ru[month]} {year}"
    lines = [
        f"{header:^{width}}",
        " ".join(f"{day:^4}" for day in weekdays_ru),
        "─" * width
    ]

    for week in cal:
        row = []
        for day in week:
            if day == 0:
                row.append("    ")
            else:
                iso = f"{year:04d}-{month:02d}-{day:02d}"
                wd = datetime.date(year, month, day).weekday()
                if iso in exceptions:
                    mark = "✅" if exceptions[iso] == 1 else "❌"
                else:
                    mark = "✅" if wd in working else "❌"
                row.append(f"{day:2d}{mark} ")
        lines.append("".join(row))

    lines.append("─" * width)
    lines.append("✅ Рабочий  ❌ Не рабочий")

    text = "```\n" + "\n".join(lines) + "\n```"

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=inline_view_schedule_kb(master_id, year, month)
    )


@router.callback_query(
    AdminStates.Masters.configure_schedule_action,
    F.data.startswith("view_schedule_")
)
async def view_schedule(callback: CallbackQuery):
    master_id = int(callback.data.split("_")[-1])
    today = datetime.date.today()
    year = today.year
    month = today.month

    await render_schedule_view(callback, master_id, year, month)


@router.callback_query(F.data.startswith("next_month_view_"))
async def view_next_month(callback: CallbackQuery):
    parts = callback.data.split("_")
    master_id = int(parts[3])
    year = int(parts[4])
    month = int(parts[5])

    if month == 12:
        month = 1
        year += 1
    else:
        month += 1

    await render_schedule_view(callback, master_id, year, month)
    await callback.answer()


@router.callback_query(F.data.startswith("prev_month_view_"))
async def view_prev_month(callback: CallbackQuery):
    parts = callback.data.split("_")
    master_id = int(parts[3])
    year = int(parts[4])
    month = int(parts[5])

    if month == 1:
        month = 12
        year -= 1
    else:
        month -= 1

    await render_schedule_view(callback, master_id, year, month)
    await callback.answer()


# 3b) Запуск inline-редактора календаря
@router.callback_query(
    AdminStates.Masters.configure_schedule_action,
    F.data.startswith("edit_schedule_")
)
async def edit_schedule(callback: CallbackQuery, state: FSMContext):
    master_id = int(callback.data.split("_")[-1])
    await state.update_data(master_id=master_id)
    await state.set_state(AdminStates.Masters.configure_schedule_edit)

    kb = await inline_edit_calendar(master_id)
    await callback.message.edit_text(
        "Нажмите на дату, чтобы переключить статус (рабочий/нерабочий):",
        reply_markup=kb
    )
    await callback.answer()


# 4) Переключение статуса конкретной даты
@router.callback_query(
    AdminStates.Masters.configure_schedule_edit,
    F.data.startswith("toggle_")
)
@router.callback_query(
    StateFilter(AdminStates.Masters.configure_schedule_edit),
    F.data.startswith("toggle_")
)
async def toggle_time_off(callback: CallbackQuery, state: FSMContext):
    iso = callback.data.split("_", 1)[1]
    data = await state.get_data()
    master_id = data['master_id']

    # День недели по ISO
    wd = datetime.date.fromisoformat(iso).weekday()
    default = wd < 5  # Пн–Пт → рабочие по шаблону

    exceptions = await get_master_date_exceptions(master_id)
    if iso in exceptions:
        await remove_time_off(master_id, iso)
    else:
        await add_time_off(master_id, iso, int(not default))

    # Перерисуем inline-календарь
    calendar_year = data.get("calendar_year")
    calendar_month = data.get("calendar_month")
    kb = await inline_edit_calendar(master_id, calendar_year, calendar_month)

    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer("Статус даты обновлён")


# 5) Завершить редактирование
@router.callback_query(
    AdminStates.Masters.configure_schedule_edit,
    F.data == "done_edit"
)
async def finish_edit(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "✅ График обновлён.",
        reply_markup=get_master_management_kb()
    )
    await state.set_state(AdminStates.in_master_management)
    await callback.answer()


@router.callback_query(
    AdminStates.Masters.configure_schedule_edit,
    F.data.startswith("next_month_")
)
async def next_month_handler(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    master_id = int(parts[2])
    year = int(parts[3])
    month = int(parts[4])

    # Переключение месяца
    if month == 12:
        month = 1
        year += 1
    else:
        month += 1

    kb = await inline_edit_calendar(master_id, year, month)
    await state.update_data(calendar_year=year, calendar_month=month)
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer()


@router.callback_query(
    AdminStates.Masters.configure_schedule_edit,
    F.data.startswith("prev_month_")
)
async def prev_month_handler(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    master_id = int(parts[2])
    year = int(parts[3])
    month = int(parts[4])

    # Переключение месяца
    if month == 1:
        month = 12
        year -= 1
    else:
        month -= 1

    kb = await inline_edit_calendar(master_id, year, month)
    await state.update_data(calendar_year=year, calendar_month=month)
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer()


# 6) Отмена на любом шаге
@router.callback_query(
    StateFilter(
        AdminStates.Masters.configure_schedule_select_master,
        AdminStates.Masters.configure_schedule_action,
        AdminStates.Masters.configure_schedule_edit,
    ),
    F.data == "cancel_schedule"
)
async def cancel_schedule(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.in_master_management)
    await callback.message.edit_text(
        "Настройка графика отменена.",
        reply_markup=get_master_management_kb()
    )
    await callback.answer()


@router.callback_query(
    StateFilter(
        AdminStates.Masters.configure_schedule_action,
        AdminStates.Masters.configure_schedule_edit
    ),
    F.data.startswith("schedule_action_")
)
async def back_to_schedule_actions(callback: CallbackQuery, state: FSMContext):
    master_id = int(callback.data.split("_")[-1])
    # возвращаемся в меню действий
    await state.set_state(AdminStates.Masters.configure_schedule_action)
    kb = inline_schedule_actions(master_id)
    await callback.message.edit_text(
        "Что вы хотите сделать с графиком?",
        reply_markup=kb
    )
    await callback.answer()
