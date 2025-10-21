import asyncio
from aiogram import Bot

async def set_webhook():
    bot = Bot(token="7548864714:AAFZklf5PYSSGV_qWula7-SnebSxgeBrDTA")
    await bot.set_webhook("https://winproline.ru/webhook")
    print("✅ Webhook o‘rnatildi!")
    await bot.session.close()  # 🔹 sessiyani to‘g‘ri yopamiz

if __name__ == "__main__":
    asyncio.run(set_webhook())
