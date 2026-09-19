# تحویل ادامهٔ شناخت حرفه‌ای وارانگار

تاریخ وضعیت: ۲۰۲۶-۰۸-۳۱ ـ منطقهٔ زمانی Asia/Tehran

این فایل نقطهٔ تحویل قابل‌انتقال پروژهٔ شناخت وارانگار است. Task بعدی باید ادامهٔ مستقیم همین مسیر باشد، نه تحلیل دوباره از صفر.

## روش انتقال

فقط این فایل کافی نیست؛ کل پوشهٔ پروژه را با ساختار آن به سیستم مقصد منتقل کنید:

`G:\NeginAI`

در سیستم مقصد می‌توان مسیر ریشه را تغییر داد، اما ساختار نسبی `docs`، `artifacts`، `scripts` و `tests` باید حفظ شود. پوشهٔ `.venv` ممکن است روی سیستم دیگر قابل استفاده نباشد و در آن صورت باید محیط Python مطابق وابستگی‌های پروژه بازسازی شود. هیچ Credential، Connection String یا دادهٔ خام عملیاتی نباید هنگام انتقال اضافه شود.

## دستور قطعی برای Task بعدی

این Task ادامهٔ مستقیم شناخت وارانگار است. از صفر شروع نکن، تحلیل‌های بسته‌شده را بدون مشاهدهٔ Drift یا نقص شواهد تکرار نکن و اسناد موجود را مرجع قرار بده. کار فقط‌خواندنی، مستند، بازتولیدپذیر و پیوسته است. برای تصمیم‌های عادی منتظر پاسخ کاربر نمان، ولی هیچ مرز ایمنی یا نیازمند مجوز را فرض نکن.

ریشهٔ پروژه را از محل واقعی سیستم مقصد تشخیص بده. مسیر مبدأ هنگام تحویل `G:\NeginAI` بوده است.

ابتدا این فایل و سپس منابع مرجع زیر را بخوان. بعد وضعیت Hash، Checkpoint و تست را کنترل کن و دقیقاً از بخش «نقطهٔ ادامه» پیش برو.

## منابع مرجع اصلی

1. `docs/VARANEGAR_KNOWLEDGE_FA.md` ـ دانش تجمیعی وارانگار.
2. `docs/varanegar_reconstruction/DISCOVERY_LOG_FA.md` ـ تاریخچهٔ کشفیات.
3. `docs/varanegar_reconstruction/README_FA.md` ـ فهرست اسناد.
4. `docs/varanegar_reconstruction/VARANEGAR_15H_FINAL_HANDOFF_20260829_FA.md` ـ تحویل مرحلهٔ ۱۵ساعته.
5. `artifacts/varanegar_analysis/varanegar_15h_final_baseline_bundle_20260829.json` ـ Baseline مرحلهٔ قبل.
6. `artifacts/varanegar_analysis/varanegar_25h_final_baseline_bundle_20260829.json` ـ Bundle تجمیعی ۲۵ساعتهٔ پیش از بسته‌های آخر.
7. `artifacts/varanegar_analysis/varanegar_25h_final_test_result_20260829.json` ـ آخرین نتیجهٔ رسمی موجود.
8. `artifacts/varanegar_analysis/varanegar_24h_continuation_consolidated_audit_20260829.json` ـ ممیزی تاریخی پایه.
9. `artifacts/varanegar_analysis/varanegar_24h_continuation_consolidated_checkpoint_20260829.json` ـ Checkpoint ممیزی تاریخی.

## مرز حقیقت و سطح اطمینان

- ۸۴ ریسک ثبت‌شده و ۳۴۳ انتساب ریسک/نیاز همچنان پایهٔ معتبر است.
- Runtime parity، اجرای Golden/UAT، Owner approval، Command readiness و Pilot readiness همگی صفر هستند.
- `PASS` در Artifact یا تست آفلاین فقط انسجام طراحی و شواهد ایستا را ثابت می‌کند؛ رفتار Runtime یا آمادگی عملیاتی را ثابت نمی‌کند.
- Lower bound طراحی پس از موج‌های اخیر ۱۴۰۴ است و با بسته‌های قراردادی جدید افزایش داده نشده است.
- هیچ ریسک تازه‌ای ساخته نشده؛ یافته‌ها به ریسک‌های موجود متصل شده‌اند.
- هر ادعا باید به یکی از سطوح «تأییدشده»، «استنباط قوی»، «فرضیه» یا «ردشده» منتسب شود.

## وضعیت فنی در لحظهٔ تحویل

- تعداد JSONهای تحلیلی: ۶۴۷.
- JSON نامعتبر: صفر.
- Checkpointهای سطح بالای موجود: ۱۸۳.
- Checkpoint با `validation != PASS`: صفر.
- آخرین نتیجهٔ رسمی موجود: ۳۱۴ فایل تست، ۱۵۳۶ تست پاس، یک Warning و bootstrap exclusion صفر.
- آزمون متمرکز دو بستهٔ آخر در همین تحویل دوباره اجرا شد: ۱۸ تست پاس و یک Warning در هر اجرای ۹تستی.
- بازتولید Artifact و Checkpoint هر دو بستهٔ آخر انجام شد و هر چهار JSON در وضعیت `PASS` هستند.
- ممیزی تجمیعی تاریخی و Checkpoint آن پس از تغییر فهرست رسمی دوباره ساخته و `PASS` شدند.
- زنجیرهٔ کامل Base 203، Audit/Checkpoint و Post 126 پس از Runner رسمی دوباره settle شده است.
- Freshness بازگشتی از ۱۸۳ Checkpoint روی ۵۰۳ Node یکتای JSON کنترل شد و stale edge برابر صفر است.
- هیچ فرایند Python مربوط به `G:\NeginAI` در پس‌زمینه باقی نمانده است.
- پروژه Git repository نیست؛ هنگام انتقال باید کل پوشه و همهٔ فایل‌های آن حفظ شود.

## دانش و بسته‌های تکمیل‌شده در موج اخیر

### Cross-Lane closure و intake

- ۲۹ Packet و ۲۰۳ Case در پنج Lane از P0 تا P4.
- ۲۰ Packet دارای Candidate و ۹ Packet explicit-none.
- ۲۴۶ جفت مقایسه شامل ۷۸ Failure و ۱۶۸ Control.
- مسیرهای تصمیم: ۹ Alias/New Action، ۱۲ Semantic، پنج Effect+Result و سه Export+Result.
- ۲۹۰ Receipt requirement و ۱۵۰ Gate assignment.
- ۱۳ نوع نقش، ۵۸ Packet assignment، ۴۰۶ Case assignment و ۵۸۰ Receipt-slot assignment.
- مالک نام‌دار، Receipt پذیرفته‌شده، Semantic closure، Result parity و Readiness همگی صفر.

### اصلاح Multi-Class receipt

- Receipt classifier از مدل تک‌کلاسه به class-set و union gate اصلاح شد.
- ۱۴ Slot چندکلاسه و ۲۷ Slot زیر CG-05 وجود دارد.
- پنج Receipt مرکب P3 اکنون هم‌زمان به `CG-02/CG-03/CG-05/CG-04` متصل‌اند.

### Activation design

- P0: هفت Packet، ۴۹ Case، ۷۰ Receipt، ۱۴ Role و ۳۵ Gate assignment.
- P1 تا P4: چهار Lane، ۲۲ Packet، ۱۵۴ Case، ۲۲۰ Receipt، ۴۴ Role و ۱۱۵ Gate assignment.
- هشت Packet P3/P4 به CG-05 وابسته‌اند.
- همهٔ Activationها طراحی‌شده ولی اجرا‌نشده و فاقد مجوز عملیاتی هستند.

### ماتریس CG-05 برای P3/P4

- هشت Packet، ۵۶ Case و ۲۰ بُعد parity.
- ۱۶۰ Dimension assignment و ۲۷ CG-05 Receipt assignment.
- File/Render/Per-item comparison هنوز closure ندارد.
- Result parity صریح، Owner approval، Execution و Readiness صفر است.

## دو بستهٔ آخر تحویل

### قرارداد Frozen Fixture/Output

سند:
`docs/varanegar_reconstruction/P3_P4_FROZEN_FIXTURE_OUTPUT_MANIFEST_CONTRACT_20260829_FA.md`

Artifact و Checkpoint:

- `artifacts/varanegar_analysis/varanegar_p3_p4_frozen_fixture_output_manifest_contract_20260829.json`
- `artifacts/varanegar_analysis/varanegar_p3_p4_frozen_fixture_output_manifest_checkpoint_20260829.json`

Builder و تست:

- `scripts/windows/build_varanegar_p3_p4_frozen_fixture_output_manifest_contract_20260829.py`
- `scripts/windows/build_varanegar_p3_p4_frozen_fixture_output_manifest_checkpoint_20260829.py`
- `tests/test_varanegar_p3_p4_frozen_fixture_output_manifest_contract.py`
- `tests/test_varanegar_p3_p4_frozen_fixture_output_manifest_checkpoint.py`

وضعیت:

- هشت قرارداد، شامل پنج فرمان P3 و سه فرمان P4.
- ۵۶ Golden/UAT Case؛ هفت Case برای هر فرمان.
- سه schema شانزده‌فیلدی برای Fixture، Output و Comparison.
- ۵۱۲ Field assignment، تعداد ۱۶ سمت Capture و ۵۶ Acquisition assignment.
- ۱۶۰ Parity-dimension assignment و ۲۷ CG-05 Receipt assignment.
- Capture واقعی، مقدار خام تجاری، Comparison، Acceptance، Execution و Readiness صفر.

### Playbook تشخیص اختلاف Result parity

سند:
`docs/varanegar_reconstruction/P3_P4_RESULT_PARITY_MISMATCH_DIAGNOSTIC_PLAYBOOK_20260829_FA.md`

Artifact و Checkpoint:

- `artifacts/varanegar_analysis/varanegar_p3_p4_result_parity_mismatch_diagnostic_playbook_20260829.json`
- `artifacts/varanegar_analysis/varanegar_p3_p4_result_parity_mismatch_diagnostic_checkpoint_20260829.json`

Builder و تست:

- `scripts/windows/build_varanegar_p3_p4_result_parity_mismatch_diagnostic_playbook_20260829.py`
- `scripts/windows/build_varanegar_p3_p4_result_parity_mismatch_diagnostic_checkpoint_20260829.py`
- `tests/test_varanegar_p3_p4_result_parity_mismatch_diagnostic_playbook.py`
- `tests/test_varanegar_p3_p4_result_parity_mismatch_diagnostic_checkpoint.py`

وضعیت:

- ده Playbook و حداقل ۱۰۰ Step.
- ۷۲ Packet assignment، تعداد ۵۰۴ Case cross-link و ۳۴ Parity-dimension link.
- چهار Outcome تشخیصی:
  - `MATCH_CONFIRMED_BY_ACCEPTED_HASH_ONLY_EVIDENCE`
  - `EXPLAINED_OWNER_APPROVED_VERSIONED_EXCEPTION`
  - `INVALID_OR_STALE_EVIDENCE_RECOLLECTION_REQUIRED`
  - `UNEXPLAINED_DIFFERENCE_BLOCKS_CG05`
- وضعیت فعلی `DESIGNED_NOT_RUN_NO_CAPTURE_AUTHORIZATION` است.
- Diagnostic run، Repair، Replay، Recapture، Owner resolution، Parity، Execution و Readiness صفر.

### ماتریس داوری Golden/UAT و Promotion Guard

سند:
`docs/varanegar_reconstruction/P3_P4_GOLDEN_UAT_RESULT_ADJUDICATION_PROMOTION_GUARD_20260829_FA.md`

Artifact و Checkpoint:

- `artifacts/varanegar_analysis/varanegar_p3_p4_golden_uat_result_adjudication_promotion_guard_20260829.json`
- `artifacts/varanegar_analysis/varanegar_p3_p4_golden_uat_result_adjudication_promotion_guard_checkpoint_20260829.json`

Builder و تست:

- `scripts/windows/build_varanegar_p3_p4_golden_uat_result_adjudication_promotion_guard_20260829.py`
- `scripts/windows/build_varanegar_p3_p4_golden_uat_result_adjudication_promotion_guard_checkpoint_20260829.py`
- `tests/test_varanegar_p3_p4_golden_uat_result_adjudication_promotion_guard.py`
- `tests/test_varanegar_p3_p4_golden_uat_result_adjudication_promotion_guard_checkpoint.py`

وضعیت:

- هشت Packet/۵۶ Case و چهار Outcome به ۳۲ Route و ۲۲۴ Case assignment متصل شده‌اند.
- دوازده Guard و ۹۶ Guard assignment تعریف شده است.
- فقط Match مبتنی بر hash واجد ورود به بازبینی CG-05 است؛ Closure خودکار برای هیچ Outcome وجود ندارد.
- Adjudication، Exception acceptance، Recollection، CG-05 closure، UAT و Readiness همگی صفر است.

### قرارداد Hash-Only Comparison Adapter برای ERP مقصد

سند:
`docs/varanegar_reconstruction/TARGET_ERP_HASH_ONLY_COMPARISON_ADAPTER_CONTRACT_20260829_FA.md`

Artifact و Checkpoint:

- `artifacts/varanegar_analysis/varanegar_target_erp_hash_only_comparison_adapter_contract_20260829.json`
- `artifacts/varanegar_analysis/varanegar_target_erp_hash_only_comparison_adapter_checkpoint_20260829.json`

Builder و تست:

- `scripts/windows/build_varanegar_target_erp_hash_only_comparison_adapter_contract_20260829.py`
- `scripts/windows/build_varanegar_target_erp_hash_only_comparison_adapter_checkpoint_20260829.py`
- `tests/test_varanegar_target_erp_hash_only_comparison_adapter_contract.py`
- `tests/test_varanegar_target_erp_hash_only_comparison_adapter_checkpoint.py`

وضعیت:

- هشت Profile/۵۶ Case با Input و Receipt هجده‌فیلدی، دوازده Stage، شانزده Error code و شش Typed status.
- ۱۶۰ Dimension assignment، تعداد ۲۷ Receipt assignment و ۹۶ Promotion Guard assignment.
- SHA-256 domain-separated، Idempotency پنج‌جزئی و منع کامل Persist دادهٔ خام.
- Implementation، Request، Run، Receipt، Parity و Readiness همگی صفر است.

### بردارهای استاندارد و قرارداد اصالت Receipt مقایسه

سند:
`docs/varanegar_reconstruction/TARGET_ERP_COMPARISON_ADAPTER_TEST_VECTOR_RECEIPT_VERIFICATION_20260829_FA.md`

Artifact و Checkpoint:

- `artifacts/varanegar_analysis/varanegar_target_erp_comparison_adapter_test_vector_receipt_verification_contract_20260829.json`
- `artifacts/varanegar_analysis/varanegar_target_erp_comparison_adapter_test_vector_receipt_verification_checkpoint_20260829.json`

Builder و تست:

- `scripts/windows/build_varanegar_target_erp_comparison_adapter_test_vector_receipt_verification_contract_20260829.py`
- `scripts/windows/build_varanegar_target_erp_comparison_adapter_test_vector_receipt_verification_checkpoint_20260829.py`
- `tests/test_varanegar_target_erp_comparison_adapter_test_vector_receipt_verification_contract.py`
- `tests/test_varanegar_target_erp_comparison_adapter_test_vector_receipt_verification_checkpoint.py`

وضعیت:

- دوازده بردار canonical مثبت و شانزده بردار خطای منفی برای هر هشت Profile؛ جمعاً ۲۸ بردار و ۲۲۴ انتساب.
- دوازده digest مورد انتظار و taxonomy خطای منفی دقیقاً هم‌تراز با شانزده Error code قرارداد Adapter است.
- شانزده فیلد اصالت، هشت Verification outcome، شش وضعیت چرخهٔ کلید، هشت قاعدهٔ rotation و ده مرحلهٔ verification تعریف شده است.
- الگوریتم امضا و key provider انتخاب نشده؛ هیچ کلید، signature bytes، مقدار تجاری، Signing یا Verification واقعی ثبت نشده است.
- اصالت Receipt جدا از Result parity است؛ حتی `AUTHENTIC_CURRENT` نیز Closure، UAT یا Readiness خودکار ایجاد نمی‌کند.

## ادغام انجام‌شده

نام بسته‌های اخیر در این نقاط ثبت شده است:

- `scripts/windows/build_varanegar_24h_continuation_consolidated_audit_20260829.py` در مجموعهٔ `EXCLUDE`.
- `scripts/windows/build_varanegar_25h_final_bundle_20260829.py` در `CONTINUATION_CHECKPOINTS`.
- `scripts/windows/build_varanegar_24h_continuation_wave01_bundle_20260829.py` در `POST_WAVE01_CHECKPOINTS`.
- `docs/VARANEGAR_KNOWLEDGE_FA.md`.
- `docs/varanegar_reconstruction/DISCOVERY_LOG_FA.md`.
- `docs/varanegar_reconstruction/README_FA.md`.

هدف این ادغام آن است که شمارنده‌های تاریخی Base تغییر نکنند و بسته‌های جدید به‌عنوان ادامهٔ post-chain محاسبه شوند.

## نقطهٔ دقیق ادامه در سیستم مقصد

### گام اول ـ کنترل انتقال

1. وجود همهٔ مسیرهای مرجع را کنترل کن.
2. همهٔ JSONها را parse کن؛ تعداد نامعتبر باید صفر باشد.
3. Hash و اندازهٔ `source_manifest` و `manifest` را به‌صورت بازگشتی کنترل کن.
4. اگر فقط مسیر ریشه تغییر کرده، manifestهای نسبی نباید دستکاری شوند.

### گام دوم ـ settle کامل زنجیره

ترتیب تثبیت باید dependency-aware باشد:

1. بازسازی گراف پایهٔ ۲۰۳ Artifact با Kahn topological ordering.
2. در انتخاب Node آماده، ابتدا Nodeهای عادی و سپس بسته‌های ویژه با اولویت زیر:
   1. `varanegar_15h_final_baseline_bundle_20260829.json`
   2. `varanegar_25h_opening_gap_map_20260829.json`
   3. `varanegar_25h_final_baseline_bundle_20260829.json`
   4. `varanegar_24h_continuation_wave01_bundle_20260829.json`
3. Dependencyها از `source_manifest` و `manifest` خوانده شوند.
4. سپس ممیزی تجمیعی و Checkpoint آن ساخته شود.
5. گراف post با ۱۲۶ Node بازسازی شود.
6. Runner رسمی اجرا شود:

   `.\.venv\Scripts\python.exe scripts/windows/run_varanegar_25h_final_tests.py --output artifacts/varanegar_analysis/varanegar_25h_final_test_result_20260829.json`

7. چون برخی تست‌های تاریخی Artifact می‌سازند، پس از Runner رسمی یک بار دیگر Base 203، ممیزی/Checkpoint و Post 126 ساخته شود.
8. Freshness بازگشتی نهایی کنترل شود.

انتظار پس از settle کامل ـ فقط انتظار و نه نتیجهٔ تأییدشدهٔ فعلی:

- ۱۸۳ Checkpoint سطح بالا، همگی PASS و stale صفر.
- ۳۱۴ فایل تست و ۱۵۳۶ تست پاس با یک Warning شناخته‌شده و bootstrap exclusion صفر.
- Base graph برابر ۲۰۳ و Post graph برابر ۱۲۶.
- JSON نامعتبر صفر.
- Risk برابر ۸۴ و Trace assignment برابر ۳۴۳.
- Runtime/Command/Pilot readiness همچنان صفر.

اگر شمارنده‌ها متفاوت شد، نتیجه را جعل یا به عدد مورد انتظار مجبور نکن؛ اختلاف را ریشه‌یابی و در Discovery Log ثبت کن.

### گام سوم ـ کار دانشی بعدی

ماتریس adjudication، قرارداد Hash-Only Comparison Adapter و بستهٔ بردار/اصالت Receipt کامل شده‌اند. Adapter هشت Profile، schema ورودی/Receipt هجده‌فیلدی، دوازده Stage، شانزده Error و Idempotency پنج‌جزئی دارد؛ بستهٔ بعدی نیز ۲۸ بردار و قرارداد verification بدون کلید واقعی دارد.

بستهٔ بعدی این است:

`بستهٔ Offline Synthetic Conformance Harness و Algorithm/Key-Provider Decision Record برای Comparison Adapter`

این بسته باید اجرای کاملاً محلی بردارهای مصنوعی را از رفتار ERP واقعی جدا کند، نتیجهٔ conformance را با hash و taxonomy خطای تایپ‌شده ثبت کند و Decision Record گزینه‌های الگوریتم/Provider را بدون انتخاب امنیتی زودهنگام بسازد؛ هیچ Key واقعی، امضا، Capture، اتصال یا اجرای عملیاتی مجاز نیست.

## قرارداد ثبت هر کشف مادی

هر کشف تازه باید هم‌زمان داشته باشد:

1. Artifact ماشین‌خوان.
2. Extractor یا Builder بازتولیدپذیر.
3. مستند فارسی.
4. تست تازه.
5. Hash منابع.
6. سطح اطمینان.
7. محدودیت و موارد اثبات‌نشده.
8. اتصال به یکی از ۸۴ ریسک موجود یا دلیل مستند برای Risk جدید.
9. اثر بر معماری ERP مقصد.
10. Checkpoint قابل زنجیره‌شدن.

## قواعد ایمنی غیرقابل‌تغییر

- هیچ فرم وارانگار را باز یا اجرا نکن.
- هیچ Stored Procedure عملیاتی را اجرا نکن.
- هیچ `INSERT`، `UPDATE`، `DELETE`، `MERGE`، DDL یا Command تغییردهنده اجرا نکن.
- به Database زنده یا داده‌های وارانگار/NGT متصل نشو و چیزی را تغییر نده.
- دسترسی Write نساز.
- در این ادامه به Clone هم متصل نشو مگر اینکه Task بعدی مجوز و نیاز روشن داشته باشد و ابتدا READ_ONLY و deny-write بودن آن مستقل اثبات شود.
- Assemblyها را Load، Import، runtime-reflect یا Execute نکن؛ فقط Metadata/IL ایستا.
- Credential، Connection String، PII، متن خام Rule و مقدار تجاری حساس را Persist نکن.
- UAT عملیاتی فقط با محیط ایزوله و اجازهٔ صریح کاربر ممکن است.
- تغییر فقط در اسناد، Extractorها، Builderها، Artifactهای تحلیلی و تست‌های شناخت وارانگار مجاز است.
- وجود فایل، تست PASS یا شباهت نام‌ها مجوز Promotion، Equivalence یا Runtime readiness نیست.

## فرمان آزمون متمرکز دو بستهٔ آخر

در PowerShell:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
.\.venv\Scripts\python.exe -m pytest -q `
  tests/test_varanegar_target_erp_hash_only_comparison_adapter_contract.py `
  tests/test_varanegar_target_erp_hash_only_comparison_adapter_checkpoint.py `
  tests/test_varanegar_target_erp_comparison_adapter_test_vector_receipt_verification_contract.py `
  tests/test_varanegar_target_erp_comparison_adapter_test_vector_receipt_verification_checkpoint.py
```

آخرین اجرای متمرکز هر بسته: `9 passed, 1 warning`. آخرین اجرای رسمی: `1536 passed, 1 warning` روی ۳۱۴ فایل.

## متن کوتاه آماده برای شروع Task جدید

```text
این Task ادامهٔ مستقیم پروژهٔ شناخت وارانگار است و نباید از صفر آغاز شود.
کل پروژه را منتقل کرده‌ام. ابتدا فایل VARANEGAR_CONTINUATION_HANDOFF_20260831_FA.md را کامل بخوان و مسیر ریشهٔ فعلی پروژه را تشخیص بده. سپس Knowledge، Discovery Log، README و Artifactهای معرفی‌شده در فایل تحویل را بررسی کن.

قواعد ایمنی فایل تحویل قطعی است: هیچ فرم یا Stored Procedure عملیاتی اجرا نکن، به سامانه یا DB زنده متصل نشو، هیچ Write یا mutation نساز، Assemblyها را Load/Execute نکن و هیچ Credential/PII/raw business value ذخیره نکن.

ابتدا انتقال را کنترل کن و نتیجهٔ ۳۱۴/۱۵۳۶، تعداد ۱۸۳ Checkpoint و stale صفر را تأیید کن. سپس بدون انتظار برای تصمیم‌های عادی، بستهٔ Offline Synthetic Conformance Harness و Algorithm/Key-Provider Decision Record را با Artifact + Builder + Doc + Tests + Checkpoint بساز؛ فقط دادهٔ مصنوعی و metadata طراحی مجاز است. Runtime parity و readiness را فقط با شاهد واقعی و مجاز ارتقا بده؛ در غیر این صورت صفر نگه دار.
```

## نتیجهٔ تحویل

دانش کسب‌شده فقط در حافظهٔ گفتگو نیست؛ در اسناد فارسی، Artifactهای JSON، Builderهای بازتولیدپذیر، تست‌ها و Checkpointها داخل همین پروژه ثبت شده است. این فایل مرز میان وضعیت تأییدشدهٔ فعلی، نتیجهٔ مورد انتظار پس از settle و کار بعدی را صریح نگه می‌دارد.
