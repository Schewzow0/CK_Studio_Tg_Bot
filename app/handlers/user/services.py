from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from app.states import BookingStates
from app.keyboards import (
    inline_services,
    inline_masters_by_service,
    inline_master_services_by_category,
    format_duration,
    service_description_kb,
    inline_user_calendar,
    main_kb,
    months_ru,
    inline_time_selector
)
from app.database import get_service_name, get_master_name


from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from app.config import DB_PATH
import aiosqlite
from datetime import datetime

router = Router()


# Начало выбора услуги
@router.message(F.text == "Услуги")
async def services(message: Message, state: FSMContext):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        cursor = await db.execute("SELECT is_blocked FROM users WHERE telegram_id = ?", (message.from_user.id,))
        row = await cursor.fetchone()

    if row and row[0] == 1:
        await message.answer("🚫 Вы были заблокированы. Обратитесь к администратору для восстановления доступа.")
        return

    await state.set_state(BookingStates.choosing_category)
    keyboard = await inline_services()
    await message.answer("Выберите категорию услуги:", reply_markup=keyboard)


# Обработка выбора категории услуги
@router.callback_query(F.data.startswith("service_"), BookingStates.choosing_category)
async def service_selected(callback: CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split("_")[1])
    await state.update_data(service_id=service_id)

    # Получаем название услуги для отображения
    service_name = await get_service_name(service_id)

    await state.set_state(BookingStates.choosing_master)
    keyboard = await inline_masters_by_service(service_id, add_back_button=True)
    await callback.message.edit_text(
        f"Вы выбрали категорию: {service_name}\nТеперь выберите мастера:",
        reply_markup=keyboard
    )
    await callback.answer()


# Обработка возврата к выбору категорий
@router.callback_query(F.data == "back_to_services", BookingStates.choosing_master)
async def back_to_services(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BookingStates.choosing_category)
    keyboard = await inline_services()
    await callback.message.edit_text(
        "Выберите категорию услуги:",
        reply_markup=keyboard
    )
    await callback.answer()


# Обработка выбора мастера
@router.callback_query(F.data.startswith("master_"), BookingStates.choosing_master)
async def master_selected(callback: CallbackQuery, state: FSMContext):
    master_id = int(callback.data.split("_")[1])
    state_data = await state.get_data()
    service_id = state_data['service_id']

    await state.update_data(master_id=master_id)
    await state.set_state(BookingStates.choosing_service)

    keyboard = await inline_master_services_by_category(master_id, service_id, add_back_button=True)

    # Получаем имя мастера и услуги для отображения
    master_name = await get_master_name(master_id)
    service_name = await get_service_name(service_id)

    await callback.message.edit_text(
        f"Категория: {service_name}\nМастер: {master_name}\nВыберите конкретную услугу:",
        reply_markup=keyboard
    )
    await callback.answer()


# Обработка возврата к выбору мастеров
@router.callback_query(F.data.startswith("back_to_masters_"), BookingStates.choosing_service)
async def back_to_masters(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    service_id = state_data.get("service_id")

    if not service_id:
        await callback.answer("Ошибка: категория не найдена.", show_alert=True)
        return

    await state.set_state(BookingStates.choosing_master)

    keyboard = await inline_masters_by_service(service_id, add_back_button=True)
    service_name = await get_service_name(service_id)

    await callback.message.edit_text(
        f"Вы выбрали категорию: {service_name}\nТеперь выберите мастера:",
        reply_markup=keyboard
    )
    await callback.answer()


# Обработка выбора конкретной услуги мастера
@router.callback_query(F.data.startswith("master_service_"), BookingStates.choosing_service)
async def master_service_selected(callback: CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split("_")[-1])
    await state.update_data(master_service_id=service_id)

    # Получаем подробности об услуге
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        cursor = await db.execute('''
            SELECT name, description, price, duration, photo
            FROM master_services
            WHERE id = ?
        ''', (service_id,))
        row = await cursor.fetchone()

    if not row:
        await callback.answer("❌ Услуга не найдена", show_alert=True)
        return

    name, description, price, duration, photo = row
    duration_str = format_duration(duration)

    text = (
        f"*{name}*\n\n"
        f"💬 {description}\n\n"
        f"💰 *Цена:* {price}₽\n"
        f"⏱ *Длительность:* {duration_str}"
    )

    await state.set_state(BookingStates.viewing_service)

    await callback.message.delete()

    if photo:
        await callback.message.answer_photo(
            photo=photo,
            caption=text,
            parse_mode="Markdown",
            reply_markup=service_description_kb(service_id)
        )
    else:
        await callback.message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=service_description_kb(service_id)
        )

    await callback.answer()


@router.callback_query(F.data.startswith("back_to_services_list_"), BookingStates.viewing_service)
async def back_to_services_list(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    master_id = state_data["master_id"]
    category_id = state_data["service_id"]

    # Удаляем старое сообщение с фото
    await callback.message.delete()

    # Отправляем новое сообщение с клавиатурой выбора услуг мастера
    keyboard = await inline_master_services_by_category(master_id, category_id, add_back_button=True)
    master_name = await get_master_name(master_id)
    service_name = await get_service_name(category_id)

    await state.set_state(BookingStates.choosing_service)

    # Отправляем сообщение с клавиатурой
    await callback.message.answer(
        f"Категория: {service_name}\nМастер: {master_name}\nВыберите конкретную услугу:",
        reply_markup=keyboard
    )

    await callback.answer()


@router.callback_query(F.data.startswith("book_"), BookingStates.viewing_service)
async def begin_booking(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    master_id = state_data["master_id"]

    await state.set_state(BookingStates.choosing_date)
    await callback.message.delete()

    calendar_kb = await inline_user_calendar(master_id)

    await callback.message.answer(
        text="📅 Выберите удобный день для записи:",
        reply_markup=calendar_kb
    )

    await callback.answer()


# Функция для получения доступных месяцев
def get_available_months():
    today = datetime.today().date()
    available_months = [today.month]  # Сначала текущий месяц
    # Добавляем следующий месяц
    if today.month < 12:
        available_months.append(today.month + 1)
    else:
        available_months.append(1)  # Если декабрь, то следующий месяц — январь
    return available_months


# Хендлер для кнопки "вперед"
@router.callback_query(F.data.startswith("user_next_month_"), BookingStates.choosing_date)
async def next_month(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    master_id = int(parts[3])
    year = int(parts[4])
    month = int(parts[5])

    available_months = get_available_months()  # Получаем доступные месяцы для перехода

    if month in available_months:
        # Переход на следующий месяц
        if month == 12:
            month = 1
            year += 1
        else:
            month += 1
        # Проверяем, доступен ли следующий месяц
        if month not in available_months:
            await callback.answer("Вы не можете записаться в более поздние месяцы.")
            return
    else:
        await callback.answer("Невозможно перейти в этот месяц.")
        return

    # Обновляем календарь
    calendar_kb = await inline_user_calendar(master_id, year, month)

    # Отправляем новый календарь
    await callback.message.edit_text(
        f"Выберите дату в {months_ru[month]} {year}",
        reply_markup=calendar_kb
    )

    # Обновляем данные о календаре в состоянии
    await state.update_data(calendar_year=year, calendar_month=month)
    await callback.answer()


# Хендлер для кнопки "назад"
@router.callback_query(F.data.startswith("user_prev_month_"), BookingStates.choosing_date)
async def prev_month(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    master_id = int(parts[3])
    year = int(parts[4])
    month = int(parts[5])

    available_months = get_available_months()  # Получаем доступные месяцы для перехода

    if month in available_months:
        # Переход на предыдущий месяц
        if month == 1:
            month = 12
            year -= 1
        else:
            month -= 1
        # Проверяем, доступен ли предыдущий месяц
        if month not in available_months:
            await callback.answer("Вы не можете выбрать месяц ранее текущего.")
            return
    else:
        await callback.answer("Невозможно перейти в этот месяц.")
        return

    # Обновляем календарь
    calendar_kb = await inline_user_calendar(master_id, year, month)

    # Отправляем новый календарь
    await callback.message.edit_text(
        f"Выберите дату в {months_ru[month]} {year}",
        reply_markup=calendar_kb
    )

    # Обновляем данные о календаре в состоянии
    await state.update_data(calendar_year=year, calendar_month=month)
    await callback.answer()


@router.callback_query(F.data.startswith("select_date_"), BookingStates.choosing_date)
async def select_date(callback: CallbackQuery, state: FSMContext):
    selected_date = callback.data.split("_")[-1]
    date_obj = datetime.strptime(selected_date, "%Y-%m-%d")
    formatted_date = date_obj.strftime("%d-%m-%Y")

    await state.update_data(selected_date=selected_date)

    state_data = await state.get_data()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        cursor = await db.execute('''
            SELECT duration FROM master_services WHERE id = ?
        ''', (state_data["master_service_id"],))
        duration = (await cursor.fetchone())[0]

    time_keyboard = await inline_time_selector(
        master_id=state_data["master_id"],
        selected_date=selected_date,
        service_duration=duration
    )

    await callback.message.edit_text(
        f"Вы выбрали дату: {formatted_date}\n\n"
        "⏳ — пересекается с текущей записью\n"
        "✖️ — пересекается с будущей записью\n"
        "🕒 — время в прошлом\n\n"
        "Выберите время:",
        reply_markup=time_keyboard
    )
    await state.set_state(BookingStates.choosing_time)
    await callback.answer()


@router.callback_query(F.data == "back_to_service_info", BookingStates.choosing_date)
async def back_to_service_info(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()

    # Извлекаем данные из состояния, если они существуют
    master_id = state_data.get("master_id")  # ID мастера
    service_id = state_data.get("service_id")  # ID услуги

    # Удаляем старое сообщение с календарем (если оно было)
    await callback.message.delete()

    # Генерируем клавиатуру для выбора услуг мастера
    keyboard = await inline_master_services_by_category(master_id, service_id, add_back_button=True)

    # Получаем имя мастера и название услуги
    master_name = await get_master_name(master_id)
    service_name = await get_service_name(service_id)

    # Отправляем новое сообщение с клавиатурой
    await callback.message.answer(
        f"Категория: {service_name}\nМастер: {master_name}\nВыберите услугу:",
        reply_markup=keyboard
    )

    # Устанавливаем состояние для выбора услуги
    await state.set_state(BookingStates.choosing_service)

    # Завершаем обработку
    await callback.answer()


# Внутренние Утилиты
async def _create_appointment(user_id: int, master_id: int, service_id: int,
                              date: str, time: str, duration: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        await db.execute(
            """INSERT INTO appointments
               (user_id, master_id, service_id, date, time, duration)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, master_id, service_id, date, time, duration)
        )
        await db.commit()


async def _finish_booking(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.set_state(BookingStates.confirming_booking)
    await callback.message.edit_text(
        f"Ваше бронирование на {data['selected_date']} в {data['selected_time']} успешно создано!\n\n✅ Вы записаны!"
    )
    await callback.message.answer("Выберите действие:", reply_markup=main_kb)
    await callback.answer()


# Новый хендлер
@router.callback_query(F.data.startswith("select_time_"), BookingStates.choosing_time)
async def select_time(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    selected_time = callback.data.split("_")[-1]

    # сохраняем выбор времени
    await state.update_data(selected_time=selected_time)

    # достаём из state прежние данные
    data = await state.get_data()
    master_id = data["master_id"]
    service_id = data["master_service_id"]
    selected_date = data["selected_date"]

    # 1) получаем duration из БД
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        cur = await db.execute(
            "SELECT duration FROM master_services WHERE id = ?", (service_id,)
        )
        duration = (await cur.fetchone())[0]

    # 2) сохраняем duration в state (чтобы потом использовать в регистрационном хендлере)
    await state.update_data(duration=duration)

    # проверяем, есть ли юзер
    tg_id = callback.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        cur = await db.execute(
            "SELECT id FROM users WHERE telegram_id = ?", (tg_id,)
        )
        row = await cur.fetchone()

    if row:
        # уже зарегистрирован — сразу создаём бронь
        user_id = row[0]
        await _create_appointment(user_id, master_id, service_id,
                                  selected_date, selected_time, duration)
        await _finish_booking(callback, state)
    else:
        # новый пользователь — просим имя
        await state.set_state(BookingStates.asking_name)
        await callback.message.answer(
            "Похоже, вы у нас впервые. Пожалуйста, введите ваше имя:"
        )


@router.callback_query(F.data == "back_to_calendar", BookingStates.choosing_time)
async def back_to_calendar(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()

    # Проверка наличия данных о месяце и годе
    month = state_data.get("calendar_month")
    year = state_data.get("calendar_year")

    if not month or not year:
        # Если месяц или год не установлены, устанавливаем текущий месяц и год
        today = datetime.today()
        month = today.month
        year = today.year

    # Проверяем, что месяц и год корректны
    if month not in months_ru:
        await callback.answer("Ошибка: Некорректный месяц.")
        return

    # Генерация календаря с использованием данных мастера
    calendar_kb = await inline_user_calendar(state_data["master_id"], year, month)

    # Получаем имя мастера и название услуги
    master_name = await get_master_name(state_data["master_id"])
    service_name = await get_service_name(state_data["service_id"])

    # Устанавливаем состояние для выбора даты
    await state.set_state(BookingStates.choosing_date)

    # Отправляем сообщение с календарем для выбора даты
    await callback.message.edit_text(
        f"Категория: {service_name}\nМастер: {master_name}\nВыберите день для записи в {months_ru[month]} {year}:",
        reply_markup=calendar_kb
    )

    await callback.answer()


@router.callback_query(F.data.startswith("occupied_"), BookingStates.choosing_time)
async def handle_occupied_time(callback: CallbackQuery):
    reason = callback.data.split("_")[1]

    if reason == "forward":
        text = "⏳ Это время уже занято другим клиентом"
    elif reason == "backward":
        text = "✖️ Это время пересекается с записью другого клиента"
    elif reason == "past":
        text = "🕒 Вы не можете записаться на прошедшее время"
    else:
        text = "⛔ Недоступное время"

    await callback.answer(text, show_alert=True)


@router.message(F.text.lower() == "отменить регистрацию", BookingStates.asking_phone)
async def cancel_registration_text(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Регистрация отменена.", reply_markup=main_kb)


@router.message(BookingStates.asking_name, F.text)
async def process_registration_name(message: Message, state: FSMContext):
    await state.update_data(user_name=message.text.strip())
    await state.set_state(BookingStates.asking_phone)

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📲 Отправить номер", request_contact=True)],
            [KeyboardButton(text="Отменить регистрацию")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(
        "Пожалуйста, отправьте свой номер телефона нажатием на кнопку ниже:",
        reply_markup=kb
    )


@router.message(BookingStates.asking_phone, F.contact)
async def process_registration_phone_contact(message: Message, state: FSMContext):
    # пришёл контакт
    phone = message.contact.phone_number
    await _save_user_and_book(message, state, phone)


async def _save_user_and_book(message: Message, state: FSMContext, phone: str):
    data = await state.get_data()
    user_name = data["user_name"]
    master_id = data["master_id"]
    service_id = data["master_service_id"]
    selected_date = data["selected_date"]
    selected_time = data["selected_time"]
    duration = data["duration"]

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        cur = await db.execute(
            "INSERT INTO users (telegram_id, name, phone) VALUES (?, ?, ?)",
            (message.from_user.id, user_name, phone)
        )
        await db.commit()
        user_id = cur.lastrowid

    await _create_appointment(
        user_id,
        master_id,
        service_id,
        selected_date,
        selected_time,
        duration
    )

    await message.answer(
        "Регистрация и бронирование прошли успешно ✅",
        reply_markup=main_kb
    )
    await state.clear()
