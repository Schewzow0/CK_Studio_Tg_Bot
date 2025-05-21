from aiogram import Router, F
from aiogram.types import Message

router = Router()


@router.message(F.text == "Скидки")
async def show_discounts(message: Message):
    await message.answer(
        "🎉 *Наши скидки!*\n\n"
        "💅 Маникюр + педикюр — *-15%*\n"
        "🎨 Окрашивание + уход — *-20%*\n"
        "👯 Приведи подругу — *скидка 10% обеим*\n\n"
        "_Подробности об акциях и скидках можно узнать у администратора._",
        parse_mode='Markdown'
    )
