import aiosqlite
import calendar
import datetime
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config import DB_PATH

from app.database import get_master_schedule, get_master_date_exceptions, get_master_working_hours_for_date

# Главное меню (для пользователей)
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Услуги"), KeyboardButton(text="Мои записи")],
        [KeyboardButton(text="Поддержка"), KeyboardButton(text="Скидки")],
        [KeyboardButton(text="О нас")]
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите пункт меню..."
)

# Главное меню (для админа)
main_admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Услуги"), KeyboardButton(text="Мои записи")],
        [KeyboardButton(text="Поддержка"), KeyboardButton(text="Наши скидки")],
        [KeyboardButton(text="О нас")],
        [KeyboardButton(text="Админ-панель")]
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите пункт меню..."
)

# Админ-панель
admin_panel_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Управление услугами"), KeyboardButton(text="Управление мастерами")],
        [KeyboardButton(text="Выгрузка данных"), KeyboardButton(text="Отмена записи")],
        [KeyboardButton(text="Управление пользователями"), KeyboardButton(text="Сделать рассылку")],
        [KeyboardButton(text="Назад")]
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите действие..."
)


def get_user_management_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔒 Заблокировать", callback_data="block_user")
    builder.button(text="🔓 Разблокировать", callback_data="unblock_user")
    builder.button(text="◀ Назад", callback_data="admin_back_to_menu")
    return builder.adjust(2, 1).as_markup()


def get_export_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Выгрузить клиентов", callback_data="export_users")
    builder.button(text="📅 Выгрузить записи", callback_data="export_appointments")
    builder.button(text="◀ Назад", callback_data="admin_back_to_menu")
    return builder.adjust(2, 1).as_markup()


def about_inline_kb():
    builder = InlineKeyboardBuilder()

    builder.button(text="🧑‍🎨 О мастерах", callback_data="about_masters")
    builder.button(text="🏠 О студии", callback_data="about_studio")
    builder.button(text="🏆 О достижениях", callback_data="about_achievements")
    builder.button(text="◀ Назад", callback_data="back_to_main")

    return builder.adjust(1).as_markup()


def get_service_management_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить услугу", callback_data="add_service")
    builder.button(text="➖ Удалить услугу", callback_data="delete_service")
    builder.button(text="✏️ Редактировать услугу", callback_data="edit_service")
    builder.button(text="◀️ Назад", callback_data="cancel_management")
    return builder.adjust(2).as_markup()


def get_master_management_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить мастера", callback_data="add_master")
    builder.button(text="➖ Удалить мастера", callback_data="delete_master")
    builder.button(text="✏️ Редактировать мастера", callback_data="edit_master")
    builder.button(text="📅 Настроить график", callback_data="configure_schedule")
    builder.button(text="◀️ Назад", callback_data="cancel_management")
    return builder.adjust(2, 2).as_markup()


def inline_schedule_actions(master_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Внести изменения", callback_data=f"edit_schedule_{master_id}")
    builder.button(text="🔍 Просмотреть график", callback_data=f"view_schedule_{master_id}")
    builder.button(text="◀ Назад",                callback_data="cancel_schedule")
    return builder.adjust(2, 1).as_markup()


def back_to_configure_schedule_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="◀ Назад", callback_data="configure_schedule")
    return builder.as_markup()


months_ru = {
    1: "Январь",  2: "Февраль", 3: "Март",     4: "Апрель",
    5: "Май",     6: "Июнь",    7: "Июль",     8: "Август",
    9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
    }


async def inline_edit_calendar(master_id: int, year=None, month=None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    today = datetime.date.today()
    year = year or today.year
    month = month or today.month

    working = await get_master_schedule(master_id)
    exceptions = await get_master_date_exceptions(master_id)

    cal = calendar.Calendar(firstweekday=calendar.MONDAY)
    month_cal = cal.monthdayscalendar(year, month)

    # Заголовок с переключателями
    builder.row(
        InlineKeyboardButton(text="◀", callback_data=f"prev_month_{master_id}_{year}_{month}"),
        InlineKeyboardButton(text=f"{months_ru[month]} {year}", callback_data="ignore"),
        InlineKeyboardButton(text="▶", callback_data=f"next_month_{master_id}_{year}_{month}")
    )

    weekdays_ru = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    builder.row(*[InlineKeyboardButton(text=wd, callback_data="ignore") for wd in weekdays_ru])

    for week in month_cal:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text="  ", callback_data="ignore"))
            else:
                iso = f"{year:04d}-{month:02d}-{day:02d}"
                wd = datetime.date(year, month, day).weekday()
                mark = (
                    "✅" if iso in exceptions and exceptions[iso] == 1
                    else "❌" if iso in exceptions
                    else "✅" if wd in working else "❌"
                )
                row.append(InlineKeyboardButton(
                    text=f"{day:2d}{mark}",
                    callback_data=f"toggle_{iso}"
                ))
        builder.row(*row)

    builder.row(
        InlineKeyboardButton(text="✔ Готово", callback_data="done_edit"),
        InlineKeyboardButton(text="◀ Назад", callback_data=f"schedule_action_{master_id}")
    )

    return builder.as_markup()


def inline_view_schedule_kb(master_id: int, year: int, month: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="◀", callback_data=f"prev_month_view_{master_id}_{year}_{month}")
    builder.button(text="◀ Назад", callback_data=f"schedule_action_{master_id}")
    builder.button(text="▶", callback_data=f"next_month_view_{master_id}_{year}_{month}")
    return builder.adjust(3).as_markup()


def get_master_edit_menu_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Имя", callback_data="edit_name")
    builder.button(text="✏️ Описание", callback_data="edit_about")
    builder.button(text="✏️ Интервью", callback_data="edit_interview")
    builder.button(text="📷 Фото", callback_data="edit_photo")
    builder.button(text="💅 Услуги мастера", callback_data="edit_services")
    builder.button(text="↩️ Назад", callback_data="cancel_master_action")
    return builder.adjust(2, 2, 1, 1).as_markup()


def get_edit_master_services_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить услугу", callback_data="add_service_to_master")
    builder.button(text="➖ Удалить услугу", callback_data="remove_service_from_master")
    builder.button(text="🔙 Назад", callback_data="back_to_master_edit")
    return builder.adjust(2).as_markup()


def get_cancel_master_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отменить", callback_data="cancel_master_action")
    return builder.as_markup()


# Услуги
async def inline_services(add_back_button: bool = False):
    keyboard = InlineKeyboardBuilder()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        async with db.execute("SELECT id, name FROM services") as cursor:
            rows = await cursor.fetchall()

    for service_id, name in rows:
        keyboard.button(text=name, callback_data=f"service_{service_id}")

    if add_back_button or not rows:
        keyboard.button(text="◀ Назад", callback_data="cancel_action_service")

    return keyboard.adjust(2).as_markup()


# Мастера
async def inline_masters(add_back_button: bool = False) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        async with db.execute("SELECT id, name FROM masters") as cursor:
            rows = await cursor.fetchall()

    for master_id, name in rows:
        keyboard.button(text=name, callback_data=f"master_{master_id}")

    if add_back_button or not rows:
        keyboard.button(text="◀ Назад", callback_data="cancel_action_master")

    return keyboard.adjust(2).as_markup()


async def inline_masters_for_users(add_back_button: bool = False) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        async with db.execute("SELECT id, name FROM masters") as cursor:
            rows = await cursor.fetchall()

    for master_id, name in rows:
        keyboard.button(text=name, callback_data=f"master_for_users_{master_id}")

    if add_back_button or not rows:
        keyboard.button(text="◀ Назад", callback_data="cancel_action_master_users")

    return keyboard.adjust(2).as_markup()


# Услуги мастера
async def inline_master_services(master_id: int, add_back_button: bool = False):
    builder = InlineKeyboardBuilder()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        async with db.execute('''
            SELECT ms.id, ms.name, s.name 
            FROM master_services ms
            JOIN services s ON ms.service_id = s.id
            WHERE ms.master_id = ?
            ORDER BY s.name, ms.name
        ''', (master_id,)) as cursor:
            rows = await cursor.fetchall()

    for service_id, service_name, category_name in rows:
        builder.button(
            text=f"{service_name} ({category_name})",
            callback_data=f"master_service_{service_id}"
        )

    if add_back_button:
        builder.button(text="◀ Назад", callback_data="cancel_action_master")

    return builder.adjust(1).as_markup()


def format_duration(minutes: int) -> str:
    hours = minutes // 60
    minutes = minutes % 60
    parts = []
    if hours:
        parts.append(f"{hours} час{'а' if 1 < hours < 5 else '' if hours == 1 else 'ов'}")
    if minutes:
        parts.append(f"{minutes} минут{'ы' if 1 < minutes < 5 else 'а' if minutes == 1 else ''}")
    return ' '.join(parts) if parts else '0 минут'


# Добавим в keyboards.py новые функции:

async def inline_masters_by_service(service_id: int, add_back_button: bool = False):
    """Клавиатура с мастерами, работающими в конкретной категории услуг"""
    builder = InlineKeyboardBuilder()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        # Получаем мастеров, связанных с этой услугой
        async with db.execute('''
            SELECT m.id, m.name 
            FROM masters m
            JOIN services_masters sm ON m.id = sm.master_id
            WHERE sm.service_id = ?
            ORDER BY m.name
        ''', (service_id,)) as cursor:
            rows = await cursor.fetchall()

    for master_id, name in rows:
        builder.button(text=name, callback_data=f"master_{master_id}")

    if add_back_button or not rows:
        builder.button(text="◀ Назад", callback_data="back_to_services")

    return builder.adjust(2).as_markup()


async def inline_master_services_by_category(master_id: int, service_id: int, add_back_button: bool = False):
    """Клавиатура с услугами мастера в конкретной категории"""
    builder = InlineKeyboardBuilder()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        async with db.execute('''
            SELECT id, name, price, duration 
            FROM master_services 
            WHERE master_id = ? AND service_id = ?
            ORDER BY name
        ''', (master_id, service_id)) as cursor:
            rows = await cursor.fetchall()

    for service_id, name, price, duration in rows:
        duration_str = format_duration(duration)
        builder.button(
            text=f"{name} - {price}₽ ({duration_str})",
            callback_data=f"master_service_{service_id}"
        )

    if add_back_button:
        builder.button(text="◀ Назад", callback_data=f"back_to_masters_{service_id}")

    return builder.adjust(1).as_markup()


async def master_info_kb(master_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="◀ Назад", callback_data="about_masters")
    builder.button(text="📖 Прочитать интервью", callback_data=f"read_interview_{master_id}")
    return builder.adjust(2).as_markup()


async def read_interview_kb(master_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    # Меняем callback_data на тот же префикс, что в show_master_info_for_users
    builder.button(
        text="◀ Назад",
        callback_data=f"master_for_users_{master_id}"
    )
    return builder.as_markup()


def service_description_kb(service_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="◀ Назад", callback_data=f"back_to_services_list_{service_id}")
    builder.button(text="🗓 Записаться", callback_data=f"book_{service_id}")
    return builder.adjust(2).as_markup()


# Календарь для пользователя
async def inline_user_calendar(master_id: int, year=None, month=None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    today = datetime.date.today()
    year = year or today.year
    month = month or today.month

    working_days = await get_master_schedule(master_id)
    day_exceptions = await get_master_date_exceptions(master_id)

    cal = calendar.Calendar(firstweekday=calendar.MONDAY)
    month_cal = cal.monthdayscalendar(year, month)

    builder.row(
        InlineKeyboardButton(text="◀", callback_data=f"user_prev_month_{master_id}_{year}_{month}"),
        InlineKeyboardButton(text=f"{months_ru[month]} {year}", callback_data="ignore"),
        InlineKeyboardButton(text="▶", callback_data=f"user_next_month_{master_id}_{year}_{month}")
    )

    weekdays_ru = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    builder.row(*[InlineKeyboardButton(text=d, callback_data="ignore") for d in weekdays_ru])

    for week in month_cal:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
                continue

            iso_date = f"{year:04d}-{month:02d}-{day:02d}"
            weekday = datetime.date(year, month, day).weekday()

            # Проверка, чтобы не отображать дни, предшествующие сегодняшнему
            if datetime.date(year, month, day) < today:
                # Если день раньше сегодняшнего, показываем его с ❌
                row.append(InlineKeyboardButton(text=f"{day:2d} ❌", callback_data="ignore"))
                continue

            is_available = (
                (iso_date in day_exceptions and day_exceptions[iso_date] == 1) or
                (iso_date not in day_exceptions and weekday in working_days)
            )

            mark = "✅" if is_available else "❌"
            cb = f"select_date_{iso_date}" if is_available else "ignore"
            row.append(InlineKeyboardButton(text=f"{day:2d}{mark}", callback_data=cb))
        builder.row(*row)

    builder.row(InlineKeyboardButton(text="◀ Назад", callback_data="back_to_service_info"))

    return builder.as_markup()


# В keyboards.py обновляем функцию inline_time_selector
async def inline_time_selector(master_id: int, selected_date: str, service_duration: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        cursor = await db.execute('''
            SELECT time, duration 
            FROM appointments 
            WHERE master_id = ? AND date = ?
        ''', (master_id, selected_date))
        appointments = await cursor.fetchall()

    working_hours = await get_master_working_hours_for_date()

    busy_intervals = []
    for time_str, duration in appointments:
        start = datetime.datetime.strptime(time_str, "%H:%M")
        end = start + datetime.timedelta(minutes=duration)
        busy_intervals.append((start, end))

    now = datetime.datetime.now().time()
    is_today = selected_date == datetime.datetime.now().date().isoformat()
    available_times = []
    blocked_forward = set()
    blocked_backward = set()
    past_times = set()

    for time in working_hours:
        new_start = datetime.datetime.strptime(time, "%H:%M")
        new_end = new_start + datetime.timedelta(minutes=service_duration)

        if is_today and new_start.time() < now:
            past_times.add(time)
            continue

        for busy_start, busy_end in busy_intervals:
            if busy_start <= new_start < busy_end:
                blocked_forward.add(time)
                break
            if busy_start < new_end <= busy_end:
                blocked_backward.add(time)
                break
            if new_start < busy_start and new_end > busy_end:
                blocked_forward.add(time)
                break
        else:
            available_times.append(time)

    for time in working_hours:
        if time in available_times:
            builder.button(text=time, callback_data=f"select_time_{time}")
        elif time in past_times:
            builder.button(text=f"🕒 {time}", callback_data=f"occupied_past_{time}")
        elif time in blocked_forward:
            builder.button(text=f"⏳ {time}", callback_data=f"occupied_forward_{time}")
        elif time in blocked_backward:
            builder.button(text=f"✖️ {time}", callback_data=f"occupied_backward_{time}")

    builder.button(text="◀ Назад", callback_data="back_to_calendar")
    return builder.adjust(5).as_markup()
