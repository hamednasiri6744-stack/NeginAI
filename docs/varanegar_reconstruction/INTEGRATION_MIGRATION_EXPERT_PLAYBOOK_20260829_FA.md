# Playbook تخصصی Integration/Migration — ۲۰۲۶۰۸۲۹

هفت Playbook برای Package نامعتبر یا خارج Scope، Gap/Fork/تکرار، Commit با Ack نامعلوم، Partial POS Batch، NGT History/Crosswalk mismatch، Compensation تکراری و Migration rerun/mixed snapshot ساخته شد.

قاعدهٔ ثابت این است که Transport، Apply، Reconcile و Acknowledge یک State نیستند. هر نتیجهٔ نامعلوم پیش از Retry قرنطینه می‌شود و هیچ Replay، Ack synthesis، Crosswalk repair، Compensation، Import resume یا Source write-back در فرایند تشخیص انجام نمی‌شود.
