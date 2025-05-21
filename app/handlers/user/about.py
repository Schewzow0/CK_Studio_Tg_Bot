import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from app.keyboards import (
    about_inline_kb,
    inline_masters_for_users,
    master_info_kb,
    read_interview_kb,
    main_kb,
    main_admin_kb
)
from app.database import get_master_name
from app.config import ADMINS

from app.config import DB_PATH

router = Router()

# Вопросы для всех мастеров
QUESTIONS = [
    "Как давно ты занимаешься своим делом? Почему это направление?",
    "Как и где ты проходила обучение?",
    "Почему стоит выбрать тебя как мастера?"
]


@router.message(F.text == "О нас")
async def about_us(message: Message):
    await message.answer(
        "Выберите, что вас интересует:",
        reply_markup=about_inline_kb(),
    )


@router.callback_query(F.data == "about_masters")
async def about_masters(callback: CallbackQuery):
    await callback.answer()
    await callback.message.delete()
    await callback.message.answer(
        "🧑‍🎨 Наши мастера — настоящие профессионалы с многолетним опытом и индивидуальным подходом к каждому клиенту.",
        reply_markup=await inline_masters_for_users(add_back_button=True),
    )


@router.callback_query(F.data == "cancel_action_master_users")
async def back_to_masters(callback: CallbackQuery):
    await callback.answer()
    await callback.message.delete()
    await callback.message.answer(
        "Выберите, что вас интересует:",
        reply_markup=about_inline_kb(),
    )


@router.callback_query(F.data.startswith("master_for_users_"))
async def show_master_info_for_users(callback: CallbackQuery):
    await callback.answer()
    await callback.message.delete()

    master_id = int(callback.data.split("_")[-1])

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        cursor = await db.execute(
            "SELECT about, interview, photo FROM masters WHERE id = ?",
            (master_id,),
        )
        row = await cursor.fetchone()

    if not row:
        return await callback.answer("❌ Информация о мастере не найдена.", show_alert=True)

    about_text, interview_text, photo_file_id = row
    name = await get_master_name(master_id)

    await callback.message.answer_photo(
        photo=photo_file_id,
        caption=f"*{name}*\n{about_text}",
        parse_mode="Markdown",
        reply_markup=await master_info_kb(master_id),
    )


@router.callback_query(F.data.startswith("read_interview_"))
async def read_interview(callback: CallbackQuery):
    await callback.answer()
    await callback.message.delete()

    master_id = int(callback.data.split("_")[-1])
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        cursor = await db.execute(
            "SELECT interview FROM masters WHERE id = ?", (master_id,)
        )
        row = await cursor.fetchone()
    interview_text = row[0] if row else ""
    name = await get_master_name(master_id)

    answers = [line.strip() for line in interview_text.splitlines() if line.strip()]
    if len(answers) == len(QUESTIONS):
        interview_block = "\n\n".join(
            f"🌿 *{QUESTIONS[i]}*\n{answers[i]}"
            for i in range(len(QUESTIONS))
        )
    else:
        interview_block = interview_text

    await callback.message.answer(
        f"*Интервью с {name}:*\n\n{interview_block}",
        parse_mode="Markdown",
        reply_markup=await read_interview_kb(master_id),
    )


@router.callback_query(F.data == "about_studio")
async def about_studio(callback: CallbackQuery):
    await callback.answer()
    await callback.message.delete()

    photo_file_id = "AgACAgIAAxkBAAIG52gQtciWgPuSZniQM4QyVvFH6JUHAAIw8jEb3GqISE4kC_yy__3oAQADAgADeAADNgQ"
    caption = (
        "*CK Studio*\n\n"
        "📍 *Адрес:* г\\. Калининград, ул\\. Космонавта Леонова, 47\n"
        "⏰ *Режим работы:* ежедневно с 9:00 до 21:00\n"
        "🌷 *Ориентиры:* ресторан «Тресковия» и магазин «Spar»\n"
        "☎️ *Контакты:* \\+7 \\(928\\) 188\\-09\\-16, \\+7 \\(921\\) 269\\-51\\-57\n"
        "🚗 *Транспорт:* автобусы № 28, 31, 8, 36, маршрутка № 88\n\n"
        "Чтобы попасть в нашу студию, пройдите магазин «Spar»\\. Между магазином и рестораном "
        "«Тресковия» находится поворот направо — поверните туда и пройдите немного вдоль здания\\. "
        "Уже через несколько шагов вы увидите уютный вход в *CK Studio*\\."
    )
    await callback.message.answer_photo(
        photo=photo_file_id,
        caption=caption,
        parse_mode="MarkdownV2",
        reply_markup=about_inline_kb(),
    )


@router.callback_query(F.data == "about_achievements")
async def about_achievements(callback: CallbackQuery):
    await callback.answer()
    await callback.message.delete()

    text = (
        "Наша студия *CK Studio* открылась в 2017 году, и вот уже больше 8 лет мы каждый день "
        "с любовью создаём красоту для вас\\. \n\n"
        "За это время мы стали не просто командой мастеров, а настоящей семьёй, объединённой одной "
        "целью — делать людей счастливее\\! \n\n"
        "Мы гордимся тем, что наши работы отмечались на городских фестивалях красоты и конкурсах\\. "
        "Наши мастера принимали участие в региональных и всероссийских чемпионатах по парикмахерскому "
        "искусству и макияжу, где не раз поднимались на пьедестал\\.\n\n"
        "*В 2021 году* наша студия вошла в *ТОП\\-10 лучших салонов Калининграда* по версии "
        "*Beauty Kaliningrad Awards*, а в *2023* наши специалисты получили дипломы за самые "
        "трендовые окрашивания и авторские техники ухода за волосами\\.\n\n"
        "Кроме того, *CK Studio* была удостоена специальной награды *«Лучшая студия современной "
        "окраски»* на конкурсе *Color Art Fest 2022*, а также получила премию *Beauty Star "
        "Kaliningrad* за высокий уровень сервиса и заботу о клиентах\\.\n\n"
        "Мы постоянно учимся, вдохновляемся новыми идеями, посещаем мастер\\-классы, семинары и "
        "обучающие курсы, чтобы быть на одной волне с мировыми трендами\\.\n\n"
        "Но самое главное наше достижение — это люди\\. Ваши улыбки, ваши доверенные перемены, ваша "
        "благодарность\\. Именно ради этого мы работаем, развиваемся и становимся лучше каждый день\\. "
        "*Спасибо, что выбираете нас\\!*"
    )

    await callback.message.answer(
        text=text,
        parse_mode="MarkdownV2",
        reply_markup=about_inline_kb(),
    )


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    await callback.answer()
    await callback.message.delete()
    await callback.message.answer(f"Выберите действие:", reply_markup=main_kb)
    if callback.from_user.id in ADMINS:
        await callback.message.answer(f"Выберите действие:", reply_markup=main_admin_kb)
