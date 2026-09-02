# Checkpoint فقط‌خواندنی UI وارانگار — ساعت ۰۳:۰۰

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS؛ NO_SEMANTIC_UI_DRIFT در سطح Inventory مجاز**

از Process باز `VN.SDS.Container` روی ماشین `192.168.1.184` یک Inventory تازه
گرفته شد. Extractor هیچ Invoke، Focus، SetValue، Click، SendKeys یا Pattern
اجرایی ندارد و فقط Labelهای Allowlist‌شده یا Hash را ذخیره می‌کند.

Baseline و Checkpoint در شش بخش `source/safety/summary/windows/win32 tree/controls`
پس از حذف فقط Timestamp و Process id مقایسه شدند:

- یک پنجره‌ی Top-level در هر دو؛
- ۷۶ Control مشاهده‌شده در هر دو؛
- ۱۸ Control با Label امن در هر دو؛
- ۸۵ Child window و ۱۹ عنوان امن Win32 در هر دو؛
- صفر بخش تغییرکرده از شش بخش.

این نتیجه فقط ثبات Session/Inventory قرمزده‌شده را نشان می‌دهد؛ تمام Roleها،
فرم‌های پنهان، رفتار فرمان و Workflowهای دیگر را اثبات نمی‌کند.

Artifacts:

- `artifacts/varanegar_analysis/ui/varanegar_ui_checkpoint_20260827_0300.json`
- `artifacts/varanegar_analysis/ui/varanegar_ui_checkpoint_comparison_20260827_0300.json`

Builder:
`scripts/windows/build_varanegar_ui_checkpoint_comparison.py`

