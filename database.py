from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Enum, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import enum

DATABASE_URL = "sqlite:///database.db"
Base = declarative_base()

# 🔹 User status
class UserStatus(enum.Enum):
    new = "new"
    accept = "accept"
    rejected = "rejected"

# 🔹 Telegram foydalanuvchilari
class TelegramUser(Base):
    __tablename__ = "telegram_users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    phone_number = Column(String, nullable=True)
    username = Column(String, nullable=True)
    fullname = Column(String, nullable=True)
    status = Column(Enum(UserStatus), default=UserStatus.new, nullable=False)
    sms = Column(Boolean, default=False, nullable=False)

    dbbet_id = Column(Integer, nullable=True)


    # 🔹 User tomonidan qilingan referrals
    referrals = relationship(
        "Referral",
        back_populates="referrer",
        foreign_keys="Referral.referred_by_id"
    )

# 🔹 Referral jadvali
class Referral(Base):
    __tablename__ = "referrals"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, ForeignKey("telegram_users.telegram_id"), nullable=False)
    referred_by_id = Column(Integer, ForeignKey("telegram_users.telegram_id"), nullable=False)
    subscribed = Column(Boolean, default=False)  # ✅ Obuna bo‘lgan yoki yo‘qligini bildiradi

    # 🔹 Referral qilgan user
    referrer = relationship(
        "TelegramUser",
        back_populates="referrals",
        foreign_keys=[referred_by_id]
    )

# 🔹 Database engine va session
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


# 🔹 Foydalanuvchining DBBET ID sini yangilash
def update_user_dbb_id(tid, dbb_id):
    s = SessionLocal()
    u = s.query(TelegramUser).filter_by(telegram_id=tid).first()
    if u:
        u.dbbet_id = dbb_id
        s.commit()
    s.close()



# 🔹 DB init
def init_db():
    Base.metadata.create_all(bind=engine)
    print("✅ Database va jadval yaratildi!")

# 🔹 Foydalanuvchi statusini yangilash
def update_user_status(telegram_id, status):
    session = SessionLocal()
    user = session.query(TelegramUser).filter(TelegramUser.telegram_id == telegram_id).first()
    if user:
        user.status = UserStatus(status)
        session.commit()
    session.close()

# 🔹 Yangi foydalanuvchi qo‘shish
def add_user(telegram_id, fullname, username, phone_number=None):
    session = SessionLocal()
    existing_user = session.query(TelegramUser).filter_by(telegram_id=telegram_id).first()

    if not existing_user:
        user = TelegramUser(
            telegram_id=telegram_id,
            fullname=fullname,
            username=username,
            phone_number=phone_number
        )
        session.add(user)
        session.commit()
    else:
        # Agar foydalanuvchi telefon yuborsa — yangilaymiz
        if phone_number and not existing_user.phone_number:
            existing_user.phone_number = phone_number
            session.commit()

    session.close()

def get_users_for_broadcast():
    session = SessionLocal()
    users = session.query(TelegramUser).filter(TelegramUser.sms == False).all()
    session.close()
    return users


# 🔹 Foydalanuvchining sms statusini yangilash (True yoki False)
def set_user_sms_status(telegram_id: int, value: bool = True):
    session = SessionLocal()
    user = session.query(TelegramUser).filter(TelegramUser.telegram_id == telegram_id).first()
    if user:
        user.sms = value
        session.commit()
    session.close()


def reset_all_sms():
    session = SessionLocal()
    session.query(TelegramUser).update({TelegramUser.sms: False})
    session.commit()
    session.close()
# 🔹 Referral qo‘shish
def add_referral(telegram_id, referred_by_id):
    session = SessionLocal()
    existing = session.query(Referral).filter_by(telegram_id=telegram_id, referred_by_id=referred_by_id).first()
    if not existing:
        referral = Referral(telegram_id=telegram_id, referred_by_id=referred_by_id)
        session.add(referral)
        session.commit()
    session.close()

# 🔹 Foydalanuvchi obuna bo‘lganda `subscribed=True` qilamiz
def update_referral_subscribed(telegram_id, status=True):
    session = SessionLocal()
    referral = session.query(Referral).filter_by(telegram_id=telegram_id).first()
    if referral:
        referral.subscribed = status
        session.commit()
    session.close()

# 🔹 Foydalanuvchi telefon raqam yuborganda — subscribedni ham tekshiramiz
def update_user_phone(telegram_id, phone_number):
    session = SessionLocal()
    user = session.query(TelegramUser).filter(TelegramUser.telegram_id == telegram_id).first()
    referral = session.query(Referral).filter(Referral.telegram_id == telegram_id).first()

    if user:
        user.phone_number = phone_number

        # 🔹 Agar referral mavjud bo‘lsa — obuna bo‘lgan deb belgilaymiz
        if referral:
            referral.subscribed = True

        session.commit()

    session.close()

# 🔹 Referrallar soni (faqat subscribed=True bo‘lsa)
def get_referred_count(user_id):
    session = SessionLocal()
    count = session.query(Referral).filter(
        Referral.referred_by_id == user_id,
        Referral.subscribed == True
    ).count()
    session.close()
    return count

# 🔹 Telegram ID bo‘yicha user olish
def get_user_by_telegram_id(telegram_id):
    session = SessionLocal()
    user = session.query(TelegramUser).filter(TelegramUser.telegram_id == telegram_id).first()
    session.close()
    return user


def get_user_by_dbb_id(dbb_id: int):
    session = SessionLocal()
    user = session.query(TelegramUser).filter(TelegramUser.dbbet_id == dbb_id).first()
    session.close()
    return user

# 🔹 Foydalanuvchining barcha referral’larini olish (faqat obuna bo‘lganlar)
def get_all_referred_users(user_id):
    session = SessionLocal()
    referrals = (
        session.query(Referral)
        .filter(Referral.referred_by_id == user_id, Referral.subscribed == True)
        .all()
    )
    session.close()
    return referrals

# 🔹 Barcha foydalanuvchilarni olish
def get_all_users():
    session = SessionLocal()
    users = session.query(TelegramUser).all()
    session.close()
    return users

# 🔹 Script sifatida ishga tushsa DB yaratish
if __name__ == "__main__":
    init_db()
