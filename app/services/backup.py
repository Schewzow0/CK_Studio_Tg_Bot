import asyncio
import shutil
import os
from datetime import datetime, time, timedelta, timezone
from aiogram import Bot
from aiogram.types import BufferedInputFile
from app.config import DB_PATH, ADMINS

# Фиксированный часовой пояс Калининграда
TZ = timezone(timedelta(hours=2))

BACKUP_FOLDER = "database/backups"


async def daily_backup_loop(bot: Bot):
    os.makedirs(BACKUP_FOLDER, exist_ok=True)

    while True:
        now = datetime.now(TZ).replace(second=0, microsecond=0)
        target_time = datetime.combine(now.date(), time(21, 0), tzinfo=TZ)

        if now >= target_time:
            target_time += timedelta(days=1)

        wait_seconds = (target_time - now).total_seconds()
        await asyncio.sleep(wait_seconds)

        # Удаление старых бэкапов (старше 7 дней)
        for file in os.listdir(BACKUP_FOLDER):
            path = os.path.join(BACKUP_FOLDER, file)
            if file.startswith("backup_") and file.endswith(".db"):
                mtime = os.path.getmtime(path)
                age_days = (datetime.now(TZ) - datetime.fromtimestamp(mtime, TZ)).days
                if age_days > 7:
                    os.remove(path)

        # Создание нового бэкапа
        timestamp = datetime.now(TZ).strftime("%Y-%m-%d_%H-%M")
        backup_path = os.path.join(BACKUP_FOLDER, f"backup_{timestamp}.db")
        shutil.copy2(DB_PATH, backup_path)

        # Отправка файла администраторам
        file = BufferedInputFile.from_file(backup_path)
        for admin_id in ADMINS:
            await bot.send_document(admin_id, file, caption="📦 Резервная копия базы данных")
