from flask import Flask, render_template
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Enum, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import enum


# 🔹 Database setup
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
    dbbet_id = Column(Integer, nullable=True)

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
    subscribed = Column(Boolean, default=False)

    referrer = relationship(
        "TelegramUser",
        back_populates="referrals",
        foreign_keys=[referred_by_id]
    )


# 🔹 Database engine va session
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


# 🔹 Flask app
app = Flask(__name__)


# 🔹 Referrallar soni
def get_referred_count(user_id):
    session = SessionLocal()
    count = session.query(Referral).filter(
        Referral.referred_by_id == user_id,
        Referral.subscribed == True
    ).count()
    session.close()
    return count


# 🔹 Barcha qabul qilingan foydalanuvchilarni olish
def get_accepted_users():
    session = SessionLocal()
    users = session.query(TelegramUser).filter(TelegramUser.status == UserStatus.accept).all()
    session.close()
    return users


# 🔹 Index route
@app.route('/bu-link-shunchaki-yashirin-shunga-uzun-qildim')
def index():
    accepted_users = get_accepted_users()
    users_data = []
    for user in accepted_users:
        referrals_count = get_referred_count(user.telegram_id)
        users_data.append({
            'telegram_id': user.telegram_id,
            'phone_number': user.phone_number or 'Yo‘q',
            'username': f"@{user.username}" if user.username else 'Yo‘q',
            'fullname': user.fullname or 'Yo‘q',
            'dbbet_id': user.dbbet_id or 'Yo‘q',
            'status': user.status.value,
            'referrals_count': referrals_count
        })

    return render_template('index.html', users=users_data)  # ✅ Qavs to‘g‘rilandi


# 🔹 Faqat dbbet ko‘rinishi uchun sahifa
@app.route('/dbbet')
def dbbet():
    accepted_users = get_accepted_users()
    users_data = []
    for user in accepted_users:
        referrals_count = get_referred_count(user.telegram_id)
        users_data.append({
            'telegram_id': user.telegram_id,
            'phone_number': user.phone_number or 'Yo‘q',
            'username': f"@{user.username}" if user.username else 'Yo‘q',
            'fullname': user.fullname or 'Yo‘q',
            'dbbet_id': user.dbbet_id or 'Yo‘q',
            'status': user.status.value,
            'referrals_count': referrals_count
        })

    return render_template('dbbet.html', users=users_data)


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
