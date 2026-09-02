# قرارداد تطبیق و Quarantine بین‌ماژولی — ۱۴۰۵/۰۶/۰۷

حسابداری، خزانه و توزیع با ۲۲ فرمان شناخته‌شده به یک schema مشترک تطبیق متصل شدند. هفت edge عبارت‌اند از command→receipt، sale→accounting source، source→batch/journal، distribution→sale link، distribution→exit، exit→type-60 voucher و NGT payment→back-office receipt.

قرارداد بر identity، scope، version، ordered history و durable effect تکیه دارد. دو استنتاج صریحاً ممنوع‌اند: `MAX(id)` به‌عنوان وضعیت جاری و برابری مبلغ NGT payment با receipt. از ۲۷۴ crosswalk پرداخت/receipt، دامنهٔ مبلغ در ۲۷۰ مورد متفاوت است؛ پس identity و allocation باید مستقل کنترل شوند.

نتیجهٔ تطبیق یکی از `MATCHED`، `EXPECTED_ABSENCE`، `PARTIAL_DURABLE_EFFECT`، `IDENTITY_CONFLICT`، `VERSION_FORK` یا `UNPROVEN` است. outcome ناشناخته، fork pointer/history، shell شماره‌دار خالی، source/target-only، crosswalk متعارض، scope/version mismatch و نبود delete/audit evidence به quarantine می‌روند. اجرای runtime و owner approval صفر است.
