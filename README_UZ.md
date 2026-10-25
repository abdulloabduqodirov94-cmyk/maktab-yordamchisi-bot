# Maktab Yordamchisi — Telegram bot (boshlang‘ich versiya)

## Nimalar ishlaydi?
- /start va /apply orqali ariza topshirish
- Ism-familiya, maktab va fanlarni yig‘ish
- Administratorga tasdiqlash/rad etish tugmalari bilan xabar yuborish
- Faqat administrator tasdiqlagan a’zolarga asosiy menyuni ochish
- Ko‘pi bilan 10 ta faol a’zo
- /pending — kutayotgan arizalar
- /members — a’zolar ro‘yxati
- /block TELEGRAM_ID — a’zoni bloklash
- SQLite ma’lumotlar bazasi

Ta’lim AI, eMaktab statistikasi integratsiyasi, hisobotlar va jurnalga yozish funksiyalari hali ulanmagan. Ular keyingi bosqichlarda alohida ishlab chiqiladi.

## 1. BotFather orqali bot yaratish
Telegramda @BotFather ni oching va `/newbot` buyrug‘i bilan yangi bot yarating. Tokenni maxfiy saqlang.

## 2. Administrator Telegram ID sini oling
Botni ishga tushirishdan oldin o‘z raqamli Telegram ID ingizni aniqlang. Uni ishonchli ID ko‘rsatuvchi bot yoki o‘zingiz boshqaradigan Telegram vositasi orqali tekshiring. Bot username emas, raqamli ID kerak.

## 3. Python o‘rnating
Python 3.11 yoki yangiroq versiya tavsiya etiladi.

## 4. O‘rnatish
Terminalda loyiha papkasiga kiring:

```bash
python -m venv .venv
```

Windows:
```bash
.venv\Scripts\activate
```

Linux/macOS:
```bash
source .venv/bin/activate
```

So‘ng:
```bash
pip install -r requirements.txt
```

`.env.example` faylidan nusxa olib `.env` deb nomlang va ichiga BOT_TOKEN hamda ADMIN_TELEGRAM_ID ni kiriting.

Windows PowerShell:
```powershell
Copy-Item .env.example .env
```

Linux/macOS:
```bash
cp .env.example .env
```

## 5. Ishga tushirish
```bash
python bot.py
```

Terminal ochiq va jarayon ishlayotgan paytda bot javob beradi. 24/7 ishlashi uchun keyinchalik VPS/hostingga joylashtirish kerak.

## Administrator buyruqlari
- `/pending` — kutayotgan arizalar
- `/members` — a’zolar va statuslari
- `/block 123456789` — foydalanuvchini bloklash

## Muhim xavfsizlik eslatmalari
- `.env` faylini hech kimga yubormang va GitHub kabi ochiq joyga yuklamang.
- Bot tokeni oshkor bo‘lsa, BotFather orqali yangilang.
- eMaktab login/parollarini ushbu botning hozirgi versiyasiga kiritmang. Hozircha eMaktab bilan ulanish mavjud emas.
- SQLite bazasining zaxira nusxasini xavfsiz joyda saqlang.
- Internetga chiqarishdan oldin serverda fayl ruxsatlari, yangilanishlar, zaxira nusxa va monitoringni sozlang.
