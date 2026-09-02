# نامزدهای اتصال Field به Property کسب‌وکار

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS برای Co-occurrence استاتیک؛ Runtime binding صفر**

برای هر ۸۱۳ Field، Propertyهای `get_/set_` لایه Entity/EntityHelper/DataLayer/
Business که در همان Method دیده شدند بررسی شدند:

- ۷۸ Field دارای Match نامی قوی + هم‌وقوعی Method؛
- ۳۱ Field دارای الگوی تک‌Field/تک‌Property در Method؛
- ۱۷۳ Field فقط هم‌وقوعی مبهم و ۵۳۱ Field بدون Property candidate؛
- ۱۰۰ Property call یکتای Match نامی قوی؛
- Runtime binding و Source column/query parameter اثبات‌شده هر دو صفر.

نمونه‌های قوی‌تر شامل مبلغ/توضیح وجه نقد، مبلغ/تاریخ/شماره چک، شماره صیاد،
مشخصات حواله بانکی، ShowInBuy/ShowInSale کالا و بعضی گزینه‌های CPrice هستند.
بااین‌حال حتی Match نامی می‌تواند Branch یا Record دیگری باشد؛ Fieldهایی مانند
DataTable/Grid نیز احتمال False positive را نشان می‌دهند.

برای قرارداد نهایی مقصد، Match باید با CLR type، Command/Query contract، Metadata
ستون و UAT مالک کسب‌وکار تأیید شود.

Artifact: `artifacts/varanegar_analysis/ui/varanegar_data_entry_field_binding_candidates_20260827.json`

Builder: `scripts/windows/build_varanegar_data_entry_field_binding_candidates.py`
