# Python bazaviy image
FROM python:3.11-slim

# Ishchi papka
WORKDIR /var/www/html/bot

# Fayllarni konteynerga nusxalash
COPY . .
# Copy web/database.py and database.db
COPY web/database.py ../web/database.py
COPY web/database.db ../web/database.db

# Kerakli kutubxonalarni o‘rnatish
RUN pip install --no-cache-dir -r requirements.txt

# Expose webhook port
EXPOSE 8443

# Botni ishga tushirish
CMD ["python", "main.py"]