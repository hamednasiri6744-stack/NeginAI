# گراف گذرای SQL برای Replication رسید POS

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS برای استخراج امن؛ گراف در سقف ایمنی بریده شده و کامل نیست**

این بررسی از ریشه‌ی اثبات‌شده‌ی `dbo.usp_ReplicateSalesReceipt` شروع شد و فقط
کاتالوگ و Definitionهای Clone فقط‌خواندنی `NeginPakhsh_WebDev` را در حافظه
تحلیل کرد. هیچ Procedure، Trigger، Function، View یا فرمان برنامه اجرا نشد و
Definition، Literal و مقدار کسب‌وکاری در Artifact ذخیره نشده است.

## نتیجه‌ی کمی

- عمق حداکثر: ۳؛
- سقف ایمنی: ۵۰۰ Node؛ گراف به سقف رسید و ۱۶۰ Module در Frontier بازنشده ماند؛
- ۱٬۰۳۹ Edge؛
- ۸۲ Table، ۲۸ Stored Procedure، ۳۶۲ Trigger، ۱۶ View، ۹ Function و ۳ Sequence؛
- ۴۰۰ Mutation token: ۱۲۲ `INSERT`، ۲۷۰ `UPDATE` و ۸ `DELETE`؛
- ۴۸ Write target حل‌شده؛
- ۱۴۰ Module دارای نشانه‌ی Transaction، ۲۱ Module دارای `TRY/CATCH` و ۱۰ Module
  دارای نشانه‌ی Dynamic SQL؛
- ۱۷۹ Dependency حل‌نشده که Alias، pseudo-tableهای `inserted/deleted` یا Name
  بدون Schema هم در آن‌ها وجود دارد.

## معنای معماری

Replication رسید POS یک «Save ساده» نیست. حتی گراف محدود سه‌لایه به صدها
Trigger و ده‌ها مقصد نوشتن می‌رسد. بنابراین Procedure Legacy نباید در ERP مقصد
کپی یا مستقیماً صدا زده شود. قرارداد مقصد باید همان طراحی Batch/Receipt،
Idempotency، Outbox/Inbox، Quarantine و Reconciliation را نگه دارد و اثرهای Sale،
Return، Payment، Inventory، Credit و Session را در مرزهای مالکیت مستقل اعمال کند.

رسیدن به سقف ایمنی خودش شاهد ریسک است، نه شاهد کامل‌بودن دامنه. عددهای این سند
حداقل مشاهده‌شده‌اند و نباید به‌عنوان کل اثرهای Runtime یا تایید آمادگی Production
تفسیر شوند.

## Artifact و Extractor

- `artifacts/varanegar_analysis/ui/varanegar_pos_replication_transitive_graph_20260827.json`
- `scripts/sql/extract_varanegar_pos_replication_transitive_graph.py`

