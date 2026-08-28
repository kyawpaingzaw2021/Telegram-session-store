FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ဖိုင်တွဲဆောက်ပြီး Permission အပြည့်အဝ (777) ပေးလိုက်ခြင်း
RUN mkdir -p /app/data && chmod 777 /app/data

CMD ["python", "-m", "bot.main"]

