# Python bazaviy image
FROM python:3.11-slim

# Ishchi papka
WORKDIR /var/www/html

# Bot va web papkalarini konteynerga nusxalash
COPY bot ./bot
COPY web ./web

# Kerakli kutubxonalarni o‘rnatish
RUN pip install --no-cache-dir -r bot/requirements.txt

# Expose webhook port
EXPOSE 8443

# Botni ishga tushirish
CMD ["python", "bot/main.py"]
