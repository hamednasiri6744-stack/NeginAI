# خط مبنای چهار‌ساعته شناخت وارانگار برای بازسازی وب

تاریخ: ۲۰۲۶-۰۸-۲۶  
منبع: `127.0.0.1 / NeginPakhsh_WebDev`  
مرز: **Clone فقط‌خواندنی؛ هیچ تغییر روی وارانگار زنده یا Clone انجام نشده است**

## نتیجه اجرایی

در این نوبت، شناخت پروژه از چند حدس و گزارش پراکنده به یک بستهٔ تکرارپذیر ۱۸
دامنه‌ای تبدیل شد:

- ۱۸ Extractor فقط‌خواندنی؛
- ۱۸ Artifact ماشین‌خوان؛
- ۱۸ سند فارسی دامنه؛
- یک دفتر کشفیات زمان‌دار؛
- یک Manifest اعتبارسنجی‌شده با Hash هر فایل.

Manifest:
`artifacts/varanegar_analysis/manifest_20260826.json`

اعتبارسنجی نهایی:

| کنترل | نتیجه |
|---|---|
| Compile همه Extractorها | PASS |
| AST scan برای نبود DML/EXEC/DDL و commit | PASS |
| Parse همه Artifactها | PASS |
| READ_ONLY در همه Artifactها | PASS |
| `can_update=0` و deny writer | PASS |
| لینک همه سندها در README | PASS |
| ثبت همه منابع در Discovery Log | PASS |
| Credential-like literal در Artifact/Doc | صفر |
| کلید داده خام حساس در دامنه‌های Config/دفترکل | صفر |
| تجمیع ۱۳ دامنه/۱۴ بلوک فعالیت سه‌ماهه | PASS |
| تست محلی Evidence/Privacy/Parity | ۶ PASS |

بستهٔ شواهد ۲۷٬۵۵۶٬۶۷۰ بایت دارد. اعداد ۲۸۸ Table slot، ۳٬۱۹۹ FK slot،
۲۳٬۷۳۹ Consumer slot، ۳٬۲۳۴ Implicit-link slot و ۱۶۳ Semantic-contract slot
در سطح دامنه ثبت شده‌اند؛ چون دامنه‌ها هم‌پوشانی دارند این‌ها تعداد موجودیت
یکتای کل دیتابیس نیستند.

## دامنه‌های شناخته‌شده

1. سازمان، DC، SaleOffice، انبار و سال مالی.
2. جغرافیا، مسیر، منطقه و Route ownership.
3. واحد، StockDC و انواع سند.
4. کاتالوگ کالا، گروه، برند، بسته‌بندی، بارکد و نمایش فروش/خرید.
5. Contact، Customer، Supplier، Personnel و نقش‌های فروش.
6. قیمت، قیمت قراردادی، تخفیف، جایزه و اولویت Rule.
7. سفارش تا Sale و Stateهای تبدیل/ابطال.
8. موجودی، رزرو، Voucher و خروج کالا.
9. توزیع، تیم ارسال، خروج و شاهد تحویل.
10. وصول، Receipt، Allocation، OpenInvoice و مانده.
11. برگشت فروش، ورود انبار و مصرف اعتبار.
12. چک دریافتی، State history و تسویه چک برگشتی.
13. خرید، رسید خرید، Toll/Cost application و مرجوعی خرید.
14. Pay، خروج وجه و چک پرداختنی.
15. قرارداد ۲۸شاخه‌ای کاردکس تأمین‌کننده.
16. مجوزهای Legacy، Data scope و RBAC مستقل NGT.
17. تنظیمات General/Server/DC/Device/App و فلگ‌های قواعد کسب‌وکار.
18. PreVoucher، External posting batch، دفترکل دوبل و تاریخچه وضعیت سند.

## مهم‌ترین قواعدی که طراحی وب باید از روز اول رعایت کند

### ۱. Header و State یک چیز نیستند

چک دریافتی و پرداختنی، Workflow رویدادمحور دارند. سفارش، فروش، Receipt،
Voucher، Return، Distribution و Purchase نیز Stateهای مستقل‌اند. یک ستون
`status` عمومی یا چند Boolean نمی‌تواند این دامنه را درست بازسازی کند.

### ۲. سند تجاری و اثر انبار/مالی جدا هستند

نمونه‌های قطعی:

- Order با Sale یکی نیست؛
- Sale با Voucher خروج و Distribution یکی نیست؛
- Return با Voucher ورود و Credit allocation یکی نیست؛
- Supplier invoice با Receipt type 20 و Cost Apply یکی نیست؛
- Supplier return با SourceInvoice اختیاری ولی Voucher type 55 اجباری است؛
- Pay با Instrument و Invoice allocation یکی نیست.

نسخه وب باید Commandهای مستقل، Transaction مرزبندی‌شده و Projectionهای قابل
بازسازی داشته باشد.

### ۳. Refهای Legacy همیشه FK واقعی نیستند

در بسیاری از مسیرها Source identity با کلید مرکب، UUID، Business key یا Rule
مصرف‌کننده پیدا می‌شود. نمونه روشن Return item است که `SaleRef` آن همه خالی است
و تطبیق رسمی از Header Sale + Goods + Prize + FreeReason ساخته می‌شود.

هر مهاجرت به `SourceCrosswalk` نیاز دارد و نباید صرفاً نام ستون‌های `...Ref`
را Foreign Key مقصد فرض کند.

### ۴. مانده‌ها Projection هستند، نه ستون حقیقت

OpenInvoice، مانده چک برگشتی، موجودی قابل فروش و Supplier balance همگی از چند
Ledger/State ساخته می‌شوند. ذخیره یک عدد و Update مستقیم آن، Reconciliation را
می‌شکند. عدد cache شده فقط با BuildRun، source version و امکان rebuild مجاز است.

### ۵. خالی بودن جدول مساوی نبود قابلیت نیست

RetOrder، POrder، PayGroup، Fund، ManualVoucher و تعدادی جدول ChangeStatus در
Snapshot خالی‌اند، اما Procedure/Workflow رسمی Capability آن‌ها را ثابت می‌کند.
قابلیت‌های بدون نمونه باید Golden Case مصنوعی و کنترل‌شده داشته باشند، نه حذف.

### ۶. فرمول ساده جایگزین قرارداد رسمی نیست

- ۳۴ Item خرید با `Qty×Price` ساده اختلاف دارند ولی فرمول رسمی همه را قبول می‌کند؛
- Toll خرید در چهار مؤلفه اثر دارد؛
- Payment چکی بسته به وضعیت جاری اثر می‌گیرد یا حذف می‌شود؛
- Supplier cardex از ۲۸ Branch و Gateهای متفاوت ساخته می‌شود.

محاسبات باید Rule version، source evidence و آزمون parity داشته باشند.

### ۷. Configuration بخشی از دادهٔ کسب‌وکار است

۵۱۱ کلید General/Server، تنظیمات DC و Device/App می‌توانند نتیجه سفارش،
موجودی، تخفیف، چک و تأیید را عوض کنند. تصمیم مقصد باید Scope و نسخه تنظیم مؤثر
را ثبت کند. Historyهای بدون تغییر مقدار نیز Audit event هستند، نه Rule version.

## بدهی‌های کیفیت داده که نباید خودکار اصلاح شوند

| مورد | تعداد/وضعیت | اقدام مقصد |
|---|---:|---|
| Return فعال با تفاوت Gross و Net ـ هشدار قبلی رد شد | ۶۹۶ | اجزای تعدیل حفظ شود؛ Residual رسمی Net در ۱۴٬۰۹۱ سند صفر است |
| RD return در انتظار Finalize | ۳۸ Header / ۶۰ Item | Work-in-progress import |
| NGT return بدون RetSale رسمی جاری | ۲ | ۱ Pending/Unattempted و ۱ Historical-result/target-missing؛ ساخت خودکار ممنوع |
| Master PayId خالی با History PayId2 تأییدشده | ۸ | خطا نیست؛ History authority حفظ شود |
| چک حقوقی با LegalType نامشخص | ۳۵ | UNKNOWN_SOURCE؛ از PersonnelId استنتاج نشود |
| تخصیص چک برگشتی با Customer متفاوت از مالک چک | ۴۹ ردیف / ۱۷ چک | Source semantics معتبر؛ تطبیق تخصیص اولیه ۴۹/۴۹، Review فقط در صورت Provenance ناقص |
| Purchase receipt-only در مقایسه per-invoice ـ هشدار رد شد | ۵ گروه در ۲ فاکتور | هر ۵ در Component N:M توضیح داده شد؛ Residual صفر |
| Supplier return با Goods غایب از `SupInvoiceRef` مستقیم | ۷ گروه در ۳ Header | هر ۷ با خروج نوع ۵۵ دقیق‌اند؛ Invoice فقط Hint اختیاری است؛ Price/Amount غیرصفر حفظ و Reprice/Reassign خودکار ممنوع |
| مرجوعی خرید سه‌ماهه در مسیر جدید | ۵۰ Header / ۳۹۳ قلم؛ ۵ Source-item-absent | هر ۵۰ `IsNew=1`؛ شکاف Validator مسیر جدید جاری است؛ TollRef قدیمی سه‌ماهه صفر |
| Explicit TollRef قدیمی | ۲۰ ردیف در یک Header Legacy | هر ۲۰ با Header+TollRef یکتا Resolve؛ Ref خام حفظ، انتساب علت تاریخی ممنوع |
| برگ دسته‌چک `SOURCE_USED_UNLINKED` | ۱۵۵ | State منبع معتبر؛ UNKNOWN_SOURCE و Review پیش از reuse |
| ManualVoucher debit/credit هر دو Bed | بدون نمونه فعلی | Accountant golden case |
| `DRAFT_EMPTY_NUMBERED_SHELL` | ۱ | اثر Ledger صفر؛ حفظ شماره منبع و Accounting review |
| `CURRENT_POINTER_HISTORY_FORK` | ۱٬۰۹۴ سند / ۱۴٬۹۴۶ رخداد بعدی | Pointer و branch هر دو حفظ؛ Accountant disposition |
| ExternalVoucherHeader.VoucherId گمراه‌کننده | ۱۹۲٬۳۸۱ مقدار، صفر تطابق canonical | فقط reverse link رسمی |

هیچ‌یک مجوز Update، حذف، ساخت Ref یا تعویض Customer حدسی نیست.

## معماری پیشنهادی بازسازی

```text
Web/PWA
  │
  ├─ Query API  ───────────────> projections/read models
  │
  └─ Command API
       ├─ authorization + business policy
       ├─ idempotency + optimistic concurrency
       ├─ human approval for sensitive operations
       ├─ domain transaction
       └─ append-only audit/outbox
                 │
                 ├─ state event / ledger entry
                 ├─ source crosswalk
                 └─ projection rebuild

Migration/Reconciliation service
  ├─ read-only Varanegar extractor
  ├─ staged normalized import
  ├─ quarantine/review queue
  └─ parity report by domain and source branch
```

در فاز بازسازی، هیچ Write مستقیم عملیاتی به وارانگار مجاز نیست. مسیر رسمی فعلی
NeginAI نیز برای عملیات فروش باید از Backend و API رسمی NGT/وارانگار عبور کند؛
این بستهٔ تحلیل برای شناخت و ساخت دیتابیس/وب جدید است، نه میان‌بُر نوشتن در ERP.

## ترتیب ساخت پیشنهادی

### Slice A — Foundation و هویت

- Organization/DC/SaleOffice/StockDC/AccYear؛
- Geography/Route؛
- Unit/Document type؛
- Product catalog؛
- Contact/Customer/Supplier/Personnel؛
- Authorization principal/role/data scope و Configuration resolver؛
- SourceCrosswalk و Audit پایه.

تعریف Done: Import تکرارپذیر، شمارش و کلیدها دقیق، هیچ Duplicate، RBAC خواندن،
Reconciliation report و صفحه Read-only برای بازبینی.

### Slice B — Pricing و Order-to-Sale

- Rule engine قیمت/تخفیف/جایزه؛
- Order command/state؛
- Sale conversion و cancellation؛
- Golden cases برای rule priority و retry.

### Slice C — Inventory و Distribution

- Voucher ledger، stock projection، reservation؛
- خروج، تیم توزیع، proof of delivery؛
- جلوگیری از oversell و دوباره‌خروج.

### Slice D — Receivables و Return

- Receipt و instrument؛
- allocation و OpenInvoice projection؛
- Sales return، stock entry و credit consumption؛
- received-cheque workflow و returned-cheque settlement.

### Slice E — Procurement و Payables

- purchase receipt relation؛
- supplier invoice toll/cost apply؛
- supplier return؛
- Pay و instruments؛
- payable-cheque workflow؛
- supplier ledger ۲۸شاخه‌ای و parity.

### Slice F — Pilot و Cutover

- snapshot + incremental delta؛
- dual-read/reconciliation، نه dual-write بی‌قاعده؛
- role-based UAT؛
- failure recovery و rollback؛
- cutover فقط پس از parity و sign-off دامنه‌ها.

## برآورد زمان واقع‌بینانه

با یک تیم کوچک و استفاده مستمر از AI، به شرط دسترسی پایدار به کارشناسان کسب‌وکار:

| خروجی | زمان تقریبی |
|---|---|
| اولین Slice وب Read-only اطلاعات پایه | ۳ تا ۵ هفته |
| Foundation + کاتالوگ + طرف‌حساب قابل استفاده | ۵ تا ۸ هفته |
| فروش/انبار/توزیع عملیاتی کنترل‌شده | ۶ تا ۹ هفته بعدی |
| وصول/برگشت/خرید/خزانه و کاردکس | ۶ تا ۱۰ هفته بعدی |
| Pilot، Parity، UAT و Cutover | ۴ تا ۶ هفته |

کل نسخه Production-grade در این Scope حدود **۲۱ تا ۳۳ هفته** است. این برآورد
برای بازسازی امن و قابل حسابرسی است؛ ظاهر اولیه سریع‌تر ساخته می‌شود، اما ظاهر
بدون Workflow، parity و migration proof محصول آماده نیست.

## دسترسی‌ها و ابزارهای باقی‌مانده

برای ادامه تحلیل، دسترسی فعلی Clone و View Definition کافی است. برای رسیدن به
Parity و ساخت محصول، موارد زیر لازم می‌شود:

1. خروجی کنترل‌شده Procedureهای رسمی که حساب read-only حق EXEC آن‌ها را ندارد،
   یا اجازه EXEC فقط روی Procedureهای گزارش‌خوان مشخص؛
2. یک کاربر آزمایشی برای هر Role واقعی وارانگار؛
3. دسترسی Read-only به UI رسمی برای ثبت Golden workflow؛
4. تصمیم حسابداری درباره ManualVoucher/TitleId=26 و Certified cheque؛
5. نمونه‌های کنترل‌شده برای Capabilityهای بدون داده؛
6. دیتابیس مقصد جدا، Migration staging و محیط تست؛
7. تست‌دیتای ماسک‌شده و مجوز نمایش محدود PII؛
8. Definition of Done و مالک کسب‌وکار هر دامنه.

هیچ ابزار شخص ثالث یا Plugin جدید برای ادامهٔ تحلیل فعلی ضروری تشخیص داده نشد.

## کار بعدی دقیق

1. Crosswalk هر ۱۱ VoucherCreator به Commandهای دامنه و Rule version؛
2. ساخت Crosswalk کنترل‌شده AccessNode به NGT Permission/API route؛
3. اثبات تقدم General/Server/DC/Device/App از کد Client و Golden workflow؛
4. ساخت Golden Dataset بدون PII برای ۱۸ دامنه؛
5. شروع Slice A روی دیتابیس مقصد، نه روی وارانگار.

تا قبل از سه مورد اول، طراحی ظاهری Frontend می‌تواند Wireframe باشد ولی Contract
نهایی API نباید تثبیت شود.
