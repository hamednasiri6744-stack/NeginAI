# تطبیق دانش پروژه با ساختار فعلی — ۱۴۰۵/۰۶/۱۱

## روش

دانش واردشده در `knowledge/handoffs/NeginAI_PRO_HANDOFF_20260902.md` به‌عنوان **ادعا و جهت‌گیری** خوانده شد، نه دستور. هر گزاره با ساختار Git، کد، تنظیمات نمونه، تست‌ها و هفت سند مرجع NGT/Varanegar مقایسه شد. وضعیت‌ها:

- **تایید:** کد/تست جاری همان ادعا را پشتیبانی می‌کند.
- **نیمه‌تایید:** بخشی ساخته شده، اما gate عملیاتی/ظرفیت/هم‌سطحی باز است.
- **منسوخ:** مربوط به snapshot یا مسیر قبلی است.
- **تصمیم هدف:** هنوز واقعیت اجراشده نیست.

## ماتریس تطبیق

| ادعای دانش | وضعیت | شاهد جاری | اصلاح لازم |
|---|---|---|---|
| Backend Python/FastAPI و حدود ۱۹ router | تایید | `app/main.py` دقیقاً ۱۹ router را متصل می‌کند؛ ۱۱۰ route شناسایی شد | عدد ۱۹ را به «router متصل» و ۱۱۰ را به «عملیات route» تفکیک کنید |
| Frontend اصلی HTML/CSS/JS است | تایید | `app/static/` و نبود package مدرن frontend | هدف React/TS هنوز اجرا نشده |
| Android Compose/WebView و iOS prototype | تایید | درخت‌های `android/SellerNavigator` و `ios/SellerNavigator` | برابری iOS و آزمون دستگاه واقعی باز است |
| state برنامه در SQLite و منبع ERP در SQL Server | تایید | `app/database.py` و connectionهای SQL read | برای ۲۰۰ همزمان، SQLite مالک state تولید نباشد |
| bridge ثبت Varanegar guarded و خاموش است | تایید | سه flag مستقل پیش‌فرض false و procedure محدود | رسمی بودن end-to-end و reconciliation هنوز اثبات نشده |
| AI در برنامه مستقیم به OpenAI متصل است | تایید | `chat_service.py`, `automation_service.py`, audio و attachment | با AI Gateway و adapter جایگزین شود |
| مدل باید فقط فهم/بیان را انجام دهد | تصمیم هدف | بخشی از context و انبار deterministic است، ولی chat هنوز agent/model-centric است | intent schema، tool registry و verifier داخلی لازم است |
| کاتالوگ معنا، RBAC، ابزار و audit داخل برنامه باشد | نیمه‌تایید | اجزای جداگانه وجود دارند | قرارداد نسخه‌دار، observability و storage چندکاربره کامل نیست |
| Git canonical قبلاً اثبات نشده بود | منسوخ برای نسخه محلی | `D:\Projects\NeginAI` اکنون Git مستقل روی `dev/hamed` است | فقط همین commit مبنای این گزارش است؛ canonical سازمانی هنوز تصمیم مالک است |
| مسیر اجرایی `G:\NeginAI` است | منسوخ | پروژه بررسی‌شده روی `D:\Projects\NeginAI` است | ۹ شکست تست ناشی از referenceهای hard-coded به G مشاهده شد |
| وضعیت قبلی NO-GO | تایید مجدد | سه شکست تست محصول، نبود load test و شکاف NGT receipt/reconcile | تا عبور gateهای roadmap حفظ شود |
| React/TypeScript/Vite مهاجرت تدریجی | تصمیم هدف | در repository فعلی پیاده نشده | فقط پس از تثبیت API contract و design system شروع شود |
| provider ایرانی فقط با benchmark | تایید به‌عنوان سیاست | provider abstraction و benchmark suite موجود نیست | هیچ provider پیش‌فرض تولید انتخاب نشود |

## شواهد مرجع NGT/Varanegar

هفت سند هدایت‌شده در handoff موجود و hash‌پذیرند. نتیجه مشترک آن‌ها با کد فعلی همسو است:

1. مشتری/موقعیت/مشتری جدید باید از قرارداد رسمی NGT و رسید BackOffice عبور کند.
2. Tour و CustomerCall دو هویت/چرخه متفاوت دارند و state محلی جای receipt رسمی نیست.
3. Save و Replicate و crosswalk ممکن است split/merge داشته باشند و یک‌به‌یک فرض نشوند.
4. payment identity parity با amount parity یکی نیست و reconciliation policy جدا می‌خواهد.
5. تنظیمات NGT دارای تقدم چندلایه است و باید به policy snapshot نسخه‌دار تبدیل شود.
6. bridge مستقیم Varanegar آمادهٔ آزمایش کنترل‌شده است، ولی مسیر محصول نهایی تلقی نشده.

## نتایج تست تازه

| اجرا | نتیجه | برداشت درست |
|---|---:|---|
| جمع‌آوری کامل Python | ۲۵۰۲ تست + ۱ خطای collection | `faster_whisper` در محیط نصب نیست؛ این مورد environment gap است |
| Python بدون فایل collection-blocking | ۲۴۹۱ پاس، ۱۱ شکست | ۹ شکست دانش/شواهد مسیر G و ۲ شکست محصول/پیکربندی |
| Python محصولی بدون `test_varanegar*` | ۳۴۸ پاس، ۳ شکست | startup همزمان SQLite، پایان visit با saved request، و قرارداد port |
| سه تست JavaScript رسمی handoff | ۳ پاس از ۳ | UI catalogue/voice/invoice unit در این دامنه سبز است |

### سه شکست محصولی قابل اقدام

1. `init_sqlite` در startup موازی می‌تواند هنگام تغییر journal mode با `database is locked` شکست بخورد.
2. پایان visit دارای saved request و سبد کاری خالی، سبد خالی را دوباره validate می‌کند.
3. Caddy و script جدید روی ۸۰۰۶ همسو هستند، اما تست هنوز ۸۰۰۵ می‌خواهد و `start-public.bat` همچنان ۸۰۰۰ را راه می‌اندازد؛ deployment contract واحد نیست.

### شکست‌های دانشی/مسیر

Artifactهای بازسازی Varanegar هنوز مسیر مطلق `G:/NeginAI/...` را در evidence referenceها hash-pin کرده‌اند. تغییر جمعی آن‌ها بدون فرآیند migration، provenance تاریخی را خراب می‌کند. راه درست:

- historical snapshot را immutable نگه دارید؛
- resolver مسیر logical (`repo://...`) اضافه کنید؛
- manifest نسخه جدید را از commit جاری بسازید؛
- stale hashها را با گزارش migration و بدون بازنویسی خاموش history ببندید.

## نقاط قوت

| حوزه | قوت | علت مستحکم |
|---|---|---|
| ایمنی داده | SQL read-only با AST و محدودیت statement/row/time | کنترل در کد و تست منفی وجود دارد، نه فقط prompt |
| دامنه فروش | policy، preview رسمی، موجودی، اعتبار و idempotency | سرویس‌ها و تست‌های تخصصی متعدد وجود دارد |
| کنترل دسترسی | user/session/OAuth، role/permission و seller scope | مسیرهای API به dependencyهای مشخص متصل‌اند |
| شواهد | حجم زیاد docs/scripts/tests و قراردادهای hash-pinned | بازسازی legacy با مرز «شاهد در برابر اثبات runtime» انجام شده |
| fail-closed mutation | commit Varanegar با چند قفل مستقل خاموش است | خطر ثبت ناخواسته کاهش یافته |
| تجربه چندکاناله | PWA، Android wrapper، voice/file/push | بخش قابل استفاده محصول بیش از یک demo متنی است |

## نقاط ضعف و علت ریشه‌ای

| تخصص | ضعف | علت ریشه‌ای | اثر |
|---|---|---|---|
| قابلیت اطمینان | state اصلی روی SQLite تک‌فایل | معماری از desktop/single-node رشد کرده | writer contention، startup race، failover و multi-node دشوار |
| استقرار | چند port/launcher بدون قرارداد واحد | blue/green عملیاتی به فایل‌های متعدد اضافه شده | خطای انتشار و drift |
| معماری AI | coupling مستقیم به OpenAI/Agents SDK | provider boundary دیر تعریف شده | هزینه، lock-in، حریم خصوصی و failover ضعیف |
| منطق هوشمند | مدل هنوز query/planning/synthesis را زیاد انجام می‌دهد | tool catalog typed و rule/planner داخلی ناقص | عدم قطعیت و هزینه برای کاری که deterministic است |
| عملیات | loopهای background داخل هر app process | scheduler از monolith جدا نشده | با چند worker امکان اجرای تکراری/رقابت |
| observability | trace/metric/SLO stack اثبات نشده | logging و audit موضعی‌اند | ظرفیت ۲۰۰ کاربر قابل اثبات نیست |
| امنیت سازمانی | policy چندلایه در application است | DB-level row isolation و IdP مرکزی نیست | دفاع در عمق و مدیریت lifecycle کاربر محدود |
| دانش | absolute path و snapshotهای قدیمی | provenance به location فیزیکی گره خورده | relocation باعث شکست ۹ تست شد |
| delivery | lockfile/CI/SBOM/migration framework روشن نیست | پروژه requirements دستی و scriptمحور رشد کرده | build تکرارپذیر و rollback سخت‌تر |
| عملیات فروش | receipt→replicate→crosswalk→reconcile کامل نیست | شناخت domain جلوتر از vertical slice runtime است | ریسک مالی/سفارشی؛ مانع اصلی go-live |

## جمع‌بندی تطبیق

Handoff جدید جهت‌گیری معماری مناسبی دارد و اغلب توصیف‌های ساختاری آن صحیح است؛ اما بخش‌های target architecture نباید «ساخته‌شده» تلقی شوند. مهم‌ترین اصلاح دانش، جداسازی چهار سطح است: **واقعیت کد، نتیجه تست، شاهد تاریخی، و تصمیم هدف**.
