FROM python:3.11-slim

WORKDIR /var/www/html/bot

# Fayllarni nusxalash
COPY bot ./
COPY web ./web

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8443
CMD ["python", "main.py"]
