# IMEI-Check DZ — مدقق الهواتف المسروقة

منصة جزائرية للتحقق من الهواتف المسروقة والإبلاغ عنها.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Flask](https://img.shields.io/badge/Flask-3.0-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

## المميزات

- فحص IMEI / S/N مع تحقق **Luhn**
- رقم مرجعي فريد لكل بلاغ (`DZ-YYYY-XXXXXX`)
- إبلاغ عن هاتف مسروق مع رفع عدة ملفات إثبات
- متابعة حالة البلاغ بالرقم المرجعي
- طلب حذف بلاغ مع إثباتات
- لوحة إدارة: قبول / رفض / حذف منطقي / تصدير CSV
- إحصائيات ورسوم بيانية (آخر 7 أيام + الولايات)
- صلاحيات متعددة: `superadmin` / `moderator` / `viewer`
- تشفير بيانات المالك (Fernet)
- حماية CSRF + CAPTCHA حسابي + Rate Limiting
- سجل عمليات الإدارة + سجل دخول فاشل + سجل بحث
- ملفات محمية (خارج static)
- وضع ليلي / نهاري
- واجهة موبايل RTL
- API: `GET /api/check/<imei>`
- دعم **Turso** و SQLite
- إشعارات اختيارية: Email + Telegram

## التقنيات

| الطبقة | التقنية |
|--------|---------|
| Backend | Flask 3 |
| Database | Turso (libSQL) / SQLite |
| Frontend | Bootstrap 5 RTL |
| Hosting | PythonAnywhere |
| Repo | GitHub |

## التثبيت السريع

```bash
git clone https://github.com/YOUR_USERNAME/imei-check-dz.git
cd imei-check-dz
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

عدّل `.env`:

```env
FLASK_SECRET_KEY=ضع-مفتاحاً-طويلاً-عشوائياً
ADMIN_USERNAME=admin
ADMIN_PASSWORD=كلمة-مرور-قوية
# اختياري: مفتاح التشفير
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=
```

إنشاء الجداول:

```bash
export FLASK_APP=wsgi.py
python -c "from app import create_app, db; app=create_app(); app.app_context().push(); db.create_all()"
python wsgi.py
```

- الموقع: http://127.0.0.1:5000  
- الإدارة: http://127.0.0.1:5000/admin/login  

## إعداد Turso

1. أنشئ قاعدة على [turso.tech](https://turso.tech)
2. ضع في `.env`:

```env
TURSO_DATABASE_URL=libsql://xxxx.turso.io
TURSO_AUTH_TOKEN=eyJ...
```

3. أعد تشغيل التطبيق

## النشر على PythonAnywhere

1. Clone المشروع في حسابك
2. أنشئ Virtualenv وثبّت `requirements.txt`
3. في Web tab → WSGI:

```python
import sys
path = '/home/YOUR_USERNAME/imei-check-dz'
if path not in sys.path:
    sys.path.append(path)

from wsgi import app as application
```

4. أضف متغيرات البيئة أو ملف `.env`
5. Reload

## هيكل المشروع

```
imei-check-dz/
├── app/
│   ├── __init__.py       # Factory + CSRF + Limiter
│   ├── models.py         # الجداول
│   ├── routes/
│   │   ├── public.py     # فحص + إبلاغ + متابعة + API
│   │   ├── admin.py      # لوحة الإدارة
│   │   ├── contact.py    # طلب حذف
│   │   └── files.py      # تحميل محمي للملفات
│   ├── utils/
│   │   ├── imei.py       # Luhn
│   │   ├── crypto.py     # تشفير
│   │   ├── captcha.py
│   │   ├── auth.py       # أدوار المشرفين
│   │   ├── upload.py
│   │   └── notify.py     # Email + Telegram
│   ├── templates/        # واجهة RTL موبايل
│   └── static/
├── uploads/              # ملفات محمية (خارج static)
├── wsgi.py
├── requirements.txt
└── .env.example
```

## الصفحات

| المسار | الوظيفة |
|--------|---------|
| `/` | الرئيسية |
| `/check` | فحص IMEI |
| `/report` | إبلاغ عن مسروق |
| `/track` | متابعة بلاغ |
| `/contact` | طلب حذف |
| `/api/check/<imei>` | API JSON |
| `/admin` | لوحة التحكم |

## الأمان

- CSRF على كل النماذج
- CAPTCHA على الإبلاغ وطلب الحذف
- Rate limiting
- تشفير اسم ورقم المالك
- الملفات غير متاحة علنًا
- Soft delete
- سجل محاولات الدخول الفاشلة

## الرخصة

MIT — للاستخدام الحر.
