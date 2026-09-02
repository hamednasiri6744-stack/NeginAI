# ماتریس Sequencing فعال‌سازی شواهد بیرونی P1 تا P4 — ۲۰۲۶-۰۸-۲۹

این ماتریس ۲۲ Packet و ۱۵۴ Case باقیماندهٔ P1 تا P4 را در چهار Lane risk-first مرتب می‌کند. ترتیب، اولویت review است؛ مجوز جمع‌آوری یا اجرای عملیاتی نیست و دریافت شواهد redacted می‌تواند پس از prerequisiteهای مشترک به‌صورت موازی انجام شود.

## توزیع Laneها

- **P1:** هشت Packet/۵۶ Case، ۸۰ receipt، ۱۶ role و ۴۰ gate assignment؛
- **P2:** شش Packet/۴۲ Case، ۶۰ receipt، ۱۲ role و ۳۰ gate assignment؛
- **P3:** پنج Packet/۳۵ Case، ۵۰ receipt، ۱۰ role و ۳۰ gate assignment؛
- **P4:** سه Packet/۲۱ Case، ۳۰ receipt، شش role و ۱۵ gate assignment.

جمع کل ۲۲۰ receipt slot، ۴۴ role assignment از ۱۲ نوع نقش، ۱۱۵ gate assignment و ۱۵۴ prerequisite assignment است. هفده Packet کاندیددار و پنج Packet explicit-none هستند؛ مسیرها ۵ Alias/New Action، ۹ Semantic Equivalence، ۵ Report Effect+Result و ۳ Export Effect+Result است.

## مرز CG-05

هر هشت Packet P3/P4 الزام CG-05 دارد. موفقیت فرمان چاپ، ساخته‌شدن فایل یا عدم‌خطای export نمی‌تواند جای frozen-fixture value/rowset/render/file parity را بگیرد. P4 می‌تواند برای جمع‌آوری مدرک موازی باشد، ولی closure آن از Result parity مستقل عبور نمی‌کند.

وضعیت فعلی همهٔ ۲۲ Packet: owner و receipt پذیرفته‌شده صفر، activation صفر، route decision صفر، اجرا/owner approval/readiness صفر. lower bound طراحی ۱۴۰۴ ثابت است.

Artifact:

`artifacts/varanegar_analysis/varanegar_p1_p4_external_evidence_activation_sequence_matrix_20260829.json`

Checkpoint:

`artifacts/varanegar_analysis/varanegar_p1_p4_external_evidence_activation_sequence_checkpoint_20260829.json`
