# Playbook تخصصی و قرارداد ERP حسابداری — ۱۴۰۵/۰۶/۰۷

پنج رخداد تخصصی پوشش داده شد: خطای transfer با اثر durable، اختلاف pointer/history، shell شماره‌دار بدون line، نتیجهٔ مبهم Manual Save و اشتباه گرفتن UI-close با لغو مالی.

روش مشترک: correlation/scope/version بدون PII، کنترل drift، read-back pointer/history/effect، مقایسه outcome با Commit، طبقه‌بندی چهارحالته و توقف پیش از repair. سه برداشت صریحاً رد می‌شوند: «متن خطا یعنی rollback»، «MAX(history) یعنی وضعیت جاری» و «بستن فرم یعنی لغو مالی».

قرارداد ERP مقصد state machine، command schema، deny-first authorization، unit of work، idempotency، typed outcome، immutable lineage و quarantine را تعریف می‌کند. Acceptance نیازمند اجرای ۴۲ case در محیط ایزوله و تأیید مالک است.
