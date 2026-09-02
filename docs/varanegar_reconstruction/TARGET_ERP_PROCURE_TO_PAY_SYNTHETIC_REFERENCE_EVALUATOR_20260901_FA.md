# ارزیاب مرجع مصنوعی خرید تا پرداخت

این ارزیاب pure و قطعی، precedence تصمیم خرید تا پرداخت را فقط با ورودی‌های boolean و نام عملیات مصنوعی آزمایش می‌کند. هیچ داده ERP، تأمین‌کننده، سفارش، رسید، صورتحساب، پرداخت یا دفتر خوانده و هیچ عملیات عملیاتی اجرا نشده است.

ترتیب fail-closed از schema و scope آغاز می‌شود، سپس version/idempotency، unknown commit و blocking unknown را می‌بندد و بعد قواعد اختصاصی ORDER، RECEIVE، SERVICE، MATCH، RETURN، RELEASE، PAYMENT و RECONCILE را اعمال می‌کند.

هشت مسیر مثبت و ۲۳ مسیر منفی، در مجموع ۳۱ بردار، باید دقیقاً outcome مورد انتظار را تولید کنند. ارزیاب انتخاب provider یا ادعای readiness نیست؛ command-ready و pilot-ready همچنان صفر هستند.
