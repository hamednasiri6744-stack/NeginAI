# Comparator معنایی Action Aliasهای P2 ـ ۲۰۲۶-۰۸-۲۹

هفت Candidate action به ۷۳ جفت Case هم‌نوع تبدیل شد؛ یک کاندید `received_cheque.validate_transition` هیچ kind قابل‌مقایسه‌ای ندارد. توزیع جفت‌ها: Authorization هفت، Concurrency یازده، Failure Injection پانزده، Idempotency ده، Scope دو، Success شش و Validation بیست‌ودو.

در baselineهای schema قدیمی، category با نگاشت صریح نرمال و `expected[]` فقط assertion-list تلقی شد، نه Outcome label. exact precondition صفر، exact outcome دو، exact assertion-list صفر و full exact صفر است. دو outcome برابر در family چک بدون برابری شرط و assertion قابل پذیرش نیستند.

هیچ Candidate/Pair پذیرفته یا اجرا نشده و lower bound طراحی ۱۴۰۴، Risk/Trace برابر ۸۴/۳۴۳ و readiness صفر باقی مانده است.
