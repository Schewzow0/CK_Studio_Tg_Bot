import aiosqlite
import datetime
from app.config import DB_PATH


async def db_start():
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("PRAGMA foreign_keys = ON")
        await conn.execute("PRAGMA journal_mode=WAL;")

        cursor = await conn.cursor()

        # Таблица категорий услуг
        await cursor.execute('''
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
        ''')

        # Таблица мастеров
        await cursor.execute('''
        CREATE TABLE IF NOT EXISTS masters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            about TEXT DEFAULT '',
            interview TEXT DEFAULT '',
            photo TEXT DEFAULT ''
        )
        ''')

        # Таблица, связывающая мастеров с категориями услуг (многие ко многим)
        await cursor.execute('''
        CREATE TABLE IF NOT EXISTS services_masters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_id INTEGER NOT NULL,
            master_id INTEGER NOT NULL,
            FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE,
            FOREIGN KEY (master_id) REFERENCES masters(id) ON DELETE CASCADE,
            UNIQUE(service_id, master_id)  -- Запрещаем дублирование связей
        )
        ''')

        # Таблица конкретных услуг мастеров
        await cursor.execute('''
        CREATE TABLE IF NOT EXISTS master_services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            master_id INTEGER NOT NULL,
            service_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            price REAL NOT NULL CHECK (price > 0),
            duration INTEGER NOT NULL CHECK (duration > 0), -- Длительность в минутах
            photo TEXT DEFAULT '',
            FOREIGN KEY (master_id) REFERENCES masters(id) ON DELETE CASCADE,
            FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE
        )
        ''')

        # Таблица пользователей
        await cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL CHECK (length(phone) >= 10)
        )
        ''')

        # Таблица записей клиентов (Appointments)
        await cursor.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            master_id INTEGER NOT NULL,
            service_id INTEGER NOT NULL,
            date TEXT NOT NULL,  -- Формат YYYY-MM-DD
            time TEXT NOT NULL,  -- Формат HH:MM
            duration INTEGER NOT NULL CHECK (duration > 0),  -- Продолжительность брони
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (master_id) REFERENCES masters(id) ON DELETE CASCADE,
            FOREIGN KEY (service_id) REFERENCES master_services(id) ON DELETE CASCADE,
            UNIQUE (master_id, date, time)  -- Запрещаем двойное бронирование
        )
        ''')

        # Индексы для быстрого поиска
        await cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_telegram ON users(telegram_id)')
        await cursor.execute('CREATE INDEX IF NOT EXISTS idx_appointments_user ON appointments(user_id)')
        await cursor.execute('CREATE INDEX IF NOT EXISTS idx_master_services_master ON master_services(master_id)')
        await cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_appointments_master '
            'ON appointments(master_id, date, time)'
        )

        # ——————— РАБОЧИЙ ГРАФИК МАСТЕРОВ ———————
        # Таблица регулярного графика: по каким дням недели мастер работает
        await cursor.execute('''
        CREATE TABLE IF NOT EXISTS master_working_days (
            master_id INTEGER NOT NULL,
            weekday INTEGER NOT NULL,        -- 0 = Понедельник … 6 = Воскресенье
            is_working INTEGER NOT NULL,     -- 1 = рабочий, 0 = выходной
            PRIMARY KEY (master_id, weekday),
            FOREIGN KEY (master_id) REFERENCES masters(id) ON DELETE CASCADE
        )
        ''')

        # Таблица исключений: конкретные дни, когда мастер не работает
        await cursor.execute("""
        CREATE TABLE IF NOT EXISTS master_time_off (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            master_id   INTEGER NOT NULL,
            date        TEXT    NOT NULL,    -- YYYY-MM-DD
            reason      TEXT    DEFAULT '',
            is_working  INTEGER NOT NULL DEFAULT 0,
            UNIQUE(master_id, date),
            FOREIGN KEY(master_id) REFERENCES masters(id) ON DELETE CASCADE
        );
        """)

        # «Засеем» для каждого уже существующего мастера пн–пт = рабочие, сб–вс = выходные
        await cursor.execute("SELECT id FROM masters")
        masters = await cursor.fetchall()
        for (master_id,) in masters:
            for weekday in range(7):
                is_working = 1 if weekday < 5 else 0
                await cursor.execute(
                    '''
                    INSERT OR IGNORE INTO master_working_days
                       (master_id, weekday, is_working)
                    VALUES (?, ?, ?)
                    ''',
                    (master_id, weekday, is_working)
                )

        await conn.commit()


async def get_service_name(service_id: int) -> str:
    """Получаем название услуги по ID"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT name FROM services WHERE id = ?", (service_id,)) as cursor:
            result = await cursor.fetchone()
    return result[0] if result else "Неизвестная услуга"


async def get_master_name(master_id: int) -> str:
    """Получаем имя мастера по ID"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT name FROM masters WHERE id = ?", (master_id,)) as cursor:
            result = await cursor.fetchone()
    return result[0] if result else "Неизвестный мастер"


async def get_master_schedule(master_id: int) -> set[int]:
    """
    Возвращает множество рабочих дней недели для мастера.
    weekday: 0=Пн … 6=Вс
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT weekday FROM master_working_days WHERE master_id = ? AND is_working = 1",
            (master_id,)
        )
        rows = await cursor.fetchall()
    return {row[0] for row in rows}


async def get_master_time_off(master_id: int) -> set[str]:
    """
    Возвращает множество дат-строк (YYYY-MM-DD), когда мастер вне работы.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT date FROM master_time_off WHERE master_id = ?",
            (master_id,)
        )
        rows = await cursor.fetchall()
    return {row[0] for row in rows}


async def add_time_off(master_id: int, date: str, is_working: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO master_time_off (master_id, date, reason, is_working) VALUES (?, ?, '', ?)",
            (master_id, date, is_working)
        )
        await db.commit()


async def remove_time_off(master_id: int, date: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM master_time_off WHERE master_id = ? AND date = ?",
            (master_id, date)
        )
        await db.commit()


async def get_master_date_exceptions(master_id: int) -> dict[str, int]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT date, is_working FROM master_time_off WHERE master_id = ?",
            (master_id,)
        )
        rows = await cursor.fetchall()
    return {date: flag for date, flag in rows}


# В database.py обновляем функцию get_available_times_for_date
async def get_available_times_for_date(master_id: int, selected_date: str, service_duration: int) -> list[str]:
    """Получаем доступные временные слоты с полным учетом длительности"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Получаем все записи на выбранный день
        cursor = await db.execute('''
            SELECT time, duration 
            FROM appointments 
            WHERE master_id = ? AND date = ?
        ''', (master_id, selected_date))
        appointments = await cursor.fetchall()

        # Получаем рабочие часы мастера
        working_hours = await get_master_working_hours_for_date()

        # Создаем множество заблокированных времен
        blocked_times = set()

        for time, duration in appointments:
            start = datetime.datetime.strptime(time, "%H:%M")
            end = start + datetime.timedelta(minutes=duration)

            # Блокируем все слоты, которые попадают в интервал [start, end)
            current = start
            while current < end:
                blocked_times.add(current.strftime("%H:%M"))
                current += datetime.timedelta(minutes=15)

        # Фильтруем рабочие часы
        available_times = []
        for time in working_hours:
            slot_time = datetime.datetime.strptime(time, "%H:%M")
            slot_end = slot_time + datetime.timedelta(minutes=service_duration)

            # Проверяем, что весь интервал [slot_time, slot_end) свободен
            conflict = False
            check_time = slot_time
            while check_time < slot_end:
                if check_time.strftime("%H:%M") in blocked_times:
                    conflict = True
                    break
                check_time += datetime.timedelta(minutes=15)

            if not conflict:
                available_times.append(time)

        return available_times


async def get_master_working_hours_for_date() -> list[str]:
    """Получаем рабочие часы мастера с интервалом 15 минут, включая последний интервал"""
    start_time = datetime.time(10, 0)
    end_time = datetime.time(21, 0)  # До 21:00 включительно

    # Создаем список всех временных слотов
    current_time = datetime.datetime.combine(datetime.date.today(), start_time)
    end_time_dt = datetime.datetime.combine(datetime.date.today(), end_time)

    working_hours = []
    while current_time <= end_time_dt:
        working_hours.append(current_time.strftime("%H:%M"))
        current_time += datetime.timedelta(minutes=15)

    return working_hours
