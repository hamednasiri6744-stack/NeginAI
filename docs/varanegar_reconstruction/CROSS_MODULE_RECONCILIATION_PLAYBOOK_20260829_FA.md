# Playbook تطبیق بین‌ماژولی و قرنطینه — ۱۴۰۵/۰۶/۰۷

هفت Playbook، مسیر بررسی اختلاف‌های Command Receipt، فروش/منبع حسابداری، منبع/Batch/Journal، توزیع/فروش، توزیع/خروج، خروج/سند نوع ۶۰ و پرداخت NGT/رسید BackOffice را پوشش می‌دهند.

ترتیب مشترک Evidence-first است: تثبیت هویت و Scope، کنترل Hash، خواندن فقط‌خواندنی مبدأ/مقصد/Crosswalk/History/Audit/Outbox، مقایسهٔ مستقل پنج محور، طبقه‌بندی چهارگانه و سپس قرنطینه. نتیجه فقط یکی از `NATURAL_BEHAVIOR`، `DATA_DEBT`، `BUG` یا `UNPROVEN` است.

Playbook مجوز اصلاح یا Retry نیست. در History fork از `MAX(id)`، در Empty Shell از ساخت Line، در خروج مفقود از فرض ابطال و در اختلاف مبلغ پرداخت/رسید از فرض خطای هویتی استفاده نمی‌شود. هر Repair یا Retry کار جداگانه و نیازمند اختیار صریح است.
