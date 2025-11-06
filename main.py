import asyncio
from aiogram import types
from aiogram import Bot, Dispatcher, F, Router
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
    update_user_status, update_user_dbb_id, get_user_by_dbb_id,
)

# 🔹 Bot sozlamalari
TOKEN = "7209776053:AAEP3H3By5RyIK4yArNBAOeTOfypMy2_-uI"

ADMIN_IDS = [8091009811]


CHANNELS = [
    "@shohbozbekuz",
]
CHANNEL_POSTS = {"@lalalallalar": [12]}
WEBHOOK_PATH = "/webhook"  # Webhook endpoint
WEBHOOK_URL = "https://winproline.ru/webhook"
WEBAPP_HOST = "0.0.0.0"  # Listen on all interfaces
WEBAPP_PORT = 8443  # Internal port for webhook server

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())  # FSM storage



# ==========================================================
# 🔹 FSM holatlari
# ==========================================================
class SendMessageState(StatesGroup):
    waiting_for_photos = State()

class AdminMessageState(StatesGroup):
    waiting_for_message = State()
    waiting_for_broadcast = State()
    waiting_for_single_message = State()


# 🔹 Obuna tekshirish
async def is_subscribed(user_id: int) -> bool:
    for ch in CHANNELS:
        if ch.startswith("@"):  # Telegram kanali bo'lsa
            try:
                member = await bot.get_chat_member(chat_id=ch, user_id=user_id)
                if member.status not in ["member", "administrator", "creator"]:
                    return False
            except Exception as e:
                print(f"❌ Obuna tekshirishda xato ({ch}): {e}")
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
        print(f"❌ send_all_channel_posts xatosi: {e}")


# ==================== FSM STATES ====================
class DBBetStates(StatesGroup):
    waiting_for_dbb_id = State()   # FIXED STATE

# ==========================================================
# 🔹 Asosiy menyu
# ==========================================================
async def send_main_menu(chat_id: int):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎰 Baraban"), KeyboardButton(text="✉️ DBBET ID yuborish")]
        ],
        resize_keyboard=True
    )
    await bot.send_message(chat_id, "📋 Asosiy menyu:", reply_markup=keyboard)

# 🔹 Foydalanuvchi talablarini tekshirish
async def check_user_requirements(message: Message) -> bool:
    user_id = message.from_user.id
    print(f"🔹 check_user_requirements chaqirildi: user_id={user_id}")

    user = get_user_by_telegram_id(user_id)
    print(f"🔹 Foydalanuvchi ma'lumotlari: {user}")

    if not user:
        print("🔹 Foydalanuvchi topilmadi, yangi foydalanuvchi qo‘shilmoqda")
        add_user(
            telegram_id=user_id,
            fullname=message.from_user.full_name,
            username=message.from_user.username
        )
        user = get_user_by_telegram_id(user_id)
        print(f"🔹 Yangi foydalanuvchi qo‘shildi: {user}")

    # 🔸 Faqat Telegram kanallar uchun obuna tekshiruvi
    not_subscribed_channels = []
    telegram_channels = [ch for ch in CHANNELS if ch.startswith("@")]
    print(f"🔹 Tekshiriladigan kanallar: {telegram_channels}")

    for ch in telegram_channels:
        try:
            member = await bot.get_chat_member(chat_id=ch, user_id=user_id)
            print(f"🔹 {ch}: member.status = {member.status}")
            if member.status not in ["member", "administrator", "creator"]:
                print(f"❌ {ch} ga obuna emas")
                not_subscribed_channels.append(ch)
            else:
                print(f"✅ {ch} ga obuna")
        except Exception as e:
            print(f"❌ {ch} tekshirishda xato: {e}")
            not_subscribed_channels.append(ch)

    print(f"🔹 Obuna bo‘lmagan kanallar: {not_subscribed_channels}")

    if not_subscribed_channels:
        buttons = []
        for ch in telegram_channels:
            buttons.append([
                InlineKeyboardButton(
                    text=f"✅ Obuna bo‘lish",
                    url=f"https://t.me/{ch.strip('@')}"
                )
            ])

        buttons.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await message.answer(
            "Iltimos, quyidagi Telegram kanallariga obuna bo‘ling:",
            reply_markup=keyboard
        )
        print("🔹 Obuna bo‘lmagan foydalanuvchi xabari yuborildi")
        return False

    # 🔸 Telefon raqami tekshiruvi
    if not user.phone_number:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📞 Telefon raqamni yuborish", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await message.answer("📱 Iltimos, telefon raqamingizni yuboring:", reply_markup=keyboard)
        print("🔹 Telefon raqami so‘raldi")
        return False

    # 🔸 Obuna bo‘lganini belgilaymiz
    update_referral_subscribed(telegram_id=user_id, status=True)
    print("✅ Foydalanuvchi obuna va telefon tekshiruvidan o'tdi")
    return True





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

@dp.message(Command("shartlar"))
async def shartlar_handler(message: Message):
    if await check_user_requirements(message):
        await send_all_channel_posts(message.chat.id)


@dp.message(F.contact)
async def contact_handler(message: Message):
    phone = message.contact.phone_number
    user_id = message.from_user.id

    # Telefon raqamini saqlaymiz
    update_user_phone(user_id, phone)

    # Foydalanuvchi obuna bo‘lgan bo‘lsa
    if await is_subscribed(user_id):
        update_referral_subscribed(telegram_id=user_id, status=True)
        await message.answer("✅ Telefon raqamingiz saqlandi!", reply_markup=ReplyKeyboardRemove())

        # Kick platformasiga obuna bo‘lish xabari
        buttons = [
            [InlineKeyboardButton(text="🎯 Kickga obuna bo‘lish", url="https://kick.com/vertual-bola")],
            [InlineKeyboardButton(text="📃 Qo'llanma", url="https://t.me/lalalallalar/14")],
            [InlineKeyboardButton(text="➡️ Keyingisi", callback_data="continue_after_kick")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await message.answer(
            "<b>🎬 Endi Kick platformamizga obuna bo‘ling 👇</b>\n\n"
            "⚠️ <b>Diqqat!</b> Agar siz Kick kanaliga obuna bo‘lmasangiz, <u>konkurslarda ishtirok eta olmaysiz</u> va "
            "yangi imkoniyatlardan bebahra qolasiz.\n\n"
            "✅ <b>Obuna bo‘ling va pastdagi tugma orqali tasdiqlang!</b>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )


    else:
        # Agar hali Telegram kanallarga obuna bo‘lmagan bo‘lsa
        await check_user_requirements(message)


# ➡️ Keyingisi tugmasi bosilganda
@dp.callback_query(F.data == "continue_after_kick")
async def after_kick(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    await callback.message.answer("✅ Rahmat! Endi keyingi shartimiz quydagicha!")
    await send_all_channel_posts(chat_id)



@dp.callback_query(F.data == "check_sub")
async def check_subscription(callback: CallbackQuery):
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id

    print(f"🔹 check_subscription chaqirildi: user_id={user_id}")

    # Telegram kanallari tekshiriladi
    not_subscribed = []
    telegram_channels = [ch for ch in CHANNELS if ch.startswith("@")]
    print(f"🔹 Tekshiriladigan kanallar: {telegram_channels}")

    for ch in telegram_channels:
        try:
            member = await bot.get_chat_member(chat_id=ch, user_id=user_id)
            print(f"🔹 {ch}: member.status = {member.status}")

            if member.status not in ["member", "administrator", "creator"]:
                print(f"❌ {ch} ga obuna emas")
                not_subscribed.append(ch)
            else:
                print(f"✅ {ch} ga obuna")
        except Exception as e:
            print(f"❌ {ch} tekshirishda xato: {e}")
            not_subscribed.append(ch)

    print(f"🔹 Obuna bo‘lmagan kanallar: {not_subscribed}")

    # Agar Telegram kanaliga obuna bo'lmagan bo'lsa
    if not_subscribed:
        buttons = []
        for ch in telegram_channels:
            buttons.append(
                [InlineKeyboardButton(
                    text=f"✅ Obuna bo'lish",
                    url=f"https://t.me/{ch.strip('@')}"
                )]
            )

        # Tekshirish tugmasi
        if telegram_channels:
            buttons.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.answer(
            "⚠️ Hali quyidagi Telegram kanallarga obuna bo‘lmagansiz!",
            reply_markup=keyboard
        )
        print("🔹 Obuna bo‘lmagan foydalanuvchi xabari yuborildi")
        return

    # Telefon raqami tekshiruvi
    user = get_user_by_telegram_id(user_id)
    print(f"🔹 Foydalanuvchi: {user}")

    if not user.phone_number:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📞 Telefon raqamni yuborish", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await callback.message.answer("📱 Telefon raqamingizni yuboring:", reply_markup=keyboard)
        print("🔹 Telefon raqami so‘raldi")
        return

    # Foydalanuvchi obuna va telefon tekshiruvidan o'tgan bo'lsa
    update_referral_subscribed(telegram_id=user_id, status=True)
    await send_all_channel_posts(chat_id)
    print("✅ Foydalanuvchi obuna va telefon tekshiruvidan o'tdi, postlar yuborildi")




# ——— BARABAN BUTTON (text) ———
@dp.message(F.text == "🎰 Baraban")
async def baraban_handler(message: Message):
    if not await check_user_requirements(message):
        return

    user = get_user_by_telegram_id(message.from_user.id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🎰 BARABANNI OCHISH",
            web_app=types.WebAppInfo(url="https://vertualbolabetkonkurs.winproline.ru/dbbet")
        )
    ]])

    # DBBET ID — bor bo'lsa ID, yo'q bo'lsa "ID yuborilmagan"
    dbbet_line = f"🆔 <b>DBBET ID:</b> <code>{user.dbbet_id}</code>\n" if user.dbbet_id else "🆔 <b>DBBET ID:</b> ID yuborilmagan\n"

    # Status — o‘zbekcha
    if user.status.value == "new":
        status = "🆕 <b>Yangi foydalanuvchi</b>"
    elif user.status.value == "accept":
        status = "✅ <b>O‘yinda ishtirokchisiz</b>"
    else:
        status = "❌ <b>Rad etilgan</b>"

    # Text tayyorlash
    text = (
        f"🎉 <b>Sizga omad!</b>\n\n"
        f"👤 <b>Ism:</b> {user.fullname}\n"
        f"{dbbet_line}"
        f"📞 <b>Telefon:</b> {user.phone_number}\n"
        f"📊 <b>Status:</b> {status}\n\n"
        f"🔥 Pastdagi tugmani bosing → baraban <u>Telegram ichida</u> ochiladi!"
    )

    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)


# ---------- DBBET ID ----------
@dp.message(F.text == "✉️ DBBET ID yuborish")
async def start_dbb_id(message: Message, state: FSMContext):
    if not await check_user_requirements(message):
        return
    user = get_user_by_telegram_id(message.from_user.id)
    if user.status.value == "accept":
        await message.answer("⚠️ Siz allaqachon yuborgansiz!")
        return

    await message.answer(
        "🔢 DBBET ID yuboring:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
            resize_keyboard=True
        )
    )
    await state.set_state(DBBetStates.waiting_for_dbb_id)

@dp.message(DBBetStates.waiting_for_dbb_id)
async def receive_dbb_id(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("⚠️ Xato! Faqat DBBET ID raqam yuboring.")
        return

    txt = message.text.strip()

    if txt == "❌ Bekor qilish":
        await send_main_menu(message.chat.id)
        await state.clear()
        return

    if not (txt.isdigit() and 1 <= len(txt) <= 14):
        await message.answer("⚠️ Xato! Faqat DBBET ID raqam yuboring.")
        return

    user = get_user_by_telegram_id(message.from_user.id)
    ref_cnt = get_referred_count(message.from_user.id)

    # 🔹 Statusni chiroyli ko‘rsatish
    status_map = {
        "new": "🆕 Yangi foydalanuvchi",
        "accept": "✅ Qabul qilingan",
        "rejected": "❌ Rad etilgan"
    }
    user_status = status_map.get(user.status.value, "Noma’lum")

    caption = (
        f"<b>📩 Yangi DBBET ID</b>\n\n"
        f"👤 <b>Ism:</b> {message.from_user.full_name}\n"
        f"📱 <b>Telefon:</b> {user.phone_number}\n"
        f"🆔 <b>TG ID:</b> <code>{message.from_user.id}</code>\n"
        f"📊 <b>Status:</b> {user_status}\n"
        f"🔢 <b>DBBET ID:</b> <code>{txt}</code>"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Qabul qilish", callback_data=f"acc_{message.from_user.id}_{txt}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"rej_{message.from_user.id}_0"),
        ],
        [InlineKeyboardButton(text="✉️ Xabar yuborish", callback_data=f"msg_{message.from_user.id}_0")]
    ])

    for adm in ADMIN_IDS:
        try:
            await bot.send_message(adm, caption, parse_mode="HTML", reply_markup=kb)
        except Exception as e:
            print(f"Admin {adm} ga yuborishda xato: {e}")

    await message.answer(
        "✅ ID muvaffaqiyatli adminlarga yuborildi!\n"
        "Javob kelguncha kutib turing...",
        reply_markup=ReplyKeyboardRemove()
    )
    await send_main_menu(message.chat.id)
    await state.clear()


@dp.callback_query(F.data.startswith("acc_"))
async def accept(cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS:
        return await cb.answer("❌ Ruxsat yo‘q!", show_alert=True)

    parts = cb.data.split("_")
    user_id = int(parts[1])
    dbb_id = parts[2]  # 0 emas, real ID

    update_user_status(user_id, "accept")
    update_user_dbb_id(user_id, int(dbb_id))

    await cb.answer("✅ Qabul qilindi")
    await cb.message.edit_reply_markup(reply_markup=None)
    await bot.send_message(user_id, "🎉 So‘rovingiz qabul qilindi!\nSiz endi o‘yinda ishtirok etasiz!")
    await notify_other_admins(cb, user_id, "✅ qabul qildi")


@dp.callback_query(F.data.startswith("rej_"))
async def reject(cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS:
        return await cb.answer("❌ Ruxsat yo‘q!", show_alert=True)

    user_id = int(cb.data.split("_")[1])
    update_user_status(user_id, "rejected")

    await cb.answer("❌ Rad etildi")
    await cb.message.edit_reply_markup(reply_markup=None)
    await bot.send_message(user_id, "❌ So‘rovingiz rad etildi.\nSabab: Noto‘g‘ri yoki takroriy ID.")
    await notify_other_admins(cb, user_id, "❌ rad etdi")


async def notify_other_admins(cb: CallbackQuery, user_id: int, action: str):
    for admin_id in ADMIN_IDS:
        if admin_id != cb.from_user.id:
            try:
                await bot.send_message(
                    admin_id,
                    f"ℹ️ <b>{cb.from_user.full_name}</b> {action}\n"
                    f"🆔 Foydalanuvchi: <code>{user_id}</code>",
                    parse_mode="HTML"
                )
            except:
                pass

@dp.callback_query(F.data.startswith("msg_"))
async def send_message_mode(cb: CallbackQuery, state: FSMContext):
    if cb.from_user.id not in ADMIN_IDS:
        return await cb.answer("❌ Ruxsat yo‘q!", show_alert=True)

    user_id = int(cb.data.split("_")[1])
    await state.set_state(AdminMessageState.waiting_for_message)
    await state.update_data(target_user_id=user_id)

    await cb.message.answer(
        f"✉️ <b>Xabar yozing:</b>\n"
        f"👤 Foydalanuvchi ID: <code>{user_id}</code>",
        parse_mode="HTML"
    )
    await cb.answer("Xabar rejimi yoqildi")



@dp.message(AdminMessageState.waiting_for_message)
async def admin_send_message_handler(message: Message, state: FSMContext):
    # 🔹 Faqat ro'yxatda bor adminlargina xabar yubora oladi
    if message.from_user.id not in ADMIN_IDS:
        return

    data = await state.get_data()
    target_user_id = data.get("target_user_id")

    if not target_user_id:
        await message.answer("❌ Xato: Foydalanuvchi topilmadi.")
        await state.clear()
        return

    user = get_user_by_telegram_id(target_user_id)

    try:
        # 🟢 Matnli xabar
        if message.text:
            await bot.send_message(
                chat_id=target_user_id,
                text=(
                    f"📩 <b>Admindan yangi xabar:</b>\n"
                    f"💬 <i>{message.text}</i>\n\n"
                    f"📌 <b>Holat:</b> {user.status.value}"
                ),
                parse_mode="HTML"
            )

        # 🟡 Rasm
        elif message.photo:
            await bot.send_photo(
                chat_id=target_user_id,
                photo=message.photo[-1].file_id,
                caption=(
                    f"🖼 <b>Admindan yangi rasm:</b>\n"
                    f"💬 <i>{message.caption or 'Rasm'}</i>\n\n"
                    f"📌 <b>Holat:</b> {user.status.value}"
                ),
                parse_mode="HTML"
            )

        # 📄 Hujjat
        elif message.document:
            await bot.send_document(
                chat_id=target_user_id,
                document=message.document.file_id,
                caption=(
                    f"📄 <b>Admindan yangi hujjat:</b>\n"
                    f"💬 <i>{message.caption or 'Hujjat'}</i>\n\n"
                    f"📌 <b>Holat:</b> {user.status.value}"
                ),
                parse_mode="HTML"
            )

        # 🎥 Video
        elif message.video:
            await bot.send_video(
                chat_id=target_user_id,
                video=message.video.file_id,
                caption=(
                    f"🎥 <b>Admindan yangi video:</b>\n"
                    f"💬 <i>{message.caption or 'Video'}</i>\n\n"
                    f"📌 <b>Holat:</b> {user.status.value}"
                ),
                parse_mode="HTML"
            )

        # 🎵 Audio
        elif message.audio:
            await bot.send_audio(
                chat_id=target_user_id,
                audio=message.audio.file_id,
                caption=(
                    f"🎵 <b>Admindan yangi audio:</b>\n"
                    f"💬 <i>{message.caption or 'Audio'}</i>\n\n"
                    f"📌 <b>Holat:</b> {user.status.value}"
                ),
                parse_mode="HTML"
            )

        # 🔴 Noma’lum xabar turi
        else:
            await message.answer("❌ Yuborish uchun mos xabar turi topilmadi.")
            await state.clear()
            return

        # ✅ Adminni ogohlantirish
        await message.answer("✅ Xabar foydalanuvchiga muvaffaqiyatli yuborildi!")

        # 🔹 Qolgan adminlarga kim xabar yuborganini bildirish (ixtiyoriy)
        for admin_id in ADMIN_IDS:
            if admin_id != message.from_user.id:
                try:
                    await bot.send_message(
                        admin_id,
                        f"✉️ <b>{message.from_user.full_name}</b> "
                        f"<code>{target_user_id}</code> foydalanuvchiga xabar yubordi.",
                        parse_mode="HTML"
                    )
                except Exception as e:
                    print(f"⚠️ Admin {admin_id} ga bildirish yuborilmadi: {e}")

    except Exception as e:
        await message.answer(f"❌ Xabar yuborishda xato: {e}")

    await state.clear()


# ==== 2. BIR FOYDALANUVCHIGA XABAR YUBORISH ====
@dp.message(Command("send_to_user"))
async def send_to_user_handler(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Sizda bu amalni bajarish huquqi yo‘q!")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("⚠️ Iltimos, foydalanuvchi Telegram ID sini kiriting. Masalan: /send_to_user 123456789")
        return

    try:
        target_user_id = int(args[1])
        user = get_user_by_telegram_id(target_user_id)
        if not user:
            await message.answer("❌ Bunday Telegram ID bilan foydalanuvchi topilmadi.")
            return
    except ValueError:
        await message.answer("❌ Telegram ID raqam bo‘lishi kerak!")
        return

    await state.set_state(AdminMessageState.waiting_for_single_message)
    await state.update_data(target_user_id=target_user_id)
    await message.answer(f"✉️ Foydalanuvchiga ({target_user_id}) yuboriladigan xabarni yozing:")


@dp.message(AdminMessageState.waiting_for_single_message)
async def single_message_handler(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return

    data = await state.get_data()
    target_user_id = data.get("target_user_id")

    if not target_user_id:
        await message.answer("❌ Xato: Foydalanuvchi topilmadi.")
        await state.clear()
        return

    user = get_user_by_telegram_id(target_user_id)
    try:
        if message.text:
            await bot.send_message(
                chat_id=target_user_id,
                text=f"📬 Admindan xabar:\n\n{message.text}\n\nStatus: {user.status.value}"
            )
        elif message.photo:
            await bot.send_photo(
                chat_id=target_user_id,
                photo=message.photo[-1].file_id,
                caption=f"📬 Admindan xabar:\n\n{message.caption or 'Rasm'}\n\nStatus: {user.status.value}"
            )
        elif message.document:
            await bot.send_document(
                chat_id=target_user_id,
                document=message.document.file_id,
                caption=f"📬 Admindan xabar:\n\n{message.caption or 'Hujjat'}\n\nStatus: {user.status.value}"
            )
        elif message.video:
            await bot.send_video(
                chat_id=target_user_id,
                video=message.video.file_id,
                caption=f"📬 Admindan xabar:\n\n{message.caption or 'Video'}\n\nStatus: {user.status.value}"
            )
        elif message.audio:
            await bot.send_audio(
                chat_id=target_user_id,
                audio=message.audio.file_id,
                caption=f"📬 Admindan xabar:\n\n{message.caption or 'Audio'}\n\nStatus: {user.status.value}"
            )
        else:
            await message.answer("❌ Yuborish uchun mos xabar turi topilmadi.")
            await state.clear()
            return

        await message.answer(f"✅ Xabar foydalanuvchiga ({target_user_id}) yuborildi!")
    except Exception as e:
        await message.answer(f"❌ Xabar yuborishda xato: {e}")

    await state.clear()

@dp.message(Command("statistika"))
async def statistika_handler(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Sizda bu amalni bajarish huquqi yo‘q!")
        return

    users = get_all_users()
    total_users = len(users)
    accepted_users = [user for user in users if user.status.value == "accept"]
    accepted_count = len(accepted_users)

    stats_message = (
        f"📊 <b>Bot Statistikasi:</b>\n"
        f"👥 <b>Jami foydalanuvchilar:</b> {total_users} ta\n"
        f"✅ <b>Qabul qilingan foydalanuvchilar:</b> {accepted_count} ta\n\n"
        f"📋 <b>Qabul qilingan foydalanuvchilar ro‘yxati:</b>\n"
    )

    if not accepted_users:
        stats_message += "ℹ️ Hozircha qabul qilingan foydalanuvchilar yo‘q."
    else:
        for i, user in enumerate(accepted_users, 1):
            referrals_count = get_referred_count(user.telegram_id)
            dbbet_line = (
                f"   🆔 <b>DBBET ID:</b> <code>{user.dbbet_id}</code>\n"
                if user.dbbet_id else
                "   🆔 <b>DBBET ID:</b> ID yuborilmagan\n"
            )

            stats_message += (
                f"{i}. 👤 <b>Ism:</b> {user.fullname or 'Yo‘q'}\n"
                f"   💬 <b>Username:</b> @{user.username or 'Yo‘q'}\n"
                f"   🆔 <b>Telegram ID:</b> {user.telegram_id}\n"
                f"{dbbet_line}"
                f"   📱 <b>Telefon:</b> {user.phone_number or 'Yo‘q'}\n"
                f"   📊 <b>Status:</b> {user.status.value}\n\n"
            )

    await message.answer(stats_message, parse_mode="HTML")



@dp.message(Command("user_info"))
async def user_info_handler(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Sizda bu amalni bajarish huquqi yo‘q!")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("⚠️ Foydalanuvchi DBBET ID sini kiriting.\nMisol: /user_info 123456")
        return

    try:
        target_dbb_id = int(args[1])
    except ValueError:
        await message.answer("❌ DBBET ID faqat raqam bo‘lishi kerak!")
        return

    # ✅ DBBET ID orqali foydalanuvchini olish
    user = get_user_by_dbb_id(target_dbb_id)
    if not user:
        await message.answer("❌ Bunday foydalanuvchi bazada topilmadi.")
        return

    referred_count = get_referred_count(user.telegram_id)

    text = (
        f"👤 <b>Foydalanuvchi ma’lumotlari:</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🆔 <b>Telegram ID:</b> <code>{user.telegram_id}</code>\n"
        f"👨‍💼 <b>Ism:</b> {user.fullname or 'Yo‘q'}\n"
        f"💬 <b>Username:</b> @{user.username or 'Yo‘q'}\n"
        f"📱 <b>Telefon:</b> {user.phone_number or 'Yo‘q'}\n"
        f"📊 <b>Status:</b> {user.status.value}\n"
        f"🔢 <b>DBBET ID:</b> <code>{user.dbbet_id or 'Yo‘q'}</code>\n"
        f"🤝 <b>Taklif qilgan do‘stlar soni:</b> {referred_count}\n"
    )

    await message.answer(text, parse_mode="HTML")



@dp.message(SendMessageState.waiting_for_photos, F.text == "❌ Bekor qilish")
async def cancel_send(message: Message, state: FSMContext):
    if not await check_user_requirements(message):
        await state.clear()
        return

    await message.answer("❌ Xabar yuborish bekor qilindi.", reply_markup=ReplyKeyboardRemove())
    await send_main_menu(message.chat.id)
    await state.clear()




@dp.message()
async def all_message_handler(message: Message):
    await check_user_requirements(message)

# ==========================================================
# 🔹 Webhook server setup
# ==========================================================
async def handle_webhook(request):
    update = await request.json()
    await dp.feed_raw_update(bot=bot, update=update)
    return web.Response()

async def on_startup(app):  # Added app parameter
    print("🤖 Bot ishga tushdi...")
    await bot.delete_webhook()
    await bot.set_webhook(url=WEBHOOK_URL)
    print(f"✅ Webhook set to {WEBHOOK_URL}")

async def on_shutdown(app):  # Added app parameter
    print("🤖 Bot to‘xtatilmoqda...")
    await bot.delete_webhook()
    await bot.session.close()

# ==========================================================
# 🔹 Main function for webhook
# ==========================================================
async def main():
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, handle_webhook)
    app.on_startup.append(on_startup)  # No parentheses, just the function reference
    app.on_shutdown.append(on_shutdown)  # No parentheses, just the function reference

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, WEBAPP_HOST, WEBAPP_PORT)
    await site.start()
    print(f"🚀 Webhook server running at {WEBAPP_HOST}:{WEBAPP_PORT}")

    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())