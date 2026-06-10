# 🏋️ GymManager — Fitnes klubni boshqarish tizimi

Fitnes klub / sport zalni to'liq boshqarish uchun veb-ilova. Flask + SQLite asosida
yozilgan, o'rnatish oson, interfeys to'liq **o'zbek tilida**.

## ✨ Imkoniyatlari

| Bo'lim | Tavsif |
|--------|--------|
| 📊 **Bosh sahifa** | Jami/faol/tugayotgan a'zolar, bugungi tashriflar, oylik va umumiy tushum statistikasi |
| 👥 **A'zolar** | Qo'shish, tahrirlash, o'chirish, qidirish, holat bo'yicha filtrlash (faol/tugayotgan/tugagan) |
| 🎟️ **Tariflar** | Abonement rejalari (1 oylik, 3 oylik, yillik, kunlik). Narx va muddatni boshqarish |
| 💳 **To'lovlar** | Abonement to'lovlari va qo'shimcha to'lovlar (naqd/karta/o'tkazma). Tushum hisoboti |
| ✅ **Davomat** | Bir tugma bilan kirishni belgilash (check-in), kun bo'yicha davomat |
| 🧑‍🏫 **Murabbiylar** | Murabbiylarni qo'shish va a'zolarga biriktirish |

A'zo holati avtomatik hisoblanadi:
- 🟢 **Faol** — abonement amal qiladi
- 🟠 **Tugayapti** — 3 kun yoki kamroq qoldi
- 🔴 **Tugagan** — abonement muddati o'tgan / yo'q

## 🚀 Ishga tushirish

```bash
cd fitness_club

# 1. Virtual muhit (ixtiyoriy, tavsiya etiladi)
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Kutubxonalarni o'rnatish
pip install -r requirements.txt

# 3. (Ixtiyoriy) Namuna ma'lumotlarni qo'shish
python seed_demo.py

# 4. Dasturni ishga tushirish
python app.py
```

So'ng brauzerda oching: **http://localhost:5000**

> Birinchi ishga tushirishda `fitness.db` bazasi va standart tariflar avtomatik yaratiladi.

## 🗂️ Loyiha tuzilishi

```
fitness_club/
├── app.py             # Flask ilovasi va barcha sahifalar (route)
├── models.py          # Ma'lumotlar bazasi modellari (a'zo, tarif, to'lov, davomat...)
├── seed_demo.py       # Namuna ma'lumotlar generatori
├── requirements.txt
├── templates/         # HTML sahifalar
└── static/style.css   # Dizayn
```

## 🛠️ Texnologiyalar
- **Python 3.11+**
- **Flask** — veb-freymvork
- **Flask-SQLAlchemy** — ma'lumotlar bazasi (SQLite)

## 📌 Eslatma
Ilova lokal foydalanish uchun mo'ljallangan (ofis/qabulxona kompyuteri). Internetga
ochiq joylashtirilganda autentifikatsiya (login/parol) va HTTPS qo'shish tavsiya etiladi.
