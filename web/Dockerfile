FROM python:3.11-slim

WORKDIR /var/www/html/web

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

CMD ["python", "app.py"]
