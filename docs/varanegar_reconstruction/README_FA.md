# دفتر دانش زنده بازسازی وارانگار

این پوشه مرجع ماندگار شناختی است که برای بازسازی وارانگار در NeginAI به دست
می‌آید. هدف این است که هر تحلیل بعدی روی شواهد قبلی ساخته شود و هیچ رابطه یا
قاعده مهمی فقط در متن گفت‌وگو باقی نماند.

## ساختار مرجع

- `DISCOVERY_LOG_FA.md`: فهرست زمان‌دار تمام کشفیات و تصمیم‌های بعدی.
- `domains/`: قرارداد مستند هر دامنه اطلاعات پایه یا عملیاتی.
- `../../artifacts/varanegar_analysis/domains/`: شواهد خام و ماشین‌خوان JSON.
- `../../scripts/sql/`: استخراج‌کننده‌های تکرارپذیر و فقط‌خواندنی.
- `../VARANEGAR_KNOWLEDGE_FA.md`: دانش‌نامه معنایی و چرخه‌های عملیاتی موجود.
- `FOUR_HOUR_ANALYSIS_20260826_FA.md`: خط مبنای یکپارچه، معماری، ترتیب ساخت و برآورد.
- `THREE_MONTH_OPERATIONAL_ACTIVITY_20260826_FA.md`: خط مبنای حجم و تنوع فعالیت سه ماه تجاری.
- `RECONSTRUCTION_READINESS_MATRIX_20260826_FA.md`: آمادگی هر دامنه، Gate بعدی و Definition of Done.
- `CHECKPOINT_20260826_FA.md`: نقطه ادامه، فرمان کنترل و کار بعدی دقیق.
- `CHECKPOINT_20260828_RULE_REPLICATION_FA.md`: نقطه ادامهٔ Hash‌شده برای قرارداد صدور سند، انتقال/دریافت قواعد، ریسک و Traceability.
- `CHECKPOINT_20260829_AUTHORIZATION_FA.md`: Checkpoint ۲۸‌منبعی/۷۰-Gate مجوز و Owner scope
- `NGT_OWNER_SCOPE_RUNTIME_AND_EFFECTIVE_BOUNDARY_20260829_FA.md`: زنجیره Header، Repository خام/Owner-aware، Scope گروه و Snapshot مؤثر NGT
  NGT، شکاف Endpoint، Admin short-circuit، ریسک و Traceability.
- `NGT_OPERATION_DATE_AND_REPLICATION_SELECTOR_BOUNDARY_20260829_FA.md`: تفکیک
  زمان رویداد Return، انتخاب‌گر چهارحالته تاریخ Replication و `GNR.tblOprDate`؛
  مقایسه Business IL و SQL، Guard مقدار خالی، Default سال ۱۹۰۰ و ریسک `R-060`.
- `../../artifacts/varanegar_analysis/varanegar_operation_date_checkpoint_20260829.json`:
  Checkpoint مستقل ۱۷‌منبعی/۳۶-Gate برای مرز تاریخ، ریسک و Traceability.
- `UI_RUNTIME_INVENTORY_20260827_FA.md`: Snapshot امن فرم‌های واقعی و قرارداد UI↔SQL.
- `DOTNET_RUNTIME_ARCHITECTURE_20260827_FA.md`: معماری ماژول‌ها، منوی مجوزمحور و Call graph چهار فرم فعال.
- `UI_CAPABILITY_MATRIX_20260827_FA.md`: Permission، Feature، Context، Data partition و Guard هر Command فعال.
- `FORM_CATALOG_20260827_FA.md`: کاتالوگ ۴۴۵ فرم Runtime، شکل صفحه و نگاشت اولیه دامنه‌ای.
- `WORKFLOW_CATALOG_20260827_FA.md`: قرارداد ۲۰ Workflow/Tracking و ۱۰۱ Method فرمانی.
- `REPORT_CATALOG_20260827_FA.md`: کاتالوگ ۲۰ Report/Analysis، Query source، فیلتر و مرز Print/Export.
- `MENU_ROUTE_CROSSWALK_20260827_FA.md`: اتصال ۸۳۶ MenuConfig به FormInfo/AccessNode و چهار فرم فعال.
- `AUTHORIZATION_ROUTE_MATRIX_20260827_FA.md`: ۴۰ Node مجوز چهار Route فعال، پوشش ناشناس Allow/Deny و قرارداد نقش مقصد.
- `domains/16_AUTHORIZATION_LEGACY_AND_NGT_FA.md`: قرارداد deny-wins Legacy و
  Guard مستقر NGT؛ تفکیک overload سه‌پارامتری، فیلتر `Grant=1` و Materialization
  مستقیم Catalog به Permission اتمی.
- `AUTHORIZATION_RISK_DELTA_20260829_FA.md`: ریسک‌های `R-057/R-058` برای ۶۰
  شکاف اعلان Endpoint، ۳۸ mutation، سه mismatch کاتالوگ و Admin short-circuit،
  با Caveat صریح Reachability/Incident.
- `RUNTIME_DRIFT_BASELINE_20260827_FA.md`: شناسنامه معنایی DLL/Menu/Workflow/SQL/Permission برای تشخیص تغییر روزهای بعد.
- `ACTIVE_PAGE_CONTRACTS_20260827_FA.md`: فیلد، فیلتر، Validation و مرز Command چهار صفحه فعال.
- `STATE_MACHINE_CATALOG_20260827_FA.md`: ۲۲ وضعیت و Edgeهای مجاز/مشاهده‌شده چک دریافتی، پرداختنی و توزیع.
- `COMMAND_SIDE_EFFECTS_20260827_FA.md`: Trace فرمان تا Handler/SQL/Ledger، Transaction evidence و Idempotency gap.
- `GOLDEN_COMMAND_CASES_20260827_FA.md`: ۷۷ Case موفق/منفی/Retry/Fault/Reconciliation برای ساخت امن Commandهای مقصد.
- `REPORT_EXECUTION_CONTRACTS_20260827_FA.md`: تفکیک Read/Preview/Export/Print-completed و اصلاح Classification فرم Statement.
- `TARGET_ERP_BLUEPRINT_20260827_FA.md`: ۱۴ مرز مالکیت، Command envelope، هفت فاز Gateدار و Definition of Done مقصد.
- `NIGHT_EVIDENCE_BUNDLE_20260827_FA.md`: Manifest یکپارچه Hash/Link/Safety همه خروجی‌های Runtime و طراحی مقصد.
- `MIGRATION_CONTRACT_20260827_FA.md`: قرارداد Snapshot/Crosswalk/Quarantine/Reconciliation و ترتیب ۱۲ Slice مهاجرت.
- `ROLE_AND_SOD_CONTRACT_20260827_FA.md`: ۴۵ Capability، ۱۵ Role template بدون هویت و ۱۰ تضاد وظیفه مقصد.
- `DATA_ENTRY_IL_CATALOG_20260827_FA.md`: Call graph و Command/Validator ۱۴۱ فرم Data-entry/Master-detail.
- `HIGH_IMPACT_CALL_GRAPH_20260827_FA.md`: Trace دوازده فرم پرتراکم تا ۸۷ Business و ۴۳ DataAccess type.
- `ORCHESTRATOR_COMMAND_CONTRACTS_20260827_FA.md`: ده Command مقصد برای Order/Return/SupplierInvoice/StockVoucher.
- `ORCHESTRATOR_GOLDEN_CASES_20260827_FA.md`: ۱۵۴ Case مصنوعی Auth/Scope/Retry/Fault/Reconciliation برای ده Command.
- `ALL_FORM_CALL_CONTRACTS_20260827_FA.md`: پوشش Compact تمام ۴۴۲ فرم High-confidence و Coupling ماژولی آن‌ها.
- `FORM_EVIDENCE_GAPS_20260827_FA.md`: Route/Domain/Call/Permission gap همه ۴۴۵ Candidate با هفت اولویت بالا.
- `PRIORITY_FORM_GAP_RESOLUTION_20260827_FA.md`: Route ثابت، Parent constructor، DataLayer و اسکن ۶۲ فایل .NET؛ چهار Child تأیید و سه Root حل‌نشده.
- `DEPLOYMENT_ROOT_REFERENCE_SCAN_20260827_FA.md`: اسکن ۸۵۳ فایل Deployment؛ سه Root فقط در اسمبلی فعال/کپی disable خود دیده شدند و reference بیرونی صفر بود.
- `UNRESOLVED_ROOT_CLOSURE_CONTRACT_20260827_FA.md`: تفکیک سه Root، توقف اسکن تکراری و قرارداد Telemetry/Owner evidence بدون هویت برای بستن هرکدام.
- `BANK_RECONCILIATION_SOURCE_MODEL_20260827_FA.md`: Aggregate مغایرت بانکی، ۱۵ Object، لینک چندنوعی ReconcileItem و مرز امن Import/Match/Confirm.
- `BANK_RECONCILIATION_COMMAND_GUARDS_20260827_FA.md`: Alias مجوز، تاریخ عملیات، Validation و Transaction مرزهای Import/Delete مغایرت بانکی.
- `BANK_RECONCILIATION_PERMISSION_CATALOG_20260827_FA.md`: دو Alias/هفت Child واقعی، شمارش aggregate حق و Capabilityهای مجزای مقصد بدون هویت.
- `BANK_RECONCILIATION_DELETE_SEMANTICS_20260827_FA.md`: تفکیک Unmatch، Discard، Cancel و Reversal؛ Cancel Legacy مستقل هنوز اثبات نشده.
- `BANK_RECONCILIATION_TRANSACTION_BOUNDARY_20260827_FA.md`: Nesting تأیید، شمارنده/Connection static Legacy و الزام UnitOfWork scoped مقصد.
- `BANK_RECONCILIATION_CARDEX_SQL_BOUNDARY_20260827_FA.md`: روال و امضای دقیق ثبت کاردکس، ۹ وابستگی کاتالوگی و قرارداد typed/atomic مقصد.
- `BANK_RECONCILIATION_MATCHING_BOUNDARY_20260827_FA.md`: شش نگاشت نوع‌دار Match، Eventهای دارای persistence فوری، Read model و قرارداد command/transaction مقصد.
- `BANK_RECONCILIATION_PROFILE_STATE_BOUNDARY_20260827_FA.md`: projection واقعی Profile، سه Parser dispatch، markerهای تأیید و اصلاح Root نام‌گذاری‌شدهٔ گمراه‌کننده.
- `BANK_RECONCILIATION_ROLE_UAT_CONTRACT_20260827_FA.md`: شش Role template، هفت Capability مستقل از جمله Reversal و ۱۰۰ Case UAT مصنوعی بدون هویت یا ادعای اجرای واقعی.
- `BANK_RECONCILIATION_SUMMARY_UI_BOUNDARY_20260827_FA.md`: نگاشت یازده خروجی Summary به Label و Presentation علامت/رنگ بدون ادعای فرمول SQL.
- `BANK_RECONCILIATION_SUMMARY_SQL_SEMANTICS_20260827_FA.md`: یازده فرمول Redacted، شش Predicate و ریسک دو Alias املایی بدون اجرای Procedure.
- `BANK_STATEMENT_PARSER_ROW_AND_ATOMICITY_20260827_FA.md`: سه Parser، شش ستون Canonical، Dedup ناامن و Partial-commit Legacy.
- `BANK_RECONCILIATION_CONFIRM_CARDEX_SEMANTICS_20260827_FA.md`: شش Update نوع‌دار و Defect Return زودهنگام که هر اجرا را به حداکثر یک Link محدود می‌کند.
- `BANK_RECONCILIATION_CONFIRM_ORCHESTRATION_20260827_FA.md`: ترتیب Outer transaction و اثبات Commit markerها همراه فقط اولین Instrument update.
- `BANK_RECONCILIATION_UNMATCH_SQL_SEMANTICS_20260827_FA.md`: Delete همهٔ Linkهای BankBill بدون Reset ابزار و تفکیک اجباری Unmatch از Reverse.
- `BANK_RECONCILIATION_DISCARD_CANCEL_BOUNDARY_20260827_FA.md`: حذف فقط ردیف‌ها، باقی‌ماندن Header و اثبات‌نشدن Cancel واقعی Legacy.
- `BANK_RECONCILIATION_INTEGRITY_AGGREGATES_20260827_FA.md`: Queryهای Aggregate بدون ID و اثبات نبود Fixture Runtime در Clone جاری.
- `BANK_RECONCILIATION_TYPE_ALIAS_AGGREGATES_20260827_FA.md`: شمارش فقط‌خواندنی هشت Literal و اثبات پوشش ۴۵٬۴۵۴ ردیفی Predicateهای Summary در برابر ۱۴۶٬۵۷۶ ردیف canonical `RCASHDRAFT` در Clone.
- `BANK_RECONCILIATION_DIFFERENTIAL_ACCEPTANCE_20260827_FA.md`: ۱۱۶ تعهد تست تفاضلی Summary/Parser/Confirm/Unmatch/Reverse/Cancel بدون ادعای اجرا.
- `BANK_RECONCILIATION_OWNER_DECISION_PACK_20260827_FA.md`: نگاشت کامل ۱۲ Case نیازمند تصمیم به هفت تصمیم مالک، گزینه‌ها و Gateهای بدون Approval استنباطی.
- `BANK_STATEMENT_PROFILE_TARGET_CONTRACT_20260827_FA.md`: Schema/Command contract نسخه‌دار و Approval-gated برای Profile امن بدون SQL/Provider/Path اجرایی.
- `BANK_RECONCILIATION_READ_MODEL_TARGET_CONTRACT_20260827_FA.md`: چهار Projection و پنج Query scoped برای Session/Rows/Links/Candidates/Summary بدون ادعای Runtime parity.
- `BANK_STATEMENT_STAGING_TARGET_CONTRACT_20260827_FA.md`: Parser worker محدود و Staging اتمیک با Hash/Idempotency/Diagnostic بدون SQL/Office/Path اجرایی.
- `BANK_RECONCILIATION_TARGET_STATE_MACHINE_20260827_FA.md`: جداسازی پنج Lifecycle state از چهار Match progress و Transitionهای مستقل Cancel/Reverse/Quarantine.
- `BANK_RECONCILIATION_COMMAND_ENVELOPE_20260827_FA.md`: Envelope اتمیک پنج Command با Guard order، Version/Idempotency و Errorهای پایدار بدون نشت Legacy.
- `BANK_RECONCILIATION_AUTHENTICATED_UAT_RUNBOOK_20260827_FA.md`: اجرای مرحله‌ای ۱۰۰ UAT با Principal/Fixture slot و Evidence بدون ذخیره هویت یا مقدار تجاری.
- `BANK_RECONCILIATION_EVIDENCE_ACCESS_REQUEST_PACK_20260827_FA.md`: نه درخواست اولویت‌دار با مالک و حداقل دسترسی برای Snapshot/Profile/Summary/UAT/Failure/Root closure.
- `BANK_RECONCILIATION_END_TO_END_EVIDENCE_MAP_20260827_FA.md`: نقشهٔ واحد Legacy→Target→Gate از Profile/Import تا Summary/Match/Confirm/Cancel/Reverse.
- `BANK_RECONCILIATION_IMPLEMENTATION_READINESS_20260827_FA.md`: تجمیع ۳۰ شاهد در نه بُعد آمادگی، شش برش ساخت و هشت Gate اجباری Pilot.
- `BANK_STATEMENT_IMPORT_BOUNDARY_20260827_FA.md`: مرز OleDb/Query، Schema file، Excel Automation و Pipeline امن Parser مقصد.
- `BANK_STATEMENT_PERSISTENCE_BOUNDARY_20260827_FA.md`: زنجیره SaveData تا CRUD BankBill، Atomicity Header/rows و حذف Hook اختیاری Runtime.
- `BANK_RECONCILIATION_GOLDEN_CASES_20260827_FA.md`: ۹۳ Case مصنوعی Import/Match/Unmatch/Confirm/Cancel با Auth/Retry/Fault/Reconciliation/Parity.
- `PRIORITY_FORM_DECLARED_FIELDS_20260827_FA.md`: متادیتای ۲۲۹ Field مستقیم هفت فرم مبهم و تفکیک Field مستقل از قابلیت‌های ارثی Framework.
- `SPECIAL_OPTIONS_DISTRICT_ASSESSMENT_20260827_FA.md`: هم‌بستگی فرم خالی، صفر Route/Launcher و صفر Candidate محدود کاتالوگ؛ پوسته یا قابلیت پویا، بدون مجوز حذف.
- `P0_IMPLEMENTATION_BACKLOG_20260827_FA.md`: ۲۶ آیتم Gateدار برای Foundation، امنیت، مهاجرت، Reconciliation، تست و اولین Web slice فقط‌خواندنی.
- `MODULE_READINESS_MATRIX_20260827_FA.md`: تراکم شواهد، Blocker و Gate چهارده ماژول؛ صفر Command/Pilot/Production-ready.
- `RISK_REGISTER_20260827_FA.md`: ۵۶ ریسک باز با Severity، کنترل، مسئول و Exit criterion؛ شامل ۳۱ ریسک بحرانی.
- `NAVIGATION_MODULE_MAP_20260827_FA.md`: درخت ۸۳۶ Route/۳۱ Root، پوشش Runtime و Hint ماژولی برای معماری ناوبری وب.
- `SCOPE_FREEZE_CATALOG_20260827_FA.md`: اولویت ۲۳۹ Route دارای FormInfo ولی Runtime-unmatched؛ ۷۶ High و حذف خودکار صفر.
- `EXTENDED_ROUTE_TYPE_RESOLUTION_20260827_FA.md`: حل ۳۳ Route Present-package به ۳۲ Type POS/Tablet/Setting/Report/VNMembers؛ یک Route ناسازگار.
- `EXTENSION_CAPABILITY_MAP_20260827_FA.md`: قابلیت و Hint ماژولی ۳۲ Type Extension با Write/Validation/Permission evidence و Gate مقصد.
- `EXTENSION_DEPENDENCY_GRAPH_20260827_FA.md`: Trace لایه‌ای ۳۲ Extension؛ ۱۳ UI با DataAccess مستقیم و ۳۱ با Business mediation.
- `EXTENSION_COMMAND_PATHS_20260827_FA.md`: Trace Method-level دوازده قابلیت مادی Extension؛ ۵۵ Command candidate و ۴۹ Guard.
- `EXTENSION_TARGET_CONTRACTS_20260827_FA.md`: یازده Command و دو Query مقصد برای Extensionهای مادی با Idempotency، Transaction، Failure و Reconciliation gate.
- `EXTENSION_GOLDEN_CASES_20260827_FA.md`: ۲۱۵ Case مصنوعی برای Auth/Scope/Retry/Fault/Reconciliation و اثبات No-mutation Queryها.
- `EXTENSION_SQL_AND_DATA_BOUNDARIES_20260827_FA.md`: Catalog فقط‌خواندنی ۱۳۲ Object candidate و تفکیک شش Direct UI→DA boundary برای مقصد.
- `EXTENSION_GAP_PATHS_20260827_FA.md`: حل Gapهای LinearDiscount/POSSession/DealerDayPath با IL عمیق و اصلاح Command نشست POS.
- `EXTENSION_SQL_ANCHOR_CONTRACTS_20260827_FA.md`: انتخاب ۴۸ Anchor SQL برای ۱۲ Capability با تفکیک دو Link اثبات‌شده از ۴۶ Candidate.
- `EXTENSION_SQL_SEMANTICS_20260827_FA.md`: Semantic footprint هشت Procedure حساس؛ ۳۱ Mutation candidate و Orchestration پرتراکم POS receipt.
- `POS_RECEIPT_REPLICATION_CONTRACT_20260827_FA.md`: Batch state machine، Idempotency، Crosswalk، Quarantine و Reconciliation رسید POS بدون Write-back به وارانگار.
- `POS_RECEIPT_TRANSITIVE_SQL_GRAPH_20260827_FA.md`: گراف محدود سه‌لایه‌ی Procedure رسید POS؛ ۵۰۰ Node و ۳۶۲ Trigger با اعلام صریح بریدگی در سقف ایمنی.
- `REQUIREMENTS_TRACEABILITY_MATRIX_20260827_FA.md`: اتصال ۱۴ ماژول به ۸۷۷ Golden case، ۵۶ ریسک و ۲۶ آیتم P0 با Gapهای صریح.
- `POS_SOURCE_MODEL_AND_SNAPSHOT_BOUNDARY_20260827_FA.md`: مدل ۱۳ جدول POS، ۵۱ Trigger، FKهای not-trusted و محدودیت داده‌ی خالی Clone.
- `STACK_AND_RECOVERY_DECISION_INPUT_20260827_FA.md`: پیشنهاد Stack تکامل‌یابنده، گزینه‌های SQL Server/PostgreSQL و RPO/RTO برای تصمیم کاربر.
- `UI_CHECKPOINT_0300_20260827_FA.md`: Snapshot فقط‌خواندنی Session ۱۸۴ و مقایسه‌ی بدون Drift با Baseline.
- `END_TO_END_PROCESS_ATLAS_20260827_FA.md`: ده مسیر انتها‌به‌انتها از Foundation تا POS با Workflow/Report/State/Test/Risk.
- `REPORT_TARGET_CONTRACTS_AND_GOLDEN_CASES_20260827_FA.md`: قرارداد ۲۰ Query/Export/Print/Statement و ۱۷۵ Golden case بدون اجرای Legacy.
- `REPORT_DEPENDENCY_GRAPH_20260827_FA.md`: Trace بیست Report به ۲۵ Business و ۲۷ DataAccess type؛ پنج Shell/Selector باز.
- `REPORT_SQL_CANDIDATES_20260827_FA.md`: ۵۱۸ نامزد کاتالوگ برای ۱۱ Report با اعلام صریح Name-match-only و سقف‌ها.
- `REPORT_METHOD_PATHS_20260827_FA.md`: Trace متدی ۲۰ Report تا ۴۷ DataAccess method و تفکیک Commit از Query.
- `REPORT_EVIDENCE_GAPS_20260827_FA.md`: سطح شاهد و برنامه بستن شکاف هر ۲۰ Report؛ ۹ مورد L3 و Result parity صفر.
- `REPORT_SHELL_ENTRYPOINTS_20260827_FA.md`: اسکن ۶۲ Assembly برای هفت Shell؛ Entry-point چهار مورد روشن شد.
- `REPORT_SHELL_CALLER_PATHS_20260827_FA.md`: Trace Callerهای Shell تا Business و ثبت مرز حل‌نشده Generic dispatch.
- `REPORT_GENERIC_BINDINGS_20260827_FA.md`: پنج EntityHelper و ۱۷ فیلتر Callerهای جنریک Dashboard/Inventory.
- `REPORT_GENERIC_SQL_CANDIDATES_20260827_FA.md`: پنج Anchor یکتای Dashboard/Cardex از کاتالوگ فقط‌خواندنی.
- `REPORT_GENERIC_SQL_SEMANTICS_20260827_FA.md`: امضا و Dependency پنج Procedure بدون اجرای آن‌ها یا ادعای Result parity.
- `ROLE_UAT_CASES_20260827_FA.md`: ۱۸۴ سناریوی Allow/Deny/Scope/SoD بدون هویت یا Grant واقعی.
- `IDENTITY_ACCESS_ADMINISTRATION_NAVIGATION_GAP_20260827_FA.md`: شانزده Route مدیریت کاربر/گروه/Scope با Runtime form و Grant مؤثر اثبات‌نشده.
- `SYSTEM_CONFIGURATION_NAVIGATION_AND_PRECEDENCE_20260827_FA.md`: پانزده Route تنظیمات، لایه‌های Scope و Gate انتشار/Close بدون ذخیره Value یا Secret.
- `FINAL_DATE_MANAGEMENT_CROSS_DOMAIN_BOUNDARY_20260827_FA.md`: چهار Command مستقل تاریخ قطعی فروش/خرید/مالی/تنخواه با DC/FiscalYear و Reopen صریح.
- `FINAL_DATE_INCIDENT_DIAGNOSTIC_PLAYBOOK_20260827_FA.md`: راهنمای عیب‌یابی تاریخ عملیات/قطعی با ۱۱ یافتهٔ کاتالوگ، IL و فعالیت سه‌ماهه؛ شامل خرابی ساخت نخستین رکورد و دامنهٔ خطر بازگشایی.
- `DATA_ENTRY_FIELD_DICTIONARY_20260827_FA.md`: ۵۸۱ Field candidate و ۱٬۵۹۴ Label امن برای ۱۴۱ فرم ورود داده.
- `DATA_ENTRY_DECLARED_FIELDS_20260827_FA.md`: ۸۱۳ Field metadata candidate؛ ۲۳۲ مورد تازه و ۴۶ فرم Base/inherited محتمل.
- `DATA_ENTRY_BASE_TEMPLATE_CONTRACTS_20260827_FA.md`: حل هر ۴۶ فرم محلیِ بدون Field به شش Template مشترک CRUD/List/Tree/Master-detail.
- `DATA_ENTRY_FIELD_TYPES_20260827_FA.md`: Decode کامل نوع CLR هر ۸۱۳ Field candidate و ثبت ۲۲۱ ناسازگاری Prefix/type.
- `DATA_ENTRY_FIELD_BINDING_CANDIDATES_20260827_FA.md`: ۷۸ Match نامی قوی و ۲۰۴ نامزد ضعیف/مبهم Field→Property بدون ادعای Binding.
- `DATA_ENTRY_FIELD_SQL_COLUMN_CANDIDATES_20260827_FA.md`: تطبیق ۱۰۰ Property با کاتالوگ ستون Clone؛ ۲۱ Anchor دقیق‌تر ولی Binding قطعی صفر.
- `TREASURY_EDIT_COMMAND_AND_VIEW_TRIGGER_BOUNDARY_20260827_FA.md`: سه فرمان ویرایش وصول، دو View قابل‌نوشتن، ۲۹ Trigger، عنوان‌های UI و سه Screen contract نامزد وب.
- `ORDER_SALE_WEB_SCREEN_AND_COMMAND_BOUNDARY_20260827_FA.md`: سه Screen درخواست/فروش/برگشت، ۱۴۰ Input، مرز Save/Validate، هفت Procedure و گراف ۷۳ Trigger.
- `STOCK_VOUCHER_AND_DISTRIBUTION_EXIT_BOUNDARY_20260827_FA.md`: مرز Draft/Confirm/Return سند انبار و آبشار SQL/Trigger توزیع تا خروج.
- `STOCK_RECONCILIATION_INCIDENT_PLAYBOOK_20260827_FA.md`: اصلاح برداشت ۱٬۵۹۴ اختلاف؛ فرمول رسمی Cardex منهای تعهد فروشِ بدون خروج، Residual صفر و Runbook امن بدون اجرای Repair.
- `DISTRIBUTION_PATH_RUNTIME_DIAGNOSTIC_20260827_FA.md`: رد برداشت Orphan-FK برای ۲۶٬۰۸۶ Header؛ اثبات کد عددی mode-dependent و قرارداد مهاجرت بدون Route حدسی.
- `SALES_RETURN_AMOUNT_DIAGNOSTIC_20260827_FA.md`: رد هشدار کاذب ۶۹۶ برگشت فعال؛ اثبات فرمول Gross→Net و Residual صفر در ۱۴٬۰۹۱ سند.
- `NGT_RETURN_CROSSWALK_DIAGNOSTIC_20260827_FA.md`: تفکیک دو برگشت موبایلی بدون سند رسمی به یک Pending/Unattempted و یک Result تاریخی با هدف جاری مفقود؛ کشف پل FRU/NGT و Failure window پس از Commit.
- `SUPPLIER_RECEIPT_COMPONENT_DIAGNOSTIC_20260827_FA.md`: رد هشدار پنج Receipt-only با Component N:M، اثبات Item authority خروج نوع ۵۵، Grain تجمعی Validator، تفاوت مسیر Desktop/SDSNET، شاهد سه‌ماهه مسیر جدید و بازیابی یکتای ۲۰ TollRef قدیمی Legacy.
- `RETURNED_CHEQUE_CROSS_CUSTOMER_DIAGNOSTIC_20260827_FA.md`: رد هشدار کاذب ۴۹ تسویه بین‌مشتری؛ اثبات تطبیق ۴۹/۴۹ با تخصیص اولیه و Over-settlement صفر.
- `RECEIVED_CHEQUE_PAY_PROJECTION_AND_LEGAL_TYPE_DIAGNOSTIC_20260827_FA.md`: رد هشدار کاذب هشت Pay link؛ تفکیک Master projection از History authority و اثبات نقص انتقال `LegalType` در تأیید گروهی.
- `PAYABLE_CHEQUE_LEAF_USAGE_DIAGNOSTIC_20260827_FA.md`: اثبات State رسمی `SOURCE_USED_UNLINKED` برای ۱۵۵ برگ و مرزبندی میان معنای معتبر منبع و علت تاریخی غیرقابل‌بازیابی.
- `VOUCHER_STATUS_POINTER_DIAGNOSTIC_20260827_FA.md`: اثبات ۱٬۰۹۴ Fork میان Current pointer و ۱۴٬۹۴۶ رخداد detached؛ منع MAX/Delete و الزام Fault-injection مسیر تغییر وضعیت.
- `EMPTY_VOUCHER_SHELL_DIAGNOSTIC_20260827_FA.md`: رد تفسیر سند Posted خراب؛ طبقه‌بندی یک Draft شماره‌دار بدون قلم و اثر مالی صفر با شماره‌ی نیازمند تصمیم حسابدار.
- `SUPPLIER_INVOICE_RETURN_AND_TRIGGER_GUARD_BOUNDARY_20260827_FA.md`: مرز فاکتور/برگشت خرید، Toll و Guard تریگری رابطهٔ سند انبار.
- `SUPPLIER_COST_APPLY_REAPPLY_ATOMICITY_BOUNDARY_20260829_FA.md`: ترتیب Apply/ReApply هزینه، تطبیق Status/Price، Callerهای تراکنشی و غیرتراکنشی، IL هش‌سنجی‌شده و قرارداد Atomic مقصد (`R-071`).
- `SUPPLIER_UNAPPLY_DELETE_AND_COST_REVERSAL_BOUNDARY_20260829_FA.md`: مسیرهای متفاوت Unlink/Delete، Relation lifecycle فعال، N:M cost reversal، Audit gap و قرارداد مقصد (`R-072`).
- `PAYABLE_CHEQUE_DESTRUCTIVE_UNDO_BOUNDARY_20260829_FA.md`: حذف فیزیکی آخرین History در Undo چک پرداختنی، تطبیق Log، Projection جاری، محدودیت فرم‌های Runtime و قرارداد append-only مقصد (`R-073`).
- `RECEIVED_CHEQUE_DESTRUCTIVE_UNDO_AND_TRIGGER_PROJECTION_BOUNDARY_20260829_FA.md`: Undo یک/دو رخداد چک دریافتی، Projection تریگری `IsLast`، تطبیق Log/Runtime و قرارداد جبرانی مقصد (`R-074`).
- `UI_CHECKPOINT_0545_TO_0900_20260827_FA.md`: پایش بدون تعامل UI وارانگار از ثبت میانی تا پایان بازه.
- `ACCOUNTING_VOUCHER_ENTRYPOINTS_AND_AUTOMATION_BOUNDARY_20260827_FA.md`: تفکیک سند خودکار، تأیید انبار و سند دستی با Config/date/source guards.
- `domains/19_VOUCHER_CREATION_ATOMICITY_AND_POLICY_FA.md`: Binding دقیق فرم تا `usp_DoExternalVoucher`، Atomicity مسیر Desktop، ۱۱ Creator و Drift سیاست صدور تاریخی.
- `domains/20_EXTERNAL_VOUCHER_LIFECYCLE_FA.md`: مسیر دقیق Confirm/Unconfirm/Delete/Transfer، State machine، یک‌به‌یکی دفترکل و شکاف Cleanup پیش از Validation.
- `domains/21_ACCOUNTING_ISSUANCE_FINALITY_BOUNDARY_FA.md`: الگوریتم تاریخ قطعی صدور، شکست pre-mutation، پوشش ناقص StockDC خرید و استثنای بدون نمونهٔ حقوق.
- `domains/22_VOUCHER_TYPE_STRUCTURAL_VALIDATION_FA.md`: Validator نوع سند، ۴۵ کاندید از ۶۵ تنظیم، ۲۰ نوع Dormant/ناقص و ۷۱ Predicate اجرا‌نشده.
- `domains/23_DYNAMIC_RULE_SQL_AND_SOURCE_SNAPSHOT_FA.md`: خواندن `NOLOCK` منبع staging، دو محل SQL پویای Rule و قرارداد DSL/Snapshot مقصد.
- `domains/24_VOUCHER_RULE_TEMPLATE_TRANSFER_AND_PUBLISH_FA.md`: دو Procedure انتقال Template، نبود مسیر ویرایش Application، Failure window انتشار جزئی و Command انتشار مقصد.
- `domains/25_RULE_REPLICATION_TRANSPORT_AND_RECEIPT_FA.md`: سرویس مستقل Replication، Binary outbox، Transaction دریافت و محدودیت Watermark بدون Rule version/approval.
- `NGT_CONFIGURATION_PRECEDENCE_AND_TRANSPORT_BOUNDARY_20260829_FA.md`: Resolver چندسطحی App/Device/Center، اختلاف Business با View انتقال، NULL/removed، قرارداد مقصد و checkpoint مستقل ۳۹/۳۹ (`R-061`).
- `NGT_ORDER_PERSISTENCE_REPLICATION_AND_CROSSWALK_BOUNDARY_20260829_FA.md`: مسیر Save/Update/Replication سفارش NGT، مالکیت transaction، دو grain هم‌زمان Crosswalk، Split/Many-to-one، تقویت `R-033` و checkpoint آفلاین هش‌دار.
- `NGT_TOUR_CUSTOMER_CALL_STATE_AND_COMMAND_BOUNDARY_20260829_FA.md`: state machine واقعی Tour/CustomerCall، PreviousStatus محدود، taxonomy ترکیبی Visit/Delivery، مرز زمان، mutating GET و قرارداد مقصد (`R-008`/`R-062`).
- `NGT_PAYMENT_SETTLEMENT_AND_RECEIPT_BOUNDARY_20260829_FA.md`: سربرگ/ریز پرداخت NGT، تخصیص سفارش جاری و فاکتور قدیمی، اتصال Receipt، PaymentApproved، تراکنش مستقل `SaveTourPaymentChanges`، ۵۷ کم‌تخصیص و قرارداد مقصد (`R-007`/`R-061`/`R-063`).
- `NGT_PAYMENT_REPLICATION_AND_CROSSWALK_IDEMPOTENCY_BOUNDARY_20260829_FA.md`: مسیر واقعی پرداخت موبایل تا Receipt/ابزار/Settlement، `TourHistory(Type=10)`، ۷۰ Crosswalk شماره-only با History تکراری، مرز Commit/Write-back و قرارداد Idempotency مقصد (`R-007`/`R-064`).
- `CUSTOMER_GOODS_MASTER_WEB_SCREEN_BOUNDARY_20260827_FA.md`: مرز واقعی فیلد/مجوز/روابط مشتری و کالا و Gate شروع Read-only وب.
- `SUPPLIER_MASTER_WEB_SCREEN_BOUNDARY_20260827_FA.md`: مرز مستقل تأمین‌کننده با Guard پرداخت، Contact/DL، حسابداری و کاردکس.
- `OPERATIONAL_CONTEXT_AND_STOCK_DC_WEB_BOUNDARY_20260827_FA.md`: تفکیک سال عملیاتی/مالی، DC، دفتر فروش، انبار، نوع موجودی و PriceMethod.
- `MORNING_HANDOFF_0900_20260827_FA.md`: جمع‌بندی قابل‌اقدام شناخت، محدودیت‌ها، ترتیب ساخت و تصمیم‌های لازم برای ERP شخصی نگین.
- `CONTEXTUAL_PRICE_DISCOUNT_WEB_BOUNDARY_20260827_FA.md`: Scope، Priority، Version، Condition، Prize و Close قیمت/تخفیف.
- `../../scripts/windows/extract_varanegar_ui_inventory.ps1`: استخراج‌گر فقط‌خواندنی UI/Win32.
- `../../scripts/windows/extract_varanegar_targeted_il_contracts.py`: IL فقط برای Typeهای Allowlist‌شده، با Redaction رشته‌ها.
- `../../scripts/sql/extract_varanegar_ui_sql_contracts.py`: اتصال تکرارپذیر Commandهای UI به Signature/Dependency/Hash در Clone فقط‌خواندنی.
- `../../scripts/windows/rebuild_negin_erp_risk_and_traceability.ps1`: بازسازی آفلاین و یک‌مرحله‌ای رجیستر ریسک و Traceability از Artifactهای ماندگار.
- `../../scripts/sql/extract_varanegar_route_authorization_matrix.py`: استخراج ناشناس و تجمیعی Page/Command rights بدون هویت یا Grant فردی.
- `../../artifacts/varanegar_analysis/ui/`: Artifactهای Runtime بدون مقدارهای Data-bound.
- `../../artifacts/varanegar_analysis/manifest_20260826.json`: Manifest اعتبارسنجی و Hash همه خروجی‌ها.

## دامنه‌های ثبت‌شده

1. [ساختار سازمانی و سال مالی](domains/01_ORGANIZATION_AND_FISCAL_YEAR_FA.md)
2. [جغرافیا و مسیرها](domains/02_GEOGRAPHY_AND_ROUTES_FA.md)
3. [واحدها، نوع حمل/انبار و انواع سند](domains/03_UNITS_STOCK_AND_DOCUMENT_TYPES_FA.md)
4. [کالا، گروه، برند، بسته‌بندی و بارکد](domains/04_PRODUCT_CATALOG_FA.md)
5. [طرف‌حساب، مشتری، تأمین‌کننده، پرسنل و نقش فروش](domains/05_PARTIES_CUSTOMERS_SUPPLIERS_PERSONNEL_FA.md)
6. [قیمت، قیمت قراردادی، تخفیف و جایزه](domains/06_PRICING_DISCOUNTS_AND_PRIZES_FA.md)
7. [چرخه سفارش تا فروش](domains/07_ORDER_TO_SALE_LIFECYCLE_FA.md)
8. [موجودی، رزرو، گردش انبار و خروج کالا](domains/08_INVENTORY_RESERVATION_AND_EXIT_FA.md)
9. [توزیع، تیم ارسال، خروج و شاهد تحویل](domains/09_DISTRIBUTION_AND_DELIVERY_FA.md)
10. [وصول، ابزار دریافت، تخصیص پرداخت و مانده باز](domains/10_COLLECTIONS_PAYMENTS_OPEN_INVOICES_FA.md)
11. [برگشت از فروش، ورود انبار و مصرف اعتبار](domains/11_SALES_RETURNS_AND_SETTLEMENT_FA.md)
12. [چرخه چک دریافتی و تسویه چک برگشتی](domains/12_RECEIVED_CHEQUE_LIFECYCLE_FA.md)
13. [خرید، مرجوعی خرید و بدهی تأمین‌کننده](domains/13_SUPPLIER_PURCHASE_AND_PAYABLES_FA.md)
14. [خروج وجه تأمین‌کننده و چرخه چک پرداختنی](domains/14_SUPPLIER_DISBURSEMENT_AND_PAYABLE_CHEQUES_FA.md)
15. [قرارداد رسمی کاردکس و مانده تأمین‌کننده](domains/15_OFFICIAL_SUPPLIER_CARDEX_CONTRACT_FA.md)
16. [مجوزهای Legacy، دامنه داده و RBAC مستقل NGT](domains/16_AUTHORIZATION_LEGACY_AND_NGT_FA.md)
17. [تنظیمات چندسطحی و فلگ‌های قواعد کسب‌وکار](domains/17_CONFIGURATION_AND_RULE_FLAGS_FA.md)
18. [PreVoucher، سند خارجی و دفترکل دوبل](domains/18_GENERAL_LEDGER_STAGING_AND_POSTING_FA.md)
19. [مسیر واقعی ساخت سند، Atomicity و نسخهٔ سیاست صدور](domains/19_VOUCHER_CREATION_ATOMICITY_AND_POLICY_FA.md)
20. [چرخهٔ تأیید، حذف و انتقال سند خارجی به دفترکل](domains/20_EXTERNAL_VOUCHER_LIFECYCLE_FA.md)
21. [مرز تاریخ قطعی پیش از صدور سند حسابداری](domains/21_ACCOUNTING_ISSUANCE_FINALITY_BOUNDARY_FA.md)
22. [اعتبارسنجی ساختاری نوع سند و مرز قابلیت فعال](domains/22_VOUCHER_TYPE_STRUCTURAL_VALIDATION_FA.md)
23. [مرز SQL پویای قواعد و Snapshot منبع سند حسابداری](domains/23_DYNAMIC_RULE_SQL_AND_SOURCE_SNAPSHOT_FA.md)
24. [انتقال Template قواعد سند و مرز انتشار](domains/24_VOUCHER_RULE_TEMPLATE_TRANSFER_AND_PUBLISH_FA.md)
25. [انتقال، Outbox و Receipt قواعد حسابداری](domains/25_RULE_REPLICATION_TRANSPORT_AND_RECEIPT_FA.md)

## مرزهای متمرکز NGT در ۲۰۲۶-۰۸-۲۹

- [Replication پرداخت و Idempotency رسید](NGT_PAYMENT_REPLICATION_AND_CROSSWALK_IDEMPOTENCY_BOUNDARY_20260829_FA.md)
- [Compensation و Rollback پس از Replication](NGT_REPLICATION_COMPENSATION_AND_ROLLBACK_BOUNDARY_20260829_FA.md)
- [Replication، Crosswalk و Atomicity برگشت NGT](NGT_RETURN_REPLICATION_AND_INGEST_ATOMICITY_BOUNDARY_20260829_FA.md)
- [Replication فروش و Idempotency تاریخچه Type=8](NGT_SALE_REPLICATION_TYPE8_IDEMPOTENCY_BOUNDARY_20260829_FA.md)
- [تطبیق تاریخچه سفارش NGT با هدف مفقود](NGT_ORDER_HISTORY_MISSING_TARGET_RECONCILIATION_BOUNDARY_20260829_FA.md)
- [حذف Target سفارش و Tombstone آگاه از NGT](NGT_ORDER_TARGET_DELETION_AND_TOMBSTONE_BOUNDARY_20260829_FA.md)
- [تطبیق علّی Delete Log با Targetهای مفقود NGT](NGT_ORDER_DELETE_LOG_CAUSAL_RECONCILIATION_BOUNDARY_20260829_FA.md)

## مرز متمرکز خرید و هزینه در ۲۰۲۶-۰۸-۲۹

- [Atomicity اعمال و اعمال‌مجدد هزینهٔ فاکتور تأمین‌کننده](SUPPLIER_COST_APPLY_REAPPLY_ATOMICITY_BOUNDARY_20260829_FA.md)
- [Unapply، حذف فاکتور خرید و برگشت هزینه](SUPPLIER_UNAPPLY_DELETE_AND_COST_REVERSAL_BOUNDARY_20260829_FA.md)

## مرز متمرکز خزانه در ۲۰۲۶-۰۸-۲۹

- [Undo تخریبی تاریخچهٔ چک پرداختنی](PAYABLE_CHEQUE_DESTRUCTIVE_UNDO_BOUNDARY_20260829_FA.md)
- [Undo تخریبی چک دریافتی و Projection مبتنی بر Trigger](RECEIVED_CHEQUE_DESTRUCTIVE_UNDO_AND_TRIGGER_PROJECTION_BOUNDARY_20260829_FA.md)
- [حذف Master چک دریافتی و مرز پاک‌سازی Receipt](RECEIVED_CHEQUE_AND_RECEIPT_DELETION_BOUNDARY_20260829_FA.md)

## مرز متمرکز انبار در ۲۰۲۶-۰۸-۲۹

- [ماشین حالت تأیید، ابطال تأیید و حذف سند انبار](STOCK_VOUCHER_CONFIRM_UNCONFIRM_DELETE_STATE_BOUNDARY_20260829_FA.md)
- [Projection موجودی و Failure اعتبارسنجی پس از سند](STOCK_PROJECTION_AND_POST_VALIDATION_FAILURE_BOUNDARY_20260829_FA.md)

## مرز متمرکز توزیع در ۲۰۲۶-۰۸-۲۹

- [صدور، ادغام، لغو و حذف فیزیکی خروج توزیع](DISTRIBUTION_EXIT_ISSUE_CANCEL_AND_PHYSICAL_DELETE_BOUNDARY_20260829_FA.md)

## مرز متمرکز فروش در ۲۰۲۶-۰۸-۲۹

- [تراکنش، وضعیت و حذف در تبدیل سفارش به فروش](ORDER_TO_SALE_CONVERSION_TRANSACTION_AND_STATE_BOUNDARY_20260829_FA.md)
- [لغو فروش، پرداخت، موجودی و پیوند سفارش/خروج](SALE_CANCELLATION_PAYMENT_STOCK_AND_ORDER_POINTER_BOUNDARY_20260829_FA.md)
- [صدور و لغو برگشت از فروش، سند ورود و اعتبار](SALES_RETURN_ISSUE_CANCEL_VOUCHER_AND_CREDIT_BOUNDARY_20260829_FA.md)
- [Snapshot ووچر فروش و تبدیل معکوس](SALE_VOUCHER_SNAPSHOT_AND_REVERSE_CONVERSION_BOUNDARY_20260829_FA.md)
- [Watermark صدور حسابداری فروش و Crosswalk دفترکل](SALE_ACCOUNTING_ISSUANCE_WATERMARK_AND_CROSSWALK_BOUNDARY_20260829_FA.md)
- [Template فاکتور Crystal و Audit چاپ فیزیکی](SALE_INVOICE_CRYSTAL_TEMPLATE_AND_PRINT_AUDIT_BOUNDARY_20260829_FA.md)

## مرز مشترک نتیجه و تراکنش در ۲۰۲۶-۰۸-۲۹

- [ماتریس Outcome، پیام، Commit و Rollback فرمان‌ها](COMMAND_OUTCOME_MESSAGE_COMMIT_AND_ROLLBACK_MATRIX_20260829_FA.md)
- [Idempotency، Retry و Guardهای ذخیره‌سازی](IDEMPOTENCY_RETRY_AND_STORAGE_GUARD_BOUNDARY_20260829_FA.md)
- [Policy Override و تبدیل جزئی سفارش به فروش](ORDER_TO_SALE_POLICY_OVERRIDE_AND_PARTIAL_CONVERSION_BOUNDARY_20260829_FA.md)
- [تاریخ عملیات و قطعیت تبدیل سفارش به فروش](ORDER_TO_SALE_OPERATION_DATE_AND_FINALITY_BOUNDARY_20260829_FA.md)
- [Authorization و Resource Scope تبدیل سفارش به فروش](ORDER_TO_SALE_AUTHORIZATION_AND_RESOURCE_SCOPE_BOUNDARY_20260829_FA.md)
- [مالکیت DataContext Transaction و شکاف EVC/Conversion](DATACONTEXT_TRANSACTION_OWNERSHIP_AND_ORDER_SALE_SPLIT_20260829_FA.md)
- [Gap Map آغاز مرحله شناخت ۲۵ ساعته](VARANEGAR_25H_OPENING_GAP_MAP_20260829_FA.md)
- [Binding گزارش‌های مرجع موجودی و طرح Reconciliation](STOCK_REFERENCE_REPORT_BINDINGS_AND_RECONCILIATION_20260829_FA.md)
- [مرز Template خارجی گزارش برگشت فروش](RETURN_REPORT_EXTERNAL_TEMPLATE_BOUNDARY_20260829_FA.md)
- [گزارش کاردکس سلامت و مرز Print Attempt](HEALTHY_CARDEX_REPORT_AND_PRINT_ATTEMPT_BOUNDARY_20260829_FA.md)
- [چاپ Batch، Partial Success و Completion](PRINT_BATCH_PARTIAL_SUCCESS_AND_COMPLETION_BOUNDARY_20260829_FA.md)
- [شکاف EVC، fallback دو محاسبه‌ای و Discount V2](ORDER_TO_SALE_EVC_SPLIT_AND_DISCOUNT_V2_BOUNDARY_20260829_FA.md)
- [Datasetهای ورودی و Query contract موتور Discount V2](DISCOUNT_V2_INPUT_DATASET_AND_QUERY_CONTRACT_20260829_FA.md)
- [Pipeline موتور Discount V2 و مرز قواعد SQL پویا](DISCOUNT_V2_ENGINE_PIPELINE_AND_DYNAMIC_RULE_BOUNDARY_20260829_FA.md)
- [تحویل Baseline/Bundle/Test مرحله شناخت ۱۵ ساعته](VARANEGAR_15H_FINAL_HANDOFF_20260829_FA.md)

## سطح اطمینان

- **تأییدشده:** مستقیماً از Clone فقط‌خواندنی، فایل رسمی برنامه یا آزمون قابل
  تکرار استخراج شده است.
- **استنباط قوی:** چند شاهد مستقل آن را پشتیبانی می‌کنند، اما قرارداد رسمی هنوز
  پیدا نشده است.
- **فرضیه:** برای ادامه بررسی ثبت شده و نباید مبنای مهاجرت یا پیاده‌سازی باشد.
- **ردشده:** بررسی بعدی نادرستی آن را ثابت کرده است؛ دلیل رد باید حفظ شود.

## قرارداد ثبت هر دامنه

هر سند دامنه باید حداقل این موارد را داشته باشد:

`عنوان → جدول اصلی → جداول جزئیات → PK/FK → ارتباط‌های ضمنی → مصرف‌کننده‌ها → تعداد رکورد → نمونه وضعیت فعلی → ابهام‌ها → مدل پیشنهادی مقصد`

## مرز ایمنی

- استخراج از `127.0.0.1 / NeginPakhsh_WebDev` انجام می‌شود.
- Clone باید `READ_ONLY` و حساب تحلیل عضو `db_denydatawriter` باشد.
- هیچ رمز، Connection String یا مقدار حساس در اسناد و Artifactها ذخیره نمی‌شود.
- مشاهده UI فقط Property/Window metadata است؛ Invoke/SetValue/SendKeys و
  هر Command عملیاتی ممنوع است.
- متادیتای Clone یا زمان استفاده Indexها به‌تنهایی شاهد فعالیت سه‌ماهه سیستم
  عملیاتی نیست؛ آن تحلیل یک مسیر مستقل و تاریخ‌محور دارد.

## بازسازی خروجی‌های تجمیعی و اعتبارسنجی

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\build_varanegar_three_month_activity.py `
  --output G:\NeginAI\artifacts\varanegar_analysis\three_month_operational_activity_20260826.json

G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\validate_varanegar_reconstruction_bundle.py `
  --output G:\NeginAI\artifacts\varanegar_analysis\manifest_20260826.json

G:\NeginAI\.venv\Scripts\python.exe -m pytest `
  G:\NeginAI\tests\test_varanegar_reconstruction_evidence.py -q
```

Validator باید `PASS` و تست متمرکز باید `7 passed` برگرداند. هر تغییر در
Extractor/Artifact/Doc، Hash متناظر Manifest را تغییر می‌دهد و باید همراه با
Discovery Log و Golden case مربوطه بازبینی شود.

بسته تکمیلی Party Cardex در
`PARTY_CARDEX_SCOPE_FORMULA_AND_RECONCILIATION_20260829_FA.md`، Artifact قرارداد
`party_cardex_reference_contract_20260829.json` و checkpoint زنجیره‌ای
`varanegar_party_cardex_checkpoint_20260829.json` ثبت شده است. این بسته فقط
Static IL و Catalog clone را می‌خواند و هیچ گزارش/Procedure/Fararu را اجرا نمی‌کند.

بسته `RPT-13` در `PRODUCTION_ORDER_REPORT_SCOPE_AND_RECONCILIATION_20260829_FA.md`
و `production_order_report_contract_20260829.json` است. checkpoint آن مستقیماً به
Party Cardex متصل است و Query/Export عملیاتی اجرا نمی‌کند.

بسته `RPT-06` در `CALL_CENTER_REPORT_TYPE_SCOPE_AND_PARITY_20260829_FA.md` و
`call_center_report_contract_20260829.json` است؛ mapping مقدار `Type` را ادعا
نمی‌کند و checkpoint آن به `RPT-13` زنجیر شده است.

بسته `RPT-14` در `PRODUCTION_DETAIL_BATCH_SCOPE_AND_EXPORT_20260829_FA.md` و
`production_detail_report_contract_20260829.json` است. binding آن از inheritance
ایستا اثبات شده و checkpoint به `RPT-06` متصل است.

بسته selectorهای `RPT-16/RPT-17` در `STOCK_REPORT_SELECTOR_ROUTING_BOUNDARY_20260829_FA.md`
و `stock_report_selector_contract_20260829.json` است؛ result set مستقل به آنها
نسبت نمی‌دهد و downstream را به RPT-14/RPT-15 پیوند می‌دهد.

بسته `RPT-03/RPT-04` در `DASHBOARD_HOST_ZOOM_AND_WIDGET_PARITY_20260829_FA.md` و
`dashboard_shell_contract_20260829.json` است؛ shell parity را از پنج قرارداد child
widget جدا می‌کند.

بسته `RPT-01/RPT-02` در `TREASURY_CRYSTAL_VIEWER_EXTERNAL_DOCUMENT_BOUNDARY_20260829_FA.md`
و `treasury_crystal_viewer_contract_20260829.json` است؛ Viewer را از مالکیت
caller/template جدا می‌کند.

دفتر تجمیعی `REPORT_SURFACE_CLOSURE_LEDGER_20260829_FA.md` و Artifact
`varanegar_report_surface_closure_ledger_20260829.json` وضعیت ownership، parity و
readiness هر ۲۰ Surface را بدون خلط این سه محور ثبت می‌کند.

دفتر `COMMAND_TRUTH_TABLE_READINESS_LEDGER_20260829_FA.md` و Artifact
`varanegar_command_readiness_ledger_20260829.json` پنج ضلع فرمان را برای ۱۴ ماژول
ردیابی می‌کند و design evidence را از runtime/owner approval جدا نگه می‌دارد.

Artifact `discount_rule_authoring_boundary_20260829.json` مسیر ساخت، اجرای
آزمایشی، Save و شکاف مجوز محلی `SqlCondition` را به‌صورت IL ایستا ثبت می‌کند؛
نبود Guard محلی به معنی نبود مجوز Menu/BaseForm نیست.
Artifact `discount_rule_authorization_boundary_20260829.json` نیز Route
`DiscountRules/404`، چهار قابلیت CRUD و نبود Review/Publish مستقل را فقط با
Aggregate ناشناس و بدون ذخیره هویت/Assignment ثبت می‌کند.
# به‌روزرسانی ۱۴۰۵/۰۶/۰۷ — Golden/UAT

- [دفتر شواهد Golden Case و UAT](GOLDEN_UAT_EVIDENCE_LEDGER_20260829_FA.md): تفکیک صریح ۷۷ طراحی synthetic از اجرای ایزوله، تطبیق نتیجه و تأیید مالک؛ وضعیت UAT/pilot همچنان صفر.
- [ماتریس Playbook کارشناسی](EXPERT_INCIDENT_PLAYBOOK_MATRIX_20260829_FA.md): ده سناریوی اصلی با evidence، تصمیم چهارحالته، مرز توقف، ریسک و اثر ERP مقصد.
- [تحویل نهایی مرحله ۲۵ ساعته](VARANEGAR_25H_FINAL_HANDOFF_20260829_FA.md): baseline نهایی، مرز اثبات و دروازه‌های باقی‌ماندهٔ UAT/مالک.
- [Gap Map ادامهٔ ۲۴ساعته](VARANEGAR_24H_CONTINUATION_GAP_MAP_20260829_FA.md): رتبه‌بندی شکاف‌های بعد از baseline و جداسازی کار ایستا از UAT.
- [Truth Table outcome و lineage حسابداری](ACCOUNTING_COMMAND_OUTCOME_LINEAGE_TRUTH_20260829_FA.md): هفت candidate فرمان با transaction، نتیجه، retry و confidence.
- [مرز Manual Voucher](MANUAL_VOUCHER_SAVE_CANCEL_STATIC_BOUNDARY_20260829_FA.md): اثبات Save عمومی و رد `InternalCancelCommand` به‌عنوان فرمان لغو مالی.
- [Generic Save و transaction در Manual Voucher](MANUAL_VOUCHER_GENERIC_SAVE_TRANSACTION_20260829_FA.md): binding دقیق generic handler/adapter و مالک Commit در مسیرهای CRUD.
- [اصلاح Inventory فرمان حسابداری](ACCOUNTING_COMMAND_INVENTORY_CORRECTION_20260829_FA.md): کاهش هفت candidate به شش و حذف UI-close از فرمان‌های مالی.
- [Delta آمادگی فرمان حسابداری](COMMAND_READINESS_ACCOUNTING_DELTA_20260829_FA.md): ارتقای outcome-contract طراحی‌شده بدون ادعای runtime readiness.
- [Golden/UAT حسابداری](ACCOUNTING_GOLDEN_UAT_CASES_20260829_FA.md): ۴۲ case مصنوعی برای شش فرمان اصلاح‌شده و حذف false cancel family.
- [Golden Fixture گزارش‌ها](REPORT_GOLDEN_FIXTURE_DESIGN_20260829_FA.md): ۸۸ fixture design برای ۲۰ سطح و ownership-aware assertionها.
- [Playbook تخصصی و قرارداد ERP حسابداری](ACCOUNTING_EXPERT_PLAYBOOK_AND_ERP_CONTRACT_20260829_FA.md): پنج مسیر تشخیص evidence-first و قرارداد ۹بخشی مقصد با acceptance gate چهل‌ودو case.
- [دلتا‌ی Traceability و Risk ادامه](CONTINUATION_TRACEABILITY_RISK_DELTA_20260829_FA.md): اتصال هفت بستهٔ شاهد تازه به نیازها، ماژول‌ها و ریسک‌های موجود بدون بازنویسی ثبت پایه.
- [Checkpoint میانی Wave-01 ادامه](VARANEGAR_24H_CONTINUATION_WAVE01_20260829_FA.md): baseline غیرنهایی موج حسابداری/Golden/Playbook و اولویت‌های موج بعد.
- [Outcome/Retry فرمان‌های خزانه](TREASURY_COMMAND_OUTCOME_RETRY_ENVELOPE_20260829_FA.md): ۱۲ فرمان legacy/target با چهار outcome و read-back اجباری.
- [دلتا‌ی آمادگی خزانه](TREASURY_COMMAND_READINESS_DELTA_20260829_FA.md): ارتقای design coverage از چهار به پنج ماژول بدون runtime promotion.
- [Golden/UAT خزانه](TREASURY_GOLDEN_UAT_CASES_20260829_FA.md): ۸۴ case مصنوعی برای denial، retry، fault و شاخه‌های خاص.
- [Playbook تخصصی خزانه](TREASURY_EXPERT_INCIDENT_PLAYBOOK_20260829_FA.md): شش رخداد evidence-first بدون تشخیص یا repair ساختگی.
- [دلتا‌ی Traceability خزانه](TREASURY_TRACEABILITY_RISK_DELTA_20260829_FA.md): چهار شاهد، هفت نیازمندی و ۹ ریسک موجود.
- [Outcome/Retry فرمان‌های توزیع](DISTRIBUTION_COMMAND_OUTCOME_RETRY_ENVELOPE_20260829_FA.md): چهار فرمان با transaction/idempotency gap و read-back چندجدولی.
- [دلتا‌ی آمادگی توزیع](DISTRIBUTION_COMMAND_READINESS_DELTA_20260829_FA.md): افزایش design coverage از پنج به شش بدون runtime promotion.
- [Golden/UAT توزیع](DISTRIBUTION_GOLDEN_UAT_CASES_20260829_FA.md): ۲۸ case برای late-cardex، unknown merge و partial cleanup.
- [Playbook تخصصی توزیع](DISTRIBUTION_EXPERT_INCIDENT_PLAYBOOK_20260829_FA.md): پنج رخداد evidence-first با مرز توقف پیش از repair.
- [دلتا‌ی Traceability توزیع](DISTRIBUTION_TRACEABILITY_RISK_DELTA_20260829_FA.md): چهار شاهد، هفت نیازمندی و ۹ ریسک موجود.
- [قرارداد تطبیق و قرنطینهٔ بین‌ماژولی](CROSS_MODULE_RECONCILIATION_AND_QUARANTINE_CONTRACT_20260829_FA.md): هفت لبه، ۱۰ invariant، شِمای رسید ده‌بخشی و قواعد منفی استنتاج.
- [Golden Caseهای تطبیق بین‌ماژولی](CROSS_MODULE_RECONCILIATION_GOLDEN_CASES_20260829_FA.md): ۳۵ طراحی مصنوعی برای پنج حالت هر لبه، بدون اجرای runtime.
- [Playbook تطبیق بین‌ماژولی](CROSS_MODULE_RECONCILIATION_PLAYBOOK_20260829_FA.md): هفت مسیر evidence-first با قرنطینه و توقف پیش از repair/retry.
- [دلتا‌ی Traceability تطبیق بین‌ماژولی](CROSS_MODULE_RECONCILIATION_TRACEABILITY_RISK_DELTA_20260829_FA.md): سه شاهد، ۱۰ نیازمندی و ۱۰ ریسک موجود بدون promotion.
- [Gap Refresh ادامه](VARANEGAR_24H_CONTINUATION_GAP_REFRESH_20260829_FA.md): انتخاب `reporting_documents` پس از پوشش شش ماژول و تفکیک دروازه‌های خارجی.
- [Outcome/Retry خروجی‌های گزارش](REPORTING_OUTPUT_OUTCOME_RETRY_ENVELOPE_20260829_FA.md): هشت سطح، پنج outcome و جداسازی Render/Print/Completion/Audit/File/Import.
- [Delta آمادگی خروجی‌های گزارش](REPORTING_OUTPUT_READINESS_DELTA_20260829_FA.md): افزایش design coverage از شش به هفت بدون runtime promotion.
- [Golden/UAT خروجی‌های گزارش](REPORTING_OUTPUT_GOLDEN_UAT_CASES_20260829_FA.md): ۵۶ Case مصنوعی و اجرا‌نشده برای هشت سطح.
- [Playbook خروجی‌های گزارش](REPORTING_OUTPUT_EXPERT_PLAYBOOK_20260829_FA.md): شش مسیر evidence-first با توقف پیش از Reprint/Replay.
- [Delta ردیابی خروجی‌های گزارش](REPORTING_OUTPUT_TRACEABILITY_RISK_DELTA_20260829_FA.md): پنج شاهد، ۱۰ نیازمندی و هشت ریسک موجود.
- [قرارداد Outcome/Retry و انتشار قواعد قیمت‌گذاری](PRICING_RULE_OUTCOME_RETRY_AND_PUBLICATION_CONTRACT_20260829_FA.md): هفت مسیر، DSL امن، تخصیص اتمیک و مرز Replication.
- [Delta آمادگی قواعد قیمت‌گذاری](PRICING_RULE_READINESS_DELTA_20260829_FA.md): افزایش پوشش طراحی از هفت به هشت ماژول بدون Runtime promotion.
- [Golden/UAT Delta قواعد قیمت‌گذاری](PRICING_RULE_GOLDEN_UAT_DELTA_20260829_FA.md): reuse شصت‌وچهار Case و ۲۸ Case تازه؛ مجموع طراحی ۹۲.
- [Playbook تخصصی قواعد قیمت‌گذاری](PRICING_RULE_EXPERT_PLAYBOOK_20260829_FA.md): هفت مسیر Evidence-first برای اولویت، DSL، allocator، provenance و replication.
- [Delta ردیابی قواعد قیمت‌گذاری](PRICING_RULE_TRACEABILITY_RISK_DELTA_20260829_FA.md): پنج شاهد، ۱۰ نیازمندی، ۳۰ Link ماژولی و ۴۰ Link ریسک.
- [قرارداد Outcome/Receipt در Integration/Migration](INTEGRATION_MIGRATION_OUTCOME_RECEIPT_CONTRACT_20260829_FA.md): شش مسیر و تفکیک Stage/Apply/Reconcile/Ack/Compensation.
- [Delta آمادگی Integration/Migration](INTEGRATION_MIGRATION_READINESS_DELTA_20260829_FA.md): افزایش پوشش طراحی از هشت به نه ماژول بدون Runtime promotion.
- [Golden/UAT Delta Integration/Migration](INTEGRATION_MIGRATION_GOLDEN_UAT_DELTA_20260829_FA.md): reuse سی‌وچهار Case و ۳۵ Case تازه؛ مجموع ۶۹.
- [Playbook تخصصی Integration/Migration](INTEGRATION_MIGRATION_EXPERT_PLAYBOOK_20260829_FA.md): هفت مسیر برای Package، Ordering، Ack، Crosswalk، Compensation و Migration.
- [Delta ردیابی Integration/Migration](INTEGRATION_MIGRATION_TRACEABILITY_RISK_DELTA_20260829_FA.md): پنج شاهد، ۱۰ نیازمندی، ۳۵ Link ماژولی و ۴۵ Link ریسک.
- [قرارداد نسخه، تقدم و انتشار پیکربندی](CONFIGURATION_VERSION_PRECEDENCE_ROLLOUT_CONTRACT_20260829_FA.md): پنج فرمان، نسخهٔ immutable، تقدم قطعی، null تایپ‌شده، secret reference و rollout acknowledgment.
- [Delta آمادگی پیکربندی](CONFIGURATION_READINESS_DELTA_20260829_FA.md): افزایش پوشش طراحی از نه به ده ماژول بدون Runtime promotion.
- [Golden/UAT Delta پیکربندی](CONFIGURATION_GOLDEN_UAT_DELTA_20260829_FA.md): reuse پنجاه‌وچهار Case و ۲۸ Case تازه؛ مجموع ۸۲.
- [Playbook تخصصی پیکربندی](CONFIGURATION_EXPERT_PLAYBOOK_20260829_FA.md): هفت مسیر برای drift، تقدم، null، removed-reference، secret، partial ack و rollback.
- [Delta ردیابی پیکربندی](CONFIGURATION_TRACEABILITY_RISK_DELTA_20260829_FA.md): پنج شاهد، ۱۰ نیازمندی، ۳۰ Link ماژولی و ۴۵ Link ریسک.
- [قرارداد تصمیم و Session هویت/مجوز](IDENTITY_AUTHORIZATION_DECISION_SESSION_CONTRACT_20260829_FA.md): شش فرمان deny-first برای policy، assignment، scope، revoke/session و break-glass.
- [Delta آمادگی هویت/مجوز](IDENTITY_AUTHORIZATION_READINESS_DELTA_20260829_FA.md): افزایش پوشش طراحی از ۱۰ به ۱۱ ماژول بدون Runtime promotion.
- [Golden/UAT Delta هویت/مجوز](IDENTITY_AUTHORIZATION_GOLDEN_UAT_DELTA_20260829_FA.md): reuse صدوهشتادوچهار Case و ۴۲ Case تازه؛ مجموع ۲۲۶.
- [Playbook تخصصی هویت/مجوز](IDENTITY_AUTHORIZATION_EXPERT_PLAYBOOK_20260829_FA.md): هفت مسیر برای deny conflict، endpoint، admin، scope، session، partial receipt و SoD.
- [Delta ردیابی هویت/مجوز](IDENTITY_AUTHORIZATION_TRACEABILITY_RISK_DELTA_20260829_FA.md): پنج شاهد، ۱۰ نیازمندی، ۳۵ Link ماژولی و ۴۵ Link ریسک.
- [قرارداد Snapshot و تاریخ Organization Context](ORGANIZATION_CONTEXT_SNAPSHOT_DATE_CONTRACT_20260829_FA.md): شش فرمان، ContextSnapshot immutable و تفکیک چهار مفهوم تاریخ.
- [Delta آمادگی Organization Context](ORGANIZATION_CONTEXT_READINESS_DELTA_20260829_FA.md): افزایش پوشش طراحی از ۱۱ به ۱۲ ماژول بدون Runtime promotion.
- [Golden/UAT Delta Organization Context](ORGANIZATION_CONTEXT_GOLDEN_UAT_DELTA_20260829_FA.md): reuse شصت‌وچهار Case و ۳۵ Case تازه؛ مجموع ۹۹.
- [Playbook تخصصی Organization Context](ORGANIZATION_CONTEXT_EXPERT_PLAYBOOK_20260829_FA.md): هفت مسیر برای mixed context، date boundary، relation، lifecycle و publication.
- [Delta ردیابی Organization Context](ORGANIZATION_CONTEXT_TRACEABILITY_RISK_DELTA_20260829_FA.md): پنج شاهد، ۱۰ نیازمندی، ۳۵ Link ماژولی و ۴۵ Link ریسک.
- [قرارداد نسخه، Crosswalk و Merge دادهٔ پایه](MASTER_DATA_VERSION_CROSSWALK_MERGE_CONTRACT_20260829_FA.md): ۱۰ فرمان مقصد برای Aggregate نسخه‌دار، قرنطینهٔ تطبیق ضعیف و Merge برگشت‌پذیر.
- [Delta آمادگی دادهٔ پایه](MASTER_DATA_READINESS_DELTA_20260829_FA.md): افزایش پوشش طراحی از ۱۲ به ۱۳ ماژول بدون Runtime promotion.
- [Golden/UAT Delta دادهٔ پایه](MASTER_DATA_GOLDEN_UAT_DELTA_20260829_FA.md): reuse صد‌وچهارده Case و ۳۵ Case تازه؛ مجموع ۱۴۹.
- [Playbook تخصصی دادهٔ پایه](MASTER_DATA_EXPERT_PLAYBOOK_20260829_FA.md): هفت مسیر برای duplicate، sentinel، route code، child set، role، merge و PII.
- [Delta ردیابی دادهٔ پایه](MASTER_DATA_TRACEABILITY_RISK_DELTA_20260829_FA.md): پنج شاهد، ۱۰ نیازمندی، ۴۰ Link ماژولی و ۵۰ Link ریسک.
- [قرارداد Outcome/Retry انتشار و بازیابی Platform](PLATFORM_RELEASE_RECOVERY_OUTCOME_CONTRACT_20260829_FA.md): شش فرمان provider-neutral و جداسازی Commit کنترل از اثر خارجی.
- [Delta آمادگی Platform](PLATFORM_READINESS_DELTA_20260829_FA.md): تکمیل پوشش طراحی ۱۳→۱۴ بدون انتخاب Stack/RPO/RTO یا Runtime promotion.
- [Golden/UAT Delta Platform](PLATFORM_GOLDEN_UAT_DELTA_20260829_FA.md): ۴۲ Case طراحی‌شده و اجرا‌نشده برای شش سطح کنترل.
- [Playbook تخصصی Platform](PLATFORM_EXPERT_PLAYBOOK_20260829_FA.md): هفت مسیر Release/Retry/Restore/Failover/Secret/Transport.
- [Delta ردیابی Platform](PLATFORM_TRACEABILITY_RISK_DELTA_20260829_FA.md): پنج شاهد، ۱۰ نیازمندی، ۴۰ Link ماژولی و ۵۰ Link ریسک.
- [ممیزی تجمیعی غیرنهایی ادامه](VARANEGAR_24H_CONTINUATION_CONSOLIDATED_AUDIT_20260829_FA.md): پوشش طراحی ۱۴ ماژول، ۱۲۲۹ obligation، ۷۸ Playbook و شش Gate خارجی باقی‌مانده.
- [مرز Transaction/Mutation هویت و یکپارچگی](IDENTITY_INTEGRATION_TRANSACTION_MUTATION_BOUNDARY_20260829_FA.md): Target design برای هر ۱۲ فرمان موجود است، اما اثبات کامل Legacy/static، Runtime atomicity/effect parity، UAT و Owner approval صفر می‌ماند.
- [نقشهٔ اولویت Gateهای شواهد خارجی/Runtime](EXTERNAL_EVIDENCE_GATE_PRIORITY_MAP_20260829_FA.md): CG-06 ریشهٔ تصمیم، CG-05 مسیر موازی محدود، CG-01/02/03 مسیر Runtime ایزوله و CG-04 Gate نهایی UAT/مالک است.
- [قرارداد Evidence intake تصمیم‌های Platform](PLATFORM_DECISION_EVIDENCE_INTAKE_CONTRACT_20260829_FA.md): هشت Slot وابسته، Packet یازده‌فیلدی، Proposal≠Approval و Conflict/Dependency validation برای CG-06.
- [قرارداد Evidence intake Result/Formula parity گزارش‌ها](REPORT_PARITY_EVIDENCE_INTAKE_CONTRACT_20260829_FA.md): تفکیک ۱۱ Result owner، دو Command-only و هفت Routing/View و منع جایگزینی Receipt فرمان با Formula parity.
- [قرارداد Evidence intake Runtime authorization/scope](AUTHORIZATION_RUNTIME_EVIDENCE_INTAKE_CONTRACT_20260829_FA.md): چهارده Packet ماژولی، هشت سناریوی deny-first/server-side و وابستگی اجرای CG-01 به پذیرش CG-06.
- [قرارداد Evidence intake Fault-injection/Atomicity](ATOMICITY_FAULT_EVIDENCE_INTAKE_CONTRACT_20260829_FA.md): ۱۴ Packet، ۱۰ مرز خطا، Unknown outcome و تفکیک ۱۲ ماژول دارای شاهد از دو Target-design-only.
- [قرارداد Evidence intake Mutation/Result/External-effect parity](EFFECT_PARITY_EVIDENCE_INTAKE_CONTRACT_20260829_FA.md): ده لایهٔ اثر، Packet نوزده‌فیلدی و وابستگی CG-03 به CG-06/CG-02.
- [ماتریس یکپارچهٔ تحویل و پذیرش Gateهای بیرونی](EXTERNAL_GATE_HANDOFF_ACCEPTANCE_MATRIX_20260829_FA.md): ۸۴ واحد پذیرش، نه Edge وابستگی و ماشین وضعیت Hash-pinned برای شش Gate باز، بدون ارتقای Readiness.
- [Triage ایستای Graph تکثیر رسید POS](POS_REPLICATION_STATIC_GRAPH_RISK_TRIAGE_20260829_FA.md): تفکیک ۱۶۸ pseudo-table از ۱۷۹ unresolved، شناسایی ۱۱ SCC چرخه‌ای و مرز توسعه‌نیافتهٔ Graph بدون اتصال مجدد به DB.
- [ماتریس سیاست Formula/Grain گزارش](REPORT_FORMULA_GRAIN_POLICY_MATRIX_20260829_FA.md): یازده Result-owner، چهارده بُعد سیاست، ۱۲۳ الزام و Packet بیست‌فیلدی بدون ادعای Result parity.
- [Triage شکاف‌های Identity/Authorization](IDENTITY_AUTHORIZATION_GAP_TRIAGE_20260829_FA.md): تفکیک ۶۰ Endpoint به ۳۸ Mutation و ۲۲ Read، تمرکز ۵۸ Scope mismatch و هفت Lane/۱۳۹ واحد تعیین تکلیف.
- [Addendum Playbook تشخیصی مشترک](CROSS_GATE_DIAGNOSTIC_PLAYBOOK_ADDENDUM_20260829_FA.md): هشت سناریوی غیرتکراری برای Drift/Scope، POS graph، Formula/Grain و Packet supersession.
- [ممیزی Delta طراحی Golden/UAT](GOLDEN_UAT_DESIGN_DELTA_AUDIT_20260829_FA.md): جداسازی ۱۷۵ Case غیرتکراری و ارتقای lower bound طراحی از snapshot ۱۲۲۹ به ۱۴۰۴، بدون ادعای اجرا.
- [قرارداد Evidence intake نهایی Owner-UAT](TERMINAL_OWNER_UAT_EVIDENCE_INTAKE_CONTRACT_20260829_FA.md): پنج Gate و ۷۰ Packet/Slot بالادست، ۱۲۲۹ Obligation و ۱۴ Approval packet پیش از هر Readiness promotion.
- `CROSS_GATE_GOLDEN_UAT_REFINEMENT_MATRIX_20260829_FA.md`: ۳۲ قالب refinement غیرجمع‌شونده با Failure oracle و Receipt؛ lower bound طراحی ۱۴۰۴ بدون تورم شمارش.
- `GOLDEN_UAT_CROSSWALK_FEASIBILITY_MATRIX_20260829_FA.md`: بازسازی ۵۱۱ Case baseline، اثبات ۶۴ Exact-ID reuse و تفکیک ۳۰ تطبیق کاندید غیرقابل‌ارتقا.
- `DISTRIBUTION_TREASURY_SEMANTIC_ALIAS_CANDIDATE_PACKETS_20260829_FA.md`: ۳۰ Packet داوری Action+Kind با Auto-accept ممنوع و معادل‌بودن پذیرفته‌شدهٔ صفر.
- `UNMATCHED_GOLDEN_CASE_ALIAS_WORK_QUEUE_20260829_FA.md`: صف Case-level برای ۲۰۸ مورد unmatched در ۳۴ Action، با ۲۰۳ Alias و ۵ Kind/multiplicity gap.
- `FIVE_CASE_KIND_MULTIPLICITY_DISPOSITION_PACKETS_20260829_FA.md`: پنج Packet اولویت‌دار با ۱۳ reference پایه و پذیرش خودکار ممنوع.
- `ACTION_ALIAS_OWNER_EVIDENCE_PACKET_MATRIX_20260829_FA.md`: ۲۹ Packet Action-level برای ۲۰۳ Case با ۵۸ role assignment و ده فیلد پذیرش.
- `ACTION_ALIAS_HANDOFF_PRIORITY_MATRIX_20260829_FA.md`: صف risk-first پنج‌سطحی برای تحویل ۲۹ Packet/۲۰۳ Case، بدون owner assignment یا پذیرش ضمنی.
- `P0_ALIAS_BASELINE_CANDIDATE_SHORTLIST_20260829_FA.md`: جست‌وجوی baseline برای هفت Packet P0؛ شش Action reference/۹۲ Case reference، با چهار نتیجهٔ explicit-none و پذیرش صفر.
- `P0_ALIAS_SEMANTIC_EVIDENCE_COMPARATOR_20260829_FA.md`: مقایسهٔ ۶۶ جفت Case هم‌نوع برای شش کاندید P0؛ دو outcome برابر، صفر assertion/precondition/full match.
- `P0_FAILURE_INJECTION_ADJUDICATION_PACKETS_20260829_FA.md`: سه Packet برای ۲۰ جفت Failure Injection با ۱۸ stage عمومی‌به‌دقیق و پذیرش صفر.
- `P0_CONTROL_OUTCOME_VOCABULARY_ADJUDICATION_20260829_FA.md`: شش Packet/۴۶ جفت کنترلی؛ هشت Outcome جدید در برابر ۲۳ baseline و فقط دو label برابر.
- `P0_ASSERTION_EFFECT_FAMILY_GAP_MATRIX_20260829_FA.md`: دوازده خانوادهٔ اثر برای ۶۶ جفت؛ صفر family-set برابر و عدم‌تقارن ۲۹۴/۱۲۵ assignment.
- `P0_FINAL_EVIDENCE_GAP_STATUS_MATRIX_20260829_FA.md`: Packetization کامل هفت Action P0 با semantic disposition صفر و مسیر تصمیم ۴ Alias/New-Action + ۳ equivalence.
- `P1_ALIAS_BASELINE_CANDIDATE_SHORTLIST_20260829_FA.md`: جست‌وجوی baseline برای هشت Packet P1؛ چهار نگاشت صریح command-to-capability بانکی/۷۶ Case reference و چهار نتیجهٔ explicit-none، بدون پذیرش معنایی.
- `P1_ALIAS_SEMANTIC_EVIDENCE_COMPARATOR_20260829_FA.md`: مقایسهٔ ۵۵ جفت Case هم‌نوع برای چهار نگاشت بانکی P1؛ صفر precondition/outcome/assertion/full exact و پذیرش صفر.
- `P1_FAILURE_INJECTION_ADJUDICATION_PACKETS_20260829_FA.md`: چهار Packet/۱۹ جفت خطا؛ صفر stage دقیق، ۱۵ retry/convergence، ۱۶ no-partial و ۹ audit/outbox-sensitive.
- `P1_CONTROL_OUTCOME_VOCABULARY_ADJUDICATION_20260829_FA.md`: پنج Packet/۳۶ جفت کنترل؛ سه Outcome جدید در برابر ۱۶ baseline و صفر label/assertion/full exact.
- `P1_ASSERTION_EFFECT_FAMILY_GAP_MATRIX_20260829_FA.md`: دوازده خانواده برای ۵۵ جفت؛ صفر family-set برابر و عدم‌تقارن ۲۵۵/۸۰ assignment.
- `P1_FINAL_EVIDENCE_GAP_STATUS_MATRIX_20260829_FA.md`: Packetization کامل هشت Action P1 با disposition صفر و مسیر تصمیم ۴ Alias/New-Action + ۴ Semantic Equivalence.
- `P2_ALIAS_BASELINE_CANDIDATE_SHORTLIST_20260829_FA.md`: شش Packet P2؛ هفت Action reference/۸۷ Case/۳۸ kind-overlap و یک explicit-none، بدون پذیرش.
- `P2_ALIAS_SEMANTIC_EVIDENCE_COMPARATOR_20260829_FA.md`: هفت Candidate/۷۳ جفت هم‌نوع؛ دو outcome برابر ولی صفر precondition/assertion/full exact.
- `P2_FAILURE_INJECTION_ADJUDICATION_PACKETS_20260829_FA.md`: پنج Packet/۱۵ جفت خطا؛ stage برابر ۲، retry/no-partial برابر ۱۰/۱۰ و audit/outbox-sensitive برابر ۱۳.
- `P2_CONTROL_OUTCOME_VOCABULARY_ADJUDICATION_20260829_FA.md`: شش Packet/۵۸ جفت کنترل؛ شش Outcome جدید در برابر ۲۳ baseline، دو label برابر و صفر assertion/full exact.
- `P2_ASSERTION_EFFECT_FAMILY_GAP_MATRIX_20260829_FA.md`: دوازده خانواده برای ۷۳ جفت؛ صفر family-set برابر، ۹ بدون overlap و عدم‌تقارن ۴۲۰/۹۷ assignment.
- `P2_FINAL_EVIDENCE_GAP_STATUS_MATRIX_20260829_FA.md`: Packetization کامل شش Action P2 با disposition صفر و مسیر تصمیم ۱ Alias/New-Action + ۵ Semantic Equivalence.
- `P3_ALIAS_BASELINE_CANDIDATE_SHORTLIST_20260829_FA.md`: پنج Packet P3؛ شش Action reference/۳۱ Case/۲۶ kind-overlap، بدون پذیرش معنایی یا Result parity.
- `P3_ALIAS_SEMANTIC_EVIDENCE_COMPARATOR_20260829_FA.md`: شش Candidate/۳۸ جفت هم‌نوع؛ صفر precondition/outcome/assertion/full exact و صفر Result parity.
- `P3_FAILURE_INJECTION_ADJUDICATION_PACKETS_20260829_FA.md`: پنج Packet/۱۸ جفت خطا؛ صفر stage دقیق، recovery/unknown برابر ۱۸/۱۸ و حساسیت audit/file برابر ۱۵/۱۲.
- `P3_CONTROL_OUTCOME_VOCABULARY_ADJUDICATION_20260829_FA.md`: چهار Packet/۲۰ جفت کنترل؛ سه Outcome جدید، baseline بدون label صریح و صفر outcome/assertion/full exact.
- `P3_ASSERTION_EFFECT_FAMILY_GAP_MATRIX_20260829_FA.md`: شانزده خانواده برای ۳۸ جفت؛ صفر family-set برابر، عدم‌تقارن ۱۷۴/۶۷ و Result/Content parity صریح فقط ۰/۲.
- `P3_FINAL_EVIDENCE_GAP_STATUS_MATRIX_20260829_FA.md`: Packetization کامل پنج Action P3 با disposition و Result parity صفر و پنج مسیر تصمیم مشترک Effect/Result.
- `P4_ALIAS_BASELINE_CANDIDATE_SHORTLIST_20260829_FA.md`: سه Packet P4؛ سه reference/۱۴ Case/۱۰ kind-overlap، مالکیت ۳/۳ بسته ولی Result parity برابر صفر.
- `P4_ALIAS_SEMANTIC_EVIDENCE_COMPARATOR_20260829_FA.md`: سه Candidate/۱۴ جفت؛ صفر precondition/outcome/assertion/full exact و Result parity صفر.
- `P4_FAILURE_INJECTION_ADJUDICATION_PACKETS_20260829_FA.md`: دو Packet/شش جفت خطا؛ Candidate بانکی بدون failure pair و شش قرارداد quarantine/immutability/file.
- `P4_CONTROL_OUTCOME_VOCABULARY_ADJUDICATION_20260829_FA.md`: سه Packet/هشت جفت کنترل؛ سه Outcome جدید، baseline بدون label و صفر outcome/assertion/full exact.
- `P4_ASSERTION_EFFECT_FAMILY_GAP_MATRIX_20260829_FA.md`: هجده خانواده برای ۱۴ جفت؛ صفر family-set برابر، عدم‌تقارن ۶۴/۲۱ و Result/Content parity صریح ۰/۴.
- `P4_FINAL_EVIDENCE_GAP_STATUS_MATRIX_20260829_FA.md`: Packetization کامل سه Export P4 با disposition و Result parity صفر؛ یک Read candidate و دو Export-file.
- `ALIAS_CROSS_LANE_CLOSURE_ROUTE_MATRIX_20260829_FA.md`: تجمیع پنج Lane/۲۹ Packet/۲۰۳ Case با مسیرهای ۹/۱۲/۵/۳ و صفر semantic/result closure.
- `ALIAS_CROSS_LANE_EXTERNAL_EVIDENCE_INTAKE_QUEUE_20260829_FA.md`: صف intake چهارگروهی برای همان ۲۹ Packet/۲۰۳ Case با ۲۹۰ receipt و ۱۵۰ gate assignment؛ مالک نام‌گذاری‌شده، مدرک پذیرفته‌شده و readiness همگی صفر.
- `ALIAS_CROSS_LANE_EVIDENCE_RECEIPT_VALIDATION_MATRIX_20260829_FA.md`: تبدیل ۲۹۰ requirement به slotهای receipt با چهارده metadata، چهارده rejection code و ماشین وضعیت هشت‌حالته؛ همهٔ slotها فعلاً `MISSING`.
- `ALIAS_CROSS_LANE_ROLE_HANDOFF_WORKLIST_20260829_FA.md`: ۱۳ worklist نوع‌نقش با ۵۸ Packet، ۴۰۶ Case و ۵۸۰ receipt-slot assignment تکراری؛ هیچ مالک نام‌دار یا پذیرش ثبت نشده است.
- `P0_EXTERNAL_EVIDENCE_COLLECTION_ACTIVATION_PACKETS_20260829_FA.md`: هفت Packet P0/۴۹ Case با ۷۰ receipt slot، ۱۴ role و ۳۵ gate assignment؛ activation جمع‌آوری مدرک و اجرای عملیاتی هر دو فعلاً صفر/ممنوع.
- `P1_P4_EXTERNAL_EVIDENCE_ACTIVATION_SEQUENCE_MATRIX_20260829_FA.md`: sequencing چهار Lane/۲۲ Packet/۱۵۴ Case با ۲۲۰ receipt و ۱۱۵ gate assignment؛ هشت Packet P3/P4 صریحاً به CG-05 وابسته‌اند.
- `P3_P4_CG05_RESULT_PARITY_RECEIPT_MATRIX_20260829_FA.md`: هشت Packet/۵۶ Case، بیست بُعد parity و ۲۷ receipt زیر CG-05؛ شامل اصلاح پنج receipt چندکلاسهٔ per-item outcome.
- `P3_P4_FROZEN_FIXTURE_OUTPUT_MANIFEST_CONTRACT_20260829_FA.md`: هشت قرارداد/۵۶ Case با سه schema شانزده‌فیلدی و ۵۱۲ field assignment؛ Capture و مقدار واقعی همچنان صفر است.
- `P3_P4_RESULT_PARITY_MISMATCH_DIAGNOSTIC_PLAYBOOK_20260829_FA.md`: ده Playbook/۱۰۰ step با ۷۲ اتصال Packet و ۵۰۴ اتصال Case؛ Run، Repair و Promotion همچنان صفر است.
- `P3_P4_GOLDEN_UAT_RESULT_ADJUDICATION_PROMOTION_GUARD_20260829_FA.md`: هشت Packet/۵۶ Case، چهار Outcome، ۳۲ مسیر داوری و دوازده Guard؛ فقط Match مبتنی بر hash می‌تواند وارد بازبینی CG-05 شود و هیچ Closure خودکاری وجود ندارد.
- `TARGET_ERP_HASH_ONLY_COMPARISON_ADAPTER_CONTRACT_20260829_FA.md`: هشت Profile/۵۶ Case با schema ورودی/Receipt هجده‌فیلدی، دوازده مرحله canonicalization، شانزده Error و Idempotency پنج‌جزئی؛ Implementation و Run صفر.
- `TARGET_ERP_COMPARISON_ADAPTER_TEST_VECTOR_RECEIPT_VERIFICATION_20260829_FA.md`: دوازده بردار canonical مثبت و شانزده بردار خطای منفی برای هر هشت Profile، همراه قرارداد metadata اصالت Receipt، چرخهٔ کلید و rotation؛ هیچ کلید، امضا یا اجرای verification ثبت نشده است.
- `TARGET_ERP_COMPARISON_ADAPTER_OFFLINE_CONFORMANCE_ALGORITHM_PROVIDER_DECISION_20260829_FA.md`: اجرای محلی ۹۶ digest مصنوعی و ۱۲۸ lint taxonomy همراه Decision Record باز برای چهار الگوریتم، چهار Provider pattern، چهارده معیار و ده Gate؛ هیچ کلید، امضا یا اجرای عملیاتی ندارد.
- `TARGET_ERP_COMPARISON_ADAPTER_SYNTHETIC_NEGATIVE_REFERENCE_CODEC_20260829_FA.md`: Reference Codec خالص با هشت Baseline مثبت و ۱۲۸ Mutation منفی تک‌فیلدی؛ taxonomy و تقدم شانزده خطا اجرا می‌شود، ولی Operational adapter و Result parity صفر است.
- `P3_P4_ISOLATED_CAPTURE_AUTHORIZATION_REDACTION_GATE_20260829_FA.md`: شانزده Channel جدا برای Capture دو سمت هشت Packet، schemaهای ۲۴/۱۸ فیلدی، چهارده Gate و شش Role؛ همهٔ مجوزها، Captureها و Receiptها صفرند.
- `P3_P4_CAPTURE_TO_COMPARISON_EVIDENCE_HANDOFF_MATRIX_20260829_FA.md`: پل hash-only هشت Pair به هشت Adapter Profile، ۲۷ Receipt و بیست بُعد parity با ۵۴/۳۲۰ link و ۹۶ Gate assignment؛ همهٔ Handoffها بسته‌اند.
- `P3_P4_HASH_ONLY_EVIDENCE_CUSTODY_RETENTION_REVOCATION_20260829_FA.md`: پنجاه‌وچهار Custody requirement برای اتصال Channel/Receipt با schema بیست‌فیلدی، نه State، دوازده Transition، ۵۴۰ Gate و ۲۱۶ Role assignment؛ همه `MISSING` هستند.
- `P3_P4_EVIDENCE_INVALIDATION_REOPEN_PROPAGATION_20260829_FA.md`: دوازده علت Invalidation روی ۵۴ Custody requirement با ۶۴۸ assignment و ۲۸۵ Edge تا Handoff/Adapter/Receipt/Guard؛ رخداد مشاهده‌شده و reacceptance صفر است.
- `P3_P4_EVIDENCE_FRESHNESS_CLOCK_POLICY_REFERENCE_20260829_FA.md`: Evaluator ثابت و مصنوعی برای چهار نوع Artifact، هشت Outcome و دوازده Vector؛ ۴۸/۴۸ PASS و ۲۱۶ obligation واقعی همگی Missing هستند.
- `TARGET_ERP_BACKUP_RESTORE_REHEARSAL_EVIDENCE_20260829_FA.md`: قرارداد شاهد بازیابی برای ۱۴ ماژول مقصد با شش کلاس دارایی، دوازده سناریو و Gateهای fail-closed؛ هیچ Backup خوانده یا Restore اجرا نشده است.
- `TARGET_ERP_RESTORE_DEPENDENCY_WAVE_RECONCILIATION_20260829_FA.md`: تبدیل ۳۸ وابستگی چهارده ماژول به هفت موج Restore و ۱۵۲ تعهد تطبیق Edge؛ همهٔ موج‌ها و enablementها بسته‌اند.
- `TARGET_ERP_COMMAND_IDEMPOTENCY_OUTBOX_INBOX_CONVERGENCE_20260829_FA.md`: قرارداد یکنواخت ۴۹ فرمان مقصد برای Idempotency، Commit نامعلوم و همگرایی Outbox/Inbox؛ تمام اثبات‌های Runtime صفرند.
- `TARGET_ERP_TRANSACTION_OWNER_SAGA_COMPENSATION_20260829_FA.md`: مرز مالک تراکنش و چهار Pattern نامنتخب برای ۴۹ فرمان، همراه ۱۵۹ تعهد هماهنگی و قرارداد Compensation؛ Atomicity عملیاتی صفر است.
- `TARGET_ERP_COMMAND_AUTHORIZATION_SCOPE_DECISION_TRACE_20260829_FA.md`: دوازده بُعد Scope و چهارده Negative case برای هر ۴۹ فرمان با Decision Trace hash-only؛ Authorization عملیاتی صفر است.
- `TARGET_ERP_EVIDENCE_LOGGING_REDACTION_RETENTION_20260829_FA.md`: ده کانال Evidence، چهارده کلاس ممنوع و قرارداد hash-only/retention؛ هیچ Log یا دادهٔ واقعی خوانده نشده است.
- `TARGET_ERP_EVIDENCE_REDACTION_SYNTHETIC_REFERENCE_VALIDATOR_20260829_FA.md`: Validator خالص هشت‌فیلدی با ۱۰ Baseline و ۱۴۰ Mutation؛ ۱۵۰/۱۵۰ اجرای مصنوعی PASS و Runtime صفر است.
- `TARGET_ERP_MIGRATION_CUTOVER_SNAPSHOT_DELTA_RECONCILIATION_20260829_FA.md`: دوازده فاز Cutover و دوازده بُعد تطبیق برای چهارده ماژول؛ Snapshot/Delta/Cutover واقعی صفر است.
- `TARGET_ERP_ENVIRONMENT_ISOLATION_WRITE_FENCE_EXECUTION_TOKEN_20260829_FA.md`: چهار محیط و Execution Token بیست‌فیلدی برای ۴۹ فرمان؛ Legacy write و Production auto-promotion ممنوع است.
- `TARGET_ERP_RELEASE_PROMOTION_CHANGE_ROLLBACK_EVIDENCE_20260829_FA.md`: قرارداد دو گذار Sandbox→UAT و UAT→Production با digest یکسان، Change/Release/Rollback receipt و جداسازی پذیرش UAT از مجوز Production؛ هیچ انتشار عملیاتی ثبت نشده است.
- `TARGET_ERP_OBSERVABILITY_SLO_INCIDENT_EVIDENCE_20260829_FA.md`: دوازده کلاس Signal و چرخهٔ SLI/SLO/Alert/Incident برای ۱۴ ماژول؛ Process-up موفقیت نیست و هیچ telemetry واقعی خوانده نشده است.
- `TARGET_ERP_CONFIGURATION_POLICY_IMMUTABILITY_CHANGE_AUDIT_20260829_FA.md`: نسخه‌های immutable، precedence قطعی، audit تغییر و override محدود برای ۱۴ ماژول؛ هیچ configuration یا secret عملیاتی خوانده نشده است.
- `TARGET_ERP_DATA_PROVENANCE_READ_MODEL_REBUILD_20260829_FA.md`: authority/lineage و بازسازی deterministic برای Read modelهای ۱۴ ماژول؛ هیچ dataset یا rebuild عملیاتی انجام نشده است.
- `TARGET_ERP_RELEASE_PROMOTION_ROLLBACK_SYNTHETIC_REFERENCE_EVALUATOR_20260829_FA.md`: Evaluator خالص Promotion/Rollback با ۳ مسیر مثبت و ۲۳ Mutation منفی؛ ۲۶/۲۶ PASS و Runtime صفر.
- `TARGET_ERP_MONETARY_QUANTITY_TEMPORAL_SEMANTICS_20260829_FA.md`: Decimal/Currency/Rounding/Unit/Timezone/Fiscal/Calendar semantics برای ۱۴ ماژول؛ هیچ مقدار عملیاتی خوانده نشده است.
- `TARGET_ERP_MONETARY_TEMPORAL_SYNTHETIC_REFERENCE_EVALUATOR_20260829_FA.md`: Reference خالص Decimal/Allocation/Conversion/Reversal/Temporal با ۳۴/۳۴ vector PASS؛ هیچ دادهٔ واقعی ندارد.
- `TARGET_ERP_OPTIMISTIC_CONCURRENCY_VERSION_FENCING_20260829_FA.md`: expected-version/CAS/sequence/lease/fencing برای ۴۹ فرمان؛ Idempotency جای concurrency نیست و Runtime صفر است.
- `TARGET_ERP_CONCURRENCY_SYNTHETIC_REFERENCE_EVALUATOR_20260829_FA.md`: state evaluator خالص Replay/Unknown/Retry/Version/CAS/Sequence/Fence با ۱۶/۱۶ vector PASS.
- `TARGET_ERP_MASTER_DATA_IDENTITY_DEDUP_MERGE_SUPERSESSION_20260829_FA.md`: scoped identity، dedup، merge/unmerge، supersession و cross-reference برای ۱۴ ماژول؛ PII read صفر.
- `TARGET_ERP_CAPACITY_TIMEOUT_BACKPRESSURE_DEGRADATION_20260829_FA.md`: ظرفیت، timeout/retry budget، queue/backpressure و degraded-mode برای ۱۴ ماژول؛ هیچ load عملیاتی ندارد.
- `TARGET_ERP_CAPACITY_BUDGET_SYNTHETIC_REFERENCE_EVALUATOR_20260829_FA.md`: Evaluator خالص timeout/retry/backpressure/degradation/recovery با ۱۹/۱۹ vector PASS.
- `TARGET_ERP_DOCUMENT_NUMBERING_SERIES_VOID_ROLLOVER_20260829_FA.md`: Scope/Series/Reserve/Commit/Gap/Void/Offline/Rollover برای ۱۴ ماژول؛ شمارهٔ عملیاتی خوانده نشده است.
- `TARGET_ERP_NUMBERING_SYNTHETIC_REFERENCE_EVALUATOR_20260829_FA.md`: state evaluator خالص Draft/Reserve/Commit/Replay/Void/Offline/Rollover با ۲۰/۲۰ vector PASS.
- `TARGET_ERP_FILE_ATTACHMENT_IMPORT_EXPORT_INTEGRITY_20260829_FA.md`: path/type/archive/malware/DLP/quarantine/download/retention برای فایل‌های ۱۴ ماژول؛ هیچ فایل واقعی خوانده نشده است.
- `TARGET_ERP_FILE_METADATA_SYNTHETIC_REFERENCE_VALIDATOR_20260829_FA.md`: اعتبارسنج خالص و metadata-only برای تقدم fail-closed مسیر/اندازه/hash/type/archive/scan/DLP/download/derivative/export/retention؛ ۱۹/۱۹ بردار مصنوعی و صفر خواندن بدنهٔ فایل.
- `TARGET_ERP_FISCAL_PERIOD_CLOSE_REOPEN_ADJUSTMENT_LOCK_20260829_FA.md`: قرارداد قفل دوره، Soft/Hard close، Reopen کمینه و منقضی‌شونده، Adjustment/Reversal و Reclose با reconciliation و supersession؛ بدون خواندن یا ثبت عملیاتی.
- `TARGET_ERP_FISCAL_PERIOD_SYNTHETIC_REFERENCE_EVALUATOR_20260829_FA.md`: evaluator خالص برای تقدم Scope/Version/State/Lock/Unknown و مسیرهای Close/Adjustment/Reopen/Reclose؛ ۲۳/۲۳ بردار مصنوعی و صفر اجرای ERP.
- `TARGET_ERP_INTEGRATION_WEBHOOK_MESSAGE_AUTHENTICITY_REPLAY_DEADLETTER_20260829_FA.md`: قرارداد TLS/signature/schema/scope/replay/idempotency/order/retry/quarantine/dead-letter/redrive برای integrationهای ۱۴ ماژول؛ بدون endpoint یا پیام عملیاتی.
- `TARGET_ERP_INTEGRATION_MESSAGE_SYNTHETIC_REFERENCE_EVALUATOR_20260829_FA.md`: evaluator خالص تقدم authenticity/scope/replay/dedup/order/unknown/retry/DLQ/redrive؛ ۲۹/۲۹ بردار مصنوعی و صفر I/O شبکه.
- `TARGET_ERP_OUTPUT_PRINT_PDF_LABEL_BARCODE_RENDERING_INTEGRITY_20260829_FA.md`: قرارداد template/snapshot/renderer/font/RTL/layout/barcode/QR/PDF/signature/print/reprint برای خروجی ۱۴ ماژول؛ بدون render یا چاپ عملیاتی.
- `TARGET_ERP_OUTPUT_RENDERING_SYNTHETIC_REFERENCE_EVALUATOR_20260829_FA.md`: evaluator خالص تقدم template/data/font/RTL/layout/barcode/PDF/copy/print؛ ۲۷/۲۷ بردار مصنوعی و صفر rendering.
- `TARGET_ERP_PRIVACY_CONSENT_LEGAL_BASIS_DATA_SUBJECT_RIGHTS_20260829_FA.md`: قرارداد jurisdiction-neutral برای inventory/purpose/basis/notice/consent/rights/retention/sharing/profiling/breach؛ بدون PII یا اقدام عملیاتی.
- `TARGET_ERP_PRIVACY_RIGHTS_SYNTHETIC_REFERENCE_EVALUATOR_20260829_FA.md`: evaluator jurisdiction-neutral برای تقدم basis/notice/withdrawal/rights/hold/sharing/breach/disposition؛ ۳۰/۳۰ بردار مصنوعی و صفر PII.
- `TARGET_ERP_APPROVAL_DELEGATION_ESCALATION_SOD_BREAKGLASS_20260829_FA.md`: قرارداد threshold/quorum/SoD/delegation/substitution/escalation/break-glass/invalidation/execution-token؛ بدون user یا workflow عملیاتی.
- `TARGET_ERP_APPROVAL_SYNTHETIC_REFERENCE_EVALUATOR_20260829_FA.md`: evaluator خالص delegation/SoD/quorum/escalation/break-glass/token؛ ۲۹/۲۹ بردار مصنوعی و صفر workflow action.
- `TARGET_ERP_TAX_FISCALIZATION_EINVOICE_CLEARANCE_20260829_FA.md`: قرارداد jurisdiction-neutral برای regime/registration/schema/tax/rounding/number/signature/submission/correction/archive/reconciliation؛ بدون ارسال عملیاتی.
- `TARGET_ERP_TAX_FISCALIZATION_SYNTHETIC_REFERENCE_EVALUATOR_20260829_FA.md`: evaluator jurisdiction-neutral تقدم fiscal identity/signature/provider/contingency/correction؛ ۲۹/۲۹ بردار مصنوعی و صفر submission.
- `TARGET_ERP_INVENTORY_LOT_SERIAL_EXPIRY_COSTING_VALUATION_20260829_FA.md`: قرارداد item/UOM/lot/serial/state/expiry/negative-stock/cost-layer/landed-cost/transfer/count/revaluation/GL؛ بدون خواندن انبار عملیاتی.
- `TARGET_ERP_INVENTORY_SYNTHETIC_REFERENCE_EVALUATOR_20260829_FA.md`: evaluator خالص scope/lot/expiry/negative/cost-layer/transfer/count/revalue/reconcile؛ ۲۸/۲۸ بردار مصنوعی و صفر mutation.
- `TARGET_ERP_PROCURE_TO_PAY_THREE_WAY_MATCH_20260901_FA.md`: قرارداد design-only خرید تا پرداخت؛ سه‌طرفه‌سازی PO/receipt-or-service/invoice، tolerance، duplicate، return/debit-note، hold/release، payment eligibility و reconciliation.
- `TARGET_ERP_PROCURE_TO_PAY_SYNTHETIC_REFERENCE_EVALUATOR_20260901_FA.md`: evaluator خالص P2P با ۳۱/۳۱ بردار مصنوعی، ۲۴ outcome متمایز و صفر runtime/mutation.
- `TARGET_ERP_ORDER_TO_CASH_CREDIT_COLLECTIONS_20260901_FA.md`: قرارداد design-only فروش تا وصول؛ credit exposure، fulfillment، billing، cash allocation، collection/aging/ECL، revenue و AR/GL reconciliation.
- `TARGET_ERP_ORDER_TO_CASH_SYNTHETIC_REFERENCE_EVALUATOR_20260901_FA.md`: evaluator خالص O2C با ۲۸/۲۸ بردار مصنوعی، ۲۴ outcome متمایز و صفر runtime/mutation.
- `TARGET_ERP_WORKFORCE_TIME_PAYROLL_20260901_FA.md`: قرارداد design-only workforce/time/payroll؛ attendance/leave، gross-to-net، statutory، retro/off-cycle، payslip/privacy، payment و payroll/GL.
- `TARGET_ERP_PAYROLL_SYNTHETIC_REFERENCE_EVALUATOR_20260901_FA.md`: evaluator خالص payroll با ۲۶/۲۶ بردار مصنوعی، ۱۹ outcome متمایز و صفر خواندن داده پرسنلی یا runtime.
- `VARANEGAR_10H_CONTINUATION_HANDOFF_20260901_FA.md`: نقطه تحویل قابل‌انتقال؛ resume checkpoint، فرمان freshness/settle، خانواده‌های تکمیل‌شده، مرز حقیقت و backlog مجاز.
- `TARGET_ERP_FIXED_ASSET_LIFECYCLE_DEPRECIATION_20260901_FA.md`: قرارداد design-only دارایی ثابت؛ acquisition/CIP/component، depreciation، impairment/revaluation، transfer/disposal و asset-register/GL.
- `TARGET_ERP_FIXED_ASSET_SYNTHETIC_REFERENCE_EVALUATOR_20260901_FA.md`: evaluator خالص دارایی ثابت با ۲۶/۲۶ بردار، ۲۰ outcome متمایز و صفر runtime/mutation.
- `TARGET_ERP_PROJECT_JOB_COSTING_REVENUE_BILLING_20260901_FA.md`: قرارداد طراحی چرخهٔ پروژه/WBS، بودجه و تعهد، هزینه، پیشرفت، صورتحساب، شناسایی درآمد و تطبیق پروژه/GL.
- `TARGET_ERP_PROJECT_JOB_COSTING_SYNTHETIC_REFERENCE_EVALUATOR_20260901_FA.md`: ارزیاب خالص پروژه با ۲۴ بردار ثابت و تقدم fail-closed.
- `TARGET_ERP_DOMAIN_COVERAGE_GAP_REGISTER_20260901_FA.md`: inventory بازتولیدپذیر ۵۴ قرارداد مقصد و backlog شش دامنه با اولویت ۰/۴/۲ برای P0/P1/P2.
- `TARGET_ERP_CONTRACT_PORTFOLIO_INVARIANT_AUDIT_20260901_FA.md`: meta-audit سبد ۵۴ قرارداد؛ شناسه/manifest/safety/runtime/readiness/lower-bound، با صفر finding.
- `TARGET_ERP_MANUFACTURING_MRP_SHOPFLOOR_QUALITY_20260901_FA.md`: قرارداد design-only ساخت؛ BOM/routing/MRP/order/material/shop-floor/genealogy/quality/WIP/costing.
- `TARGET_ERP_MANUFACTURING_SYNTHETIC_REFERENCE_EVALUATOR_20260901_FA.md`: evaluator خالص ساخت با ۲۶/۲۶ بردار، ۱۹ outcome و صفر runtime/mutation.
