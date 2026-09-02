# قرارداد Document Numbering، Series، Void و Rollover مقصد

دوازده بُعد Numbering برای چهارده ماژول ۱۶۸ assignment و دوازده Stage نیز ۱۶۸ assignment دارد. Series policy و Allocation receipt هرکدام بیست‌ودو، Void receipt هجده و Rollover receipt بیست فیلد دارد.

شانزده Failure case تعداد ۲۲۴، بیست Gate تعداد ۲۸۰ و شش Role تعداد ۸۴ assignment دارد. شمارهٔ انسانی surrogate ID نیست؛ Scope باید Tenant/Organization/Fiscal/Document type و Series version را مشخص کند.

Gap پنهان یا reuse نمی‌شود و Void receipt immutable می‌خواهد. Preview/Draft/Print پیش از Stage مصوب شماره نمی‌گیرد؛ Unknown commit شمارهٔ دوم نمی‌سازد و Offline range باید non-overlap، زمان‌دار و reconciled باشد.

هیچ Document number/Series/Gap/Identifier عملیاتی خوانده و هیچ Reserve/Commit/Void/Offline/Rollover اجرا نشد. Policy/Receipt/Reconciliation/Approval/Readiness همگی صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت است.
