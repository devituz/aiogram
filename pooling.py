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
    WebAppInfo
)

from database import (
    add_user,
    get_user_by_telegram_id,
    get_all_users,
    update_user_phone,
    add_referral,
    update_referral_subscribed,
    get_referred_count,
    update_user_status,
    update_user_dbb_id,
    get_user_by_dbb_id,
)

# ========================== BOT SOZLAMALARI ==========================
TOKEN = "7810772768:AAG7yf11ErEOuMh1eFn1CMCjDHdL4QjxiM4"
ADMIN_IDS = [7321341340]

CHANNELS = ["@shohbozbekuz"]
CHANNEL_POSTS = {"shohbozbekuz": [3334]}

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ========================== FSM HOLATLARI ==========================
class SendMessageState(StatesGroup):
    waiting_for_photos = State()

class AdminMessageState(StatesGroup):
    waiting_for_message = State()
    waiting_for_broadcast = State()
    waiting_for_single_message = State()

class DBBetStates(StatesGroup):
    waiting_for_dbb_id = State()

# ========================== YORDAMCHI FUNKSIYALAR ==========================
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

async def send_all_channel_posts(chat_id: int):
    try:
        for channel, post_ids in CHANNEL_POSTS.items():
            for post_id in post_ids:
                await bot.forward_message(chat_id=chat_id, from_chat_id=channel, message_id=post_id)
                await asyncio.sleep(0.3)
        await send_main_menu(chat_id)
    except Exception as e:
        print(f"send_all_channel_posts xatosi: {e}")

async def send_main_menu(chat_id: int):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Baraban"), KeyboardButton(text="DBBET ID yuborish")]
        ],
        resize_keyboard=True
    )
    await bot.send_message(chat_id, "Asosiy menyu:", reply_markup=keyboard)

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
            except Exception:
                not_subscribed_channels.append(ch)

    if not_subscribed_channels:
        buttons = [
            [InlineKeyboardButton(text=f"Obuna bo‘lish", url=f"https://t.me/{ch.strip('@')}")]
            for ch in not_subscribed_channels
        ]
        buttons.append([InlineKeyboardButton(text="Tekshirish", callback_data="check_sub")])
        await message.answer(
            "Iltimos, quyidagi kanallarga obuna bo‘ling:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
        return False

    if not user.phone_number:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Telefon raqamni yuborish", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await message.answer("Telefon raqamingizni yuboring:", reply_markup=keyboard)
        return False

    update_referral_subscribed(telegram_id=user_id, status=True)
    return True

# ========================== HANDLERLAR ==========================
@dp.message(CommandStart())
async def start_handler(message: Message, command: CommandStart):
    user_id = message.from_user.id
    args = command.args

    user = get_user_by_telegram_id(user_id)
    referred_by_id = None

    if not user:
        if args:
            try:
                referrer = get_user_by_telegram_id(int(args))
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

@dp.message(Command("shartlar"))
async def shartlar_handler(message: Message):
    if await check_user_requirements(message):
        await send_all_channel_posts(message.chat.id)

@dp.message(F.contact)
async def contact_handler(message: Message):
    phone = message.contact.phone_number
    user_id = message.from_user.id
    update_user_phone(user_id, phone)

    if await is_subscribed(user_id):
        update_referral_subscribed(telegram_id=user_id, status=True)
        await message.answer("Telefon raqamingiz saqlandi!", reply_markup=ReplyKeyboardRemove())

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Kickga obuna bo‘lish", url="https://kick.com/vertual-bola")],
            [InlineKeyboardButton(text="Qo'llanma", url="https://t.me/lalalallalar/14")],
            [InlineKeyboardButton(text="Keyingisi", callback_data="continue_after_kick")]
        ])

        await message.answer(
            "<b>Endi Kick platformamizga obuna bo‘ling</b>\n\n"
            "Agar Kick kanaliga obuna bo‘lmasangiz, <u>konkurslarda ishtirok eta olmaysiz</u>.\n\n"
            "Obuna bo‘ling va pastdagi tugma orqali tasdiqlang!",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        await check_user_requirements(message)

@dp.callback_query(F.data == "continue_after_kick")
async def after_kick(callback: CallbackQuery):
    await callback.message.answer("Rahmat! Endi keyingi shartlar...")
    await send_all_channel_posts(callback.message.chat.id)

@dp.callback_query(F.data == "check_sub")
async def check_subscription(callback: CallbackQuery):
    user_id = callback.from_user.id
    not_subscribed = []
    for ch in CHANNELS:
        if ch.startswith("@"):
            try:
                member = await bot.get_chat_member(ch, user_id)
                if member.status not in ["member", "administrator", "creator"]:
                    not_subscribed.append(ch)
            except:
                not_subscribed.append(ch)

    if not_subscribed:
        buttons = [
            [InlineKeyboardButton(text=f"Obuna bo‘lish", url=f"https://t.me/{ch.strip('@')}")]
            for ch in not_subscribed
        ]
        buttons.append([InlineKeyboardButton(text="Tekshirish", callback_data="check_sub")])
        await callback.message.answer(
            "Hali obuna bo‘lmagansiz!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
        return

    user = get_user_by_telegram_id(user_id)
    if not user.phone_number:
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Telefon raqamni yuborish", request_contact=True)]],
            resize_keyboard=True, one_time_keyboard=True
        )
        await callback.message.answer("Telefon raqamingizni yuboring:", reply_markup=kb)
        return

    update_referral_subscribed(telegram_id=user_id, status=True)
    await send_all_channel_posts(callback.message.chat.id)

@dp.message(F.text == "Baraban")
async def baraban_handler(message: Message):
    if not await check_user_requirements(message):
        return

    user = get_user_by_telegram_id(message.from_user.id)
    dbbet_line = f"DBBET ID: <code>{user.dbbet_id}</code>\n" if user.dbbet_id else "DBBET ID: ID yuborilmagan\n"

    status = {
        "new": "Yangi foydalanuvchi",
        "accept": "O‘yinda ishtirokchisiz",
        "rejected": "Rad etilgan"
    }.get(user.status.value, "Noma’lum")

    text = (
        f"<b>Sizga omad!</b>\n\n"
        f"Ism: {user.fullname}\n"
        f"{dbbet_line}"
        f"Telefon: {user.phone_number}\n"
        f"Status: {status}\n\n"
        f"Pastdagi tugmani bosing → baraban Telegram ichida ochiladi!"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="BARABANNI OCHISH",
            web_app=WebAppInfo(url="https://vertualbolabetkonkurs.winproline.ru/dbbet")
        )
    ]])

    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)

@dp.message(F.text == "DBBET ID yuborish")
async def start_dbb_id(message: Message, state: FSMContext):
    if not await check_user_requirements(message):
        return

    user = get_user_by_telegram_id(message.from_user.id)
    if user.status.value == "accept":
        await message.answer("Siz allaqachon yuborgansiz!")
        return

    await message.answer(
        "DBBET ID yuboring:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Bekor qilish")]],
            resize_keyboard=True
        )
    )
    await state.set_state(DBBetStates.waiting_for_dbb_id)

@dp.message(DBBetStates.waiting_for_dbb_id)
async def receive_dbb_id(message: Message, state: FSMContext):
    if message.text == "Bekor qilish":
        await send_main_menu(message.chat.id)
        await state.clear()
        return

    txt = message.text.strip()
    if not (txt.isdigit() and 1 <= len(txt) <= 14):
        await message.answer("Xato! Faqat raqam yuboring (1-14 belgigacha).")
        return

    user = get_user_by_telegram_id(message.from_user.id)
    caption = (
        f"<b>Yangi DBBET ID</b>\n\n"
        f"Ism: {message.from_user.full_name}\n"
        f"Telefon: {user.phone_number}\n"
        f"TG ID: <code>{message.from_user.id}</code>\n"
        f"Status: {user.status.value}\n"
        f"DBBET ID: <code>{txt}</code>"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Qabul qilish", callback_data=f"acc_{message.from_user.id}_{txt}"),
            InlineKeyboardButton(text="Rad etish", callback_data=f"rej_{message.from_user.id}_0"),
        ],
        [InlineKeyboardButton(text="Xabar yuborish", callback_data=f"msg_{message.from_user.id}_0")]
    ])

    for adm in ADMIN_IDS:
        try:
            await bot.send_message(adm, caption, parse_mode="HTML", reply_markup=kb)
        except Exception as e:
            print(f"Admin {adm} ga xabar yuborilmadi: {e}")

    await message.answer(
        "ID adminlarga yuborildi! Javob kuting...",
        reply_markup=ReplyKeyboardRemove()
    )
    await send_main_menu(message.chat.id)
    await state.clear()

@dp.callback_query(F.data.startswith("acc_"))
async def accept(cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS:
        return await cb.answer("Ruxsat yo‘q!", show_alert=True)

    _, user_id, dbb_id = cb.data.split("_")
    user_id, dbb_id = int(user_id), int(dbb_id)

    update_user_status(user_id, "accept")
    update_user_dbb_id(user_id, dbb_id)

    await cb.answer("Qabul qilindi")
    await cb.message.edit_reply_markup(reply_markup=None)
    await bot.send_message(user_id, "So‘rovingiz qabul qilindi!\nSiz endi o‘yinda ishtirok etasiz!")
    await notify_other_admins(cb, user_id, "qabul qildi")

@dp.callback_query(F.data.startswith("rej_"))
async def reject(cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS:
        return await cb.answer("Ruxsat yo‘q!", show_alert=True)

    user_id = int(cb.data.split("_")[1])
    update_user_status(user_id, "rejected")

    await cb.answer("Rad etildi")
    await cb.message.edit_reply_markup(reply_markup=None)
    await bot.send_message(user_id, "So‘rovingiz rad etildi.\nSabab: Noto‘g‘ri yoki takroriy ID.")
    await notify_other_admins(cb, user_id, "rad etdi")

async def notify_other_admins(cb: CallbackQuery, user_id: int, action: str):
    for admin_id in ADMIN_IDS:
        if admin_id != cb.from_user.id:
            try:
                await bot.send_message(
                    admin_id,
                    f"{cb.from_user.full_name} {action}\nFoydalanuvchi: <code>{user_id}</code>",
                    parse_mode="HTML"
                )
            except:
                pass

# === Qolgan admin funksiyalari (statistika, user_info, xabar yuborish) ===
# (Oldingi kodda bor, joy tejash uchun qoldirdim — kerak bo‘lsa qo‘shib beraman)

@dp.message()
async def all_messages(message: Message):
    await check_user_requirements(message)

# ========================== POLLING ISHGA TUSHIRISH ==========================
async def main():
    print("Bot polling rejimida ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())