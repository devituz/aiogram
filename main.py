import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
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

from database import (
    add_user,
    get_user_by_telegram_id,
    update_user_phone,
    add_referral,
    update_referral_subscribed,
    get_referred_count,
    update_user_status
)

# 🔹 Bot sozlamalari
TOKEN = "7548864714:AAFZklf5PYSSGV_qWula7-SnebSxgeBrDTA"
ADMIN_ID = 7321341340  # Admin Telegram ID
CHANNELS = ["@shohbozbekuz"]
CHANNEL_POSTS = {"@shohbozbekuz": [3320]}

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())  # FSM storage


# ==========================================================
# 🔹 FSM holatlari
# ==========================================================
class SendMessageState(StatesGroup):
    waiting_for_photos = State()


class AdminMessageState(StatesGroup):
    waiting_for_message = State()  # Admin xabar yuborish uchun holat


# ==========================================================
# 🔹 Obuna tekshirish
# ==========================================================
async def is_subscribed(user_id):
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except Exception as e:
            print(f"❌ Obuna tekshirishda xato: {e}")
            return False
    return True


# ==========================================================
# 🔹 Kanal postlarini yuborish
# ==========================================================
async def send_all_channel_posts(chat_id: int):
    try:
        for channel, post_ids in CHANNEL_POSTS.items():
            for post_id in post_ids:
                await bot.forward_message(chat_id=chat_id, from_chat_id=channel, message_id=post_id)
                await asyncio.sleep(0.3)

        await bot.send_message(
            chat_id=chat_id,
            text="📦 *Go Tashkent* ilovasi haqida ma’lumot!\n\n👇 Quyidagini sinab ko‘ring:",
            parse_mode="Markdown"
        )
        await send_main_menu(chat_id)
    except Exception as e:
        print(f"❌ send_all_channel_posts xatosi: {e}")


# ==========================================================
# 🔹 Asosiy menyu
# ==========================================================
async def send_main_menu(chat_id: int):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎁 Referal"), KeyboardButton(text="✉️ Xabar yuborish")]
        ],
        resize_keyboard=True
    )
    await bot.send_message(chat_id, "📋 Asosiy menyu:", reply_markup=keyboard)


# ==========================================================
# 🔹 Foydalanuvchi talablarini tekshirish
# ==========================================================
async def check_user_requirements(message: Message):
    user_id = message.from_user.id
    user = get_user_by_telegram_id(user_id)

    if not user:
        add_user(
            telegram_id=user_id,
            fullname=message.from_user.full_name,
            username=message.from_user.username
        )
        user = get_user_by_telegram_id(user_id)

    # Obuna tekshirish
    if not await is_subscribed(user_id):
        buttons = [[InlineKeyboardButton(text=f"🔗 {ch}", url=f"https://t.me/{ch.strip('@')}")] for ch in CHANNELS]
        buttons.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer("⚠️ Quyidagi kanallarga obuna bo‘ling:", reply_markup=keyboard)
        return False

    # Telefon raqami tekshirish
    if not user.phone_number:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📞 Telefon raqamni yuborish", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await message.answer("📱 Iltimos, telefon raqamingizni yuboring:", reply_markup=keyboard)
        return False

    update_referral_subscribed(telegram_id=user_id, status=True)
    return True


# ==========================================================
# 🔹 /start handler (referral bilan)
# ==========================================================
@dp.message(CommandStart())
async def start_handler(message: Message, command: CommandStart):
    user_id = message.from_user.id
    start_arg = command.args  # /start 12345

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

    await check_user_requirements(message)  # Har doim tekshirish


# ==========================================================
# 🔹 Telefon raqam yuborish
# ==========================================================
@dp.message(F.contact)
async def contact_handler(message: Message):
    phone = message.contact.phone_number
    user_id = message.from_user.id

    update_user_phone(user_id, phone)
    if await is_subscribed(user_id):
        update_referral_subscribed(telegram_id=user_id, status=True)
        await message.answer("✅ Telefon raqamingiz saqlandi!", reply_markup=ReplyKeyboardRemove())
        await send_all_channel_posts(message.chat.id)
    else:
        await check_user_requirements(message)  # Obuna bo‘lmagan bo‘lsa, qayta tekshirish


# ==========================================================
# 🔹 Callback — obuna tekshirish
# ==========================================================
@dp.callback_query(F.data == "check_sub")
async def check_subscription(callback: CallbackQuery):
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id

    if not await is_subscribed(user_id):
        buttons = [[InlineKeyboardButton(text=f"🔗 {ch}", url=f"https://t.me/{ch.strip('@')}")] for ch in CHANNELS]
        buttons.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.answer("⚠️ Hali obuna bo‘lmagansiz!", reply_markup=keyboard)
        return

    user = get_user_by_telegram_id(user_id)
    if not user.phone_number:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📞 Telefon raqamni yuborish", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await callback.message.answer("📱 Telefon raqamingizni yuboring:", reply_markup=keyboard)
        return

    update_referral_subscribed(telegram_id=user_id, status=True)
    await send_all_channel_posts(chat_id)


# ==========================================================
# 🔹 Referral handler
# ==========================================================
@dp.message(F.text == "🎁 Referal")
async def referral_handler(message: Message):
    if not await check_user_requirements(message):
        return  # Agar shartlar bajarilmagan bo‘lsa, hech narsa qilmaydi

    user_id = message.from_user.id
    referral_link = f"https://t.me/YOUR_BOT_USERNAME?start={user_id}"  # Bot username o'rniga haqiqiy nom qo'yilishi kerak
    referred_count = get_referred_count(user_id)

    text = (
        f"🎁 Sizning referal linkingiz:\n"
        f"<a href='{referral_link}'>{referral_link}</a>\n\n"
        f"✅ Siz {referred_count} do‘stni taklif qildingiz!"
    )
    await message.answer(text=text, parse_mode="HTML")


# ==========================================================
# 🔹 Xabar yuborish
# ==========================================================
@dp.message(F.text == "✉️ Xabar yuborish")
async def start_send_message(message: Message, state: FSMContext):
    if not await check_user_requirements(message):
        return  # Agar shartlar bajarilmagan bo‘lsa, hech narsa qilmaydi

    await message.answer(
        "📸 Iltimos, faqat rasm (screenshot) va unga izoh (caption) yuboring.\n\nTayyor bo‘lgach, '✅ Yuborish' tugmasini bosing.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="✅ Yuborish"), KeyboardButton(text="❌ Bekor qilish")]],
            resize_keyboard=True
        )
    )
    await state.set_state(SendMessageState.waiting_for_photos)
    await state.update_data(photos=[])


# ==========================================================
# 🔹 Rasm va caption qabul qilish
# ==========================================================
@dp.message(SendMessageState.waiting_for_photos, F.photo)
async def photo_handler(message: Message, state: FSMContext):
    if not await check_user_requirements(message):
        await state.clear()
        return  # Agar shartlar bajarilmagan bo‘lsa, holatni tozalaydi va qaytaradi

    data = await state.get_data()
    photos = data.get("photos", [])
    caption = message.caption or "Matn biriktirilmagan."
    photos.append({"file_id": message.photo[-1].file_id, "caption": caption})
    await state.update_data(photos=photos)
    await message.answer(f"📸 {len(photos)}-rasm qabul qilindi.")


# ==========================================================
# 🔹 Oddiy matn xabari uchun ogohlantirish
# ==========================================================
@dp.message(SendMessageState.waiting_for_photos, F.text & ~F.text.in_(["✅ Yuborish", "❌ Bekor qilish"]))
async def text_message_warning(message: Message):
    if not await check_user_requirements(message):
        return  # Agar shartlar bajarilmagan bo‘lsa, hech narsa qilmaydi

    await message.answer(
        "⚠️ Faqat rasm va unga izoh (caption) yuborishingiz mumkin! Iltimos, rasm yuboring."
    )


# ==========================================================
# 🔹 Yuborish — barcha rasm va izohlar bilan
# ==========================================================
@dp.message(SendMessageState.waiting_for_photos, F.text == "✅ Yuborish")
async def send_to_admin(message: Message, state: FSMContext):
    if not await check_user_requirements(message):
        await state.clear()
        return  # Agar shartlar bajarilmagan bo‘lsa, holatni tozalaydi va qaytaradi

    data = await state.get_data()
    photos = data.get("photos", [])
    user = get_user_by_telegram_id(message.from_user.id)
    referred_count = get_referred_count(message.from_user.id)
    user_id = message.from_user.id

    if not photos:
        await message.answer("⚠️ Hech qanday rasm yuborilmadi.")
        return

    izohlar = "\n".join([f"{i + 1}️⃣ {photo['caption']}" for i, photo in enumerate(photos)])

    caption = (
        f"📩 <b>Yangi xabar:</b>\n"
        f"👤 <b>Foydalanuvchi:</b> {message.from_user.full_name}\n"
        f"💬 <b>Username:</b> @{message.from_user.username or 'yo‘q'}\n"
        f"📱 <b>Telefon:</b> {user.phone_number or 'yo‘q'}\n"
        f"🆔 <b>ID:</b> <code>{message.from_user.id}</code>\n"
        f"🤝 <b>Taklif qilingan do‘stlar:</b> {referred_count} ta\n"
        f"🖼 <b>Rasmlar soni:</b> {len(photos)} ta\n"
        f"✏️ <b>Izohlar:</b>\n{izohlar}"
    )

    # Inline keyboard qo'shish
    inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Qabul qilish", callback_data=f"accept_user_{user_id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_user_{user_id}"),
        ],
        [InlineKeyboardButton(text="✉️ Xabar yuborish", callback_data=f"message_user_{user_id}")]
    ])

    media_group = []
    for i, photo in enumerate(photos):
        if i == 0:
            media_group.append(InputMediaPhoto(media=photo["file_id"], caption=caption, parse_mode="HTML"))
        else:
            media_group.append(InputMediaPhoto(media=photo["file_id"]))

    # Media group va inline keyboard yuborish
    await bot.send_media_group(chat_id=ADMIN_ID, media=media_group)
    await bot.send_message(chat_id=ADMIN_ID, text="Amallar:", reply_markup=inline_keyboard)

    await message.answer("✅ Xabaringiz yuborildi!", reply_markup=ReplyKeyboardRemove())
    await send_main_menu(message.chat.id)
    await state.clear()


# ==========================================================
# 🔹 Admin callback handlerlari
# ==========================================================
@dp.callback_query(F.data.startswith("accept_user_"))
async def accept_user_callback(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Sizda bu amalni bajarish huquqi yo‘q!", show_alert=True)
        return

    user_id = int(callback.data.split("_")[2])
    update_user_status(user_id, "accept")
    await callback.answer("✅ Foydalanuvchi qabul qilindi!")
    await callback.message.edit_reply_markup(reply_markup=None)  # Tugmalarni o'chirish
    # Foydalanuvchiga xabar yuborish
    await bot.send_message(chat_id=user_id, text="✅ Sizning so‘rovingiz qabul qilindi!")


@dp.callback_query(F.data.startswith("reject_user_"))
async def reject_user_callback(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Sizda bu amalni bajarish huquqi yo‘q!", show_alert=True)
        return

    user_id = int(callback.data.split("_")[2])
    update_user_status(user_id, "rejected")
    await callback.answer("❌ Foydalanuvchi rad etildi!")
    await callback.message.edit_reply_markup(reply_markup=None)  # Tugmalarni o'chirish
    # Foydalanuvchiga xabar yuborish
    await bot.send_message(chat_id=user_id, text="❌ Sizning so‘rovingiz rad etildi!")


@dp.callback_query(F.data.startswith("message_user_"))
async def message_user_callback(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Sizda bu amalni bajarish huquqi yo‘q!", show_alert=True)
        return

    user_id = int(callback.data.split("_")[2])
    await state.set_state(AdminMessageState.waiting_for_message)
    await state.update_data(target_user_id=user_id)
    await callback.message.answer("✉️ Foydalanuvchiga yuboriladigan xabarni yozing:")
    await callback.answer("Xabar yuborish rejimi yoqildi.")


# ==========================================================
# 🔹 Admin xabar yuborish
# ==========================================================
@dp.message(AdminMessageState.waiting_for_message)
async def admin_send_message_handler(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return

    data = await state.get_data()
    target_user_id = data.get("target_user_id")

    if not target_user_id:
        await message.answer("❌ Xato: Foydalanuvchi topilmadi.")
        await state.clear()
        return

    try:
        # Har qanday turdagi xabar yuborish (matn, rasm, fayl va h.k.)
        if message.text:
            await bot.send_message(chat_id=target_user_id, text=message.text)
        elif message.photo:
            await bot.send_photo(chat_id=target_user_id, photo=message.photo[-1].file_id, caption=message.caption or "")
        elif message.document:
            await bot.send_document(chat_id=target_user_id, document=message.document.file_id,
                                    caption=message.caption or "")
        elif message.video:
            await bot.send_video(chat_id=target_user_id, video=message.video.file_id, caption=message.caption or "")
        elif message.audio:
            await bot.send_audio(chat_id=target_user_id, audio=message.audio.file_id, caption=message.caption or "")
        else:
            await message.answer("❌ Yuborish uchun mos xabar turi topilmadi.")
            await state.clear()
            return

        await message.answer("✅ Xabar foydalanuvchiga yuborildi!")
    except Exception as e:
        await message.answer(f"❌ Xabar yuborishda xato: {e}")

    await state.clear()


# ==========================================================
# 🔹 Bekor qilish
# ==========================================================
@dp.message(SendMessageState.waiting_for_photos, F.text == "❌ Bekor qilish")
async def cancel_send(message: Message, state: FSMContext):
    if not await check_user_requirements(message):
        await state.clear()
        return  # Agar shartlar bajarilmagan bo‘lsa, holatni tozalaydi va qaytaradi

    await message.answer("❌ Xabar yuborish bekor qilindi.", reply_markup=ReplyKeyboardRemove())
    await send_main_menu(message.chat.id)
    await state.clear()


# ==========================================================
# 🔹 Har qanday boshqa xabar
# ==========================================================
@dp.message()
async def all_message_handler(message: Message):
    await check_user_requirements(message)  # Har bir xabar uchun tekshirish


# ==========================================================
# 🔹 Botni ishga tushirish
# ==========================================================
async def main():
    print("🤖 Bot ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
