import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiohttp import web

TOKEN = "7548864714:AAHOj3bWV7FRgYXCfAL1yx7Qm7gDlyImK58"
WEBHOOK_URL = "https://winproline.ru/webhook"

bot = Bot(token=TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def start_handler(message: types.Message):
    await message.answer("Hey nima gap!")


async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)
    print("✅ Webhook o‘rnatildi")


async def on_shutdown(app):
    await bot.delete_webhook()
    print("❌ Webhook o‘chirildi")


async def handle_webhook(request):
    data = await request.json()
    update = types.Update(**data)
    await dp.feed_update(bot, update)
    return web.Response(text="ok")


def main():
    app = web.Application()
    app.router.add_post("/webhook", handle_webhook)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    # faqat konteyner ichida ishlaydi
    web.run_app(app, host="0.0.0.0", port=8443)


if __name__ == "__main__":
    main()
