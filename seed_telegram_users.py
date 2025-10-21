from faker import Faker
from sqlalchemy.orm import Session
import random

from database import SessionLocal, TelegramUser, UserStatus

fake = Faker()

def seed_telegram_users(count=100):
    db: Session = SessionLocal()
    users = []

    for _ in range(count):
        user = TelegramUser(
            telegram_id=random.randint(1000000, 9999999),
            phone_number=fake.phone_number(),
            username=fake.user_name(),
            fullname=fake.name(),
            status=random.choice(list(UserStatus))  # Enum'dan random tanlanadi
        )
        users.append(user)

    db.add_all(users)
    db.commit()
    db.close()

    print(f"{count} ta soxta foydalanuvchi muvaffaqiyatli qo'shildi ✅")

if __name__ == "__main__":
    seed_telegram_users()
