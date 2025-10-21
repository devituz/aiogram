import asyncio
from aiogram import Bot

TOKEN = "7548864714:AAHOj3bWV7FRgYXCfAL1yx7Qm7gDlyImK58"
WEBHOOK_URL = "https://06f45320a054.ngrok-free.app/webhook/7548864714:AAHOj3bWV7FRgYXCfAL1yx7Qm7gDlyImK58"

bot = Bot(token=TOKEN)

async def main():
    await bot.set_webhook(WEBHOOK_URL)
    print("Webhook o‘rnatildi ✅")
    await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
