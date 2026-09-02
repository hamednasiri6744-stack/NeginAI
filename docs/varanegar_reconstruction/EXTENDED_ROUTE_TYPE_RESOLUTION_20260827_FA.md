# حل Typeهای Route خارج از کاتالوگ Core وارانگار

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **۳۳ از ۳۴ Route به TypeDef واقعی Resolve شد؛ یک Route ناسازگار باقی ماند**

## علت شکاف قبلی

کاتالوگ ۴۴۵ فرم اولیه روی خانواده‌های Core متمرکز بود. ۳۴ Route در Scope-freeze
به Package حاضر اشاره می‌کردند، اما Type آن‌ها در آن کاتالوگ نبود. اسکن تمام ۶۲
فایل و ۷٬۶۵۰ TypeDef نشان داد این شکاف عمدتاً فرم‌های Setting، POS، Tablet،
Report Interface و VNMembers است، نه DLL گم‌شده.

## نتیجهٔ Resolution

- ۱۳ Route به Typeهای `VN.SDS.POSSystem.UI.dll`؛
- ۹ Route به Typeهای `VN.SDS.Tablet.UI.dll`؛
- ۸ Route به Typeهای `VN.SDS.Setting.UI.dll`؛
- دو Route به یک Type مشترک
  `VN.SDS.Report.InterFace.Forms.FrmReportSelectingMenu`؛
- یک Route به `VNMembers.Forms.frmContactList`؛
- یک Route حل‌نشده: Menu `20037` با Class
  `FrmReportSelectingMenu1` و File hint
  `VN.SDS.Report.InterFace.Forms.FrmAddNewReport` که هیچ‌کدام TypeDef متناظر در
  Package فعلی ندارند.

در مجموع ۳۲ Type متمایز در پنج Assembly و ۶۰۷ Method body بدون خطا/Hash mismatch
تحلیل شد. ۲۶ Type Method نام‌Write-like و ۱۳ Type Method نام‌Permission-like
دارند؛ این‌ها Heuristic هستند، نه شاهد اجرای Command یا Permission مؤثر.

## قابلیت‌های اضافه‌شده به شناخت

POS فقط یک صفحه فروش نیست و فرم‌های Subscriber، Safe، LinearDiscount، Session،
Setting، Scale، SubscriberGroup، OldPrice، BarcodePrint، ChangePanel، Charge
Device، Instalment Method و Instalment Receipt دارد.

Tablet نیز Product group، Catalog، Calendar template، Visit template، Visit
plan، Dealer-day path، Dealer، Product و Customer را به‌عنوان Console مدیریتی
دارد. این‌ها نشان می‌دهند Integration/Tablet باید Master projection و برنامه
ویزیت را پوشش دهد، نه اینکه صرفاً Sync endpoint تلقی شود.

Setting شامل GeneralConfig، Stock accounting access، User setting design، سه
Final-date management، WebServiceConfig و ArticleTemplate است. بنابراین
Configuration، Authorization و Fiscal/close boundaries در UI قدیمی به‌هم
Couple شده‌اند و در مقصد باید مالکیت جدا داشته باشند.

## Route حل‌نشدهٔ 20037

ناسازگاری Class/File می‌تواند Stale config، Plugin/version دیگر، Dynamic loader
یا دادهٔ اشتباه باشد. این Route خودکار Retire نمی‌شود و برای Scope freeze به
Deployment history یا شاهد مالک کسب‌وکار نیاز دارد.

## مرز اطمینان

TypeDef موجود فقط Presence در Package را ثابت می‌کند؛ Usage، Visibility مؤثر،
مجوز، صحت رفتار و ورود قطعی به Scope مقصد را ثابت نمی‌کند. فرم‌های جدید به ۴۴۵
Candidate Core اضافه نشده‌اند؛ به‌صورت Extension route-backed جدا نگه داشته
شده‌اند تا شمارش‌ها گمراه‌کننده نشود.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/varanegar_present_package_route_types_20260827.json`
- `scripts/windows/extract_varanegar_present_package_route_types.py`
- `tests/test_varanegar_ui_evidence.py`

گام بعدی: استخراج قرارداد Compact همین ۳۲ Type به نقشهٔ قابلیت POS/Tablet/
Setting و تصمیم Scope برای Route `20037`.
