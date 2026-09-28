# 🛋 RAYYON Mebel — Bot + Mini App (1-bosqich: poydevor)

Bu bosqichda quyidagilar tayyor:
- Telegram bot: `/start` bosilganda Mini App ochiladigan tugma chiqadi
- Mini App: zamonaviy qorong'i+oltin dizaynda, "Bizning ishlarimiz" (portfolio) bo'limi ishlaydi
- Admin (bot orqali, `/admin`): portfolio va material narxlarini qo'shish/o'chirish
- Baza: users, admins, portfolio, material narxlari, orders va payments jadvallari tayyor (keyingi bosqichlarda to'liq ishlatiladi)

## Keyingi bosqichlar (hali qo'shilmagan)
- Mini App ichida to'liq buyurtma formasi (o'lcham, rang, material, zapchast tanlash)
- AI narx hisoblash
- Buyurtma holati kuzatuvi va to'lov/qarzdorlik ko'rsatkichi
- To'liq admin Mini App paneli

## O'rnatish

```bash
pip install -r requirements.txt
cp .env.example .env
# .env to'ldiring: BOT_TOKEN, SUPER_ADMIN_ID, DATABASE_URL, WEBAPP_URL
python main.py
```

`WEBAPP_URL` — bu loyihaning o'zi joylashgan ochiq (https) manzil. Railway'da
domen generatsiya qilingach, o'sha manzilni shu yerga yozasiz.

## Muhim: Mini App uchun talablar
- Manzil albatta **https** bo'lishi kerak (Telegram talabi)
- BotFather'da botga Menu Button yoki inline tugma orqali shu manzil ulanadi
  (bu kodda inline tugma orqali avtomatik ishlaydi, qo'shimcha BotFather sozlash shart emas)
