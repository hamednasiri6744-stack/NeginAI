# کاتالوگ Scope freeze برای Routeهای تطبیق‌نشده وارانگار

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **۲۳۹ Candidate؛ ۷۶ High، ۱۰۵ Medium، ۵۸ Low؛ حذف خودکار صفر**

## چرا این Gate لازم است؟

از ۳۹۹ Route دارای FormInfo/AccessNode، تعداد ۱۶۰ فرم به Runtime بستهٔ فعلی
تطبیق شد و ۲۳۹ مورد باقی ماند. این موارد را نمی‌توان یک‌جا «قابلیت مفقود» یا
«منوی مرده» دانست. کاتالوگ آن‌ها را برای تصمیم Scope مرتب می‌کند و هیچ موردی را
خودکار Retire، Retain یا Implement نمی‌کند.

## ترکیب Candidateها

- ۶۱ Navigation/selector shell؛
- ۳۴ Leaf با اشاره به Package حاضر ولی Type تطبیق‌نشده؛
- ۱۰۴ Leaf با Hint بستهٔ خارجی یا غایب؛
- ۳۷ Leaf با Target تهی/Placeholder؛
- سه Leaf با Target Redacted و نیازمند Review کنترل‌شده.

بررسی بعدی روی تمام TypeDefهای Package، ۳۳ Route از آن ۳۴ مورد را به ۳۲ Type
واقعی در POS/Tablet/Setting/Report/VNMembers Resolve کرد. این Resolution در
`EXTENDED_ROUTE_TYPE_RESOLUTION_20260827_FA.md` ثبت است؛ Route `20037` همچنان
Class/File ناسازگار دارد. Presence در Package اولویت Review را کم نمی‌کند و
Scope را قطعی نمی‌سازد.

همه ۲۳۹ مورد AccessNode دارند، اما AccessNode وجودی مجوز مؤثر کاربر نیست. ۸۵
مورد Container-visible و ۱۲۸ مورد حداقل یک Signal مادی از Visibility/Action
دارند. Confirm/Notify در این مجموعه مشاهده نشد و سه Action menu وجود دارد.

## سیاست اولویت

- **High (۷۶):** Leaf مادیِ Present-package، External/absent یا Redacted که
  حداقل یک Signal Visibility/Action دارد؛ شامل ۳۳ Present-package، ۴۰ External
  و هر سه Redacted؛
- **Medium (۱۰۵):** Leaf مادی بدون Signal یا Shell دارای Signal؛
- **Low (۵۸):** Shell بدون Signal یا Target تهی/Placeholder.

Priority فقط ترتیب Review است. Low به معنی Retire نیست و High به معنی ورود قطعی
به Scope نیست.

## شواهد بعدی بر حسب کلاس

- Present-package: تطبیق دقیق FormInfo class/file با تمام TypeDefها، Base/Event و
  مالک قابلیت؛
- External/absent: Manifest استقرار/Plugin مجاز و تعیین مالک/وضعیت Integration؛
- Shell: بررسی Child routeها و حفظ صرفاً Navigation در صورت نیاز؛
- Null/placeholder: تاریخچه پیکربندی و شاهد استفاده مالک کسب‌وکار؛
- Redacted: Review محدود Allowlist بدون ذخیره مقدار خام ناامن.

## خوشه‌های دارای بیشترین Candidate

بر اساس Hint ریشه—نه مالکیت نهایی—Sales دارای ۹۰ Assignment، Integration/Tablet/
B2B دارای ۵۴، Procurement دارای ۵۰، Receivables دارای ۴۶ و Reporting دارای ۳۷
Candidate است. Rootهای چندماژولی باعث می‌شوند مجموع Assignment از تعداد Route
بیشتر باشد.

## مرز تصمیم

Scope freeze هر قابلیت مادی به Owner، Retain/Replace/Retire rationale، شاهد
Runtime/Deployment در صورت نیاز و Acceptance test احتیاج دارد. Static visibility،
AccessNode یا نبود DLL به‌تنهایی Usage، Permission یا Retirement را ثابت نمی‌کند.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/varanegar_scope_freeze_catalog_20260827.json`
- `scripts/windows/build_varanegar_scope_freeze_catalog.py`
- `tests/test_varanegar_ui_evidence.py`

گام بعدی: Trace ۷۶ Candidate High از Present-package/External manifest و اتصال
تصمیم آن‌ها به Risk و P0/P1 scope.
