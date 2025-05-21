import asyncio
from datetime import datetime, timedelta, timezone
import aiosqlite
from aiogram import Bot
from app.config import DB_PATH

# Фиксированный часовой пояс Калининграда (UTC+2)
TZ = timezone(timedelta(hours=2))


async def ensure_reminder_column():
    """
    Добавляет в таблицу appointments колонку reminder_sent, если её ещё нет.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        cursor = await db.execute("PRAGMA table_info(appointments)")
        cols = [row[1] for row in await cursor.fetchall()]
        if "reminder_sent" not in cols:
            await db.execute(
                "ALTER TABLE appointments ADD COLUMN reminder_sent INTEGER DEFAULT 0"
            )
            await db.commit()


async def reminder_loop(bot: Bot):
    """
    Фоновая задача: каждые 60 секунд проверяет записи ровно через 24 часа
    по калининградскому времени (UTC+2) и отправляет пользователю напоминание.
    """
    await ensure_reminder_column()
    while True:
        # Текущее время в Калининграде (UTC+2), без секунд и микросекунд
        now = datetime.now(TZ).replace(second=0, microsecond=0)
        # Время для напоминания — ровно через 24 часа
        target = now + timedelta(days=1)
        date_str = target.strftime("%Y-%m-%d")
        time_str = target.strftime("%H:%M")

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("PRAGMA foreign_keys = ON")
            cursor = await db.execute(
                """
                SELECT a.id, u.telegram_id, a.date, a.time, m.name, ms.name
                FROM appointments a
                JOIN users u ON a.user_id = u.id
                JOIN masters m ON a.master_id = m.id
                JOIN master_services ms ON a.service_id = ms.id
                WHERE a.date = ? AND a.time = ? AND (a.reminder_sent IS NULL OR a.reminder_sent = 0)
                """,
                (date_str, time_str)
            )
            rows = await cursor.fetchall()
            for appointment_id, tg_id, apt_date, apt_time, master_name, service_name in rows:
                text = (
                    f"🔔 Напоминание: завтра у вас запись на {apt_date} в {apt_time}.\n"
                    f"Услуга: {service_name}\n"
                    f"Мастер: {master_name}"
                )
                try:
                    await bot.send_message(chat_id=tg_id, text=text)
                except Exception as e:
                    # Логируем ошибки отправки
                    print(f"Ошибка при отправке напоминания для записи {appointment_id}: {e}")
                else:
                    await db.execute(
                        "UPDATE appointments SET reminder_sent = 1 WHERE id = ?",
                        (appointment_id,)
                    )
            await db.commit()

        # Ждём 60 секунд до следующей проверки
        await asyncio.sleep(60)
