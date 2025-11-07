import telebot
from telebot import types
import time
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

# Bot sozlamalari
TOKEN = "7209776053:AAEP3H3By5RyIK4yArNBAOeTOfypMy2_-uI"
bot = telebot.TeleBot(TOKEN)

ADMIN_IDS = [8091009811]

CHANNELS = ["@Vertual_Bola"]
CHANNEL_POSTS = {"@lalalallalar": [12]}

# FSM o'rniga holat saqlash
user_states = {}
user_data = {}


# ==========================================================
# Obuna tekshirish
# ==========================================================
def is_subscribed(user_id):
    for ch in CHANNELS:
        try:
            member = bot.get_chat_member(ch, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except Exception as e:
            print(f"Obuna tekshirishda xato ({ch}): {e}")
            return False
    return True


def send_all_channel_posts(chat_id):
    try:
        for channel, post_ids in CHANNEL_POSTS.items():
            for post_id in post_ids:
                bot.forward_message(chat_id, channel, post_id)
                time.sleep(0.3)
        send_main_menu(chat_id)
    except Exception as e:
        print(f"send_all_channel_posts xatosi: {e}")


# ==========================================================
# Asosiy menyu
# ==========================================================
def send_main_menu(chat_id):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Baraban", "DBBET ID yuborish")
    bot.send_message(chat_id, "Asosiy menyu:", reply_markup=keyboard)


# ==========================================================
# Foydalanuvchi talablarini tekshirish
# ==========================================================
def check_user_requirements(message):
    user_id = message.from_user.id
    user = get_user_by_telegram_id(user_id)

    if not user:
        add_user(
            telegram_id=user_id,
            fullname=message.from_user.full_name,
            username=message.from_user.username
        )
        user = get_user_by_telegram_id(user_id)

    # Telegram kanallari
    not_subscribed = []
    for ch in CHANNELS:
        try:
            member = bot.get_chat_member(ch, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                not_subscribed.append(ch)
        except:
            not_subscribed.append(ch)

    if not_subscribed:
        markup = types.InlineKeyboardMarkup()
        for ch in CHANNELS:
            markup.add(types.InlineKeyboardButton("Obuna bo‘lish", url=f"https://t.me/{ch[1:]}"))
        markup.add(types.InlineKeyboardButton("Tekshirish", callback_data="check_sub"))
        bot.send_message(message.chat.id, "Iltimos, quyidagi Telegram kanallariga obuna bo‘ling:", reply_markup=markup)
        return False

    # Telefon raqami
    if not user.phone_number:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(types.KeyboardButton("Telefon raqamni yuborish", request_contact=True))
        bot.send_message(message.chat.id, "Iltimos, telefon raqamingizni yuboring:", reply_markup=markup)
        return False

    update_referral_subscribed(telegram_id=user_id, status=True)
    return True


# ==========================================================
# /start
# ==========================================================
@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.from_user.id
    args = message.text.split()
    referred_by_id = None

    user = get_user_by_telegram_id(user_id)
    if not user:
        if len(args) > 1:
            try:
                referrer = get_user_by_telegram_id(int(args[1]))
                if referrer:
                    referred_by_id = referrer.telegram_id
            except:
                pass

        add_user(
            telegram_id=user_id,
            fullname=message.from_user.full_name,
            username=message.from_user.username
        )
        if referred_by_id:
            add_referral(telegram_id=user_id, referred_by_id=referred_by_id)

    if check_user_requirements(message):
        send_all_channel_posts(message.chat.id)


@bot.message_handler(commands=['shartlar'])
def shartlar_handler(message):
    if check_user_requirements(message):
        send_all_channel_posts(message.chat.id)


# ==========================================================
# Kontakt (telefon)
# ==========================================================
@bot.message_handler(content_types=['contact'])
def contact_handler(message):
    phone = message.contact.phone_number
    user_id = message.from_user.id
    update_user_phone(user_id, phone)

    if is_subscribed(user_id):
        update_referral_subscribed(telegram_id=user_id, status=True)
        bot.send_message(message.chat.id, "Telefon raqamingiz saqlandi!", reply_markup=types.ReplyKeyboardRemove())

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Kickga obuna bo‘lish", url="https://kick.com/vertual-bola"))
        markup.add(types.InlineKeyboardButton("Qo'llanma", url="https://t.me/lalalallalar/14"))
        markup.add(types.InlineKeyboardButton("Keyingisi", callback_data="continue_after_kick"))

        bot.send_message(
            message.chat.id,
            "<b>Endi Kick platformamizga obuna bo‘ling</b>\n\n"
            "<b>Diqqat!</b> Agar siz Kick kanaliga obuna bo‘lmasangiz, <u>konkurslarda ishtirok eta olmaysiz</u> va "
            "yangi imkoniyatlardan bebahra qolasiz.\n\n"
            "<b>Obuna bo‘ling va pastdagi tugma orqali tasdiqlang!</b>",
            reply_markup=markup,
            parse_mode="HTML"
        )
    else:
        check_user_requirements(message)


# ==========================================================
# Callback: Keyingisi
# ==========================================================
@bot.callback_query_handler(func=lambda call: call.data == "continue_after_kick")
def after_kick(call):
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "Rahmat! Endi keyingi shartimiz quydagicha!")
    send_all_channel_posts(call.message.chat.id)


# ==========================================================
# Obuna tekshirish tugmasi
# ==========================================================
@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_subscription(call):
    user_id = call.from_user.id
    not_subscribed = [ch for ch in CHANNELS if
                      bot.get_chat_member(ch, user_id).status not in ["member", "administrator", "creator"]]

    if not_subscribed:
        markup = types.InlineKeyboardMarkup()
        for ch in CHANNELS:
            markup.add(types.InlineKeyboardButton("Obuna bo‘lish", url=f"https://t.me/{ch[1:]}"))
        markup.add(types.InlineKeyboardButton("Tekshirish", callback_data="check_sub"))
        bot.send_message(call.message.chat.id, "Hali quyidagi Telegram kanallarga obuna bo‘lmagansiz!",
                         reply_markup=markup)
        return

    user = get_user_by_telegram_id(user_id)
    if not user.phone_number:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(types.KeyboardButton("Telefon raqamni yuborish", request_contact=True))
        bot.send_message(call.message.chat.id, "Telefon raqamingizni yuboring:", reply_markup=markup)
        return

    update_referral_subscribed(telegram_id=user_id, status=True)
    send_all_channel_posts(call.message.chat.id)


# ==========================================================
# Baraban
# ==========================================================
@bot.message_handler(func=lambda m: m.text == "Baraban")
def baraban_handler(message):
    if not check_user_requirements(message):
        return

    user = get_user_by_telegram_id(message.from_user.id)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(
        "BARABANNI OCHISH",
        web_app=types.WebAppInfo(url="https://vertualbolabetkonkurs.winproline.ru/dbbet")
    ))

    dbbet_line = f"DBBET ID: <code>{user.dbbet_id}</code>\n" if user.dbbet_id else "DBBET ID: ID yuborilmagan\n"
    status = {"new": "Yangi foydalanuvchi", "accept": "O‘yinda ishtirokchisiz"}.get(user.status.value,
                                                                                                      "Rad etilgan")

    text = (
        f"<b>Sizga omad!</b>\n\n"
        f"Ism: {user.fullname}\n"
        f"{dbbet_line}"
        f"Telefon: {user.phone_number}\n"
        f"Status: {status}\n\n"
        f"Pastdagi tugmani bosing → baraban <u>Telegram ichida</u> ochiladi!"
    )
    bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=markup)


# ==========================================================
# DBBET ID yuborish
# ==========================================================
@bot.message_handler(func=lambda m: m.text == "DBBET ID yuborish")
def start_dbb_id(message):
    if not check_user_requirements(message):
        return
    user = get_user_by_telegram_id(message.from_user.id)
    if user.status.value == "accept":
        bot.send_message(message.chat.id, "Siz allaqachon yuborgansiz!")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Bekor qilish")
    bot.send_message(message.chat.id, "DBBET ID yuboring:", reply_markup=markup)
    user_states[message.from_user.id] = "waiting_dbb_id"


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "waiting_dbb_id")
def receive_dbb_id(message):
    user_id = message.from_user.id
    if message.text == "Bekor qilish":
        send_main_menu(message.chat.id)
        user_states.pop(user_id, None)
        return

    txt = message.text.strip()
    if not (txt.isdigit() and 1 <= len(txt) <= 14):
        bot.send_message(message.chat.id, "Xato! Faqat DBBET ID raqam yuboring.")
        return

    user = get_user_by_telegram_id(user_id)
    ref_cnt = get_referred_count(user_id)
    status_map = {"new": "Yangi foydalanuvchi", "accept": "Qabul qilingan", "rejected": "Rad etilgan"}
    user_status = status_map.get(user.status.value, "Noma’lum")

    caption = (
        f"<b>Yangi DBBET ID</b>\n\n"
        f"Ism: {message.from_user.full_name}\n"
        f"Telefon: {user.phone_number}\n"
        f"TG ID: <code>{user_id}</code>\n"
        f"Status: {user_status}\n"
        f"DBBET ID: <code>{txt}</code>"
    )

    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("Qabul qilish", callback_data=f"acc_{user_id}_{txt}"),
        types.InlineKeyboardButton("Rad etish", callback_data=f"rej_{user_id}_0")
    )
    kb.add(types.InlineKeyboardButton("Xabar yuborish", callback_data=f"msg_{user_id}_0"))

    for adm in ADMIN_IDS:
        try:
            bot.send_message(adm, caption, parse_mode="HTML", reply_markup=kb)
        except Exception as e:
            print(f"Admin {adm} ga yuborishda xato: {e}")

    bot.send_message(message.chat.id, "ID muvaffaqiyatli adminlarga yuborildi!\nJavob kelguncha kutib turing...",
                     reply_markup=types.ReplyKeyboardRemove())
    send_main_menu(message.chat.id)
    user_states.pop(user_id, None)


# ==========================================================
# Admin: Qabul / Rad etish
# ==========================================================
@bot.callback_query_handler(func=lambda call: call.data.startswith("acc_"))
def accept(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "Ruxsat yo‘q!", show_alert=True)
        return

    parts = call.data.split("_")
    user_id = int(parts[1])
    dbb_id = parts[2]

    update_user_status(user_id, "accept")
    update_user_dbb_id(user_id, int(dbb_id))

    bot.answer_callback_query(call.id, "Qabul qilindi")
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    bot.send_message(user_id, "So‘rovingiz qabul qilindi!\nSiz endi o‘yinda ishtirok etasiz!")
    notify_other_admins(call, user_id, "qabul qildi")


@bot.callback_query_handler(func=lambda call: call.data.startswith("rej_"))
def reject(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "Ruxsat yo‘q!", show_alert=True)
        return

    user_id = int(call.data.split("_")[1])
    update_user_status(user_id, "rejected")

    bot.answer_callback_query(call.id, "Rad etildi")
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    bot.send_message(user_id, "So‘rovingiz rad etildi.\nSabab: Noto‘g‘ri yoki takroriy ID.")
    notify_other_admins(call, user_id, "rad etdi")


def notify_other_admins(call, user_id, action):
    for admin_id in ADMIN_IDS:
        if admin_id != call.from_user.id:
            try:
                bot.send_message(
                    admin_id,
                    f"<b>{call.from_user.full_name}</b> {action}\n"
                    f"Foydalanuvchi: <code>{user_id}</code>",
                    parse_mode="HTML"
                )
            except:
                pass


# ==========================================================
# Admin: Xabar yuborish (tugma bosilganda)
# ==========================================================
@bot.callback_query_handler(func=lambda call: call.data.startswith("msg_"))
def send_message_mode(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "Ruxsat yo‘q!", show_alert=True)
        return

    parts = call.data.split("_")
    if len(parts) < 2:
        return
    target_user_id = int(parts[1])

    # Saqlash: admin_id → "admin_msg_{target_id}"
    user_states[call.from_user.id] = f"admin_msg_{target_user_id}"

    bot.send_message(
        call.message.chat.id,
        f"Xabar yuborish rejimi yoqildi\n\n"
        f"Foydalanuvchi ID: <code>{target_user_id}</code>\n\n"
        f"Xabarni yozing:",
        parse_mode="HTML"
    )
    bot.answer_callback_query(call.id)


# ==========================================================
# Admin: Xabar yuborish (handler)
# ==========================================================
@bot.message_handler(func=lambda m: any(v.startswith(f"admin_msg_{m.from_user.id}") for v in user_states.values()))
def admin_send_message_handler(message):
    if message.from_user.id not in ADMIN_IDS:
        return

    # Qaysi target uchun ekanligini topish
    target_user_id = None
    for admin_id, state in user_states.items():
        if state == f"admin_msg_{message.from_user.id}":
            target_user_id = int(admin_id)
            break

    if not target_user_id:
        return

    user = get_user_by_telegram_id(target_user_id)
    try:
        status_text = {"new": "Yangi", "accept": "Qabul qilingan", "rejected": "Rad etilgan"}.get(
            user.status.value, user.status.value
        )

        if message.text:
            bot.send_message(
                target_user_id,
                f"Admindan xabar:\n\n{message.text}\n\nHolat: {status_text}"
            )
        elif message.photo:
            bot.send_photo(
                target_user_id, message.photo[-1].file_id,
                caption=f"Admindan rasm:\n\n{message.caption or ''}\n\nHolat: {status_text}"
            )
        elif message.document:
            bot.send_document(
                target_user_id, message.document.file_id,
                caption=f"Admindan hujjat:\n\n{message.caption or ''}\n\nHolat: {status_text}"
            )
        elif message.video:
            bot.send_video(
                target_user_id, message.video.file_id,
                caption=f"Admindan video:\n\n{message.caption or ''}\n\nHolat: {status_text}"
            )
        elif message.audio:
            bot.send_audio(
                target_user_id, message.audio.file_id,
                caption=f"Admindan audio:\n\n{message.caption or ''}\n\nHolat: {status_text}"
            )
        else:
            bot.send_message(message.chat.id, "Xabar turi qo‘llab-quvvatlanmaydi.")
            return

        bot.send_message(message.chat.id, f"Xabar muvaffaqiyatli yuborildi! (ID: {target_user_id})")
    except Exception as e:
        bot.send_message(message.chat.id, f"Xato: {e}")
    finally:
        user_states.pop(message.from_user.id, None)


# ==========================================================
# Admin: /send_to_user
# ==========================================================
@bot.message_handler(commands=['send_to_user'])
def send_to_user_handler(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "Sizda bu amalni bajarish huquqi yo‘q!")
        return

    args = message.text.split()
    if len(args) < 2:
        bot.send_message(message.chat.id,
                         "Iltimos, foydalanuvchi Telegram ID sini kiriting. Masalan: /send_to_user 123456789")
        return

    try:
        target_user_id = int(args[1])
        user = get_user_by_telegram_id(target_user_id)
        if not user:
            bot.send_message(message.chat.id, "Bunday Telegram ID bilan foydalanuvchi topilmadi.")
            return
    except:
        bot.send_message(message.chat.id, "Telegram ID raqam bo‘lishi kerak!")
        return

    user_states[message.from_user.id] = f"single_msg_{target_user_id}"
    bot.send_message(message.chat.id, f"Foydalanuvchiga ({target_user_id}) yuboriladigan xabarni yozing:")


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, "").startswith("single_msg_"))
def single_message_handler(message):
    if message.from_user.id not in ADMIN_IDS:
        return

    target_user_id = int(user_states[message.from_user.id].split("_")[2])
    user = get_user_by_telegram_id(target_user_id)

    try:
        if message.text:
            bot.send_message(target_user_id, f"Admindan xabar:\n\n{message.text}\n\nStatus: {user.status.value}")
        elif message.photo:
            bot.send_photo(target_user_id, message.photo[-1].file_id,
                           caption=f"Admindan xabar:\n\n{message.caption or 'Rasm'}\n\nStatus: {user.status.value}")
        elif message.document:
            bot.send_document(target_user_id, message.document.file_id,
                              caption=f"Admindan xabar:\n\n{message.caption or 'Hujjat'}\n\nStatus: {user.status.value}")
        elif message.video:
            bot.send_video(target_user_id, message.video.file_id,
                           caption=f"Admindan xabar:\n\n{message.caption or 'Video'}\n\nStatus: {user.status.value}")
        elif message.audio:
            bot.send_audio(target_user_id, message.audio.file_id,
                           caption=f"Admindan xabar:\n\n{message.caption or 'Audio'}\n\nStatus: {user.status.value}")
        else:
            bot.send_message(message.chat.id, "Yuborish uchun mos xabar turi topilmadi.")
            return

        bot.send_message(message.chat.id, f"Xabar foydalanuvchiga ({target_user_id}) yuborildi!")
    except Exception as e:
        bot.send_message(message.chat.id, f"Xabar yuborishda xato: {e}")

    user_states.pop(message.from_user.id, None)


# ==========================================================
# Admin: /statistika
# ==========================================================
@bot.message_handler(commands=['statistika'])
def statistika_handler(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "Sizda bu amalni bajarish huquqi yo‘q!")
        return

    users = get_all_users()
    total_users = len(users)
    accepted_users = [u for u in users if u.status.value == "accept"]

    stats_message = (
        f"<b>Bot Statistikasi:</b>\n"
        f"<b>Jami foydalanuvchilar:</b> {total_users} ta\n"
        f"<b>Qabul qilingan foydalanuvchilar:</b> {len(accepted_users)} ta\n\n"
        f"<b>Qabul qilingan foydalanuvchilar ro‘yxati:</b>\n"
    )

    if not accepted_users:
        stats_message += "Hozircha qabul qilingan foydalanuvchilar yo‘q."
    else:
        for i, user in enumerate(accepted_users, 1):
            dbbet_line = f"   DBBET ID: <code>{user.dbbet_id}</code>\n" if user.dbbet_id else "   DBBET ID: ID yuborilmagan\n"
            stats_message += (
                f"{i}. Ism: {user.fullname or 'Yo‘q'}\n"
                f"   Username: @{user.username or 'Yo‘q'}\n"
                f"   Telegram ID: {user.telegram_id}\n"
                f"{dbbet_line}"
                f"   Telefon: {user.phone_number or 'Yo‘q'}\n"
                f"   Status: {user.status.value}\n\n"
            )

    bot.send_message(message.chat.id, stats_message, parse_mode="HTML")


# ==========================================================
# Admin: /user_info
# ==========================================================
@bot.message_handler(commands=['user_info'])
def user_info_handler(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "Sizda bu amalni bajarish huquqi yo‘q!")
        return

    args = message.text.split()
    if len(args) < 2:
        bot.send_message(message.chat.id, "Foydalanuvchi DBBET ID sini kiriting.\nMisol: /user_info 123456")
        return

    try:
        target_dbb_id = int(args[1])
    except:
        bot.send_message(message.chat.id, "DBBET ID faqat raqam bo‘lishi kerak!")
        return

    user = get_user_by_dbb_id(target_dbb_id)
    if not user:
        bot.send_message(message.chat.id, "Bunday foydalanuvchi bazada topilmadi.")
        return

    referred_count = get_referred_count(user.telegram_id)
    text = (
        f"<b>Foydalanuvchi ma’lumotlari:</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Telegram ID: <code>{user.telegram_id}</code>\n"
        f"Ism: {user.fullname or 'Yo‘q'}\n"
        f"Username: @{user.username or 'Yo‘q'}\n"
        f"Telefon: {user.phone_number or 'Yo‘q'}\n"
        f"Status: {user.status.value}\n"
        f"DBBET ID: <code>{user.dbbet_id or 'Yo‘q'}</code>\n"
        f"Taklif qilgan do‘stlar soni: {referred_count}\n"
    )
    bot.send_message(message.chat.id, text, parse_mode="HTML")


# ==========================================================
# Barcha xabarlar
# ==========================================================
@bot.message_handler(func=lambda m: True)
def all_message_handler(message):
    check_user_requirements(message)


# ==========================================================
# Botni ishga tushirish
# ==========================================================
if __name__ == "__main__":
    print("Bot ishga tushdi...")
    bot.infinity_polling()