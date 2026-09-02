# دفتر ثبت کشفیات وارانگار

## ۲۰۲۶-۰۸-۲۷ — واگرایی داده/SQL در Alias مغایرت بانکی

- از ۱۹۲٬۱۰۶ ردیف `BankAccountCardex` در Clone فقط‌خواندنی، `RCASHDRAFT`
  ۱۴۶٬۵۷۶ بار و Literal مورد استفاده Summary یعنی `RCASHDRAF` صفر بار دیده شد.
- شش Predicate دقیق Summary در سطح کل Clone فقط ۴۵٬۴۵۴ ردیف را واجد شرط
  می‌کنند؛ ۱۴۶٬۵۷۶ ردیف canonical جایگزین و ۵۳ ردیف `RCHEQUE` خارج از Status=3 است.
- `RCASHDRAFT` در ۲۳ Object کاتالوگ SQL استفاده شده، اما `RCASHDRAF` فقط در
  `dbo.DoReconcile_GetSummary` دیده شد؛ Definition خام ذخیره نشد.
- `RBANKDRAFT` نیز در دو View مصرف شده و `RBANKDARFT` فقط در همان Summary است؛
  هر دو Alias غلط Outlier محلی یک Procedure هستند.
- هر دو املای `RBANKDARFT/RBANKDRAFT` در Clone صفرند؛ این Snapshot فراوانی
  Production یا Runtime parity را ثابت نمی‌کند.
- تصمیم `BR-DEC-001` همچنان بدون Approval و Normalize بی‌صدا ممنوع است.
- سند: `BANK_RECONCILIATION_TYPE_ALIAS_AGGREGATES_20260827_FA.md`.

## ۲۰۲۶-۰۸-۲۷ — نقشهٔ انتها‌به‌انتهای بانک

- کل جریان Account/Profile→Import→Rows→Summary→Match/Unmatch→Confirm→Cancel/Reverse
  در یک سند Legacy/Target/Gate جمع شد.
- ده Non-inference حیاتی و مرز سه Slice مجاز در برابر پنج Command مسدود ثبت شد.
- سند: `BANK_RECONCILIATION_END_TO_END_EVIDENCE_MAP_20260827_FA.md`.

## ۲۰۲۶-۰۸-۲۷ — بستهٔ نه درخواست شواهد/دسترسی بانک

- نه درخواست در سه اولویت با نه مالک، حداقل دسترسی، منع صریح و Gate قابل‌رفع
  ساخته شد؛ Production write برای هیچ درخواست لازم نیست.
- Snapshot/Profile/Summary، Owner decision/UAT و Failure/Root evidence مسیر بعدی‌اند.
- Satisfied request، Access grant و Owner approval فعلی همگی صفرند.
- سند: `BANK_RECONCILIATION_EVIDENCE_ACCESS_REQUEST_PACK_20260827_FA.md`.

## ۲۰۲۶-۰۸-۲۷ — Runbook UAT احراز‌شدهٔ بانک

- ۱۰۰ Case در پنج Wave با هفت Principal slot و پانزده Fixture slot قابل‌اجرا شد؛
  هر شش Role و Deny baseline پوشش دارد.
- Evidence امن سیزده Field و پنج کلاس ممنوع دارد؛ Identity/Credential/Business
  value فقط بیرون Artifact و در محیط مجاز نگه داشته می‌شود.
- Provisioned account، executed/pass case و Owner-approved expected result همگی صفرند.
- سند: `BANK_RECONCILIATION_AUTHENTICATED_UAT_RUNBOOK_20260827_FA.md`.

## Checkpoint نهایی ادامهٔ سه‌ساعته — ۲۰۲۶-۰۸-۲۷

- قرارداد آمادگی بانک از ۳۰ Artifact معتبر ساخته شد: سه Slice محدود Profile،
  Parser/Staging و ReadModel/Summary قرارداد مقصد دارند؛ پنج Command همچنان blocked است.
- ۱۱۶ Acceptance تفاضلی، ۱۰۰ UAT بدون هویت، هفت تصمیم مالک تأییدنشده، پنج
  Lifecycle state و Command envelope اتمیک پنج‌فرمانی ثبت شد.
- Clone جاری برای Reconcile/BankBill/Link/Profile فاقد Fixture است؛ Runtime parity،
  authenticated UAT، Owner approval، Root closure و Target execution همگی صفرند.
- Baseline همان Checkpoint روی ۱۶۷ Source نتیجهٔ `NO_SEMANTIC_DRIFT` داشت؛ Bundle شامل ۱۷۸
  Artifact، ۱۱۴ سند و ۱۴۵ Builder/Extractor با `PASS` و خطای صفر است.
- Manifest هجده دامنه `PASS` و Suite شواهد ۱۴۵/۱۴۵ Pass است. هیچ Form/Procedure/
  Operational write یا تغییر Business row/Identity انجام نشد.

## ۲۰۲۶-۰۸-۲۷ — Command envelope مقصد بانک

- پنج Command مستقل با ده Request field/Guard، نه Response field، یازده Error
  پایدار و دوازده Invariant در یک قرارداد جمع شد.
- Auth→Capability→Feature→Scope→Date→Version→Idempotency→State/Domain→Atomic
  mutation/audit/outbox ترتیب اجباری است؛ Repository commit مستقل ممنوع است.
- Command implemented/executed صفر و owner/UAT/parity Gateها بازند.
- سند: `BANK_RECONCILIATION_COMMAND_ENVELOPE_20260827_FA.md`.

## ۲۰۲۶-۰۸-۲۷ — State machine مقصد بانک

- پنج Lifecycle state از چهار Progress محاسبه‌شده جدا و هفت Transition/Capability
  مستقل برای Import/Match/Unmatch/Confirm/Cancel/Reverse/Quarantine ثبت شد.
- Match/Unmatch State Header را تغییر نمی‌دهند؛ Cancel و Reverse مستقل و
  Quarantine برای Marker/Link/Instrument ناسازگار است.
- ۱۴ Invariant و ۱۸ Acceptance obligation ساخته شد؛ تصمیم 006/007، implementation
  و UAT واقعی همچنان صفرند.
- سند: `BANK_RECONCILIATION_TARGET_STATE_MACHINE_20260827_FA.md`.

## ۲۰۲۶-۰۸-۲۷ — قرارداد Parser/Staging ایزوله مقصد بانک

- چهار Entity/۴۰ Field، هشت State/Pipeline stage، چهارده Invariant، شش Command و
  شانزده Acceptance obligation برای Slice دوم ساخته شد.
- Header/Rows فقط پس از Parse/Preview کامل و Commit صریح در یک Transaction ایجاد
  می‌شوند؛ Parser failure و mid-commit failure هیچ Persistence جزئی ندارند.
- SQL/Provider/Office/Shell/Path اجرایی ممنوع و تصمیم‌های 002/003/004 هنوز بازند؛
  implementation و owner approval صفر است.
- سند: `BANK_STATEMENT_STAGING_TARGET_CONTRACT_20260827_FA.md`.

## ۲۰۲۶-۰۸-۲۷ — قرارداد Read Model و Summary مقصد بانک

- چهار Projection/۴۴ Field، پنج Query، یازده فرمول، شش Typed mapping و شانزده
  Acceptance obligation برای Slice فقط‌خواندنی ساخته شد.
- API مبلغ signed decimal را حفظ می‌کند، Scope/AsOfDate/Pagination پایدار دارد و
  Candidate query هیچ Side effect ندارد.
- Alias املایی تا `BR-DEC-001`، و Runtime parity تا Fixture Redacted بسته است؛
  implementation و parity-approved هر دو صفرند.
- سند: `BANK_RECONCILIATION_READ_MODEL_TARGET_CONTRACT_20260827_FA.md`.

## ۲۰۲۶-۰۸-۲۷ — قرارداد مقصد Profile نسخه‌دار بانک

- سه Entity با ۲۹ Field، دوازده Invariant، چهار Command و دوازده Acceptance
  obligation برای اولین Slice Profile catalog ساخته شد.
- Profile با Family/Version/Effective range/Approval/Hash immutable است؛ Mapping
  دقیق شش ستون Canonical و انتخاب Server-side بر اساس Bank/AccountType دارد.
- SQL/Provider/Path هیچ Field مقصدی ندارد؛ چهار Option خاموش Legacy تا تصمیم
  `BR-DEC-004` و Parser typed/tested غیرفعال می‌مانند.
- Profile واقعی، Approval و اجرای پیاده‌سازی همچنان صفر است.
- سند: `BANK_STATEMENT_PROFILE_TARGET_CONTRACT_20260827_FA.md`.

## ۲۰۲۶-۰۸-۲۷ — بستهٔ هفت تصمیم باز مالک فرایند بانک

- هر ۱۲ Acceptance case نیازمند Owner decision دقیقاً یک بار به هفت تصمیم
  Alias، مبلغ دوطرفه/صفر، Profile field، Conflict، Reversal و Cancel نگاشت شد.
- هر تصمیم گزینه، اثر، ریسک، شاهد لازم، نقش مالک و پیش‌فرض محافظه‌کارانه دارد؛
  approved همچنان صفر است و توصیه به‌عنوان Approval ثبت نمی‌شود.
- Parser/Summary/Command فقط پس از تصمیم مرتبط و شاهدش از Gate عبور می‌کنند؛
  هیچ هویت، Command، UI action یا دادهٔ عملیاتی خوانده/تغییر داده نشد.
- سند: `BANK_RECONCILIATION_OWNER_DECISION_PACK_20260827_FA.md`.

## ۲۰۲۶-۰۸-۲۷ — قرارداد یکپارچهٔ آمادگی پیاده‌سازی مغایرت بانکی

- ۲۸ Artifact معتبر به یک تصمیم اجرایی تبدیل شد: از شش برش ساخت، سه Read-side
  شامل Profile catalog، Parser/Staging و Summary candidate اجازهٔ شروع محدود دارند.
- پوشش ایستا شامل ۱۵ جدول، ۵۸ Method contract، شش نگاشت Match، ۱۴ پارامتر
  Summary، ۹۳ Golden case و ۱۰۰ UAT case بدون هویت است.
- Gateهای واقعی پنهان نشدند: Profile واقعی، authenticated UAT، owner approval،
  Root بسته‌شده و Target command execution همگی صفرند؛ Summary formula و
  Cancel/Reverse نیز بازند.
- نه بعد آمادگی، هشت Gate اجباری Pilot، ترتیب شش‌مرحله‌ای ساخت و Definition of
  Done مقصد در Artifact/Builder/Test ماندگار شد.
- سند: `BANK_RECONCILIATION_IMPLEMENTATION_READINESS_20260827_FA.md`.

## ۲۰۲۶-۰۸-۲۷ — Snapshot Aggregate Integrity بانک

- Reconcile/BankBill/ReconcileItem و چهار جدول Profile در Clone جاری همگی صفرند؛
  پس Frequency Defect، marker mismatch و Row parity قابل‌اندازه‌گیری نیست.
- Queryهای Aggregate برای marker، orphan، multi-link، typed-ref و شش Instrument
  ساخته شد؛ هیچ ID/Date/Amount/User value ذخیره نشد.
- صفر فعلی به Production تعمیم داده نمی‌شود؛ همان Extractor روی Snapshot تازهٔ
  READ_ONLY اجرا و هر anomaly غیرصفر Quarantine می‌شود.
- سند: `BANK_RECONCILIATION_INTEGRITY_AGGREGATES_20260827_FA.md`.

## ۲۰۲۶-۰۸-۲۷ — ۱۱۶ تعهد Acceptance تفاضلی بانک

- ۳۸ Case Summary، ۲۴ Parser و ۵۴ Confirm/Unmatch/Reverse/Cancel ساخته شد.
- ۴۱ Case Fixture واقعی Redacted، ۱۲ Owner decision، ۱۱ Failure injection و پنج
  UAT احراز‌شده می‌خواهند؛ executed و owner-approved هر دو صفر است.
- Defect یک‌لینکی، دو Alias املایی، Partial import، Dedup بدون Scope و Gateهای
  Auth/Date/Version اکنون Regression obligation هستند و در سند باقی نمانده‌اند.
- این ۹۴ مورد جدا از ۹۷۰ Golden mapping است و هیچ پوشش اجرایی ادعا نمی‌کند.
- سند: `BANK_RECONCILIATION_DIFFERENTIAL_ACCEPTANCE_20260827_FA.md`.

## ۲۰۲۶-۰۸-۲۷ — Discard ردیف در برابر Cancel Session

- SaveData قبل از Parser Header را Commit می‌کند؛ btnDelete فقط BankBillS را پس
  از صفر بودن Linkها Delete/Update و Header را دست‌نخورده رها می‌کند.
- Permission/Date/Confirm-state guard داخل مسیر دیده نشد؛ Parser failure یا
  Discard می‌تواند Header خالی ماندگار بگذارد.
- مقصد Discard/Cancel را جدا، Cancel را idempotent/atomic/audited و Confirmed را
  فقط Reversal می‌کند. شش Case Acceptance افزوده شد.
- سند: `BANK_RECONCILIATION_DISCARD_CANCEL_BOUNDARY_20260827_FA.md`.

## ۲۰۲۶-۰۸-۲۷ — معنای واقعی SQL Unmatch

- Procedure با BankBillId همهٔ ReconcileItemهای آن Bill را حذف می‌کند، نه یک
  LinkId مشخص؛ Scope حساب/Reconcile/State/Version و affected count ندارد.
- هیچ Instrument flag را Reset نمی‌کند؛ Unmatch پس از Confirm می‌تواند Link را
  حذف و IsReconciled را true باقی بگذارد.
- مقصد Unmatch را به unconfirmed محدود و Confirmed را فقط با Reversal اتمیک
  Owner-approved برمی‌گرداند. هشت Case جدید Acceptance افزوده شد.
- سند: `BANK_RECONCILIATION_UNMATCH_SQL_SEMANTICS_20260827_FA.md`.

## ۲۰۲۶-۰۸-۲۷ — Orchestration کامل Confirm

- DoAccept ابتدا Amount=0 و markerهای Confirm را می‌نویسد، Reconcile.Update و
  سپس Cardex procedure را در یک Physical transaction فراخوانی می‌کند.
- Cardex پس از اولین Update موفق ErrorNo=0 می‌دهد؛ Outer همان را Commit می‌کند.
  پس Session confirmed با Instrumentهای باقی‌ماندهٔ unreconciled ممکن است.
- DoAccept هیچ Permission/OperationDate call ندارد؛ مقصد همه Gateها را Server-side
  دوباره بررسی و خطا را Typed می‌کند.
- ۱۲۹ Instruction فقط ایستا تحلیل و هیچ Form/Transaction/Command اجرا نشد.
- سند: `BANK_RECONCILIATION_CONFIRM_ORCHESTRATION_20260827_FA.md`.

## ۲۰۲۶-۰۸-۲۷ — Defect Confirm/Cardex مغایرت بانکی

- Procedure شش Instrument table را از Cursor Linkهای Session Update می‌کند، اما
  در موفقیت و شکست هر Branch فوراً Return دارد؛ حداکثر Update در هر اجرا یک است.
- Cursor فاقد ORDER BY است، بنابراین در Session چندLinkی همان یک ابزار هم
  deterministic نیست. ۱۲ Return، شش Update و دو Fetch ثبت شد.
- مقصد نباید این Defect را برای Result parity کپی کند؛ همهٔ Linkها باید در یک
  Transaction همراه State/Audit/Outbox Update یا کامل Rollback شوند.
- Definition فقط Redacted در حافظه Parse شد؛ Procedure اجرا و Business row خوانده نشد.
- سند: `BANK_RECONCILIATION_CONFIRM_CARDEX_SEMANTICS_20260827_FA.md`.

## ۲۰۲۶-۰۸-۲۷ — Parser row mapping و Atomicity صورتحساب بانک

- DBF/TXT، SQLStatement خام Profile را اجرا می‌کنند؛ XLS آن را Overwrite و همیشه
  Sheet1 را می‌خواند. هیچ‌یک HDR را مصرف نمی‌کند و Getterهای StartRow/Seperator/
  IsArabic در کل Forms assembly صفر بود.
- شش ستون Canonical `No1/Date/Comment/Debit/Credit/BaLance` به BankBill نگاشت شد؛
  Debit branch بر Credit اولویت دارد و حالت هر دو غیرصفر Row guard ندارد.
- Dedup با Predicate رشته‌ای Amount+No+Date و بدون Account/Reconcile scope است؛
  پس هم Injection surface و هم false-duplicate risk دارد.
- Header قبل از Parser و هر BankBill جدا Commit می‌شوند؛ Parser/row failure می‌تواند
  Partial import بگذارد. مقصد Atomic staging/commit و idempotency کامل می‌خواهد.
- سند: `BANK_STATEMENT_PARSER_ROW_AND_ATOMICITY_20260827_FA.md`.

## ۲۰۲۶-۰۸-۲۷ — فرمول Redacted SQL برای Summary مغایرت بانکی

- Definition فقط در حافظه از Clone READ_ONLY خوانده شد؛ ۱۱ فرمول، ۱۳ Pattern،
  شش Dependency و شش Type/Status predicate با صفر Mutation keyword ثبت شد.
- ماندهٔ Bill از آخرین/اولین مبنا و گردش دوره، ماندهٔ Cardex از Credit-Debit به
  اضافه InitialBalance و Reconcile از اختلاف دو RealRemaining ساخته می‌شود.
- اختلاف مادی کشف شد: Summary دارای `RBANKDARFT/RCASHDRAF` ولی Match دارای
  `RBANKDRAFT/RCASHDRAFT` است؛ تصحیح خودکار ممنوع و Fixture parity اجباری شد.
- این کشف Slice سوم Read-side را برای Candidate باز می‌کند، نه Command/Pilot را؛
  Procedure اجرا و Business row خوانده نشد.
- سند: `BANK_RECONCILIATION_SUMMARY_SQL_SEMANTICS_20260827_FA.md`.

## ۲۰۲۶-۰۸-۲۷ — مرز Summary تا UI مغایرت بانکی

- ترتیب یازده خروجی Money به یازده Label دقیق از IL متد ۳۹۴-Instructionی
  `RefreshSummary` وصل شد؛ Scope ورودی Reconcile/Date/Account حفظ شد.
- هر مقدار منفی در Local copy قدرمطلق، داخل پرانتز و Red؛ صفر/مثبت DarkBlue
  نمایش داده می‌شود. ۱۱ Compare، ۱۱ Multiply، ۲۲ Text و ۲۲ Color assignment ثبت شد.
- این رفتار فقط Presentation است و هیچ Entity را Update نمی‌کند؛ مقصد Signed
  decimal و Accessibility مستقل از رنگ می‌خواهد.
- فرمول Procedure و Row parity همچنان اثبات نشده و این کشف Command/Pilot را باز
  نمی‌کند. هیچ فرم، Procedure، Business row یا String literal اجرا/خوانده/ثبت نشد.
- سند: `BANK_RECONCILIATION_SUMMARY_UI_BOUNDARY_20260827_FA.md`.

## ۲۰۲۶-۰۸-۲۷ — قرارداد بستن سه Root حل‌نشده

- اسکن ایستا روی ۶۲ Assembly و ۸۵۳ فایل exhausted است؛ اجرای دوباره با همان
  ورودی توصیه نمی‌شود و هر سه Root به Runtime/owner evidence نیاز دارند.
- frmReconciliationSetup منطق واقعی Import دارد و در Scope می‌ماند، ولی Route
  آن provisional است؛ frmBankReconciliationList template/file-preview candidate
  و SpecialOptionsDistrict placeholder/dynamic candidate است.
- Telemetry بدون هویت با سه Session و allowlist فیلدها تعریف شد؛ business value،
  credential، raw SQL و identity ممنوع است. Scope exclusion خودکار صفر است.
- سند: `UNRESOLVED_ROOT_CLOSURE_CONTRACT_20260827_FA.md`.

## ۲۰۲۶-۰۸-۲۷ — Role/UAT بدون هویت مغایرت بانکی

- هفت Capability به شش Role template پیشنهادی وصل شد؛ Reversal از Confirm/Cancel
  جداست و Edit→Confirm، Delete→Cancel/Reverse و Aggregate count→Actor allow ممنوع است.
- ۱۰۰ Case مصنوعی شامل ۴۲ assignment، ۳۰ context منفی، ۱۵ state/profile، هفت
  SoD و شش non-inference ساخته شد؛ authenticated execution و owner approval صفر است.
- Authorization مقصد ترکیب Capability، feature، fiscal/DC/account scope، تاریخ
  عملیات، state و domain validation است؛ Parent UI هیچ حقی به Web ارث نمی‌دهد.
- سند: `BANK_RECONCILIATION_ROLE_UAT_CONTRACT_20260827_FA.md`.

## ۲۰۲۶-۰۸-۲۷ — مرز Profile و State مغایرت بانکی

- Setup چهار Profile field را از projection `BankAccount2` می‌گیرد؛ View جاری
  ۴۶ ستون و هفت dependency دارد و dispatch دقیق Import روی dbf/txt/xls است.
- چهار جدول Profile جمعاً صفر ردیف و فاقد Version/EffectiveDate/Active/Approval
  هستند؛ StartRow/Seperator/IsArabic در جدول‌اند ولی getter آن‌ها در فرم دیده نشد.
- Reconcile ستون State ندارد؛ Confirm با Key `Ok` جفت ConfirmerId/ConfirmDate را
  می‌نویسد و Amount را صریحاً Decimal.Zero می‌کند. marker ناقص باید quarantine شود.
- `frmBankReconciliationList` صف مغایرت اثبات‌شده نیست: loader خالی و coupling
  آن TransferList/Transfer است؛ Child فقط Excel preview است. Root همچنان
  unresolved/template-like و ساخت Route یا حذف حدسی ممنوع است.
- سند: `BANK_RECONCILIATION_PROFILE_STATE_BOUNDARY_20260827_FA.md`.

## ۲۰۲۶-۰۸-۲۷ — مرز Match مغایرت بانکی

- `DoVocherPass` برخلاف نامش سند حسابداری صادر نمی‌کند؛ یک ReconcileItem Link
  میان BankBill و دقیقاً یکی از شش منبع PCheque/PWithdraw/RBankDraft/RCashDraft/
  RCheque/Transfer می‌سازد.
- دو Event گرید با سیگنال‌های Decimal equality/absolute difference و تأیید کاربر
  Link را فوراً Persist و Grid/Summary را Refresh می‌کنند؛ مقصد Event persistence
  را حذف و فرمان صریح و idempotent تعریف می‌کند.
- Read model بر FreeBankAccountCardex/FreeBankBill/BankBill2 و account/as-of-date
  scope تکیه دارد؛ ۲۷ ستون و ۱۱ dependency کاتالوگی بدون ردیف/تعریف SQL ثبت شد.
- BeforeReconcileItem/AfterReconcileItem در IL probe می‌شوند اما در Clone حاضر
  نیستند؛ مقصد runtime hook discovery و nested static transaction را حذف می‌کند.
- Summary به `DoReconcile_GetSummary` با سه ورودی scope و ۱۱ خروجی money وصل شد؛
  نام/نوع پارامتر و شش dependency اثبات شد، اما فرمول metricها بدون definition/row
  همچنان نیازمند fixture یا owner validation است.
- Artifact/Extractor با ۱۵ Method، شش mapping، ۱۴ پارامتر Summary و صفر
  validation error ثبت شد؛ سیاست tolerance مبلغ هنوز نیازمند شاهد بیشتر است.
- سند: `BANK_RECONCILIATION_MATCHING_BOUNDARY_20260827_FA.md`.

## Checkpoint مبنای شروع این ادامه — ۲۰۲۶-۰۸-۲۷ (Snapshot تاریخی)

- شناخت مغایرت بانکی اکنون Source model، فیلد/Guard، Parser، Persistence،
  Transaction، Cardex SQL، Permission catalog، Delete semantics و ۹۳ Golden case
  را به‌صورت Artifact/Extractor/Test پوشش می‌دهد.
- Source model اکنون ۱۵ Object/۲۶۹ ستون دارد و ReconciliationColumn را نیز در
  Profile وارد می‌کند؛ ۸ جدول هسته/Profile در Clone صفر ردیف‌اند.
- Effective permission نه فقط Assignment: روی ۱۴۱ کاربر فعال، Allow بسته به
  Node برابر ۱۸ یا ۲۷ و Admin bypass برابر ۷ است؛ خروجی فقط Aggregate است.
- سه Root حل‌نشده علاوه بر ۶۲ اسمبلی، در ۸۵۳ فایل Deployment نیز بررسی شدند؛
  reference بیرونی صفر و وضعیت unresolved با محدودیت صریح حفظ شد.
- در این Snapshot تاریخی، Baseline ۱۴۴ Source با `NO_SEMANTIC_DRIFT` بود و Bundle ۱۵۵ Artifact،
  ۹۰ سند و ۱۲۲ Builder/Extractor با `PASS` و صفر خطا دارد.
- Handoff نیز از Snapshot فعلی بازسازی شد: ۸۷۷ Golden case در Traceability عمومی
  ثبت است و Matrix ماژول با افزودن ۹۳ Case بانک به ۹۷۰ Mapping می‌رسد؛ این دو
  شمارش Scope متفاوت دارند و نباید به‌عنوان تناقض یا پوشش اجرایی تفسیر شوند.
- Suite فعلی ۱۲۲ تست PASS دارد. هیچ فرم/assembly/SQL command اجرا نشد و هیچ
  business row، هویت فردی یا Source عملیاتی تغییر نکرد.
- با وجود این پیشرفت، Command/Pilot/Production-ready همچنان صفر است: Profile و
  ردیف واقعی Clone در بخش بانک صفر، Cancel مستقل Legacy اثبات‌نشده، سه Root باز،
  Effective permission فردی/UAT و Target implementation/parity هنوز انجام نشده‌اند.

### ترتیب ادامهٔ کم‌ریسک

1. یک Snapshot فقط‌خواندنی و Redacted از Profile واقعی Import و چند Session در
   وضعیت‌های مختلف تهیه شود تا Parser/State/Count بدون نگهداری مقدار تجاری سنجیده شود.
2. با حساب‌های تست نقش‌محور، View/Import/Match/Unmatch/Confirm/Cancel جداگانه UAT
   شوند؛ Aggregate فعلی مجوز هیچ فرد مشخصی را ثابت نمی‌کند.
3. برای سه Root باز، Telemetry اجرای واقعی یا تأیید مالک فرایند گرفته شود؛ نبود
   Reference استاتیک مجوز حذف یا ساخت Route حدسی نیست.
4. پیاده‌سازی مقصد از Read model و Import staging شروع شود؛ Commandها فقط پس از
   قرارداد State/Permission/OperationDate، Idempotency، Transaction/Outbox و
   اجرای ۹۳ Golden case و Parity کاردکس فعال شوند.

## ۲۰۲۶-۰۸-۲۷ — Shape تنظیمات Profile Import بانک

- سه جدول BankBillFormatType/BankBillFormat/BankBillFormatItem نوع فایل،
  Bank/Account type، StartRow/Separator/HDR/Arabic و نگاشت بازه ستون را مدل می‌کنند.
- SQLStatement و SchemaFile در Profile Legacy ذخیره می‌شوند، ولی هر سه جدول در
  Clone صفر ردیف‌اند؛ مقدار نمونه و parity عملیاتی در دسترس نیست.
- مقصد Profile نسخه‌دار و allowlist‌شده می‌سازد؛ SQL/provider/path دلخواه از
  پیکربندی قابل اجرا نیست. این Shape در Artifact مدل منبع و تست پایدار شد.

## ۲۰۲۶-۰۸-۲۷ — تفکیک Deleteهای مغایرت بانکی

- Delete در فرم Detail با transaction و روال `DoBankBill_DeleteReconcileItem`
  فقط یک Link را Unmatch می‌کند؛ امضا BankBillId/ErrorNo و وابستگی ReconcileItem است.
- Delete در Setup پس از بررسی Link، BankBillS را Delete/Update می‌کند و هیچ
  Reconcile.Delete/Update ندارد؛ این Discard ردیف Import است، نه Cancel Session.
- فرمان مستقل Legacy برای Cancel مشاهده نشد؛ Cancel در Golden فعلاً provisional،
  نیازمند sign-off مالک و جدا از Reversal Session تأییدشده است.
- سند: `BANK_RECONCILIATION_DELETE_SEMANTICS_20260827_FA.md`.

## ۲۰۲۶-۰۸-۲۷ — مرز Persistence صورت‌حساب بانکی

- مسیر SaveData تا SQL از Reconcile.Update/UpdateDetailTables و BankBillS/BankBill
  به BankBillAdapter و CRUD رسید؛ ۱۰ Method با Hash منطبق ثبت شد.
- هفت fingerprint شامل چهار SELECT از BankBill2 و INSERT/UPDATE/DELETE روی
  BankBill است؛ متن SQL و داده تجاری ذخیره نشد.
- سه Hook name در Adapter دیده شد، اما Clone فقط
  `DoBankBill_DeleteReconcileItem` را دارد؛ Before/After در Clone غایب‌اند.
- مقصد Header/rows را اتمیک commit می‌کند، Staging حق Ledger commit ندارد و Hook
  اختیاری Runtime را به event/outbox صریح و نسخه‌دار تبدیل می‌کند.
- سند: `BANK_STATEMENT_PERSISTENCE_BOUNDARY_20260827_FA.md`.

## ۲۰۲۶-۰۸-۲۷ — کاتالوگ مجوز مغایرت بانکی

- Aliasهای IL در Clone تأیید شدند: `TransferList` چهار Child و
  `ReconciliationSetup` سه Child دارد؛ هر دو زیر `OtherOperation` هستند.
- هیچ Child مستقل Confirm وجود ندارد؛ مقصد `Edit` را به Confirm ارتقا نمی‌دهد و
  شش Capability پایه برای View/Import/Match/Unmatch/Confirm/Cancel تعریف می‌کند؛
  Reversal مستقل یک Capability مقصدی افزوده و از Alias Legacy استنتاج نشده است.
- فقط Aggregate ثبت شد: ۶۳ Allow مستقیم، ۲۲ Allow گروهی و صفر Deny؛ Effective
  allow روی ۱۴۱ کاربر فعال بسته به Node برابر ۱۸ یا ۲۷ و Admin bypass برابر ۷
  است. هویت/عضویت/حق منفرد ذخیره نشد و مجوز شخص نام‌برده‌ای ادعا نمی‌شود.
- سند: `BANK_RECONCILIATION_PERMISSION_CATALOG_20260827_FA.md`.

## ۲۰۲۶-۰۸-۲۷ — اسکن کامل Deployment برای سه Root حل‌نشده

- ۸۵۳ فایل منتخب DLL/EXE/Disable/Config/XML/Manifest/TXT/RESX با مجموع
  ۵۹۸٬۵۵۸٬۴۳۱ بایت برای فقط سه نام Type allowlist‌شده خوانده شد؛ خطا صفر بود.
- Match فقط در دو اسمبلی تعریف‌کننده و کپی `.disable` همان‌ها دیده شد؛ Plugin،
  Config یا Binary خارجی با reference دقیق صفر است.
- این شاهد احتمال launcher استاتیک بیرونی را کم می‌کند ولی فرم dynamic/محیط دیگر
  یا legacy را رد نمی‌کند؛ هر سه Root همچنان unresolved و حذف حدسی ممنوع‌اند.
- سند: `DEPLOYMENT_ROOT_REFERENCE_SCAN_20260827_FA.md`.

## ۲۰۲۶-۰۸-۲۷ — مرز SQL ثبت کاردکس تطبیق بانکی

- IL محدود و کاتالوگ Clone هر دو فرمان `dbo.DoReconcile_UpdateBankAccountCardex`
  را تأیید کردند؛ Hash اسمبلی منطبق و خطای اعتبارسنجی صفر است.
- امضا `@ReconcileId int` ورودی و `@ErrorNo tinyint` خروجی است؛ ۹ وابستگی
  کاتالوگی شامل ReconcileItem و هفت نوع سند خزانه ثبت شد.
- مقصد روال Legacy را مستقیم API نمی‌کند؛ `bank_reconciliation.confirm` یک
  Application-service transaction دارد و اثرات پس از Commit با parity check سنجیده می‌شود.
- متن روال، داده تجاری و اجرای command عمداً صفر بود؛ سند:
  `BANK_RECONCILIATION_CARDEX_SQL_BOUNDARY_20260827_FA.md`.

## ۲۰۲۶-۰۸-۲۷ — Transaction تأیید مغایرت بانکی

- DoAccept Scope بیرونی دارد و Reconcile.Update/UpdateBankAccountCardex هر دو
  Scope داخلی می‌سازند؛ شمارنده Level فقط outermost Commit را Physical می‌کند.
- TransactionLevel، Connection، ConnectionString و Trans همگی static و بدون
  ThreadStatic هستند؛ کپی این State process-wide به Web ممنوع شد.
- مقصد یک Application-service Transaction owner و UnitOfWork command-scoped دارد؛
  Repository-level Commit مجاز نیست.
- سند: `BANK_RECONCILIATION_TRANSACTION_BOUNDARY_20260827_FA.md`.

## ۲۰۲۶-۰۸-۲۷ — Golden caseهای مغایرت بانکی مقصد

- پنج Command مقصد به ۹۳ Case مصنوعی تبدیل شد: ۴۰ مشترک، ۱۵ Fault injection،
  ۳۰ مرز دامنه‌ای و ۸ parity پس از Commit؛ Duplicate id صفر است.
- Matrix ماژولی اکنون ۹۷۰ Golden نگاشت‌شده دارد و سهم Receivables/Treasury از
  ۶۹ به ۱۶۲ رسیده، بدون اینکه Command/Pilot/Production-ready شود.
- فایل/Parser، لینک چندنوعی، Cross-account، Idempotency، Date/State، Cardex و
  Outbox پوشش داده شد و Source وارانگار در تمام Caseها ممنوع است.
- PASS فقط طراحی تست است؛ Command مقصد اجرا یا پیاده‌سازی نشده و مالک فرایند P06
  هنوز نیازمند تأیید کسب‌وکار است.
- سند: `BANK_RECONCILIATION_GOLDEN_CASES_20260827_FA.md`.

## ۲۰۲۶-۰۸-۲۷ — مرز Import صورت‌حساب بانکی

- سه Parser DBF/TXT/XLS از OleDbConnection/OleDbCommand/DataAdapter.Fill استفاده
  می‌کنند و Dispatch به FormatExtension/HDR/SchemaFile/SQLStatement وابسته است.
- Schema file در Desktop ایجاد/حذف می‌شود؛ مسیر Excel نیز Interop، Copy/Delete و
  `Process.Kill` دارد.
- این شاهد مرز پرریسک را ثابت می‌کند، نه Injection واقعی. مقصد باید Parser ایزوله،
  Profile نسخه‌دار، Staging/Quarantine و بدون Office Automation داشته باشد.
- سند: `BANK_STATEMENT_IMPORT_BOUNDARY_20260827_FA.md`؛ Artifact:
  `varanegar_bank_statement_import_boundary_20260827.json`.

## ۲۰۲۶-۰۸-۲۷ — ارزیابی SpecialOptionsDistrict

- فرم فقط سه Method Designer، صفر Business method و صفر Field مستقیم دارد؛ ۸۸
  Field دیگر صرفاً از Base framework ارث می‌رسد.
- Route ثابت، Launcher/Reference بیرونی در ۶۲ Assembly و Candidate چهار الگوی
  محدود نام Object/Column در Clone همگی صفر بودند.
- اسکن تکمیلی Stringهای تعبیه‌شده نیز برای نام کامل/کوتاه سه Root روی ۸۱٬۴۷۳
  Method body صفر Reference داد؛ متن خام Stringها ذخیره نشد.
- نتیجه «پوسته یا قابلیت پویا و حل‌نشده» است؛ حذف از Scope یا ساخت Schema/Command
  حدسی مجاز نیست.
- سند: `SPECIAL_OPTIONS_DISTRICT_ASSESSMENT_20260827_FA.md`؛ Artifact:
  `varanegar_special_options_district_assessment_20260827.json`.

## ۲۰۲۶-۰۸-۲۷ — Guardهای فرمان مغایرت بانکی

- List از Alias مجوز `TransferList.AddNew/Edit/Delete` همراه Gate بسته‌بودن تاریخ
  عملیات استفاده می‌کند؛ Alias قدیمی نباید نام Capability مقصد شود.
- Setup با `ReconciliationSetup.Edit/Delete` Guard می‌شود و Validation آن حساب،
  تاریخ بانک و فایل بانک را لمس می‌کند.
- حذف Link در Detail Signal کامل Start/Commit/RollBack دارد؛ مسیر Import/Save در
  UI Signal Transaction مشابه ندارد و Transaction owner مقصد باید صریح باشد.
- چهار Type و ده Method با Hash منطبق و صفر خطای Parse ثبت شد؛ سند:
  `BANK_RECONCILIATION_COMMAND_GUARDS_20260827_FA.md`.

## ۲۰۲۶-۰۸-۲۷ — فیلدهای فرم‌های اولویت‌بالا و مرز ارث‌بری

- هفت Type با Parse متادیتای آفلاین و Hash منطبق بررسی شد؛ شش فرم Treasury مجموعاً
  ۲۲۹ Field مستقیم دارند و صفر Type گمشده یا خطای Metadata ثبت شد.
- `FormSpecialOptionsDistrict` صفر Field مستقیم دارد، اما زنجیره Base آن ۸۸ Field
  عمومی Framework دارد؛ این ۸۸ مورد اثبات کنترل قابل‌مشاهده یا Binding دامنه‌ای نیست.
- نام Fieldها فقط برای Shape اولیه استفاده شد؛ مقدار، String، Resource، Config،
  DLL runtime و UI خوانده/اجرا نشد.
- سند: `PRIORITY_FORM_DECLARED_FIELDS_20260827_FA.md`؛ Artifact:
  `varanegar_priority_gap_declared_fields_20260827.json`.

## ۲۰۲۶-۰۸-۲۷ — مدل منبع مغایرت‌گیری بانکی

- مغایرت بانکی یک Aggregate از `Reconcile`، قالب/فایل بانک، `BankBill` و
  `ReconcileItem` است؛ CRUD مستقیم یک جدول قرارداد درستی نیست.
- ۱۵ Object، ۲۶۹ ستون، ۶۵ FK و ۲۱ Trigger ثبت شد؛ ۴۷ FK `not trusted` است.
- `ReconcileItem` به BankBill و شش نوع Source خزانه لینک می‌شود؛ لینک بدون Source،
  چندSource یا مبهم باید در مقصد Quarantine شود.
- UI/IL وجود Transaction، ConfirmDate/Confirmer و
  `UpdateBankAccountCardex` را نشان می‌دهد، اما Result parity اجرا نشده است.
- هشت جدول هسته در Clone صفر ردیف دارند؛ بنابراین این شکاف با کوتاه‌کردن بازه
  سه‌ماهه حل نمی‌شود و به Snapshot/محیط ایزوله نیاز دارد.
- سند: `BANK_RECONCILIATION_SOURCE_MODEL_20260827_FA.md`؛ Artifact:
  `varanegar_bank_reconciliation_source_model_20260827.json`.

## ۲۰۲۶-۰۸-۲۷ — Checkpoint نهایی بازهٔ شبانه

- Snapshot نهایی ساعت ۰۸:۴۶ با همان پیمایش محدود breadth-first ثبت شد.
- مقایسه فقط با Baseline روش ثابت ۰۷:۴۰ انجام شد و هر شش بخش معنایی Unchanged
  ماند: یک پنجره، ۸۳ Control و ۱۹ Label مجاز.
- نتیجه `NO_SEMANTIC_UI_DRIFT` است؛ Invoke/Input/SetValue/SendMessage و Write
  دیتابیس همچنان صفر باقی ماند.
- Artifactها: `varanegar_ui_checkpoint_20260827_0900.json` و
  `varanegar_ui_checkpoint_comparison_20260827_0900.json`.

## ۲۰۲۶-۰۸-۲۷ — پایدارسازی پیمایش UI Automation بدون تعامل

- `FindAll(Descendants)` Provider فعلی متوقف می‌شد؛ سه Client PowerShell قدیمی
  و موقت بسته شدند، اما Process وارانگار PID 18160 باز و پاسخ‌گو ماند.
- Extractor به breadth-first `TreeScope.Children` با سقف ۵۰۰۰ Element تبدیل شد؛
  Invoke/Input/SetValue/SendMessage همچنان صفر است.
- Baseline روش جدید ساعت ۰۷:۴۰، ۸۳ Control و ۱۹ Label مجاز دارد. اختلاف با
  ۰۵:۴۵ در `source/UIA` ثبت شد، اما `safety/Win32` ثابت است؛ تکرار فوری روش
  جدید هر شش بخش را بدون تغییر بازگرداند و اختلاف قدیم/جدید به‌تنهایی Release
  drift نیست.
- سنجش ۰۹:۰۰ فقط با Baseline ۰۷:۴۰ و همان روش مقایسه می‌شود.
- Probe ساعت ۰۸:۰۰ نیز هر شش بخش را Unchanged و ۸۳/۱۹ را ثابت برگرداند؛ فایل
  موقت وارد Bundle نشد.
- سند: `UI_CHECKPOINT_0545_TO_0900_20260827_FA.md`
- Artifact: `varanegar_ui_checkpoint_20260827_0740.json`

## ۲۰۲۶-۰۸-۲۷ — تطبیق Executable زنده با بسته تحلیل‌شده

- Process باز و پاسخ‌گوی `VN.SDS.Container` روی `192.168.1.184` فقط از طریق
  metadata سیستم‌عامل و Hash فایل بررسی شد؛ هیچ UI action اجرا نشد.
- SHA-256 فایل اجرایی Process دقیقاً یک Match با `VN.SDS.Container.exe` در
  Inventory ۶۲ فایل داشت؛ بنابراین Executable زنده با بستهٔ تحلیل‌شده منطبق است.
- این تطبیق نقطه‌ای، Lazy-loaded DLLها یا اجرای همه Branchهای Runtime را اثبات
  نمی‌کند و جای Snapshot/Drift نهایی را نمی‌گیرد.
- Artifact مرجع: `varanegar_binary_inventory_20260827.json`
- سند: `RUNTIME_DRIFT_BASELINE_20260827_FA.md`

## ۲۰۲۶-۰۸-۲۷ — اصلاح مالک واحد انتشار تنظیمات

- Blueprint مالک `config_definition/config_value/config_version` را ماژول
  Configuration می‌داند، ولی قرارداد افزونه General/WebService را به Platform
  نسبت داده بود.
- مالک دو Command `configuration.publish_general_version` و
  `configuration.publish_web_service_version` به Configuration اصلاح شد؛
  Platform فقط سرویس‌های مشترک Idempotency/Audit/Outbox را فراهم می‌کند.
- ۲۱۵ Golden افزونه بدون تغییر تعداد PASS شد و ۳۶ Case از Platform به
  Configuration منتقل شد؛ این اصلاح از دو مالک Write برای تنظیمات جلوگیری می‌کند.
- سند: `EXTENSION_TARGET_CONTRACTS_20260827_FA.md`
- Artifact: `varanegar_extension_target_contracts_20260827.json`

## ۲۰۲۶-۰۸-۲۷ — تکمیل نگاشت Goldenهای Master/Foundation به فرایندها

- Atlas پیشین Goldenهای `master` و `foundation` را در Traceability داشت، اما
  تفکیک Source فرایند فقط Core/Orchestrator/Extension/Report را می‌شمرد.
- P01 اکنون ۱۱۹ Case و P02 اکنون ۱۹۶ Case دارد؛ P04 نیز ۳۲ Case Context انبار
  را صریحاً در Source foundation نشان می‌دهد.
- Invariant اجباری شد که جمع Sourceهای هر فرایند با کل Golden همان فرایند برابر
  باشد؛ ده فرایند PASS و صفر فرایند Implementation-ready باقی ماند.
- سند: `END_TO_END_PROCESS_ATLAS_20260827_FA.md`
- Artifact: `negin_erp_end_to_end_process_atlas_20260827.json`

## ۲۰۲۶-۰۸-۲۷ — مرز چهارگانه تاریخ قطعی

- پنج Route تاریخ قطعی پیکربندی‌شده است؛ دو Form فروش runtime-matched و سه Form
  خرید/مالی/تنخواه present-package ولی unmatched هستند.
- سه Capability افزونه Business-mediated و direct UI→DataAccess صفرند؛ Handler
  چهار Update/پنج Validation و DataAccess چهار Update/چهار Validation دارد.
- مقصد چهار Command جدا و نسخه‌دار با DC/FiscalYear، Reopen صریح، Audit/Outbox
  اتمیک و Reconciliation می‌خواهد؛ Runtime effect و Golden execution صفر است.
- ریسک بحرانی `R-041` ثبت شد؛ پس از اصلاح ریسک موجودی، شمار کل ریسک ۴۱ و ریسک بحرانی ۱۷ است.
- سند: `FINAL_DATE_MANAGEMENT_CROSS_DOMAIN_BOUNDARY_20260827_FA.md`
- Artifact: `varanegar_final_date_management_boundary_20260827.json`

## ۲۰۲۶-۰۸-۲۷ — قرارداد تشخیص رخداد تاریخ عملیات و تاریخ قطعی

- زنجیرهٔ سه فرم جدید خرید/مالی/تنخواه تا Handler، DataAccess و Procedureهای
  `GNR.USP_SDSNET_*` فقط با PE/IL و کاتالوگ Clone دنبال شد؛ هیچ Assembly یا
  Command عملیاتی اجرا نشد.
- یازده یافته ثبت شد: سه بحرانی، هفت High و یک Medium. مهم‌ترین‌ها حذف
  `UserRef` اجباری در شش مسیر Insert، حذف Opening statement بدون قید سال هنگام
  بازگشایی مالی و تغییر سراسری وضعیت توزیع هنگام بازگشایی فروش هستند.
- در آخرین سال مالی، از دو DC فقط یک رکورد SysRef فروش و یک رکورد مالی وجود
  دارد؛ خرید/تنخواه/هزینهٔ شعبه برای هر دو DC غایب‌اند. بنابراین عیب «ویرایش
  کار می‌کند ولی ایجاد اولیه شکست می‌خورد» یک امضای تشخیصی مستند است.
- اسکن محدود سه‌ماههٔ Log، ۱۶۰ Update مرتبط و صفر Insert/Delete نشان داد؛ متن
  Script، هویت و تاریخ‌های کسب‌وکاری ذخیره نشدند. دسترسی به DMV اجرای Procedure
  به‌علت نبود `VIEW SERVER STATE` ممکن نبود.
- سند: `FINAL_DATE_INCIDENT_DIAGNOSTIC_PLAYBOOK_20260827_FA.md`
- Artifact: `varanegar_final_date_diagnostic_contract_20260827.json`
- Extractor: `scripts/sql/extract_varanegar_final_date_diagnostic_contract.py`

## ۲۰۲۶-۰۸-۲۷ — Navigation و precedence تنظیمات سیستم

- ریشه تنظیمات پنجاه Route و پانزده FormInfo/AccessNode پیکربندی‌شده دارد؛ فقط
  چهار Form در Runtime package منطبق و یازده مورد unmatched است.
- شواهد فقط‌خواندنی ۱۷۷ کلید General، ۳۳۴ کلید Server، چهل کلید History-only و
  ۲۲ Rule key میان‌ماژولی را بدون مقدار یا Secret به این Navigation وصل کرد.
- مقصد باید precedence نسخه‌دار `global/server/DC/device/app/user-exception`،
  Explain، Draft/Published، Secret store و Command مستقل Close/Publish داشته باشد.
- سند: `SYSTEM_CONFIGURATION_NAVIGATION_AND_PRECEDENCE_20260827_FA.md`
- Artifact: `varanegar_system_configuration_navigation_contract_20260827.json`

## ۲۰۲۶-۰۸-۲۷ — شکاف Runtime مدیریت کاربر، گروه و دسترسی

- شانزده Route استاتیک برای معرفی کاربر/گروه، تنظیمات کاربری، دسترسی ویژه،
  انبار/مالی، صندوق و Scope اطلاعات جدا شد؛ Runtime-matched form صفر است.
- ده Route دارای FormInfo/AccessNode هستند، اما هیچ هویت، عضویت گروه یا Grant
  فردی خوانده نشد و رفتار مجوز مؤثر اثبات نشده است.
- مرز مقصد `deny-first capability + scope` و اولین Slice فقط‌خواندنی بدون هویت
  شخص ثبت شد؛ Write تا Policy owner/UAT/SoD/Audit روی Target ایزوله مسدود است.
- سند: `IDENTITY_ACCESS_ADMINISTRATION_NAVIGATION_GAP_20260827_FA.md`
- Artifact: `varanegar_identity_access_navigation_gap_contract_20260827.json`

## ۲۰۲۶-۰۸-۲۷ — ۱۹۲ Golden case پایه برای تأمین‌کننده، Context و قیمت

- دوازده Command نامزد به ۱۹۲ Case مصنوعی وصل شد: ۳۲ Master تأمین‌کننده، ۶۴
  Context سازمانی، ۳۲ Context حسابداری/انبار و ۶۴ Pricing؛ ۳۵ مورد Failure
  injection است.
- مجموع Golden قابل‌ردیابی ERP از ۶۸۵ به ۸۷۷ رسید؛ همه Caseها فقط برای Target
  test DB ایزوله طراحی شده‌اند و روی وارانگار/Clone اجرا نشده‌اند.
- Gap تعریف Golden در یک Screen تأمین‌کننده، سه Screen Context و دو Screen
  قیمت صفر شد؛ Owner approval، Implementation readiness و Runtime execution
  همچنان صفر است.
- Artifact: `negin_erp_foundation_context_pricing_golden_cases_20260827.json`
- Builder: `build_negin_erp_foundation_context_pricing_golden_cases.py`

## ۲۰۲۶-۰۸-۲۷ — مرز قیمت زمینه‌ای و تخفیف

- دو فرم CPrice/Discount در ۵۶ Method/۱۳٬۴۳۳ Instruction، ۱۱۹ Field reference،
  چهارده Rule و دو Commit signal مدل شدند.
- Scope قیمت شامل مشتری/نوع، جغرافیا، DC، BuyType، Currency، Batch، Package/Unit
  و Priority است؛ تخفیف نیز Condition/Arrange/Group/Prize/PreventSale/Close دارد.
- دو Screen دارای چهل Input است؛ ۳۲ Label و هشت Gap متن استاتیک ثبت شد.
- ۶۴ Golden save/copy/priority/close/delete/retry/fault طراحی شد؛ Runtime parity
  و اجرای Caseها صفر است.
- ریسک `R-040` تخت‌کردن Rule و ازبین‌بردن Version/precedence/explain را منع می‌کند.
- سند: `CONTEXTUAL_PRICE_DISCOUNT_WEB_BOUNDARY_20260827_FA.md`

## ۲۰۲۶-۰۸-۲۷ — تحویل صبح برای شروع ERP شخصی نگین

- ۱۸ دامنه، ۴۴۵ فرم، ۸۳۶ Route، بیست Workflow، بیست Report، چهارده ماژول، ده
  Process، ۸۷۷ Golden case و ۴۱ ریسک در Handoff همان checkpoint صبح جمع شد؛
  Baseline جاری بعداً به ۴۵ ریسک ارتقا یافت.
- نتیجه صریحاً `SUBSTANTIAL...NOT_COMPLETE_RUNTIME_PARITY` است؛ Command-ready و
  Implementation-ready صفر باقی ماند.
- ترتیب هشت‌مرحله‌ای از Safety/Context تا Read-only، Snapshot/Harness، Command
  ایزوله و Pilot Gate ثبت شد.
- سند: `MORNING_HANDOFF_0900_20260827_FA.md`
- Artifact: `negin_erp_morning_readiness_handoff_20260827.json`

## ۲۰۲۶-۰۸-۲۷ — مرز سال عملیاتی و Stock/DC

- سه فرم سال عملیاتی، Stock/DC و تنظیم حسابداری انبار در ۴۱ Method/۱٬۱۰۵
  Instruction، بیست Field reference، نه Rule و دو Commit signal مدل شدند.
- StockDC رابطهٔ DC/SaleOffice/Stock/ShipType و پنج Flag نوع موجودی را مدیریت
  می‌کند؛ ICAstockdcinfo نیز PriceMethod و Guard `StockHasPrice` دارد.
- سه Screen دارای ۲۶ Input است؛ ۱۷ مورد Label دارند و نه مورد بدون متن استاتیک
  قابل اتکا هستند. سه Screen به ۹۶ Golden طراحی‌شده وصل‌اند؛ Runtime parity صفر است.
- ریسک `R-039` از یکی‌گرفتن سال عملیاتی/مالی و تخت‌کردن Context انبار جلوگیری
  می‌کند.
- سند: `OPERATIONAL_CONTEXT_AND_STOCK_DC_WEB_BOUNDARY_20260827_FA.md`

## ۲۰۲۶-۰۸-۲۷ — مرز مستقل Master تأمین‌کننده

- `FormSupplier` در ۱۹ Method/۶۲۸ Instruction دارای یازده Field reference، نه
  Rule و یک Commit signal است.
- حذف با `IsUsedInPay` محافظت می‌شود و Save به After-save، Contact/DL، گروه
  حسابداری، Status، Attachment و Cardex وابسته است.
- Parse کامل ۴۱ Field، ۳۷ Component، دوازده Web-input و سیزده Control دارای
  Layout binding را ثبت کرد؛ Type unresolved صفر است.
- ۳۲ Golden ذخیره/حذف تأمین‌کننده طراحی شد، اما اجرا نشده و Screen مقصد
  Write-ready نیست.
- ریسک `R-038` ثبت شد؛ Read-only list/detail اولین Slice مجاز است.
- سند: `SUPPLIER_MASTER_WEB_SCREEN_BOUNDARY_20260827_FA.md`

## ۲۰۲۶-۰۸-۲۷ — ۶۴ Golden case مشتری و کالا

- چهار Command نامزد `customer.save/delete` و `goods.save/delete` به ۶۴ Case
  مصنوعی وصل شد؛ ۴۴ حالت مشترک و ۲۰ حالت دامنه‌ای، شامل ۱۲ Fault injection.
- هر Screen به ۳۲ Case وصل است و Gap تعریف Golden صفر شد؛ Owner-approved،
  Implementation-ready و Runtime-executed همچنان صفر است.
- همه Caseها فقط برای Target test DB ایزوله طراحی شده‌اند؛ وارانگار و Clone
  جزو محیط‌های ممنوع اجرای Case هستند.
- Artifact: `negin_erp_customer_goods_master_golden_cases_20260827.json`
- Builder: `build_negin_erp_customer_goods_master_golden_cases.py`

## ۲۰۲۶-۰۸-۲۷ — Screen و Command مشتری و کالا

- ۲۱ Method/۲٬۱۱۹ Instruction، ۲۹ Field reference، ده Rule و چهار Commit signal
  برای Save/Delete مشتری و کالا ثبت شد.
- مشتری ۲۶۳ Field/۶۹ Input و کالا ۱۷۸ Field/۶۱ Input دارد؛ Type unresolved صفر.
- دو Screen در مجموع ۱۳۰ Input و ۱۶ Command control دارند؛ فقط ۶۸ Input دارای
  Layout-label و ۶۲ Input فاقد متن استاتیک قابل اتکا هستند.
- در ثبت بعدی ۶۴ Golden contract برای Save/Delete تعریف شد؛ Read-only
  list/detail همچنان اولین Slice مجاز و فعال‌سازی Write فعلاً Block است.
- سند: `CUSTOMER_GOODS_MASTER_WEB_SCREEN_BOUNDARY_20260827_FA.md`

## ۲۰۲۶-۰۸-۲۷ — مرز سند حسابداری خودکار و دستی

- سه Entry point حسابداری شامل ۷۱ Method body، ۲۱ Method نوشتاری، چهار مسیر
  برگشتی/حذفی، هفت Command candidate و هشت Rule signal تفکیک شدند.
- سند خودکار چهار Transition تولید/تأیید/حذف/انتقال و Scope نوع سند/DC/بازه
  تاریخ/سال مالی/تنظیم تفکیک شعبه دارد؛ سند دستی ابعاد بدهکار/بستانکار مستقل دارد.
- کاتالوگ نامی Clone شامل ۱۲۸ Candidate، ۴۰ Procedure، ۲۷ View، ۱۱ Table و
  ۹ Trigger است؛ Binding دقیق و Runtime parity صفر است.
- سند: `ACCOUNTING_VOUCHER_ENTRYPOINTS_AND_AUTOMATION_BOUNDARY_20260827_FA.md`

## ۲۰۲۶-۰۸-۲۷ — Screen candidate سند انبار و خرید

- سه فرم Stock/Supplier دارای ۲۸۸ Field حل‌شده، ۲۱۳ Component و ۹۴ Web-input
  candidate شدند؛ Type unresolved صفر است.
- ۶۷ Layout binding دقیق، ۵۹ Input+Label و ۳۵ Input بدون Label ثبت شد.
- سه Screen به ۷۷ Golden case مصنوعی وصل شدند؛ Owner/Implementation/Runtime
  readiness هر سه صفر است و Deleteهای خرید Golden contract کامل ندارند.

## ۲۰۲۶-۰۸-۲۷ — Checkpoint فقط‌خواندنی ساعت ۰۵:۴۵

- UI وارانگار با ثبت ۰۳:۰۰ در شش بخش معنایی مقایسه شد؛ Drift صفر، یک پنجره،
  ۷۶ کنترل مشاهده‌شده و ۱۸ کنترل دارای عنوان امن ثبت شد.
- Invoke/Input/SetValue/Message/Screenshot همگی صفر هستند.
- ثبت نهایی نزدیک ساعت ۰۹:۰۰ در همان سند تکمیل می‌شود.
- سند: `UI_CHECKPOINT_0545_TO_0900_20260827_FA.md`

## ۲۰۲۶-۰۸-۲۷ — مرز فاکتور خرید و Trigger محافظ رابطهٔ سند

- دو فرم فاکتور و برگشت خرید در ۱۹ Method/۱٬۱۵۵ Instruction، پانزده Field،
  هشت Rule signal و سه Commit signal مدل شدند.
- IL لایه DataAccess دو Literal خاموش/روشن‌کردن Trigger محافظ و Delete رابطهٔ
  `ICA.tblSupInvInvoiceRelation` را آشکار کرد؛ هیچ‌کدام اجرا نشد.
- جدول رابطه پنج ستون، یک PK، یک FK و چهار Trigger فعال دارد.
- گراف چهار Trigger بدون Truncation به ۲۱۵ Node/۳۴۳ Edge، ۱۴۳ Trigger node،
  ۴۶ Table و ۲۹ Write target رسید؛ ۴۱ Dependency حل‌نشده است.
- سند: `SUPPLIER_INVOICE_RETURN_AND_TRIGGER_GUARD_BOUNDARY_20260827_FA.md`

## ۲۰۲۶-۰۸-۲۷ — مرز سند انبار و توزیع تا خروج

- نه Method کلیدی فرم سند انبار شامل ۱٬۱۲۲ Instruction، بیست Field و هشت Rule
  signal به سه Command مقصد `save`، `confirm_or_unconfirm` و `generate_return`
  متصل شد؛ Commit در Handler دیده می‌شود اما Runtime dispatch جنریک هنوز باز است.
- چهار Command توزیع به پنج Procedure، ۴۹ Parameter، ۶۵ Dependency و ۱۶ جدول
  Mutation target وصل شدند؛ پارامتر صریح Idempotency صفر است.
- ۱۶ جدول مقصد ۳۱۶ ستون، ۱۰۵ FK observation و ۸۷ Trigger فعال دارند.
- گراف سه‌لایه در ۵۰۰ Node/۱٬۲۱۵ Edge به Safety cap رسید؛ ۳۸ Write target،
  ۲۳۲ Dependency حل‌نشده و ۱۴۲ Frontier باقی ماند.
- سند: `STOCK_VOUCHER_AND_DISTRIBUTION_EXIT_BOUNDARY_20260827_FA.md`
- هیچ Command/Procedure/Trigger اجرا و هیچ Row عملیاتی خوانده یا نوشته نشد.

## ۲۰۲۶-۰۸-۲۷ — مرز Screen و Command درخواست، فروش و برگشت

- سه فرم اصلی به `order.save`، `order.convert_to_sale` و `sales_return.save`
  وصل شدند؛ ۱۸ Method/۱٬۷۵۴ Instruction، ۲۵ Business call و سیزده Rule signal
  ثبت شد و SQL مستقیم UI صفر است.
- Parse کامل ۴۲۳ Field، ۱۴۰ Web-input candidate و ۳۴۲ UI component داد؛
  Prefix-filter قبلی فقط ۴۳ Field را می‌دید.
- ۱۴۰ رابطهٔ دقیق `LayoutItem.set_Control` استخراج شد؛ ۱۲۲ مورد Input و ۱۱۳
  مورد Input+Label استاتیک‌اند. Runtime layout/binding/requiredness صفر است.
- گراف دو لایه ۳۰ Edge ریشه، ۵۳ Business method، ۸۶ Dependency و ۲۸ DataAccess
  method دارد؛ Member حل‌نشده و Hash mismatch صفر است.
- هفت Procedure Clone با ۹۵ Parameter و ۱۱۴ Dependency به دست آمد؛ دو Procedure
  Mutation دارند و ۹ Target پایدار کاتالوگی حل شد. Result-shape هر هفت همچنان
  Metadata failure دارد و Runtime parity صفر است.
- نه جدول Target دارای ۲۶۵ ستون، ۱۱۵ مشاهده FK، ۷۳ Trigger فعال و ۲٬۰۸۸
  Referencing-module observation هستند.
- گراف سه‌لایه Trigger در ۵۰۰ Node/۱٬۰۱۳ Edge به Safety cap رسید؛ ۳۸۴ Trigger،
  ۳۵ Write target، ۲۰۷ Dependency حل‌نشده و ۱۸۴ Frontier گسترش‌نیافته دارد.
- Risk بحرانی `R-033` ثبت شد؛ دفتر ریسک اکنون ۳۳ Risk شامل ۱۲ Critical است.
- سه Screen candidate به ۴۸ Golden case مصنوعی وصل شدند؛ Owner-approved،
  Implementation-ready و Runtime-executed صفر است.
- سند: `ORDER_SALE_WEB_SCREEN_AND_COMMAND_BOUNDARY_20260827_FA.md`
- Artifactها: `varanegar_order_sale_entry_command_contracts_20260827.json`،
  `varanegar_order_sale_ui_label_candidates_20260827.json`،
  `varanegar_order_sale_full_field_metadata_20260827.json`،
  `varanegar_order_sale_layout_bindings_20260827.json`،
  `negin_erp_order_sale_web_screen_contract_candidates_20260827.json`،
  `varanegar_order_sale_command_dependency_graph_20260827.json`،
  `varanegar_order_sale_sql_semantics_20260827.json`،
  `varanegar_order_sale_mutation_source_model_20260827.json` و
  `varanegar_order_sale_trigger_transitive_graph_20260827.json`.

## ۲۰۲۶-۰۸-۲۷ — مرز Command و View/Trigger ابزارهای دریافت

- سه فرم ویرایش نقد/چک/حواله هرکدام ExecuteNonQuery مستقیم و Transaction در UI
  دارند؛ ۲۴ setter و ۲۹ Field یکتا در مسیر فرمان ثبت شد.
- `dbo.RCheque` و `dbo.RCashDraft` Viewهای قابل‌نوشتن با Trigger `INSTEAD OF`
  سه‌رویدادی‌اند؛ جدول‌های زیرین `Acc.TblCheque` و `Acc.TblBankOrders` هستند.
- ریسک بحرانی `R-032` ثبت شد؛ Risk register اکنون ۳۲ ریسک شامل ۱۱ Critical است.
- سه Command مقصد و ۵۱ Acceptance obligation تعریف شد؛ Owner-approved، Implemented
  و Executed صفر است و هنوز به Golden bundle ۶۲۱تایی اضافه نشده‌اند.
- هفت Method خزانه، چهارده Rule signal شامل وضعیت/جمع رسید، تسویه، تاریخ خورشیدی،
  Customer-required، Duplicate draft number، Future date، Arrival interval و
  Safe/Bank balance دارد؛ شرط Branch دقیق همچنان اثبات نشده است.
- گراف سه‌لایه ۲۹ Trigger به ۳۷۶ Node/۷۵۵ Edge، ۲۷۰ Trigger و ۴۲ Write target
  رسید؛ سقف ۵۰۰ Node نخورده ولی ۱۶۰ Dependency حل‌نشده باقی است.
- Blast radius استاتیک Bridge چک ۱۲۱ Node/۱۰ Write target و Bridge حواله ۹۳
  Node/۱۱ Write target است؛ این Reachability به معنی اجرای همه Branchها نیست.
- Merge فیلدهای سه فرم ۶۸ Control داد: ۱۶ نامزد Property+Column، یک Conflict
  واقعی میان شماره حواله و Setting جلوگیری از تکرار، دو Property-only و هفت
  Validation/Command-only؛ Runtime binding/requiredness صفر است.
- Parse فقط‌خواندنی `InitializeComponent` سه عنوان فرم و ۳۷ متن Control را از
  ۴۰ انتساب UI Allowlist‌شده ثبت کرد؛ Runtime visibility/effective text صفر است.
- سه Screen contract نامزد وب ۲۷ Input، شش Command control، ۳۱ Label جفت‌نشده،
  چهارده Rule signal و ۵۱ Acceptance obligation را یکجا وصل می‌کند؛ هر سه هنوز
  `NOT_IMPLEMENTATION_READY` و Owner-approved/Runtime-Golden صفرند.
- هشت Object شامل ۲۳۵ ستون، ۷۵ مشاهده FK، ۲۹ Trigger فعال و ۸۰۴ مشاهده
  referencing module است؛ Definition یا مقدار تجاری خوانده نشد.
- Semantic footprint هر ۲۹ Trigger شامل ۱۳۳ Dependency و ۲۰ Mutation token است؛
  دو Bridge دقیقاً `Acc.TblCheque` و `Acc.TblBankOrders` را هدف می‌گیرند.
- Lineage متادیتایی ۸۹ مورد از ۹۷ ستون visible دو View را به ستون منبع رساند؛
  Parse درون‌حافظه‌ای برای هر هشت Alias/Expression باقیمانده Identifier candidate
  ساخت، اما Effect parity آن‌ها همچنان صفر است.
- سند: `TREASURY_EDIT_COMMAND_AND_VIEW_TRIGGER_BOUNDARY_20260827_FA.md`
- Artifactها: `varanegar_treasury_edit_command_paths_20260827.json` و
  `varanegar_treasury_edit_source_model_20260827.json`
- Artifact تکمیلی: `varanegar_treasury_trigger_semantics_20260827.json`
- Artifact Lineage: `varanegar_treasury_view_column_lineage_20260827.json`
- Artifact مقصد: `negin_erp_treasury_edit_target_contracts_20260827.json`
- Artifact قواعد: `varanegar_treasury_edit_validation_contracts_20260827.json`
- Artifact گراف: `varanegar_treasury_trigger_transitive_graph_20260827.json`
- Artifact فیلد وب: `varanegar_treasury_web_field_contract_candidates_20260827.json`
- Artifact برچسب UI: `varanegar_treasury_ui_label_candidates_20260827.json`
- Artifact Screen وب: `negin_erp_treasury_web_screen_contract_candidates_20260827.json`
- Extractor/Builder: `extract_varanegar_treasury_ui_label_candidates.py` و
  `build_negin_erp_treasury_web_screen_contract_candidates.py`

## ۲۰۲۶-۰۸-۲۷ — نامزدهای Field/Property به ستون SQL

- ۸۵ مورد از ۱۰۰ Property قوی حداقل یک ستون هم‌نام دارند؛ ۷۰ Field پوشش ستون
  و ۵۶ Field نامزد Entity/Object قوی‌تر دارند.
- ۲۸ Property call با Object دقیقاً هم‌نام Entity تطبیق یافت؛ بعد از حذف
  getter/setter تکراری، ۲۱ پیوند Field/Property/Object/Column باقی ماند.
- False positive تنظیم `NotInsertDuplicateRCashDraftNo` نشان داد این Anchorها
  Binding نیستند؛ Runtime/source-column proven همچنان صفر است.
- سند: `DATA_ENTRY_FIELD_SQL_COLUMN_CANDIDATES_20260827_FA.md`
- Artifact: `varanegar_data_entry_field_sql_columns_20260827.json`

## ۲۰۲۶-۰۸-۲۷ — نامزدهای Field به Property

- ۷۸ Field Match نامی قوی، ۳۱ Singleton method و ۱۷۳ Co-occurrence مبهم دارند؛
  ۵۳۱ Field Property candidate در IL منتخب ندارند.
- ۱۰۰ Property call یکتای قوی ثبت شد، اما Runtime binding و Source column/query
  parameter اثبات‌شده صفر باقی ماند.
- سند: `DATA_ENTRY_FIELD_BINDING_CANDIDATES_20260827_FA.md`
- Artifact: `varanegar_data_entry_field_binding_candidates_20260827.json`

## ۲۰۲۶-۰۸-۲۷ — حل نوع CLR فیلدها

- هر ۸۱۳ Field signature بدون Load کردن Assembly حل شد: ۸۰۵ TypeDef/TypeRef،
  پنج Primitive و سه Generic؛ ۵۳ CLR type یکتا و Failure صفر.
- ۵۹۲ Prefix با Type هم‌خوان بود و ۲۲۱ mismatch/unclassified ثابت کرد طراحی فرم
  مقصد نباید فقط از Prefix نام Legacy نتیجه‌گیری شود.
- Runtime visibility/enabled، Binding، Requiredness و Authorization همچنان صفر است.
- سند: `DATA_ENTRY_FIELD_TYPES_20260827_FA.md`
- Artifact: `varanegar_data_entry_field_types_20260827.json`

## ۲۰۲۶-۰۸-۲۷ — حل شکاف فیلد محلی با Base template

- هر ۴۶ فرم بدون Control field محلی از شش Base template مشترک ارث می‌برد؛ ۲۸
  مورد فقط از `FormBaseWithListDataEntry` هستند.
- Templateها ۴۳ Control field و ۲۶۳ Method body دارند؛ ۱۰۴ Method signal شامل
  ۴۶ Write/Delete و ۱۹ Validation/Guard است.
- این فرم‌ها Base-template-driven هستند، نه اثبات‌شده fieldless؛ Runtime binding
  و مجوز/Branch مؤثر همچنان صفر است.
- سند: `DATA_ENTRY_BASE_TEMPLATE_CONTRACTS_20260827_FA.md`
- Artifact: `varanegar_data_entry_base_template_contracts_20260827.json`

## ۲۰۲۶-۰۸-۲۷ — Field metadata مستقیم فرم‌های ورود داده

- هر ۱۴۱ Type از DLL Hash‌شده حل شد و ۸۱۳ Field candidate/۴۹۰ نام یکتا به دست آمد؛
  ۵۸۱ مورد Usage داشت و ۲۳۲ مورد فقط در Metadata اعلام شده بود.
- ۴۶ فرم Control field محلی ندارند و احتمال Base/inherited/dynamic باز است؛ نبود
  Field محلی به معنی نبود ورودی نیست.
- Runtime type، Binding و Requiredness اثبات‌شده همچنان صفر است.
- سند: `DATA_ENTRY_DECLARED_FIELDS_20260827_FA.md`
- Artifact: `varanegar_data_entry_declared_fields_20260827.json`

## ۲۰۲۶-۰۸-۲۷ — واژه‌نامه فیلد فرم‌های ورود داده

- برای ۱۴۱ فرم منتخب، ۵۸۱ Field candidate با ۳۵۰ نام یکتا استخراج شد؛ ۹۳ فرم
  پوشش نام کنترل دارند و ۴۸ فرم در این روش بدون Field candidate ماندند.
- ۱٬۵۹۴ Label امن حفظ شد ولی برای جلوگیری از ادعای نادرست، با Fieldها Pair نشد.
- Required/Nullable و Data binding اثبات‌شده صفر است؛ Runtime field contract و
  UAT هنوز Gate بعدی‌اند.
- سند: `DATA_ENTRY_FIELD_DICTIONARY_20260827_FA.md`
- Artifact: `varanegar_data_entry_field_dictionary_20260827.json`

## ۲۰۲۶-۰۸-۲۷ — سناریوهای UAT نقش و SoD

- برای ۱۵ Role template و ۴۵ Capability، تعداد ۱۸۴ Case مصنوعی ساخته شد:
  ۷۵ Allow، ۷۱ Deny، ۱۵ Context invalidation، ده SoD، نه Negative و چهار Non-inference.
- هیچ هویت یا Grant واقعی نتیجه‌گیری نشد؛ Owner-approved و Production assignment
  هر دو صفر و Gate تا Signoff/UAT احرازشده مسدود است.
- سند: `ROLE_UAT_CASES_20260827_FA.md`
- Artifact: `negin_erp_role_uat_cases_20260827.json`

## ۲۰۲۶-۰۸-۲۷ — ریسک مستقل برابری گزارش

- `R-031` ثبت شد: هیچ Method signal، نامزد نامی SQL یا Parameter/dependency footprint
  بدون Exact binding، Snapshot و Golden value مالک به Result parity تبدیل نمی‌شود.
- Risk register اکنون ۳۱ ریسک باز دارد: ۱۰ Critical، ۱۸ High و ۳ Medium؛
  Traceability شامل ۱۰۵ Assignment است و آمادگی Command/Pilot همچنان صفر است.

## ۲۰۲۶-۰۸-۲۷ — Binding جنریک و Anchorهای Dashboard/Cardex

- هشت Caller به پنج EntityHelper، پنج Handler و ۱۷ Filter member رسید؛ دو Chart
  `GetAllView` جنریک دارند و Selector موجودی فیلتر کامل CardexBatch را می‌سازد.
- پنج نامزد یکتای SQL پیدا شد: ReviewOrderPoints، SaleAmountPerInterval،
  TopDealerSales، SaleDashboard_GetList و UspRptCardexBatchNo6004.
- پنج Procedure مجموعاً ۳۲ Parameter و ۳۲ Dependency دارند. هیچ Durable mutation
  target حل نشد؛ Tokenهای Insert عمدتاً Temp هستند، اما Read-only و Result parity
  هنوز اثبات نشده‌اند و Result metadata هر پنج با خطای `SYNTAX` باز ماند.
- اسناد: `REPORT_GENERIC_BINDINGS_20260827_FA.md`، `REPORT_GENERIC_SQL_CANDIDATES_20260827_FA.md` و `REPORT_GENERIC_SQL_SEMANTICS_20260827_FA.md`

## ۲۰۲۶-۰۸-۲۷ — Caller و مرز Generic گزارش‌های Shell

- هفت Shell گزارش در تمام ۶۲ Assembly ردیابی شد؛ چهار مورد Entry-point استاتیک
  دارند: شش Chart برای Zoom و زنجیره Selector گزارش موجودی.
- هشت Caller type به شش Edge و پنج Business type رسید، اما `TypeSpecRow.GetAllView`
  و Generic dispatch مسیر دقیق DataAccess را در این عمق پنهان نگه داشتند.
- نبود DataAccess edge به معنی نبود Query نیست؛ Result parity و آمادگی Pilot صفر است.
- اسناد: `REPORT_SHELL_ENTRYPOINTS_20260827_FA.md` و `REPORT_SHELL_CALLER_PATHS_20260827_FA.md`
- Artifacts: `varanegar_report_shell_entrypoints_20260827.json` و `varanegar_report_shell_caller_paths_20260827.json`

## ۲۰۲۶-۰۸-۲۷ — مسیر متدی و دفتر شکاف گزارش‌ها

- ۲۰ Report تا ۴۷ DataAccess method انتهایی Trace شد؛ ۲۶ متد Execution signal
  و یک متد Mutation signal (`DataContext.Commit`) دارند.
- Commit از Print-completed و Statement save می‌آید و باید Command مستقل از
  Preview/Search/Export باقی بماند.
- Crosswalk شواهد: هفت Report در L0، سه L1، یک L2 و نه L3 هستند؛ برای هر ۲۰
  Report، SQL identity/parameter binding، Effective scope، Golden value و Result parity باز است.
- اسناد: `REPORT_METHOD_PATHS_20260827_FA.md` و `REPORT_EVIDENCE_GAPS_20260827_FA.md`
- Artifacts: `varanegar_report_method_paths_20260827.json` و `varanegar_report_evidence_gaps_20260827.json`

## ۲۰۲۶-۰۸-۲۷ — نامزدهای SQL گزارش‌ها

- ۴۰ DataAccess type/member term در Clone فقط‌خواندنی به ۵۱۸ Object نامزد رسید؛
  ۲۲ Term و ۱۱ Report Candidate دارند، ولی ده Term در سقف ۴۰ بریده شدند.
- Termهای `CallCenterProductCustomerReport/ProductQtyReport/PrintInvoice/TRSReport22/23`
  Name match ندارند؛ Name match/absence هیچ‌کدام Execution یا Result parity را ثابت نمی‌کند.
- سند: `docs/varanegar_reconstruction/REPORT_SQL_CANDIDATES_20260827_FA.md`
- Artifact: `artifacts/varanegar_analysis/ui/varanegar_report_sql_candidates_20260827.json`
- Extractor: `scripts/sql/extract_varanegar_report_sql_candidates.py`

## ۲۰۲۶-۰۸-۲۷ — گراف وابستگی گزارش‌ها

- ۲۰ Report به ۶۷۴ Edge UI، ۲۵ Business type و ۲۷ DataAccess type Trace شد؛
  ۱۳ Report مسیر Business→DataAccess و چهار Report Coupling مستقیم UI→DataAccess دارند.
- پنج Shell/Selector در عمق یک‌مرحله‌ای DataAccess نشان ندادند؛ این Static absence
  دلیل نبود Query نیست و Result parity هر ۲۰ Report همچنان صفر است.
- سند: `docs/varanegar_reconstruction/REPORT_DEPENDENCY_GRAPH_20260827_FA.md`
- Artifact: `artifacts/varanegar_analysis/ui/varanegar_report_dependency_graph_20260827.json`
- Extractor: `scripts/windows/extract_varanegar_report_dependency_graph.py`

## ۲۰۲۶-۰۸-۲۷ — قرارداد و Golden case گزارش‌ها

- برای ۲۰ سطح گزارش، ۲۰ Query contract، سه Export، سه Print-completion command
  و دو Statement command طراحی شد.
- ۱۷۵ Golden case مصنوعی Scope/Pagination/Freshness/Privacy/Export/Print/Write
  ساخته شد؛ اجرای Legacy و Result parity همچنان صفر است.
- سند: `docs/varanegar_reconstruction/REPORT_TARGET_CONTRACTS_AND_GOLDEN_CASES_20260827_FA.md`
- Artifact: `artifacts/varanegar_analysis/ui/varanegar_report_target_contracts_golden_cases_20260827.json`
- Builder: `scripts/windows/build_varanegar_report_target_contracts_and_golden_cases.py`

## ۲۰۲۶-۰۸-۲۷ — اطلس فرایندهای انتها‌به‌انتها

- ده فرایند مقصد تعریف و هر ۲۰ Workflow، ۲۰ Report و سه State machine پوشش داده شد.
- هر فرایند به Golden case و Riskهای ماژول‌های درگیر وصل شد؛ هیچ فرایند به‌اشتباه
  Implementation/Pilot/Production-ready اعلام نشده است.
- سند: `docs/varanegar_reconstruction/END_TO_END_PROCESS_ATLAS_20260827_FA.md`
- Artifact: `artifacts/varanegar_analysis/ui/negin_erp_end_to_end_process_atlas_20260827.json`
- Builder: `scripts/windows/build_negin_erp_end_to_end_process_atlas.py`

## ۲۰۲۶-۰۸-۲۷ — Checkpoint UI ساعت ۰۳:۰۰

- Snapshot تازه‌ی Process باز روی `192.168.1.184` بدون هیچ UI action گرفته شد.
- هر شش بخش Semantic با Baseline برابر بود: یک پنجره، ۷۶ Control، ۱۸ Label امن،
  ۸۵ Child window و ۱۹ Win32 title امن؛ `NO_SEMANTIC_UI_DRIFT`.
- سند: `docs/varanegar_reconstruction/UI_CHECKPOINT_0300_20260827_FA.md`
- Artifacts: `artifacts/varanegar_analysis/ui/varanegar_ui_checkpoint_20260827_0300.json` و
  `artifacts/varanegar_analysis/ui/varanegar_ui_checkpoint_comparison_20260827_0300.json`

## ۲۰۲۶-۰۸-۲۷ — ورودی تصمیم Stack و Recovery

- Repository فعلی ۵۷ فایل Python برنامه، ۲۱ Route module و ۴۳ ماژول تست دارد؛
  FastAPI/SQL adapters/PWA/Caddy ظرفیت قابل‌استفاده‌اند.
- پیشنهاد موقت Modular Monolith با Backend موجود و Web TypeScript component-based
  است؛ Database مقصد و Hosting هنوز تصمیم کاربر است و SQLite برای ERP مالی
  چندکاربره رد شده است.
- Tier پیشنهادی Recovery برابر RPO حداکثر ۵ دقیقه و RTO حداکثر ۶۰ دقیقه است،
  ولی تا تأیید هزینه/مالک پشتیبانی الزام مصوب نیست.
- سند: `docs/varanegar_reconstruction/STACK_AND_RECOVERY_DECISION_INPUT_20260827_FA.md`
- Artifact: `artifacts/varanegar_analysis/ui/negin_erp_stack_recovery_decision_input_20260827.json`
- Builder: `scripts/windows/build_negin_erp_stack_and_recovery_decision_input.py`

## ۲۰۲۶-۰۸-۲۷ — مدل منبع POS و محدودیت داده‌ی Clone

- ۱۳ جدول POS دارای ۳۰۹ ستون، ۱۷ کلید، ۸۹ FK و ۵۱ Trigger فعال‌اند؛ ۶۱ FK
  `not trusted` است و هیچ signal آشکار Version/Rowversion وجود ندارد.
- ۱۲ جدول POS در Clone صفر ردیف‌اند و فقط `Safe` دارای ۳۰ ردیف است؛ بنابراین
  Schema قابل استناد است ولی رفتار و حجم عملیاتی POS از Clone قابل نتیجه‌گیری نیست.
- Snapshot مقصد باید Watermark، Payload hash، Crosswalk، کنترل Count/Amount و
  Quarantine orphanها را نگه دارد و هیچ ACK به وارانگار ننویسد.
- سند: `docs/varanegar_reconstruction/POS_SOURCE_MODEL_AND_SNAPSHOT_BOUNDARY_20260827_FA.md`
- Artifact: `artifacts/varanegar_analysis/ui/varanegar_pos_source_model_20260827.json`
- Extractor: `scripts/sql/extract_varanegar_pos_source_model.py`

## ۲۰۲۶-۰۸-۲۷ — ماتریس ردیابی ERP مقصد

- هر ۱۴ ماژول به Evidence count، Golden case، ریسک باز، P0 مستقیم و Blocker وصل شد.
- ۶۲۱ Golden case، ۳۱ ریسک با ۱۰۵ Assignment، ۲۶ آیتم P0 و ۱۴ بلوک فعالیت
  سه‌ماهه بدون مورد گمشده ردیابی شدند؛ ۹ ماژول شاهد فعالیت مستقیم دارند، اما
  همچنان صفر ماژول Command/Pilot/Production-ready است.
- Artifact: `artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260827.json`
- سند: `docs/varanegar_reconstruction/REQUIREMENTS_TRACEABILITY_MATRIX_20260827_FA.md`
- Builder: `scripts/windows/build_negin_erp_requirements_traceability.py`

## ۲۰۲۶-۰۸-۲۷ — گراف گذرای Replication رسید POS

- ریشه‌ی Runtime اثبات‌شده‌ی `dbo.usp_ReplicateSalesReceipt` در Clone فقط‌خواندنی
  تا عمق سه پیمایش شد؛ خروجی در سقف ۵۰۰ Node و با ۱۶۰ Module بازنشده متوقف شد.
- در همین محدوده ۱٬۰۳۹ Edge، ۳۶۲ Trigger، ۸۲ Table، ۴۰۰ Mutation token و ۴۸
  Write target حل‌شده مشاهده شد؛ پس پورت مستقیم Procedure برای ERP مقصد ممنوع
  می‌ماند و Batch/Reconciliation مرز درست است.
- هیچ Module اجرا نشد و Definition، Literal یا مقدار کسب‌وکاری ذخیره نشد.
- سند: `docs/varanegar_reconstruction/POS_RECEIPT_TRANSITIVE_SQL_GRAPH_20260827_FA.md`
- Artifact: `artifacts/varanegar_analysis/ui/varanegar_pos_replication_transitive_graph_20260827.json`
- Extractor: `scripts/sql/extract_varanegar_pos_replication_transitive_graph.py`

## ۲۰۲۶-۰۸-۲۷ — قرارداد Batch رسید POS مقصد

وضعیت: **۹ State، ۱۰ Transition، شش Effect boundary و نه Reconciliation check**

منابع:

- `scripts/windows/build_negin_erp_pos_receipt_replication_contract.py`
- `artifacts/varanegar_analysis/ui/negin_erp_pos_receipt_replication_contract_20260827.json`
- `docs/varanegar_reconstruction/POS_RECEIPT_REPLICATION_CONTRACT_20260827_FA.md`

کشفیات کلیدی:

1. Receipt replication به Batch و Item state machine قابل Resume شکسته شد؛
   `BLOCKING_UNKNOWN` تا شاهد تازه اجازه Acceptance ندارد.
2. Idempotency هر Receipt با Source/session/receipt/version و Payload hash تعریف
   شد و شش اثر Sales/Return/Payment/Inventory/Credit/Session مالک جدا گرفت.
3. نه Check تعداد/مبلغ/Crosswalk/Ledger/Delivery/Quarantine همگی Blocking هستند.
4. ۲۰ Golden case Command به Gate متصل شد، ولی هنوز Spec است و اجرا نشده است.
5. ACK فقط Target-local است؛ هیچ Write-back یا Status update در وارانگار مجاز
   نشد.

مرحله بعدی:

- طراحی Migration/read-model Slice برای Session/Receipt source snapshot؛
- استخراج Field/cardinality دقیق `usp_ReplicateSalesReceipt` بدون مقدار تجاری.

## ۲۰۲۶-۰۸-۲۷ — دو ریسک افزوده‌شده از Deep trace

وضعیت: **۲۸ ریسک؛ ۱۰ Critical، ۱۵ High، ۳ Medium؛ Validation برابر PASS**

کشفیات کلیدی:

1. `R-027` پورت Receipt replication با ۶۶ Dependency و ۱۷ Mutation candidate را
   تا اثبات Batch idempotency، per-item quarantine و reconciliation بحرانی نگه
   می‌دارد.
2. `R-028` کپی `MAX(Id)+1` در LinearDiscount را تا جایگزینی با allocator اتمیک،
   Unique constraint و تست parallel writer High نگه می‌دارد.
3. هر ۲۸ ریسک Open است؛ این به‌روزرسانی Risk acceptance یا مجوز Production نیست.

## ۲۰۲۶-۰۸-۲۷ — Semantic footprint هشت Procedure حساس

وضعیت: **هشت Module، ۳۱ Operation و Validation برابر PASS**

منابع:

- `scripts/sql/extract_varanegar_extension_sql_semantics.py`
- `artifacts/varanegar_analysis/ui/varanegar_extension_sql_semantics_20260827.json`
- `docs/varanegar_reconstruction/EXTENSION_SQL_SEMANTICS_20260827_FA.md`

کشفیات کلیدی:

1. `usp_ReplicateSalesReceipt` با ۶۶ Dependency، ۱۷ Mutation candidate، چهار
   Cursor و ۲۶ EXEC token یک Orchestrator چنددامنه‌ای است، نه CRUD Session.
2. Targetهای حل‌شده آن Payment، Order/Return crosswalk، Inventory voucher،
   Session، Payment relation و Credit را همزمان درگیر می‌کنند.
3. پنج Procedure Transaction envelope صریح دارند، اما فقط Replication Procedure
   Error propagation صریح شناسایی‌شده دارد؛ Atomicity سرتاسری هنوز اثبات نشده است.
4. ConfirmBaseChargeDevice هم `BaseChargeDevice` و هم `PSession` را Update می‌کند؛
   Device/Session invariant باید یک Gate مستقل باشد.
5. Definition/String/Business row ذخیره نشد و هیچ Module اجرا نشد.

مرحله بعدی:

- افزودن ریسک ویژه POS receipt replication و `MAX(Id)+1` به Risk register؛
- طراحی Batch/crosswalk/reconciliation contract برای انتقال POS.

## ۲۰۲۶-۰۸-۲۷ — SQL Anchor contract افزونه‌ها

وضعیت: **۴۸ Anchor، ۱۲ Capability و Validation برابر PASS**

منابع:

- `scripts/windows/build_varanegar_extension_sql_anchor_contracts.py`
- `artifacts/varanegar_analysis/ui/varanegar_extension_sql_anchor_contracts_20260827.json`
- `docs/varanegar_reconstruction/EXTENSION_SQL_ANCHOR_CONTRACTS_20260827_FA.md`

کشفیات کلیدی:

1. ۱۷ Table، ۳۰ Stored procedure و یک View به‌عنوان Anchor منتخب باقی ماند؛ ۸۴
   Candidate دیگر برای Contract اصلی لازم نبودند اما در Catalog حفظ شدند.
2. ۲۶۶ Column، ۱۵۰ Parameter، ۵۱ FK، ۳۲ Trigger و ۲۰۷ Dependency ثبت شد.
3. فقط `dbo.POSLineDiscount` و `dbo.usp_ReplicateSalesReceipt` Link مستقیم نام
   SQL در IL دارند؛ ۴۶ Anchor دیگر Candidate هستند و این محدودیت صریح ماند.
4. هر ۱۲ Capability Gate پیاده‌سازی جدا دارد؛ PASS شدن Artifact اجازه Migration،
   Command یا Pilot نیست.

مرحله بعدی:

- استخراج Replication procedure semantic footprint بدون اجرای آن؛
- تعیین Schema مقصد و Crosswalk برای نخستین Slice فقط‌خواندنی بعد از انتخاب Stack.

## ۲۰۲۶-۰۸-۲۷ — حل Gap عمیق و اصلاح قرارداد POSSession

وضعیت: **سه Gap حل شد؛ یک Command تازه و Validation برابر PASS**

منابع:

- `scripts/windows/extract_varanegar_extension_gap_paths.py`
- `artifacts/varanegar_analysis/ui/varanegar_extension_gap_paths_20260827.json`
- `docs/varanegar_reconstruction/EXTENSION_GAP_PATHS_20260827_FA.md`

کشفیات کلیدی:

1. `POSSessionHandler.Send → POSSessionAdapter.Send → usp_ReplicateSalesReceipt`
   با `ExecuteNonQuery` و Transaction Start/Commit/RollBack پیدا شد؛ فرض Query-only
   قبلی رد و Command مستقل Replication رسید اضافه شد.
2. `LinearDiscountAdapter.GenerateLinearDiscountId` به `dbo.POSLineDiscount`
   وصل است و `MAX(Id)+1` دارد؛ مقصد باید Sequence/Identity/UUID و Unique constraint
   داشته باشد.
3. `FormEditDealerDayPath.SaveCommand` و Fieldهای ActiveDate/Dealer/VisitPath و
   Detail Product/Order پیدا شد؛ سه Procedure Save/List نامزد Clone نیز کشف شد.
4. اسکن هفت Assembly شامل ۱۶ Type، ۵۵ Method، ۴۵۴ Call و صفر خطا/Hash mismatch
   بود؛ هیچ Assembly یا Command اجرا نشد.
5. قرارداد مقصد اکنون ۱۱ Command و دو Query و Golden bundle اکنون ۲۱۵ Case دارد.

مرحله بعدی:

- تثبیت Procedure/Column contract سه مسیر تازه؛
- بررسی Replication semantics و Failure boundary رسیدهای POS.

## ۲۰۲۶-۰۸-۲۷ — مرز DataAccess و Candidateهای SQL Extension

وضعیت: **شش Direct UI→DA، ۱۳۲ Catalog candidate و Validation برابر PASS**

منابع:

- `scripts/sql/extract_varanegar_extension_sql_surface.py`
- `scripts/windows/build_varanegar_extension_data_boundary_assessment.py`
- `artifacts/varanegar_analysis/ui/varanegar_extension_sql_surface_20260827.json`
- `artifacts/varanegar_analysis/ui/varanegar_extension_data_boundary_assessment_20260827.json`
- `docs/varanegar_reconstruction/EXTENSION_SQL_AND_DATA_BOUNDARIES_20260827_FA.md`

کشفیات کلیدی:

1. ArticleTemplate و GeneralConfig در UI `DataContext.Commit` صریح دارند؛ Web
   config و POSSession lifecycle Context را در UI می‌سازند و POS Charge/Safe
   Lookup مستقیم DataAccess دارند.
2. Clone با READ_ONLY، `can_update=0` و `db_denydatawriter=1` کنترل شد؛ فقط
   Catalog metadata خوانده شد و Procedure/Trigger یا Business-row اجرا/خوانده نشد.
3. هر ۱۲ Capability Candidate دارد؛ ۱۳۲ Object شامل ۲۸ Table و ۱۰۴ Module با
   Search termهای مبتنی بر IL ثبت شد.
4. `GNR.tblGeneralConfig` با ۱۷۷ ردیف Metadata و History با ۸٬۷۸۲ ردیف، جدایی
   Current/History را تأیید می‌کنند؛ این شمارش Snapshot زنده نیست.
5. `dbo.ArticleTemplate` و `dbo.BaseChargeDevice` در Clone شمارش صفر دارند؛ این
   نباید به حذف Scope یا «عدم استفاده Operational» تعبیر شود.

مرحله بعدی:

- Trace Adapter/ORM تا SQL برای سه Gap و Candidateهای Command حساس؛
- استخراج Contract دقیق Column/Trigger/Procedure فقط برای Anchorهای منتخب.

## ۲۰۲۶-۰۸-۲۷ — Golden caseهای Extension مقصد

وضعیت: **۲۱۵ Case، سیزده Surface و Validation برابر PASS**

منابع:

- `scripts/windows/build_varanegar_extension_golden_cases.py`
- `artifacts/varanegar_analysis/ui/varanegar_extension_golden_cases_20260827.json`
- `docs/varanegar_reconstruction/EXTENSION_GOLDEN_CASES_20260827_FA.md`

کشفیات کلیدی:

1. یازده Command با Auth/Scope/Concurrency/Idempotency، ۴۶ Invariant، ۴۴ Failure
   stage و ۴۵ Reconciliation check پوشش داده شد.
2. هر Query صندوق/نشست POS Case مستقل No-mutation، Pagination، Cutoff و Privacy
   دارد؛ Status projection با Command تسویه یکی گرفته نشد.
3. همه ۱۹۵ Case فقط برای Test harness مقصد هستند و اجازه اجرای Legacy صفر است.
4. Caseهای Crash، پذیرفته‌شدن نتیجه جزئی و Dual write بدون همگرایی Retry را رد
   می‌کنند.

مرحله بعدی:

- Trace DataAccess/SQL چهار Command دارای Direct UI→DA؛
- تبدیل Caseها به تست executable پس از انتخاب Stack و ساخت Skeleton مقصد.

## ۲۰۲۶-۰۸-۲۷ — قرارداد Command/Query Extensionهای مادی

وضعیت: **۱۱ Command، دو Query و Validation برابر PASS**

منابع:

- `scripts/windows/build_varanegar_extension_target_contracts.py`
- `artifacts/varanegar_analysis/ui/varanegar_extension_target_contracts_20260827.json`
- `docs/varanegar_reconstruction/EXTENSION_TARGET_CONTRACTS_20260827_FA.md`

کشفیات کلیدی:

1. ده Capability دارای ۵۵ Method فرمانی UI و POSSession دارای Deep mutation
   evidence به یازده Command مقصد نگاشت شد؛ هیچ فرمان Legacy یا مقصد اجرا نشد.
2. `pos.safe` فقط Query ماند؛ POSSession هم Query scoped و هم Command مستقل
   Replication رسید دارد.
3. پنج Command از سطح Legacy دارای Direct UI→DA آمده‌اند؛ مقصد برای همه آن‌ها
   Application service، Atomic append/pointer/outbox و Idempotency اجباری دارد.
4. General config از Web-service config و Secret boundary جدا شد؛ Secret فقط
   با Vault handle و بدون Log/Artifact/Result مجاز است.
5. Authorization scope matrix، Route planning، Visit template و Pricing rule
   همگی Versioned/Immutable تعریف شدند و Delete به Retirement جدا تبدیل شد.

مرحله بعدی:

- ساخت Golden cases مصنوعی برای ده Command و دو Query؛
- Trace لایه DataAccess/SQL برای چهار Command دارای Direct UI→DA.

## ۲۰۲۶-۰۸-۲۷ — مسیر Command/Guard Extensionهای مادی

وضعیت: **۱۲ Capability، ۲۱۶ UI path، ۸۹ Business method و Validation برابر PASS**

منابع:

- `scripts/windows/extract_varanegar_extension_command_paths.py`
- `artifacts/varanegar_analysis/ui/varanegar_extension_command_paths_20260827.json`
- `docs/varanegar_reconstruction/EXTENSION_COMMAND_PATHS_20260827_FA.md`

کشفیات کلیدی:

1. ۵۵ Command candidate، ۴۹ Guard و ۱۱۲ Query/Event/Context path از ۲۶۵ Method
   UI استخراج شد.
2. ۹۰ UI→Business، ۲۶ Direct UI→DA و ۱۰۵ Business→DA Edge یکتا ثبت شد.
3. Stock accounting access با ۳۱ مسیر و ۱۶ Permission guard، Authorization و
   Config و Inventory/Accounting را Couple می‌کند.
4. POS Charge device بیشترین Direct-DA occurrence را در انتخاب مادی دارد؛
   General/WebService config و Article template نیز Direct DA دارند.
5. Transaction signal صریح در UI/Business method مستقیم صفر است؛ Atomicity رد
   یا اثبات نشد و Target transaction/fault tests اجباری ماند.

مرحله بعدی:

- Command/query contract و Golden cases Extensionها؛
- Trace DataAccess/SQL برای Commandهای نهایی منتخب.

## ۲۰۲۶-۰۸-۲۷ — Dependency graph بسته‌های Extension

وضعیت: **۳۲ Capability؛ ۱۴۹ UI→Business، ۴۲ UI→DataAccess، ۱۸۴ Business→DA**

منابع:

- `scripts/windows/extract_varanegar_extension_dependency_graph.py`
- `artifacts/varanegar_analysis/ui/varanegar_extension_dependency_graph_20260827.json`
- `docs/varanegar_reconstruction/EXTENSION_DEPENDENCY_GRAPH_20260827_FA.md`

کشفیات کلیدی:

1. ۳۱ Capability Business mediation دارند، اما ۱۳ مورد هم DataAccess مستقیم از
   UI دارند؛ Legacy لایه‌بندی پاک ندارد.
2. POS Charge/Safe/Session/Setting/Scale/Instalment/Barcode/SubscriberGroup، سه
   Setting، Report selector و Contact selector Coupling مستقیم دارند.
3. ۷۳ Type Business و ۵۸ Type DataAccess کامل پیدا شد؛ ۱٬۰۹۹ Method body و صفر
   خطا/Hash mismatch ثبت شد.
4. Contact selector تنها Capability بدون Business mediation صریح است.
5. Target Web UI نباید Legacy Adapter/QueryHelper را کپی کند؛ Application
   Command/Query و Server-side Scope الزامی است.

مرحله بعدی:

- Trace Method/SQL Couplingهای مادی POS/Setting؛
- قرارداد Command/Query Extensionهای اولویت‌بالا.

## ۲۰۲۶-۰۸-۲۷ — Capability map بسته‌های Extension

وضعیت: **۳۲ Capability، ۳۳ Route، ۱٬۸۲۸ Call و Validation برابر PASS**

منابع:

- `scripts/windows/build_varanegar_extension_capability_map.py`
- `artifacts/varanegar_analysis/ui/varanegar_extension_capability_map_20260827.json`
- `docs/varanegar_reconstruction/EXTENSION_CAPABILITY_MAP_20260827_FA.md`

کشفیات کلیدی:

1. ۱۳ POS، ۹ Tablet، ۸ Setting و دو Selector به Capability hint مقصد نگاشت شد.
2. ۲۶ Capability Write-like، ۱۳ Delete/Reverse-like، ۲۰ Validation-like و ۱۳
   Permission-like است؛ این نام‌ها اثر/مجوز واقعی را ثابت نمی‌کنند.
3. POS به Sales/Pricing/Master/Treasury/Config/Integration وصل است و نباید یک
   Aggregate واحد شود.
4. Tablet هم Master projection و هم Visit planning/path دارد؛ Sync endpoint
   تنها، قرارداد کافی نیست.
5. Setting میان Permission، Final dates، General config، Web service و Article
   template Coupling دارد و باید در مقصد به Policy/Secret/Auth/Accounting جدا شود.

مرحله بعدی:

- Dependency/call-family map برای ۳۲ Capability؛
- قرارداد Command اولویت‌بالا برای POS/Tablet/Setting.

## ۲۰۲۶-۰۸-۲۷ — Resolution Typeهای خارج از Core

وضعیت: **۳۳ از ۳۴ Route حل شد؛ ۳۲ Type، پنج Assembly و ۶۰۷ Method body**

منابع:

- `scripts/windows/extract_varanegar_present_package_route_types.py`
- `artifacts/varanegar_analysis/ui/varanegar_present_package_route_types_20260827.json`
- `docs/varanegar_reconstruction/EXTENDED_ROUTE_TYPE_RESOLUTION_20260827_FA.md`

کشفیات کلیدی:

1. ۱۳ POS، ۹ Tablet، ۸ Setting، دو Route Report روی یک Type و یک VNMembers
   شکاف Present-package کاتالوگ Core را توضیح دادند.
2. ۳۲ Type متمایز و ۶۰۷ Method body بدون خطا/Hash mismatch خوانده شد؛ ۲۶
   Write-like و ۱۳ Permission-like فقط Heuristic هستند.
3. POS شامل Safe/Session/Discount/Subscriber/Instalment/Barcode/Scale است و
   Tablet شامل Catalog/Visit plan/path/dealer/product/customer است؛ Scope آن‌ها
   بزرگ‌تر از یک صفحه یا Sync endpoint ساده است.
4. Setting میان General config، Stock access، User setting، Final dates، Web
   service و Article template Coupling دارد که در مقصد باید جدا شود.
5. Menu `20037` با Class/File ناسازگار تنها Route حل‌نشده است و خودکار Retire
   نمی‌شود.

مرحله بعدی:

- Capability map برای ۳۲ Type Extension؛
- Deployment/owner evidence برای Route `20037`.

## ۲۰۲۶-۰۸-۲۷ — Scope freeze Routeهای تطبیق‌نشده

وضعیت: **۲۳۹ Candidate؛ ۷۶ High، ۱۰۵ Medium، ۵۸ Low؛ Auto-retire صفر**

منابع:

- `scripts/windows/build_varanegar_scope_freeze_catalog.py`
- `artifacts/varanegar_analysis/ui/varanegar_scope_freeze_catalog_20260827.json`
- `docs/varanegar_reconstruction/SCOPE_FREEZE_CATALOG_20260827_FA.md`

کشفیات کلیدی:

1. ۶۱ Shell و ۱۷۸ Leaf تطبیق‌نشده برای Scope decision جدا شد؛ همه AccessNode
   دارند ولی این مجوز مؤثر یا Usage نیست.
2. ۷۶ High شامل ۳۳ Present-package، ۴۰ External/absent و سه Redacted دارای
   Signal مادی Visibility/Action است.
3. ۱۰۵ Medium و ۵۸ Low فقط ترتیب Review را تعیین می‌کنند؛ هیچ Candidate خودکار
   Retire/Retain/Implement نشد.
4. ۸۵ Candidate Container-visible و ۱۲۸ Candidate دارای Signal مادی‌اند؛
   Confirm/Notify صفر و Action menu سه است.
5. Sales/Integration/Procurement/Treasury/Reporting بیشترین Assignment را دارند؛
   Root hint مالکیت نهایی Aggregate نیست.

مرحله بعدی:

- Trace ۷۶ High با TypeDef/Deployment manifest/Owner evidence؛
- اتصال Scope disposition به Risk و Traceability matrix.

## ۲۰۲۶-۰۸-۲۷ — نقشهٔ Navigation به ماژول مقصد

وضعیت: **۸۳۶ Route، ۳۱ Root، عمق ۴، Cycle/Orphan صفر و Validation برابر PASS**

منابع:

- `scripts/windows/build_varanegar_navigation_module_map.py`
- `artifacts/varanegar_analysis/ui/varanegar_navigation_module_map_20260827.json`
- `docs/varanegar_reconstruction/NAVIGATION_MODULE_MAP_20260827_FA.md`

کشفیات کلیدی:

1. Sales با ۱۷۸، Treasury با ۱۴۳، BaseData2 با ۵۷، Inventory با ۵۵ و Settings
   با ۵۰ Route بزرگ‌ترین بخش‌های Navigation هستند.
2. ۴۳۷ ردیف Navigation-only و ۱۶۰ فرم Runtime-matched است؛ ۶۱ Shell و ۱۷۸
   Leaf/Target تطبیق‌نشده جدا شدند.
3. از Targetهای تطبیق‌نشده، ۳۴ به Package حاضر، ۱۰۴ به External/absent hint،
   ۳۷ به Null/placeholder و سه مورد به Target redacted تعلق دارند.
4. ۱۲۶ Form route تطبیق‌شده Primary domain دارد؛ Root hint و Domain hint جدا
   ماند تا Navigation grouping با Aggregate ownership اشتباه نشود.
5. منوی ثابت حقوق مؤثر هیچ کاربری نیست و Visibility اجازهٔ Command ایجاد نمی‌کند.

مرحله بعدی:

- Scope-freeze catalog برای ۱۷۸ Shell/Leaf تطبیق‌نشده؛
- Traceability Requirement/Evidence/Backlog/Test/Risk.

## ۲۰۲۶-۰۸-۲۷ — دفتر ریسک مقصد

وضعیت: **۲۸ ریسک؛ ۱۰ Critical، ۱۵ High، ۳ Medium؛ هر چهارده ماژول پوشش دارد**

منابع:

- `scripts/windows/build_negin_erp_risk_register.py`
- `artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260827.json`
- `docs/varanegar_reconstruction/RISK_REGISTER_20260827_FA.md`

کشفیات و تصمیم‌ها:

1. Write به Source، Grant هویتی حدسی، PII/Secret leak، CRUD bypass، Retry duplicate،
   Partial commit، Ledger conflation، Restore اثبات‌نشده و قبول Unknown نه ریسک
   بحرانی‌اند.
2. شش کلاس ناهنجاری Aggregate به Risk/Control/Exit criterion متصل شد؛ هیچ Repair
   یا Normalize خودکاری مجاز نیست.
3. Drift، Clone staleness، Session bias و سه Root حل‌نشده به‌عنوان ریسک شناخت
   حفظ شدند؛ Static absence نتیجهٔ حذف نیست.
4. Severity اثر است نه احتمال؛ Likelihood ساختگی از Static evidence تولید نشد.
5. هر ۲۸ ریسک Open است و این Artifact هیچ Risk acceptance یا مجوز Production
   صادر نمی‌کند.

مرحله بعدی:

- Traceability الزام→شاهد→Backlog→Test→Risk؛
- Checkpoint ایمنی و Drift بعدی بدون تعامل عملیاتی.

## ۲۰۲۶-۰۸-۲۷ — ماتریس شناخت و آمادگی ماژول‌ها

وضعیت: **۱۴ ماژول؛ ۹ ماژول با شاهد چندمنبعی قابل‌توجه؛ صفر Command-ready**

منابع:

- `scripts/windows/build_negin_erp_module_readiness_matrix.py`
- `artifacts/varanegar_analysis/ui/negin_erp_module_readiness_matrix_20260827.json`
- `docs/varanegar_reconstruction/MODULE_READINESS_MATRIX_20260827_FA.md`

کشفیات کلیدی:

1. هر ۱۸ دامنه معتبر به چهارده مرز مقصد نگاشت شد؛ ۳۷۹ از ۴۴۵ فرم Primary domain
   دارند و ۶۶ فرم همچنان Unmapped است.
2. نه ماژول Configuration/Master/Pricing/Sales/Inventory/Distribution/
   Receivables/Procurement/Accounting شاهد هم‌زمان داده و UI و حداقل یک شاهد رفتاری دارند.
3. پنج Foundation module فقط برای P0 refinement و Master/Reporting فقط برای
   P1 read-only refinement آماده‌اند؛ هفت ماژول عملیاتی طراحی/تست مصنوعی‌اند.
4. هر ۶۲۱ Golden case به مالک ماژولی نگاشت شد، اما هیچ Target runtime یا UAT
   وجود ندارد؛ Command/Pilot/Production-ready برای همه صفر است.
5. هفت Gap High و سه Root حل‌نشده در ماژول‌های مقصد حفظ شد و با نبود Static
   evidence حذف نشد.

مرحله بعدی:

- ساخت Risk register با Severity/Owner/Evidence/Exit criterion؛
- ادامه مشاهدهٔ فقط‌خواندنی و Checkpoint نهایی تا ساعت ۰۹:۰۰.

## ۲۰۲۶-۰۸-۲۷ — Backlog اجرایی P0 مقصد

وضعیت: **۲۶ آیتم، ۱۳ Workstream، ۵۱ Dependency edge و Validation برابر PASS**

منابع:

- `scripts/windows/build_negin_erp_p0_backlog.py`
- `artifacts/varanegar_analysis/ui/negin_erp_p0_backlog_20260827.json`
- `docs/varanegar_reconstruction/P0_IMPLEMENTATION_BACKLOG_20260827_FA.md`

کشفیات و تصمیم‌ها:

1. P0 با Stack ADR و محیط هدف جدا شروع می‌شود، نه CRUD یا کپی Schema وارانگار.
2. Context/Auth/Scope/Audit قبل از هر Query یا Command کسب‌وکاری اجباری است.
3. Snapshot/Provenance/Crosswalk/Quarantine/Reconciliation یک زنجیرهٔ وابسته‌اند؛
   Source write-back و Repair خاموش ممنوع است.
4. ۶۲۱ Golden case فقط در Target test DB مصنوعی اجرا می‌شوند و Varanegar/Clone
   محیط اجرای Case نیستند.
5. انتخاب Stack و RPO/RTO تصمیم کاربر است؛ سه Root حل‌نشده نیز شاهد مالک
   کسب‌وکار می‌خواهند. زمان ۲–۳ هفتهٔ Blueprint Effort تک‌نفره نیست.

مرحله بعدی:

- ساخت ماتریس Confidence/Readiness چهارده ماژول مقصد؛
- پس از پایان بازهٔ تحلیل، انتخاب Stack و شروع P0-002..P0-004.

## ۲۰۲۶-۰۸-۲۷ — حل شکاف هفت فرم اولویت‌بالا

وضعیت: **۴ Child surface تأییدشده؛ ۳ Root entrypoint حل‌نشده**

منابع:

- `scripts/sql/extract_varanegar_priority_gap_routes.py`
- `scripts/windows/extract_varanegar_priority_gap_call_graph.py`
- `artifacts/varanegar_analysis/ui/varanegar_priority_gap_routes_20260827.json`
- `artifacts/varanegar_analysis/ui/varanegar_priority_gap_call_graph_20260827.json`
- `docs/varanegar_reconstruction/PRIORITY_FORM_GAP_RESOLUTION_20260827_FA.md`

کشفیات کلیدی:

1. هیچ‌یک از هفت فرم در FormInfo/Menu/AccessNode ثابت Clone Route ندارد؛ نبود
   Route به‌تنهایی فرم مرده را ثابت نمی‌کند.
2. با معیار سخت `ctor` از Type متفاوت، BankReconciliation، frmChek، frmList و
   Reconciliation پنجرهٔ فرعی والدهای مشخص‌اند.
3. BankReconciliationList، ReconciliationSetup و SpecialOptionsDistrict پس از
   اسکن هر ۶۲ فایل .NET، ۷٬۶۵۰ Type و ۸۱٬۴۷۳ Method body هم Entrypoint بیرونی
   نداشتند؛ هنوز مرده اعلام نمی‌شوند و شاهد Runtime/مالک کسب‌وکار لازم است.
4. ۱۸ Type دادهٔ خزانه‌داری کامل پیدا شد؛ `PdtReport` با Namespace لایهٔ داده
   داخل DLL فرم‌هاست و ناسازگاری Namespace/Deployment باید در مقصد اصلاح شود.
5. ۲۰ Launcher edge معتبر، صفر Hash mismatch و صفر خطای غیرمنتظره ثبت شد؛ دو
   خطای Designer شناخته‌شده و نامرتبط به‌عنوان Blind spot حفظ شد. هیچ DLL اجرا
   و هیچ Command عملیاتی فراخوانی نشد.

مرحله بعدی:

- تأیید سه Root باقی‌مانده از Runtime configuration یا مالک کسب‌وکار؛
- تبدیل Gapهای بسته‌شده و باز به P0 backlog با Acceptance صریح.

## ۲۰۲۶-۰۸-۲۷ — شکاف شواهد فرم‌ها

وضعیت: **۴۴۵ Candidate؛ ۷ High، ۱۴۰ Medium و ۲۹۸ Low**

منابع:

- `scripts/windows/build_varanegar_form_evidence_gap_catalog.py`
- `artifacts/varanegar_analysis/ui/varanegar_form_evidence_gaps_20260827.json`
- `docs/varanegar_reconstruction/FORM_EVIDENCE_GAPS_20260827_FA.md`

کشفیات کلیدی:

1. ۱۵۷ فرم Route مستقیم دارند؛ ۱۷۹ Unrouted شکل Child محتمل و ۱۰۹ شکل غیرChild
   نیازمند Entrypoint review هستند.
2. از ۶۶ Unmapped، با جدا کردن Framework/system و Integration/compliance فقط
   هفت شکاف اولویت بالا باقی ماند.
3. اولویت‌های بالا عمدتاً Reconciliation قدیمی Treasury و
   SpecialOptionsDistrict هستند.
4. ۲۷۷ Write-like بدون Permission method محلی اثبات بی‌مجوز بودن نیست؛ Base/
   Menu/Server evidence و Deny test لازم است.
5. سه Candidate متوسط و ۲۲ فرم بدون Call مستقیم به‌عنوان Limit حفظ شدند و به‌زور
   قطعی یا مرده اعلام نشدند.

مرحله بعدی:

- Trace هفت Gap بالا و Parent launcherهای آن‌ها؛
- ساخت P0 backlog با Scope دقیق Evidenceهای تأییدشده.

## ۲۰۲۶-۰۸-۲۷ — پوشش سراسری Call contract فرم‌ها

وضعیت: **۴۴۲ فرم، ۱۰٬۳۸۶ Method body و ۱۵٬۹۹۷ Call First-party**

منابع:

- `scripts/windows/extract_varanegar_all_form_call_contracts.py`
- `artifacts/varanegar_analysis/ui/varanegar_all_form_call_contracts_20260827.json`
- `docs/varanegar_reconstruction/ALL_FORM_CALL_CONTRACTS_20260827_FA.md`

کشفیات کلیدی:

1. همه ۴۴۲ فرم High-confidence پیدا شدند؛ صفر Method کسب‌وکاری خطا و صفر Hash
   mismatch ثبت شد.
2. ۳۵۸ فرم Validation، ۱۲۲ Permission محلی، ۱۱۲ Output و ۱۱۲ Transaction signal
   دارند؛ Heuristic نام Method مجوز یا Command واقعی نیست.
3. ۲۸۰ فرم با احتساب Setting و ۱۱۱ فرم پس از حذف Setting، چندماژولی‌اند؛ ترکیب
   غالب MainData+Sales و MainData+Stock است.
4. شش Orchestrator هم‌زمان MainData/Sales/Stock را درگیر می‌کنند؛ Modular
   Monolith اولیه از این Coupling پشتیبانی می‌کند.
5. ۲۲ فرم بدون Call مستقیم First-party مرده اعلام نشدند؛ Base/Reflection/ORM/
   Event مسیرهای بررسی باقی‌مانده‌اند.

مرحله بعدی:

- فهرست Evidence gapهای ۶۳ فرم Unmapped و ۲۲ فرم بدون Call مستقیم؛
- P0 backlog و Vertical slice فقط‌خواندنی مقصد.

## ۲۰۲۶-۰۸-۲۷ — Golden case Orchestratorهای اصلی

وضعیت: **۱۵۴ Case مصنوعی؛ ۵۴ Failure stage و صفر اجرای Runtime**

منابع:

- `scripts/windows/build_varanegar_orchestrator_golden_cases.py`
- `artifacts/varanegar_analysis/ui/varanegar_orchestrator_golden_cases_20260827.json`
- `docs/varanegar_reconstruction/ORCHESTRATOR_GOLDEN_CASES_20260827_FA.md`

کشفیات و تصمیم‌ها:

1. برای هر ده Command هفت Gate مشترک و خطا بعد از تک‌تک ۵۴ Stage تعریف شد.
2. ۳۰ Case خاص Over-return، Credit، Batch، Toll، Cardex، Posting، Conversion و
   Voucher/Settlement dependency را پوشش می‌دهد.
3. Retry باید به یک Aggregate/Event/Outbox/result همگرا شود و Business outcome
   ناقص هیچ‌وقت Accepted نشود.
4. محیط اجرای مجاز فقط Target test DB ایزوله با Fixture مصنوعی است؛ وارانگار،
   Clone و Production ممنوع‌اند.

مرحله بعدی:

- ساخت P0 implementation backlog با Dependency و Acceptance؛
- تعریف اولین Vertical slice فقط‌خواندنی برای Context/Master/Authorization.

## ۲۰۲۶-۰۸-۲۷ — Command contract Orchestratorهای پرتراکم

وضعیت: **۱۰ Command؛ تمام Method evidence موجود و Validation برابر PASS**

منابع:

- `scripts/windows/build_varanegar_orchestrator_command_contracts.py`
- `artifacts/varanegar_analysis/ui/varanegar_orchestrator_command_contracts_20260827.json`
- `docs/varanegar_reconstruction/ORCHESTRATOR_COMMAND_CONTRACTS_20260827_FA.md`

کشفیات و تصمیم‌ها:

1. Order، Return، SupplierInvoice و StockVoucher به ده Command اتمیک شکسته شدند؛
   Save/Cancel/Convert/Confirm/Generate-return یک Operation واحد نیستند.
2. هر Command یک Transaction owner دارد و اثرهای میان ماژول با Outbox و
   Consumer idempotent انجام می‌شود.
3. Number allocation، stale version، retry و خطا بعد از هر Stage جزو قرارداد
   اجباری است.
4. Ledger/Projection، Source/Target provenance و State/current pointer باید بعد
   از هر Command Reconcile شوند.
5. قراردادها Atomicity Legacy یا آمادگی Production را ادعا نمی‌کنند و هیچ
   Command عملیاتی اجرا نشده است.

مرحله بعدی:

- ساخت Golden caseهای اختصاصی این ده Command؛
- تکمیل P0 backlog و Definition of Ready برای شروع کدنویسی مقصد.

## ۲۰۲۶-۰۸-۲۷ — Call graph عمیق فرم‌های پرتراکم

وضعیت: **۱۲ فرم، ۱۴۰ Edge UI→Business و ۴۵ Edge Business→DataAccess**

منابع:

- `scripts/windows/extract_varanegar_high_impact_call_graph.py`
- `artifacts/varanegar_analysis/ui/varanegar_high_impact_call_graph_20260827.json`
- `docs/varanegar_reconstruction/HIGH_IMPACT_CALL_GRAPH_20260827_FA.md`

کشفیات کلیدی:

1. هر ۱۲ فرم در UI یا Business فراخوانی‌شده Transaction/Commit signal دارند؛
   این Atomicity کل زنجیره را ثابت نمی‌کند.
2. Order/RetSale با EVC/Sale/Discount/Batch/Dist و SupplierInvoice با
   ICA/Stock/Supplier balance/BuyToll مرز چندAggregate دارند.
3. Stock Voucher به Batch/Goods/StockDC/Supplier/Sale/Dist و Customer به چند
   Route namespace/Credit/DC dependency/Access متصل است.
4. در مقصد Transaction owner باید Application command واحد باشد و Commitهای
   UI/Handler Legacy عیناً تکثیر نشوند.
5. همه ۱۳۰ Type هدف پیدا شدند، ۱٬۴۴۳ Method body بدون خطا خوانده شد و Hash شش
   Assembly تغییر نکرده بود.

مرحله بعدی:

- استخراج Command contractهای Order/RetSale/SupplierInvoice/StockVoucher؛
- تعیین Failure boundary و Reconciliation هر Orchestrator.

## ۲۰۲۶-۰۸-۲۷ — IL همه فرم‌های Data-entry

وضعیت: **۱۴۱ از ۱۴۱ فرم؛ ۳٬۹۷۱ Method؛ صفر خطای Method کسب‌وکاری**

منابع:

- `scripts/windows/extract_varanegar_data_entry_il_contracts.py`
- `artifacts/varanegar_analysis/ui/varanegar_data_entry_il_contracts_20260827.json`
- `docs/varanegar_reconstruction/DATA_ENTRY_IL_CATALOG_20260827_FA.md`

کشفیات کلیدی:

1. ۱۳۴ فرم Write-like، ۹۹ فرم Delete/Reverse-like و ۱۳۱ فرم Validation-like
   دارند؛ بازسازی فرم‌ها عمدتاً Command-oriented است، نه CRUD خام.
2. الگوی پایه `SaveCommand/CreateNewDataObject/DeleteCommand/PostExecute` بین
   خانواده‌ها مشترک است و باید به Application shell مقصد تبدیل شود.
3. Discount، Order، RetSale، SupplierInvoice، Customer، Stock Voucher و Goods
   پرتراکم‌ترین نقاط Call graph هستند و اولویت Trace بعدی‌اند.
4. نبود Permission method محلی در ۱۰۴ فرم Write-like اثبات بی‌مجوز بودن نیست؛
   Base template/Menu/Handler باید جدا Trace شود.
5. تنها خطای Parse مربوط به `InitializeComponent` فرم ServerConfig است؛ صفر
   Method کسب‌وکاری خطا داشت و Hash شش DLL تغییر نکرده بود.

مرحله بعدی:

- Trace عمیق Order/RetSale/SupplierInvoice/StockVoucher/Discount؛
- تفکیک Shell مشترک Data-entry از Transaction و Ruleهای دامنه‌ای.

## ۲۰۲۶-۰۸-۲۷ — Role template و Segregation of Duties

وضعیت: **۴۵ Capability، ۱۵ Template و ۱۰ تضاد؛ Grant واقعی صفر**

منابع:

- `scripts/windows/build_negin_erp_sod_role_contract.py`
- `artifacts/varanegar_analysis/ui/negin_erp_role_sod_contract_20260827.json`
- `docs/varanegar_reconstruction/ROLE_AND_SOD_CONTRACT_20260827_FA.md`

کشفیات و تصمیم‌ها:

1. تصمیم مجوز مقصد اشتراک Capability/Scope/Context/Config/Guard با تقدم Deny
   است؛ Visible بودن منو اجازه Command نیست.
2. Planner توزیع، Operator خروج و Controller استثنا سه نقش مستقل شدند.
3. Change و Undo چک‌ها، Posting و Reverse/Close و Migration operator/reviewer
   تضادهای صریح دارند.
4. Approval مادی Scopeدار، Contextدار، منقضی‌شونده، یک‌بارمصرف و غیرقابل
   Self-approval است.
5. Templateها به هیچ شخص واقعی نسبت داده نشده‌اند و برای Production به Signoff
   و UAT نیاز دارند.

مرحله بعدی:

- تبدیل P0 Blueprint به Backlog قابل اجرا و Dependency/Acceptance matrix؛
- تعریف Schema قرارداد Platform/Context/Audit/Outbox/Idempotency.

## ۲۰۲۶-۰۸-۲۷ — قرارداد مهاجرت مقصد

وضعیت: **۱۲ Slice؛ Snapshot/Import اجراشده صفر**

منابع:

- `scripts/windows/build_varanegar_migration_contract.py`
- `artifacts/varanegar_analysis/ui/negin_erp_varanegar_migration_contract_20260827.json`
- `docs/varanegar_reconstruction/MIGRATION_CONTRACT_20260827_FA.md`

کشفیات و تصمیم‌ها:

1. مهاجرت به چهار Contract مستقل Snapshot، Crosswalk، Quarantine و
   Reconciliation شکسته شد؛ کپی جدول به‌تنهایی پذیرفته نیست.
2. Target UUID از Source key مستقل است و نگاشت ambiguous/quarantined اجازه
   فعال شدن Command مقصد نمی‌دهد.
3. دوازده Slice ترتیب وابستگی Master→Rules→Transactions→Ledger را حفظ می‌کنند.
4. شش کلاس ناهنجاری Aggregate فعلی Baseline قرنطینه شدند؛ هیچ‌کدام مجوز Repair
   خودکار Legacy ایجاد نمی‌کنند.
5. هر اختلاف غیرصفر باید Evidence، Owner، Reason و Approval داشته باشد و
   `blocking_unknown` Gate پذیرش است.

مرحله بعدی:

- طراحی Role template و ماتریس Segregation of Duties مقصد؛
- تعریف P0 backlog و Schema contractهای Platform/Context/Crosswalk.

## ۲۰۲۶-۰۸-۲۷ — Manifest یکپارچهٔ شواهد شبانه

وضعیت: **۱۹ Artifact، ۱۶ سند و ۲۰ Builder/Extractor؛ Validation برابر PASS**

منابع:

- `scripts/windows/validate_varanegar_night_evidence_bundle.py`
- `artifacts/varanegar_analysis/ui/varanegar_night_evidence_bundle_manifest_20260827.json`
- `docs/varanegar_reconstruction/NIGHT_EVIDENCE_BUNDLE_20260827_FA.md`

کشفیات و تصمیم‌ها:

1. Artifact identity، Schema version، Hash، ثبت سند در Indexهای دانش و Count
   gateهای اصلی اکنون با یک Validator Offline کنترل می‌شوند.
2. Drift hash برای تغییر معنایی Runtime و Bundle hash برای Snapshot دقیق بستهٔ
   دانش دو قرارداد جدا هستند و نباید جای هم استفاده شوند.
3. PASS این بسته فقط Consistency و Reproducibility دانش را ثابت می‌کند و مجوز
   Write یا آمادگی Cutover نیست.

مرحله بعدی:

- تعریف قرارداد SourceSnapshot/Crosswalk/Quarantine برای فاز P0؛
- ساخت ماتریس Segregation of Duties برای Role templateهای مقصد.

## ۲۰۲۶-۰۸-۲۷ — Blueprint ERP شخصی نگین

وضعیت: **۱۴ ماژول، هفت فاز؛ Technology stack هنوز انتخاب نشده است**

منابع:

- `scripts/windows/build_varanegar_target_erp_blueprint.py`
- `artifacts/varanegar_analysis/ui/negin_personal_erp_blueprint_20260827.json`
- `docs/varanegar_reconstruction/TARGET_ERP_BLUEPRINT_20260827_FA.md`

کشفیات و تصمیم‌ها:

1. معماری شروع `Modular Monolith` با مالکیت دیتای صریح است؛ این تصمیم
   Stack-neutral است و امکان جداسازی ماژول‌های بعدی را حفظ می‌کند.
2. مقصد ۱۴ مرز دارد و هر ماژول فقط داده خودش را می‌نویسد؛ ارتباط Write میان
   ماژول‌ها از Command contract یا Event/Outbox عبور می‌کند.
3. هر Command مادی به `command_id`، `expected_version`، Context عملیاتی و
   تصمیم مجوز نیاز دارد؛ این پاسخ مستقیم به شکاف هشت فرمان Legacy است.
4. اولین برش فقط‌خواندنی ۳ تا ۵ هفته و کل مسیر Gateدار ۲۱ تا ۳۳ هفته برآورد شد؛
   عبور از Gate به Evidence و UAT وابسته است، نه صرف زمان.
5. هیچ Write روی وارانگار، Dual-write، Repair خودکار یا Cutover مجاز نشده است.

مرحله بعدی:

- ساخت Manifest یکپارچه شواهد شبانه و آزمون Hash/Link/Safety؛
- طراحی قرارداد Migration/Crosswalk/Quarantine و Definition of Ready فاز P0.

## ۲۰۲۶-۰۸-۲۷ — قرارداد اجرای گزارش و چاپ

وضعیت: **۲۰ Surface؛ سه چاپ Stateful، سه Export و دو Command-form**

منابع:

- `scripts/windows/build_varanegar_report_execution_contracts.py`
- `artifacts/varanegar_analysis/ui/varanegar_report_execution_contracts_20260827.json`
- `docs/varanegar_reconstruction/REPORT_EXECUTION_CONTRACTS_20260827_FA.md`

کشفیات کلیدی:

1. Batch/Factor/RetSale چاپ را با `PrintedCompleted` و Set-completed/Login hook
   به State وصل می‌کنند؛ Preview و Completion یک Operation نیستند.
2. سه Stock/Cardex surface Export فایل دارند؛ DB write دیده نشد ولی Export باید
   Permission و Audit خروج داده داشته باشد.
3. Statement list/data-entry `SaveCommand` دارند و Report نیستند؛ Aggregate
   Treasury مستقل‌اند.
4. ۱۶ Surface Filter contract دارند و Drill-down باید Scope را دوباره ارزیابی
   کند.

مرحله بعدی:

- Blueprint نهایی Module/API/Data/Audit و ترتیب ساخت ERP شخصی؛
- بازسازی Manifest و گزارش Checkpoint صبحگاهی با همه Hashها و تست‌ها.

## ۲۰۲۶-۰۸-۲۷ — Golden command و Failure injection

وضعیت: **۷۷ Case طراحی شد؛ اجرای Runtime صفر**

منابع:

- `scripts/windows/build_varanegar_golden_command_cases.py`
- `artifacts/varanegar_analysis/ui/varanegar_golden_command_cases_20260827.json`
- `docs/varanegar_reconstruction/GOLDEN_COMMAND_CASES_20260827_FA.md`

کشفیات کلیدی:

1. هر هشت Command Mutating پنج Gate مشترک Auth، Scope، stale version، duplicate
   command و mid-transaction fault دارد.
2. ۳۴ Case خاص، Number race، Cardex منفی، Batch mismatch، Lock conflict، Reverse
   چندExit، Edge نامعتبر و وابستگی Transfer/Balance/Voucher/BookItem را پوشش می‌دهد.
3. Command زمانی Pilot-ready است که هم موفقیت و هم Rollback/Retry/Reconciliation
   روی Target test DB مصنوعی PASS شوند؛ وجود API کافی نیست.

مرحله بعدی:

- قرارداد گزارش و Export/Print با تفکیک Preview و side effect؛
- طراحی Blueprint ماژول‌ها و ترتیب ساخت ERP شخصی بر مبنای Evidence تکمیل‌شده.

## ۲۰۲۶-۰۸-۲۷ — Trace فرمان تا Side effect

وضعیت: **۱۱ Trace، ۱۲ SQL object، ۹۵ Reference رسمی؛ صفر Procedure اجراشده**

منابع:

- `scripts/sql/extract_varanegar_command_side_effects.py`
- `artifacts/varanegar_analysis/ui/varanegar_command_side_effects_20260827.json`
- `docs/varanegar_reconstruction/COMMAND_SIDE_EFFECTS_20260827_FA.md`

کشفیات کلیدی:

1. هشت Command Mutating هیچ پارامتر صریح Idempotency/request/command ID ندارند؛
   مقصد باید این قرارداد را اضافه کند.
2. CreateDist هم Header و Sale link و History را تغییر می‌دهد و GetMaxDistNo
   خودش Side effect دارد.
3. IssueExit به Exit، Sale، Voucher item/detail، Cardex validation و History
   متصل است؛ RemoveExit با ۱۲ Delete و هفت Update یک Reverse چنددفتره است.
4. Change/Undo چک پرداختنی Current cheque، History و ChequeBookItem را درگیر
   می‌کند؛ دریافتی نیز History/Current و وابستگی‌های Transfer/Balance دارد.
5. Transaction محلی Procedureهای چک روشن است؛ Atomicity مسیرهای اصلی توزیع از
   متن همان Moduleها کامل ثابت نشد و Gate caller/nested transaction باقی ماند.

مرحله بعدی:

- طراحی Golden command cases و Failure injection matrix بدون اجرای Runtime؛
- تکمیل Contract گزارش‌ها و Print/Export side effect برای ERP مقصد.

## ۲۰۲۶-۰۸-۲۷ — State machine چک‌ها و توزیع

وضعیت: **۲۲ State، ۲۶ Edge تنظیم‌شده و ۳۴ Edge مشاهده‌شده**

منابع:

- `scripts/windows/build_varanegar_state_machine_catalog.py`
- `artifacts/varanegar_analysis/ui/varanegar_state_machine_catalog_20260827.json`
- `docs/varanegar_reconstruction/STATE_MACHINE_CATALOG_20260827_FA.md`

کشفیات کلیدی:

1. هر ۲۰ Edge مشاهده‌شده دو چرخه چک داخل Workflow تنظیم‌شده‌اند؛ Edge غیرمجاز
   مشاهده نشد، ولی شش Edge مجاز هنوز در History دیده نشده‌اند.
2. وضعیت انتقال بین صندوق در چک دریافتی Current usage صفر دارد اما چرخهٔ
   `1→8→1` با ۴۶٬۵۱۴ رویداد فعال بوده؛ Snapshot جاری برای حذف State کافی نیست.
3. توزیع مسیر غالب `1→2→3→4→7` و چند مسیر برگشتی/Tablet دارد؛ Workflow خطی
   نیست.
4. Status برگشتی توزیع در این Snapshot استفاده نشده و ۲۶٬۰۸۶ توزیع Legacy path
   master ندارند؛ Crosswalk مسیر فعلی هنوز Gate است.
5. مدل مقصد به Transition ledger، Current pointer versioned، allowed-edge و
   Reconciliation وابستگی‌های مالی/انبار نیاز دارد.

مرحله بعدی:

- ساخت Trace end-to-end Command→Handler→SQL→Ledger→Audit؛
- استخراج قرارداد Lock/Idempotency/transaction عملیات حساس.

## ۲۰۲۶-۰۸-۲۷ — قرارداد چهار صفحه فعال

وضعیت: **۲۱ Type، ۴۵ ستون Grid، ۱۰۵ Field candidate و ۶۱ Validation method**

منابع:

- `scripts/windows/build_varanegar_active_page_contracts.py`
- `artifacts/varanegar_analysis/ui/varanegar_active_page_contracts_20260827.json`
- `docs/varanegar_reconstruction/ACTIVE_PAGE_CONTRACTS_20260827_FA.md`

کشفیات کلیدی:

1. صفحه فعال چک دریافتی ۲۹ ستون و Inbox وضعیت‌های ۱،۲،۴،۸،۹ دارد؛ پرداختنی
   ۱۶ ستون و Inbox وضعیت‌های ۱،۵ دارد.
2. هر دو Inbox علاوه بر وضعیت به DC/SaleOffice مؤثر User محدود می‌شوند و گزارش
   جامع همه چک‌ها نیستند.
3. اقلام انبار رابطه Goods×StockDC×AccYear با Policyهای Batch/OrderPoint/Min/Max
   و Snapshotهای OnHand/Damaged/Reserved/Undelivered است.
4. مدیریت توزیع Header، SaleS، مسیر، تیم، ظرفیت خودرو، تاریخ/وضعیت، Lock خروج و
   Goods/Batch/Stock exit را در یک Orchestrator جمع می‌کند.
5. API مقصد باید Read model را از Command جدا و Expected version، Context،
   Idempotency و Audit را اجباری کند.

مرحله بعدی:

- ساخت Trace end-to-end سناریوهای کلیدی و ماتریس State transition؛
- تکمیل Status dictionary از جداول مرجع بدون خواندن دادهٔ عملیاتی شخصی.

## ۲۰۲۶-۰۸-۲۷ — خط مبنای نسخه و Drift

وضعیت: **شش گروه شاهد Hash شدند؛ Baseline برقرار**

منابع:

- `scripts/windows/build_varanegar_runtime_drift_baseline.py`
- `artifacts/varanegar_analysis/ui/varanegar_runtime_drift_baseline_20260827.json`
- `docs/varanegar_reconstruction/RUNTIME_DRIFT_BASELINE_20260827_FA.md`

کشفیات کلیدی:

1. Release مشاهده‌شده ۶۲ Binary دارد؛ ۶۰ فایل Version `5.9.0.376` هستند و دو
   استثنا جدا ثبت شدند.
2. Runtime، Navigation، Behavior/SQL، Authorization، Session surface و Manifest
   Hash معنایی مستقل دارند؛ زمان تولید باعث Drift کاذب نمی‌شود.
3. تغییر هر گروه Gate بازبینی متفاوت دارد و ادعای Parity دامنهٔ تحت اثر را تا
   بازتولید Evidence و تست معتبر متوقف می‌کند.

مرحله بعدی:

- استخراج قرارداد Field/Filter/Validation فرم‌های فعال؛
- ساخت Trace end-to-end برای سناریوهای read-only و write-intent بدون اجرا.

## ۲۰۲۶-۰۸-۲۷ — ماتریس مجوز Route و Command

وضعیت: **۴۰ AccessNode، ۳۶ Command node، بدون هویت و بدون ردیف Grant فردی**

منابع:

- `scripts/sql/extract_varanegar_route_authorization_matrix.py`
- `artifacts/varanegar_analysis/ui/varanegar_route_authorization_matrix_20260827.json`
- `docs/varanegar_reconstruction/AUTHORIZATION_ROUTE_MATRIX_20260827_FA.md`

کشفیات کلیدی:

1. چهار Route باز ۳۶ زیرمجوز مستقل دارند؛ Page access معادل Command access
   نیست.
2. ChangeStatus و Undo برای چک‌های دریافتی/پرداختنی جدا هستند؛ مدیریت توزیع
   نیز Approve/Reverse/Exit/RemoveExit/Free/Print/Export را مستقل می‌کند.
3. از ۱۴۱ کاربر فعال Clone، هفت Admin bypass دارند. پوشش چهار Page به‌ترتیب
   دریافتنی ۳۵، پرداختنی ۲۸، اقلام انبار ۵۲ و توزیع ۳۴ Allow مؤثر است.
4. `issuanceOutput` سه Deny صریح دارد؛ شاهد واقعی برای قاعدهٔ deny-wins است، نه
   فقط یک قرارداد نظری.
5. مجوز عملکردی، محدودهٔ داده Legacy و RBAC مستقل NGT باید در ERP مقصد سه
   مفهوم متمایز بمانند.

مرحله بعدی:

- اتصال Nodeهای فرمان به Handler/SQL و طراحی Role template مقصد با SoD؛
- ثبت Drift/version baseline برای Assembly، Config و SQL contracts.

## ۲۰۲۶-۰۸-۲۷ — معماری Runtime و Call graph فرم‌های فعال

وضعیت: **۲۶ Type هدف، صفر خطای Parse؛ ۱۲ SQL contract و ۹ تست PASS**

منابع:

- `scripts/windows/extract_varanegar_targeted_il_contracts.py`
- `artifacts/varanegar_analysis/ui/varanegar_targeted_il_contracts_20260827.json`
- `docs/varanegar_reconstruction/DOTNET_RUNTIME_ARCHITECTURE_20260827_FA.md`
- `tests/test_varanegar_ui_evidence.py`
- `scripts/sql/extract_varanegar_ui_sql_contracts.py`
- `artifacts/varanegar_analysis/ui/varanegar_ui_sql_contracts_20260827.json`
- `docs/varanegar_reconstruction/UI_CAPABILITY_MATRIX_20260827_FA.md`
- `docs/varanegar_reconstruction/FORM_CATALOG_20260827_FA.md`
- `docs/varanegar_reconstruction/WORKFLOW_CATALOG_20260827_FA.md`
- `docs/varanegar_reconstruction/REPORT_CATALOG_20260827_FA.md`
- `docs/varanegar_reconstruction/MENU_ROUTE_CROSSWALK_20260827_FA.md`

کشفیات کلیدی:

1. منوی Container از `MenuConfig`، Nodeهای Permission و Feature lock ساخته
   می‌شود؛ سال مالی و DC با تغییر Context منو و تاریخ‌های عملیاتی را بازسازی
   می‌کنند.
2. فرم جدید چک دریافتی `RChequeAdapter.GetRChequeSWhere` را با Work queue
   وضعیت‌های ۱،۲،۴،۸ مصرف می‌کند؛ فرم پرداختنی نیز Statusهای ۱ و ۵ را Inbox
   اولیه می‌داند. هیچ‌کدام گزارش «همه چک‌ها» نیستند.
3. Combo وضعیت از Workflow خوانده می‌شود و ChangeStatus/Undo مجوز مستقل و
   Validator تاریخ/تراز/History دارند.
4. `اقلام انبار` از `StockGoodsGridServerModeDC` و Projection
   `vwStockGoodsServerMode` تغذیه می‌شود، نه فقط Master کالا.
5. `مدیریت توزیع` مجموعه Commandهای Create، Exit، Follow، Reverse، Revoke،
   RemoveExit، Free و Batch/Print است و CRUD ساده نیست.
6. زنجیره UI تا Clone برای ۱۲ Object کامل شد: Create/Exit/Remove/Merge توزیع،
   Add/Undo/Validate دو نوع چک و View سروری اقلام انبار؛ Signature، Dependency و
   Hash هر Object ثبت شد.
7. ماتریس ۱۶ Capability نشان داد دسترسی نهایی حاصل اشتراک Menu node، Permission
   Command، Feature entitlement، Context سال/DC، تاریخ عملیاتی و Validator
   وضعیت است؛ این قرارداد برای API وب ثبت شد.
8. تطبیق Hash رشته‌های UI با `InitializeComponent`، تعلق فرم‌ها به خانواده‌های
   R/P tracking را تأیید کرد، اما Labelهای زنده بین old/new مشترک بودند؛ Variant
   دقیق همچنان با اطمینان متوسط ثبت شد و به‌زور قطعی اعلام نشد.
9. کاتالوگ Metadata شامل ۴۴۵ فرم (۴۴۲ با اطمینان بالا)، ۲۰ صفحه Workflow، ۲۰
   Report/analysis، ۸۱ فرم دارای Method گزارش، ۱۹۹ فرم write-capable و ۱۲۰ فرم
   permission-aware ساخته شد. این ظرفیت Runtime است، نه منوی مجاز کاربر جاری.
10. هر ۲۰ Workflow form با IL هدفمند پوشش داده شد: ۱۰۱ Method فرمانی و ۴۷۶
    اتصال Business/DataAccess. Guarantee چهار State machine جدا دارد، توزیع یک
    Orchestrator چندمرحله‌ای است و Follow voucher به تخفیف/EVC/اعتبار/موجودی/
    جایزه/توزیع وابسته است.
11. هر ۲۰ Report/Analysis form با ۸۸ Method و ۷۸ اتصال لایه‌ای تحلیل شد. Cardex
    مشتری/ارزی/متمرکز قراردادهای جدا دارد، گزارش موجودی Router چند Query است و
    چاپ فروش/توزیع به‌دلیل ثبت `PrintCompleted` یک Side effect مجزا محسوب می‌شود.
12. Catalog منو ۸۳۶ MenuConfig، ۴۳۳ FormInfo و ۴٬۵۰۶ AccessNode دارد. چهار
    Caption باز دقیقاً به یک Route رسیدند و دو فرم چک به Variant قدیمی Route
    شدند؛ ابهام old/new با شاهد Config حل شد.

مرحله بعدی:

- استخراج هدفمند Handler/Validator چهار دامنه؛
- اتصال Commandها به Procedure/Viewهای Clone؛
- ساخت ماتریس Capability صفحه/Command/Role/Data partition.

## ۲۰۲۶-۰۸-۲۶ — شروع تطبیق Runtime UI با قراردادهای داده

وضعیت: **استخراج فقط‌خواندنی UI و Win32 با چهار تست PASS**

منابع:

- `scripts/windows/extract_varanegar_ui_inventory.ps1`
- `artifacts/varanegar_analysis/ui/varanegar_ui_inventory_20260827.json`
- `docs/varanegar_reconstruction/UI_RUNTIME_INVENTORY_20260827_FA.md`
- `tests/test_varanegar_ui_evidence.py`

کشفیات کلیدی:

1. Session واقعی `VN.SDS.Container.exe` روی سیستم `192.168.1.184` از Share
   سرور `192.168.1.171` اجرا می‌شود.
2. Snapshot اولیه چهار فرم فعال «اقلام انبار»، «پیگیری چک دریافتی»، «پیگیری
   چک پرداختنی» و «مدیریت توزیع» را ثبت کرد.
3. دو فرم چک ساختار مشترک تاریخ پیگیری/وضعیت/تعداد/مبلغ/توضیحات دارند و هر دو
   Command تغییر وضعیت را بدون انتخاب غیرفعال نگه می‌دارند.
4. Win32 read-only از UI Automation پایدارتر بود؛ Artifact فقط Labelهای
   Allowlist‌شده را ذخیره و همه مقدارهای دیگر را Fingerprint می‌کند.

مرحله بعدی:

- کشف منوی کامل کاربر جاری و Source query چهار فرم بدون اجرای Command؛
- ثبت Visibility/Enablement و تطبیق Permission↔Role؛
- گسترش Golden Caseهای UI برای دامنه‌های ۸، ۹، ۱۲ و ۱۴.

## ۲۰۲۶-۰۸-۲۶ — قفل ماندگاری Evidence و آمادگی ساخت

وضعیت: **Manifest PASS و هفت تست متمرکز PASS**

منابع:

- `scripts/sql/validate_varanegar_reconstruction_bundle.py`
- `tests/test_varanegar_reconstruction_evidence.py`
- `artifacts/varanegar_analysis/manifest_20260826.json`
- `docs/varanegar_reconstruction/RECONSTRUCTION_READINESS_MATRIX_20260826_FA.md`

کشفیات کلیدی:

1. هر ۱۸ سند اکنون Golden case، ابهام، دستور بازتولید و قرارداد مقصد دارد.
2. Validator علاوه بر Compile/Parse/READ_ONLY/deny writer، کلید خام حساس در
   Config/دفترکل، پوشش گزارش سه‌ماهه و کامل‌بودن سندها را Fail-fast می‌کند.
3. هفت تست محلی Manifest، حریم Config و دامنه‌های هویتی/مالی، تراز و اتصال canonical دفترکل، پوشش
   سه‌ماهه و Handoffهای ماندگار را بدون اتصال به SQL تأیید کردند.
4. ماتریس آمادگی هیچ دامنه را Pilot-ready اعلام نمی‌کند؛ همه Foundationها
   Schema-ready هستند و Gate واقعی هرکدام ثبت شده است.

مرحله بعدی:

- ایجاد Target DB جدا و شروع SourceSnapshot/Crosswalk/Quarantine/Audit.
- Import فقط‌خواندنی Slice A و Reconciliation dashboard.
- سپس Golden parity قیمت/Order/Posting، پیش از Command عملیاتی.

## ۲۰۲۶-۰۸-۲۶ — خط مبنای فعالیت سه ماه تجاری

وضعیت: **تجمیع ۱۳ دامنه و ۱۴ بلوک تاریخ‌محور تأیید شد**

منابع:

- `scripts/sql/build_varanegar_three_month_activity.py`
- `artifacts/varanegar_analysis/three_month_operational_activity_20260826.json`
- `docs/varanegar_reconstruction/THREE_MONTH_OPERATIONAL_ACTIVITY_20260826_FA.md`

کشفیات کلیدی:

1. پنجره ثابت `۱۴۰۵/۰۳/۰۱..۱۴۰۵/۰۵/۳۱` بر Business date است، نه CreatedDate.
2. ۳۸٬۰۶۳ سفارش، ۴۰٬۰۵۹ Sale، ۱۲٬۲۶۲ سند انبار، ۳٬۳۷۹ توزیع و ۱٬۲۱۰
   برگشت فروش، جریان عملیاتی فعال و چندمرحله‌ای را ثابت می‌کنند.
3. ۷٬۰۷۳ Receipt، ۶۵٬۵۴۳ Allocation، ۱۲٬۰۸۸ Event چک دریافتی، ۳٬۴۱۹ Pay
   و ۱٬۸۸۳ Event چک پرداختنی، Envelope/Instrument/Allocation/State separation
   را برای مقصد اجباری می‌کنند.
4. ۴۶۴ خرید و ۵۰ مرجوعی خرید فعال است؛ دو Supplier settlement مستقیم نماینده
   کل پرداخت نیست.
5. ۲۷٬۱۷۷ Source group و ۱۰۹٬۴۲۸ PreVoucher line دقیقاً با ۲۰۴ External batch
   و ۱۰۹٬۴۲۸ External line از نظر مبلغ برابرند؛ ۸۸۷ Journal شامل Manual نیز هست.
6. ۳۰٬۱۷۱ مشتری و ۲٬۳۳۶ کالا فعالیت داشته‌اند، ولی ۱۴٬۶۵۸ مشتری و ۱٬۴۸۸ کالا
   بدون فعالیت بوده‌اند؛ Active master و recent activity باید جدا مدل شوند.

مرحله بعدی:

- تعریف Golden dataset نماینده برای هر جریان پرتکرار و استثنا.
- Crosswalk VoucherCreator و Permission/Config به Commandهای Slice A/B.
- شروع مقصد Read-only و Reconciliation dashboard از همین Baseline.

## ۲۰۲۶-۰۸-۲۶ — PreVoucher، سند خارجی و دفترکل دوبل

وضعیت: **زنجیره Posting و تراز عددی تأیید شد**

منابع:

- `scripts/sql/extract_varanegar_general_ledger_domain.py`
- `artifacts/varanegar_analysis/domains/general_ledger_staging_and_posting_20260826.json`
- `docs/varanegar_reconstruction/domains/18_GENERAL_LEDGER_STAGING_AND_POSTING_FA.md`

کشفیات کلیدی:

1. Pipeline سه‌لایه است: ۲٬۳۷۰٬۵۶۹ PreVoucher line → ۱۹۷٬۵۱۸ External batch
   با ۱٬۲۸۷٬۸۷۴ line → ۲۰۵٬۹۴۴ Journal با ۱٬۳۸۵٬۶۹۴ line.
2. هر ۹۴۹٬۲۱۲ گروه Source در PreVoucher، هر External batch و هر ۲۰۵٬۹۴۲
   Journal فعال تراز است. مجموع External دقیقاً با PreVoucher برابر است.
3. دفترکل فعال بدهکار/بستانکار `150,593,312,715,430` دارد؛ سهم External
   `141,731,974,265,684` و سهم Manual `8,861,338,449,746` است.
4. PreVoucher Bus چنددامنه‌ای است: Inventory، Sale، Receipt، Payment، Pay،
   چک دریافتی/پرداختنی، Return، Transfer و Supplier invoice/return را متصل می‌کند.
5. اتصال معتبر External به Journal از `Voucher.ExternalVoucherHeaderId` است.
   `ExternalVoucherHeader.VoucherId` در هیچ مورد با PK یا VoucherNo متناظر برابر
   نیست و نباید FK تلقی شود.
6. Current status pointer یتیم ندارد، اما در ۱٬۰۹۴ سند برابر MAX history نیست؛
   Pointer رسمی است و `MAX(HistoryId)` جایگزین آن نیست.
7. وضعیت جاری تقریباً همه ۲۰۵٬۹۴۰ سند «موقت» است و Status قطعی فعلاً نمونه ندارد؛
   معنی حقوقی/عملی آن باید با حسابداری تأیید شود.
8. Item منفی، دوطرفه، صفر/صفر یا سند فعال نامتوازن صفر است. تمام Itemها سطح
   Sixth ledger دارند؛ Fifth محدود و Seventh در Snapshot صفر است.
9. ۱۷ VoucherCreator و ۵۹۷ Field definition وجود دارد؛ ۱۱ Creator فعال‌اند.
   انبار، فروش و دریافت به‌ترتیب ۱٬۰۱۳٬۷۹۲، ۶۲۵٬۸۳۹ و ۳۴۸٬۴۵۴ PreVoucher line
   ساخته‌اند. شش Capability فعلاً داده ندارند ولی Contractشان حفظ می‌شود.

مرحله بعدی:

- استخراج Rule/Validation هر ۱۱ VoucherCreator از View/Procedure مربوطه.
- بررسی Current pointer rollbackها و معنای وضعیت موقت/قطعی.
- Golden parity از Source تا Journal و سپس شروع Slice A مقصد.

## ۲۰۲۶-۰۸-۲۶ — تنظیمات چندسطحی و فلگ‌های قواعد کسب‌وکار

وضعیت: **ساختار و مصرف SQL تأیید شد؛ تقدم Scopeها و مقدار مؤثر باز است**

منابع:

- `scripts/sql/extract_varanegar_configuration_domain.py`
- `artifacts/varanegar_analysis/domains/configuration_and_rule_flags_20260826.json`
- `docs/varanegar_reconstruction/domains/17_CONFIGURATION_AND_RULE_FLAGS_FA.md`

کشفیات کلیدی:

1. Configuration حداقل پنج Scope دارد: General، Server، DC، Device/NGT و App؛
   ریختن همه در یک Key/Value store بدون Scope معنی قواعد را از بین می‌برد.
2. ۱۷۷ General key و ۳۳۴ Server key فعال، یکتا و بدون Key خالی وجود دارد؛
   فقط سه Server value خالی است و هیچ مقدار خامی در Artifact ذخیره نشده است.
3. General history شامل ۸٬۷۸۲ و Server history شامل ۲۱٬۹۱۴ ردیف است، اما
   ۸٬۶۹۵ و ۲۱٬۱۶۱ ردیف مقدار را تغییر نداده‌اند؛ Save event با Rule version
   یکی نیست.
4. ۴۰ History-only key دیده شد؛ آن‌ها Retired/Renamed candidate هستند و نباید
   خودکار به‌عنوان تنظیم فعال وارد مقصد شوند.
5. تنظیمات DC دو مرکز معتبر دارد؛ ۱۰۲ Customer-field policy برای ۵۱ فیلد و
   ۲۸ الزام ثبت شده و هیچ DC یتیم نیست.
6. از ۴۰ DeviceSettings، ۲۳ مورد Removed است. GPS/distance/stock/return/
   inventory/Sayad field coverage کامل است، ولی Coverage مقدار مؤثر را ثابت
   نمی‌کند.
7. ۲۲ فلگ عملیاتی در ۳ تا ۱۶ Module SQL مصرف می‌شوند؛ AutoOrderConfirm با
   ۱۶ Consumer و SettlementPreviousDebtId با ۱۱ Consumer گسترده‌ترین‌اند.
8. Artifact فقط نام Key، شکل مقدار و Aggregate را نگه می‌دارد؛ Value/OldValue،
   Credential، URL، Path، Host/Application identity و raw history حذف شده‌اند.

مرحله بعدی:

- کشف ترتیب تقدم General/Server/DC/Device/App از کد Client و Stored moduleها.
- ساخت Resolver نسخه‌گذاری‌شده با Scope، effective period و hash غیرحساس.
- استخراج General Ledger/Voucher و Parity موردی مانده تأمین‌کننده.

## ۲۰۲۶-۰۸-۲۶ — مجوزهای Legacy، دامنه داده و RBAC مستقل NGT

وضعیت: **تأییدشده؛ Crosswalk دو مدل باز است**

منابع:

- `scripts/sql/extract_varanegar_authorization_domain.py`
- `artifacts/varanegar_analysis/domains/authorization_legacy_ngt_20260826.json`
- `docs/varanegar_reconstruction/domains/16_AUTHORIZATION_LEGACY_AND_NGT_FA.md`

کشفیات کلیدی:

1. Legacy سه مقدار Neutral=0، Allow=1 و Deny=2 دارد. Admin مستقیم مجاز می‌شود؛
   سپس Allowهای User/Group OR و هر Deny User/Group نتیجه را رد می‌کند.
2. ۱۴۳ User، ۲۲ Group، ۱۵۲ Membership و ۴٬۵۰۶ AccessNode وجود دارد؛ ۱۳ User
   بدون گروه و ۱۵ User چندگروهی‌اند.
3. ۶۲۵٬۶۵۳ UserRight و ۹۵٬۱۶۸ GroupRight معتبر و بدون Pair تکراری وجود دارد؛
   ۹ تعارض direct-allow/group-deny و ۱۳ تعارض direct-deny/group-allow همگی Deny‌اند.
4. مجوز عملیاتی از Data scope جداست. DC، SaleOffice، StockDC با شش operation،
   Customer، Supervisor، PaymentUsance، Manufacturer و OrderType scope مستقل دارند.
5. AccessNodeKey کامل و sibling duplicate صفر است، اما ۱۹ Parent گمشده و
   LevelOfNode همه ۱ است؛ Hierarchy از ParentId ساخته و orphanها قرنطینه می‌شوند.
6. NGT مدل جدا دارد: ۷۸۶ User، ۸۰۷ Principal، هشت Role، ۸۸۷ assignment، ۳۶۹
   Permission، ۴۵۵ Catalog و بیش از ۲٬۴۰۰ Grant/Deny در هر سطح.
7. FK رسمی `IdentityRole_Id` در همه UserRoles خالی است ولی `RoleId` ضمنی همه
   به Role معتبر وصل می‌شود. ۲۳ subject User نیستند و Principal معتبرند.
8. ۲۱۳ Role pair و ۲۸ Catalog pair تکراری وجود دارد؛ Catalog duplicateها جهت
   یکسان دارند. بدون بررسی Owner scope حذف خودکار ممنوع است.

مرحله بعدی:

- استخراج Crosswalk AccessNode به NGT Permission/API route.
- تحلیل General Ledger/Voucher و Feature Flagها.
- ساخت تست تصمیم مجوز و Data scope برای هر Command نسخه وب.

## ۲۰۲۶-۰۸-۲۶ — قرارداد رسمی کاردکس و مانده تأمین‌کننده

وضعیت: **قرارداد تأییدشده؛ Parity عددی موردی در انتظار**

منابع:

- `scripts/sql/extract_varanegar_supplier_cardex_contract.py`
- `artifacts/varanegar_analysis/domains/supplier_cardex_contract_20260826.json`
- `docs/varanegar_reconstruction/domains/15_OFFICIAL_SUPPLIER_CARDEX_CONTRACT_FA.md`

کشفیات کلیدی:

1. Procedure رسمی ۶۵۳ خط Dynamic SQL و ۲۸ Union leg با ۲۷ TitleId دارد؛
   فرمول نهایی `ΣBedAmount - ΣBesAmount` است.
2. مانده از فروش/برگشت، دریافت‌های مشتری‌مانند، چک و حواله، Pay و سه ابزار،
   سند حسابداری، خرید/مرجوعی، تنخواه و اعلامیه ساخته می‌شود؛ یک جدول کافی نیست.
3. Crosswalkهای Supplier/Contact/DL/Customer هم‌زمان مصرف می‌شوند و هر Branch
   Date/AccYear/DC/SaleOffice/SL/Reason/State/Flag gate مخصوص دارد.
4. چک دریافتی در وضعیت ۴/۵/۹ جهت بدهکار و سایر وضعیت‌ها بستانکار می‌شود؛ چک
   پرداختنی non-certified در ۳/۵ بدهکار و ۲ بستانکار است.
5. خرید بستانکار و مرجوعی خرید بدهکار است؛ مبلغ خرید، ineffective supplier
   addition/discount را نیز اصلاح می‌کند.
6. POrder/PPayment، PayGroup، Fund/FundItem و ManualVoucher فعلاً خالی‌اند، ولی
   Branch رسمی آن‌ها باید در مقصد و Golden Dataset حفظ شود.
7. دو branch ManualVoucher با DebitContact و CreditContact هر دو TitleId=26 و
   هر دو Bed هستند؛ بدون نمونه داده، رفتار منبع حفظ و برای حسابداری Review شد.
8. SHA-256 Procedure در Artifact ثبت شده تا هر تغییر تعریف، بازبینی دوباره
   ماتریس و Reconciliation را اجباری کند.

مرحله بعدی:

- اجرای Parity کنترل‌شده برای Golden Supplierها در سطح TitleId و مانده نهایی.
- استخراج Feature Flagهای داخلی و ساخت Scope contract نسخه‌گذاری‌شده.
- تبدیل ۱۵ دامنه کشف‌شده به ترتیب مهاجرت و Definition of Done نسخه وب.

## ۲۰۲۶-۰۸-۲۶ — خروج وجه تأمین‌کننده و چرخه چک پرداختنی

وضعیت: **تأییدشده روی Clone فقط‌خواندنی**

منابع:

- `scripts/sql/extract_varanegar_supplier_disbursement_domain.py`
- `artifacts/varanegar_analysis/domains/supplier_disbursement_and_payable_cheques_20260826.json`
- `docs/varanegar_reconstruction/domains/14_SUPPLIER_DISBURSEMENT_AND_PAYABLE_CHEQUES_FA.md`

کشفیات کلیدی:

1. ۳۰٬۳۲۲ Pay همگی Status=2 تأییدشده‌اند، ولی ConfirmDate فقط در ۱۷٬۳۰۱
   ردیف پر است؛ Status مرجع رسمی و تاریخ تأیید شاهد ناقص Legacy است.
2. Pay پاکت پرداخت است و Cash/Withdrawal/PCheque فرزند آن‌اند. ۱٬۴۵۱ Pay چند
   Instrument و ۲۹ Pay ترکیب چند نوع ابزار دارند؛ بیشینه ۷۶ ابزار در یک Pay.
3. ۴۸۷ Pay بدون سه ابزار اصلی وجود دارد و از مسیرهای دیگری مصرف می‌شود؛ مدل
   مقصد نباید Payment را به یک Type و Amount منفرد تقلیل دهد.
4. پرداخت مستقیم Supplier شامل ۱۱۸ نقد، ۱٬۷۲۸ برداشت و ۲٬۶۳۰ چک است؛ این
   جمعیت ثابت می‌کند دو ردیف tblSupSettlement کل پرداخت تأمین‌کننده نیست.
5. ۴٬۶۷۲ چک، ۱۳٬۱۰۸ History و ۸٬۴۳۶ Transition وجود دارد. Current pointer
   در همه چک‌ها معتبر، متعلق به همان چک و برابر آخرین HistoryId است.
6. همه چک‌ها از Status 1 «صادره» شروع شده‌اند؛ وضعیت جاری: یک عودت، ۳٬۶۳۷
   پرداخت، ۸۱ ابطالی و ۹۵۳ پرداختنی. تمام انتقال‌های مشاهده‌شده مجازند.
7. Cardex رسمی چک Supplierِ non-certified را در Status 3/5 به Bed و Status 2
   به Bes می‌برد و Status 4 را بی‌اثر می‌کند؛ Certified از این شاخه حذف است.
8. ۶۶ دسته‌چک و ۵٬۶۸۷ برگ وجود دارد. ۴٬۶۷۲ برگ به چک یکتا وصل‌اند و ۱۵۵ برگ
   Used بدون چک فعلی به Review نیاز دارند.
9. همه Instrumentها UUID یکتا، مبلغ مثبت و Pay معتبر دارند؛ IsReconciled برای
   همه Withdrawal/Cheque فعلی صفر است.
10. سه ماه Clone شامل ۳٬۴۱۹ Pay، ۳٬۳۹۹ برداشت، ۶۰۱ چک و ۱٬۸۸۳ رخداد وضعیت چک
    است؛ مسیر خروج وجه فعال و عملیاتی است.

مرحله بعدی:

- بازسازی دفتر حساب تأمین‌کننده با تمام ۲۵ Source قرارداد رسمی و تطبیق مانده.
- بررسی ۴۸۷ Pay با ابزار جایگزین، Certified cheque و برگ‌های Used بدون چک.
- تبدیل قراردادهای خرید/پرداخت به Golden Dataset مهاجرت.

## ۲۰۲۶-۰۸-۲۶ — خرید، مرجوعی خرید و بدهی تأمین‌کننده

وضعیت: **تأییدشده روی Clone فقط‌خواندنی**

منابع:

- `scripts/sql/extract_varanegar_supplier_purchase_domain.py`
- `artifacts/varanegar_analysis/domains/supplier_purchase_and_payables_20260826.json`
- `docs/varanegar_reconstruction/domains/13_SUPPLIER_PURCHASE_AND_PAYABLES_FA.md`

کشفیات کلیدی:

1. خرید یک State واحد نیست: رسید انبار نوع ۲۰، Relation فاکتور/رسید و Apply
   هزینه سه مرحله مستقل‌اند. هر ۱۴۱ فاکتور Status=0 نیز رسید Confirmed دارد.
2. ۳٬۴۲۶ فاکتور و ۳۰٬۰۹۶ Item برای ۶۳ تأمین‌کننده وجود دارد. همه Qtyها مثبت
   و تمام مراجع اصلی معتبرند.
3. ضرب ساده Qty×Price برای ۳۴ Item اختلاف دارد، اما قرارداد رسمی نوع کالا،
   PrizeQty، ExchangeRate و Floor/Round هر ۳۰٬۰۹۶ Item را معتبر می‌داند.
4. ۳٬۶۸۹ Relation، همه فاکتورها را به ۳٬۶۸۸ رسید Confirmed نوع ۲۰ وصل می‌کند؛
   ۲۰۹ فاکتور چند رسید و یک رسید دو فاکتور دارد، پس رابطه واقعاً چندبه‌چند است.
5. مقدار همه ۳۰٬۰۹۶ گروه مشترک Invoice/Goods دقیق است. پنج گروه Voucher-only
   در دو فاکتور با Qty مجموع ۹٬۳۲۰ باید Review شوند، نه حذف یا تبدیل خودکار.
6. ۷٬۵۱۶ Toll و ۶۲٬۶۷۰ Allocation در سطح Header و هر چهار مؤلفه Item دقیقاً
   تطبیق دارند. Apply رسمی هزینه را روی ItemPrice انبار توزیع و گردکردن را
   اصلاح می‌کند.
7. ۴۶۷ مرجوعی و ۳٬۵۱۸ Item همگی خروج Confirmed نوع ۵۵ دارند و مقدار همه گروه‌ها
   دقیق است. فقط ۲۷ مرجوعی SourceInvoice دارند؛ این Ref منشأ اختیاری است.
8. در ۲۷ مرجوعی مبنادار، ۱۴۹ گروه کالا در محدوده فاکتور منبع، هفت گروه بدون
   Source goods و هیچ گروه بیش از Qty منبع است.
9. `tblSupSettlement` فقط دو Allocation جزئی دارد و دفتر مانده نیست؛ قرارداد
   رسمی مانده تأمین‌کننده فاکتور، مرجوعی، ابزارهای پرداخت، فروش و اسناد دستی را
   با هم ترکیب می‌کند.
10. در سه ماه Clone، ۴۶۴ فاکتور، ۴٬۲۵۵ Item، ۵۰ مرجوعی و ۵۰۱ Relation فعال
    ثبت شده است؛ POrder Legacy و PurchaseOrderRef فعلی مصرف نشده‌اند.

مرحله بعدی:

- استخراج چک پرداختنی، برداشت/پرداخت نقدی و چرخه واقعی خروج وجه تأمین‌کننده.
- بازسازی Supplier Cardex با تمام Sourceها و تطبیق مانده رسمی.
- ساخت Golden Caseهای Apply/Unapply هزینه، چندرسیدی و مرجوعی مستقل.

## ۲۰۲۶-۰۸-۲۶ — چرخه چک دریافتی و تسویه چک برگشتی

وضعیت: **تأییدشده روی Clone فقط‌خواندنی**

منابع:

- `scripts/sql/extract_varanegar_received_cheque_domain.py`
- `artifacts/varanegar_analysis/domains/received_cheque_lifecycle_20260826.json`
- `docs/varanegar_reconstruction/domains/12_RECEIVED_CHEQUE_LIFECYCLE_FA.md`

کشفیات کلیدی:

1. وضعیت چک روی Header نیست؛ ۲۳٬۸۲۲ چک و ۱۰۶٬۱۳۱ رخداد History وجود دارد و
   هر چک دقیقاً یک `IsLast=1` دارد. وضعیت جاری همیشه آخرین ID تاریخچه است.
2. هر ۸۲٬۳۰۹ Transition دارای Previous History و TransitionId معتبر است؛
   یتیم، اتصال به چک دیگر یا عدم تطابق Old/New Status صفر است.
3. Statusهای جاری: ۷۰۳ صندوق، ۵۳ بانک، ۸٬۲۸۴ وصولی، ۱۳۸ برگشتی، ۱٬۹۵۶
   استرداد، ۱۲٬۶۳۵ واگذار به غیر و ۵۳ حقوقی. Status 8 فقط Event انتقال صندوق
   و Current آن صفر است.
4. همه چک‌ها Receipt تأییدشده، مبلغ مثبت، UUID یکتا و Bank/Type معتبر دارند.
   کلید حساس بانک+شماره+تاریخ+حساب نیز گروه تکراری ندارد؛ مقادیر ذخیره نشده‌اند.
5. در پنجره سه‌ماهه ۱۲٬۰۸۸ Event برای ۳٬۶۸۹ چک ثبت شده است. پرتکرارترین مسیر
   ۲۳٬۲۵۷ جفت انتقال ۱→۸→۱، سپس ۱۳٬۷۳۶ واگذاری به غیر است.
6. Procedure رسمی Payment چکی نوع ۲/۱۰۰۸ را در وضعیت‌های ۴ برگشتی، ۵ استرداد
   و ۹ حقوقی از PayAmount حذف می‌کند؛ Status 7 واگذار به غیر همچنان پرداخت
   معتبر مشتری است.
7. اکنون ۴٬۶۹۲ Allocation برای ۲٬۰۱۸ چک و ۴٬۳۴۷ Sale به‌علت Status ۴/۵/۹
   از اثر پرداخت حذف می‌شوند.
8. ۵٬۶۵۰ Payment با RetChequeRef برای ۱٬۳۲۰ چک وجود دارد. از ۲٬۱۴۷ چک جاری
   مشکل‌دار، ۸۲۷ بدون تسویه، ۴۶۳ جزئی، ۸۵۷ کامل و Over-settlement صفر است.
9. مانده چک برگشتی OpenInvoice در سطح Sale Pool می‌شود، نه چک. بازسازی فرمول
   برای هر ۲۱۴٬۹۷۱ Projection دقیق و اختلاف صفر بود؛ ۲٬۰۰۸ Sale مانده مثبت دارد.
10. هشت چک واگذارشده Master PayId ندارند و ۳۵ چک حقوقی LegalType ندارند. این
    برداشت اولیه بعداً اصلاح شد: هر هشت History PayId2 معتبر دارند و LegalType
    تهی نیز UNKNOWN_SOURCE است؛ ریسک واقعی نقص انتقال LegalType در تأیید گروهی است.
    دربارهٔ ۴۹ Payment با Customer متفاوت بعداً اصلاح شد: هر ۴۹ مورد تخصیص
    اولیه‌ی دقیق دارند و Anomaly نیستند؛ رجوع شود به قرارداد RCX پایین سند.

مرحله بعدی:

- استخراج خرید، فاکتور تأمین‌کننده، ورود خرید و بدهی/پرداختنی.
- تطبیق Purchase Order → Purchase/Receipt → Inventory → Supplier Settlement.
- ساخت Golden Caseهای چک جایگزین، Pool چندچک و تسویه بین‌طرفی.

## ۲۰۲۶-۰۸-۲۶ — برگشت از فروش، ورود انبار و مصرف اعتبار

وضعیت: **تأییدشده روی Clone فقط‌خواندنی**

منابع:

- `scripts/sql/extract_varanegar_sales_return_domain.py`
- `artifacts/varanegar_analysis/domains/sales_returns_and_settlement_20260826.json`
- `docs/varanegar_reconstruction/domains/11_SALES_RETURNS_AND_SETTLEMENT_FA.md`

کشفیات کلیدی:

1. RetOrder، RetSale رسمی، Voucher ورود انبار، مصرف اعتبار و RD/NGT Draft
   Stateهای مستقل‌اند و نباید در یک جدول یا یک Status ادغام شوند.
2. ۱۴٬۰۹۱ برگشت با UUID و کلید تجاری یکتا وجود دارد؛ ۱۳٬۹۱۳ فعال، ۱۷۸
   ابطال‌شده، ۹۶۸ دارای Sale مبنا و ۱۱٬۱۷۱ متصل به توزیع‌اند.
3. `tblRetSaleItm.SaleRef` در همه ۴۱٬۹۳۱ Item خالی است. کلید مرکب رسمی
   `TSaleRef+Goods+Prize+FreeReason` برای هر ۶٬۰۲۵ Item مبنادار دقیقاً یک
   SaleItem می‌یابد؛ ۵٬۹۰۱ گروه برگشت کامل، ۱۲۴ جزئی و بیش‌برگشت صفر است.
4. **اصلاح‌شده در ۲۰۲۶-۰۸-۲۷:** تفاوت TotalAmount با `Item.Amount` اختلاف
   Gross/Net است، نه فساد داده. قرارداد رسمی `TotalAmount=ΣAmountNut` و
   `AmountNut=Amount-Discount+AddAmount` در هر ۱۴٬۰۹۱ سند Residual صفر دارد؛
   ۶۹۶ مورد فعال قبلی نباید صرف این تفاوت وارد Quarantine شوند.
5. هر ۱۳٬۹۱۳ برگشت فعال دقیقاً یک Voucher نوع ۱۰ تأییدشده دارد. تطبیق صحیح
   تجمیعی `(RetSale,Goods)` در هر ۳۹٬۶۰۹ گروه دقیق و اختلاف مقدار صفر است؛ ID
   و RowOrder Voucher Crosswalk ردیف برگشت نیست.
6. ۱۴٬۵۸۶ Payment نوع 1006 به ۱۳٬۲۲۳ برگشت متصل است و هر کدام دقیقاً یک
   Counter-entry نوع 97 با مبلغ/Customer برابر دارد. ۱۲٬۴۹۶ برگشت کاملاً،
   ۸۱۳ جزئی و ۶۹۰ هنوز اصلاً مصرف نشده‌اند؛ بیش‌مصرف صفر است.
7. فقط ۸٬۴۴۴ Allocation با `Header.SaleSettlementRef` برابر و ۵٬۱۷۸ متفاوت
   است؛ این فیلد Hint اولیه است، نه فهرست نهایی تخصیص‌ها.
8. RetOrder فقط ۵ نمونه دارد و هیچ نمونه Confirm‌شده/فعالِ تبدیل‌شده وجود
   ندارد؛ مسیر درخواست برای Golden Case به داده کنترل‌شده نیاز دارد.
9. ۳۸ Header و ۶۰ Item در RD با Status 7 هنوز هیچ Main Return متناظر ندارند؛
   این‌ها کار در جریان پایان توزیع‌اند. Procedure Finalize پس از تبدیل، Staging
   را حذف می‌کند.
10. دو NGT Return فعلی هیچ Crosswalk معتبر به RetOrder/RetSale ندارند و تا
    تأیید Integration نباید سند مالی یا انبار رسمی شمرده شوند.

مرحله بعدی:

- بستن ماشین حالت چک دریافتی، انتقال/واگذاری، برگشت، جایگزینی و تسویه مجدد.
- تطبیق `TblCheque`، Historyها، RCheque/RCheque2 و اثر رسمی بر OpenInvoice.
- ساخت Golden Caseهای Return چندفاکتوری، RD Finalize و اختلاف مبلغ Header.

## ۲۰۲۶-۰۸-۲۶ — وصول، ابزار دریافت، تخصیص پرداخت و مانده باز

وضعیت: **تأییدشده روی Clone فقط‌خواندنی**

منابع:

- `scripts/sql/extract_varanegar_collection_payment_domain.py`
- `artifacts/varanegar_analysis/domains/collections_payments_open_invoices_20260826.json`
- `docs/varanegar_reconstruction/domains/10_COLLECTIONS_PAYMENTS_OPEN_INVOICES_FA.md`

کشفیات کلیدی:

1. Receipt، ابزار دریافت، Ledger تخصیص `Acc.tblPayments` و Projection
   `tblOpenInvoice` چهار لایه مستقل‌اند. ثبت دریافت معادل تسویه فاکتور نیست.
2. مبلغ هر ۶۸٬۶۲۶ Receipt دقیقاً با مجموع Cash/Cheque/BankOrder آن منطبق است؛
   اختلاف و ابزار یتیم صفر است. ۹٬۹۸۸ Receipt ابزار ترکیبی دارند.
3. از ۴۹۳٬۴۹۴ Payment فقط ۲۵۶٬۳۲۹ ردیف به ابزار Receipt وصل است؛ ۲۳۷٬۱۶۵
   ردیف تخفیف، برگشت، انتقال و سایر تعدیلات بدون ابزار دریافت‌اند.
4. هیچ Over-allocation وجود ندارد، اما ۱٬۴۴۸ Receipt بدون تخصیص و ۷ Receipt
   دارای تخصیص ناقص‌اند. Trigger رسمی سقف تخصیص را کنترل می‌کند.
5. `OpenAmount = TotalAmount - ISNULL(PayAmount,0)` برای تمام ۲۱۴٬۹۷۱ ردیف
   دقیق است. PayAmount رسمی وضعیت چک، علامت نوع، برگشت و روابط تسویه را لحاظ
   می‌کند؛ جمع خام در ۴٬۷۴۴ و جمع علامت‌دار ساده در ۴٬۶۷۷ فاکتور غلط است.
6. OpenInvoice یک Cache بازسازی‌شونده است: دو Sale فعال فعلاً در آن نیست، ۱۷
   مانده منفی و ناسازگاری گسترده PassDate وجود دارد. Clamp یا اصلاح خودکار
   ممنوع است.
7. NGT دارای ۳٬۵۲۳ Payment و ۳٬۹۱۷ Detail است. ۲۷۴ Crosswalk Receipt از نظر
   ID/UUID/شماره دقیق‌اند، ولی مبلغ فقط در چهار مورد برابر است؛ Scope Receipt
   تیم پخش با Payment یک تماس یکی فرض نمی‌شود.
8. ۱۴ NGT Payment بدون Detail و ۴۳ مورد Under-allocation وجود دارد؛ ۱۷۲ Detail
   فاکتور قدیمی Crosswalk عددی/UUID دقیق دارند.
9. از ۴۰۴ PaymentTerm فقط ۱۵ فعال است. ۴۸۲ اتصال فعال فروشنده به Term حذف‌شده
   وجود دارد و باید در Migration Reconciliation شود.
10. هیچ داده خام چک/حساب/صیاد/POS، هویت مشتری یا نام کاربر/میزبان در Artifact
    ذخیره نشده و همه Assertions ایمنی و تطبیق عبور کرده‌اند.

مرحله بعدی:

- استخراج برگشت فروش، برگشت چک و اثر آن‌ها بر Settlement.
- بستن ماشین حالت چک دریافتی از `tblChqHist` و Viewهای رسمی.
- ساخت Golden Caseهای Receipt ترکیبی، Allocation ناقص و NGT Team Settlement.

## ۲۰۲۶-۰۸-۲۶ — توزیع، تیم ارسال، خروج و شاهد تحویل

وضعیت: **تأییدشده روی Clone فقط‌خواندنی**

منابع:

- `scripts/sql/extract_varanegar_distribution_delivery_domain.py`
- `artifacts/varanegar_analysis/domains/distribution_delivery_20260826.json`
- `docs/varanegar_reconstruction/domains/09_DISTRIBUTION_AND_DELIVERY_FA.md`

کشفیات کلیدی:

1. ۲۶٬۰۸۶ Distribution با UUID یکتا وجود دارد؛ شماره فقط در ترکیب سال، DC
   و DistNo یکتا است. ۲۳٬۳۸۲ مورد خاتمه‌یافته و ۲٬۵۸۴ مورد ابطال‌شده‌اند.
2. ۱۹۲٬۵۷۳ رخداد Log، ماشین حالت `صادر نشده → خروجی → ارسال → توزیع → خاتمه`
   و مسیرهای بازگشت را ثابت می‌کند. Status باید Projection از Event باشد.
3. شش Distribution قدیمی Header جاری ندارند ولی ۵۱ رخداد Log آن‌ها باقی است؛
   این تاریخچه باید به‌صورت Tombstone حفظ شود.
4. همه Distributionها تیم کامل دارند، اما Master و مصرف خودرو فقط یک Truck
   است. ۲۰ Team Template نیز یک Truck و ۲۰ Driver/Distributer دارد.
5. اصلاح مهم: هفت کد DistPath در ۲۶٬۰۸۶ Header، FK یتیم نیستند. ستون FK رسمی
   ندارد، `CreateDist` عدد را مستقیم ذخیره می‌کند، Lookup مقدار
   `DistPathTreeNo` را می‌نویسد و تنظیمات فعلی Branch ورود عدد آزاد را فعال کرده
   است. کدها معتبر ولی بدون عنوان‌اند و نباید به ID مستر یا Default route نگاشت
   شوند.
6. ۲۴۸٬۵۵۴ Sale به ۲۳٬۵۰۲ Distribution وصل‌اند. ۱۵٬۱۷۸ Sale سابقه چند
   تخصیص دارند و ۱٬۸۰۷ Sale تاریخچه دارند ولی Pointer جاری آن‌ها پاک شده است.
7. ۹۵۳٬۹۷۸ Full Event برای ۲۵۶٬۲۵۴ Sale وجود دارد، اما PreviousId در همه
   ردیف‌ها Null است؛ ترتیب باید از زمان/ID ساخته شود.
8. ۲۴٬۰۳۵ Exit فعال برای ۲۳٬۵۰۱ Distribution است؛ ۵۳۴ Distribution دو Exit
   فعال دارند. DistRef Sale و Exit در همه ۲۴۸٬۵۵۳ اتصال منطبق است.
9. سه دلیل عدم تحویل و جدول‌های برگشت توزیع وجود دارند، اما هیچ مصرف فعلی
   ندارند؛ Workflow آن‌ها هنوز عملیاتی اثبات نشده است.
10. ۷٬۴۰۵ CustomerCall NGT به ۵۲۱ Distribution با ID/UUID منطبق وصل‌اند،
    اما DeliveryDate و SaleDate همه خالی‌اند؛ Status خاتمه اثبات مستقل دریافت
    مشتری نیست.

مرحله بعدی:

- استخراج وصول، پرداخت، مانده باز فاکتور، دریافت نقد/چک/POS و اتصال به تور.
- ردیابی Procedureهای عدم تحویل و برگشت برای تعیین Workflow فعال یا مرده.
- تعریف Golden Case توزیع چندخروجی و Unassign/Reassign فروش.

## ۲۰۲۶-۰۸-۲۶ — موجودی، رزرو، گردش انبار و خروج کالا

وضعیت: **تأییدشده روی Clone فقط‌خواندنی**

منابع:

- `scripts/sql/extract_varanegar_inventory_reservation_exit_domain.py`
- `artifacts/varanegar_analysis/domains/inventory_reservation_and_exit_20260826.json`
- `docs/varanegar_reconstruction/domains/08_INVENTORY_RESERVATION_AND_EXIT_FA.md`

کشفیات کلیدی:

1. در سال ۱۴۰۵ تعداد ۳۳٬۳۱۴ Snapshot کالا–انبار برای ۳٬۸۲۴ کالا و ۹ انبار
   وجود دارد. هیچ جزء موجودی منفی نیست، اما `OnHand-Reserved` در ۲۱۲ کلید
   منفی است؛ Trigger اجزا را کنترل می‌کند نه تفاضل آن‌ها را.
2. رزرو سندی و تعهد سفارش باز دو قرارداد مستقل‌اند: ۲۹۷ کلید رزرو، ۳۱۸ کلید
   سفارش باز و فقط ۱۱ کلید مشترک. `OnHand-OpenOrder` فقط در ۳ کلید منفی است.
3. مانده رزرو و ضایعاتی با Viewهای رسمی Cardex در تمام ۳۳٬۳۱۴ کلید تطبیق
   دارد. مقایسهٔ اولیهٔ Cardex-only در ۱٬۵۹۴ کلید، با فاصلهٔ ۱۰۴٬۴۷۰، اختلاف نشان داد؛ این نتیجه در کشف اصلاحی ۲۰۲۶-۰۸-۲۷ به تعهد فروشِ بدون خروج بازطبقه‌بندی شد و Residual فرمول رسمی صفر است.
   Ledger در همه آن‌ها بزرگ‌تر از Snapshot است.
4. `StockGoods` باید Snapshot عملیاتی مرجع و Cardex باید Ledger مستقل با Job
   مغایرت‌گیری باشد؛ هیچ Rebuild یا Overwrite خودکار از جمع ساده اسناد مجاز نیست.
5. ۹۶٬۵۰۲ سند و ۱٬۵۱۸٬۱۶۶ ردیف انبار وجود دارد. شماره سند فقط در ترکیب سال،
   انبار، نوع و شماره یکتا است؛ ۱۰٬۱۱۸ Header UUID ندارند و یک UUID تکراری است.
6. اتصال خروج فعال به سند نوع ۶۰ دقیقاً یک‌به‌یک است: ۲۴٬۰۳۵ خروج فعال و
   ۲۴٬۰۳۵ سند، بدون یتیم، تکرار یا اختلاف انبار. `DocRef` برای سایر نوع‌ها
   همچنان Polymorphic است.
7. ۲۴۸٬۵۵۳ Sale به ۲۴٬۰۳۵ خروج فعال وصل‌اند. راننده در Exit مستقیم ذخیره
   نشده و باید از دامنه توزیع استخراج شود.
8. `PreSaleStockOnHandQty` فقط ۶۵۷ کالا از یک انبار را پوشش می‌دهد و Projection
   محدود پیش‌فروش است، نه Master موجودی.
9. `NGT.StockLevels` تعداد ۴۰٬۹۴۵ Snapshot برای ۵۶۶ تور و ۱٬۳۴۱ کالا دارد؛
   فعلاً فقط InitialQty پر است و Ledger کامل تور محسوب نمی‌شود.
10. هر سه مسیر Batch فعلی خالی‌اند، با وجود وجود Schema و کد پشتیبان؛ قابلیت
    باید حفظ ولی فعال‌سازی آن جداگانه آزموده شود.

مرحله بعدی:

- استخراج توزیع، راننده/خودرو، تخصیص Sale به Dist و وضعیت تحویل.
- تکرار فرمول کامل Cardex منهای تعهدهای عملیاتی روی Snapshot مجاز و آرام Production؛ Residual Clone فعلی صفر است.

## ۲۰۲۶-۰۸-۲۷ — اصلاح اساسی برداشت ۱٬۵۹۴ اختلاف موجودی

- مقایسهٔ قبلی `StockGoods.OnHandQty` با Cardex-only، فرمول رسمی
  `dbo.usp_ModifyStockGoods` را ناقص کرده بود.
- فرمول کامل شش خانوادهٔ تعهد عملیاتی را از `vwHealthyCardexForCheck` کم
  می‌کند. در Clone فعلی فقط فروش فعالِ بدون خروج غیرصفر است: ۱٬۵۹۴ کلید و
  ۱۰۴٬۴۷۰ واحد.
- پس از اعمال فرمول رسمی، هر ۳۳٬۳۱۴ کلید دقیقاً برابر و Residual صفر است.
- ۸۲۱ فروش/۵٬۱۸۰ ردیف این تعهد را می‌سازند؛ ۷۶۸ فروش در سن ۳–۷ روز و ۵۳
  فروش در سن ۸–۳۰ روز قرار دارند.
- Procedure رسمی Repair هم دارد و در این تحلیل اجرا نشد؛ فقط SELECT متناظر
  روی Clone `READ_ONLY` اجرا شد.
- سند: `STOCK_RECONCILIATION_INCIDENT_PLAYBOOK_20260827_FA.md`
- Artifact: `varanegar_stock_reconciliation_diagnostic_contract_20260827.json`
- Extractor: `scripts/sql/extract_varanegar_stock_reconciliation_diagnostic_contract.py`
- طراحی قرارداد Snapshot/Ledger/Reconciliation و Golden Case خروج نوع ۶۰.

## ۲۰۲۶-۰۸-۲۶ — چرخه سفارش تا فروش

وضعیت: **تأییدشده روی Clone فقط‌خواندنی**

منابع:

- `scripts/sql/extract_varanegar_order_sale_lifecycle_domain.py`
- `artifacts/varanegar_analysis/domains/order_sale_lifecycle_20260826.json`
- `docs/varanegar_reconstruction/domains/07_ORDER_TO_SALE_LIFECYCLE_FA.md`

کشفیات کلیدی:

1. ۲۶۰٬۵۱۷ سفارش و ۲۷۵٬۹۹۵ Sale وجود دارد. سفارش می‌تواند چند SaleHdr
   تاریخی داشته باشد و فقط یک نسخه را با SaleHdrRef انتخاب کند.
2. ۱۸٬۰۰۹ سفارش چند تلاش Sale دارند، اما هیچ سفارش بیش از یک Sale فعال ندارد؛
   ۲۶٬۳۹۲ نسخه لغوشده قدیمی غیرمنتخب‌اند.
3. ۳۴٬۳۹۷ سفارش غیرلغوشده به Sale لغوشده منتخب اشاره می‌کنند. این یک State
   واقعی «تلاش تبدیل لغوشده/منتظر اقدام» است، نه داده‌ای برای حذف.
4. ۲۱۲٬۷۵۹ فاکتور فعال و ۲٬۲۱۴ حواله فعال بدون SaleNo وجود دارد. SaleNo Null
   در این مرحله وضعیت معتبر است.
5. تقریباً تمام سفارش‌ها ConfirmDate دارند؛ این فقط Marker ذخیره‌شده است و
   Human Approval را ثابت نمی‌کند.
6. SoldQty تمام ۱٬۴۶۹٬۷۲۷ OrderLine صفر است، درحالی‌که IsUsed وضعیت صدور را
   نشان می‌دهد؛ مقدار فروش باید از SaleLine/Qty Detail Reconcile شود.
7. `tblSaleHdrDetail` با ۵۴۰٬۸۸۸ ردیف برای ۲۷۵٬۹۹۵ Sale، Event/Snapshot
   انتقال وضعیت است، نه Extension یک‌به‌یک Header.
8. ۲۶۶٬۱۸۳ Voucher Snapshot یکتا و ۲٬۱۲۸٬۲۵۳ Item وجود دارد. Route Snapshot
   فقط ۱۳٬۶۶۳ سفارش از ۳۸٬۰۶۳ سفارش سه‌ماهه را پوشش می‌دهد.
9. شماره سفارش و فاکتور Global Unique نیست؛ ترکیب سال مالی، DC و شماره سند
   یکتا است.
10. Crosswalk NGT در Line کامل‌تر از Header است: ۱٬۱۱۲٬۷۱۱ Line با ID/UUID
    سفارش منطبق، ۲۱۱٬۲۱۱ Header دارای Line منطبق و هفت Split Order وجود دارد.
11. PriceUniqueId در NGT Polymorphic است و میان صفر، tblPrice و tblCPrice
    تقسیم می‌شود؛ CPriceUniqueId جدیدتر پوشش دقیق‌تری دارد.

مرحله بعدی:

- استخراج موجودی، رزرو سفارش، حواله خروج و اثر انواع سند.
- بستن Transitionهای Status با Procedureهای تبدیل/توزیع و Golden Case.
- طراحی Idempotency و Event/Snapshot قرارداد مقصد.

## ۲۰۲۶-۰۸-۲۶ — قیمت، قیمت قراردادی، تخفیف و جایزه

وضعیت: **تأییدشده روی Clone فقط‌خواندنی**

منابع:

- `scripts/sql/extract_varanegar_pricing_discount_domain.py`
- `artifacts/varanegar_analysis/domains/pricing_discounts_prizes_20260826.json`
- `docs/varanegar_reconstruction/domains/06_PRICING_DISCOUNTS_AND_PRIZES_FA.md`

کشفیات کلیدی:

1. `tblPrice` تاریخچه قیمت کالا و `tblCPrice` موتور قیمت قراردادی مشروط‌اند؛
   این دو جایگزین هم نیستند.
2. در `۱۴۰۵/۰۶/۰۴` تعداد ۳٬۷۸۴ کالا Price و ۳٬۵۵۷ کالا CPrice مؤثر دارند.
   ۴۰ و ۲۶۷ کالا به‌ترتیب فاقد این پوشش‌اند.
3. از ۴۲٬۸۵۸ CPrice مؤثر، ۴۲٬۷۵۸ ردیف شرط نوع سفارش دارند و فقط دو ردیف
   کاملاً بی‌شرط‌اند. View عمومی قیمت فقط ۹۲ کالا را برمی‌گرداند و منبع کامل
   سفارش نیست.
4. `Priority` در CPrice از نوع Float با مقادیر کسری شبه‌ترتیبی است؛ مدل مقصد
   باید ترتیب Decimal/Integer پایدار و Golden Test داشته باشد.
5. از ۵٬۰۹۸ Rule تخفیف، فقط ۸۵۴ Rule در تاریخ Snapshot واقعاً مؤثرند؛ ۲٬۹۳۲
   Rule Flag فعال ولی تاریخ منقضی دارند. Flag بدون بازه تاریخ کافی نیست.
6. DisType ۳۰۰ در Stored Procedure رسمی Rule خطی و سایر خانواده‌های فعلی
   گروهی‌اند. PrizeTypeها تخفیف، Addition، تک‌جایزه، جایزه انتخابی، سبد و امتیاز
   را جدا می‌کنند.
7. ۱۹۸٬۱۷۹ اتصال کالا و ۵٬۰۷۹ اتصال جایزه وجود دارد. ۸۴۵ Rule نیز SQL شرطی
   دارند که نباید در وب‌ERP مستقیماً اجرا شود.
8. در سه ماه، تمام ۲۰۱٬۸۶۵ ردیف فروش معتبر CPriceRef دارند و ۳۰۰٬۳۶۱ اثر
   Rule از ۷۰۴ Rule روی ۲۹٬۰۵۳ فروش ثبت شده است.
9. جایزه‌های NGT همگی DisRef عددی معتبر دارند، اما ۶۷٬۱۵۰ ردیف UUID تخفیف صفر
   دارند؛ ID و UUID باید جدا و با وضعیت کیفیت Crosswalk نگهداری شوند.
10. ده Condition برای هشت Rule حذف‌شده وجود دارد؛ ۳۲ گروه Code تخفیف تکراری
    و ۱۳٬۷۸۰ بازه معکوس CPrice نیز بدهی مهاجرت‌اند.

مرحله بعدی:

- استخراج چرخه سفارش فروش، تأیید، تبدیل به فروش و Snapshot محاسبات.
- ساخت Golden Caseهای قیمت و تخفیف با حفظ Context واقعی سفارش.
- طبقه‌بندی امن الگوهای `SqlCondition` بدون ذخیره یا اجرای مستقیم آن‌ها.

## ۲۰۲۶-۰۸-۲۶ — طرف‌حساب، مشتری، تأمین‌کننده، پرسنل و نقش فروش

وضعیت: **تأییدشده روی Clone فقط‌خواندنی**

منابع:

- `scripts/sql/extract_varanegar_party_domain.py`
- `artifacts/varanegar_analysis/domains/parties_customers_suppliers_personnel_20260826.json`
- `docs/varanegar_reconstruction/domains/05_PARTIES_CUSTOMERS_SUPPLIERS_PERSONNEL_FA.md`

کشفیات کلیدی:

1. `dbo.Contact` ریشه مشترک ۴۴٬۸۲۹ مشتری، ۷۵ تأمین‌کننده و ۸۳۸ پرسنل است.
   Flag نقش‌ها با اتصال واقعی کاملاً سازگار است؛ ۲۹۱ Contact هیچ نقش فعلی ندارد.
2. هر ۴۴٬۸۲۹ مشتری UUID و Contact معتبر دارد. Crosswalk فعال NGT بر پایه
   `CustGUID` است؛ دو UUID تماس NGT با مشتری فعلی تطبیق ندارد.
3. فقط ۶۱۸ مشتری Main/Sub classification دارند، درحالی‌که Category و Activity
   برای همه کامل است. این سه Taxonomy مستقل‌اند.
4. از ۳۰٬۶۹۲ مشتری دارای مختصات، ۳٬۵۵۴ مختصات صفر و ۲۷٬۱۳۸ مختصات قابل
   استفاده‌اند. صفر نباید موقعیت معتبر تلقی شود.
5. در پنجره `۱۴۰۵/۰۳/۰۱..۱۴۰۵/۰۵/۳۱` تعداد ۳۰٬۱۷۱ مشتری حداقل سفارش، فروش
   یا تماس NGT داشته و ۱۴٬۶۵۸ مشتری بدون فعالیت بوده‌اند.
6. همه ۳٬۸۲۴ کالا از طریق ۳٬۹۱۵ اتصال به ۷۰ تأمین‌کننده وصل‌اند؛ Master
   تأمین‌کننده ۷۵ عضو دارد و ۵ عضو اتصال کالای فعلی ندارند.
7. پرسنل چندنقشی‌اند: ۱٬۴۶۱ انتساب شغلی جاری برای ۸۳۸ نفر و ۲۸۵ نفر با بیش
   از یک شغل جاری وجود دارد. نقش باید جدول رابطه‌ای زمان‌دار باشد.
8. `dbo.PDealer` Master شخص جدا نیست؛ View پرسنل است. از ۸۳۴ ردیف View فقط
   ۶۴۹ نقش فروش فعال دارد و دو فروشنده جاری به‌دلیل غیرفعال‌بودن Personnel در
   View فعال قرار نمی‌گیرند.
9. فیلدهای Credential قدیمی فقط به‌صورت شمارش تجمیعی بررسی شدند. هیچ مقدار
   Credential ذخیره نشد و مهاجرت مستقیم آن‌ها ممنوع است؛ Reissue/Reset لازم است.
10. تکرار تلفن/شناسه ملی فقط هشدار Reconciliation است و نباید Merge خودکار
    ایجاد کند.

مرحله بعدی:

- استخراج قیمت پایه، لیست قیمت، تخفیف، جایزه و شروط مشتری/کالا.
- ردیابی مالکیت مشتری میان SalePath، فروشنده و سرپرست.
- طراحی قرارداد Party/Role و Quarantine برای Contactهای بی‌نقش.

## ۲۰۲۶-۰۸-۲۶ — کالا، گروه، برند، بسته‌بندی و بارکد

وضعیت: **تأییدشده روی Clone فقط‌خواندنی**

منابع:

- `scripts/sql/extract_varanegar_product_catalog_domain.py`
- `artifacts/varanegar_analysis/domains/product_catalog_20260826.json`
- `docs/varanegar_reconstruction/domains/04_PRODUCT_CATALOG_FA.md`

کشفیات کلیدی:

1. ۳٬۸۲۴ کالا هم‌زمان در Taxonomy قدیمی GNR، طبقه‌بندی Main/SubType و درخت
   UUIDمحور NGT قرار دارند. این سه مدل جایگزین هم نیستند.
2. درخت GNR دارای ۱۷۰ گره و ۱۰ ریشه موضوعی است؛ درخت فعال NGT دارای ۹۹ ریشه
   تجاری/لاین و ۴۶۲ زیرگروه استفاده‌شده است. تمام کالاها اتصال معتبر Main/Sub
   دارند.
3. Brand و MainGroup NGT یک‌به‌یک نیستند: ۳۳ برند به چند MainGroup و ۱۹
   MainGroup به چند برند متصل‌اند؛ Crosswalk باید از خود کالا ساخته شود.
4. جدول طبقه‌بندی قدیمی ۱٬۳۳۵ ردیف برای ۱٬۱۸۰ کالای حذف‌شده دارد. این ردیف‌ها
   باید در Quarantine مهاجرت حفظ شوند، نه اینکه به Product فعلی FK شوند.
5. `GNR.tblPackage` تعداد ۸٬۲۳۸ تبدیل واحد معتبر برای همه کالاها دارد؛ بسته
   تخفیفی SLE با ۸ Header و ۳۶ Item مفهوم مستقلی است.
6. Barcode اصلی ۳٬۶۴۱ کالا پر است، اما ۲۸۶ مقدار بین کالاها تکرار شده، ۵۷
   مقدار Sentinel صفر و ۲۶ مقدار غیراستاندارد/خراب وجود دارد. Unique سراسری
   قبل از پاک‌سازی ممنوع است.
7. از ۱٬۲۱۶ CatalogProduct، تعداد ۱٬۱۹۹ با UUID کالا تطبیق می‌کند و ۱۷ ردیف
   Placeholder با UUID صفر است. `Number_ID` هیچ تطبیقی با Goods.ID ندارد.
8. در پنجره `۱۴۰۵/۰۳/۰۱..۱۴۰۵/۰۵/۳۱` تعداد ۲٬۳۳۶ کالا فعالیت داشته و ۱٬۴۸۸
   کالا بدون فعالیت بوده‌اند. `ShowInSale` به‌تنهایی تاریخچه فعالیت نیست.

مرحله بعدی:

- استخراج اشخاص، مشتریان، تأمین‌کنندگان و پرسنل و تعیین Person Master مشترک.
- ردیابی Runtime انتخاب Package/Barcode در فرم سفارش و POS.
- طراحی قرارداد Reconciliation برای Barcode و Crosswalk چندبه‌چند Brand/NGT.

## ۲۰۲۶-۰۸-۲۶ — واحدها، نوع حمل/انبار و انواع سند

وضعیت: **تأییدشده روی Clone فقط‌خواندنی**

منابع:

- `scripts/sql/extract_varanegar_units_documents_domain.py`
- `artifacts/varanegar_analysis/domains/units_stock_and_document_types_20260826.json`
- `docs/varanegar_reconstruction/domains/03_UNITS_STOCK_AND_DOCUMENT_TYPES_FA.md`

کشفیات کلیدی:

1. واحد فروش، واحد بسته‌بندی، واحد فیزیکی، نوع حمل، نوع کانال انبار، نوع سند
   انبار، نوع سفارش، نوع سند دفترکل و نوع مدرک پرسنلی قراردادهای مستقلی هستند
   و نباید در یک Type عمومی ادغام شوند.
2. از ۳٬۸۲۴ کالا، ۳٬۸۲۲ کالا Unit «عدد» دارند؛ PackUnit میان «کارتن» برای
   ۲٬۶۳۳ و «کارتن ۱» برای ۱٬۱۹۱ کالا تقسیم شده است. هیچ ارجاع Unit یا
   PackUnit یتیم نیست.
3. نوع حمل ۳ مقدار دارد: عادی، یخچالی و زیر صفر. ۳٬۸۲۰ کالا عادی و ۴ کالا
   زیر صفرند؛ نوع یخچالی فعلاً مصرف ندارد.
4. نوع انبار دو Encoding ناسازگار دارد: کد ترتیبی `0..4` در Lookup و Bit Flag
   `1,2,4,8,16` در FRU/عملیات. تابع `GNR.HasStockType` با فرمول
   `Power(2, Code-1)` نسبت به داده فعلی مشکوک است و نباید عیناً منتقل شود.
5. ۳۰ نوع سند انبار و ۶۰ نگاشت نوع سند/کانال ثبت شد. هشت ردیف پل برای کدهای
   ۳۵ و ۸۰ Lookup ندارند، اما هیچ سند تاریخی با این دو کد ثبت نشده است.
6. `dbo.DocumentType` برخلاف نام عمومی آن فقط هشت نوع مدرک هویتی/پرسنلی است؛
   انواع سفارش فروش (۲۳)، سند دفترکل (۷۸) و نگاشت بیرونی (۶۵) منابع جدا هستند.
7. در پنجره عملیاتی `۱۴۰۵/۰۳/۰۱..۱۴۰۵/۰۵/۳۱` تعداد ۱۲٬۲۶۲ سند انبار،
   ۳۸٬۰۶۳ سفارش و ۸۸۷ سند دفترکل ثبت شده است. مبنا Business Date است، نه
   CreatedDate مهاجرتی.

مرحله بعدی:

- استخراج کالا، برند، گروه کالا، Package و Barcode با حفظ تفاوت Unit/PackUnit.
- ردیابی مصرف Runtime تابع `GNR.HasStockType` و معنای `Selectable=2`.
- ساخت Crosswalk نسخه‌دار انواع سند برای مدل مقصد.

## ۲۰۲۶-۰۸-۲۶ — حوزه جغرافیا و مسیرها

وضعیت: **تأییدشده روی Clone فقط‌خواندنی**

منابع:

- `scripts/sql/extract_varanegar_geography_domain.py`
- `artifacts/varanegar_analysis/domains/geography_and_routes_20260826.json`
- `docs/varanegar_reconstruction/domains/02_GEOGRAPHY_AND_ROUTES_FA.md`

کشفیات کلیدی:

1. سلسله‌مراتب جغرافیایی رسمی `State → County → Area` است و ۳۱ استان، ۴۰
   شهرستان و ۶۹ Area دارد. برچسب دقیق UI برای `Area` هنوز باید از فرم رسمی
   تأیید شود.
2. مرکز عملیاتی `DC=1` به ۳۱ Area فعال در گیلان، البرز، تهران و قزوین وصل است؛
   همه Distance صفر دارند، پس مقدار صفر فعلی نباید فاصله واقعی تلقی شود.
3. مسیر فروش قدیمی دارای ۲ Zone، ۵ SaleArea و ۱۴۶ SalePath است؛ مسیرهای
   توزیع، وصول و فروش تلفنی در جداول GNR خالی‌اند.
4. از ۴۴٬۸۲۹ مشتری، ۴۲٬۴۶۲ مشتری State، ۴۰٬۹۲۵ مشتری Area و ۸٬۶۵۷ مشتری
   SalePath دارند. ستون‌های `CityZone` و `CityArea` قرارداد FK یا جدول مرجع
   اثبات‌شده ندارند.
5. مدل فعال NGT جداست: ۱۹۲ VisitTemplate فعال، ۲٬۵۵۰ Path فعال و ۸۷٬۹۳۵
   اتصال فعال Path/Customer برای ۳۷٬۲۴۸ مشتری ثبت شد.
6. `NGT.VisitTemplatePaths.Number_ID` نگاشت یک‌به‌یک قابل اتکا به
   `GNR.tblSalePath.ID` نیست؛ بیشتر ردیف‌های فعال مقدار صفر دارند و فقط ۲۴ شناسه
   متمایز با مسیر فروش قدیمی تطبیق پیدا کردند.
7. آزمون‌های این دامنه هیچ یتیم رسمی یا گروه کد تکراری در سلسله‌مراتب اصلی
   پیدا نکردند؛ بااین‌حال ۵۶۸ کاندید ارتباط ضمنی بدون FK ثبت شد.

مرحله بعدی:

- استخراج واحدهای سنجش، نوع انبار/ارسال و انواع سند.
- تعیین عنوان رسمی `Area` از منو/فرم یا قرارداد گزارش.
- جداسازی تحلیل تغییرات Master مسیر از تحلیل اجرای واقعی تور و ویزیت.

## ۲۰۲۶-۰۸-۲۶ — حوزه سازمانی و سال مالی

وضعیت: **تأییدشده روی Clone فقط‌خواندنی**

منابع:

- `scripts/sql/extract_varanegar_org_domain.py`
- `artifacts/varanegar_analysis/domains/organization_and_fiscal_year_20260826.json`
- `docs/varanegar_reconstruction/domains/01_ORGANIZATION_AND_FISCAL_YEAR_FA.md`

کشفیات کلیدی:

1. هسته سازمانی فعلی از مرکز توزیع، دفتر فروش، انبار و جدول پل سه‌طرفه ساخته
   شده است؛ این مفاهیم نباید در مدل جدید در یک «شعبه» ادغام شوند.
2. دو مدل سال وجود دارد: `GNR.tblAccYear` برای سال عملیاتی و
   `dbo.FiscalYear` برای سال مالی/دفترکل. شناسه‌های آن‌ها قابل جایگزینی با هم
   نیستند.
3. سه ردیف `dbo.DCFiscalYear` به `DCId=0` (ستاد مرکز) وصل‌اند، ولی ده انبار و
   ده پل دفترفروش/انبار به `DCRef=1` وصل‌اند.
4. برای هشت جدول این مرحله ۲۱۶ ارتباط FK رسمی و ۲۲۷۸ مصرف‌کننده ماژولی ثبت شد.
   همچنین ۵۳۰ ستون نام‌مشابه بدون FK رسمی وجود دارد که باید دامنه‌به‌دامنه
   تعیین تکلیف شوند.
5. هیچ جدول پایه پرشده‌ای که با اطمینان «شرکت» باشد هنوز اثبات نشده است؛ مدل
   تک‌شرکتی ضمنی یک فرضیه است، نه نتیجه نهایی.

مرحله بعدی:

- تعیین معنای `DC=0` و `DC=1` در اسناد واقعی.
- استخراج حوزه جغرافیا، `GNR.tblArea` و وابستگی ۳۱ ناحیه به مرکز عملیاتی.
- تحلیل تاریخ‌محور استفاده از انبارها و مراکز در سه ماه گذشته روی منبع مجاز.

## ۲۰۲۶-۰۸-۲۷ — اصلاح قرارداد `DistPath` توزیع

وضعیت: **تأییدشده روی Clone فقط‌خواندنی و IL بستهٔ Deploy‌شده**

منابع:

- `scripts/sql/extract_varanegar_distribution_path_diagnostic_contract.py`
- `artifacts/varanegar_analysis/ui/varanegar_distribution_path_diagnostic_contract_20260827.json`
- `docs/varanegar_reconstruction/DISTRIBUTION_PATH_RUNTIME_DIAGNOSTIC_20260827_FA.md`

کشفیات کلیدی:

1. فرض قبلی «۲۶٬۰۸۶ Distribution بدون Path master یعنی Orphan» رد شد؛ ستون
   `SLE.tblDist.DistPath` هیچ FK رسمی ندارد.
2. `CreateDist` پارامتر عددی را مستقیم ذخیره می‌کند و Master مسیر را نمی‌خواند.
3. فرم در Lookup مقدار `DistPathTreeNo` را ذخیره می‌کند، نه `ID`.
4. مقادیر فعلی `DistPathingType=0` و `DistLimitType=0` Branch ورود عدد آزاد را
   فعال می‌کنند؛ این با خالی‌بودن Zone/Area/Path سازگار است.
5. هفت کد در ۲۶٬۰۸۶ Header و پنج کد در ۳٬۳۷۹ Header سه‌ماهه دیده شد؛ کد ۵
   با ۱۲۰ ردیف اخیر ثابت می‌کند فیلد دوحالته نیست.
6. ریسک واقعی مهاجرت، نسبت‌دادن ID/Label/Route حدسی است. عدد، Mode و Provenance
   باید حفظ و Label فقط با Crosswalk معتبر افزوده شود.

محدودیت: معنای انسانی کدها هنوز از دادهٔ فعلی معلوم نیست؛ ممکن است شماره مسیر،
نوبت حرکت یا قرارداد داخلی دیگری باشد و باید از منبع معتبر کسب‌وکار تأیید شود.

## ۲۰۲۶-۰۸-۲۷ — اصلاح قرارداد مبلغ برگشت فاکتور

وضعیت: **تأییدشده روی Clone فقط‌خواندنی و IL بستهٔ Deploy‌شده**

منابع:

- `scripts/sql/extract_varanegar_sales_return_amount_diagnostic_contract.py`
- `artifacts/varanegar_analysis/ui/varanegar_sales_return_amount_diagnostic_contract_20260827.json`
- `docs/varanegar_reconstruction/SALES_RETURN_AMOUNT_DIAGNOSTIC_20260827_FA.md`

کشفیات کلیدی:

1. فرض قبلی «۶۹۶ برگشت فعال دارای مغایرت مبلغ» رد شد؛ مقایسه اشتباهاً Net
   سربرگ را با Gross قلم می‌سنجید.
2. قرارداد رسمی `AmountNut = Amount - Discount + AddAmount` و
   `Header.TotalAmount = Σ AmountNut` است.
3. `Discount` و `AddAmount` نیز دقیقاً از اجزای تفصیلی خود Rollup می‌شوند؛
   Tax/Charge در فرمول AmountNut وارد نمی‌شوند.
4. برای هر ۱۴٬۰۹۱ Header، Residual خالص ذخیره‌شده و محاسبه‌شده، فرمول قلم و
   Rollup اجزا صفر است؛ همین نتیجه در سه ماه اخیر نیز برقرار است.
5. اختلاف تجمعی Gross و Net برابر ۲۰٬۷۲۶٬۲۴۵٬۸۵۸ و تعدیل توضیح‌پذیر تجاری است.
6. مقصد باید Bridge ناخالص تا خالص و Provenance اجزا را حفظ کند و فقط نقض
   Invariant رسمی را Quarantine کند.

محدودیت: Snapshot فعلی Editهای میانی تاریخچه یا Branch دقیق هر کاربر را ثابت
نمی‌کند؛ Runtime rounding/config drift همچنان باید با Golden case پایش شود.

## ۲۰۲۶-۰۸-۲۷ — اصلاح قرارداد تسویه‌ی Cross-customer چک برگشتی

وضعیت: **تأییدشده روی Clone فقط‌خواندنی، SQL رسمی و IL موجود**

منابع:

- `scripts/sql/extract_varanegar_returned_cheque_cross_customer_diagnostic_contract.py`
- `artifacts/varanegar_analysis/ui/varanegar_returned_cheque_cross_customer_diagnostic_contract_20260827.json`
- `docs/varanegar_reconstruction/RETURNED_CHEQUE_CROSS_CUSTOMER_DIAGNOSTIC_20260827_FA.md`

کشفیات کلیدی:

1. فرض قبلی «۴۹ اختلاف Customer نیازمند Approval موردی است» رد شد؛ ۴۹/۴۹ ردیف
   به Allocation اولیه‌ی دقیق همان `Cheque + Sale + Customer` وصل‌اند.
2. از ۴۹ ردیف، ۴۸ ردیف Saleدار با Customer فاکتور برابرند و هیچ مورد با مالک
   چک برابر نیست؛ مالک چک و Customer تخصیص دو نقش مستقل‌اند.
3. ۳۱ Pair ناشناس Cheque/Sale/Customer وجود دارد: ۲۷ کامل، چهار جزئی و
   Over-settlement صفر.
4. `Usp_CheckRemRetChequeRef` و لیست رسمی تسویه، مانده را در سطح
   `RetChequeRef + SaleRef` کنترل می‌کنند؛ Check فقط در سطح چک نادرست است.
5. مسیرهای `Usp_CreatePaymentsFromOthersCust` و Parent-customer پایه‌های مرتبط
   را عمداً می‌سازند و Provenance را نگه می‌دارند.
6. `ManualCustRef` فقط در دو مورد با Customer تسویه برابر است و مرجع Repair یا
   Allocation نیست.

محدودیت: دلیل متنی اپراتور و اجرای دقیق هر رکورد تاریخی از Aggregate/Static code
قابل اثبات نیست؛ آخرین Bucket فعلی `1404/12` است. Review فقط برای تخصیص مفقود،
ناسازگاری Sale/Customer، بیش‌تسویه یا پایهٔ حسابداری شکسته لازم است.

## ۲۰۲۶-۰۸-۲۷ — اصلاح Pay authority و کشف شکاف LegalType چک دریافتی

وضعیت: **PASS؛ Clone فقط‌خواندنی، SQL رسمی؛ اجرای Command صفر**

- هر ۸ چک وضعیت ۷ با Master PayId تهی، History PayId2 معتبر و Pay تأییدشده
  دارند؛ Orphan و Conflict صفر است. برداشت «Pay link مفقود» رد شد.
- `Pay2` و لیست رسمی واگذاری، مرجع Draft را از Master و مرجع Approved را از
  History می‌خوانند؛ مقصد باید این دو فاز را جدا نگه دارد.
- ۳۵ چک وضعیت ۹ LegalType نامشخص و ۱۸ مورد نوع ۲ دارند. PersonnelId در هر دو
  گروه موجود است و برای Imputation معتبر نیست.
- مسیر تأیید گروهی `LegalType` را در Parent ذخیره می‌کند ولی در فراخوانی
  `DoRCheque_AddRChequeHistory` آن را منتقل نمی‌کند. اثر تاریخی دقیق این نقص از
  Snapshot قابل تعیین نیست و Source نباید دستکاری شود.
- Artifact و Runbook بازتولیدپذیر با شناسه‌های `RCL-001..005` ثبت شد.

## ۲۰۲۶-۰۸-۲۷ — اصلاح معنای ۱۵۵ برگ Used بدون چک پرداختنی جاری

وضعیت: **PASS؛ Clone فقط‌خواندنی و SQL رسمی؛ اجرای Command صفر**

- ۴٬۸۲۷ برگ Used دقیقاً به ۴٬۶۷۲ برگ متصل به PCheque و ۱۵۵ برگ unlinked
  تجزیه می‌شوند؛ reuse/orphan در چک جاری صفر است.
- هر ۱۵۵ مورد لینک Transfer/Archive/RPTransfer صفر، متن زمینه صفر و پراکندگی
  در ۲۳ دفترچه فعال دارند.
- Procedure ذخیره‌ی نگهداری برگ `IsUsed` را مستقیم می‌پذیرد و BeforeSave فقط
  unmark برگ مصرف‌شده در PCheque/Transfer را منع می‌کند؛ پس حالت unlinked رسمی است.
- نبود Actor/ModifiedDate و متن زمینه اجازه نمی‌دهد منشأ تاریخی هر ردیف «دستی»
  اعلام شود. State مقصد `SOURCE_USED_UNLINKED/UNKNOWN_SOURCE` است.
- Artifact و Runbook با یافته‌های `PCL-001..004` ثبت شد؛ پاک‌کردن یا ساخت چک
  مصنوعی ممنوع است.

## ۲۰۲۶-۰۸-۲۷ — تشخیص Fork وضعیت سند حسابداری

وضعیت: **PASS؛ Clone فقط‌خواندنی و SQL رسمی؛ اجرای Command صفر**

- ۱٬۰۹۴ Pointer معتبر اما غیرآخرین‌اند؛ ۱۴٬۹۴۶ History event بعد از Pointer
  باقی مانده و ۱٬۰۹۱ سند Branch با وضعیت متفاوت دارند.
- ۱٬۰۹۰ Pointer رخداد اول را نگه داشته‌اند؛ همه‌ی موارد Manual و بدون External
  voucher link هستند. ۱٬۰۸۳ آخرین رخداد وضعیت ۲ و ۱۱ مورد وضعیت ۱ دارد.
- Read model رسمی Pointer را Current می‌داند، اما شماره‌گذاری اختلاف با آخرین
  History را صریحاً رد می‌کند؛ پس اختلاف operationally material است.
- `Get_ChangeVoucherStatus` Insert event و Update pointer را Transactional انجام
  می‌دهد، اما CATCH Rollback صریح ندارد. این Root-cause candidate است، نه اثبات
  تاریخی برای هر سند.
- Migration state برابر `CURRENT_POINTER_HISTORY_FORK/UNKNOWN_OUTCOME` است؛
  MAX/Delete ممنوع و Accountant disposition الزامی شد.

## ۲۰۲۶-۰۸-۲۷ — اصلاح معنای سند فعال بدون قلم

وضعیت: **PASS؛ Clone فقط‌خواندنی و SQL رسمی؛ اجرای Command صفر**

- تنها Header فعال بدون Item، Manual، نوع ۵۹، Current/only status برابر Draft،
  بدون External link و با Debit/Credit صفر است؛ فساد Posted نیست.
- VoucherNo منبع دارد، ولی `DoVoucher_SetVoucherNo` نبود Item را صریحاً رد
  می‌کند؛ شماره باید Provenance بماند و پیش از reuse تصمیم حسابدار داشته باشد.
- Save می‌تواند Itemهای غایب را حذف و سند نامعتبر موقت را Draft کند و فراخوانی
  بازشماری مسیر دستی Comment است؛ Root-cause candidate، نه علت تاریخی قطعی.
- State مقصد `DRAFT_EMPTY_NUMBERED_SHELL/UNKNOWN_SOURCE` و Line مصنوعی ممنوع شد.

## ۲۰۲۶-۰۸-۲۷ — تفکیک دو وضعیت Crosswalk برگشت NGT

وضعیت: **PASS؛ Clone فقط‌خواندنی و Catalog SQL؛ اجرای Command صفر**

- دو Header/Line فعال NGT هر دو بدون RetOrder/RetSale جاری‌اند، اما فقط یکی
  نتیجه‌ی دقیق UUID/Ref در `TourHistory` دارد؛ دیگری هیچ Result تاریخی ندارد.
- مورد اول `HISTORICAL_RESULT_CURRENT_TARGET_MISSING` و مورد دوم
  `PENDING_OR_UNATTEMPTED` شد؛ طبقه‌بندی قبلی «دو Pending» اصلاح گردید.
- FKهای SLE به `FRU.CustomerCallReturns.Id` عددی اشاره دارند، نه UUID مدل NGT؛
  Join مستقیم ممنوع و هویت‌های FRU/NGT باید مستقل بمانند.
- `NGT_DoReplicateTour` Commit نتیجه را پیش از Write-back Crosswalk Line انجام
  می‌دهد؛ Failure window مادی است ولی علت تاریخی غیبت هدف را به‌تنهایی ثابت نمی‌کند.
- Net Header/Line برابر و Orphan صفر است. اختلاف `CurrentQty` با جمع ساده Detail
  تا حل Unit/ConvertFactor فساد تلقی نمی‌شود؛ مسیر deployed از Detail.Qty می‌خواند.
- Artifact و Runbook بازتولیدپذیر
  `NGT_RETURN_CROSSWALK_DIAGNOSTIC_20260827_FA.md` ثبت و ساخت
  RetOrder/RetSale مصنوعی ممنوع شد.

## ۲۰۲۶-۰۸-۲۷ — رد هشدار Receipt-only خرید با Component N:M

- مقایسه‌ی قبلی per-invoice پنج گروه Receipt-only در دو فاکتور نشان می‌داد.
- یک رسید به دو فاکتور وصل است؛ هر پنج گروه از فاکتور دیگر همان Component می‌آیند.
- ۳٬۶۸۹ Relation به ۳٬۴۲۵ Component تبدیل شد؛ ۳۰٬۰۹۶ گروه Component/Goods دقیق
  و Receipt-only، Invoice-only و Quantity residual همگی صفر شدند.
- `ICA.usp_ApplySupInvoice` نیز Invoice list و Voucher list را جمعی بر Goods
  می‌سنجد؛ پس Relation N:M باید حفظ و پنج Item مالی مصنوعی ساخته نشود.
- سند `SUPPLIER_RECEIPT_COMPONENT_DIAGNOSTIC_20260827_FA.md` و Extractor
  بازتولیدپذیر ثبت شد؛ Procedure یا Write اجرا نشد.
- هفت Goods بدون Source مستقیم در سه Supplier return هستند؛ هر هفت با خروج نوع
  ۵۵ دقیق و دارای Price/Amount غیرصفرند. IL ثابت کرد Item authority سند انبار و
  Invoice فقط Hint اختیاری Source/Price است؛ State به
  `OPTIONAL_SOURCE_ITEM_ABSENT_NOT_AN_INVENTORY_ERROR` اصلاح و Reprice/Reassign
  حدسی ممنوع شد.

## ۲۰۲۶-۰۸-۲۷ — اثبات شکاف Blocking در Validator برگشت تأمین‌کننده

وضعیت: **PASS؛ Clone فقط‌خواندنی و هفت Module SQL؛ اجرای Command صفر**

- ۱۵۶ گروه سندی `(Return,Goods)` به ۱۱۵ گروه تجمعی `(SupInvoiceRef,Goods)` در
  Grain واقعی Validator تبدیل می‌شوند؛ در هر دو دید هفت Goods با قلم منبع Match
  نمی‌شوند. در گروه‌های تجمعی Match‌شده Over-return تعداد/جایزه و اختلاف مبلغ
  برگشت کامل فعلاً صفر است.
- سمت Source ظاهراً Line-level است، اما Unique index رسمی `(HdrRef,GoodsRef)`
  و Duplicate جاری صفر، برابری آن با Grain کالا را تضمین می‌کند؛ این مورد Risk
  جدید نیست، ولی Invariant مقصد باید حفظ یا با تجمیع صریح جایگزین شود.
- Validator با `INNER JOIN` فقط Matchها را کنترل و Goodsهای غایب را حذف می‌کند؛
  Check صریح Unmatched ندارد و برای Source تهی زود Return می‌کند.
- Save جدید SDSNET در INSERT پس از Write آن را صدا می‌زند اما Return code را
  نمی‌گیرد و پیام را به `RAISERROR` تبدیل نمی‌کند؛ مسیر UPDATE آن را صدا نمی‌زند.
- Desktop متفاوت است: IL مرتب SaveCommand نشان می‌دهد پیام غیرخالی به
  `ValidationFailure`، Dispose و خروج پیش از `DataContext.Commit` می‌رسد؛ ولی
  همان Validator با `INNER JOIN` هنوز Goodsهای Unmatched را نمی‌بیند.
- Binding کامل Desktop→Business→DataAccess→`SLE.usp_CheckRetSupInvoice` با
  Hash دقیق هر سه Assembly و `DataContext.Execute` اثبات شد؛ Name matching نیست.
- پنج گروه مسیر جدید و دو گروه Legacyِ Source-item-absent همگی Price/Amount
  غیرصفر دارند؛ Grid فقط Numeric بودن Price/Amount را کنترل می‌کند. منشأ تاریخی
  مقدار معلوم نیست و «دستی» نام‌گذاری نشد.
- سه Writer قیمت اثبات شد: Legacy/Desktop پارامتر Price را ذخیره می‌کند، SDSNET
  آن را از Temp payload کپی می‌کند و Import رسمی `usp_Convert_RetSupInvoice2`
  از UnitPrice و `Qty×UnitPrice` می‌سازد. نبود creation-path marker اجازهٔ
  انتساب هفت مورد جاری به هیچ‌یک را نمی‌دهد.
- Transaction/Catch/Rollback در Save هست، ولی Control flow فعلی خطای Validator
  را به Exception مسدودکننده تبدیل نمی‌کند. هیچ Save برای اثبات این نتیجه اجرا نشد.
- شرط Toll نیز ItemRef را با Header ID می‌سنجد؛ این Defect فیلتر Static است و
  ۲۰ Explicit TollRef قدیمی را نمی‌بیند. هر ۲۰ متعلق به یک Header هستند، Ref
  جهانی‌شان غایب است، اما با Same-header TollRef به‌طور یکتا Resolve و در View
  سازگاری رسمی دیده می‌شوند؛ Unresolved/Ambiguous/Omitted صفر است.
- شاخه UPDATE SDSNET از `@HdrId` مقدارنگرفته برای Allocation جدید استفاده و Ref
  موجود را Retarget نمی‌کند؛ Defect واقعی است، اما Header دارای ۲۰ Ref قدیمی
  `IsNew=0` است. بنابراین این مسیر علت تاریخی آن ۲۰ مورد اعلام نشد.
- Risk بحرانی `R-046`، تعداد کل ریسک‌ها را به ۴۶ و Assignmentها را به ۱۷۵ رساند.
- Permission مسیر جدید Nodeهای 826001/2/3 را چک می‌کند ولی DC/AccYear را به
  Authorizer نمی‌فرستد؛ Final-date خرید SysRef=5 را با سال و بدون DC می‌خواند.
- Required-Goods check به‌اشتباه کل جدول Item را بدون Header scope می‌سنجد؛
  Snapshot جاری صفر ردیف Goods تهی دارد، پس Defect فعلاً Save سراسری را نبسته است.
- پروفایل سه‌ماهه نشان داد هر ۵۰ Header و ۳۹۳ قلم مرجوعی از مسیر `IsNew=1`
  آمده‌اند؛ مسیر Legacy صفر، Source-linked Header یک، Source-item-absent group
  پنج و Explicit TollRef قدیمی صفر است. بنابراین شکاف Validator مسیر جدید
  Operationally current است، ولی ۲۰ TollRef ناسالم موجود Historical/Legacy است.

## ۲۰۲۶-۰۸-۲۸ — مسیر واقعی ساخت سند، Atomicity و Drift سیاست صدور

وضعیت: **۴ PASS و ۱ FAIL در ماتریس Verification؛ هیچ Command عملیاتی اجرا نشد**

- Binding قبلی که فقط کاندیدهای نامی SQL داشت به مسیر دقیق Hash-pinned تبدیل شد:
  `FormExternalVoucher.DoWorkSave -> ExternalVoucherHeaderHandler.DoExternalVoucher
  -> ExternalVoucherHeaderAdapter.DoExternalVoucher -> dbo.usp_DoExternalVoucher
  -> dbo.usp_DoPreVoucher`.
- مسیر فعلی فرم به `DoExternalVoucher_Create` نمی‌رود؛ آن رویه و شاخه
  `DoExternalVoucher_Create_With_PreVoucher` جایگزین/Legacy هستند.
- فرم DataContext را `null` می‌فرستد؛ Business مقدار `Transaction.Begin=0` را
  می‌سازد. Provider پیش از Query تراکنش DB را آغاز، Command را به آن متصل، پس
  از تکمیل Adapter Commit و در Finally Dispose می‌کند. Atomicity Desktop ثابت
  شد؛ خود `usp_DoExternalVoucher` هیچ Transaction/TRY/CATCH ندارد و Caller مستقیم
  همچنان اثبات‌نشده است.
- تمام ۲٬۳۷۰٬۵۶۹ PreVoucher line متصل و Marked هستند؛ Header بدون Line، Orphan،
  عدم تراز و Header/Line amount mismatch در کل Snapshot و سه‌ماهه صفر است.
- Unique index کامل Signature خط فعال و Duplicate دقیق صفر است. Anti-join Source/DC
  قرارداد Snapshot immutable است، نه Repair/Upsert خط‌به‌خط.
- هر ۱۱ Creator فعال پنج ستون پایه را case-insensitive دارد؛ ۱۴۹ Article شامل
  Ruleهای Debit/Credit و Dimension fingerprint شد. Structural contract PASS است،
  ولی Golden parity مالی هر Creator هنوز اجرا نشده است.
- کشف اصلی: سال ۱۴۰۵ اکنون `ExternalVoucherIssueMode=1` دارد، اما ۳۶۶ از ۳۸۲
  Header چند Source دارند. در سه ماه منتخب ۲۷٬۱۷۷ Source group فقط در ۲۰۴ Header
  قرار گرفته است. هر ۲۰۴ Header دقیقاً یک تاریخ/نوع/DC/SaleOffice دارد؛ شکل با
  Mode 2 روزانه سازگار است. بنابراین Current config تاریخچه را بازتولید نمی‌کند؛
  تغییر Config از تغییر Procedure قدیمی قابل تفکیک نیست و زمان/Actor نامعلوم است.
- Risk بحرانی `R-047` ثبت شد: ERP مقصد باید Policy version immutable را روی هر
  Batch Snapshot کند، تاریخچه را با Current config Replay نکند و Transaction
  owner را در Command سمت Server قرار دهد.
- Risk register اکنون ۴۷ Risk باز، ۲۵ Critical، ۱۹ High و ۳ Medium دارد؛
  Traceability به ۱۷۹ Assignment و ۴۷ Risk یکتا به‌روز شد.
- چهار Creator دارای فعالیت سه‌ماهه در هر سه لایه PreVoucher/External/Journal
  Line/Header/Amount parity دقیق دارند؛ هفت Creator بی‌نمونه نیازمند Golden case‌اند.
- Artifact، Extractor، سند دامنه ۱۹ و Testهای تازه ثبت شد.

## ۲۰۲۶-۰۸-۲۸ — چرخهٔ Confirm/Delete/Transfer سند خارجی

وضعیت: **Binding و تراکنش سه فرمان PASS؛ State نهایی PASS؛ Validation purity FAIL**

- مسیرهای UI→Business→DataAccess→SQL برای Confirm/Unconfirm، Delete و Transfer
  با همان چهار Assembly Hash-pinned اثبات شد. UI در همه مسیرها Context را `null`
  می‌دهد و Business `Transaction.Begin`، Commit و Finally Dispose دارد.
- خود سه Procedure هیچ `BEGIN TRAN/COMMIT/ROLLBACK` ندارند؛ بنابراین Caller
  غیرDesktop همچنان Atomicity اثبات‌شده ندارد.
- Confirm تراز را می‌سنجد، Unconfirm سند منتقل‌شده را رد و پس از Update کنترل
  Concurrency می‌کند. Procedure Triggerهای Header را موقتاً سراسری Disable می‌کند.
- Delete فقط Batch تأییدنشده/ارسال‌نشده را می‌پذیرد و PreVoucher، Relationها،
  External line و Header را با هم حذف می‌کند. پس immutability PreVoucher فقط تا
  بقای Batch است و Reissue بعد از Delete رسمی ممکن می‌شود.
- Transfer، Voucher/Item/StatusHistory/EditLog/SetVoucherNo را می‌سازد و خطاهای
  SQL را Raise می‌کند؛ اما `SetVoucherNo` مانده را **پیش از** Validator پاک می‌کند.
  Validator خطای کسب‌وکار را با Result+RETURN عادی برمی‌گرداند، بنابراین Cleanup
  قبلی می‌تواند در Business Commit شود. این نقض Validation purity است.
- کل Clone ۱۹۷٬۵۱۸ Header دارد: همگی Confirmed، دقیقاً یک Voucher فعال و دقیقاً
  یک SetVoucherNo دارند؛ Orphan/Duplicate/Multiple-active صفر است. پنجرهٔ سه‌ماهه
  نیز ۲۰۴/۲۰۴ یک‌به‌یک است. پس Defect مسیر کد اثبات شده، ولی خرابی ماندگار فعلی
  مشاهده نشده است.
- Risk `R-048` با Severity بالا ثبت شد. Risk register اکنون ۴۸ Risk باز، ۲۵
  Critical، ۲۰ High و ۳ Medium دارد؛ Traceability برابر ۱۸۱ Assignment و ۴۸
  Risk یکتا است.
- سند دامنه ۲۰، Artifact توسعه‌یافته، Extractor بازتولیدپذیر و ۱۴ Test متمرکز
  ثبت شد؛ هیچ Command عملیاتی اجرا نشد.

## ۲۰۲۶-۰۸-۲۸ — پوشش Rule و Grain تاریخی قلم حسابداری

وضعیت: **Parity مالی کل تاریخچه PASS؛ پوشش Rule و Replay با Grain جاری FAIL**

- هر ۱۱ Creator فعال در تاریخچه نمونه دارد و Header/Amount در هر سه لایه
  PreVoucher/ExternalVoucher/Journal دقیقاً Reconcile می‌شود؛ External line و
  Journal line نیز یک‌به‌یک‌اند.
- از ۱۴۹ Rule فعال فقط ۱۰۱ Rule در کل Snapshot اجرا شده‌اند؛ ۴۸ Rule هیچ نمونه
  تاریخی و ۱۱۸ Rule هیچ نمونه سه‌ماهه ندارند. نبود نمونه به معنی Obsolete نیست و
  برای ۴۸ Branch Golden case مصنوعی الزامی شد.
- ۲٬۳۷۰٬۵۶۹ PreVoucher line به ۱٬۲۸۷٬۸۷۴ قلم رسمی تبدیل شده‌اند؛ ۱٬۰۸۲٬۶۹۵
  Stage line در ۹٬۶۲۴ گروه تجمیع و بیشینه گروه ۶٬۲۵۷ line است.
- Cardinality واقعی هر ۱۱ Creator دقیقاً با Grain معادل
  `DoExternalVoucher_Create_With_PreVoucher`—Header/Date/Article/Dimensions/Comment
  بدون ReferenceNo و debit-side—برابر است.
- Grain `usp_DoExternalVoucher` فعلی از همان تاریخچه ۱٬۴۲۴٬۰۳۹ قلم می‌سازد؛
  ۱۳۶٬۱۶۵ قلم بیشتر. فقط ۸ Creator از ۱۱ در هر دو Grain برابرند. بنابراین Replay
  با کد جاری حتی با Total مالی برابر، ساختار رسمی اقلام را تغییر می‌دهد.
- این شاهد معنای تاریخی معادل را ثابت می‌کند، نه نام Procedure یا زمان نسخه‌ای که
  هر Batch را ساخته است. `R-047` به LineGroupingPolicyVersion و حفظ Stage→Line
  crosswalk گسترش یافت.
- Artifact و Extractor به Coverage ordinal و دو Grain توسعه یافت و ۱۷ Test
  متمرکز PASS شد؛ دادهٔ ردیفی یا Command عملیاتی استفاده نشد.

## ۲۰۲۶-۰۸-۲۸ — مجوز عملیاتی و Scope چرخهٔ سند خارجی

وضعیت: **Scope خواندن و Finality صدور PASS؛ مجوز مستقل پنج عمل حساس FAIL**

- دامنهٔ IL به شش DLL Hash-pinned شامل قالب پایه و UIComponent صدور گسترش یافت؛
  Assemblyها فقط Parse شدند و Load/Execute نشدند.
- گرید سند با `AccYear` و `DC` نشست Scope می‌شود و صدور، بازهٔ سال مالی و تاریخ
  نهایی هر سیستم منبع را پیش از Write کنترل می‌کند؛ این دو Guard با مجوز Action
  یکی نیستند.
- Permission gate قالب پایه New/Edit/Delete/Print/Excel را پوشش می‌دهد، ولی
  Confirm/Unconfirm/Transfer را نه. Override فرم New/Edit/View را پنهان و
  Confirm/Unconfirm را Visible می‌کند؛ Save و Transfer سفارشی اتصال Permission
  مشاهده‌شده ندارند.
- در متدهای صدور، Confirm، Unconfirm، Delete و Transfer صفر فراخوانی Permission
  و در چهار Procedure عملیاتی صفر کنترل authorization/resource scope یافت شد.
  صدور وجود User/DC را می‌سنجد ولی رابطهٔ مجاز User→DC را نه؛ Delete Actor ندارد.
- این نتیجه نبود Gate کلی منو را ثابت نمی‌کند؛ نتیجهٔ محدود اما مهم این است که
  دسترسی صفحه، مجوز مستقل Command نیست و پس از رسیدن Principal به مسیر استاندارد،
  کنترل action/scope سمت Server پیدا نشد.
- `R-049` بحرانی ثبت شد. Risk register اکنون ۴۹ ریسک باز شامل ۲۶ Critical، ۲۰
  High و ۳ Medium است؛ Traceability همهٔ ۴۹ ریسک را در ۱۸۴ Assignment پوشش می‌دهد.
- Artifact بازتولید شد، سند دامنهٔ ۲۰ و ماتریس‌ها به‌روز شدند و ۱۸ تست اختصاصی
  به‌همراه دو تست Risk/Traceability PASS شد؛ هیچ Command عملیاتی اجرا نشد.

## ۲۰۲۶-۰۸-۲۸ — مرز تاریخ قطعی صدور و پوشش ناقص خرید

وضعیت: **Finality pre-mutation PASS؛ completeness خرید و شاهد استثنای حقوق FAIL**

- `usp_DoExternalVoucher` برای Cross product تمام نوع‌های سند و DCهای انتخابی،
  Finality را قبل از `usp_DoPreVoucher` و هر Write پایدار کنترل می‌کند. Error
  به‌شکل Result+RETURN است، اما چون پیش از Mutation است Commit بیرونی اثر جزئی
  ندارد.
- سیستم‌های غیرخرید از `GNR.tblOprDate.LastDate` با کلید
  `OperationId+DC+AccYear` استفاده می‌کنند. Duplicate کلید موجود صفر است و نبود
  کامل ردیف برای سیستم غیرمستثنا Fail-closed می‌شود.
- خرید `MIN(ICA.tblICAOprDate.DefeniteDate)` را فقط روی ردیف‌های موجود StockDC
  می‌گیرد و Anti-join completeness ندارد. برای سال ۱۴۰۵ Scope دارای انبار، ده
  StockDC و هشت Operation row دارد؛ دو ردیف مفقود برای `MIN` نامرئی‌اند. شکل
  جزئی در هر سه سال ۱۴۰۳ تا ۱۴۰۵ دیده شد.
- `OperationId=5` صریحاً مستثناست؛ دو نوع حقوق و دو Creator تنظیم شده‌اند، ولی
  صفر Line/Header تاریخی دارند. Intent ممکن است معتبر باشد، اما بدون Golden
  case و تأیید مالک قابل پورت نیست.
- ۳۸۲ Header مسیر جدید فقط فروش/خزانه‌اند و با Finality فعلی صفر Failure دارند؛
  Header جدید خرید نگه‌داری نشده، بنابراین اثر تاریخی شکاف خرید ادعا نشد.
- `R-050` بحرانی افزوده شد. دفتر ریسک اکنون ۵۰ ریسک باز، ۲۷ Critical، ۲۰ High
  و ۳ Medium دارد؛ Traceability برابر ۱۸۸ Assignment و ۵۰ ریسک یکتا است.
- Artifact به schema 2 ارتقا یافت، سند دامنهٔ ۲۱ و تست نوزدهم افزوده شد؛ هیچ
  Procedure عملیاتی یا Creator view اجرا نشد.

## ۲۰۲۶-۰۸-۲۸ — Result protocol، توقف زنجیره و Policy preflight

وضعیت: **زنجیرهٔ سه‌مرحله‌ای و پیام‌ها PASS؛ Snapshot اتمیک Policy FAIL**

- DLL مشترک نیز Hash-pinned شد و Enum دقیق Save استخراج شد: `Issue=1`،
  `IssueAndConfirm=2` و `IssueAndConfirmAndSend=3`.
- SQL نوع پیام `0=created header id`، `1=business error`، `2=warning` و
  `3=information` را برمی‌گرداند. Business فقط نوع ۱ را Validation error می‌کند
  و UI فقط نوع ۰ را به Header ID تبدیل می‌کند.
- IL فرم ثابت کرد Validation failure صدور پیش از Confirm و Validation failure
  Confirm پیش از Transfer `return` می‌کند؛ Transition بعدی روی خطا اجرا نمی‌شود.
- Business Result را پیش از Commit تنظیم می‌کند و Result نوع ۱ را نیز Commit
  می‌کند. در Procedure صدور فعلی تنها type-1 نتیجهٔ Finality و پیش از اولین
  Mutation پایدار است، پس این شاخه امن است؛ Contract مقصد باید Rejected را
  non-committing و typed کند.
- Exception path Rollback صریح ندارد؛ Finally تراکنش Provider را Dispose و سپس
  Connection را Close می‌کند. Rollback ضمنی Provider برای Legacy قابل فهم است،
  اما مقصد باید Rollback/abort صریح داشته باشد.
- چهار Policy value فرم قبل از آغاز تراکنش با Server مقایسه می‌شوند، ولی SQL
  هیچ Policy value/version نمی‌گیرد و تنظیم جاری را دوباره می‌خواند. بنابراین
  Guard stale UI وجود دارد، اما Snapshot اتمیک و مصون از TOCTOU وجود ندارد؛ این
  شاهد به `R-047` اضافه شد.
- Artifact با هفت Assembly و تست بیستم بازتولید شد؛ هیچ Assembly اجرا یا Command
  عملیاتی فراخوانی نشد.

## ۲۰۲۶-۰۸-۲۸ — Validator نوع سند و تفکیک Config از Capability

وضعیت: **۴۵ candidate از ۶۵ configured؛ ۲۰ Dormant/invalid؛ Predicate runtime باز**

- `usp_DoExternalVoucher` پیش از Finality، Validator نوع سند را صدا می‌زند.
  Validator وجود View و ستون‌های پایه/Party، CreatorField، Article مؤثر سال،
  Date/Amount/SL، ابعاد Ledger، Master code و Comment را Fail-closed کنترل می‌کند.
- Replay فقط‌خواندنی قواعد غیر اجرایی در هر سه سال ۱۴۰۳..۱۴۰۵ نتیجهٔ یکسان داد:
  ۶۵ نوع تنظیم‌شده، ۴۵ کاندید ساختاری و ۲۰ نوع نامعتبر.
- هر ۲۰ نوع Article مؤثر ندارند و ۱۳ مورد از همان ۲۰، View/Creator قابل استفاده
  نیز ندارند. پراکندگی ۱۴۰۵: خرید ۳، حسابداری مشتریان ۱۳ و خزانه ۴؛ فروش و حقوق
  صفر نوع نامعتبر ساختاری دارند.
- هیچ نوع نامعتبر در کل تاریخچه، سه‌ماهه یا Headerهای مسیر جدید استفاده نشده است؛
  بنابراین آن‌ها خرابی جاری نامیده نشدند و حذف خودکار نیز مجاز نیست.
- Validator واقعی ۷۱ Predicate را با Dynamic `WHERE 1=2` روی Creator view Compile
  می‌کند. Extractor هیچ View یا Predicate را اجرا نکرد؛ Runtime validity باز و
  نیازمند Harness ایزوله است.
- `R-051` با Severity بالا ثبت شد. دفتر ریسک ۵۱ مورد باز شامل ۲۷ Critical، ۲۱
  High و ۳ Medium دارد؛ Traceability به ۱۹۱ Assignment و ۵۱ Risk یکتا رسید.
- سند دامنهٔ ۲۲ و تست بیست‌ویکم ثبت شد؛ Raw predicate، account code، comment یا
  شناسهٔ عملیاتی در Artifact ذخیره نشد.
## ۲۰۲۶-۰۸-۲۸ — SQL پویای قواعد سند و Snapshot ناسازگار منبع

- `usp_DoPreVoucher` یک batch الحاقی می‌سازد و با `EXEC(@StrCmd)` اجرا می‌کند؛
  Validator نوع سند نیز View و Predicate تنظیمی را در SQL پویا اجرا می‌کند.
- ۱۱ دسته fragment به‌صورت فقط‌خواندنی و تجمیعی بررسی شد: ۷۱ Predicate متمایز
  وجود دارد و در snapshot فعلی شمار separator/comment/statement-keyword/quote/
  control-character مشکوک صفر است. هیچ مقدار خام ذخیره نشد.
- پاک‌بودن snapshot فعلی، executable configuration را امن نمی‌کند و دسترسی نویسنده
  پیکربندی هنوز به actor/role منتسب نشده است.
- Source creator view در batch صدور `WITH(NOLOCK)` دارد؛ Transaction بیرونی
  staging و posting را اتمیک می‌کند ولی committed-consistent بودن دادهٔ منبع را
  تضمین نمی‌کند. هیچ View یا concurrency incident اجرا نشد.
- `DefaultProvider.Open` در Binary Hash-pinned فقط `BeginTransaction()` بدون
  Isolation argument را صدا می‌زند. Clone دارای RCSI و Snapshot روشن است، اما
  `NOLOCK` آن را دور می‌زند و Production parity اثبات نشده است.
- چهار Creator فعال اخیر به ۵۴ جدول پایه و ۱۹ View در عمق حداکثر ۶ می‌رسند؛ فقط
  شش جدول rowversion و صفر جدول Temporal/Change Tracking دارد. dependency حل‌نشده
  یا external صفر است؛ column name شبیه Version به‌عنوان watermark پذیرفته نشد.
- `R-052` و `R-053` با Severity بحرانی ثبت شدند.
- Artifact: `voucher_creation_atomicity_and_policy_20260828.json`؛ سند:
  `domains/23_DYNAMIC_RULE_SQL_AND_SOURCE_SNAPSHOT_FA.md`؛ تست متمرکز: ۲۳ PASS.

## ۲۰۲۶-۰۸-۲۸ — انتقال Template و Authority انتشار Rule حسابداری

- اسکن ۶۲ Assembly Hash-pinned، صفر Form هدف‌نام‌دار، صفر Caller برای SaveCommand،
  صفر SQL literal مستقیم و صفر ارجاع به Procedureهای Template پیدا کرد.
- `ExternalVoucherTypeHandler.SaveCommand` فقط هشت instruction دارد و بدون Branch
  یک Validation failure می‌سازد؛ DataAdapter/Transaction call آن صفر است.
- `VoucherTemplateTransfer` بدون پارامتر، چهار محل SQL پویا، Drop/Create View و
  mutation سه جدول Type/Creator/Field دارد و سپس Child را صدا می‌زند.
- `VoucherTemplateArticleTransfer` بدون پارامتر، یک محل SQL پویا و mutation
  Article/ArticleComment دارد. شش Trigger مرتبط فعال‌اند.
- هر دو Procedure Transaction، TRY/CATCH، Rollback، Authorization و Rule-version/
  Publish audit ندارند. Application caller و permission صریح object صفر است؛ حساب
  تحلیل Execute ندارد. Authority ادمینی و فراوانی Runtime نامعلوم باقی ماند.
- `R-054` بحرانی افزوده شد. رجیستر اکنون ۵۴ ریسک باز شامل ۳۰ Critical، ۲۱ High
  و ۳ Medium دارد؛ Traceability به ۲۰۶ Assignment و ۵۴ Risk یکتا رسید.
- سند: `domains/24_VOUCHER_RULE_TEMPLATE_TRANSFER_AND_PUBLISH_FA.md`؛ Artifact:
  `voucher_creation_atomicity_and_policy_20260828.json`؛ تست متمرکز: ۲۴ PASS.

## ۲۰۲۶-۰۸-۲۸ — Schema drift در Template و مرز Transport قواعد

- Triggerهای INSERT جاری برای `Article` هر ۱۶ ستون و برای `ArticleComment` هر پنج
  ستون را پوشش می‌دهند؛ نقص Column coverage در Trigger وجود ندارد.
- Child قدیمی Template فقط ۱۱ ستون Article را نام می‌برد و دو نام حذف‌شدهٔ
  `VoucherCreatorId` و `ArticleCaption` دارد؛ شش ستون اختیاری جدید را نیز نمی‌نویسد.
  بنابراین Dynamic INSERT در Schema جاری Fail می‌شود، پس `R-054` با Failure window
  قطعی پس از Mutationهای Parent دقیق‌تر شد.
- ۱٬۱۳۲ لاگ Rule نگه‌داری‌شده وجود دارد؛ در بازهٔ سه‌ماهه چهار Article update ثبت
  شده است. Raw Script یا Value ذخیره نشد.
- مالک انتقال در Deployment جداگانهٔ `Replication` پیدا شد. سه Binary اصلی
  Hash-pinned و بدون Load/Execute parse شدند.
- Send path پیش از Watermark، Package را در `dbo.ReplicationFile` به‌عنوان Binary
  outbox ذخیره می‌کند و بعد از Commit آن را Upload می‌کند.
- Local و FTP receive هر دو Script را پیش از `LastExecLog` اجرا و Receipt را پیش
  از Commit در همان Transaction ثبت می‌کنند؛ Rollback path دارند.
- Receipt فاقد Rule version، Approval و Content hash است و Clone برای
  `ReplicationFile`، `ReplicationSend`، `tblLogRcv` و `tblLogSnd` صفر ردیف دارد؛
  موفقیت Delivery Production از این Snapshot اثبات نشد.
- `R-055` با Severity بالا افزوده شد. رجیستر اکنون ۵۵ ریسک باز شامل ۳۰ Critical،
  ۲۲ High و ۳ Medium دارد؛ Traceability به ۲۱۰ Assignment و ۵۵ Risk یکتا رسید.
- Artifact جدید: `rule_replication_transport_boundary_20260828.json`؛ سند:
  `domains/25_RULE_REPLICATION_TRANSPORT_AND_RECEIPT_FA.md`؛ تست‌ها: ۲۵ PASS برای
  Voucher و ۵ PASS برای Transport.

## ۲۰۲۶-۰۸-۲۸ — Encryption و Content authenticity در Replication

- `FluentFTP.dll` نسخهٔ `32.4.3.0` با Hash ثابت به Scope اضافه شد.
- `ConnectToFtpServer` Client پیش‌فرض و Credential دارد، اما EncryptionMode،
  SslProtocols و Certificate validation را تنظیم نمی‌کند؛ Constructor کتابخانه
  نیز EncryptionMode را Set نمی‌کند و Enum `None=0` است.
- Create/Extract Package هر دو Zip password دارند، ولی Hash/HMAC/Signature call در
  مسیر نام‌دار Send/Receive صفر است.
- File-share نیز پشتیبانی می‌شود و Config فعال Production خوانده نشد؛ استفادهٔ
  واقعی FTP در مرکز مشخص ادعا نشد.
- Executor از `SqlCommand.CommandText/ExecuteNonQuery` استفاده می‌کند، خودش
  `ISValidRecordToInsert` را صدا نمی‌زند و مسیر فایل پیش از Validator بعدی یک
  Executor call دارد؛ Universal typed allowlist اثبات نشد.
- `R-056` بحرانی افزوده شد. رجیستر فعلی ۵۶ ریسک باز شامل ۳۱ Critical، ۲۲ High و
  ۳ Medium و Traceability شامل ۲۱۵ Assignment و ۵۶ Risk یکتا است.
- تست Transport اکنون ۷ PASS است.

## ۲۰۲۶-۰۸-۲۸ — Retry، ترتیب و هم‌زمانی Receipt انتقال

- کاتالوگ Index نشان داد `ReplicationFile.FileName` و
  `ReplicationSend.CenterId` قید یکتا ندارند؛ `tblLogRcv` نیز فقط PK هویتی و
  Indexهای غیر‌یکتای Site/range/file دارد.
- Trigger رسید کاهش `EndLog` و `LastExecLog` را رد می‌کند، اما برابری را رد
  نمی‌کند و پیوستگی `StartLog = previous EndLog + 1` را الزام نمی‌کند.
- انتساب Scalar از `inserted` وجود دارد؛ Set-safe بودن درج چندردیفی اثبات نشد.
  History درج/حذف موجود است، ولی Idempotency key نیست.
- چون Snapshot رسیدی نگه نداشته، وقوع Duplicate/Gap در Production ادعا نشد.
- ریسک جدید تکراری ساخته نشد؛ `R-006` با این شاهد به Accounting، Configuration
  و Integration نیز متصل شد. تعداد ریسک یکتا ۵۶ ثابت ماند و Traceability به
  ۲۱۸ Assignment رسید.
- Artifact Transport و آزمون هشتم بازتولید شدند؛ هیچ Script/Procedure عملیاتی
  اجرا نشد.

## ۲۰۲۶-۰۸-۲۸ — Hook پس از دریافت و Authority سرویس Replication

- IL سرویس ثابت کرد پس از برگشت `Receive`، Script فعال تنظیمی Lookup و Execute
  می‌شود؛ `Run` یک Transaction مشترک روی Receive و Hook ندارد.
- Wrapper مستقر `usp_ReplicationAfterReciveAll` به Log-sort تراکنشی و
  `uspSetIdentityColValue` وصل است. Hook دوم Dynamic `DBCC CHECKIDENT` دارد ولی
  Transaction و TRY/CATCH خودش ندارد؛ Wrapper نیز فاقد هر دو است.
- نگاشت دقیق Config فعال عمداً خوانده نشد، پس فعال‌بودن Wrapper یا وقوع Failure
  در Production ادعا نشد. نتیجهٔ محدود: Receipt فایل تکمیل Hook را ثابت نمی‌کند.
- در ۹ Object هدف، Execute-as/مالک اختصاصی و Permission صریح Object-level صفر
  بود؛ Effective authority به Principal و Role/ownership chain نامعلوم وابسته است
  و Deny استنباط نشد.
- `R-055` بدون افزایش تعداد ریسک با Receipt مستقل Maintenance، Retry idempotent
  و Least-privilege readback دقیق‌تر شد. Artifact Transport اکنون ۹ تست متمرکز
  دارد.

## ۲۰۲۶-۰۸-۲۸ — Completion و Acknowledge خروجی Replication

- در File-share، Copy پیش از Completion و Move نهایی داخل Completion helper است.
- در FTP، Upload پیش از Remote size read، Validation helper و Rename نهایی است.
- در هر دو شاخه Database acknowledgement helper بعد از Completion صدا می‌شود؛
  پس حذف/ACK پیش از تحویل ادعا نشد.
- Helper پس از Upload یک فرمان دیتابیس اجرا می‌کند، اما اثر دقیق متن Obfuscated
  بازیابی نشد. Remote size validation نیز Content hash رمزنگاری‌شده نیست.
- Method contractهای Hash-pinned به ۳۳ رسید و آزمون دهم Transport افزوده شد؛
  هیچ Binary یا Package اجرا نشد.

## ۲۰۲۶-۰۸-۲۸ — Retention و کامل‌نبودن تاریخچهٔ Replication

- Helper پاک‌سازی پیش از Receive و Send در IL دیده شد.
- `usp_Replication_ClearReplicationReceive` از `tblLogRcv` بر پایهٔ
  `LastExecLog/MAX` حذف دارد و Transaction/TRY-CATCH داخلی ندارد؛ Binding دقیق
  Helper مبهم به Procedure اثبات نشد.
- این Cleanup از `tblLog` اصلی حذف ندارد، اما سه Procedure مستقل ایجاد مرکز
  Delete/Truncate دقیق همان Log دارند. اجرای آن‌ها در Production ادعا نشد.
- صفر Receipt نمی‌تواند عدم Delivery را ثابت کند و ۱٬۱۳۲ Rule log نیز فقط
  Retained snapshot است، نه Audit کامل و immutable.
- `R-055` به Audit append-only و retention-safe دقیق‌تر شد و آزمون یازدهم
  Transport افزوده شد.

## ۲۰۲۶-۰۸-۲۸ — Config هدف‌های Dynamic Identity hook

- `uspSetIdentityColValue` از `dbo.ColvalueTable(NAME,ColName)` برای Dynamic
  `DBCC CHECKIDENT` استفاده می‌کند و `QUOTENAME` در متن آن دیده نشد.
- Clone فعلی صفر Config row دارد؛ بنابراین هیچ Target فعال، Token نامعتبر یا
  Mutation Identity جاری ادعا نشد. Production config parity اثبات‌نشده ماند.
- Caveat به `R-055` افزوده و آزمون دوازدهم Transport ثبت شد.

## ۲۰۲۶-۰۸-۲۸ — ترتیب Packageهای ورودی

- Local receiver از `Directory.GetFiles` و FTP از `FtpClient.GetListing` استفاده
  می‌کند؛ در Receiverها و Listing helper هیچ Sort/OrderBy صریح دیده نشد.
- Trigger رسید Gap را رد نمی‌کند؛ بنابراین ترتیب قطعی Range پیش از Execute
  اثبات نشد. نبود Sort نام‌دار وقوع Incident را ثابت نمی‌کند.
- Snapshot خالی Receipt شاهد Out-of-order ندارد؛ `R-006` با تست Listing درهم،
  Gap و Overlap دقیق‌تر شد. Method contractها ۳۴ و تست Transport سیزده شد.

## ۲۰۲۶-۰۸-۲۸ — Scope مرکز و ترتیب Validator نسبت به Execute

- Local و FTP پیش از Unzip، Site/DC و Center را Lookup می‌کنند.
- هر دو Helper ورودی `string` و خروجی `int32` دارند و `String.Concat` را پیش از
  `ExecuteScalar` صدا می‌زنند؛ Parameterization و Validation کامل Token فایل
  اثبات نشد. Exploit جاری ادعا نشد.
- در هر دو Receiver، اولین `DatabaseHelper.Execute` پیش از
  `ISValidRecordToInsert` نام‌دار است؛ Pre-execution universal validator ثابت نشد.
- `R-056` با Parser تایپ‌شده، Query پارامتری و Center binding امضاشده دقیق شد؛
  Method contractها ۳۶ و تست Transport چهارده شد.

## ۲۰۲۶-۰۸-۲۸ — نتیجهٔ Executor و جلوگیری از Receipt کاذب فنی

- `DatabaseHelper.Execute` خروجی Boolean دارد؛ Return موفق true و Return رد
  اولیه/Exception false است.
- Local و FTP بلافاصله روی نتیجه `brtrue` دارند و مسیر false پیش از
  `InsertLastExecutedlogIdUpdateLog`، Rollback می‌کند.
- پس ثبت Receipt پس از false/Exception Executor در مسیر فعلی رد شد؛ Business
  parity پس از SQL موفق همچنان اثبات‌نشده است.
- آزمون پانزدهم Transport افزوده شد.

## ۲۰۲۶-۰۸-۲۸ — Propagation خطای Connector و شکست Rollback

- `DBConnector.Execute` و `CommitTransaction` در Failure دوباره Throw می‌کنند.
- `RollBackTransaction` Catch دارد اما Throw/Re-throw ندارد؛ مشاهده‌پذیری شکست
  خود Rollback اثبات نشد.
- مسیرهای Receiver Rollback را صدا می‌زنند، اما Unknown outcome ناشی از شکست
  Rollback باید جدا Quarantine/Reconcile شود.
- `R-007` به Platform/Configuration/Integration نیز متصل شد؛ ریسک یکتا ۵۶ ثابت
  و Traceability به ۲۲۱ Assignment رسید. Method contractها ۴۱ و آزمون Transport
  شانزده شد.

## ۲۰۲۶-۰۸-۲۸ — Lock نام‌دار و Concurrency فرستنده

- Start/Run هر دو `ControlLock` دارند، ولی گراف آن صفر Mutex/Monitor/DB call و یک
  File.Exists دارد؛ Cross-process lock از نام متد استنباط نشد.
- `GetLastSendId` و `UpdateLastSendId` Queryهای concatenated دارند و
  `ReplicationSend.CenterId` Unique نیست.
- BeginTransaction از Overload تک‌رشته‌ای نام Transaction استفاده می‌کند؛
  IsolationLevel صریح اثبات نشد.
- Per-center sender serialization اثبات نشد؛ Snapshot خالی Race واقعی را ثابت
  نمی‌کند. `R-006` به DB lease/application lock دارای fencing token دقیق شد.
- Method contractها ۴۹ و تست Transport هفده شد.

## ۲۰۲۶-۰۸-۲۸ — File/FTP cleanup پیش از Commit دریافت

- Local بعد از Receipt و قبل از Commit، Archive copy و چند File delete دارد.
- FTP در همان فاصله فایل‌های محلی و Remote package را حذف می‌کند.
- Commit failure Throw می‌شود، اما File/FTP در Rollback دیتابیس شرکت ندارند و
  Retry خودکار از Input محفوظ اثبات نشد. Runtime failure مشاهده نشد.
- `R-007` به Inbox state machine و Ack/Delete پس از Commit دقیق شد؛ آزمون هجدهم
  Transport افزوده شد.

## ۲۰۲۶-۰۸-۲۸ — نتیجهٔ Reset پس از Commit محلی

- `ResetReplicationSendTable` بعد از Commit اصلی Local اجرا می‌شود.
- متد تراکنش مستقل دوفرمانی، Rollback و Boolean success/failure دارد؛ Caller
  نتیجه را `pop` می‌کند.
- SQL دقیق Obfuscated و Runtime failure اثبات‌نشده است؛ عدم Propagation نتیجه
  قطعی است. `R-007` و آزمون نوزدهم Transport به‌روز شدند.

## ۲۰۲۶-۰۸-۲۸ — Checkpoint یکپارچهٔ صدور سند و Replication

- Builder آفلاین `build_varanegar_analysis_checkpoint_20260828.py` چهار Artifact
  اصلی صدور سند، Replication، رجیستر ریسک و Traceability را به Extractorها،
  تست‌ها و اسنادشان متصل کرد.
- Manifest نهایی ۲۱ منبع را با SHA-256 و اندازه ثبت می‌کند و ۳۳ Gate معنایی را
  بدون اتصال DB/Network/UI، اجرای Assembly یا Command عملیاتی کنترل می‌کند.
- وضعیت فعلی PASS است: ۵۶ ریسک باز، ۳۱ بحرانی، ۲۲۱ Assignment، ۵۶ ریسک یکتا و
  صفر ماژول Command-ready. صفر بودن Command-ready یک Gate ایمنی است و ادعای
  ناقص‌بودن شناخت دامنه نیست.

## ۲۰۲۶-۰۸-۲۸ — Timer دوره‌ای و نبود شاهد Single-flight

- `InitTimer` با Constructor بدون آرگومان Timer را می‌سازد، Interval و Elapsed
  handler را تنظیم و آن را Enabled می‌کند؛ Setter صریح `AutoReset` و
  `SynchronizingObject` در متد دیده نشد.
- `Run` یک `Thread.Sleep` دارد و در گراف آن Mutex/Monitor/Interlocked/Semaphore/
  ReaderWriterLock دیده نشد. `ControlLock` نام‌دار نیز execution mutex بودن را
  اثبات نمی‌کند. `InitTimer` و `Run` فقط `Timer.Enabled=true` دارند و تنظیم false
  تنها در `Stop` دیده شد.
- بنابراین Single-flight بودن Tickها اثبات نشد؛ وقوع overlap در Runtime ادعا
  نشد. Artifact یک Gate تازه و آزمون بیستم Transport دریافت کرد.

## ۲۰۲۶-۰۸-۲۸ — Deadline اجرای SQL بسته

- در Executor بسته، ثابت‌های واردشده به `CommandTimeout` برابر ۰، ۶۰۰ و ۳۰۰۰۰
  است؛ Connector عمومی ثابت ۶۰۰ دارد.
- Cancellation یا Deadline یکنواخت در گراف نام‌دار اثبات نشد. بنابراین محدود و
  مثبت‌بودن Timeout همهٔ مسیرها رد شد، بدون ادعای وقوع اجرای طولانی Runtime.
- Gate هجدهم Artifact Replication و آزمون بیست‌ویکم Transport ثبت شد؛ Checkpoint
  پس از افزودن هشت Gate مستقل صدور سند و Gate Quarantine اکنون ۲۸ Gate معنایی دارد.

## ۲۰۲۶-۰۸-۲۸ — سرنوشت Package ردشده

- Wrapper استاندارد Local به `ExecuteLocalFile` اصلی با Flag ثابت false Delegate
  می‌کند و Caller نتیجه را دور می‌اندازد.
- false فنی در Local پس از Rollback پنج `File.Delete` و `addDefectiveCenter` دارد؛
  `File.Move` قرنطینه در همان بازه صفر است.
- false فنی FTP پس از Rollback سه حذف محلی و صفر Remote delete در همان بلوک دارد.
  نقش دقیق Pathها و حفظ Remote در همهٔ continuationها اثبات نشد.
- Quarantine پایدار و Retry parity دو Transport اثبات نشد؛ رخداد Runtime ادعا
  نشد. آزمون بیست‌ودوم Transport افزوده شد.

## ۲۰۲۶-۰۸-۲۸ — محدودسازی اثر `IDENT_CURRENT` در Trigger قواعد

- `dbo.InsertToLog` شش پارامتر و یک خروجی `int` دارد و خروجی را با
  `IDENT_CURRENT('gnr.tblLog')` می‌سازد؛ `SCOPE_IDENTITY` ندارد.
- هر شش Trigger `Article/ArticleComment` خروجی را می‌گیرند، اما شمار استفادهٔ
  متغیر خروجی پس از Call در هر شش صفر است.
- بنابراین API خروجی concurrency-safe نیست، ولی اثر مستقیم ID برگشتی بر
  Control-flow همین Triggerها اثبات نشد و ادعای Watermark اشتباه رد شد.
- تست صدور سند و Gate بیست‌ونهم Checkpoint این محدودیت ادعا را منجمد کردند.

## ۲۰۲۶-۰۸-۲۸ — مصرف‌کنندگان واقعی خروجی `InsertToLog`

- Dependency catalog تعداد ۱۱۴۲ Trigger و ۱۱ Stored Procedure متصل به
  `dbo.InsertToLog` را ثبت کرد.
- دو Trigger باینری Voucher خروجی `@LogId` را در دو جدول Mapping ذخیره می‌کنند؛
  در نتیجه برخلاف شش Trigger Rule، اینجا ID برگشتی واقعاً مصرف می‌شود.
- دو جدول Mapping هیچ Index، Unique index یا FK ندارند و هر دو صفر ردیف‌اند؛
  بنابراین Race window `IDENT_CURRENT` قطعی، اما Incident retained اثبات‌نشده است.
- چهار Dependency SQL فقط Triggerهای Insert/Delete هستند؛ Reader `SELECT/JOIN`
  صفر و literal مستقیم در ۶۲ Assembly کاتالوگ اصلی نیز صفر است. مصرف Dynamic یا
  External همچنان نامعلوم است.
- Gate سی‌ام Checkpoint و آزمون بیست‌وششم صدور سند افزوده شد.

## ۲۰۲۶-۰۸-۲۸ — Footprint سراسری Triggerهای `InsertToLog`

- ۱۱۴۲ Trigger وابسته به `dbo.InsertToLog` همگی فعال‌اند و روی ۳۷۶ جدول در شش
  Schema قرار دارند؛ Event edgeها ۳۸۴ Insert، ۳۸۴ Update و ۳۷۸ Delete هستند.
- ۱۱۴۰ تعریف نشانهٔ Cursor دارند، `TRY/CATCH` در هیچ‌کدام دیده نشد، فقط سه تعریف
  نشانهٔ `XACT_ABORT` دارند و `NOT FOR REPLICATION` در هیچ Trigger فعال نیست.
- این Aggregate وابستگی، فراگیری Side effect ثبت تغییر را ثابت می‌کند؛ استفادهٔ
  اخیر هر جدول، وقوع خطای Runtime یا Delivery موفق downstream را ثابت نمی‌کند.
- توزیع Trigger/Table در Schemaها: `dbo=426/140`، `GNR=321/107`،
  `SLE=282/92`، `Acc=53/17`، `inv=45/15` و `ICA=15/5`؛ بنابراین Blast
  radius فروش، انبار، خرید، حسابداری و هستهٔ عمومی را هم‌زمان دربرمی‌گیرد.
- Artifact/Extractor صدور سند، آزمون بیست‌وششم و Gateهای سی‌ویکم/سی‌ودوم
  Checkpoint این مرز را بازتولیدپذیر و Hash-pinned کردند.
- Event shape نیز منجمد شد: ۳۷۶ Delete-only، ۳۸۲ Update-only و ۳۸۲ Insert-only
  همگی Cursor-based؛ دو Trigger بدون Cursor هر سه Event را پوشش می‌دهند. این دو
  Trigger اختلاف ۱۱۴۶ Event edge با ۱۱۴۲ Trigger را کامل توضیح می‌دهند.
- Gate سی‌وسوم Checkpoint آزمون multi-row/multi-event مقصد را از این مرز تغذیه
  می‌کند؛ هیچ Runtime duplicate/loss ادعا نشد.

## ۲۰۲۶-۰۸-۲۸ — قرارداد مؤثر مجوز NGT و تفکیک overload گروه

- هشت اسمبلی مستقر سرور NGT با Metadata/IL فقط‌خواندنی بررسی شد: ۱۳۴ Type،
  ۶۸۰ Method کاندید، ۶۷۸ Body موفق و صفر خطای Body؛ Assembly اجرا نشد.
- Guard وب Direct و Group را Union می‌کند. هر دو overload سه‌پارامتری در نهایت
  Query دارای فیلتر `Grant == 1` را مصرف می‌کنند؛ Predicate پس از Union فقط
  `Grant == -1` را Veto می‌کند.
- بررسی اولیه به‌علت آمیختن overload دوپارامتری async با overload سه‌پارامتری
  Guard، احتمال عبور مقدار صفر گروهی را مطرح کرده بود. افزودن Signature و
  Parameter count این فرض را رد کرد؛ این تصحیح در Artifact و Test منجمد شد.
- Snapshot شامل ۳۲۴ Atomic با مقدار ۱ و ۲٬۰۹۳ Atomic با مقدار ۰ است و هیچ مقدار
  `-1` یا خارج ۰/۱ ندارد. مقدار صفر در Guard مشاهده‌شده وارد مجموعه مجاز نمی‌شود،
  اما از روی Storage به‌تنهایی «Deny صریح» نام‌گذاری نشد.
- Guard Catalog را مستقیم نمی‌خواند. Save مسیر Catalog ردیف Atomic می‌سازد و هر
  ۲٬۴۱۵ expansion مستقیم فعلی Atomic هم‌جهت دارد؛ Missing/Opposite صفر است.
- Crosswalk Legacy↔NGT، Recursive catalog hierarchy و پوشش تک‌تک Endpointها
  همچنان باز است؛ هیچ رخداد دسترسی غیرمجاز Runtime ادعا نشد.
- دو Extractor، دو Artifact و هفت آزمون تازه ثبت شد؛ همه هفت آزمون PASS هستند.

## ۲۰۲۶-۰۸-۲۸ — پوشش Endpoint، Action چندمقداری و Cross-check Permission

- ۷۸۴ Method دارای HTTP/Route attribute بررسی شد؛ ۵۹۵ مورد NGT authorize دارند:
  ۲۵۰ مورد `Resource+Action` و ۳۴۵ مورد Role-only/empty.
- Action ورودی با ویرگول Split و سپس Trim/Lower می‌شود و membership دقیق دارد؛
  فرض substring رد شد. ۲۵۱ اعلان به ۱۲۸ زوج یکتای Resource/Action Normalize شد.
- ۱۰۰ زوج یک Permission row، تعداد ۲۵ زوج چند ردیف در Scopeهای احتمالی
  ApplicationOwner و سه زوج صفر ردیف دارند: `AreaLayer/View`،
  `Tours/ConfirmTourReceived` و `Tours/Viewpreview`.
- ۹۱ Endpoint Standard Authorize، یک Claims authorize و ۳۸ AllowAnonymous دارند.
  پس از ارث‌بری base مشترک، ۶۰ مورد هیچ‌یک از این اعلان‌ها را ندارند و ۳۸ مورد
  فعل تغییردهنده دارند.
- Startup دو Global filter برای ValidateModel/CatchExceptions می‌سازد و
  Authorization-named constructor ندارد. این هنوز Anonymous reachability را
  ثابت نمی‌کند؛ Manual async guard و Host/Middleware policy بررسی نشده است.
- Endpoint Artifact، Cross-check Clone و سه تست جدید افزوده شد؛ مجموعهٔ متمرکز
  مجوز اکنون ۱۰ PASS است.

## ۲۰۲۶-۰۸-۲۹ — Delta ریسک و Traceability مجوز وب

- رجیستر قبلی ۵۶تایی تغییر نکرد؛ Artifact جدید `R-057` را با Severity بحرانی
  و Caveat صریح احتمال/Reachability ثبت کرد.
- رجیستر جدید ۵۷ ریسک شامل ۳۲ بحرانی، ۲۲ بالا و سه متوسط دارد؛ Validation PASS.
- Traceability جدید ۲۲۴ اتصال، ۵۷ ریسک یکتا، ۱۴/۱۴ ماژول Traced و صفر
  Command-ready دارد؛ Validation PASS.
- دو آزمون Risk/Trace افزوده شد و مجموعهٔ متمرکز مجوز به ۱۲ PASS رسید.

## ۲۰۲۶-۰۸-۲۹ — Body مستقیم و Async شکاف‌های مجوز

- هر ۶۰ Endpoint بدون اعلان و `MoveNext` هر ۴۳ مورد Async با صفر خطا خوانده شد.
- فراخوانی نام‌دار Authorization decision در همه ۶۰ مورد صفر است؛ شش مورد فقط
  داده Permission/Authorization و سه مورد فقط CurrentUser context مصرف می‌کنند.
- Data access و Actor context به‌عنوان Enforcement تلقی نشد. Obfuscated/delegated
  guard و Host/Middleware policy هنوز رد نشده و Anonymous request اجرا نشده است.
- Artifact/Extractor و آزمون سیزدهم ثبت شد؛ مجموعهٔ مجوز ۱۳ PASS است.

## ۲۰۲۶-۰۸-۲۹ — Admin short-circuit و Break-glass مقصد

- Predicate نقش دقیق `lower(role).Equals("admin")` است و Branch true پیش از Base
  authorization برمی‌گردد؛ non-admin به Base می‌رود.
- Base ابتدا Web Resource/Action و سپس Authorize استاندارد را اجرا می‌کند؛ پس
  Admin هر دو را دور می‌زند. ByPass صریح Endpoint فعلی صفر است.
- Clone بدون هویت یک Admin role row، سه Assignment و سه Subject دارد؛ سوءاستفاده
  یا نامناسب‌بودن انتساب ادعا نشد.
- `R-058` برای تبدیل این مدل به Break-glass/JIT با MFA/approval/expiry/audit/SoD
  افزوده شد. رجیستر ۵۸ ریسک/۳۳ بحرانی و Traceability ۲۲۶ اتصال PASS دارد.
- دو آزمون Role/aggregate افزوده شد؛ مجموعهٔ مجوز ۱۵ PASS است.

## ۲۰۲۶-۰۸-۲۹ — Checkpoint مستقل مجوز

- Builder آفلاین شواهد Runtime/Endpoint/Manual/Admin/Clone/Risk/Trace را با اسناد،
  Extractorها و تست به یک Checkpoint Hash-pinned متصل کرد.
- نسخه اولیه ۲۰ منبع و ۴۷ Gate PASS داشت؛ پس از افزودن سند و سپس بستهٔ Owner
  scope، Manifest با ۲۸ منبع و ۶۹ Gate بازتولید شد. صفر
  DB/Network/UI/Assembly/Command در Builder اجرا می‌شود.
- این Checkpoint پایان برنامهٔ ۱۵ساعته نیست؛ نقطه ادامه برای
  ApplicationOwner/DataOwner/Scope و OperationDate/Feature است.

## ۲۰۲۶-۰۸-۲۹ — Owner scope از Header تا Repository و Snapshot

- ۱۲٬۶۹۵ Method body در سه Assembly خوانده شد؛ یک خطای IL فقط در Mapper نامرتبط
  بود و صفر Method نام‌دار Scope خطا داشت. ۱٬۴۷۳ Method Scope انتخاب شد و ۲۹۸
  مصرف‌کننده در ۲۶۱ Type ثبت شد.
- زنجیره Header برابر `Center→DataOwner→Owner` است؛ Controller هر سه Key و UserId
  را در OwnerInfo می‌گذارد، ولی Guard Permission فقط OwnerKey را می‌خواند.
- سازندهٔ تک‌Key همان مقدار را سه بار پخش می‌کند. Repository audit روی دو Assembly،
  ۷۰ Type و ۶۹۵ Method با صفر خطا نشان داد `GetQuery` خام و
  `GetQueryByOwner→CalcExtraPredict` Owner-aware است؛ Direct/Group authorization
  مسیر خام را مصرف می‌کنند.
- Snapshot Aggregate: یک Application/AO/DO، دو Center، ۳۲۴ Grant مؤثر و صفر
  Cross-Application؛ ۵۸ Membership در Scope گروه متفاوت از User، یک Membership
  یتیم و یک مرکز پیش‌فرض هم‌کلید با DataOwner.
- هر دو Center با وجود ارجاع همهٔ ۷۸۶ User، هشت Group و ۵۹ Membership،
  `IsActive=0/IsRemoved=0` هستند؛ معنای Active باید Owner-approved شود.
- `R-059` افزوده شد. رجیستر ۵۹ ریسک/۳۴ بحرانی و Traceability ۲۲۹ اتصال/۵۹ ریسک
  PASS است؛ Cross-tenant incident فعلی ادعا نشده و صفر ماژول Command-ready است.

## ۲۰۲۶-۰۸-۲۹ — OperationDate و انتخاب تاریخ Replication

- چهار Assembly NGT با ۲۷٬۷۸۸ بدنه متد بررسی شد؛ ۶۴۳ متد مرتبط، یک Caller
  Setter و چهار Caller Getter برای `OperationDate` ثبت شد و صفر خطای نام‌دار
  این مرز وجود داشت.
- `SaveTourData` مقدار `default(DateTime)` را رد می‌کند و
  `AddDistributionTour` مقدار Captureشده‌ی `DateTime.Now` را برای OperationDate
  می‌گذارد؛ Default مستقل SQL سال ۱۹۰۰ است و Check/Trigger مرتبط ندارد.
- Clone دو Return NGT، صفر Return FRU، صفر Sentinel، صفر Crosswalk دقیق و دو
  تاریخ رویداد هم‌روز با CreatedDate دارد؛ ردیف یا شناسه خام ذخیره نشد.
- تنظیم جاری معتبر `CallDate / تاريخ درخواست` است. چهار گزینه CallDate،
  OperationDate، ServerDate و ActiveDate با نام معنایی BaseValue به ثابت‌های کد
  تطبیق داده شد، بدون ذخیره UUID.
- Business IL و `dbo.NGT_DoReplicateTour` در منبع `OperationDate` برابری قطعی
  ندارند؛ ActiveDate نیز Retriever در برابر Query تاریخ باز فروش است. سه CASE
  SQL بدون ELSE هستند. این ساختار رخداد جاری را ثابت نمی‌کند.
- `R-060` با شدت High ثبت شد. رجیستر به ۶۰ ریسک (۳۴ بحرانی/۲۳ بالا/۳ متوسط)
  و Traceability به ۲۳۴ اتصال/۶۰ ریسک رسید؛ صفر ماژول Command-ready باقی ماند.

## ۲۰۲۶-۰۸-۲۹ — تقدم، scope و انتقال تنظیمات NGT

- هشت جدول تنظیم با ۳۴۷ ستون و ۹۷ ماژول چندمنبعی catalog شد؛ ۱۴ ماژول دارای
  `TOP 1` بدون `ORDER BY` فقط کاندید بررسی باقی ماندند و به‌عنوان Resolver
  نامعین ادعا نشدند.
- Business روی DeviceSetting/DeviceUser از `GetQueryByOwner`، شرط removed و
  join کاربر استفاده می‌کند و یازده گروه تنظیم را به‌ترتیب ترکیب می‌کند؛ AppSetting
  با singleton ثابت بازیابی می‌شود.
- `MandatoryCustomerVisit` در Business از Device و در SQL transport از App
  می‌آید. ۱۷/۱۷ Device فعال با App فعلی ناسازگارند و دو Device NULL هستند.
- BackOffice زنده center-effective است ولی View انتقال global ServerConfig را
  Pivot می‌کند: یک خروجی UNPIVOT جاافتاده، پنج خروجی جاری غایب و هفت مقایسه‌ی
  مرکز-به-انتقال ناسازگار ثبت شد. بعد از rename مرکز، شش خروجی Procedure در View
  وجود ندارد.
- ۲۳ DeviceSetting حذف‌شده ۲۱۸۴ ردیف در View خام می‌سازند؛ صفر DeviceUser فعلی
  به آن‌ها متصل است، اما ۵۱ DeviceOrderType فعال FK به پروفایل حذف‌شده دارد.
- دو Extractor، دو Artifact، checkpoint مستقل ۳۹/۳۹، سند فارسی و `R-061` ساخته
  شد. رجیستر ۶۱ ریسک (۳۴ بحرانی/۲۴ بالا/۳ متوسط) و Traceability ۲۳۹ اتصال/۶۱
  ریسک PASS دارد؛ incident کاربر یا ارسال واقعی پروفایل حذف‌شده ادعا نشد.

## ۲۰۲۶-۰۸-۲۹ — ذخیره، Replication و Crosswalk سفارش NGT

- چهار caller وب برای `SaveTourData` و شش caller برای `ReplicateTour` از IL
  hash-pinned استخراج شد. Save دارای transaction صریح و چهار call Replicate است؛
  UpdateFromNGT پنج SaveChanges و بدون BeginTransaction محلی دارد، با caveat
  ambient/delegated transaction.
- `NewReplicateTour` به `dbo.NGT_DoReplicateTour` می‌رسد؛ Procedure فقط
  fingerprint شد و با پنج پارامتر catalog ثبت شد، اجرا نشد.
- ۲۱۲٬۲۳۱ سفارش Line-only، ۹٬۷۹۵ Header-only، یک Partial و هفت Split هستند؛
  ۱٬۱۲۵ شناسه Header بین ۳٬۳۸۵ سفارش NGT مشترک است و بیشینه ۱۳ Header دارد.
- دو راه Crosswalk در ژوئن تا اوت هم‌زمان‌اند. وضعیت Parent/Scope فعلی سالم است،
  ولی هر ۶۱ FK مرتبط untrusted است و جدول Status صفر ردیف و بدون key دارد.
- دو Extractor، دو Artifact، تست متمرکز و سند فارسی افزوده شد. `R-033` با این
  شواهد توسعه یافت؛ تعداد ریسک ۶۱ و mappingها ۲۳۹ باقی ماند.
- Builder مستقل سفارش، همه‌ی شواهد SQL/IL/Auth/Risk/Trace و اسناد را آفلاین
  hash-pin می‌کند و در زمان ساخت صفر اتصال DB/Network/UI و صفر اجرای Command یا
  Assembly دارد.

## ۲۰۲۶-۰۸-۲۹ — State machine و فرمان Tour/CustomerCall

- چهار DLL deployed با ۲۷٬۷۸۸ بدنه IL بررسی شد؛ ۲۱۷ متد focused، ۴۵ متد mutation
  و هر ۲۰ بدنه lifecycle هدف resolve شدند؛ صفر خطای نام‌دار این مرز وجود داشت.
- Cancel/Deactivate/Activate/Receive/Send/Close/Finish یک state setter عمومی
  نیستند. Deactivate PreviousStatus را ذخیره و Activate آن را برمی‌گرداند؛
  TourReceived می‌تواند Received یا Finished را انتخاب کند.
- Snapshot شامل ۶۴٬۵۶۱ Tour و ۲٬۴۷۱٬۲۵۰ CustomerCall است. فقط ۴۵۵ Tour
  PreviousStatus دارند؛ جدول CustomerCallOrderStatus صفر ردیف است، پس history
  کامل از current row قابل بازسازی نیست.
- ۷۷۲ VisitStatus به BaseType تحویل اشاره دارند؛ ۵۵۰ تأییدشده و ۲۲۲ عدم قطعی،
  هر دو با Active Order. این cross-type union رخداد کاربر اعلام نشد.
- دو Tour با EndTime پیش از StartTime و سه Call با VisitDuration منفی، بدون ذخیره
  هویت ردیف، ثبت شد. Parent/scope Call→Tour فعلی صفر mismatch دارد.
- ۲۶٬۶۱۳ زوج Tour+Customer تکراری و ۵۷٬۳۹۱ Call در آن‌هاست؛ بیشینه ۱۴ Call.
- ۲۹ Endpoint mutation lifecycle بررسی شد: ۲۴ GET و پنج POST؛ همه یک NGT auth
  دارند (۲۵ Resource/Action و چهار Roles-only). `R-062` برای HTTP GET mutation
  اضافه و `R-008` با state/history تقویت شد.
- رجیستر ۶۲ ریسک (۳۴ بحرانی/۲۵ بالا/۳ متوسط)، Traceability ۲۴۴ اتصال/۶۲ ریسک و
  صفر ماژول Command-ready است.

## ۲۰۲۶-۰۸-۲۹ — پرداخت، تخصیص و Receipt Crosswalk در NGT

- پنج جدول و ۸۲ ستون هدف با Clone فقط‌خواندنی بررسی شد: ۳٬۵۲۳ سربرگ پرداخت و
  ۳٬۹۱۷ ریز، همگی فعال. چهار SettlementType جاری بدون reference/type mismatch
  عبارت‌اند از ۳٬۱۷۹ کارت‌خوان، ۱۸۰ نقد، ۱۵۹ چک و پنج رسید.
- ۳٬۴۶۶ سربرگ با جمع ریزها برابر و ۵۷ مورد کم‌تخصیص‌اند؛ ۱۴ مورد بدون ریز و
  ۴۳ مورد دارای تخصیص ناقص است. over-allocation صفر است. هر دو مبلغ `float` هستند.
- ۳٬۷۴۵ ریز به سفارش جاری NGT و ۱۷۲ ریز قدیمی به Sale BackOffice وصل است؛ orphan،
  removed-parent و owner-scope mismatch صفر است. یک cross-call detail در همان
  Tour و همان Customer باقی مانده و به‌عنوان corruption اعلام نشد.
- ۲۷۴ Receipt crosswalk در UUID/Ref/Number و وضعیت تأیید resolve می‌شوند؛ چهار
  مبلغ برابر و ۲۷۰ مبلغ با aggregation scope متفاوت است.
- ۲۴ FK مرتبط همگی enabled ولی untrusted هستند؛ business unique index و trigger
  روی پنج جدول صفر است. Duplicate fingerprint جاری نیز صفر است.
- `SaveTourPaymentChanges` تراکنش مستقل، soft-remove Cash، BulkMerge، Save، Commit
  و Rollback دارد. `UpdateTour` آن را پیش از ذخیره مستقل StockLevel و Order صدا
  می‌زند و در بدنه خود transaction ندارد؛ ambient بیرونی رد نشده است.
- چهار Confirm payment endpoint با POST و چهار Withdraw با GET منتشر شده‌اند؛
  هر هشت NGT authorization دارند. POS writeها POST/PUT/DELETE و Resource/Action‌اند.
- ۴۰۴ PaymentTypeOrder فقط ۱۵ active دارد؛ ۲٬۵۲۱ Bridge فعال و ۴۸۲ اتصال فعال
  به term حذف‌شده ثبت شد. exposure جاری کاربر ادعا نشد.
- دو Extractor، دو Artifact، سند فارسی، ۱۶ تست و checkpoint مستقل ۱۸ منبع/۴۰ Gate
  افزوده شد. `R-007` و `R-061` توسعه یافتند و `R-063` بحرانی اضافه شد.
- رجیستر اکنون ۶۳ ریسک (۳۵ بحرانی/۲۵ بالا/۳ متوسط)، Traceability ۲۴۸ اتصال/۶۳
  ریسک و صفر ماژول Command-ready دارد.

## ۲۰۲۶-۰۸-۲۹ — Replication پرداخت NGT و Idempotency رسید

- چهار Procedure با مجموع ۱۹۵٬۹۰۹ کاراکتر، ۱۴۵ Mutation statement و ۱۹۰
  Dependency فقط به‌صورت hash/token/object profile تحلیل شد؛ هیچ متن SQL، GUID
  یا ردیف مالی ذخیره و هیچ Procedure اجرا نشد.
- `NGT_CreateReceipt_ForDistInfo` Receipt، Cash، CashDetail، Cheque، ChequeHistory
  و BankOrder را می‌سازد. `NGT_CreateSettlement_Merge` Allocationهای Settlement
  را ایجاد می‌کند. هر دو transaction محلی ندارند و زیر transaction Procedure
  بالادست اجرا می‌شوند.
- هفت SettlementType کدشده بدون ذخیره GUID به نام معنایی حل شد: نقد، چک،
  کارت‌خوان، رسید، تخفیف، مانده بستانکاری و پرداخت با واسطه.
- `TourHistory(Type=10)` شامل ۴۴۷ ردیف برای ۳۴۴ Payment فعال است؛ Entity یتیم
  صفر، هدف Receipt موجود ۴۳۸ History و هدف مفقود ۹ History در چهار Payment است.
- ۲۷۴ Payment تک-History Crosswalk کامل دارند؛ ۷۰ Payment چند-History با ۱۷۳
  ردیف فقط `BackOfficeReceiptNo` دارند و UUID/Ref خالی است. ۷۲ duplicate target
  group، دو Payment چندهدف و بیشینه شش History ثبت شد.
- تنها Unique index روی Entity برای Type=1 فیلتر شده و Type=10 را پوشش نمی‌دهد؛
  FK و Trigger نیز صفر است. Branchهای SQL Guard یکسان `NOT EXISTS` ندارند.
- IL مستقر `ReplicateTour` یک `NewReplicateTour` و سه setter Crosswalk پرداخت را
  نشان داد؛ Commit در ترتیب خطی IL پیش و پس از setterها وجود دارد. Branch کامل
  بدون fault injection ادعا نشد، اما ۷۰ حالت number-only شاهد حالت جزئی جاری است.
- دو Extractor SQL/IL، دو Artifact، سند مستقل، تست و checkpoint افزوده شد.
  `R-007` توسعه یافت و `R-064` Critical اضافه شد؛ رجیستر ۶۴ ریسک (۳۶ بحرانی)،
  Traceability ۲۵۲ اتصال/۶۴ ریسک و صفر Command-ready دارد.

## ۲۰۲۶-۰۸-۲۹ — Compensation و Rollback پس از Replication NGT

- `TourDomain.RollBackTour` با RequestType=20 به هر دو Adapter VnLite/VnSds
  می‌رسد؛ هر Branch از EntityUniqueId نتیجه‌های Replication temp table می‌سازد،
  `dbo.NGT_RollBackTour` را اجرا می‌کند و Commit/Catch-Rollback دارد.
- `TourDomain.RollBackTour` نتیجهٔ Boolean همان `RetrieveInfo` را بلافاصله با
  opcode `pop` دور می‌ریزد؛ بنابراین `false` Adapter پس از Catch/Rollback در مرز
  Business به Caller به‌عنوان نتیجهٔ قابل بررسی منتشر نمی‌شود.
- Procedure فعال transaction محلی ندارد، به `#EntityUniqueIdList` وابسته است و
  History را در پایان حذف می‌کند. به `RCashDetail` و `tblChqHist` اشاره ندارد.
- `dbo.USP_NGT_UndoReplicateTour` به‌علت `RETURN` آغازین و Comment بودن همهٔ ۲۱
  Mutation، یک Entry point مرده است؛ cleanup گسترده‌تر آن رفتار Runtime نیست.
- Snapshot فقط Typeهای ۱، ۲، ۸ و ۱۰ دارد؛ Type=11 که Delete Payment فعال به آن
  وابسته است صفر است.
- ۳۴۲ Receipt متمایز موجود Type=10 بررسی شد: ۷۲ Cash/CashDetail، ۶۴
  Cheque/ChequeHistory و ۳۳۰ BankOrder دارند؛ همهٔ ۳۴۲ مورد حداقل یک Child واقعی
  با FK فعال `NO_ACTION` از CashDetail، ChqHist یا tblPayments دارند.
- این ترکیب نقص ساختاری Compensator را ثابت می‌کند، نه تعداد تلاش یا incident
  واقعی. هیچ Procedure/Endpoint اجرا نشد و هیچ ردیف یا GUID ذخیره نشد.
- دو Extractor، دو Artifact، سند، هشت تست و `R-065` Critical افزوده شد؛ رجیستر
  ۶۵ ریسک (۳۷ بحرانی)، Traceability ۲۵۶ اتصال/۶۵ ریسک و صفر Command-ready دارد.

## ۲۰۲۶-۰۸-۲۹ — Replication، Crosswalk و Update برگشت NGT

- SQL و IL مستقل نشان دادند ساخت نتیجهٔ BackOffice پیش از Write-back Crosswalk
  برگشت Commit می‌شود: `NewReplicateTour` پیش از Transaction مدیریت‌شده و هشت
  setter برگشت است؛ `NGT_DoReplicateTour` نیز پیش از Write-back سفارش برگشت
  Commit دارد.
- Unique index بدون فیلتر برای Entity برگشت Typeهای ۲/۱۲ در TourHistory و برای
  ستون‌های `BackOfficeReturn*` خط برگشت وجود ندارد.
- دو Line فعال: یک No-history، یک History نوع ۲ با Write-back و RetOrder هدف
  مفقود؛ RetOrder جاری صفر. این وضعیت Recreate خودکار را ممنوع می‌کند، اما علت
  تاریخی و وقوع Duplicate را ثابت نمی‌کند.
- `CustomerCallReturnDomain.UpdateFromNGT` سه SaveChanges و Caller آن یک
  SaveChanges دارد؛ هر دو صفر Transaction signal دارند. Header/Line/Detail و
  Tombstone یک Commit واحد نیستند.
- دو Extractor، دو Artifact و سند مستقل افزوده شد؛ `R-066` Critical و `R-067`
  High رجیستر را به ۶۷ ریسک (۳۸ بحرانی، ۲۶ بالا)، ۲۶۳ اتصال و صفر Command-ready
  رساندند.

## ۲۰۲۶-۰۸-۲۹ — Replication فروش و Duplicate History نوع ۸

- ۳٬۷۳۱ History نوع ۸ برای ۳٬۵۹۳ Order Entity؛ ۱۳۸ Entity هرکدام دو History
  با UUID/Ref/No/timestamp یکسان دارند. Multi-target و Sale target مفقود صفر است.
- Header NGT، History و Sale جاری برای هر ۳٬۵۹۳ Entity از UUID/Ref سازگارند؛
  Duplicate Sale/Stock/Accounting از این شاهد نتیجه‌گیری نشد.
- Unique index مرتبط برای Type=8 History یا Crosswalk Invoice Header وجود ندارد.
- IL سه setter Invoice و قرارگیری `NewReplicateTour` پیش از Transaction/setter را
  نشان داد؛ Commit در دو سوی write-back وجود دارد.
- `R-068` Critical رجیستر را به ۶۸ ریسک (۳۹ بحرانی)، ۲۶۷ اتصال و صفر
  Command-ready رساند.

## ۲۰۲۶-۰۸-۲۹ — تطبیق Type=1 Order History با Target جاری

- Extractor فقط‌خواندنی ۱٬۱۱۸٬۲۴۴ History نوع ۱ را با خط NGT و
  `SLE.tblOrderHdr` تطبیق داد: ۱٬۱۱۲٬۷۱۱ same-target و ۵٬۵۳۳ neither-match.
- ۵٬۵۳۳ Crosswalk باقی‌مانده به ۱٬۰۲۴ هدف مفقود در ۱٬۰۲۲ والد فعال و uncanceled
  تعلق دارد؛ ۶۳۴ خط/۱۱۴ والد در سه ماه اخیر هستند.
- ۱٬۰۲۱ والد کاملاً مفقود و یک والد Mixed با ۱۵ خط resolved و یک خط missing است؛
  هفت والد Split-target و سه مورد هم‌زمان missing+split هستند.
- IL سه setter سفارش را بعد از `NewReplicateTour` و Transaction مدیریت‌شده را بعد
  از Replication نشان داد؛ Commit در دو سوی write-back وجود دارد.
- Artifactها هیچ شناسه یا ردیف خامی ندارند. `R-069` Critical ثبت شد؛ علت Target
  loss و مجاز بودن recreate از این شاهد نتیجه‌گیری نشد.

## ۲۰۲۶-۰۸-۲۹ — حذف Order Target و نبود Tombstone NGT-aware

- پس از حذف Comment و String literal، چهار Procedure حذف مستقیم
  `SLE.tblOrderHdr` دارند؛ فقط `NGT_RollBackTour` به `TourHistory` اشاره می‌کند.
- سه Procedure دیگر سیگنال خط NGT یا BackOfficeOrder crosswalk ندارند. سه Trigger
  فعال DELETE نیز History/Crosswalk را نمی‌شناسند؛ فقط یکی Log عمومی می‌نویسد.
- Header سفارش Temporal/CDC/Change Tracking ندارد. دوازده FK فعال ولی untrusted
  به آن وصل‌اند: ۱۱ NO_ACTION و یک CASCADE.
- `R-070` High افزوده شد. این مرز قابلیت ایجاد stale crosswalk و فقدان Audit
  Domain-aware را نشان می‌دهد، نه اینکه یکی از این مسیرها علت جمعیت فعلی بوده است.

## ۲۰۲۶-۰۸-۲۹ — تطبیق مستقیم Missing Target با GNR.tblLog

- Trigger حذف، OperationTable/OperationType/OperationId/TransDate را ثبت می‌کند.
  همهٔ ۱٬۰۲۴ Target مفقود دقیقاً یک Delete log canonical با همان ID دارند.
- هر حذف بعد از آخرین History همان Target است: ۲۹۸ same-day، ۵۳۴ در ۱–۷ روز و
  ۱۹۲ در ۸–۳۰ روز. حذف پیش از History یا بیش از ۳۰ روز صفر است.
- جمعیت سه‌ماهه ۱۱۵ Target است؛ تمام ۵٬۵۳۳ History و ۱٬۰۲۴ Target پوشش دارند.
- ۱٬۹۰۷ Delete ID باقی‌مانده همگی اکنون غایب‌اند: ۱٬۰۲۴ Type=1 و ۸۸۳ مورد دیگر.
- Origin فقط با cardinality ذخیره شد؛ هیچ App/User/Host/SPID یا ID خامی Persist
  نشد. حذف قطعی شد، اما مسیر Procedure و علت تصمیم هنوز attribution نشده است.
- Sequence تمام ۱٬۰۲۴ Session برابر Item→Visit→Header است؛ Rollback موفق NGT
  Visit→Item→Header→History و UndoUserExtraInfo بدون Visit است، پس هر دو با مسیر
  عادی سازگار نیستند.
- Order_Delete tail دقیقاً مطابق است؛ ConfirmFreeInvoice هم همان tail را پس از
  Sale delete دارد، ولی SaleHeader DELETE مجاور صفر است. Order_Delete نامزد قوی
  است و برای تبدیل به نتیجهٔ قطعی به Runtime trace کنترل‌شده نیاز دارد.

## ۲۰۲۶-۰۸-۲۹ — Atomicity هزینهٔ فاکتور تأمین‌کننده

- پنج Procedure اصلی Apply/ReApply، پنج Caller و هشت یال Call graph بدون اجرای
  هیچ Command بررسی شدند؛ Coreها تراکنش محلی صریح ندارند.
- Apply قیمت را Delete/Insert می‌کند؛ FastApply پس از بازسازی Status را یک می‌کند؛
  ReApply ابتدا Status/ConfirmDate را یک می‌کند و سپس FastApply را در حلقه صدا
  می‌زند. این ترتیب، failure window است و وقوع partial apply را ثابت نمی‌کند.
- Snapshot فعلی clean است: ۳٬۲۸۵ Applied/۲۹٬۰۷۸ priced و ۱۴۱
  Unapplied/۱٬۳۵۴ unpriced، با صفر mismatch و صفر اشتراک آیتم بین دو Status.
- ۹۵ orphan price row و نبود FK مستقیم ثبت شد؛ causal attribution انجام نشد.
- دو Assembly با Inventory قبلی هم‌هش و چهار Method/۴۶۴ Instruction فقط از IL
  خوانده شدند. ReApply Query بدون Commit/Begin صریح و Apply دارای Commit پس از
  Adapter در ترتیب خطی است؛ Branch semantics هنوز خارج از شاهد است.
- دو Extractor، دو Artifact، سند، تست، checkpoint و `R-071` Critical افزوده شد؛
  رجیستر ۷۱ ریسک (۴۱ بحرانی/۲۷ بالا/۳ متوسط)، Traceability ۲۷۹ اتصال و صفر
  Command-ready دارد.

## ۲۰۲۶-۰۸-۲۹ — Unapply/Delete فاکتور خرید و Cost reversal

- هشت ماژول SQL منتخب بررسی شد؛ فقط سه مورد Transaction محلی دارند. Unlink
  Header را پیش از صفرکردن Price/UnitPrice Voucher انتخاب‌شده Unapplied می‌کند.
- مسیر Managed هش‌سنجی‌شده Save relation → Operation code 3 → Commit دارد، اما
  Generic SaveCommand و Reachability تراکنش فیزیکی به‌طور کامل حل نشده است.
- ۱۷ Unapplied و ۱۹۲ Applied Invoice چندرسیدی‌اند؛ current status/price parity
  همچنان صفر mismatch است.
- ۳٬۹۰۲ Insert و ۲۱۳ Delete Relation در Log مانده؛ ۱۵ Delete سه‌ماهه است. آخرین
  Event دقیقاً ۳٬۶۸۹ Current و ۲۰۳ Absent را بازسازی می‌کند؛ Reason/Actor معلوم
  نیست.
- Header و Price Audit ندارند؛ ۸۳ Zero-price row بدون attribution باقی ماند.
- دو Extractor، دو Artifact، سند، هشت تست، checkpoint و `R-072` High افزوده شد؛
  رجیستر ۷۲ ریسک (۴۱ بحرانی/۲۸ بالا/۳ متوسط)، Traceability ۲۸۳ اتصال و صفر
  Command-ready دارد.

## ۲۰۲۶-۰۸-۲۹ — Undo تخریبی تاریخچهٔ چک پرداختنی

- Procedure اصلی Undo آخرین History را در تراکنش Delete، Pointer چک را به رخداد
  قبلی و وضعیت برگ دسته‌چک را به Projection جدید برمی‌گرداند؛ Event جبرانی ندارد.
- در Log، ۱٬۵۳۷ Delete tail دقیق Undo دارند و تمام ۷۸ Delete سه‌ماهه در همین
  گروه‌اند. ۱۱۷ حذف همراه Cheque delete و ۱۴ partial tail جدا نگه داشته شدند.
- Snapshot ۴٬۶۷۲ چک/۱۳٬۱۰۸ History، Pointer mismatch و Parent mismatch صفر دارد؛
  بنابراین Projection جاری clean است، نه اینکه Audit حذف‌شده کامل باشد.
- ۴۰۲ History غایب بدون Delete retained در یک Batch تاریخی ۲۰۲۴-۰۳-۲۷ قرار
  دارند و به Undo یا bypass نسبت داده نشدند.
- Runtime دو Assembly هم‌هش و پنج Method/۷۱۴ Instruction را بدون Load/Execute
  بررسی کرد: Legacy و Adapter سیگنال تراکنش/Commit/Rollback دارند، اما Undo فرم
  New یک Instruction stub است و انتخاب Runtime فرم معلوم نیست.
- دو Extractor، دو Artifact، سند، هشت تست، checkpoint و `R-073` High افزوده شد؛
  رجیستر ۷۳ ریسک (۴۱ بحرانی/۲۹ بالا/۳ متوسط)، Traceability ۲۸۷ اتصال و صفر
  Command-ready دارد.

## ۲۰۲۶-۰۸-۲۹ — Undo تخریبی چک دریافتی و Projection مبتنی بر Trigger

- Procedure اصلی پس از Validation، History جاری را Delete می‌کند و در شاخه
  Previous=8/current=1 یک History دوم را نیز پاک می‌کند؛ Event جبرانی ندارد.
- Triggerهای فعال Delete/Insert مالک تغییر `IsLast` هستند؛ Master ستون وضعیت
  جاری ندارد. Wrapper Desktop تراکنش دارد ولی Rollback token صریح SQL ندارد.
- Log از ۱۴٬۷۱۱ Delete، تعداد ۱٬۵۰۲ فرمان نامزد Undo و ۲۲ head دوحذفی را نشان
  داد: ۱٬۵۲۴ ردیف حذف‌شده؛ سه‌ماهه ۴۷۱ فرمان/۴۷۵ ردیف است.
- Snapshot ۲۳٬۸۲۲ چک/۱۰۶٬۱۳۱ History با یک IsLast=max و chain mismatch صفر
  است. ۲۵۲ شکاف Insert-only historical به هیچ علت خاصی نسبت داده نشد.
- دو Assembly هم‌هش و شش Method/۷۰۰ Instruction بدون Load/Execute بررسی شد؛
  هر دو فرم Wrapper را صدا می‌زنند و دو Adapter Transaction تو‌در‌تو دارند.
- دو Extractor، دو Artifact، سند، نه تست، checkpoint و `R-074` High افزوده شد؛
  رجیستر ۷۴ ریسک (۴۱ بحرانی/۳۰ بالا/۳ متوسط)، Traceability ۲۹۱ اتصال و صفر
  Command-ready دارد.

## ۲۰۲۶-۰۸-۲۹ — حذف Master چک دریافتی و مرز حذف Receipt

- ده Module منتخب و هفت Candidate حذف مستقیم Master فقط از کاتالوگ Clone
  Fingerprint شدند. سه Contract اصلی `uspCHQDelete`، View trigger و
  `usp_sdsnet_Receipt_Save` از نظر Transaction/Cleanup متفاوت‌اند.
- ۳۱ Master delete لاگ‌شده، ۳۱ Master غایب و صفر mismatch به‌دست آمد؛ ۱۱ حذف
  سه‌ماهه است. همه History-delete lookback دارند، ولی فقط ۲۷ مورد جفت بلافاصله‌اند
  و چهار مورد داخل Batch چندچکی قرار دارند.
- ۱۹ Receipt-delete batch دقیقاً ۲۳ Master و ۲۳ History دارد. هفت Master با
  Receipt UPDATE و یک Master اخیر بدون tail بعدی جدا ثبت شد.
- ۲٬۳۵۱ Receipt delete retained و ۲۳۸ مورد سه‌ماهه‌اند؛ پنج Batch اخیر Master
  cleanup دارند. شباهت ساختاری با Receipt_Save، Attribution قطعی نیست.
- IL هش‌سنجی‌شده یک Assembly و دو Method/۳۴ Instruction را خواند: Legacy
  Confirmation→DataRow.Delete→Update دارد؛ New فقط Confirmation signal دارد.
- FKهای NO_ACTION/CASCADE و Cascade شدن `tblRChequeLog` ثبت شد. پنج جدول منتخب
  هیچ Temporal/CDC/Change Tracking ندارند.
- دو Extractor، دو Artifact، سند، نه تست، checkpoint و `R-075` High افزوده شد؛
  رجیستر ۷۵ ریسک (۴۱ بحرانی/۳۱ بالا/۳ متوسط)، Traceability ۲۹۵ اتصال و صفر
  Command-ready دارد.

## ۲۰۲۶-۰۸-۲۹ — وضعیت Confirm/Unconfirm/Delete سند انبار

- ده ماژول SQL و پنج جدول منتخب فقط‌خواندنی بررسی شد. Confirm و Unconfirm هر دو
  پیش از Transaction اعتبارسنجی می‌کنند، ولی مرز Commit/After و Cleanup نوع ۱۵
  متفاوت است؛ Save می‌تواند Confirm را داخل Transaction بیرونی فراخوانی کند.
- Triggerهای Header و Item Projection موجودی را می‌نویسند؛ Replication bypass،
  `XACT_ABORT OFF` و skip انواع ویژه در قرارداد ثبت شد.
- Audit برابر ۷۵٬۵۶۹ Confirm، ۱۳٬۰۲۱ Unconfirm و ۲۷٬۴۵۰ Delete است؛ سه‌ماهه
  ۸٬۸۲۲/۱٬۷۷۱/۳٬۲۰۰. Delete مستقیمِ confirmed بدون Unconfirm صفر است.
- Snapshot ۹۶٬۴۹۵ confirmed و هفت unconfirmed از ۹۶٬۵۰۲ Header دارد؛ ۱۵ شکاف
  insert-only absent تاریخی، بدون مورد سه‌ماهه، جدا نگه داشته شد.
- IL دو Assembly هم‌هش، ۱۲ Method و ۵۹۶ Instruction دو خانوادهٔ Adapter procedure
  و Dynamic writer را نشان داد؛ Runtime callsite و Physical transaction مشترک
  اثبات نشد.
- مقایسهٔ Cardex-only تعداد ۱٬۵۹۴ difference دارد، ولی فرمول رسمی همان‌ها را
  تعهد فروش باز می‌شناسد و Residual نهایی صفر است؛ attribution به مسیر سند انجام نشد.
- دو Extractor، دو Artifact، سند، نه تست، checkpoint و `R-076` Critical افزوده
  شد؛ رجیستر ۷۶ ریسک (۴۲ بحرانی/۳۱ بالا/۳ متوسط)، Traceability ۳۰۰ اتصال و صفر
  Command-ready دارد.

## ۲۰۲۶-۰۸-۲۹ — Projection موجودی و اعتبارسنجی پیام‌محور After

- ده Module SQL هش‌سنجی شد. Confirm مستقیم Commit-before-After دارد و Unconfirm
  After-before-Commit؛ هر دو AfterMsg را بدون Abort guard append می‌کنند.
- After بدون Transaction/Throw، چهار Validator را با ۹ NOLOCK فراخوانی می‌کند؛
  type-20 batch update پیش از Validation و skip انواع ۱۲/۱۳ ثبت شد.
- Matrix پنجاه‌ردیفی/سی‌نوعی Cardex شامل ۲۷ جهت مثبت، ۲۲ منفی و یک صفر است.
- Header/Item projection و StockGoods guard فعال‌اند؛ Guard set-based ولی دارای
  Session/Replication bypass است. هیچ استفادهٔ جاری از bypass استنتاج نشد.
- Snapshot ۶۷٬۱۶۱ Projection با صفر component منفی و فرمول رسمی با Residual صفر
  است؛ پس Incident جاری ادعا نشد.
- Extractor، Artifact، سند، هشت تست، checkpoint و `R-077` Critical افزوده شد؛
  رجیستر ۷۷ ریسک (۴۳ بحرانی/۳۱ بالا/۳ متوسط)، Traceability ۳۰۵ اتصال و صفر
  Command-ready دارد.

## ۲۰۲۶-۰۸-۲۹ — صدور، لغو نرم و حذف فیزیکی خروج توزیع

- ده Module SQL برای create/remove/merge/rollback و Triggerهای حذف hash-pinned
  شدند. Create و Remove تراکنش محلی کامل ندارند؛ Create کنترل Cardex را پس از
  چند write انجام می‌دهد و Remove خروج را soft-cancel می‌کند.
- Snapshot ۳۳٬۹۴۵ خروج شامل ۲۴٬۰۳۵ فعال و ۹٬۹۱۰ لغوشده است. Crosswalk فعال با
  Voucher نوع ۶۰ دقیق و cleanup لغو بدون Voucher/Sale link باقی‌مانده است.
- ۹٬۹۱۰ لغو همگی Delete نوع ۶۰ دارند؛ ۹٬۸۹۵ مورد و هر ۱٬۴۴۲ مورد اخیر در پنج
  ثانیه جفت‌اند. این adjacency انتساب قطعی Procedure/actor نیست.
- هشت خروج و شش Dist تاریخی March 2024 غایب‌اند؛ قبل از Triggerهای حذف فعلی،
  بدون مورد اخیر و با صفر status-chain break. سه مسیر حذف فیزیکی capability
  دارند، نه attribution تاریخی.
- IL سه Assembly/۱۱ Method/۱٬۲۰۱ Instruction نشان داد UI صدور و لغو Commit دارد،
  Adapterها بدون Commit Procedure را می‌خوانند، enlistment مشترک ثابت نیست و
  Merge مالک تراکنش صریح ندارد.
- دو Extractor، دو Artifact، سند، هشت تست، checkpoint و `R-078` Critical افزوده
  شد؛ رجیستر ۷۸ ریسک (۴۴ بحرانی/۳۱ بالا/۳ متوسط)، Traceability ۳۱۰ اتصال و صفر
  Command-ready دارد.

## ۲۰۲۶-۰۸-۲۹ — تراکنش و State تبدیل Order به Sale

- هفت Module SQL شامل Orchestrator/Core و Triggerهای Detail/Cancel/Stock/Delete
  بررسی شد. Orchestrator mode-dependent rollback دارد و Core تراکنش محلی ندارد.
- Runtime سه Assembly/پنج Method/۱٬۰۵۵ Instruction، Commit تو‌در‌توی Business و
  Adapter و overload مستقیم Core را نشان داد؛ Transaction enlistment ثابت نشد.
- Snapshot ۲۷۵٬۹۹۵ Sale، ۱۸٬۰۰۹ Order چندattempt و صفر چند-active/Pointer یتیم
  دارد. ۴۰٬۰۵۹ Sale و ۷٬۷۰۲ لغو در سه ماه ثبت شده است.
- ۲۶٬۶۱۸ مورد از ۲۶٬۶۲۴ اختلاف Header/Detail semantic cancel projection است؛
  شش active و سه cancelled exception تاریخی و صفر مورد اخیر باقی ماند.
- Attempt timing تعداد ۹٬۸۰۹/۹ شکاف دوطرفه دارد. ۶۴۰ Delete retained شامل ۱۱۲
  مورد اخیر و ۱۸ absent بدون Delete همگی تاریخی‌اند؛ attribution انجام نشد.
- دو Extractor، دو Artifact، سند، هشت تست، checkpoint و `R-079` Critical افزوده
  شد؛ رجیستر ۷۹ ریسک (۴۵ بحرانی/۳۱ بالا/۳ متوسط)، Traceability ۳۱۶ اتصال و صفر
  Command-ready دارد.

## ۲۰۲۶-۰۸-۲۹ — لغو Sale، حذف Payment و پیوندهای باقی‌مانده

- پنج Module SQL هش‌سنجی شد. Procedure لغو تراکنش محلی دارد و Triggerها مالک
  Payment cleanup، Detail event، Order/Sale update و Stock projection هستند.
- Snapshot ۶۱٬۰۲۲ Sale لغوشده با صفر Payment مستقیم، ۳۴٬۴۰۱ Exit/Dist link
  و ۳۴٬۶۳۰ selected Order pointer را نشان داد؛ لینک‌ها corruption نام‌گذاری نشدند.
- ۶۱٬۰۱۹ Terminal detail در مجموعهٔ semantic 0/3 و سه استثنای تاریخی وجود دارد؛
  استثنای اخیر صفر است.
- IL سه Assembly/چهار Method/۳۹۰ Instruction، reason-before-handler، delegate
  باریک و Adapter Execute بدون Commit/RollBack صریح را ثابت کرد؛ enlistment
  تراکنش محلی Procedure با Context مدیریت‌شده ثابت نشد.
- دو Extractor، دو Artifact، سند، هفت تست، checkpoint و `R-080` Critical افزوده
  شد؛ رجیستر ۸۰ ریسک (۴۶ بحرانی/۳۱ بالا/۳ متوسط)، Traceability ۳۲۲ اتصال و صفر
  Command-ready دارد.

## ۲۰۲۶-۰۸-۲۹ — صدور/لغو Sales Return، Voucher نوع ۱۰ و Credit

- نه Module SQL و سه Assembly/پنج Method/۴۰۴ Instruction hash-pinned شدند.
- ۱۳٬۹۱۳ active return همگی یک Voucher نوع ۱۰ confirmed دارند؛ ۱۷۸ cancelled
  return هیچ Voucher/Payment ندارند ولی همگی VocherFlag=1 را حفظ کرده‌اند.
- Save و Generator تراکنش/Savepoint دارند؛ Generator کنترل‌های پس از Insert نیز
  دارد. CancelVoucher تراکنش محلی و Delete+Insert graph دارد، CancelHeader جداست.
- Runtime مسیر Cancel Adapter را با Context+Commit بدون RollBack صریح و مسیر
  Generate را Query بدون Context/Commit صریح نشان داد؛ enlistment ثابت نشد.
- Audit برابر ۱۴٬۰۹۱ current/logged و صفر Delete/Absent است؛ سه delete candidate
  attribution نیست. دو Extractor، دو Artifact، سند، شش تست، checkpoint و
  `R-081` Critical افزوده شد؛ رجیستر ۸۱ ریسک/۳۲۸ اتصال/صفر Command-ready شد.

## ۲۰۲۶-۰۸-۲۹ — Snapshot ووچر Sale و مسیر Reverse Conversion

- شش Module SQL و سه Assembly/چهار Method/۲۴۳ Instruction hash-pinned شدند.
- ۲۶۶٬۱۸۳ voucher-number و Snapshot یک‌به‌یک‌اند؛ mismatch، duplicate و orphan
  صفر و تعداد Item برابر ۲٬۱۲۸٬۲۵۳ است.
- ۶۰٬۶۹۸ cancelled sale Snapshot را حفظ کرده‌اند. ۱۱٬۷۵۰ active final sale،
  شامل ۱٬۵۳۷ مورد سه‌ماهه، اختلاف Amount جاری/Snapshot دارند و بدون Rule نسخه
  corruption نام‌گذاری نشدند.
- Fill Snapshot بدون Transaction محلی ولی زیر Orchestrator سفارش است. Reverse
  procedure تراکنش محلی کامل دارد؛ مسیر Managed Contextهای جدا و بدون Commit/
  RollBack صریح منتخب دارد و enlistment مشترک ثابت نشد.
- Audit شامل ۱۸ absent تاریخی، صفر absent اخیر و صفر retained delete است؛ یک
  delete candidate فقط capability است. دو Extractor، دو Artifact، سند، هفت تست،
  checkpoint و `R-082` Critical افزوده شد؛ رجیستر ۸۲ ریسک/۳۳۴ اتصال/صفر
  Command-ready شد.

## ۲۰۲۶-۰۸-۲۹ — Sale → PreVoucher → Batch → Journal و Watermark صدور

- سه Module SQL hash-pinned و Crosswalk فقط‌خواندنی ۲۰۲٬۶۳۶ Source/۶۲۵٬۸۳۹
  Line/۱۰۱٬۶۴۹ Batch استخراج شد؛ همه Sourceها متوازن و هر لینک دارای یک Journal
  فعال است.
- ۱۰٬۱۲۲ فروش فعال نهایی ماه ۱۴۰۵/۰۵ هنوز Source ندارند، در حالی که دو ماه قبل
  پوشش کامل‌اند؛ این Pending watermark است، نه incident. یک outlier ۱۴۰۳/۰۱
  جدا نگه داشته شد.
- ماتریس Snapshot/Accounting فعال به‌ترتیب neither=480، accounting-only=9,008،
  snapshot-only=9,643 و both=193,628 است. Creator Snapshot را dependency ندارد.
- View فقط Sale غیرلغوشده/شماره‌دار/Item فعال را با NOLOCK می‌خواند؛ صفر Source
  لغوشده تاریخچه را ثابت نمی‌کند. ۳۷۰ Batch چندSource و ۱۷۵٬۰۴۲ عدم برابری مستقیم
  Debit/SaleAmount به‌عنوان policy/rule semantics حفظ شدند.
- Extractor، Artifact، سند، هفت تست، checkpoint و `R-083` Critical افزوده شد؛
  رجیستر ۸۳ ریسک/۳۳۸ اتصال/صفر Command-ready شد.

## ۲۰۲۶-۰۸-۲۹ — Crystal invoice template و PrintedDoc audit

- دو Module SQL و سه Assembly/نه Method/۱٬۰۱۱ Instruction hash-pinned شدند.
- فرم Template تنظیم‌شده را به Crystal می‌دهد؛ Engine آن را Load و با Connection
  جاری Refresh می‌کند. SQL/Formula داخل فایل است، نه DataAccess.
- شش Template فعال در ۸۸ فایل سه ریشهٔ Deployment match نشدند؛ runtime failure
  ادعا نشد ولی Template content و Result parity باز ماند.
- PrintedCompleted سپس Command نوشتن DocType=2 را فعال می‌کند. ۳۰۸٬۴۳۲ event روی
  ۱۴۴٬۸۴۷ Sale، تعداد ۳۴٬۸۴۰ reprint و بیشینه ۲۶ ثبت شد.
- ۱۴۳ event روی ۴۵ Sale لغوشده پس از terminal time، شامل دو مورد اخیر، بدون
  unauthorized attribution ثبت شد. VOID/archive policy لازم است.
- یک range bug در sibling GetList و یک Procedure hard-coded بدون caller/literal
  به‌عنوان capability-only جدا شد. دو Extractor، دو Artifact، سند، هفت تست،
  checkpoint و `R-084` Critical افزوده شد؛ رجیستر ۸۴ ریسک/۳۴۳ اتصال/صفر
  Command-ready شد.

## ۲۰۲۶-۰۸-۲۹ — ماتریس cross-domain نتیجهٔ فرمان و دوام تغییر

- ۱۲ Artifact معتبر قبلی در Builder آفلاین جدید به ۱۰ case و ۱۰ outcome class
  تبدیل شد؛ هیچ اتصال DB، اجرای UI/Procedure/Trigger یا Assembly Load رخ نداد.
- صدور حسابداری روی business-error هم Commit managed دارد، ولی خطا پیش از Write
  است؛ انتقال حسابداری می‌تواند Cleanup پیش از Validation را با همان Result
  غیرexceptional Commit کند.
- Confirm موجودی After message را پس از Commit و Unconfirm آن را پیش از Commit
  اما بدون Abort guard می‌گیرد. Desktop برگشت خرید برعکس، پیام غیرخالی را پیش از
  Commit به Validation failure تبدیل می‌کند.
- صدور برگشت فروش late-validation را با Transaction/Savepoint محلی Rollback
  می‌کند؛ توزیع و تبدیل سفارش Context/Commitهای Caller یا تو‌در‌تو با enlistment
  فیزیکی اثبات‌نشده دارند؛ لغو فروش مالک SQL روشن دارد.
- ثبت چاپ بعد از `PrintedCompleted` یک Commit جداست و باید Partial-success و
  reconciliation داشته باشد.
- هشت invariant مقصد دربارهٔ Outcome تایپ‌شده، Transaction owner، postcondition،
  Outbox و وضعیت `UNKNOWN` ثبت شد. پنج تست focused سبز شد. Risk تازه‌ای ساخته
  نشد، چون این ماتریس قرارداد مشترک ریسک‌های موجود است، نه finding مستقل.

## ۲۰۲۶-۰۸-۲۹ — Guardهای Idempotency و Retry

- ده Procedure پراثر و هفت جدول هدف از Catalog فقط‌خواندنی fingerprint شدند؛
  هیچ Procedure اجرا نشد و هیچ Definition/Filter/Index name خام ذخیره نشد.
- هر ده فرمان فاقد پارامتر retry identity هستند و شش مورد allocator دارند.
- Sale active-per-order Guard دیتابیسی ندارد ولی ۲۱۴٬۹۷۳ گروه جاری همگی تک‌فعال‌اند.
- RetSale active-source، Exit active، Voucher type-10 source/health و PreVoucher
  line signature Unique guard دارند؛ duplicate مشاهده‌شدهٔ Guardها صفر است.
- cohort فعال RetOrderRef صفر بود؛ وجود Constraint ثابت شد ولی Runtime data parity
  آن از Snapshot قابل آزمون نبود.
- PrintedDoc فاقد semantic unique است و ۵۵٬۷۹۲ repeated group دارد؛ این‌ها
  reprint/attempt history هستند و duplicate incident نام‌گذاری نشدند.
- TourHistory type 8 تعداد ۱۳۸ و type 10 تعداد ۷۰ duplicate entity group دارد؛
  Unique فقط یک Type دیگر را پوشش می‌دهد.
- هفت تست focused سبز شد. شاهد تازه به `R-006` متصل شد و Baseline شمارشی ثابت ماند.

## ۲۰۲۶-۰۸-۲۹ — فلگ‌های Policy تبدیل سفارش و Partial conversion

- سه Procedure SQL و سه Assembly به‌صورت فقط‌خواندنی/Static بررسی شدند؛ هیچ
  Procedure یا فرم اجرا و هیچ Assembly Load نشد.
- ۱۹ حضور پارامتر در سه Command و هشت Policy contract ثبت شد. مهم‌ترین کشف این
  بود که `chkNotStock=1` اقلام کسری را از Temporary conversion set حذف می‌کند؛
  این رفتار Partial conversion است، نه skip سادهٔ موجودی.
- ContractPrice، UserPrice، زوج‌های Customer/Dealer credit و MaximumLimit شاخه‌های
  مستقل دارند. زوج اعتبار فقط در حالت هر دو ۱ bypass می‌شود؛ در غیر این صورت
  مقادیر از تنظیمات DC بازنویسی می‌شوند.
- `IgnoreValidateExpDate` declared-only و `WithOutRollback` محدود به یک شاخهٔ
  doomed transaction ثبت شد تا از انتقال نام/معنی اشتباه به API جلوگیری شود.
- IL دو مسیر Caller را جدا کرد: فرم گروهی کنترل‌های Stock/Credit/Limit را می‌خواند
  و Save عادی فقط Stock را می‌گیرد؛ هر دو مسیر قیمت‌ها را صفر می‌فرستند.
- دو Extractor، دو Artifact، سند، هفت تست و checkpoint مستقل افزوده شد. شواهد به
  `R-079` متصل و Baseline ۸۴ ریسک/۳۴۳ اتصال بدون inflation حفظ شد.
- ادامهٔ همان مرز، `SetDefaultForCheckEdits` را در ۳۱ Method/۱٬۳۶۶ event ایستا
  بازسازی کرد: پنج کنترل اعتبار/سقف نگاشت ۰/۱/۲ متفاوت از Stock دارند.
- متد `ApplySetadPermission` فقط SiteType/DCRef و Select-button را لمس می‌کند و
  هیچ Permission call نام‌دار ندارد؛ نبود Gate بیرونی ادعا نشد.
- Snapshot ناشناس دو DC، دو Profile و پنج سلول NULL در یک Profile نشان داد؛ هر
  دو Stock=2 هستند. شش Getter Policy در IL Int32 غیرNullable‌اند، اما Null
  materializer حل نشد و SQL بدون coalesce می‌تواند شرط Validator را UNKNOWN کند.
- دو Extractor/Artifact دیگر به همان سند، تست و checkpoint افزوده شد؛ این مرحله
  finding قبلی را عمیق‌تر کرد و Risk count را تغییر نداد.

## ۲۰۲۶-۰۸-۲۹ — Operation date و finality تبدیل سفارش

- شش Module SQL و دو Assembly/شش Method/۱٬۴۲۲ Instruction به‌صورت فقط‌خواندنی
  و hash-pinned بررسی شد؛ هیچ Procedure، Form یا Assembly اجرا نشد.
- `CreateSaleDate` از Session می‌آید و در پنج خانوادهٔ کنترل/محاسبهٔ هسته مصرف
  می‌شود. شماره سفارش و تاریخ، Validatorهای جدا هستند.
- `IsSaleDateOpen` برای سفارش معمولی IsClosed و `SaleDate<=LastDate` را رد می‌کند؛
  انواع ۱۰۰۷/۱۰۰۸ آن را skip می‌کنند و نبود ردیف مرزی رد صریح ندارد.
- هر دو نوع ۱۰۰۷/۱۰۰۸ در master پیکربندی شده‌اند ولی Order/Sale فعلی و سه‌ماهه
  آن‌ها صفر است؛ نبود داده به‌عنوان retire decision تفسیر نشد.
- SQL FetchReason=2 ترتیب `LastDate,OprDate` را ثابت کرد. Operandهای Local در IL
  نشان دادند هر دو شاخهٔ خودکار خروجی دوم OprDate را در Session می‌گذارند.
- Snapshot ناشناس ۱۰ Profile/یک DC/صفر Orphan و سه ردیف SysRef=1 دارد؛ دو دوره
  بسته و یک دوره باز، بدون تاریخ خالی. رخداد fail-open جاری ادعا نشد.
- دو Extractor، دو Artifact، سند، تست و checkpoint افزوده و به `R-079` متصل شد؛
  Baseline شمارشی بدون inflation حفظ شد.

## ۲۰۲۶-۰۸-۲۹ — Authorization و resource scope تبدیل Order به Sale

- چهار Module SQL و سه Assembly/۱۲ Method منتخب hash-pinned شدند؛ اجرای عملیاتی
  و Assembly load صفر بود.
- فرم تبدیل و هفت متد conversion منتخب zero named permission/access call دارند؛
  BaseForm/Menu بیرونی در محدودیت باز نگه داشته شد.
- Helper حقوق نوع سفارش هفت Action غیرتبدیل دارد و ده Callsite آن فقط در فرم‌های
  Order/LoanOrder list مشاهده شد.
- AreaAccess سرور شرطی است و Clone global key فعال صفر، GeneralConfig true صفر،
  SaleUserAccess دو ردیف، direct right برابر ۱۹۰ و group right برابر ۱۲۰ دارد.
- پذیرش UserRef در Core Authorization نام‌گذاری نشد. قرارداد deny-first Action +
  Resource scope برای تبدیل عادی/جزئی/Override/تاریخ ثبت شد.
- دو Extractor، دو Artifact، سند، تست و checkpoint به `R-079` افزوده شد؛ شمارش
  Risk و Traceability ثابت ماند.

## ۲۰۲۶-۰۸-۲۹ — Thunderstruck DataContext و transaction ownership

- خود کتابخانه و ۵۹ Assembly مدیریت‌شده با PE/IL اسکن شد؛ Load/Execute و اتصال
  دیتابیس صفر بود.
- Enum `Begin=0/No=1`، default=No، Provider/Connection تازه برای هر Context،
  BeginTransaction فقط در mode صفر و Commit/Rollback مشروط به DbTransaction ثابت شد.
- Setter سفارشی Provider/ConnectionFactory/TransactionalContext در Package صفر است.
- Discount V2 یک Context No برای EVC و سپس Context Begin جدا در Adapter تبدیل دارد؛
  مرحلهٔ اول Commit no-op و اتصال فیزیکی مشترک false است.
- Overload مستقیم Core در fallback پیش‌فرض Context No و بدون Commit است؛ V2 با
  token دقیق overload Adapter را فراخوانی می‌کند.
- Extractor، Artifact، سند، تست و checkpoint به `R-079` متصل شد؛ incident تاریخی
  ادعا نشد و Baseline شمارشی ثابت ماند.

## ۲۰۲۶-۰۸-۲۹ — EVC persistence و شاخهٔ Discount V2

- سه Assembly هدف و تمام ۵۹ Assembly managed به‌صورت hash-pinned/static اسکن شد؛
  سه callsite مهم شامل constructor helper، setter فلگ و entry V2 ثبت شد.
- تنها setter تایپ‌شدهٔ `CalcForDiscountV2` داخل constructor است و مقدار اولیه صفر؛
  entry واقعی فرم `AcceptCommandDiscountV2` است.
- پنج SQL module فقط‌خواندنی نشان دادند شاخهٔ صفر دوباره staging، EVC و جدول
  `#SaleItemPaymentUsance` را می‌سازد و `usp_CreateSaleByEVC` از آن به جدول پایدار
  payment-usance می‌نویسد.
- Managed writer نام `#SaleSaleItemPaymentUsance` دارد؛ هیچ تعریف SQL و هیچ
  managed CREATE literal برای این نام دوگانه وجود ندارد. clone فعلی ردیف پایدار
  payment-usance ندارد، پس frequency/incident تاریخی نتیجه‌گیری نشد.
- دو Extractor، دو Artifact، سند دامنه و هفت تست افزوده شد. نتیجه، ریسک جدید
  مستقل نساخت و به atomicity/integrity موجود `R-079` متصل شد.
- بررسی تکمیلی فرضیهٔ concurrency را رد کرد: تمام دسترسی‌های `globalCalcData`
  instance-field هستند و factory یک EVCHandler تازه می‌سازد؛ finding نشت
  process-global ثبت نشد.
- count ایستای مسیر load برابر ۳۵ call مستقیم DataContext ثبت شد؛ این عدد
  frequency اجرا/latency نیست و به‌عنوان budget معماری مقصد استفاده می‌شود.
- فرضیهٔ blocking مستقیم UI رد شد: مسیر V2 زیر BackgroundWorker اجرا و progress/
  cancellation را گزارش می‌کند؛ telemetry latency همچنان لازم است.
- cancellation checkpoint پیش از conversion است و cancel داخل DB ندارد؛ قرارداد
  partial-batch/StopAfterCurrent برای مقصد ثبت شد.
- snapshot کلید V2 را موجود ولی خاموش نشان داد. قابلیت debug-export بدون permission
  نام‌دار، full CalcData را JSON+GZip در مسیر deployment-adjacent می‌نویسد؛ مسیر
  فعلی share وجود نداشت و رخداد جاری ادعا نشد.
- debug mode قبل از managed promotion، legacy `usp_DoEVC` را اجرا می‌کند؛ پس
  instrumentation خالص نیست و observer-effect به قرارداد تست مقصد اضافه شد.

## ۲۰۲۶-۰۸-۲۹ — Query map و read consistency تخفیف V2

- `.cctor` QueryHelper به ۴۲ زوج دقیق ldstr/stsfld تجزیه شد؛ raw SQL ذخیره نشد.
- ۱۷ reference/rule، ده order-request و ۱۵ مسیر دیگر به ۴۴ dependency نگاشت شدند؛
  هر ۴۱ object پایدار در Catalog فقط‌خواندنی حل شد.
- ۲۷ query template با ۳۱ format slot ثبت شد؛ command نوشتنی/exec صفر است.
- RCSI/Snapshot روی clone روشن است، ولی DataContext بدون transaction مجموعهٔ readها
  را در snapshot واحد قرار نمی‌دهد؛ خطر mixed-version calculation به قرارداد
  PricingSnapshot مقصد اضافه شد.

## ۲۰۲۶-۰۸-۲۹ — موتور الگوریتمی Discount V2 و `SqlCondition`

- سه DLL خارج از inventory پیشین VN پیدا و مستقل hash-pin شدند؛ شمارش کامل آن‌ها
  ۷۱۳ Type و ۷٬۱۵۶ Method است. هیچ Assembly اجرا یا Load نشد.
- ۲۲ Method منتخب/۳٬۷۴۳ Instruction، entry و ترتیب validation/usance/price/statute/special-value و
  مراحل اعمال Discount/Prize را به‌صورت IL ثابت کردند.
- هر دو AdvanceCondition helper مقدار `TypeSpecRow.SqlCondition` را escape و سپس
  با `sp_executesql` و `@EvcId/@Result` اجرا می‌کنند. نسخه SDS نام‌های EVC قدیم را
  به Tempها rewrite می‌کند؛ pairing دقیق تک‌تک Replaceها ادعا نشد.
- دو مسیر load منتخب، Constructor Helper نوع SDS را دقیقاً پیش از Constructor
  `CalcData` صدا می‌زنند؛ Helper غیر-SDS در این دو مسیر reference ندارد.
- چهار جفت Rewrite با offset دقیق حل شد. `sle.tblEvc` پیش از
  `sle.tblEvcItem[/Statutes]` است و آن‌ها را برای متن lowercase shadow می‌کند.
  Current corpus base ref صفر، `#tblTempEvc`=۷۹۳ و `EvcItemFull`=۵۲ Rule دارد؛
  incident جاری ادعا نشد.
- `FillSimpleEvcSharpSummary` یک delegate به validation دارد، ولی SDS helper
  candidateها را enumerate و برای هرکدام GetValue پویا اجرا می‌کند؛ Result=true
  نیز AllRawEntity+Execute روی include staging دارد. N+1 ساختاری ثبت شد، نه latency.
- CalcData ctor منتخب BackOfficeType=1 را hard-code می‌کند و Gate مقدار ۱ را به
  ValidateAdvanced می‌فرستد؛ این مسیر برای order-to-sale فعال است.
- SDS helper context ورودی را در base ذخیره و Validate آن را در صورت non-null
  انتخاب می‌کند. مسیر منتخب context بدون transaction EVC را تزریق می‌کند؛ پس
  per-candidate queryها transaction snapshot مشترک ندارند.
- Snapshot aggregate-only روی Clone READ_ONLY نشان داد `SLE.tblDiscount` از ۵٬۰۹۸
  Rule، ۸۴۵ شرط غیرخالی و ۶۲۶ شرط فعال دارد، ولی فقط ۴۴ متن متمایز بر مبنای Hash.
- ۸۴۴ شکل SELECT، ۸۴۳ استفاده `@EvcId`، ۸۴۴ استفاده `@Result` و ۷۹۳ ارجاع Temp
  دیده شد. DML نوشتنی، DDL/Permission و external/delay primitive صفر بود.
- متن/ID Rule persist نشد. یافته به مرز integrity `R-079` متصل می‌شود و طراحی
  مقصد را به DSL نوع‌دار، version/publish approval و Golden Case ملزم می‌کند.
- پروفایل ساختاری خانواده‌ها چهار schema object، یک temp object و ۲۳ column
  candidate معتبر Catalog استخراج کرد، بدون Literal یا ID Rule.
- Reconciliation سه‌ماهه نشان داد از ۴۴ خانواده فقط دو خانواده/سه Rule روی ۳۸
  فروش اثر retained دارند: ۴۷۱ ردیف Discount، صفر Addition و سهم ۰٫۱۵۶۸٪ از کل
  ۳۰۰٬۳۶۱ اثر. نبود اثر، اثبات اجرا نشدن یا قابل حذف بودن ۴۲ خانواده دیگر نیست.
- هر دو خانوادهٔ دارای اثر `FROM EvcItemFull`، `EXISTS` و `@EvcId/@Result` دارند؛
  خانوادهٔ بزرگ فقط `ID` و خانوادهٔ کوچک `ID/BrandName` را لمس می‌کند. Literal
  شرط و برند ذخیره نشد.
- ۶۲۶ Rule Flag فعال دارند، اما فقط ۵۷ Rule/۱۶ خانواده امروز date-effective‌اند؛
  ۲۶۷ Rule/۳۶ خانواده با پنجره سه‌ماهه فقط date-overlap دارند. IsActive تاریخی
  از Snapshot فعلی استنتاج نشد.
- DeactivationLog دارای ۱٬۳۱۳ ردیف/۱٬۳۱۳ Rule و همگی transition به صفر است؛
  activation صفر. Advancedها ۲۱۸ deactivation قبل و دو مورد داخل پنجره دارند؛
  یک Rule فعال فعلی با Log قدیمی ثابت می‌کند reactivation کامل ثبت نشده است.
- دو Rule `ID` مصرف‌شده امروز فعال‌اند؛ Rule `ID/BrandName` مصرف‌شده داخل پنجره
  غیرفعال شده و ۲۳ اثر پیش از/در همان تاریخچه retained دارد.
- Aggregate object profiles دو خوشه ساخت: ۷۹۳ Rule/۹ خانواده روی temp+history
  (`#tblTempEvc/tblDiscount/tblDisSale/tblOrderHdr`) و ۵۲ Rule/۳۵ خانواده روی
  `EvcItemFull`. خوشه اول ۴۱ effective فعلی ولی صفر اثر retained سه‌ماهه دارد؛
  هر سه Rule/۴۷۱ اثر مشاهده‌شده در خوشه دوم‌اند.
- قرارداد DSL به CurrentBasket و HistoricalRuleUsage تفکیک شد؛ zero retained
  effect با never-evaluated یا obsolete برابر نیست.

## ۲۰۲۶-۰۸-۲۹ — مسیر نویسندگی و اعتبارسنجی شرط تخفیف

- پنج DLL هش‌پین‌شده و ۳۲ متد/۲٬۱۸۳ Instruction بررسی شد. فرم اصلی
  `FormDiscountCondition` را باز و `FilterCondition` تأییدشده را در
  `SqlCondition` می‌نویسد؛ `CopyNew` دومین Setter منتخب است.
- Filter بصری به Dataset Where تبدیل می‌شود. OK ابتدا EVC temp context می‌سازد
  و سپس `ValidateUserBuiltCondition` را صدا می‌زند؛ Adapter اعتبارسنجی چهار
  `DataContext.Execute` با چهار شکل `sp_executesql` دارد. هیچ شرط واقعی اجرا یا
  متن/شناسه‌ای در Artifact نگهداری نشد.
- Save فرم پس از validation/business save، Commit می‌کند و Business save دو بار
  به `TypeSpecRow.SaveCommand` می‌رسد. BaseForm در Init با `HasPersmission`
  Enabled Toolbar را می‌سازد و Clickها Visible/Enabled را Gate می‌کنند؛ چهار
  Internal command و مسیرهای اختصاصی تخفیف Permission recheck ندارند. مرز قدیم
  UI-command gate است، نه Service authorization.
- `HasPersmission/HasPermission` فقط `UserPermissionS` نشست را با
  ClassName+AccessNodeKey یا AccessNodeId جست‌وجو و `HasAccess` را برمی‌گردانند؛
  Database call صفر است. Materialization اولیه Admin/Deny هنوز در این مرز نیست.
- کلیدهای Base منتخب `New/Edit/Delete/Print` هستند و سه فرمان Mutating را به
  Childهای Route وصل می‌کنند؛ `View` در این متد نیست و مصرف آن اثبات نشد.
- کلید مستقل Save در Base منتخب نیست؛ State ورودی New/Edit آن را غیرمستقیم Gate
  می‌کند و خود InternalSave هیچ Permission recheck ندارد.
- مقصد باید Draft/Review/Publish/Deactivate/Rollback را به مجوزهای مستقل API و
  Audit تغییرناپذیر تبدیل کند؛ Validation نباید SQL نویسنده را اجرا کند.
- Route دقیق `FormDiscount` به `DiscountRules/404` رسید و چهار Child قابل‌نمایش
  `View/New/Edit/Delete` دارد. Snapshot ناشناس ۱۴۱ کاربر فعال، هفت Admin bypass،
  پانزده Effective allow روی Root و هر Child، ۱۲۶ Neutral روی Root و صفر Deny
  صریح روی پنج Node نشان داد.
- هویت و Assignment ذخیره نشد؛ Count مساوی اثبات Principal مساوی نیست. Review یا
  Publish مستقل در Subtree وجود ندارد، پس Save قدیم چهارچشمی‌بودن را ثابت نمی‌کند.

## ۲۰۲۶-۰۸-۲۹ — بستن مرحله شناخت ۱۵ ساعته

- ۳۶ Checkpoint روز جاری بازخوانی شد؛ همه PASS هستند و هفت محور صریح هدف هرکدام
  Evidence passing دارند.
- Runner آفلاین جدید با plugin autoload خاموش، ۴۳ فایل `test_varanegar_*.py` را
  اجرا کرد: ۵۲۹ passed و یک warning غیرشکستی Pydantic.
- Baseline نهایی ۸۴ ریسک، ۵۰ Critical، ۳۱ High، سه Medium، ۳۴۳ نگاشت و صفر
  Command-ready module را بدون inflation ثبت کرد.
- Artifact نهایی هیچ اجرای عملیاتی، mutation وارانگار/NGT، ایجاد Write access یا
  Load/Execute اسمبلی گزارش نمی‌کند.
- سند تحویل:
  `VARANEGAR_15H_FINAL_HANDOFF_20260829_FA.md`؛ Artifact:
  `varanegar_15h_final_baseline_bundle_20260829.json`.

## ۲۰۲۶-۰۸-۲۹ — آغاز مرحله ۲۵ ساعته و Gap Map بدون Drift

- ۴۵ ورودی Manifest تحویل قبلی Hash شد و Drift صفر بود؛ استخراج بسته‌شده تکرار نشد.
- Crosswalk گزارش‌ها نشان داد ۲۰ قرارداد و ۱۷۵ Golden Case آفلاین وجود دارد، ولی
  Result parity و هویت SQL/پارامتر/Scope برای هر ۲۰ گزارش اثبات‌نشده است.
- این شکاف به‌عنوان اولویت اول، پیش از Truth Table باقیمانده و UAT Golden Case،
  ثبت شد و به ریسک‌های موجود `R-002/R-023/R-031` وصل شد؛ Risk جدید ساخته نشد.
- Builder، Artifact، سند، پنج تست و Checkpoint فقط‌آفلاین افزوده شد؛ اتصال دیتابیس،
  UI action، Assembly load/execute، Command عملیاتی و mutation همگی صفر بودند.

## ۲۰۲۶-۰۸-۲۹ — Binding دقیق ده گزارش موجودی `RPT-15`

- ده مسیر UI→Business→Adapter با PE/IL ایستا به ده Literal SQL Redacted رسید؛ فقط
  Object/Parameter/Hash ذخیره شد و متن خام SQL Persist نشد.
- Login و Clone پیش از Catalog query با READ_ONLY، can_update=0 و deny-write کنترل
  شدند. هر ده نام به یک Procedure یکتا، ۵۲ پارامتر و ۴۴ dependency رسید.
- مجموعه پارامترهای IL و Catalog در هر ده گزارش case-insensitive برابر بود؛ ۴۱
  Candidate قبلی برای این سطح به Binding دقیق کاهش یافت.
- Source-of-Truth واحد رد شد: خروجی‌ها Projectionهای Cardex/Stock/Open commitment/
  Reservation با Grain متفاوت‌اند. Result parity همچنان صفر و UAT فقط طراحی است.
- Artifact/دو Extractor/Builder/سند/شش تست/Checkpoint افزوده شد؛ Risk جدید ساخته
  نشد و `R-031` همراه ریسک‌های Drift/Projection/Stock reuse شد.

## ۲۰۲۶-۰۸-۲۹ — اصلاح `RPT-11` به External-template-owned

- چهار Method و ۱۱ Call از Artifact IL هش‌پین‌شده نشان داد فرم برگشت مسیر فایل
  پیکربندی را resolve و `ShowReportFact` را اجرا می‌کند.
- ۲۴ Candidate نامی قبلی به‌عنوان Binding دادهٔ گزارش رد شدند؛ Query/Formula داخل
  Template خارجی است و Result parity صفر باقی ماند.
- Artifact/Builder/سند/پنج تست/Checkpoint افزوده شد؛ Template خوانده/اجرا نشد و
  Risk تازه ساخته نشد.

## ۲۰۲۶-۰۸-۲۹ — `RPT-18`، دو Query دقیق و Print attempt پیش از Render

- دو DLL هش‌پین‌شده با PE/IL ایستا خوانده شد؛ دو Query به دو Procedure ICA دقیق
  رسید و Catalog READ_ONLY مجموعاً ۱۸ پارامتر/چهار dependency ثبت کرد.
- Master ورودی `@Where` و Dynamic SQL دارد؛ Detail ایستا است. Raw SQL ذخیره نشد.
- ترتیب `GetSelectedDocIds → InsertInTotblSdsNetPrintDoc → ShowReport` ثابت کرد
  Audit قدیم Attempt است، نه اثبات چاپ موفق.
- Artifactهای IL/SQL/Contract، سند، شش تست و Checkpoint افزوده شد؛ Risk جدید
  ساخته نشد و اجرای عملیاتی/mutation صفر بود.

## ۲۰۲۶-۰۸-۲۹ — `RPT-09`، Completion ناهمگون و Partial Success چاپ Batch

- ۱۱ Method UI و سه Method Business با PE/IL ایستا و Hash ثابت بررسی شد.
- هفت Render به چهار completion-gated و سه render-only تقسیم شد؛ چهار مسیر ترتیب
  ShowReport→PrintedCompleted→Completion command دارند.
- دو Completion path Commit و صفر Rollback محلی دارند. Orchestrator Batch چند
  خروجی را با Delay ترتیبی و بدون Transaction/Rollback Batch dispatch می‌کند.
- Truth Table، پنج Golden Case، Playbook، Artifact/دو Extractor/Builder/شش تست و
  Checkpoint افزوده شد؛ Risk جدید و اجرای عملیاتی صفر بود.

## ۲۰۲۶-۰۸-۲۹ — `RPT-05/07/08`، مرز مشترک Party Cardex

- شش Method از دو DLL هش‌پین‌شده و پنج شیء Catalog فقط‌خواندنی Crosswalk شدند؛
  حاصل ۳۹ پارامتر و ۶۶ dependency بود.
- Supplier، Customer base و Customer currency از هم جدا شدند؛ مسیر Centralized
  به Fararu تفویض می‌شود و Query محلی نیست.
- Reconciliation بر key-set، scope، business date، opening/period/closing و currency
  طراحی شد و شش Golden Case ناشناس افزوده شد.
- Formula/Result parity ادعا نشد، Risk جدید ساخته نشد و mutation/اجرای عملیاتی صفر بود.

## ۲۰۲۶-۰۸-۲۹ — `RPT-13`، گزارش سفارش تولید

- IL فرم، Query مستقیم `USP_SDSNET_ProductionOrderReport` را تأیید کرد؛ Catalog
  فقط‌خواندنی هشت پارامتر و پنج dependency ثبت کرد.
- انبار مبدأ و مقصد مستقل مدل شدند و نبود scope صریح User/AccYear در signature به‌عنوان
  شکاف اثبات مجوز/سال مالی، نه اثبات فقدان کنترل، ثبت شد.
- Truth Table، Reconciliation، Playbook، شش Golden Case، تست و checkpoint افزوده شد؛
  Procedure/Form/Export اجرا نشد و Risk جدید ساخته نشد.

## ۲۰۲۶-۰۸-۲۹ — `RPT-06`، Branch مشتری/کالا در گزارش مرکز تماس

- Gap صفر Candidate با binding IL دقیق و Catalog READ_ONLY بسته شد: یک Procedure،
  چهار پارامتر و ۱۰ dependency.
- `@Type` سه reference و ساختار branch دارد؛ labelهای UI دو mode را نشان می‌دهند،
  اما مقدار mapping حدس یا ذخیره نشد.
- Truth Table، Reconciliation، Playbook، شش Golden Case، هفت تست و checkpoint افزوده
  شد؛ Result parity، اجرای Procedure و mutation صفر ماند.

## ۲۰۲۶-۰۸-۲۹ — `RPT-14`، Generic GetAllView تا BatchNo SQL

- چهار Assembly هش‌پین‌شده زنجیره UI→generic adapter→view/entity inheritance→
  GetDataSPName→AllFast را اثبات کردند.
- Catalog READ_ONLY یک Procedure با ۱۸ پارامتر و ۱۸ dependency ثبت کرد؛ دو mode
  FetchReason بدون حدس مقدار مدل شدند.
- مرز quantity/date/export، Truth Table، Playbook، شش Golden Case، هفت تست و
  checkpoint افزوده شد؛ اجرا و mutation صفر ماند.

## ۲۰۲۶-۰۸-۲۹ — اصلاح طبقه‌بندی `RPT-16/RPT-17`

- شش Method IL نشان داد RPT-16 DialogResult selector و RPT-17 enum/resource route
  orchestrator است؛ Query method count صفر بود.
- دو route به RPT-14/RPT-15 ثبت و result parity مستقل به routing parity اصلاح شد.
- Truth Table، Playbook، شش Golden Case، هفت تست و checkpoint افزوده شد؛ اجرای UI و
  mutation صفر و Risk count ۸۴ ماند.

## ۲۰۲۶-۰۸-۲۹ — اصلاح ownership `RPT-03/RPT-04`

- ده Method IL، پنج widget، permission/refresh میزبان و zoom/drag shell را با صفر
  Query در shell ثبت کرد.
- Result parity مستقل shell حذف و host/view parity از پنج child metric parity جدا شد.
- Truth Table، Playbook، شش Golden Case، هفت تست و checkpoint افزوده شد؛ اجرا و
  mutation صفر و Risk count ۸۴ ماند.

## ۲۰۲۶-۰۸-۲۹ — `RPT-01/RPT-02`، Viewer با ReportDocument مالک بیرونی

- شش Method IL، binding سند خارجی، connection rebind، permission print/export و
  close lifecycle را ثبت کرد؛ Template Load در Viewer مشاهده نشد.
- SQL/result parity عمومی Viewer به caller/template hash منتقل شد؛ چندسندی per-tab
  outcome دارد.
- Truth Table، Playbook، شش Golden Case، هفت تست و checkpoint افزوده شد؛ credential
  ذخیره نشد و اجرا/mutation صفر ماند.

## ۲۰۲۶-۰۸-۲۹ — Closure/Traceability Ledger برای `RPT-01..20`

- ۲۰ Surface بدون duplicate به Artifactهای PASS نگاشت شدند؛ ownership evidence هر
  ۲۰ مورد بسته شد.
- Result parity/owner golden/command-ready/implementation-ready/pilot-ready همگی صفر
  و مستقل از ownership باقی ماندند.
- بانک و invoice packageهای موجود reuse شدند؛ Ledger، هفت تست و checkpoint زنجیره‌ای
  افزوده شد و Risk count ۸۴ ماند.

## ۲۰۲۶-۰۸-۲۹ — Ledger آمادگی فرمان ۱۴ ماژول

- ۱۳ Artifact PASS به ماژول‌ها نگاشت و lifecycle هفت‌مرحله‌ای Truth Table ثبت شد.
- ۱۱ trace/هشت mutation command/۷۷ Golden design case pin شد؛ Artifactهای بدون
  validation به gate ارتقا نیافتند.
- Owner approval، runtime effect/atomicity/retry و command/pilot readiness همگی صفر؛
  Ledger، هفت تست و checkpoint افزوده و Risk count ۸۴ حفظ شد.
# ۱۴۰۵/۰۶/۰۷ — Golden/UAT evidence ledger

- شواهد Golden به چهار سطح طراحی synthetic، اجرای ایزوله، تطبیق نتیجه و تأیید مالک تفکیک شد.
- ۷۷ سناریوی فرمان در سطح اول‌اند؛ اجرا، parity و owner approval همگی صفرند.
- ۲۰ سطح گزارش ownership-closed هستند، اما این وضعیت به result parity یا UAT readiness ارتقا داده نشد.
- artifact، builder، تست و checkpoint زنجیره‌ای بدون اجرای فرم، فرمان، گزارش یا اتصال پایگاه داده تولید شدند.

## ۱۴۰۵/۰۶/۰۷ — Expert incident playbook matrix

- شکاف پوشش Playbookها با ده سناریوی صریح بسته شد.
- هر سناریو evidence-to-collect، شش مرحله تشخیص، تصمیم چهارحالته، stop condition، پیوند ریسک موجود و اثر قرارداد ERP مقصد دارد.
- ریسک تازه ساخته نشد؛ شمار ریسک ۸۴ و نگاشت traceability برابر ۳۴۳ باقی ماند.
- Playbookها راهنمای تشخیص‌اند و بدون شواهد incident، تشخیص runtime یا repair را ادعا نمی‌کنند.

## ۱۴۰۵/۰۶/۰۷ — ممیزی تحویل ۲۵ ساعته

- نیازها در هشت محور با evidence مشخص ممیزی شدند.
- checkpointها از نظر PASS و freshness هش، تست‌ها از نظر پوشش همهٔ `test_varanegar_*.py` و safety از نظر صفر بودن اجرای عملیاتی کنترل می‌شوند.
- completion فقط برای دامنهٔ شناخت read-only است؛ UAT ایزوله، report parity و owner approval به‌عنوان دروازه‌های خارجی باقی مانده‌اند.

## ۱۴۰۵/۰۶/۰۷ — آغاز ادامهٔ ۲۴ساعته و Truth Table حسابداری

- Gap Map تازه، چهار شکاف قابل پیشرفت و یک دروازهٔ خارجی را تفکیک کرد؛ accounting outcome/lineage اول شد.
- هفت candidate حسابداری به ۴ مسیر دقیق External Voucher، یک مسیر انبار با ابهام route و دو مسیر Manual candidate-only تفکیک شدند.
- transfer می‌تواند business-error همراه durable cleanup داشته باشد؛ «پیام خطا = rollback» رد شد.
- risk جدید ساخته نشد و runtime parity/owner approval صفر باقی ماند.

## ۱۴۰۵/۰۶/۰۷ — اصلاح معنایی Manual Voucher

- IL hash-pinned موجود برای `SaveCommand` و `InternalCancelCommand` بازخوانی شد؛ Assembly اجرا نشد.
- `InternalCancelCommand` فقط فرم را می‌بندد و candidate لغو/برگشت مالی رد شد.
- Save مسیر generic `TypeSpecRow.SaveCommand` دارد؛ Commit/Rollback محلی و Adapter/Procedure دقیق در این سطح حل نشده است.

## ۱۴۰۵/۰۶/۰۷ — Resolve مسیر Generic Save در Manual Voucher

- پنج Assembly با hash inventory و فقط PE/CLR metadata/IL خوانده شدند؛ mismatch صفر بود.
- binding کامل UI → generic handler → ManualVoucherAdapter → BaseDataV2Adapter اثبات شد.
- UI `Transaction.Begin` می‌سازد؛ سه overload context-taking CRUD هرکدام Commit دارند و Rollback صریح ندارند.
- Branch runtime میان V2/Fararu/CRUD و effect parity همچنان اثبات‌نشده است.

## ۱۴۰۵/۰۶/۰۷ — اصلاح Inventory حسابداری

- Inventory هفت‌تایی با semantic correction تطبیق داده شد و به شش مسیر رسید.
- UI-close از فرمان‌های mutation حذف شد؛ Manual Save با generic transaction contract نگه داشته شد.
- artifact قبلی حذف نشد و به‌عنوان تاریخچه حفظ شد؛ correction جدید authoritative است.

## ۱۴۰۵/۰۶/۰۷ — Readiness delta حسابداری

- outcome-contract design حسابداری از false به true تغییر کرد.
- ماژول‌های دارای این design از سه به چهار رسیدند.
- runtime proof، command-ready و pilot-ready صفر باقی ماندند؛ risk/traceability تغییر نکرد.

## ۱۴۰۵/۰۶/۰۷ — Golden/UAT حسابداری

- برای شش فرمان اصلاح‌شده ۴۲ case مصنوعی طراحی شد.
- transfer business-error-with-durable-effect و Manual Save validation در موج ویژه قرار گرفتند.
- false Manual Cancel family حذف شد؛ case اجراشده و owner-approved همچنان صفر است.

## ۱۴۰۵/۰۶/۰۷ — Golden Fixture گزارش‌ها

- ۸۸ fixture برای هر ۲۰ سطح گزارش طراحی شد؛ چهار پایه برای هر سطح و هشت case command/partial-failure.
- assertion با ownership query/template/shell/orchestrator تطبیق دارد.
- shellها به‌اشتباه صاحب value parity مستقل نشدند؛ اجرا/parity/owner approval صفر باقی ماند.

## ۱۴۰۵/۰۶/۰۷ — Playbook تخصصی و قرارداد ERP حسابداری

- پنج رخداد تخصصی با read-back، کنترل drift، طبقه‌بندی چهارحالته و stop-before-repair پوشش داده شد.
- سه استنتاج خطرناک رد شد: «متن خطا = rollback»، «MAX(history) = وضعیت جاری» و «بستن فرم = لغو مالی».
- قرارداد مقصد ۹ بخش و acceptance gate چهل‌ودو case دارد؛ تشخیص runtime و repair هر دو صفر باقی ماندند.
- checkpoint زنجیره‌ای، source hash و Risk/Traceability ثابت ۸۴/۳۴۳ ثبت شد.

## ۱۴۰۵/۰۶/۰۷ — دلتا‌ی Traceability/Risk ادامه

- هفت Artifact تازه به ۱۰ قرارداد نیازمندی، ۲۶ پیوند ماژولی و ۳۶ پیوند ریسک متصل شدند.
- همهٔ ۱۶ ریسک یکتا از ثبت موجودند؛ هیچ ریسک تازه یا closure مصنوعی ساخته نشد.
- ثبت‌های پایهٔ ۸۴ ریسک و ۳۴۳ انتساب دست‌نخورده ماندند و دلتا فقط شاهد الحاقی است.
- runtime readiness، اجرای UAT و owner acceptance همچنان صفر است.

## ۱۴۰۵/۰۶/۰۷ — baseline میانی Wave-01 ادامه

- همهٔ checkpointها پس از تغییر اسناد در ۲۸ دور بازسازی شدند و stale count به صفر رسید.
- Bundle میانی هشت محور موج اول را audit می‌کند و صریحاً `continuation_complete=false` دارد.
- runner مستقل ادامه همهٔ تست‌های offline با الگوی کامل را اجرا می‌کند و خروجی خام pytest را ذخیره نمی‌کند.
- اولویت بعدی خزانه، توزیع و تطبیق بین‌ماژولی است؛ دروازه‌های runtime/owner باز مانده‌اند.

## ۱۴۰۵/۰۶/۰۷ — Outcome/Retry خزانه

- ۱۲ فرمان شامل هفت مسیر legacy و پنج قرارداد بانکی به outcome envelope چهارحالته متصل شدند.
- transaction gap در Delete، branch ambiguity در Undo و multi-commit clue در replication حفظ شد.
- design coverage خزانه از false به true رفت، اما runtime/command/pilot readiness صفر ماند.
- ۸۴ Golden Case و شش Playbook تخصصی ساخته شد؛ runtime diagnosis، repair و owner approval صفر است.

## ۱۴۰۵/۰۶/۰۷ — Traceability خزانه

- چهار شاهد خزانه به هفت قرارداد نیازمندی، ۱۴ پیوند ماژولی و ۲۵ پیوند روی ۹ ریسک موجود متصل شد.
- ثبت پایهٔ ۸۴ ریسک و ۳۴۳ انتساب بازنویسی نشد؛ ریسک تازه و promotion صفر است.

## ۱۴۰۵/۰۶/۰۷ — Outcome/Retry توزیع

- چهار فرمان Create/Issue/Merge/Remove با chain دقیق UI→Business→Adapter→SQL ثبت شدند.
- هر چهار idempotency gap و physical transaction enlistment اثبات‌نشده دارند؛ Merge مالک صریح ندارد.
- design coverage از پنج به شش ماژول رسید، اما runtime/command/pilot readiness صفر ماند.
- ۲۸ Golden Case و پنج Playbook تخصصی اضافه شد؛ اجرا، تشخیص رخداد، repair و owner approval صفر است.

## ۱۴۰۵/۰۶/۰۷ — Traceability توزیع

- چهار شاهد به هفت نیازمندی، ۱۸ پیوند ماژولی و ۲۵ پیوند روی ۹ ریسک موجود متصل شد.
- ثبت ۸۴/۳۴۳ تغییر نکرد و هیچ closure یا promotion ساخته نشد.

## ۱۴۰۵/۰۶/۰۷ — قرارداد تطبیق بین‌ماژولی

- هفت لبهٔ بین حسابداری، خزانه، توزیع، فروش و انبار با هویت، Scope، Version، State و Durable Effect مستقل مدل شد.
- شِمای رسید تطبیق ۱۰ بخش، شش وضعیت و هشت علت قرنطینه دارد؛ ۱۰ invariant صریح ثبت شد.
- دادهٔ Aggregate موجود نشان داد ۲۰۲٬۶۳۶ منبع حسابداری فروش بدون عدم‌توازن/چندBatch/Journal مفقودند، اما ۷۲٬۵۵۵ Snapshot بدون منبع accounting به‌خودی‌خود خطا نیستند.
- از ۲۷۴ پرداخت متصل به رسید، Scope مبلغ در ۲۷۰ مورد متفاوت است؛ بنابراین Amount equality به‌عنوان invariant رد شد.
- ۱٬۰۹۴ pointer جاری برابر بیشینهٔ history نیستند و یک shell شماره‌دار خالی باید قرنطینه شود؛ `MAX(id)` و ساخت خودکار line هر دو ممنوع‌اند.

## ۱۴۰۵/۰۶/۰۷ — Golden، Playbook و Traceability بین‌ماژولی

- ۳۵ Golden Case برای هفت لبه و پنج حالت طراحی شد؛ اجرای runtime و owner approval صفر است.
- هفت Playbook نه‌مرحله‌ای اختلاف هویت، Crosswalk، History، Exit/Voucher و Payment/Receipt را با stop-before-repair پوشش می‌دهد.
- سه Artifact به ۱۰ نیازمندی، ۲۱ پیوند ماژولی و ۳۰ پیوند روی ۱۰ ریسک موجود متصل شد.
- ریسک پایه ۸۴، انتساب پایه ۳۴۳، ریسک جدید و readiness promotion صفر باقی ماند.

## ۱۴۰۵/۰۶/۰۷ — Gap Refresh و Outcome خروجی‌های گزارش

- پس از پوشش شش ماژول، `reporting_documents` با هشت سطح Command-bearing انتخاب شد.
- پنج outcome و مرز مستقل Request/Render/Physical Print/Completion/Audit/File/Treasury Receipt تعریف شد.
- Preview از Completion جدا، Export از ERP mutation جدا و Bank Import از مالکیت financial outcome جدا شد.
- ۳۰۸٬۴۳۲ رخداد چاپ فروش، ۳۴٬۸۴۰ سند چندبارچاپ‌شده و ۱۴۳ رخداد پس از ابطال pin شد؛ بدون Request identity هیچ‌کدام خودکار Bug نیست.

## ۱۴۰۵/۰۶/۰۷ — Golden، Playbook و Traceability خروجی‌های گزارش

- design coverage از شش به هفت ماژول رسید؛ runtime/command/pilot readiness صفر ماند.
- ۵۶ Golden Case برای هشت سطح و هفت حالت ساخته شد؛ اجرا و owner approval صفر است.
- شش Playbook Evidence-first برای partial batch، completion مبهم، reprint، export drift و bank import طراحی شد.
- پنج شاهد به ۱۰ نیازمندی، ۳۰ پیوند ماژولی و ۴۰ پیوند روی هشت ریسک موجود متصل شد؛ پایه ۸۴/۳۴۳ ثابت است.

## ۱۴۰۵/۰۶/۰۷ — Outcome/Retry قواعد قیمت‌گذاری

- هفت مسیر مقصد برای Save/Close قیمت زمینه‌ای، تغییر اولویت، Save/Close تخفیف، Compile شرط و Allocate/Save تخفیف خطی تعریف شد.
- `SqlCondition` اجرایی Legacy به‌عنوان DSL مقصد پذیرفته نشد؛ Validation مقصد Side-effect-free و مبتنی بر AST/DSL نسخه‌دار و Allowlist‌شده است.
- شاهد مستقیم `MAX(Id)+1` در `GenerateLinearDiscountId` ثبت شد؛ مقصد Allocator اتمیک، Unique constraint و تست Parallel writer می‌خواهد.
- انتشار محلی، Audit و Outbox اتمیک‌اند؛ Replication Async است و شش شکاف Authentication/Idempotency/Ordering/Scope/Quarantine/Rollback observability باز ماند.

## ۱۴۰۵/۰۶/۰۷ — Golden، Playbook و Traceability قواعد قیمت‌گذاری

- ۶۴ Case موجود چهار فرمان Save/Delete reuse و ۲۸ Case تازه برای Priority/Compile/Allocator/Publication طراحی شد؛ مجموع ۹۲ و اجرا صفر است.
- هفت Playbook نه‌مرحله‌ای برای ابهام اولویت، Publish failure، DSL mismatch، برخورد شناسه، Provenance loss، Explain mismatch و Replication unknown ساخته شد.
- design coverage از هفت به هشت ماژول رسید، اما Runtime/Command/Pilot readiness و owner approval صفر ماند.
- پنج شاهد به ۱۰ نیازمندی، ۳۰ Link ماژولی و ۴۰ Link روی هشت ریسک موجود متصل شد؛ ثبت پایه ۸۴/۳۴۳ تغییر نکرد.

## ۱۴۰۵/۰۶/۰۷ — Outcome/Receipt در Integration/Migration

- شش قرارداد POS Receipt، NGT Sale، NGT Payment، Compensation، Rule Package و Migration Slice ساخته شد.
- Transport، Apply، Reconcile و Acknowledge از هم جدا شدند؛ موفقیت انتقال یا اجرای Script به‌تنهایی Ack کسب‌وکاری نیست.
- POS graph در سقف ۵۰۰ Node با ۱۶۰ Frontier باز است؛ کامل‌بودن Mutation set ادعا نشد.
- ۱۳۸ موجودیت Sale چند History به همان Target دارند و Multi-target آنها صفر است؛ History تکراری به‌تنهایی Duplicate effect نیست.
- شش Gate Transport و اجرای دوازده Slice Migration همچنان اثبات‌نشده/اجرانشده باقی ماند.

## ۱۴۰۵/۰۶/۰۷ — Golden، Playbook و Traceability Integration/Migration

- ۳۴ Case موجود reuse و ۳۵ Case Delta اضافه شد؛ مجموع ۶۹ و اجرای Runtime صفر است.
- هفت Playbook Package auth/scope، ordering/fork، unknown ack، partial POS، NGT crosswalk، compensation و migration rerun را پوشش می‌دهد.
- design coverage از هشت به نه ماژول رسید؛ runtime/command/pilot readiness و owner approval صفر ماند.
- پنج شاهد به ۱۰ نیازمندی، ۳۵ Link ماژولی و ۴۵ Link روی ۹ ریسک موجود متصل شد؛ پایه ۸۴/۳۴۳ ثابت است.

## ۱۴۰۵/۰۶/۰۷ — نسخه، تقدم و Rollout پیکربندی

- پنج قرارداد مقصد برای انتشار General، Web Service، Accounting Article Template، override محدوده‌دار و rollback-by-new-version تعریف شد.
- ۹۷ resolver چندجدولی، ۱۴ مسیر `TOP 1` بدون `ORDER BY`، هجده mismatch جاری App/Device و ۵۱ ارجاع فعال به Device Setting حذف‌شده pin شد؛ اینها شاهد ریسک‌اند، نه حکم خودکار دربارهٔ مقدار مؤثر جاری.
- تقدم مقصد tuple قطعی family/scope/effective-window/published-version/stable-version-id دارد؛ null به `INHERIT/EXPLICIT_NULL/VALUE` تفکیک می‌شود و secret value هرگز وارد payload/result/audit نمی‌شود.
- Version، effective pointer، audit و outbox اتمیک‌اند؛ acknowledgement هر مصرف‌کننده مستقل است و rollback تاریخ را بازنویسی نمی‌کند، بلکه نسخهٔ تازه‌ای از محتوای پیشین منتشر می‌کند.

## ۱۴۰۵/۰۶/۰۷ — Golden، Playbook و Traceability پیکربندی

- ۵۴ Case موجود سه فرمان reuse و ۲۸ Case تازه برای تقدم، null/removed، secret-reference و rollout/rollback طراحی شد؛ مجموع ۸۲ و اجرای Runtime صفر است.
- هفت Playbook نه‌مرحله‌ای برای drift مقدار مؤثر، بی‌ثباتی `TOP 1`، null، removed-reference، secret/endpoint، partial ack و rollback mixed-version ساخته شد.
- design coverage از نه به ده ماژول رسید، اما Runtime effect parity، owner approval، command readiness و pilot readiness صفر ماند.
- پنج شاهد به ۱۰ نیازمندی، ۳۰ Link ماژولی و ۴۵ Link روی ۹ ریسک موجود متصل شد؛ پایه ۸۴/۳۴۳ ثابت است.

## ۱۴۰۵/۰۶/۰۷ — Decision/Session Contract هویت و مجوزدهی

- شش فرمان مقصد برای انتشار policy، capability مستقیم، عضویت گروه، data scope، revoke/session invalidation و break-glass تعریف شد.
- تصمیم deny-first است و نشست تازه، deny صریح، Application/Owner، action capability، data scope، SoD/self-grant و expiry را به ترتیب بررسی می‌کند.
- ۷۸۴ endpoint ایستا شامل ۶۰ endpoint بدون declaration روشن و ۳۸ endpoint تغییردهنده در همان گروه pin شد؛ manual decision نام‌دار در آنها صفر است.
- admin short-circuit، سه subject منتسب به آن نقش، ۵۸ scope mismatch و نبود owner-filter در permission repository شاهد ریسک‌اند؛ effective production grant ادعا نشد.

## ۱۴۰۵/۰۶/۰۷ — Golden، Playbook و Traceability هویت و مجوزدهی

- ۱۸۴ Case provisional موجود reuse و ۴۲ Case Delta در شش سطح ساخته شد؛ مجموع ۲۲۶ و اجرای authenticated UAT صفر است.
- هفت Playbook نه‌مرحله‌ای conflict deny، endpoint default-deny، admin bypass، cross-owner، stale session، partial receipt و SoD/break-glass را پوشش می‌دهد.
- design coverage از ۱۰ به ۱۱ ماژول رسید؛ effective grant، owner approval، production assignment، command/pilot readiness و runtime parity صفر ماند.
- پنج شاهد به ۱۰ نیازمندی، ۳۵ Link ماژولی و ۴۵ Link روی ۹ ریسک موجود متصل شد؛ پایه ۸۴/۳۴۳ ثابت است.

## ۱۴۰۵/۰۶/۰۷ — ContextSnapshot و Date Contract

- شش فرمان Save/Delete سال عملیاتی، Save/Delete StockDC، انتشار پنجرهٔ تاریخ و فعال‌سازی ContextSnapshot تعریف شد.
- Snapshot سازمان، سال عملیاتی/مالی، DC، دفتر، انبار، پنجرهٔ تاریخ، calendar/timezone policy و نسخهٔ relation را برای تمام عمر فرمان pin می‌کند.
- timestamp رخداد، مرز باز/بسته، selector تاریخ سند/replication و ساعت Server چهار مفهوم مستقل‌اند؛ null/missing boundary به ambient default تبدیل نمی‌شود.
- شاهد ۶۴۳ method منتخب، ۱۱ SQL consumer، سه profile با OperationDate تهی و یک profile پس از LastDate را pin کرد؛ permission تغییر تاریخ در server command دوباره ارزیابی نمی‌شود.

## ۱۴۰۵/۰۶/۰۷ — Golden، Playbook و Traceability Organization Context

- ۶۴ Case موجود reuse و ۳۵ Case Delta در پنج سطح ساخته شد؛ مجموع ۹۹ و اجرا صفر است.
- هفت Playbook mixed context، date boundary، event/selector، StockDC relation، lifecycle، exception و partial publication را پوشش می‌دهد.
- design coverage از ۱۱ به ۱۲ ماژول رسید، ولی runtime context parity، owner approval، command readiness و pilot readiness صفر ماند.
- پنج شاهد به ۱۰ نیازمندی، ۳۵ Link ماژولی و ۴۵ Link روی ۹ ریسک موجود متصل شد؛ پایه ۸۴/۳۴۳ ثابت است.

## ۱۴۰۵/۰۶/۰۷ — Version، Crosswalk و Merge دادهٔ پایه

- ۱۰ قرارداد فرمان مقصد برای Customer، Goods، Supplier، POS Subscriber، قرنطینهٔ duplicate، انتشار Crosswalk و Merge برگشت‌پذیر تعریف شد.
- aggregate، child relation، party role و source identity نسخه‌دارند؛ weak barcode/contact/name/route indicator هرگز proof هویت نیست و sentinel قرنطینه می‌ماند.
- شاهد ایستا سه فرم، ۴۰ method منتخب، پنج method دارای Commit و ۱۴۲ candidate ورودی را pin کرد؛ ۶۲ candidate متن ایستای کامل ندارند.
- ۲۶٬۰۸۶ مقدار path در هفت code دیده شد، اما master row متناظر صفر است؛ path فقط `MANUAL_INTEGER_CODE` است و Route entity از آن استنتاج نمی‌شود.

## ۱۴۰۵/۰۶/۰۷ — Golden، Playbook و Traceability دادهٔ پایه

- ۱۱۴ Case موجود reuse و ۳۵ Case Delta در پنج سطح ساخته شد؛ مجموع ۱۴۹ و اجرای Merge/UAT صفر است.
- هفت Playbook duplicate، sentinel، route code، partial child set، supplier role، partial merge و PII/role collapse را پوشش می‌دهد.
- design coverage از ۱۲ به ۱۳ ماژول رسید، ولی runtime effect parity، owner approval، command readiness و pilot readiness صفر ماند.
- پنج شاهد به ۱۰ نیازمندی، ۴۰ Link ماژولی و ۵۰ Link روی ۱۰ ریسک موجود متصل شد؛ پایه ۸۴/۳۴۳ ثابت است.

## ۱۴۰۵/۰۶/۰۷ — Outcome، Recovery و Traceability Platform

- Blueprint سه فرمان `approve/reject/retry_job` دارد؛ قرارداد provider-neutral با Release Publish/Rollback و Restore Drill Attestation به شش فرمان رسید.
- Commit کنترل از اثر خارجی جدا شد؛ Deployment/Restore/Job فقط با health، reconciliation و external-effect receipt قابل تأیید است.
- اسکن ۸۵۳ فایل استقرار و صفر reference بیرونی pin شد، اما route پویا رد نشد. Stack/Database/Hosting، RPO/RTO و مالک استقرار همچنان انتخاب‌نشده‌اند.
- پوشش طراحی از ۱۳ به ۱۴ ماژول رسید؛ ۴۲ Case و هفت Playbook ساخته شد. اجرا، owner approval، command/pilot readiness و Runtime parity صفر و پایه ۸۴/۳۴۳ ثابت ماند.

## ۱۴۰۵/۰۶/۰۷ — ممیزی تجمیعی غیرنهایی ادامه

- هر ۱۴ ماژول Outcome/Retry target contract و Authorization design دارند؛ Transaction/Mutation static/design در ۱۲ ماژول است و دو ماژول Identity/Authorization و Integration/Migration در این ابعاد target-design باقی مانده‌اند.
- obligation طراحی Golden برابر ۱۲۲۹ و Playbookهای موج ادامه ۷۸ است؛ executed/owner-approved و چهار محور Runtime برای هر ۱۴ ماژول صفر است.
- مالکیت ۲۰ گزارش بسته، ولی Result/Formula parity و Owner Golden Value صفر است. ۱۱۹ Checkpoint و ۲۰۰ manifest node ورودی ممیزی current بودند.
- شش Gate خارجی Runtime، UAT/Owner، Report parity و Platform decision حفظ شد؛ Audit صریحاً non-final است.

## ۱۴۰۵/۰۶/۰۷ — مرز Transaction/Mutation هویت و یکپارچگی

- شش فرمان Identity و شش فرمان Integration همگی Target transaction و mutation/effect design دارند؛ این ۱۲/۱۲ فقط قرارداد مقصد است.
- complete legacy/static proof برای این ۱۲ فرمان صفر است و Runtime atomicity/effect parity، implementation، UAT و Owner approval نیز صفر می‌ماند.
- Identity هنوز ۳۸ endpoint تغییردهنده بدون declaration روشن و ۵۸ scope mismatch دارد؛ Integration نیز ۱۶۰ POS frontier، ۳۴۲ compensation blocker candidate و شش Gate انتقال Rule دارد.
- هیچ Assignment، Package، Migration، Compensation، Procedure یا اثر خارجی اجرا نشد؛ پایهٔ ۸۴ ریسک و ۳۴۳ انتساب ثابت ماند.

## ۱۴۰۵/۰۶/۰۷ — اولویت‌بندی Gateهای شواهد خارجی و Runtime

- شش Gate باز به چهار Lane تفکیک شد: تصمیم بنیادین CG-06، گزارش محدود و موازی CG-05، Runtime ایزوله CG-01/02/03 و UAT نهایی CG-04.
- CG-06 اول است چون Stack/Hosting، RPO/RTO، محیط ایزوله و مالک استقرار ظرف معتبر شواهد Runtime را تعیین می‌کنند؛ Proposal همچنان Approval نیست.
- CG-05 می‌تواند موازی فقط Evidence packet بسازد، چون مالکیت ۲۰/۲۰ بسته است؛ Result/Formula parity و Owner Golden Value همچنان صفرند.
- CG-04 پس از پنج Gate دیگر قرار گرفت؛ ۱۲۲۹ obligation طراحی بدون اجرای ایزوله و تأیید مالک هیچ Readiness promotion ایجاد نمی‌کند.
- برای هر Gate چهار جزء Evidence packet و Acceptance rule ثبت شد. تمام Gateها باز، اثر Promotion پیش از پذیرش `NONE` و پایهٔ ۸۴/۳۴۳ ثابت است.

## ۱۴۰۵/۰۶/۰۷ — قرارداد Evidence intake تصمیم‌های Platform

- CG-06 به هشت Slot تفکیک شد: Stack، Database، Hosting/Network، نقش مالک Deployment، RPO، RTO، محیط ایزوله و Policy Drill/Receipt.
- Packet استاندارد یازده Field مرجعی/Hash دارد و PII، Secret، Endpoint/Connection string، پیشنهاد خام فروشنده و مقدار خام تجاری را ممنوع می‌کند.
- `PROPOSAL` Approval نیست؛ Approval ناقص، Conflict جاری، Superseded و Dependency تصویب‌نشده هفت Outcome اعتبارسنجی متمایز دارند.
- CG-06 تنها با ۸/۸ `APPROVED_CURRENT` و Conflict صفر بسته می‌شود؛ حتی آن نتیجه Runtime effect، Restore یا Deployment را اثبات نمی‌کند.
- Snapshot فعلی ۰/۸ تصمیم انتخاب‌شده و ۰ Packet پذیرفته دارد؛ شش قرارداد فرمان، ۴۲ Case و هفت Playbook صرفاً طراحی‌اند و Readiness صفر است.

## ۱۴۰۵/۰۶/۰۷ — قرارداد Evidence intake Result/Formula parity گزارش‌ها

- ۲۰ سطح به ۱۱ `RESULT_PARITY_PACKET`، دو `COMMAND_OUTCOME_PACKET` و هفت `ROUTING_VIEW_PACKET` تفکیک شد؛ همهٔ مالکیت‌ها بسته‌اند.
- هشت سطح Command وجود دارد و شش‌تای آنها هم Result owner هستند؛ Receipt فرمان در این شش سطح جای Formula/Result parity را نمی‌گیرد.
- Packet نتیجه ۱۴ Field مرجعی/Hash برای Fixture، Legacy/Target digest، Key set، Formula، Grain، Scope، Rounding، Null، Watermark، Difference و Approval دارد.
- قبولی به Frozen isolated input، Policy مالک و صفر اختلاف توضیح‌نداده‌شده نیاز دارد؛ Shell/Viewer/Selector به Query owner ارتقا داده نمی‌شود.
- ۸۸ Fixture و ۵۶ Case فرمان طراحی شده، اما اجرا، Packet پذیرفته، Result parity و Owner approval همگی صفر و CG-05 باز است.

## ۱۴۰۵/۰۶/۰۷ — قرارداد Evidence intake Runtime authorization/scope

- برای هر ۱۴ ماژول یک Packet پانزده‌فیلدی و هشت دسته سناریوی authenticated deny-first تعریف شد؛ design ۱۴/۱۴ و Runtime proof صفر است.
- سناریوها Allow، Explicit deny، Capability مفقود، Scope ناسازگار، Session epoch منقضی، SoD، Break-glass و Server-vs-UI enforcement را جدا می‌کنند.
- اجرای CG-01 به پذیرش ۸/۸ Slot CG-06 وابسته است؛ اکنون ۰/۸ است و هیچ Login/Session/Grant/Revoke اجرا نشد.
- Identity همچنان ۶۰ declaration gap، ۳۸ mutating gap و ۵۸ scope mismatch دارد؛ اینها Incident سراسری ۱۴ ماژول تلقی نشدند.
- ۱۴ Packet پذیرفته، Security/Owner approval، Runtime authorization، Command/Pilot readiness و بسته‌شدن CG-01 همگی صفر و پایه ۸۴/۳۴۳ ثابت است.

## ۱۴۰۵/۰۶/۰۷ — قرارداد Evidence intake Fault-injection و Atomicity

- ۱۴ ماژول به ۱۲ ماژول با Legacy-static/Target design و دو ماژول Identity/Integration با Target-design-only تقسیم شدند؛ Runtime atomicity صفر است.
- ده مرز خطا شامل mid-mutation، pre-Audit/Outbox، post-Commit/pre-Ack، دو جهت شکاف DB/external effect، rollback failure، concurrency، stale version و retry تعریف شد.
- Packet هفده Field دارد؛ Rollback call یا Catch/Boolean اثبات Rollback موفق نیست و Commit بدون Ack تا Readback برابر Unknown outcome است.
- اجرای CG-02 پس از پذیرش CG-06 می‌تواند موازی با CG-01 باشد؛ هیچ‌یک از دیگری استنتاج نمی‌شود.
- Packet پذیرفته، Owner approval، Runtime atomicity و Readiness صفر و پایهٔ ۸۴/۳۴۳ ثابت ماند.

## ۱۴۰۵/۰۶/۰۷ — قرارداد Evidence intake Mutation/Result/External-effect parity

- ده لایهٔ مستقل برای DB mutation، Audit، Outbox، External effect، Result، Readback، Retry، Compensation، Crosswalk و Reconciliation تعریف شد.
- دوازده ماژول شاهد Mutation static/design و دو ماژول Identity/Integration فقط Target design دارند؛ Runtime effect parity صفر است.
- Packet نوزده Field مرجعی/Hash دارد؛ Commit/Audit/Outbox به‌تنهایی اثر خارجی و Result موفق بدون Readback، Mutation set را ثابت نمی‌کند.
- اجرای CG-03 به پذیرش CG-06 و CG-02 وابسته است؛ Retry باید پیش از اثر تازه Outcome قبلی را reconcile کند و Compensation append-only است.
- ۱۴ Packet پذیرفته، Owner approval، Runtime parity و Readiness صفر و پایهٔ ۸۴/۳۴۳ ثابت ماند.

## ۱۴۰۵/۰۶/۰۷ — قرارداد Evidence intake نهایی Owner-UAT

- CG-04 به پذیرش پنج Gate و مجموع ۷۰ Slot/Packet بالادست وابسته شد: ۸ Platform، ۲۰ Report و ۳×۱۴ Runtime module packet.
- برای ۱۴ ماژول Packet شانزده‌فیلدی و نه بُعد پذیرش شامل Obligation، Run receipt، Difference/Risk، Approval و Promotion/Rollback تعریف شد.
- Artifact/Test آفلاین PASS و Golden design اجرای UAT نیست؛ Approval باید Snapshot دقیق Run/Difference/Risk را ارجاع دهد.
- CG-04 فقط با اجرای ۱۲۲۹ Obligation، ۱۴ Packet، صفر اختلاف توضیح‌نداده‌شده و Approval پاسخ‌گو بسته می‌شود.
- Snapshot فعلی پذیرش ۰/۷۰، اجرای Obligation و Approval صفر و Readiness صفر؛ پایهٔ ۸۴/۳۴۳ ثابت است.

### ماتریس یکپارچهٔ تحویل و پذیرش شش Gate بیرونی

- شش قرارداد Intake در یک Matrix واحد به ۸۴ واحد پذیرش تبدیل شدند: ۸ Platform، ۲۰ Report و چهار مجموعهٔ ۱۴ماژولی.
- نه Edge وابستگی مستقیم ثبت شد؛ هر نه Edge در وضعیت `BLOCKED_SOURCE_GATE_OPEN` است و فقط Packet set دقیقِ `ACCEPTED_CURRENT` را می‌پذیرد.
- هشت Reject code برای Field مفقود، Reference بدون Hash، شاهد Stale/Superseded، Dependency باز، Approval مفقود، اختلاف توضیح‌نداده‌شده، Payload ممنوع و Promotion زودهنگام تعریف شد.
- مالکیت فقط با Role type ثبت می‌شود و هیچ هویت شخصی وارد Artifact نمی‌شود.
- Snapshot فعلی: پذیرش ۰/۸۴، Gate بسته ۰/۶، Handoff پذیرفته ۰/۹، اجرا/Approval/Readiness صفر؛ پایهٔ ۸۴/۳۴۳ ثابت است.

### Triage ایستای Graph تکثیر رسید POS

- Graph موجود ۵۰۰ گره/۱۰۳۹ Edge دارد، به Safety cap رسیده و صف ۱۶۰عضویِ بدون manifest هویت دارد؛ این صف با ۱۵۱ ماژول callable در عمق سه یکی فرض نشد.
- مرز عمق سه ۱۸۳ گره دارد: ۱۵۱ callable و ۳۲ Table؛ در callableها ۴۴ Transaction signal، چهار TRY/CATCH و چهار Dynamic-SQL signal دیده شد.
- از ۱۷۹ unresolved، تعداد ۱۶۸ مورد pseudo-tableهای `inserted/deleted` و فقط یازده مورد نام/Type/Alias قابل پیگیری‌اند؛ شمارش اصلی حذف نشد.
- یازده SCC چرخه‌ای با ۶۸ گره و بیشینهٔ ۱۷ گره شناسایی شد؛ ۴۸ Trigger، نوزده Table و یک Stored Procedure در این چرخه‌ها قرار دارند.
- ۴۸ Write target حل‌شده lower bound است؛ Atomicity/Effect parity/Readiness صفر و پایهٔ ۸۴/۳۴۳ ثابت ماند.

### ماتریس Formula/Grain برای Result-ownerهای گزارش

- از ۲۰ Surface فقط ۱۱ Result owner مستقل‌اند: هشت Query-bound، دو Template-owned و یک Bank typed read/summary؛ نه Surface غیرنتیجه‌ای به Result owner ارتقا داده نشد.
- Grain ایستای ۹ Surface تعریف‌پذیر است؛ `RPT-11/12` تا استخراج Query/Subreport/Formula داخل Template دارای Grain ناشناخته‌اند.
- چهارده بُعد Policy و ۱۲۳ تخصیص سطحی برای Key/Grain، Date/Watermark، Scope، Status، Null، Sign، Rounding، Unit/Currency، Ordering، Opening/Closing، Mode، Template، Master-detail و Version تعریف شد.
- پنجاه Golden fixture موجود فقط طراحی‌اند. Packet بیست‌فیلدی Source/Target receipt و Key/Delta را به نسخه‌های Policy متصل می‌کند.
- Snapshot: Packet پذیرفته ۰/۱۱، Fixture اجرا ۰/۵۰، Formula owner approval و Result parity صفر؛ پایهٔ ۸۴/۳۴۳ و Readiness صفر ثابت است.

### Triage شکاف‌های Identity/Authorization

- ۶۰ declaration gap به ۳۱ POST، شش PUT، یک DELETE و ۲۲ GET تفکیک شد؛ ۳۸ Mutation و ۲۲ Read است.
- در Mutationها ۳۰ مورد بدون Named signal، پنج Authorization-data-only و سه Identity-context-only هستند؛ Named authorization decision صفر است.
- هر ۵۸ Scope mismatch از کلاس `membership_user_scope_mismatch` است و به دیگر ابعاد Scope تعمیم داده نشد.
- Admin short-circuit، repository بدون owner filter و سه Resource/Action mapping مفقود به‌عنوان مرزهای ساختاری جدا حفظ شدند؛ هیچ Incident یا Grant استنتاج نشد.
- هفت Lane و ۱۳۹ واحد مرکب disposition/test تعریف شد؛ آزمون هر Endpoint داخل همان واحد است و دوباره‌شماری نمی‌شود. پذیرش ۰/۱۳۹، ۱۸۴ Role UAT فقط طراحی، Runtime/Security approval/Readiness صفر و پایهٔ ۸۴/۳۴۳ ثابت است.

### Addendum Playbook تشخیصی مشترک

- بیست Playbook عملیاتی موجود حفظ شدند و هشت Scenario تازه با ID غیرتکراری برای مرزهای شواهد افزوده شد.
- Scenarioها Metadata drift، Membership scope concentration، POS truncation/frontier، SCC cascade، Report keyset/grain، Template unknown، Policy-dimension delta و Packet supersession را پوشش می‌دهند.
- هر Playbook حداقل ده Step، Evidence request، Role escalation و Stop condition دارد و نتیجه را به پنج کلاس ثابت محدود می‌کند.
- Runtime diagnosis، Repair/Replay/Grant/Query/Command execution، Packet acceptance و Readiness همگی صفر؛ پایهٔ ۸۴/۳۴۳ ثابت است.

### ممیزی Delta طراحی Golden/UAT

- Snapshot ۱۲۲۹ به ۱۱۸۷ Case ماژولی + ۴۲ Case پلتفرم reconcile شد؛ پلتفرم دوباره‌شماری نشد.
- پنج Artifact جدید reuse-base دقیق دارند: Organization +۳۵، Identity +۴۲، Configuration +۲۸، Master Data +۳۵ و Integration +۳۵.
- Delta غیرتکراری دقیق ۱۷۵ و lower bound فعلی ۱۴۰۴ است.
- Pricing/Distribution/Treasury/Accounting/Reporting به‌علت overlap یا Case-set باریک‌تر صفر اضافه شدند و در صف Crosswalk باقی ماندند.
- ۱۴۰۴ فقط Design lower bound است؛ Execution/Approval/Readiness صفر و پایهٔ ۸۴/۳۴۳ ثابت است.
## موج ادامه ـ ماتریس Refinement بین‌دروازه‌ای Golden/UAT ـ ۲۰۲۶-۰۸-۲۹

- ۳۲ قالب refinement در چهار Lane ساخته شد: Identity ۸، POS ۸، Report ۱۰ و Handoff ۶.
- هر قالب پنج Receipt و Failure oracle دارد؛ در نبود مدرک current نتیجه `UNPROVEN` است.
- همهٔ قالب‌ها `REFINEMENT_NOT_ADDITIVE` هستند؛ lower bound غیرتکراری طراحی ۱۴۰۴ باقی ماند و ۱۶۰ Receipt slot به‌عنوان Case جدید شمرده نشد.
- اجرا، پذیرش مالک، Runtime parity، Command readiness و Pilot readiness همچنان صفر است.

## موج ادامه ـ امکان‌سنجی Crosswalk Case-level ـ ۲۰۲۶-۰۸-۲۹

- ۵۱۱ Case baseline پنج ماژول unresolved از هفت منبع Case-level بازسازی شد؛ همهٔ Case IDها یکتا هستند.
- مجموعهٔ جدید نمایندگی‌شده ۳۰۲ Case یکتا دارد؛ ۶۴ Exact-ID overlap فقط در Pricing دیده شد.
- ۴۴۷ Case baseline و ۲۳۸ Case جدید unmatched هستند؛ ۳۰ تطبیق action+kind فقط کاندید review است و semantic equivalence محسوب نمی‌شود.
- additive count صفر و lower bound طراحی ۱۴۰۴ ثابت ماند؛ اجرا/پذیرش/آمادگی صفر است.

## موج ادامه ـ Packetهای Semantic Alias توزیع و خزانه ـ ۲۰۲۶-۰۸-۲۹

- ۳۰ جفت کاندید استخراج شد: Distribution تعداد ۲۴ و Treasury تعداد ۶.
- Action و Kind در همه برابر است، اما Outcome label فقط در ۵ جفت عیناً برابر و Assertion list در هیچ جفتی برابر نیست.
- همهٔ Packetها `REVIEW_REQUIRED` و Accepted صفرند؛ Auto-accept ممنوع و additive صفر است.

## موج ادامه ـ صف ۲۰۸ Case unmatched ـ ۲۰۲۶-۰۸-۲۹

- پس از Exact-ID reuse و کاندیدهای Action+Kind، ۲۰۸ Case باقی ماند: ۲۸/۴/۷۸/۴۲/۵۶ برای Pricing/Distribution/Treasury/Accounting/Reporting.
- ۲۰۳ Case نیازمند Action/Surface alias و ۵ Case نیازمند disposition Kind یا multiplicity هستند؛ ۳۴ Action متمایز در صف است.
- همهٔ Caseها unresolved و اثر شمارشی/اجرایی/آمادگی صفر است.

## موج ادامه ـ پنج Packet Kind/Multiplicity ـ ۲۰۲۶-۰۸-۲۹

- پنج Case به سه Kind تازه و دو Multiplicity gap تفکیک شد؛ چهار مورد Distribution و یک مورد Treasury است.
- ۱۳ Case پایهٔ نزدیک بررسی شد؛ Outcome exact و Assertion exact هر دو صفر است.
- اولویت با late/ambiguous durable-effect failure است؛ هر پنج Packet unresolved و additive صفر باقی ماند.

## موج ادامه ـ ۲۹ Packet Action Alias ـ ۲۰۲۶-۰۸-۲۹

- ۲۰۳ Case Alias-required در ۲۹ Action هفت‌Case‌ای گروه‌بندی شد: ۴/۱۱/۶/۸ Packet برای Pricing/Treasury/Accounting/Reporting.
- برای هر Action دو نقش پاسخ‌گو و ده فیلد پذیرش تعیین شد؛ ۵۸ role assignment طراحی شد.
- Packet accepted، Case disposition accepted و additive count همگی صفر باقی ماند.

## موج ادامه ـ اولویت تحویل ۲۹ Action Alias ـ ۲۰۲۶-۰۸-۲۹

- ۲۹ Packet و ۲۰۳ Case بدون حذف یا تکرار در پنج Lane مرتب شد: `P0` هفت/۴۹، `P1` هشت/۵۶، `P2` شش/۴۲، `P3` پنج/۳۵ و `P4` سه/۲۱.
- ترتیب risk-first از irreversible/reversal/replication به transition مالی، policy/input، command/print و export فقط‌خواندنی می‌رسد.
- ۵۸ role assignment فقط placeholder پاسخ‌گویی است؛ named owner، acceptance، اجرا، additive و readiness همچنان صفر است.

## موج ادامه ـ Shortlist شواهد Baseline برای P0 ـ ۲۰۲۶-۰۸-۲۹

- هفت Packet/۴۹ Case اولویت P0 در baseline بازسازی‌شده جست‌وجو شد؛ سه Packet کاندید و چهار Packet explicit-none دارند.
- یک exact-action cross-module برای stock voucher و پنج lifecycle-family reference برای bank-reconciliation و received-cheque شناسایی شد.
- شش Action reference شامل ۹۲ Case پایه و ۳۷ kind-overlap است؛ هیچ‌کدام Semantic equivalence یا Alias پذیرفته‌شده نیست.

## موج ادامه ـ Comparator معنایی P0 ـ ۲۰۲۶-۰۸-۲۹

- شش کاندید به ۶۶ جفت Case هم‌نوع شکسته شد؛ ۲۰ جفت مربوط به Failure Injection است.
- exact precondition صفر، exact outcome دو، exact assertion-list صفر و full exact صفر است.
- دو برچسب outcome برابر در received-cheque بدون برابری precondition/assertion قابل پذیرش نیستند؛ acceptance و additive صفر ماند.

## موج ادامه ـ داوری Failure Injection در P0 ـ ۲۰۲۶-۰۸-۲۹

- ۲۰ جفت Failure Injection در سه Packet stock/bank/cheque گروه‌بندی شد؛ سه Case جدید در برابر ۲۰ Case baseline قرار دارد.
- دو stage label دقیق و ۱۸ نگاشت generic-to-detailed دیده شد؛ baseline در ۱۵ جفت retry/convergence و در ۱۵ جفت no-partial-effect را صریح می‌کند.
- هفت stage به audit/outbox حساس است؛ outcome/assertion/full exact همگی صفر و acceptance صفر باقی ماند.

## موج ادامه ـ داوری Outcome Vocabulary کنترل‌های P0 ـ ۲۰۲۶-۰۸-۲۹

- ۴۶ جفت غیرخطا به شش Packet Authorization/Concurrency/Idempotency/Reconciliation/Scope/Success تفکیک شد.
- vocabulary جدید هشت label جهانی و baseline تعداد ۲۳ عبارت دارد؛ `REJECTED_NO_EFFECT` روی ۲۳ جفت و committed-original-once روی ۱۱ جفت متمرکز است.
- دو outcome label برابر Success بدون assertion/full match است؛ ۴۴ mapping label و ۴۶ disposition کامل لازم است، acceptance صفر.

## موج ادامه ـ شکاف خانوادهٔ Assertion/Effect در P0 ـ ۲۰۲۶-۰۸-۲۹

- ۶۶ جفت به دوازده خانوادهٔ اثر تبدیل شد؛ family-set برابر صفر، هم‌پوشانی غیرتهی ۶۵ و بدون هم‌پوشانی یک است.
- Audit/Outbox جدید ۶۶/۶۶ در برابر baseline ۵۰/۱۴ است؛ Source immutability جدید/پایه ۰/۵۳ و Transaction ۶/۲۹ است.
- ۲۹۴ assignment فقط‌جدید و ۱۲۵ فقط‌baseline است؛ classifier فقط routing heuristic و acceptance صفر است.

## موج ادامه ـ وضعیت نهایی Evidence Gap برای P0 ـ ۲۰۲۶-۰۸-۲۹

- Packetization تحلیل هفت Action/۴۹ Case کامل شد، اما semantic disposition بسته‌شده صفر است.
- چهار Packet explicit-none به Alias/New-Action decision و سه Packet کاندیددار به Semantic-equivalence decision بیرونی نیاز دارند.
- ۱۳ فیلد closure برای هر Packet تثبیت شد؛ named owner، acceptance، اجرا، additive و readiness صفر ماند.

## موج ادامه ـ Shortlist شواهد Baseline برای P1 ـ ۲۰۲۶-۰۸-۲۹

- هشت Packet/۵۶ Case اولویت P1 در baseline بازسازی‌شده بررسی شد؛ چهار Packet بانکی کاندید و چهار Packet explicit-none دارند.
- قرارداد state-machine چهار نگاشت صریح فرمان به capability پایه دارد؛ این کاندیدها ۷۶ Case پایه و ۲۴ kind-overlap را پوشش می‌دهند.
- Action string دقیق صفر است و mapping صریح نیز به‌تنهایی semantic equivalence نیست؛ acceptance، اجرا، additive و readiness صفر باقی ماند.

## موج ادامه ـ Comparator معنایی P1 ـ ۲۰۲۶-۰۸-۲۹

- چهار نگاشت بانکی P1 به ۵۵ جفت Case هم‌نوع تبدیل شد: ۱۹ Failure Injection و ۳۶ جفت کنترل.
- exact precondition، outcome، assertion-list و full exact همگی صفر است؛ lineage صریح command-to-capability نیز reuse معنایی را ثابت نمی‌کند.
- پذیرش Candidate/Case، اجرا، additive و readiness صفر و lower bound طراحی ۱۴۰۴ باقی ماند.

## موج ادامه ـ داوری Failure Injection در P1 ـ ۲۰۲۶-۰۸-۲۹

- ۱۹ جفت خطا در چهار Packet بانکی تفکیک شد؛ پنج Case جدید در برابر ۱۵ Case پایه قرار دارد.
- fault-stage دقیق صفر است؛ ۱۵ جفت retry/convergence، ۱۶ جفت no-partial-effect و ۹ stage حساس به audit/outbox در baseline دیده شد.
- outcome/assertion/full exact و acceptance صفر باقی ماند؛ هیچ اجرای عملیاتی انجام نشد.

## موج ادامه ـ داوری Outcome Vocabulary کنترل‌های P1 ـ ۲۰۲۶-۰۸-۲۹

- ۳۶ جفت غیرخطا در پنج کنترل تفکیک شد؛ واژگان جدید سه label جهانی در برابر ۱۶ عبارت baseline دارد.
- `REJECTED_NO_EFFECT` روی ۲۱ جفت و committed-original-once روی ۱۱ جفت متمرکز است؛ outcome exact صفر و هر ۳۶ جفت نیازمند mapping است.
- assertion/full exact، پذیرش، اجرا، additive و readiness همگی صفر باقی ماند.

## موج ادامه ـ شکاف خانوادهٔ Assertion/Effect در P1 ـ ۲۰۲۶-۰۸-۲۹

- ۵۵ جفت به دوازده خانواده تبدیل شد؛ family-set دقیق صفر، overlap برابر ۵۵ و no-overlap صفر است.
- ۲۵۵ assignment فقط‌جدید و ۸۰ فقط‌baseline ثبت شد؛ Outbox برابر ۵۵/۱۵، Source immutability برابر ۰/۵۵، Transaction برابر ۰/۲۵ و Version برابر ۵۵/۰ است.
- classifier فقط routing heuristic است و acceptance/readiness ایجاد نمی‌کند.

## موج ادامه ـ وضعیت نهایی Evidence Gap برای P1 ـ ۲۰۲۶-۰۸-۲۹

- Packetization تحلیل هشت Action/۵۶ Case کامل شد، اما semantic disposition بسته‌شده صفر است.
- چهار Packet explicit-none به Alias/New-Action decision و چهار Packet دارای نگاشت state-machine به Semantic-equivalence decision بیرونی نیاز دارند.
- سیزده فیلد closure تثبیت شد؛ named owner، acceptance، اجرا، additive و readiness صفر ماند.

## موج ادامه ـ Shortlist شواهد Baseline برای P2 ـ ۲۰۲۶-۰۸-۲۹

- شش Packet/۴۲ Case بررسی شد؛ پنج Packet کاندید policy/lifecycle و یک Packet tour-payment explicit-none دارد.
- هفت Action reference، ۸۷ Case پایه و ۳۸ kind-overlap با category normalization محدود ثبت شد.
- هیچ exact action، semantic equivalence، acceptance، اجرا یا readiness از shortlist استنتاج نشد.

## موج ادامه ـ Comparator معنایی P2 ـ ۲۰۲۶-۰۸-۲۹

- هفت Candidate به ۷۳ جفت هم‌نوع تبدیل شد؛ یک validate-transition candidate هیچ kind قابل‌مقایسه‌ای ندارد.
- exact precondition صفر، outcome دو، assertion صفر و full exact صفر است؛ schema normalization به‌تنهایی equivalence نیست.
- acceptance، اجرا، additive و readiness صفر باقی ماند.

## موج ادامه ـ داوری Failure Injection در P2 ـ ۲۰۲۶-۰۸-۲۹

- ۱۵ جفت خطا در پنج Packet/شش Candidate comparison ثبت شد؛ stage دقیق دو و stage متفاوت سیزده است.
- baseline برای ۱۰ جفت retry/convergence، ۱۰ جفت no-partial و ۱۳ جفت audit/outbox sensitivity دارد.
- outcome/assertion/full exact و acceptance صفر و هیچ اجرای Runtime انجام نشد.

## موج ادامه ـ داوری Outcome Vocabulary کنترل‌های P2 ـ ۲۰۲۶-۰۸-۲۹

- ۵۸ جفت غیرخطا در شش کنترل Authorization/Concurrency/Idempotency/Scope/Success/Validation تفکیک شد.
- واژگان جدید شش label جهانی در برابر ۲۳ عبارت baseline دارد؛ `REJECTED_NO_EFFECT` روی ۳۸ جفت متمرکز است.
- فقط دو outcome label برابر است، اما assertion/full exact صفر و ۵۶ mapping لازم است؛ acceptance و readiness صفر ماند.

## موج ادامه ـ شکاف خانوادهٔ Assertion/Effect در P2 ـ ۲۰۲۶-۰۸-۲۹

- ۷۳ جفت به دوازده خانواده تبدیل شد؛ family-set دقیق صفر، overlap برابر ۶۴ و no-overlap برابر ۹ است.
- ۴۲۰ assignment فقط‌جدید و ۹۷ فقط‌baseline ثبت شد؛ Audit/Outbox برابر ۷۳/۳۶ و ۷۳/۱۴ است.
- Transaction برابر ۰/۴۶ و Version برابر ۷۳/۱۴ است؛ classifier فقط routing heuristic و acceptance صفر است.

## موج ادامه ـ وضعیت نهایی Evidence Gap برای P2 ـ ۲۰۲۶-۰۸-۲۹

- Packetization تحلیل شش Action/۴۲ Case کامل شد، اما semantic disposition بسته‌شده صفر است.
- یک Packet explicit-none به Alias/New-Action decision و پنج Packet کاندیددار به Semantic-equivalence decision بیرونی نیاز دارند.
- سیزده فیلد closure تثبیت شد؛ named owner، acceptance، اجرا، additive و readiness صفر ماند.

## موج ادامه ـ Shortlist شواهد Baseline برای P3 ـ ۲۰۲۶-۰۸-۲۹

- پنج Packet/۳۵ Case فرمان گزارش بررسی شد؛ هر پنج Packet کاندید دارد و شش Action reference به ۳۱ Case پایه می‌رسد.
- normalization صریح Success/Failure/Concurrency تعداد ۲۶ kind-overlap می‌سازد، اما Print/Export/Completion/Mutation را یکی فرض نمی‌کند.
- exact action، semantic equivalence، Result parity، acceptance، اجرا و readiness صفر باقی ماند.

## موج ادامه ـ Comparator معنایی P3 ـ ۲۰۲۶-۰۸-۲۹

- شش Candidate به ۳۸ جفت هم‌نوع نرمال‌شده تبدیل شد؛ همهٔ Candidateها دست‌کم یک جفت دارند.
- توزیع جفت‌ها Authorization=۶، Concurrency=۲، Failure=۱۸، Idempotency=۶ و Success=۶ است.
- exact precondition/outcome/assertion/full همگی صفر است؛ acceptance، Result parity، اجرا و readiness صفر ماند.

## موج ادامه ـ داوری Failure Injection در P3 ـ ۲۰۲۶-۰۸-۲۹

- ۱۸ جفت خطا در پنج Packet/شش Candidate ثبت شد؛ ۱۵ Case جدید در برابر شش Case پایه و stage دقیق صفر است.
- recovery و unknown/partial disposition در ۱۸/۱۸ جفت؛ حساسیت Audit/Outbox در ۱۵ و File/Print/Completion در ۱۲ جفت دیده شد.
- Outcome/assertion/full exact، acceptance، Result parity و اجرای Runtime صفر باقی ماند.

## موج ادامه ـ داوری Outcome Vocabulary کنترل‌های P3 ـ ۲۰۲۶-۰۸-۲۹

- ۲۰ جفت غیرخطا در چهار کنترل Authorization/Concurrency/Idempotency/Success تفکیک شد.
- سمت جدید سه label دارد؛ baseline از assertion-array استفاده می‌کند و outcome label صریح ندارد.
- هر ۲۰ جفت به mapping نیاز دارد؛ outcome/assertion/full exact، Result parity، acceptance و readiness صفر است.

## موج ادامه ـ شکاف خانوادهٔ Assertion/Effect در P3 ـ ۲۰۲۶-۰۸-۲۹

- ۳۸ جفت در شانزده خانواده مقایسه شد؛ family-set دقیق صفر، overlap برابر ۳۸ و عدم‌تقارن ۱۷۴/۶۷ است.
- File/Render/Per-item جدید هرکدام ۳۸ جفت دارد؛ baseline برابر ۶/۰/۰ و Result/Content parity صریح جدید/پایه ۰/۲ است.
- Audit/Outbox برابر ۳۸/۱۸ و ۰/۲۵ است؛ classifier فقط routing heuristic و acceptance صفر است.

## موج ادامه ـ وضعیت نهایی Evidence Gap برای P3 ـ ۲۰۲۶-۰۸-۲۹

- Packetization پنج Action/۳۵ Case کامل شد، اما semantic disposition و Result parity بسته‌شده هر دو صفر است.
- هر پنج Packet کاندیددار به تصمیم مشترک Effect-equivalence و Frozen-fixture Result/Content parity نیاز دارد.
- چهارده فیلد closure تثبیت شد؛ named owner، acceptance، اجرا، additive و readiness صفر ماند.

## موج ادامه ـ Shortlist شواهد Baseline برای P4 ـ ۲۰۲۶-۰۸-۲۹

- سه Packet/۲۱ Case export فقط‌خواندنی به سه سطح پایه با ۱۴ Case و ۱۰ kind-overlap متصل شد.
- مالکیت هر سه سطح بسته و Result parity برای هر سه applicable است، اما parity proven صفر است.
- Read statement، Export production و Export stock فقط candidate هستند؛ exact action، acceptance، اجرا و readiness صفر است.

## موج ادامه ـ Comparator معنایی P4 ـ ۲۰۲۶-۰۸-۲۹

- سه Candidate به ۱۴ جفت هم‌نوع تبدیل شد: Authorization=۳، Failure=۶، Idempotency=۲ و Success=۳.
- Read بانکی فقط دو جفت دارد و به Export ارتقا داده نمی‌شود.
- exact precondition/outcome/assertion/full، Result parity، acceptance، اجرا و readiness صفر است.

## موج ادامه ـ داوری Failure Injection در P4 ـ ۲۰۲۶-۰۸-۲۹

- شش جفت خطا فقط برای دو Export-file تشکیل شد؛ Candidate بانکی Read هیچ failure/export pair ندارد.
- stage دقیق صفر است و هر شش baseline pair قرارداد retry، quarantine، source immutability و file/artifact دارد.
- Outcome/assertion/full exact، Result parity، acceptance و اجرای Runtime صفر باقی ماند.

## موج ادامه ـ داوری Outcome Vocabulary کنترل‌های P4 ـ ۲۰۲۶-۰۸-۲۹

- هشت جفت غیرخطا در Authorization=۳، Idempotency=۲ و Success=۳ تفکیک شد.
- سمت جدید سه outcome دارد و baseline فقط assertion-array بدون label صریح است؛ هر هشت جفت mapping می‌خواهد.
- Outcome/assertion/full exact، Result parity، acceptance و readiness صفر است.

## موج ادامه ـ شکاف خانوادهٔ Assertion/Effect در P4 ـ ۲۰۲۶-۰۸-۲۹

- ۱۴ جفت در هجده خانواده مقایسه شد؛ family-set دقیق صفر، overlap برابر ۱۴ و عدم‌تقارن ۶۴/۲۱ است.
- File/Render/Per-item جدید ۱۴/۱۴/۱۴ و baseline ۱۲/۲/۰؛ Result/Content parity صریح ۰/۴ است.
- Presentation integrity برابر ۲/۰ و Pinned query/watermark برابر ۶/۱ است؛ acceptance و parity صفر ماند.

## موج ادامه ـ وضعیت نهایی Evidence Gap برای P4 ـ ۲۰۲۶-۰۸-۲۹

- Packetization سه Export/۲۱ Case کامل شد، اما semantic disposition و Result parity بسته‌شده صفر است.
- سه Candidate شامل یک Read بانکی و دو Export-file است و هر سه به تصمیم مشترک Export-effect/Fixture-result نیاز دارد.
- چهارده فیلد closure تثبیت شد؛ acceptance، اجرا، additive و readiness صفر ماند.

## موج ادامه ـ ماتریس Cross-Lane P0 تا P4 ـ ۲۰۲۶-۰۸-۲۹

- ۲۹ Packet/۲۰۳ Case به ۲۰ candidate-bearing و ۹ explicit-none تفکیک شد.
- مسیرها ۹ Alias/New-Action، ۱۲ Semantic، پنج Effect+Result و سه Export+Result است.
- ۲۴۶ جفت شامل ۷۸ Failure و ۱۶۸ Control؛ outcome exact چهار ولی assertion/full/effect exact صفر است.

## موج ادامه ـ صف Intake شواهد بیرونی Cross-Lane ـ ۲۰۲۶-۰۸-۲۹

- همان ۲۹ Packet/۲۰۳ Case بدون افزایش lower bound به چهار گروه intake با توزیع ۹/۱۲/۵/۳ و caseهای ۶۳/۸۴/۳۵/۲۱ تبدیل شد.
- برای ۵۸ انتساب نوع نقش، ۲۹۰ receipt و ۱۵۰ gate assignment تعریف شد؛ این‌ها requirement هستند، نه شواهد دریافت‌شده.
- named owner، receipt دریافت‌شده/پذیرفته‌شده، تصمیم بسته، اجرا، owner approval و readiness همگی صفر ماند.

## موج ادامه ـ ماتریس Validation برای Receiptها ـ ۲۰۲۶-۰۸-۲۹

- ۲۹۰ receipt requirement به ۲۹۰ slot یکتا تبدیل شد؛ هر intake دقیقاً ده slot و توزیع مسیرها ۹۰/۱۲۰/۵۰/۳۰ است.
- ۲۱ نوع receipt در هفت کلاس، چهارده metadata اجباری، چهارده rejection code و هشت state تعریف شد.
- همهٔ slotها `MISSING` هستند؛ hash/content/role validation، semantic closure، اجرا و readiness صفر باقی ماند.

## موج ادامه ـ Worklist نقش‌محور Cross-Lane ـ ۲۰۲۶-۰۸-۲۹

- ۱۳ نوع نقش به ۵۸ Packet assignment، ۴۰۶ Case assignment و ۵۸۰ receipt-slot assignment مسیردهی شد؛ اعداد دوبرابرشده ناشی از دو نقش برای هر Packet است.
- مجموعهٔ واقعی همچنان ۲۹ Packet/۲۰۳ Case/۲۹۰ slot است و هر worklist hash مستقل مجموعهٔ slotها دارد.
- هر ۱۳ worklist در وضعیت `UNASSIGNED_NAMED_OWNER` است؛ owner roster، receipt acceptance و readiness صفر ماند.

## موج ادامه ـ Packetهای فعال‌سازی جمع‌آوری شواهد P0 ـ ۲۰۲۶-۰۸-۲۹

- هفت Packet/۴۹ Case P0 به چهار Alias/New Action و سه Semantic Equivalence تقسیم شد؛ سه کاندید ۶۶ جفت شامل ۲۰ Failure و ۴۶ Control دارد.
- ۷۰ receipt slot، ۱۴ role assignment از هفت نوع، ۳۵ gate و ۴۹ prerequisite assignment به Packetها متصل شد.
- همهٔ Packetها `NOT_ACTIVATED_EXTERNAL_EVIDENCE_MISSING` هستند و صریحاً هیچ اجرای عملیاتی را مجاز نمی‌کنند.

## موج ادامه ـ Sequencing فعال‌سازی P1 تا P4 ـ ۲۰۲۶-۰۸-۲۹

- ۲۲ Packet/۱۵۴ Case به Laneهای P1=۸/۵۶، P2=۶/۴۲، P3=۵/۳۵ و P4=۳/۲۱ تقسیم شد.
- ۲۲۰ receipt، ۴۴ role assignment از ۱۲ نوع، ۱۱۵ gate و ۱۵۴ prerequisite assignment ثبت شد.
- هشت Packet P3/P4 نیازمند CG-05 است؛ command/export success جای Result/Render/File parity را نمی‌گیرد و activation همه صفر است.

## موج ادامه ـ اصلاح Multi-Class Receipt و ماتریس CG-05 P3/P4 ـ ۲۰۲۶-۰۸-۲۹

- classifier تک‌کلاسه، پنج receipt مرکب `failure_stage_and_per_item_outcome` را فقط Transaction می‌دید و CG-05 را حذف می‌کرد؛ مدل به class-set و gate-union اصلاح شد.
- اکنون ۱۴ slot چندکلاسه و ۲۷ slot تحت CG-05 است؛ پنج receipt P3 به `CG-02/03/05/04` متصل شد.
- هشت Packet/۵۶ Case به ۲۰ بُعد و ۱۶۰ assignment وصل شد؛ در ۵۲ جفت، effect-family exact صفر و Result parity جدید/پایه ۰/۶ است.

## موج ادامه ـ قرارداد Frozen Fixture/Output برای P3/P4 ـ ۲۰۲۶-۰۸-۲۹

- هشت قرارداد دقیقاً به پنج فرمان چاپ P3 و سه فرمان Export P4 نگاشت شد و هرکدام هفت Case دارد؛ جمع پوشش ۵۶ Case است.
- سه schema شانزده‌فیلدی Fixture، Output و Comparison، در مجموع ۵۱۲ field assignment و ۱۶ سمت Capture الزام می‌کنند؛ هیچ مقدار واقعی یا خروجی خام ذخیره نشده است.
- ۱۶۰ اتصال بُعد parity و ۲۷ اتصال receipt زیر CG-05 حفظ شد؛ Capture، Comparison، Acceptance، Execution و Readiness همگی صفر است.

## موج ادامه ـ Playbook تشخیص اختلاف Result Parity در P3/P4 ـ ۲۰۲۶-۰۸-۲۹

- ده سناریوی تشخیصی با حداقل ۱۰۰ step، ۷۲ اتصال Packet، ۵۰۴ اتصال Case و ۳۴ اتصال بُعد parity تعریف شد.
- چهار خروجی مجاز میان Match مبتنی بر hash، استثنای versioned تأییدشده، شاهد نامعتبر/کهنه و اختلاف توضیح‌نداده‌شده تفکیک می‌کنند.
- تا پیش از مجوز و شاهد پذیرفته‌شده، اجرای تشخیص، Repair، Replay، Recapture، Parity و Promotion همگی صفر/مسدود می‌ماند.

## موج ادامه ـ بازیابی Runner رسمی و حذف اتصال پنهان ـ ۲۰۲۶-۰۸-۳۱

- Runner نهایی پس از یک نتیجهٔ `FAIL` امکان bootstrap نداشت، درحالی‌که Bundleهای پایه به همان نتیجه وابسته بودند؛ این چرخه با فلگ صریح و غیرپیش‌فرض `--exclude-final-bundle-bootstrap` و ثبت تعداد فایل‌های حذف‌شده رفع شد.
- Bootstrap فقط شاخهٔ خودارجاعی را برای seed کنار می‌گذارد و نتیجهٔ نهایی باید با حالت پیش‌فرض، glob کامل و exclusion صفر ثبت شود.
- تنها تستی که در suite موسوم به آفلاین به Share شبکه وصل می‌شد با آزمون محلی قرارداد Extractor جایگزین شد؛ پنج hash و شواهد Artifact حفظ شدند و Load/Execute اسمبلی همچنان ممنوع است.
- پس از seed، settle و اجرای کامل، ۳۰۸ فایل و ۱۵۰۹ تست با exclusion صفر PASS شدند؛ این عدد پیش از اضافه‌شدن دو فایل تست بستهٔ داوری جدید است.

## موج ادامه ـ داوری Golden/UAT و Promotion Guard برای P3/P4 ـ ۲۰۲۶-۰۸-۳۱

- هشت Packet/۵۶ Case و چهار Outcome به ۳۲ مسیر داوری و ۲۲۴ اتصال Outcome-to-Case تبدیل شد.
- دوازده Promotion Guard برای هر Packet، در مجموع ۹۶ انتساب Guard، به ۱۶۰ بُعد parity و ۲۷ Receipt زیر CG-05 متصل شد.
- فقط `MATCH_CONFIRMED_BY_ACCEPTED_HASH_ONLY_EVIDENCE` می‌تواند وارد بازبینی پذیرش CG-05 شود و همان نیز Closure یا Readiness خودکار ایجاد نمی‌کند.
- Exception نتیجهٔ parity نیست، شاهد stale نیازمند مجوز جداگانهٔ recollection و اختلاف توضیح‌نداده‌شده Hard Block است؛ تمام داوری‌ها، Closure، UAT و Readiness فعلاً صفر است.

## موج ادامه ـ قرارداد Hash-Only Comparison Adapter برای ERP مقصد ـ ۲۰۲۶-۰۸-۳۱

- برای هشت Packet/۵۶ Case، هشت Adapter Profile با Input envelope و Output receipt هجده‌فیلدی ساخته شد.
- دوازده مرحلهٔ canonicalization، تعداد ۱۶ Error code و شش Typed status تعریف شد؛ ۲۸۸ schema-field assignment و ۹۶ stage assignment داریم.
- Adapter به ۱۶۰ بُعد parity، تعداد ۲۷ Receipt CG-05 و ۹۶ Promotion Guard متصل است؛ SHA-256 با domain separation، تفکیک set/order hash و منع float/raw-value persistence الزام شد.
- Idempotency از پنج hash نسخه/Profile/Fixture/Legacy/Target/Dimension-set مشتق می‌شود؛ تکرار برابر Receipt قبلی را برمی‌گرداند و تعارض رد می‌شود.
- Implementation، Request، Canonicalization، Comparison، Receipt، Parity، UAT و Readiness همگی صفر است و هیچ شبکه یا دیتابیسی استفاده نشد.

## موج ادامه ـ بردارهای استاندارد و قرارداد اصالت Receipt مقایسه ـ ۲۰۲۶-۰۸-۳۱

- برای هر هشت Adapter Profile، دوازده بردار canonical مثبت و شانزده بردار خطای منفی تعریف شد؛ ۲۸ بردار و ۲۲۴ انتساب Profile-to-Vector داریم.
- دوازده digest مورد انتظار با SHA-256، domain separation و JSON canonical مصنوعی ساخته شد؛ taxonomy شانزده خطای منفی دقیقاً با قرارداد Adapter برابر است.
- قرارداد اصالت Receipt شانزده فیلد metadata، هشت نتیجهٔ verification، شش وضعیت چرخهٔ کلید، هشت قاعدهٔ rotation و ده گام verification دارد.
- الگوریتم امضا عمداً انتخاب نشده و به تصمیم مستقل Platform/Security وابسته است؛ هیچ private/public key material، signature bytes یا مقدار تجاری در Artifact ذخیره نشد.
- Signing، Verification، Acceptance، Result parity، UAT و Readiness همگی صفر ماند و فقط `AUTHENTIC_CURRENT` می‌تواند وارد داوری مستقل شود؛ اصالت به‌تنهایی برابری نتیجه یا Closure نیست.

## موج ادامه ـ Harness آفلاین Adapter و Decision Record رمزنگاری ـ ۲۰۲۶-۰۸-۳۱

- Harness مرجع برای هشت Profile و دوازده بردار مثبت، ۹۶ digest مصنوعی را بازتولید کرد و ۹۶/۹۶ PASS شد.
- شانزده بردار منفی برای هر Profile به ۱۲۸ lint عضویت taxonomy تبدیل شد و ۱۲۸/۱۲۸ PASS شد؛ هیچ Runtime fault injection انجام نشد.
- چهار Candidate الگوریتم و چهار Provider pattern با چهارده معیار، جمعاً ۱۱۲ انتساب، و ده Gate تصمیم ثبت شد؛ همه `CANDIDATE_NOT_SELECTED` و Gateها بازند.
- استانداردهای رسمی FIPS 186-5، SP 800-57، RFC 8017، RFC 8032، CSWP 39upd1 و FIPS 204 فقط مبنای Decision Record هستند و انتخاب محیطی ایجاد نمی‌کنند.
- Key material، Signature، Signing/Verification، Operational adapter run، Receipt acceptance، Result parity و Readiness همگی صفر ماند.

## موج ادامه ـ Reference Codec منفی مصنوعی Adapter ـ ۲۰۲۶-۰۸-۳۱

- یک Validator خالص و بدون I/O برای شانزده قاعدهٔ خطای Adapter ساخته شد؛ هشت Baseline مصنوعی سالم ۸/۸ PASS شدند.
- شانزده Mutation تک‌فیلدی برای هر هشت Profile اجرا شد؛ ۱۲۸/۱۲۸ Error code و Typed status مطابق انتظار بود و fail برابر صفر ماند.
- تقدم خطاها ثابت و fail-fast است؛ هر Mutation دقیقاً یک Control field را تغییر می‌دهد و Trigger ناشناخته رد می‌شود.
- این Reference Codec فقط رفتار مصنوعی قرارداد را اجرا می‌کند و Operational adapter implementation یا Failure Injection در ERP نیست.
- Capture، Receipt emission/acceptance، Result parity، Command readiness و Pilot readiness همگی صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت است.

## موج ادامه ـ مجوز Capture ایزوله و Redaction برای P3/P4 ـ ۲۰۲۶-۰۸-۳۱

- هشت Packet/۵۶ Case و دو سمت Legacy/Target به شانزده Capture Channel با مجوزهای کاملاً جدا تبدیل شد.
- schema درخواست مجوز ۲۴ فیلد و Redaction attestation هجده فیلد دارد؛ چهارده Gate به ۲۲۴ assignment متصل شد.
- شش Role به ۹۶ assignment و پنج قاعدهٔ SoD متصل است؛ همهٔ Gateها `UNMET`، Roleها `UNASSIGNED` و Channelها `NOT_REQUESTED` هستند.
- persistence به هشت دستهٔ hash/count/status/reference محدود و چهارده دستهٔ خام یا حساس صریحاً ممنوع شد.
- Request، Approval، Activation، Capture، Attestation، Receipt acceptance، Result parity و Readiness همگی صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ Handoff شواهد Capture به Comparison Adapter ـ ۲۰۲۶-۰۸-۳۱

- شانزده Channel به هشت Pair Legacy/Target و هشت Adapter Profile متصل شد؛ هر Pair دقیقاً دو سمت و یک Profile دارد.
- ۲۷ Receipt slot زیر CG-05 به ۵۴ Channel link و بیست بُعد parity به ۳۲۰ Channel link تبدیل شد.
- Envelope بیست‌فیلدی و دوازده Gate برای هر Pair، یعنی ۹۶ assignment، فقط Hash/Count/Status/Reference را اجازه می‌دهد و Payload transfer را ممنوع می‌کند.
- همهٔ Pairها `NOT_READY_NO_AUTHORIZED_CAPTURE`، تمام Gateها `UNMET` و accepted evidence در همهٔ Linkها صفر است.
- Handoff، Adapter request، Comparison، Receipt، Result parity، CG-05 closure و Readiness همگی صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ Custody/Retention/Revocation شواهد hash-only ـ ۲۰۲۶-۰۸-۳۱

- ۵۴ اتصال Channel-to-Receipt به ۵۴ Custody requirement یکتا با schema بیست‌فیلدی تبدیل شد.
- نه State، دوازده Transition، ده Gate/۵۴۰ assignment، چهار Role/۲۱۶ assignment، هشت Retention rule و دوازده Rejection code تعریف شد.
- Expired، Revoked و Superseded برای Handoff نامعتبرند؛ expiry خودکار تمدید نمی‌شود و disposition فقط tombstone مبتنی بر hash و lineage را حفظ می‌کند.
- همهٔ requirementها `MISSING`، Gateها `UNMET` و Roleها `UNASSIGNED` هستند؛ هیچ Receipt یا شاهد خارجی دریافت نشد.
- Custody، Accepted evidence، Handoff، Parity، CG-05 و Readiness همگی صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ Propagation ابطال شواهد و بازشدن Gateها ـ ۲۰۲۶-۰۸-۳۱

- دوازده علت Invalidation به ۵۴ Custody requirement، یعنی ۶۴۸ assignment، متصل شد.
- گراف پایین‌دست ۵۴ Edge به Pair، تعداد ۵۴ به Profile، تعداد ۵۴ به Receipt slot، تعداد ۹۶ Pair-to-Promotion-Guard و ۲۷ Slot-to-Packet دارد؛ جمع Edge برابر ۲۸۵ است.
- هشت Reopen action، Custody/Handoff/Adapter/Receipt/Guard/Recapture/Readjudication/Readiness را fail-closed می‌کند و reacceptance خودکار ممنوع است.
- همهٔ assignmentها `NO_EVENT_OBSERVED` هستند؛ هیچ Invalidation، Reopen، Reacceptance یا اجرای عملیاتی رخ نداده است.
- Result parity، CG-05 و Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ Freshness/Clock policy شواهد P3/P4 ـ ۲۰۲۶-۰۸-۳۱

- چهار نوع Artifact، هشت Freshness outcome، دوازده Vector و ده Clock rule با Envelope شانزده‌فیلدی تعریف شد.
- دوازده Vector برای هر چهار نوع با timestamp ثابت اجرا شد؛ ۴۸/۴۸ PASS و fail صفر است و هیچ System clock خوانده نشد.
- `valid_from` inclusive و `expires_at` exclusive است؛ timezone-aware، Clock trust و Interval معتبر الزامی‌اند و revoke/supersede مقدم‌اند.
- ۵۴ Custody requirement به ۲۱۶ Freshness obligation تبدیل شد؛ همه `MISSING_TEMPORAL_EVIDENCE` هستند.
- Real evaluation، Current evidence، Acceptance، Handoff، Parity و Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ قرارداد شاهد تمرین Backup/Restore برای ERP مقصد ـ ۲۰۲۶-۰۸-۳۱

- چهارده ماژول مقصد به شش کلاس دارایی بازیابی و ۸۴ تعهد Module-to-Asset متصل شد؛ وجود Backup بدون Restore جداگانه اثبات بازیابی نیست.
- دوازده سناریوی تمرین، از Full/PIT restore تا خرابی قطعه، drift، replay، rebuild، reconciliation و نقض RPO/RTO، به ۱۶۸ انتساب ماژولی تبدیل شد.
- هجده فیلد هدف بازیابی، بیست فیلد شاهد تمرین، چهارده Gate/۱۹۶ assignment و پنج Role/۷۰ assignment تعریف شد؛ همهٔ هدف‌ها `UNAPPROVED`، سناریوها `UNEXECUTED`، Gateها `UNMET` و Roleها `UNASSIGNED` هستند.
- بالا آمدن سرویس یا بارگذاری schema به‌تنهایی موفقیت Restore نیست؛ reconciliation بین‌ماژولی و اندازه‌گیری RPO/RTO لازم است و Restore در Production صریحاً ممنوع است.
- Backup read/create، Restore run/pass/reconcile، Owner approval، Recovery readiness، Command readiness و Pilot readiness همگی صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ ترتیب وابستگی و تطبیق موج‌های Restore مقصد ـ ۲۰۲۶-۰۸-۳۱

- DAG چهارده ماژول Blueprint دارای ۳۸ Edge است و به هفت موج Restore تبدیل شد؛ `platform` تنها عضو موج صفر و هر dependency در موجی زودتر از dependent قرار دارد.
- ده Stage برای هر ماژول، یعنی ۱۴۰ assignment، و چهار بُعد reconciliation برای هر Edge، یعنی ۱۵۲ assignment، تعریف شد.
- چهارده Gate برای هر هفت موج، یعنی ۹۸ assignment، و پنج Role برای هر موج، یعنی ۳۵ assignment، با Receipt بیست‌فیلدی و نه Outcome ساخته شد.
- Service start/schema load تطبیق نیست، Read model منبع authoritative نیست، Replay پیش از Idempotency reconciliation و Restore در Production ممنوع است و blocking unknown enablement را می‌بندد.
- هر هفت موج `NOT_STARTED`، تمام Stageها `UNEXECUTED`، همهٔ Edgeها `UNRECONCILED`، Gateها `UNMET` و Roleها `UNASSIGNED` هستند؛ Restore/Enablement/Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ Idempotency و همگرایی Outbox/Inbox فرمان‌های مقصد ـ ۲۰۲۶-۰۸-۳۱

- ۴۹ فرمان چهارده ماژول Blueprint به Envelope بیست‌ودوفیلدی، Receipt بیست‌فیلدی، Outbox شانزده‌فیلدی و Inbox چهارده‌فیلدی متصل شد.
- چهارده Failure stage برای هر فرمان ۶۸۶ assignment و هشت بُعد convergence برای هر فرمان ۳۹۲ assignment ایجاد کرد.
- شانزده Gate/۷۸۴ assignment، پنج Role/۲۴۵ assignment و ده Outcome میان Commit نخست، Replay برابر، Conflict، Commit نامعلوم و Quarantine تفکیک می‌کنند.
- Same-key/same-fingerprint باید Receipt نخست را برگرداند؛ payload متفاوت Conflict است، Commit نامعلوم Retry کور نمی‌دهد و Recovery replay پیش از تطبیق Restore/Watermark ممنوع است.
- Implementation، Fault injection، Replay proof، Outbox atomicity، Inbox convergence، Owner approval و Readiness همگی صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ مالک تراکنش، Saga و Compensation مقصد ـ ۲۰۲۶-۰۸-۳۱

- ۳۸ Edge ماژولی برای ۴۹ فرمان به ۱۵۹ تعهد Command-to-Participant تبدیل شد.
- چهار Pattern برای هر فرمان، یعنی ۱۹۶ Candidate، همگی `CANDIDATE_NOT_SELECTED` هستند؛ مرز تراکنش ۱۸، Receipt Saga بیست و Receipt جبران ۱۸ فیلد دارد.
- دوازده Failure stage/۵۸۸ assignment، شانزده Gate/۷۸۴ assignment، شش Role/۲۹۴ assignment و ده Outcome تعریف شد.
- موفقیت Participant موفقیت Parent نیست؛ Commit نامعلوم پیش از reconciliation نه Retry و نه Compensation می‌شود و Compensation یک Business action مستقل و idempotent است، نه rollback.
- Pattern selection، مالک نام‌دار، Fault run، Runtime atomicity، Saga/Compensation acceptance و Readiness همگی صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ Authorization، Scope و Decision Trace فرمان‌های مقصد ـ ۲۰۲۶-۰۸-۳۱

- دوازده بُعد Authorization برای هر ۴۹ فرمان، یعنی ۵۸۸ assignment، از Principal/Tenant تا Resource/State/SoD/Policy/Repository تعریف شد.
- چهارده Negative case برای هر فرمان ۶۸۶ assignment، Decision Trace بیست‌ودوفیلدی، شانزده Gate/۷۸۴ assignment و پنج Role/۲۴۵ assignment ساخته شد.
- Default deny و deny-wins است؛ Admin/Role name bypass، Client-only authorization، self-approval، bulk mixed-scope partial success و stale policy صریحاً ممنوع‌اند.
- دو baseline تاریخی Role/SoD و Route Matrix فاقد فیلد `validation` بودند؛ به‌جای جعل PASS، artifact identity و schema آن‌ها pin شد و فقط منابع جاری ملزم به PASS ماندند.
- Implementation، Authenticated UAT، Allow/Deny receipt، Repository coverage، Runtime authorization و Readiness همگی صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ Redaction و Retention کانال‌های Evidence/Logging مقصد ـ ۲۰۲۶-۰۸-۳۱

- ده کانال Evidence برای ۴۹ فرمان به ۴۹۰ assignment و چهارده کلاس ممنوع به ۱۴۰ سیاست `DENY_PERSIST` متصل شد؛ فقط هشت کلاس hash/reference/count/status/version/time/role/boolean مجاز است.
- Attestation بیست‌فیلدی و Retention record شانزده‌فیلدی، چهارده Negative vector/۱۴۰ assignment، شانزده Gate/۱۶۰ assignment و پنج Role/۵۰ assignment تعریف شد.
- Unknown/nested payload، Stack خام، metric label حساس، hash بدون domain separation، endpoint/file/backup/message body و تمدید خودکار expiry fail-closed هستند.
- هیچ Log، Trace، Backup، Message، Export، فایل یا Runtime sample خوانده نشد.
- Implementation، Sample scan، Attestation، Retention approval، Disposition، Incident closure و Readiness همگی صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ Reference Validator مصنوعی Redaction شواهد ـ ۲۰۲۶-۰۸-۳۱

- یک Validator خالص و بدون I/O برای هشت فیلد مجاز، سیزده گروه فیلد ممنوع و Unknown/Nested payload ساخته شد.
- ده Baseline مثبت ۱۰/۱۰ و چهارده Mutation تک‌فیلدی در هر ده کانال ۱۴۰/۱۴۰ PASS شد؛ جمع ۱۵۰/۱۵۰ است.
- Hashهای ۶۴رقمی، Reference غیرقابل‌برگشت، Count، Status، Timestamp timezone-aware، Role type و Boolean به‌صورت type-aware بررسی می‌شوند.
- هیچ Log، Trace، Message، File، Backup، Export یا Runtime sample خوانده نشد؛ این Validator امنیت عملیاتی یا scanner production نیست.
- Reference implementation یک، Operational implementation/Runtime scan/Attestation/Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ Snapshot/Delta/Reconciliation برای Cutover مقصد ـ ۲۰۲۶-۰۸-۳۱

- چهارده ماژول در دوازده فاز Cutover به ۱۶۸ assignment و در دوازده بُعد reconciliation به ۱۶۸ assignment متصل شد.
- Snapshot manifest بیست‌ودوفیلدی، Delta receipt بیست‌فیلدی و Cutover decision هجده‌فیلدی، هجده Gate/۲۵۲ assignment و شش Role/۸۴ assignment تعریف شد.
- Clone کهنه Live نیست، Snapshot بدون Watermark current نیست، Delta gap/overlap/out-of-order رد می‌شود و Replay برابر اثر تازه نمی‌سازد.
- `blocking_unknown` برای Schedule قابل waiver نیست، Operator self-approval ندارد و Target write پیش از Source fence و Receipt نهایی بسته است.
- Snapshot/Delta capture/read/apply، Reconciliation، Cutover، Write enablement و Readiness همگی صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ Environment Isolation، Write Fence و Execution Token ـ ۲۰۲۶-۰۸-۳۱

- چهار محیط Legacy reference/Sandbox/UAT/Production برای ۴۹ فرمان به ۱۹۶ assignment متصل و همگی `NOT_AUTHORIZED` شدند.
- چهارده Fence در چهار محیط ۵۶ assignment، دوازده Negative case در ۴۹ فرمان ۵۸۸ assignment و Execution token بیست‌فیلدی تعریف شد.
- هجده Gate/۸۸۲ assignment، شش Role/۲۹۴ assignment و ده Outcome، Environment/Token/Scope/Fingerprint/Version/Promotion mismatch را fail-closed می‌کنند.
- Legacy عملیاتی Command target نیست؛ Environment از endpoint استنباط نمی‌شود، Token UAT در Production قابل Replay نیست و UAT success Promotion خودکار نمی‌دهد.
- Token/Connection/Legacy یا Target run/Fence attestation/Approval/Readiness همگی صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ Release Promotion، Change و Rollback مقصد ـ ۲۰۲۶-۰۸-۳۱

- دو گذار Sandbox→UAT و UAT→Production برای چهارده ماژول به ۲۸ assignment و هشت کلاس دارایی انتشار به ۱۱۲ assignment متصل شد.
- دوازده مرحلهٔ انتشار ۱۶۸ assignment، Release manifest بیست‌ودوفیلدی، Change receipt بیست‌فیلدی و Rollback receipt هجده‌فیلدی تعریف شد.
- دوازده Failure case در چهارده ماژول ۱۶۸ assignment، بیست Gate تعداد ۲۸۰ assignment و شش Role تعداد ۸۴ assignment می‌سازد.
- Artifact بین محیط‌ها بازساخته نمی‌شود؛ digest/provenance/signature باید همان باشد و پذیرش UAT مجوز Production نیست.
- شروع برنامه موفقیت نیست؛ Health/SLO و invariant کسب‌وکار باید جدا تأیید شوند و migration ناسازگار یا rollback مخرب promotion را می‌بندد.
- Manifest/Verification/Deploy/Promotion/Production approval/Rollback/Health acceptance/Readiness همگی صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ Observability، SLO، Alert و Incident مقصد ـ ۲۰۲۶-۰۸-۳۱

- دوازده کلاس Signal در چهارده ماژول ۱۶۸ assignment و دوازده مرحلهٔ lifecycle نیز ۱۶۸ assignment ایجاد کرد.
- SLI receipt و SLO policy هرکدام هجده فیلد، Alert receipt بیست و Incident receipt بیست‌ودو فیلد دارد.
- چهارده Failure case تعداد ۱۹۶، بیست Gate تعداد ۲۸۰ و شش Role تعداد ۸۴ assignment ساخت.
- Process-up موفقیت نیست، Technical health جای Business invariant نیست و Missing/Stale telemetry fail-closed است.
- Alert بدون Owner/Route/Runbook actionable نیست؛ Restart، Severity downgrade یا waiverِ residual difference بدون Evidence مجاز نیست.
- هیچ Telemetry واقعی خوانده یا query، Alert ارسال یا Incident ایجاد نشد؛ Implementation/Approval/Runtime/Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ Configuration/Policy Immutability و Change Audit مقصد ـ ۲۰۲۶-۰۸-۳۱

- ده Scope در چهارده ماژول ۱۴۰ assignment، دوازده Policy type تعداد ۱۶۸ و دوازده مرحلهٔ lifecycle تعداد ۱۶۸ assignment ایجاد کرد.
- Snapshot بیست‌ودو، Change receipt بیست‌وچهار، Evaluation trace بیست و Emergency override بیست فیلد دارد.
- چهارده Failure case تعداد ۱۹۶، بیست Gate تعداد ۲۸۰ و هفت Role تعداد ۹۸ assignment ساخت.
- Mutation درجا و حذف history ممنوع؛ precedence قطعی و deny-wins، effective-time پس از approval و rollback فقط activation یک نسخه است.
- Feature flag مجوز دورزدن Authorization/SoD/invariant ندارد و Emergency override محدود، مستقل، قابل‌لغو و reconcileشده است.
- هیچ Config/Feature flag/Secret/Cache عملیاتی خوانده و هیچ Change/Rollback/Override اجرا نشد؛ Runtime/Approval/Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ Data Provenance و Read-model Rebuild مقصد ـ ۲۰۲۶-۰۸-۳۱

- دوازده Data class در چهارده ماژول ۱۶۸ assignment، هشت Authority class تعداد ۱۱۲ و دوازده مرحلهٔ lifecycle تعداد ۱۶۸ assignment ساخت.
- Provenance receipt بیست‌وچهار، Rebuild receipt بیست‌ودو، Drift receipt بیست و Disposition receipt هجده فیلد دارد.
- چهارده Failure case تعداد ۱۹۶، بیست Gate تعداد ۲۸۰ و شش Role تعداد ۸۴ assignment ایجاد کرد.
- Read model/Cache/Report/Export authoritative نیست؛ Direct repair ممنوع و Rebuild فقط از منبع نسخه‌دار و Watermark معتبر است.
- Gap/Overlap/Fork/Unknown/Partial rebuild مانع Read switch است و همان source/recipe/version باید digest یکسان تولید کند.
- هیچ Dataset/Table/Row/Schema/Sample خوانده و هیچ Rebuild/Replay/Repair/Delete/Read-switch اجرا نشد؛ Runtime/Approval/Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ Reference Evaluator مصنوعی Promotion/Rollback ـ ۲۰۲۶-۰۸-۳۱

- یک Evaluator خالص و بدون I/O با schema دقیق برای سه تصمیم UAT promotion، Production promotion و Production rollback ساخته شد.
- سه Baseline مثبت ۳/۳ و بیست‌وسه Mutation منفی ۲۳/۲۳ PASS شد؛ جمع ۲۶/۲۶ و بیست Outcome متمایز مشاهده شد.
- تقدم خطا از Schema/Digest تا Supply-chain/Test/Token/Recovery/Canary/Unknown/Health/Approval/Role/Rollback safety قطعی است.
- UAT نیازی به Production approval ندارد اما آن را ایجاد نمی‌کند؛ Rollback ناامن به Forward-fix می‌رود.
- فقط hash/boolean/count مصنوعی پردازش شد؛ هیچ Runtime manifest/artifact/receipt خوانده و هیچ Deploy/Promotion/Rollback اجرا نشد.
- Reference implementation یک، Operational implementation/Receipt/Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ Monetary، Quantity و Temporal Semantics مقصد ـ ۲۰۲۶-۰۸-۳۱

- چهارده بُعد معنایی در چهارده ماژول ۱۹۶ assignment و دوازده invariant و دوازده stage هرکدام ۱۶۸ assignment ساخت.
- Numeric policy بیست‌ودو، Calculation receipt بیست‌وچهار و Conversion/Temporal receipt هرکدام بیست فیلد دارد.
- شانزده Failure case تعداد ۲۲۴، بیست‌ودو Gate تعداد ۳۰۸ و هفت Role تعداد ۹۸ assignment ایجاد کرد.
- Binary float، rounding/scale ضمنی، residual گمشده، rate بی‌نسخه، unit ناسازگار، timestamp naive و posting در دورهٔ بسته ممنوع است.
- Jalali/Gregorian نمایش نسخه‌دار است و authoritative instant یا posting date نیست.
- هیچ Amount/Quantity/Rate/Date/Timestamp خوانده و هیچ Calculation/Conversion/Posting اجرا نشد؛ Runtime/Approval/Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ Reference Evaluator مصنوعی Monetary/Temporal ـ ۲۰۲۶-۰۸-۳۱

- Evaluator خالص Decimal quantization، Largest-remainder allocation، Conversion، Reversal و Temporal/Fiscal validation ساخته شد.
- بیست Vector مثبت و چهارده Vector منفی، جمعاً ۳۴/۳۴، PASS و سیزده Error code متمایز مشاهده شد.
- شش Rounding، چهار Allocation، چهار Conversion، سه Reversal و سه Temporal baseline پوشش دارد.
- Allocation مجموع را با residual قطعی و tie-break index پایدار نگه می‌دارد؛ float، non-finite، mode/scale و denominator نامعتبر fail-closed است.
- Naive timestamp، Zone/Offset mismatch، دورهٔ مالی بسته و Calendar authoritative رد می‌شوند.
- تمام valueها مصنوعی‌اند؛ Operational read/run/receipt/readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ Optimistic Concurrency، Version و Fencing مقصد ـ ۲۰۲۶-۰۹-۰۱

- ده بُعد concurrency در ۴۹ فرمان ۴۹۰ assignment و شش Strategy candidate تعداد ۲۹۴ assignment ساخت؛ هیچ Strategy انتخاب نشد.
- Concurrency receipt بیست‌ودو، Conflict receipt هجده و Lease/Fencing receipt بیست فیلد دارد.
- چهارده Failure case تعداد ۶۸۶، هجده Gate تعداد ۸۸۲ و شش Role تعداد ۲۹۴ assignment ایجاد کرد.
- Idempotency کنترل concurrency نیست؛ expected-version و repository CAS اجباری و match count غیر از یک typed conflict است.
- Lost update/write skew/sequence duplicate/stale lease/fence ممنوع؛ Unknown commit پیش از Retry باید reconcile شود.
- هیچ Version/Transaction/Lock/Lease/Fence خوانده و هیچ Command/Retry اجرا نشد؛ Strategy/Proof/Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ Reference Evaluator مصنوعی Concurrency ـ ۲۰۲۶-۰۹-۰۱

- Evaluator خالص ترتیب Receipt/Unknown/Retry/Version/CAS/Invariant/Sequence/Lease/Fence/Bulk را executable کرد.
- سه مسیر مثبت Commit/Replay/Deadlock-retry و سیزده Mutation منفی، جمعاً ۱۶/۱۶، PASS شد.
- چهارده Outcome متمایز، Version conflict را از CAS cardinality و Sequence/Lease/Fence conflict جدا می‌کند.
- Receipt موجود پیش از Version بررسی و Unknown commit پیش از هر Retry به Reconciliation هدایت می‌شود.
- فقط version/count/boolean مصنوعی پردازش شد؛ Operational read/run/receipt/readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ Master-data Identity، Dedup، Merge و Supersession مقصد ـ ۲۰۲۶-۰۹-۰۱

- دوازده Entity class در چهارده ماژول ۱۶۸ assignment، چهارده Identity dimension تعداد ۱۹۶ و دوازده Stage تعداد ۱۶۸ assignment ساخت.
- Identity receipt بیست‌ودو، Merge receipt بیست‌وچهار و Supersession/Cross-reference receipt هرکدام بیست فیلد دارد.
- شانزده Failure case تعداد ۲۲۴، بیست‌ودو Gate تعداد ۳۰۸ و هفت Role تعداد ۹۸ assignment ایجاد کرد.
- Uniqueness بدون scope، normalization مخرب و auto-merge با fuzzy/single attribute ممنوع است.
- Merge به survivor/loser/field-resolution/unmerge نیاز دارد؛ تاریخچه immutable بازنویسی نمی‌شود و Supersession حذف نیست.
- هیچ Identifier/Code/Name/PII/Master record خوانده و هیچ Merge/Propagation اجرا نشد؛ Runtime/Approval/Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ Capacity، Timeout، Backpressure و Degradation مقصد ـ ۲۰۲۶-۰۹-۰۱

- دوازده بُعد Capacity در چهارده ماژول ۱۶۸ assignment و دوازده Stage نیز ۱۶۸ assignment ساخت.
- Capacity policy بیست‌ودو، Timeout/Retry receipt بیست، Overload receipt بیست‌ودو و Degradation receipt بیست فیلد دارد.
- شانزده Failure case تعداد ۲۲۴، بیست Gate تعداد ۲۸۰ و شش Role تعداد ۸۴ assignment ایجاد کرد.
- منابع/صف/Batch/Payload بی‌کران و child timeout بزرگ‌تر از parent ممنوع؛ Retry به idempotency، budget، backoff و jitter نیاز دارد.
- Degraded mode Authorization و invariant مالی/انبار/پرداخت را دور نمی‌زند و Recovery پیش از drain/reconciliation بسته است.
- هیچ Traffic/Metric/Queue/Resource خوانده و هیچ Load/Fault/Overload اجرا نشد؛ Runtime/Approval/Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ Reference Evaluator مصنوعی Capacity Budget ـ ۲۰۲۶-۰۹-۰۱

- Evaluator خالص برای parent/child timeout، retry، inflight، queue، circuit، degradation و recovery ساخته شد.
- شش مسیر مثبت و سیزده Mutation منفی، جمعاً ۱۹/۱۹، PASS و شانزده Outcome متمایز ثبت شد.
- Blocking unknown و Unknown commit پیش از Retry، و Timeout پیش از Limit/Queue ارزیابی می‌شود.
- Child budget از Parent عبور نمی‌کند؛ Retry unsafe/unbounded و Recovery پیش از drain/reconciliation رد می‌شود.
- فقط budget/count/boolean مصنوعی پردازش شد؛ Operational read/run/receipt/readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ Document Numbering، Series، Void و Rollover مقصد ـ ۲۰۲۶-۰۹-۰۱

- دوازده بُعد Numbering در چهارده ماژول ۱۶۸ assignment و دوازده Stage نیز ۱۶۸ assignment ساخت.
- Series policy و Allocation receipt هرکدام بیست‌ودو، Void receipt هجده و Rollover receipt بیست فیلد دارد.
- شانزده Failure case تعداد ۲۲۴، بیست Gate تعداد ۲۸۰ و شش Role تعداد ۸۴ assignment ایجاد کرد.
- شمارهٔ انسانی surrogate نیست؛ Scope/Series version اجباری و Gap/Reservation/Abandonment بدون Void immutable قابل reuse نیست.
- Preview/Draft زودهنگام شماره نمی‌گیرد؛ Unknown commit شمارهٔ دوم نمی‌سازد و Offline range باید non-overlap و reconciled باشد.
- هیچ Number/Series/Gap/Identifier خوانده و هیچ Reserve/Commit/Void/Rollover اجرا نشد؛ Runtime/Approval/Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ Reference Evaluator مصنوعی Numbering ـ ۲۰۲۶-۰۹-۰۱

- Evaluator خالص Scope/Series/Fiscal، Replay/Unknown، Sequence/Fence، Draft/Reserve/Commit، Void/Offline/Rollover را پوشش داد.
- هفت مسیر مثبت و سیزده Mutation منفی، جمعاً ۲۰/۲۰، PASS و هجده Outcome متمایز ثبت شد.
- Replay پیش از Version و Unknown commit پیش از Allocation است؛ Draft شماره تخصیص نمی‌دهد.
- Expired reservation بدون Void رد و با Void به Gap ledger می‌رود؛ Offline boundary و Rollover باز fail-closed است.
- فقط state/version/number مصنوعی پردازش شد؛ Operational read/run/receipt/readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ File/Attachment Import-Export Integrity مقصد ـ ۲۰۲۶-۰۹-۰۱

- چهارده بُعد File integrity در چهارده ماژول ۱۹۶ assignment و دوازده Stage تعداد ۱۶۸ assignment ساخت.
- File manifest/Scan receipt هرکدام بیست‌ودو و Quarantine/Disposition receipt هرکدام بیست فیلد دارد.
- شانزده Failure case تعداد ۲۲۴، بیست‌ودو Gate تعداد ۳۰۸ و هفت Role تعداد ۹۸ assignment ایجاد کرد.
- Extension/MIME اعلامی trusted نیست؛ traversal/zip-slip/symlink/bomb/unbounded parser ممنوع است.
- Scanner error/unknown fail-closed، Quarantine غیرقابل دسترسی و derivative از original immutable جداست.
- هیچ File/Archive/Body خوانده و هیچ Scan/Parser/Download/Export اجرا نشد؛ Provider/Runtime/Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ Reference Validator مصنوعی فرادادهٔ فایل ـ ۲۰۲۶-۰۹-۰۱

- یک evaluator خالص و metadata-only با ترتیب Schema، Name/Path، Size، Digest، Media type، Archive safety، Scan/DLP/Quarantine، Download authorization، Derivative lineage، Export formula و Retention ساخته شد.
- پنج بردار حفاظتی/مثبت و چهارده mutation منفی، جمعاً ۱۹/۱۹، PASS و چهارده Outcome متمایز ثبت شد.
- traversal، اندازهٔ بیش‌ازحد، hash نامعتبر، MIME mismatch، zip-slip/bomb، scanner ناشناخته، دسترسی quarantine، مجوز/لینک منقضی، derivative هم‌digest، formula injection و retention کهنه fail-closed هستند.
- فقط metadata مصنوعی و ثابت پردازش شد؛ هیچ بدنه یا archive باز نشد و هیچ scanner/parser/download/export/disposition عملیاتی اجرا نشد.
- Operational receipt، Command/Pilot readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ Fiscal Period Close/Reopen/Adjustment Lock مقصد ـ ۲۰۲۶-۰۹-۰۱

- چهارده بُعد قفل و بستن دوره برای چهارده ماژول ۱۹۶ assignment و دوازده مرحله ۱۶۸ assignment ایجاد کرد.
- Policy تعداد ۲۴ و Close/Reopen/Adjustment receipt هرکدام ۲۲ فیلد دارد؛ هجده Failure تعداد ۲۵۲، بیست‌وچهار Gate تعداد ۳۳۶ و هفت Role تعداد ۹۸ assignment ساخت.
- همهٔ مسیرهای command/import/batch/integration/storage باید همان قفل دوره را اعمال کنند؛ تغییر Document date مجوز Posting نیست.
- Hard close پیش از reconciliation زیردفتر، موجودی، بانک، مالیات، حقوق، دارایی، accrual، FX، trial balance و control total ممنوع است.
- Reopen به reason/impact/scope/expiry، تفکیک وظایف و token یک‌بارمصرف نیاز دارد؛ Reclose وابستگی‌ها را دوباره reconcile و receiptها را supersede می‌کند.
- هیچ Period/Ledger/Document/Balance/Entry خوانده و هیچ Close/Reopen/Adjustment اجرا نشد؛ Runtime/Receipt/Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ Reference Evaluator مصنوعی دورهٔ مالی ـ ۲۰۲۶-۰۹-۰۱

- ترتیب Schema، Scope، Version، State، Lock-path coverage، Blocking unknown، Close dependency، Numbering rollover، Adjustment، Reopen، Reclose و Acceptance executable شد.
- پنج مسیر مثبت و هجده mutation منفی، جمعاً ۲۳/۲۳، PASS و نوزده Outcome متمایز ثبت شد.
- Lock bypass، unknown، subledger/control total/numbering، adjustment class/balance/reversal، reopen impact/SoD/token/break-glass و reclose rerun/lineage fail-closed هستند.
- فقط boolean/state/version ثابت و مصنوعی پردازش شد؛ هیچ Period/Ledger/Document/Balance/Entry خوانده و هیچ Close/Reopen/Adjustment/Posting اجرا نشد.
- Reference implementation یک، operational implementation/receipt/readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ Inventory Lot/Serial/Expiry/Costing/Valuation مقصد ـ ۲۰۲۶-۰۹-۰۱

- چهارده بُعد Inventory در چهارده ماژول ۱۹۶ assignment و دوازده Stage تعداد ۱۶۸ assignment ایجاد کرد.
- Inventory policy تعداد ۲۴ و Stock movement/Cost layer/Reconciliation receipt هرکدام ۲۲ فیلد دارد؛ هجده Failure تعداد ۲۵۲، بیست‌وچهار Gate تعداد ۳۳۶ و هشت Role تعداد ۱۱۲ assignment ساخت.
- Item/UOM/Warehouse/Owner/Lot/Serial scope صریح است؛ Expired/Recalled/Quarantined/Damaged stock قابل allocation نیست.
- Negative stock/Backdate/Late receipt/Unknown commit fail-closed و Cost method/version/currency/scale/rounding pin می‌شود.
- Cost layer lineage، Landed-cost reconciliation، Transfer-in-transit ownership، Count variance و Stock/GL control totals اجباری است.
- هیچ Item/Lot/Serial/Quantity/Cost/Value/Ledger خوانده و هیچ Stock/Costing action اجرا نشد؛ Runtime/Provider/Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ Reference Evaluator مصنوعی Inventory/Costing ـ ۲۰۲۶-۰۹-۰۱

- ترتیب Schema، Scope، Lot/Serial/Date، Version/Idempotency، Unknown commit، State/Quantity، Negative policy، Expiry، Cost layer، Landed cost، Transfer، Count، Revalue و Reconcile executable شد.
- هفت مسیر مثبت و بیست‌ویک mutation منفی، جمعاً ۲۸/۲۸، PASS و بیست‌ودو Outcome متمایز ثبت شد.
- Unknown commit، expired allocation، negative policy، cost-layer lineage/quantity، transfer ownership، count approval و Stock/Cost/GL reconciliation fail-closed هستند.
- فقط Boolean/Operation مصنوعی پردازش شد؛ هیچ Item/Lot/Serial/Quantity/Cost/Value/Ledger خوانده یا تغییر نکرد.
- Reference implementation یک، operational implementation/receipt/readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ Tax/Fiscalization/E-invoice Clearance مقصد ـ ۲۰۲۶-۰۹-۰۱

- چهارده بُعد Fiscalization در چهارده ماژول ۱۹۶ assignment و دوازده Stage تعداد ۱۶۸ assignment ایجاد کرد.
- Policy/Document manifest تعداد ۲۴/۲۴ و Submission/Correction receipt تعداد ۲۲/۲۲ فیلد دارد؛ هجده Failure تعداد ۲۵۲، بیست‌وچهار Gate تعداد ۳۳۶ و هشت Role تعداد ۱۱۲ assignment ساخت.
- Regime/Registration/Schema/Classification/Tax/Rounding/Number/UUID/Timestamp/Signature باید با policy جاری pin شود.
- Ack/Warning/Rejection/Unknown متفاوت‌اند؛ Unknown پیش از Retry reconcile و Retry باید Fiscal identity/Payload را حفظ کند.
- Contingency محدود و منقضی‌شونده است؛ Correction/Cancellation lineage اصلی و Provider/Fiscal-period state را حفظ می‌کند.
- قرارداد jurisdiction-neutral و غیرمشاورهٔ مالیاتی است؛ هیچ Taxpayer/Document/Value/Payload/Certificate خوانده یا ارسال نشد و Runtime/Readiness صفر ماند.

## موج ادامه ـ Reference Evaluator مصنوعی Tax Fiscalization ـ ۲۰۲۶-۰۹-۰۱

- ترتیب Schema، Regime/Registration، Schema/Identifier، Tax/Rounding، Fiscal identity، Signature/Certificate، Idempotency، Human/Machine parity، Unknown، Provider outcome، Contingency و Correction executable شد.
- هشت مسیر مثبت/حفاظتی و بیست‌ویک mutation منفی، جمعاً ۲۹/۲۹، PASS و نوزده Outcome متمایز ثبت شد.
- ACK پس از تمام gateهای محتوایی است و Control-total reconciliation می‌خواهد؛ Unknown، Contingency و Correction خروجی‌های fail-closed مستقل دارند.
- فقط Boolean/Provider-state مصنوعی پردازش شد؛ هیچ Tax data/Payload/Certificate/Provider خوانده یا ارسال نشد.
- Reference implementation یک، operational implementation/receipt/readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ Approval/Delegation/Escalation/SoD/Break-glass مقصد ـ ۲۰۲۶-۰۹-۰۱

- چهارده بُعد Approval governance در چهارده ماژول ۱۹۶ assignment و دوازده Stage تعداد ۱۶۸ assignment ایجاد کرد.
- Approval policy/Decision تعداد ۲۴/۲۴ و Request/Delegation receipt تعداد ۲۲/۲۲ فیلد دارد؛ هجده Failure تعداد ۲۵۲، بیست‌وچهار Gate تعداد ۳۳۶ و هشت Role تعداد ۱۱۲ assignment ساخت.
- Authorization جای Threshold/Quorum/Sequence/SoD نیست؛ Delegation به Action/Org/Amount/Risk/Time/Qualification scope نیاز دارد.
- Timeout/Reminder/Escalation هرگز Auto-decision نیست؛ تغییر request/policy/risk تصمیم را invalidate و reapproval را لازم می‌کند.
- Break-glass به Incident/Scope/Limit/Expiry/Post-review و Execution token به Single-use/Scope/Fence/Effect reconciliation نیاز دارد.
- هیچ User/Role/Request/Decision/Delegation/Token خوانده و هیچ Approval action اجرا نشد؛ Runtime/Provider/Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ Reference Evaluator مصنوعی Approval Governance ـ ۲۰۲۶-۰۹-۰۱

- ترتیب Schema، Request/Policy/Threshold، Qualification/SoD/Conflict، Delegation scope/expiry/revocation، No-auto-decision، Unknown، Escalation، Break-glass، Token/Effect و Quorum/Sequence executable شد.
- شش مسیر مثبت و بیست‌وسه mutation منفی، جمعاً ۲۹/۲۹، PASS و شانزده Outcome متمایز ثبت شد.
- Delegation expired/revoked، timeout auto-decision، conflict/SoD، break-glass ناقص و token غیر single-use/fenced fail-closed هستند.
- فقط Boolean/Action مصنوعی پردازش شد؛ هیچ Workflow/User/Role/Decision/Token/Effect خوانده یا اجرا نشد.
- Reference implementation یک، operational implementation/receipt/readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ Output/Print/PDF/Label/Barcode Rendering Integrity مقصد ـ ۲۰۲۶-۰۹-۰۱

- چهارده بُعد Output integrity در چهارده ماژول ۱۹۶ assignment و دوازده Stage تعداد ۱۶۸ assignment ایجاد کرد.
- Output policy/Render manifest تعداد ۲۴/۲۴، Print receipt تعداد ۲۲ و Barcode verification تعداد ۲۰ فیلد دارد؛ هجده Failure تعداد ۲۵۲، بیست‌وچهار Gate تعداد ۳۳۶ و هفت Role تعداد ۹۸ assignment ساخت.
- Template/Data/Renderer/Dependency/Font/Locale/Calendar/Timezone/Rounding باید pin شود؛ RTL/Bidi/embedding بخشی از parity فارسی است.
- Barcode/QR به machine decode و payload policy نیاز دارد؛ Preview/Copy/Reprint watermark و lineage و PDF digest/signature/archival policy می‌خواهد.
- Visual match به‌تنهایی Semantic/Machine-scan/Business Golden parity نیست و Unknown print delivery پیش از retry reconcile می‌شود.
- هیچ Template/Snapshot/Document/Output/Barcode/Receipt خوانده و هیچ Render/Print/Scan/Sign اجرا نشد؛ Runtime/Provider/Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ Reference Evaluator مصنوعی Output Rendering ـ ۲۰۲۶-۰۹-۰۱

- ترتیب Schema، Template/Data، Renderer، Font/RTL، Locale/Numeric، Layout/Page، Barcode/Scan، QR، Redaction، Copy/Lineage، PDF، Accessibility، Unknown و Delivery executable شد.
- شش مسیر مثبت و بیست‌ویک mutation منفی، جمعاً ۲۷/۲۷، PASS و هجده Outcome متمایز ثبت شد.
- Font/RTL، locale/rounding، layout/page، barcode decode، QR، redaction، reprint lineage، PDF signature و accessibility fail-closed هستند.
- ACK چاپ فقط پس از تمام gateهای محتوایی ارزیابی می‌شود و Unknown print delivery نتیجهٔ typed reconciliation دارد.
- فقط Boolean/State مصنوعی پردازش شد؛ هیچ Output ساخته، باز، چاپ، scan یا sign نشد و Runtime/Receipt/Readiness صفر ماند.

## موج ادامه ـ Privacy/Consent/Legal Basis/Data-subject Rights مقصد ـ ۲۰۲۶-۰۹-۰۱

- چهارده بُعد Privacy در چهارده ماژول ۱۹۶ assignment و دوازده Stage تعداد ۱۶۸ assignment ایجاد کرد.
- Privacy policy تعداد ۲۴، Consent receipt تعداد ۲۲، Rights receipt تعداد ۲۴ و Disposition receipt تعداد ۲۲ فیلد دارد؛ هجده Failure تعداد ۲۵۲، بیست‌وچهار Gate تعداد ۳۳۶ و هشت Role تعداد ۱۱۲ assignment ساخت.
- Authorization جای Purpose/Legal basis/Consent نیست؛ Consent باید granular/proven/withdrawable و Collection محدود به necessity/allowlist باشد.
- Rights به identity/representative verification، alias/downstream discovery و third-party redaction نیاز دارد؛ Erasure حق دورزدن legal hold نیست.
- قرارداد jurisdiction-neutral و غیرمشاورهٔ حقوقی است؛ هیچ PII/Sensitive data خوانده و هیچ Consent/Rights/Disposition/Sharing/Breach action اجرا نشد.
- Runtime/Provider/Legal approval/Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ Reference Evaluator مصنوعی Privacy Rights ـ ۲۰۲۶-۰۹-۰۱

- ترتیب Schema، Inventory/Subject، Purpose/Basis/Jurisdiction، Notice، Consent/Withdrawal، Minimization، Rights identity، Discovery، Redaction، Hold/Conflict، Sharing، Automated decision، Breach و Disposition executable شد.
- نه مسیر مثبت/حفاظتی و بیست‌ویک mutation منفی، جمعاً ۳۰/۳۰، PASS و بیست‌ودو Outcome متمایز ثبت شد.
- Withdrawal، identity mismatch، incomplete discovery، legal hold، unscoped sharing، automated decision بدون human review و disposition بدون retention proof fail-closed هستند.
- فقط Boolean/Action مصنوعی پردازش شد؛ هیچ PII یا دادهٔ حساس خوانده و هیچ Privacy action اجرا نشد.
- Reference implementation یک، operational implementation/receipt/readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ Integration/Webhook Authenticity, Replay و Dead-letter مقصد ـ ۲۰۲۶-۰۹-۰۱

- چهارده بُعد Integration در چهارده ماژول ۱۹۶ assignment و دوازده Stage تعداد ۱۶۸ assignment ایجاد کرد.
- Endpoint policy/Inbound receipt تعداد ۲۴/۲۴ و Outbound/Dead-letter receipt هرکدام ۲۲ فیلد دارد؛ هجده Failure تعداد ۲۵۲، بیست‌وچهار Gate تعداد ۳۳۶ و هفت Role تعداد ۹۸ assignment ساخت.
- Signature باید canonical request/digest/timestamp/nonce/audience را bind کند؛ key ناشناخته یا revoked و replay fail-closed است.
- Message ID با fingerprint متفاوت reuse نمی‌شود؛ Unknown delivery پیش از retry reconcile و Poison message قرنطینه می‌شود.
- Redrive به Scope/Authorization/Idempotency/Cap/Loop guard و reconciliation نیاز دارد؛ payload/secret در log عادی ذخیره نمی‌شود.
- هیچ Endpoint/Certificate/Key/Message/Payload/Dead-letter خوانده و هیچ Send/Receive/Ack/Retry/Redrive اجرا نشد؛ Runtime/Provider/Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## موج ادامه ـ Reference Evaluator مصنوعی پیام Integration ـ ۲۰۲۶-۰۹-۰۱

- ترتیب Schema، Transport، Signature/Key، Digest، Schema compatibility، Scope، Replay، Dedup، Ordering، Unknown، Payload، Delivery، Retry، DLQ و Redrive executable شد.
- هشت مسیر مثبت و بیست‌ویک mutation منفی، جمعاً ۲۹/۲۹، PASS و بیست‌وسه Outcome متمایز ثبت شد.
- Unknown delivery نتیجهٔ Reconciliation، retry بدون idempotency/budget رد، poison بدون quarantine رد و redrive بدون authorization/cap/loop guard رد می‌شود.
- فقط Boolean/State/Identifier مصنوعی پردازش شد؛ هیچ Endpoint/Key/Message/Payload/Broker خوانده و هیچ network I/O اجرا نشد.
- Reference implementation یک، operational implementation/receipt/readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت ماند.

## بسته خرید تا پرداخت و تطبیق سه‌طرفه — ۲۰۲۶-۰۹-۰۱

- قرارداد design-only برای ۱۴ بُعد P2P در ۱۴ ماژول ساخته شد: requisition/budget، نسخه و approval سفارش، receipt/service acceptance، invoice identity/duplicate، line matching، toleranceهای quantity/price/tax/freight، partial/over/under، return/debit-note، hold/release، payment eligibility و accrual/AP/GL reconciliation.
- evaluator خالص آن ۸ مسیر مثبت و ۲۳ مسیر منفی را اجرا کرد؛ ۳۱/۳۱ PASS و ۲۴ outcome متمایز ثبت شد.
- هیچ supplier/order/receipt/invoice/payment/ledger عملیاتی خوانده نشد، provider انتخاب نشد، mutation و اجرای command صفر و command/pilot readiness صفر باقی ماند.
## بسته فروش تا وصول، اعتبار و مطالبات — ۲۰۲۶-۰۹-۰۱

- قرارداد design-only O2C برای ۱۴ بُعد در ۱۴ ماژول ساخته شد: customer/order/pricing، credit exposure، allocation/delivery، invoice، return/credit/refund، cash custody/allocation، dispute/collection، aging/ECL، revenue recognition و AR/cash/revenue/GL reconciliation.
- evaluator خالص آن ۹ مسیر مثبت و ۱۹ مسیر منفی را اجرا کرد؛ ۲۸/۲۸ PASS و ۲۴ outcome متمایز ثبت شد.
- هیچ customer/order/shipment/invoice/cash/AR/GL عملیاتی خوانده نشد؛ provider، mutation، command و readiness همگی صفر ماندند.
## بسته نیروی کار، زمان و حقوق و دستمزد — ۲۰۲۶-۰۹-۰۱

- قرارداد design-only برای ۱۴ بُعد payroll در ۱۴ ماژول ساخته شد: employment/effective dating، attendance/leave، earnings/deductions/benefits/loans، gross-to-net، tax/insurance، retro/off-cycle، payslip/privacy، payment، termination و payroll-to-GL.
- evaluator خالص آن ۷ مسیر مثبت و ۱۹ مسیر منفی را اجرا کرد؛ ۲۶/۲۶ PASS و ۱۹ outcome متمایز ثبت شد.
- هیچ داده پرسنلی، حضور، حقوق، بانک یا دفتر عملیاتی خوانده نشد و provider/mutation/command/readiness صفر ماند.
## کپسول تحویل ادامه ۱۰ساعته — ۲۰۲۶-۰۹-۰۱

- Artifact و checkpoint تحویل، مسیر resume، graph hash/size، نتیجه suite رسمی، خانواده‌های دانش تکمیل‌شده و backlog نیازمند مجوز را یکجا تثبیت می‌کنند.
- audit مستقل برای JSON parse، checkpoint reachability، manifest freshness، exclusion صفر و نبود recovery seed اضافه شد.
- این کپسول انتقال دانش static/synthetic است؛ runtime parity، owner acceptance و provider selection همچنان اثبات‌نشده‌اند.
## بسته چرخه دارایی ثابت و استهلاک — ۲۰۲۶-۰۹-۰۱

- قرارداد design-only دارایی ثابت برای ۱۴ بُعد در ۱۴ ماژول ساخته شد: acquisition/CIP، componentization، book/method/life/residual، depreciation/proration، impairment/revaluation، transfer/disposal و register-to-GL.
- evaluator خالص آن ۷ مسیر مثبت و ۱۹ مسیر منفی را اجرا کرد؛ ۲۶/۲۶ PASS و ۲۰ outcome متمایز ثبت شد.
- هیچ asset/cost/depreciation/value/tax/ledger عملیاتی خوانده نشد و provider/mutation/command/readiness صفر ماند.
## دفتر پوشش و شکاف دامنه ERP مقصد — ۲۰۲۶-۰۹-۰۱

- ۵۰ Artifact قراردادی `varanegar_target_erp_*contract*.json` inventory شد و هر ۵۰ مورد PASS بود.
- این snapshot پیش از بسته Manufacturing هشت شکاف داشت؛ snapshot بلافاصله پس از Manufacturing هفت شکاف داشت و تنها P0 آن Project/Job Costing بود. snapshot canonical جدیدتر در بخش Project ثبت شده است.
- این شمارش پوشش design/synthetic است؛ accepted operational receipt و command/pilot readiness صفر هستند.
## ممیزی invariant سبد قراردادهای مقصد — ۲۰۲۶-۰۹-۰۱

- پس از بسته Manufacturing، هر ۵۲ قرارداد مقصد از نظر PASS، failed-check صفر، artifact id یکتا، safety صفر، runtime/provider/receipt/readiness صفر، manifest تازه و lower bound برابر ۱۴۰۴ ممیزی شد.
- نتیجه همان snapshot پس از Manufacturing برابر ۵۲/۵۲ PASS و صفر finding/duplicate/stale/nonzero-safety/nonzero-runtime/invalid-lower-bound بود.
- run-countهای بردار مصنوعی عمداً از run-count عملیاتی تفکیک شدند تا اجرای test vector به‌اشتباه ادعای runtime تلقی نشود.
## بسته ساخت، MRP، کارگاه و کیفیت — ۲۰۲۶-۰۹-۰۱

- قرارداد design-only برای ۱۴ بُعد ساخت در ۱۴ ماژول ساخته شد: BOM/recipe، routing/resource، MPS/MRP/pegging، order، material/backflush، labor/machine/output، genealogy/quality، WIP و costing/reconciliation.
- evaluator خالص آن ۷ مسیر مثبت و ۱۹ مسیر منفی را اجرا کرد؛ ۲۶/۲۶ PASS و ۱۹ outcome متمایز ثبت شد.
- شکاف Manufacturing از register بسته شد؛ inventory قراردادهای مقصد به ۵۲ و backlog به هفت دامنه (۱ P0، ۴ P1، ۲ P2) تغییر کرد.
## ممیزی سراسری checkpointها — ۲۰۲۶-۰۹-۰۱

- ممیز freshness به حالت `--all-checkpoints` مجهز شد تا علاوه بر chain رأس، checkpointهای orphan را نیز پوشش دهد.
- آخرین اجرای recursive تعداد ۲۵۰ checkpoint معتبر در ۷۶۹ JSON، صفر stale، صفر JSON نامعتبر، صفر exclusion و نبود recovery seed را ثبت کرد.
- تست تاریخ آینده `20991231` اثبات می‌کند traversal به نام تاریخ جاری وابسته نیست.

## بسته پروژه، بهایابی کار، درآمد و صورتحساب — ۲۰۲۶-۰۹-۰۱

- شکاف P0 پروژه در سطح طراحی بسته شد: دامنه و WBS، بودجه و تعهد، هزینه‌های مستقیم/غیرمستقیم، پیشرفت، صورتحساب، شناسایی درآمد، تغییر قرارداد و تطبیق زیر‌دفتر پروژه با GL پوشش یافت.
- ارزیاب خالص ۲۴ بردار ثابت (۶ مثبت و ۱۸ منفی) را بدون داده یا اجرای عملیاتی ارزیابی می‌کند.
- inventory canonical اکنون ۵۴ قرارداد PASS و backlog شش دامنه (۰ P0، ۴ P1، ۲ P2) است؛ runtime، provider، command و pilot همچنان اثبات‌نشده و صفرند.
