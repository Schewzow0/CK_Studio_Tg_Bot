import asyncio
from aiogram import Bot, Dispatcher
from app.config import BOT_TOKEN
from app.handlers import setup_routers
from app.database import db_start
from app.services.reminders import reminder_loop
from app.services.backup import daily_backup_loop


async def main():
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()

    await db_start()
    dp.include_router(setup_routers())

    # Запуск задачи отправки напоминаний
    _reminder_task = asyncio.create_task(reminder_loop(bot))
    _backup_task = asyncio.create_task(daily_backup_loop(bot))

    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот выключен")
