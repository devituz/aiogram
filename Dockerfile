# Python bazaviy image
FROM python:3.11-slim

# Ishchi papka
WORKDIR /var/www/html

# Fayllarni konteynerga nusxalash
COPY . .

# Kerakli kutubxonalarni o‘rnatish
RUN pip install --no-cache-dir -r requirements.txt

# Botni ishga tushirish
CMD ["python", "main.py"]
