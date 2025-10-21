import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
    InputMediaPhoto
)
from aiohttp import web

from database import (
    add_user,
    get_user_by_telegram_id,
    get_all_users,
    update_user_phone,
    add_referral,
    update_referral_subscribed,
    get_referred_count,
    update_user_status
)

# Bot sozlamalari
TOKEN = "7209776053:AAEP3H3By5RyIK4yArNBAOeTOfypMy2_-uI"
ADMIN_ID = 7321341340
CHANNELS = [
    "@Vertual_Bola",
    "https://kick.com/vertual-bola"
]
CHANNEL_POSTS = {"@lalalallalar": [12]}
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = "https://winproline.ru/webhook"
WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = 8443

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ==========================================================
# FSM holatlari
# ==========================================================
class SendMessageState(StatesGroup):
    waiting_for_photos = State()

class AdminMessageState(StatesGroup):
    waiting_for_message = State()
    waiting_for_broadcast = State()
    waiting_for_single_message = State()

# ==========================================================
# Obuna tekshirish
# ==========================================================
async def is_subscribed(user_id: int) -> bool:
    for ch in CHANNELS:
        if ch.startswith("@"):
            try:
                member = await bot.get_chat_member(chat_id=ch, user_id=user_id)
                if member.status not in ["member", "administrator", "creator"]:
                    return False
            except Exception as e:
                print(f"Obuna tekshirishda xato ({ch}): {e}")
                return False
    return True

# ==========================================================
# Kanal postlarini yuborish
# ==========================================================
async def send_all_channel_posts(chat_id: int):
    try:
        for channel, post_ids in CHANNEL_POSTS.items():
            for post_id in post_ids:
                await bot.forward_message(chat_id=chat_id, from_chat_id=channel, message_id=post_id)
                await asyncio.sleep(0.3)
        await send_main_menu(chat_id)
    except Exception as e:
        print(f"send_all_channel_posts xatosi: {e}")

# ==========================================================
# Asosiy menyu
# ==========================================================
async def send_main_menu(chat_id: int):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Referal"), KeyboardButton(text="Screenshoot yuborish")]
        ],
        resize_keyboard=True
    )
    await bot.send_message(chat_id, "Asosiy menyu:", reply_markup=keyboard)

# ==========================================================
# Foydalanuvchi talablarini tekshirish
# ==========================================================
async def check_user_requirements(message: Message) -> bool:
    user_id = message.from_user.id
    user = get_user_by_telegram_id(user_id)

    if not user:
        add_user(
            telegram_id=user_id,
            fullname=message.from_user.full_name,
            username=message.from_user.username
        )
        user = get_user_by_telegram_id(user_id)

    not_subscribed_channels = []
    for ch in CHANNELS:
        if ch.startswith("@"):
            try:
                member = await bot.get_chat_member(chat_id=ch, user_id=user_id)
                if member.status not in ["member", "administrator", "creator"]:
                    not_subscribed_channels.append(ch)
            except Exception as e:
                print(f"Obuna tekshirishda xato ({ch}): {e}")
                not_subscribed_channels.append(ch)

    if not_subscribed_channels:
        buttons = []
        telegram_channels = [ch for ch in CHANNELS if ch.startswith("@")]
        web_links = [ch for ch in CHANNELS if not ch.startswith("@")]

        for ch in telegram_channels:
            buttons.append([InlineKeyboardButton(text="Obuna bo‘lish", url=f"https://t.me/{ch.strip('@')}")])
        for link in web_links:
            buttons.append([InlineKeyboardButton(text="Obuna bo‘lish", url=link)])
        if telegram_channels:
            buttons.append([InlineKeyboardButton(text="Tekshirish", callback_data="check_sub")])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        web_message = "\nSaytga tashrif buyurib Kick platformamizga kirib obuna bo'lish majburiydir!" if web_links else ""
        await message.answer(
            f"Quyidagi Telegram kanallarga obuna bo‘ling:{web_message}",
            reply_markup=keyboard
        )
        return False

    if not user.phone_number:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Telefon raqamni yuborish", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await message.answer("Iltimos, telefon raqamingizni yuboring:", reply_markup=keyboard)
        return False

    update_referral_subscribed(telegram_id=user_id, status=True)
    return True

# ==========================================================
# START
# ==========================================================
@dp.message(CommandStart())
async def start_handler(message: Message, command: CommandStart):
    user_id = message.from_user.id
    start_arg = command.args
    user = get_user_by_telegram_id(user_id)
    referred_by_id = None

    if not user:
        if start_arg:
            try:
                referrer = get_user_by_telegram_id(int(start_arg))
                if referrer:
                    referred_by_id = referrer.telegram_id
            except ValueError:
                pass

        add_user(
            telegram_id=user_id,
            fullname=message.from_user.full_name,
            username=message.from_user.username
        )
        if referred_by_id:
            add_referral(telegram_id=user_id, referred_by_id=referred_by_id)

    if await check_user_requirements(message):
        await send_all_channel_posts(message.chat.id)

# ==========================================================
# SHARTLAR
# ==========================================================
@dp.message(Command("shartlar"))
async def shartlar_handler(message: Message):
    if await check_user_requirements(message):
        await send_all_channel_posts(message.chat.id)

# ==========================================================
# KONTAKT
# ==========================================================
@dp.message(F.contact)
async def contact_handler(message: Message):
    phone = message.contact.phone_number
    user_id = message.from_user.id

    update_user_phone(user_id, phone)
    if await is_subscribed(user_id):
        update_referral_subscribed(telegram_id=user_id, status=True)
        await message.answer("Telefon raqamingiz saqlandi!", reply_markup=ReplyKeyboardRemove())
        await send_all_channel_posts(message.chat.id)
    else:
        await check_user_requirements(message)

# ==========================================================
# OBUNA TEKSHIRISH
# ==========================================================
@dp.callback_query(F.data == "check_sub")
async def check_subscription(callback: CallbackQuery):
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id
    not_subscribed = []
    telegram_channels = [ch for ch in CHANNELS if ch.startswith("@")]
    for ch in telegram_channels:
        try:
            member = await bot.get_chat_member(chat_id=ch, user_id=user_id)
            if member.status not in ["member", "administrator", "creator"]:
                not_subscribed.append(ch)
        except Exception:
            not_subscribed.append(ch)

    if not_subscribed:
        buttons = []
        for ch in telegram_channels:
            buttons.append([InlineKeyboardButton(text="Obuna bo'lish", url=f"https://t.me/{ch.strip('@')}")])
        web_links = [ch for ch in CHANNELS if not ch.startswith("@")]
        for link in web_links:
            buttons.append([InlineKeyboardButton(text="Obuna bo'lish", url=link)])
        if telegram_channels:
            buttons.append([InlineKeyboardButton(text="Tekshirish", callback_data="check_sub")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        web_message = "\nSaytga tashrif buyurib Kick platformamizga kirib obuna bo'lish majburiydir!" if web_links else ""
        await callback.message.answer(
            f"Hali quyidagi Telegram kanallarga obuna bo‘lmagansiz!{web_message}",
            reply_markup=keyboard
        )
        return

    user = get_user_by_telegram_id(user_id)
    if not user.phone_number:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Telefon raqamni yuborish", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await callback.message.answer("Telefon raqamingizni yuboring:", reply_markup=keyboard)
        return

    update_referral_subscribed(telegram_id=user_id, status=True)
    await send_all_channel_posts(chat_id)

# ==========================================================
# REFERAL
# ==========================================================
@dp.message(F.text == "Referal")
async def referral_handler(message: Message):
    if not await check_user_requirements(message):
        return

    user_id = message.from_user.id
    user = get_user_by_telegram_id(user_id)
    referral_link = f"https://t.me/vertualbola_bot?start={user_id}"
    referred_count = get_referred_count(user_id)

    text = (
        f"Sizning referal linkingiz:\n"
        f"<a href='{referral_link}'>{referral_link}</a>\n\n"
        f"Siz 5 tadan {referred_count} do‘stni taklif qildingiz!\n"
        f"Telegram ID: {user.telegram_id}\n"
        f"Telefon raqam: {user.phone_number or 'Yo‘q'}\n"
        f"Status: {user.status.value}\n"
        f"Eslatma agar 5 tadan ko'p do'stizni taklif qilmagan bo'lsangiz konkursda ishtirok eta olmaysiz!"
    )
    await message.answer(text=text, parse_mode="HTML")

# ==========================================================
# SCREENSHOT YUBORISH
# ==========================================================
@dp.message(F.text == "Screenshoot yuborish")
async def start_send_message(message: Message, state: FSMContext):
    if not await check_user_requirements(message):
        return

    user_id = message.from_user.id
    referred_count = get_referred_count(user_id)

    if referred_count < 5:
        await message.answer(
            f"Screenshoot yuborish uchun kamida 5 ta do‘stni taklif qilgan bo‘lishingiz kerak!\n"
            f"Hozirda siz {referred_count} ta do‘st taklif qildingiz."
        )
        return

    await message.answer(
        "Iltimos, faqat rasm (screenshot) va unga izoh (caption) yuboring.\n\nTayyor bo‘lgach, 'Yuborish' tugmasini bosing.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Yuborish"), KeyboardButton(text="Bekor qilish")]],
            resize_keyboard=True
        )
    )
    await state.set_state(SendMessageState.waiting_for_photos)
    await state.update_data(photos=[])

@dp.message(SendMessageState.waiting_for_photos, F.photo)
async def photo_handler(message: Message, state: FSMContext):
    if not await check_user_requirements(message):
        await state.clear()
        return

    data = await state.get_data()
    photos = data.get("photos", [])
    caption = message.caption or "Matn biriktirilmagan."
    photos.append({"file_id": message.photo[-1].file_id, "caption": caption})
    await state.update_data(photos=photos)
    await message.answer(f"{len(photos)}-rasm qabul qilindi.")

@dp.message(SendMessageState.waiting_for_photos, F.text & ~F.text.in_(["Yuborish", "Bekor qilish"]))
async def text_message_warning(message: Message):
    await message.answer("Faqat rasm va unga izoh (caption) yuborishingiz mumkin!")

@dp.message(SendMessageState.waiting_for_photos, F.text == "Yuborish")
async def send_to_admin(message: Message, state: FSMContext):
    if not await check_user_requirements(message):
        await state.clear()
        return

    data = await state.get_data()
    photos = data.get("photos", [])
    user = get_user_by_telegram_id(message.from_user.id)
    referred_count = get_referred_count(message.from_user.id)
    user_id = message.from_user.id

    if not photos:
        await message.answer("Hech qanday rasm yuborilmadi.")
        return

    izohlar = "\n".join([f"{i+1}. {photo['caption']}" for i, photo in enumerate(photos)])

    caption = (
        f"<b>Yangi xabar:</b>\n"
        f"<b>Foydalanuvchi:</b> {message.from_user.full_name}\n"
        f"<b>Username:</b> @{message.from_user.username or 'yo‘q'}\n"
        f"<b>Telefon:</b> {user.phone_number or 'yo‘q'}\n"
        f"<b>ID:</b> <code>{message.from_user.id}</code>\n"
        f"<b>Taklif qilingan do‘stlar:</b> {referred_count} ta\n"
        f"<b>Rasmlar soni:</b> {len(photos)} ta\n"
        f"<b>Izohlar:</b>\n{izohlar}"
    )

    inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Qabul qilish", callback_data=f"accept_user_{user_id}"),
            InlineKeyboardButton(text="Rad etish", callback_data=f"reject_user_{user_id}"),
        ],
        [InlineKeyboardButton(text="Xabar yuborish", callback_data=f"message_user_{user_id}")]
    ])

    media_group = []
    for i, photo in enumerate(photos):
        if i == 0:
            media_group.append(InputMediaPhoto(media=photo["file_id"], caption=caption, parse_mode="HTML"))
        else:
            media_group.append(InputMediaPhoto(media=photo["file_id"]))

    await bot.send_media_group(chat_id=ADMIN_ID, media=media_group)
    await bot.send_message(chat_id=ADMIN_ID, text="Amallar:", reply_markup=inline_keyboard)

    await message.answer("Xabaringiz yuborildi!", reply_markup=ReplyKeyboardRemove())
    await send_main_menu(message.chat.id)
    await state.clear()

@dp.message(SendMessageState.waiting_for_photos, F.text == "Bekor qilish")
async def cancel_send(message: Message, state: FSMContext):
    await message.answer("Xabar yuborish bekor qilindi.", reply_markup=ReplyKeyboardRemove())
    await send_main_menu(message.chat.id)
    await state.clear()

# ==========================================================
# ADMIN CALLBACKS
# ==========================================================
@dp.callback_query(F.data.startswith("accept_user_"))
async def accept_user_callback(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Sizda bu amalni bajarish huquqi yo‘q!", show_alert=True)
        return
    user_id = int(callback.data.split("_")[2])
    update_user_status(user_id, "accept")
    user = get_user_by_telegram_id(user_id)
    await callback.answer("Foydalanuvchi qabul qilindi!")
    await callback.message.edit_reply_markup(reply_markup=None)
    await bot.send_message(chat_id=user_id, text=f"Qabul qilindi\nStatus: {user.status.value}")

@dp.callback_query(F.data.startswith("reject_user_"))
async def reject_user_callback(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Sizda bu amalni bajarish huquqi yo‘q!", show_alert=True)
        return
    user_id = int(callback.data.split("_")[2])
    update_user_status(user_id, "rejected")
    user = get_user_by_telegram_id(user_id)
    await callback.answer("Foydalanuvchi rad etildi!")
    await callback.message.edit_reply_markup(reply_markup=None)
    await bot.send_message(chat_id=user_id, text=f"Rad etildi\nStatus: {user.status.value}")

@dp.callback_query(F.data.startswith("message_user_"))
async def message_user_callback(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Sizda bu amalni bajarish huquqi yo‘q!", show_alert=True)
        return
    user_id = int(callback.data.split("_")[2])
    await state.set_state(AdminMessageState.waiting_for_message)
    await state.update_data(target_user_id=user_id)
    await callback.message.answer("Foydalanuvchiga yuboriladigan xabarni yozing:")
    await callback.answer()

@dp.message(AdminMessageState.waiting_for_message)
async def admin_send_message_handler(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    data = await state.get_data()
    target_user_id = data.get("target_user_id")
    if not target_user_id:
        await message.answer("Xato: Foydalanuvchi topilmadi.")
        await state.clear()
        return
    user = get_user_by_telegram_id(target_user_id)
    try:
        if message.text:
            await bot.send_message(chat_id=target_user_id, text=f"Admindan xabar:\n{message.text}\nStatus: {user.status.value}")
        elif message.photo:
            await bot.send_photo(chat_id=target_user_id, photo=message.photo[-1].file_id,
                                 caption=f"Admindan xabar:\n{message.caption or 'Rasm'}\nStatus: {user.status.value}")
        await message.answer("Xabar yuborildi!")
    except Exception as e:
        await message.answer(f"Xato: {e}")
    await state.clear()

# ==========================================================
# ADMIN COMMANDS
# ==========================================================
@dp.message(Command("broadcast"))
async def broadcast_handler(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Sizda bu amalni bajarish huquqi yo‘q!")
        return
    await message.answer("Barcha foydalanuvchilarga yuboriladigan xabarni yuboring:")
    await state.set_state(AdminMessageState.waiting_for_broadcast)

@dp.message(AdminMessageState.waiting_for_broadcast)
async def broadcast_message_handler(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    users = get_all_users()
    success = error = 0
    for user in users:
        try:
            if message.text:
                await bot.send_message(chat_id=user.telegram_id, text=f"Admindan xabar:\n{message.text}\nStatus: {user.status.value}")
            elif message.photo:
                await bot.send_photo(chat_id=user.telegram_id, photo=message.photo[-1].file_id,
                                     caption=f"Admindan xabar:\n{message.caption or 'Rasm'}\nStatus: {user.status.value}")
            success += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            error += 1
            print(f"Xato (user {user.telegram_id}): {e}")
    await message.answer(f"Muvaffaqiyatli: {success}\nXato: {error}")
    await state.clear()

@dp.message(Command("send_to_user"))
async def send_to_user_handler(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Sizda bu amalni bajarish huquqi yo‘q!")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Masalan: /send_to_user 12345")
        return
    try:
        target_user_id = int(args[1])
        user = get_user_by_telegram_id(target_user_id)
        if not user:
            await message.answer("Foydalanuvchi topilmadi.")
            return
    except ValueError:
        await message.answer("ID raqam bo‘lishi kerak!")
        return
    await state.set_state(AdminMessageState.waiting_for_single_message)
    await state.update_data(target_user_id=target_user_id)
    await message.answer(f"{target_user_id} ga xabar yuboring:")

@dp.message(AdminMessageState.waiting_for_single_message)
async def single_message_handler(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    data = await state.get_data()
    target_user_id = data.get("target_user_id")
    if not target_user_id:
        await message.answer("Xato.")
        await state.clear()
        return
    user = get_user_by_telegram_id(target_user_id)
    try:
        if message.text:
            await bot.send_message(chat_id=target_user_id, text=f"Admindan xabar:\n{message.text}\nStatus: {user.status.value}")
        await message.answer("Xabar yuborildi!")
    except Exception as e:
        await message.answer(f"Xato: {e}")
    await state.clear()

@dp.message(Command("statistika"))
async def statistika_handler(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Sizda bu amalni bajarish huquqi yo‘q!")
        return
    users = get_all_users()
    total_users = len(users)
    accepted_count = len([u for u in users if u.status.value == "accept"])
    stats_message = (
        f"<b>Bot Statistikasi:</b>\n"
        f"<b>Jami foydalanuvchilar:</b> {total_users} ta\n"
        f"<b>Qabul qilingan:</b> {accepted_count} ta\n\n"
        f"<b>Qabul qilinganlar:</b>\n"
    )
    accepted_users = [u for u in users if u.status.value == "accept"]
    if not accepted_users:
        stats_message += "Hozircha yo‘q."
    else:
        for i, user in enumerate(accepted_users, 1):
            stats_message += (
                f"{i}. <b>Ism:</b> {user.fullname or 'Yo‘q'}\n"
                f"   <b>Username:</b> @{user.username or 'Yo‘q'}\n"
                f"   <b>ID:</b> {user.telegram_id}\n"
                f"   <b>Telefon:</b> {user.phone_number or 'Yo‘q'}\n"
                f"   <b>Status:</b> {user.status.value}\n"
                f"   <b>Do‘stlar:</b> {get_referred_count(user.telegram_id)} ta\n\n"
            )
    await message.answer(stats_message, parse_mode="HTML")

# ==========================================================
# YANGI: /user_info — REAL status.value
# ==========================================================
@dp.message(Command("user_info"))
async def user_info_handler(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Sizda bu amalni bajarish huquqi yo‘q!")
        return

    args = message.text.split()
    if len(args) != 2:
        await message.answer(
            "Iltimos, foydalanuvchi Telegram ID sini kiriting.\n\n"
            "<b>Misol:</b> <code>/user_info 123456789</code>",
            parse_mode="HTML"
        )
        return

    try:
        target_id = int(args[1])
    except ValueError:
        await message.answer("Telegram ID faqat raqamlardan iborat bo‘lishi kerak!")
        return

    user = get_user_by_telegram_id(target_id)
    if not user:
        await message.answer(f"ID: <code>{target_id}</code> bilan foydalanuvchi topilmadi.", parse_mode="HTML")
        return

    referred_count = get_referred_count(target_id)
    created_time = user.created_at.strftime("%d.%m.%Y %H:%M") if user.created_at else "Noma'lum"

    text = (
        f"<b>Foydalanuvchi ma'lumotlari</b>\n\n"
        f"<b>Ism:</b> {user.fullname or 'Yo‘q'}\n"
        f"<b>Username:</b> @{user.username or 'Yo‘q'}\n"
        f"<b>Telegram ID:</b> <code>{user.telegram_id}</code>\n"
        f"<b>Telefon raqam:</b> <code>{user.phone_number or 'Yo‘q'}</code>\n"
        f"<b>Status:</b> <code>{user.status.value}</code>\n"
        f"<b>Taklif qilgan do‘stlar:</b> {referred_count} ta\n"
        f"<b>Ro‘yxatdan o‘tgan vaqti:</b> {created_time}"
    )

    await message.answer(text, parse_mode="HTML")

# ==========================================================
# BOSHQA XABARLAR
# ==========================================================
@dp.message()
async def all_message_handler(message: Message):
    await check_user_requirements(message)

# ==========================================================
# WEBHOOK
# ==========================================================
async def handle_webhook(request):
    update = await request.json()
    await dp.feed_raw_update(bot=bot, update=update)
    return web.Response()

async def on_startup(app):
    print("Bot ishga tushdi...")
    await bot.delete_webhook()
    await bot.set_webhook(url=WEBHOOK_URL)
    print(f"Webhook: {WEBHOOK_URL}")

async def on_shutdown(app):
    print("Bot to‘xtatilmoqda...")
    await bot.delete_webhook()
    await bot.session.close()

async def main():
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, handle_webhook)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, WEBAPP_HOST, WEBAPP_PORT)
    await site.start()
    print(f"Server: {WEBAPP_HOST}:{WEBAPP_PORT}")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())