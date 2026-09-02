# کپسول تحویل ادامه ۱۰ساعته شناخت وارانگار

این سند نقطه‌ی ورود سیستم بعدی است. ریشه دانش `G:\NeginAI` و checkpoint بالایی `artifacts/varanegar_analysis/varanegar_10h_continuation_handoff_checkpoint_20260901.json` است. Artifact همراه، شمارش JSONها، graph قابل‌دسترسی، hash/size manifestها، نتیجه رسمی تست‌ها، مرز حقیقت و backlog را به‌صورت machine-readable نگه می‌دارد.

برای انتخاب کار بعدی، ابتدا `artifacts/varanegar_analysis/varanegar_target_erp_domain_coverage_gap_register_20260901.json` خوانده شود؛ این register پوشش ۵۴ قرارداد و شش شکاف اولویت‌بندی‌شده را ثبت می‌کند. شکاف P0 پروژه/بهایابی کار در بستهٔ طراحی و ارزیاب مصنوعی بسته شده و شکاف‌های باقی‌مانده P1/P2 هستند.

سلامت سبد با `artifacts/varanegar_analysis/varanegar_target_erp_contract_portfolio_invariant_audit_20260901.json` سنجیده می‌شود؛ آخرین معیار پذیرش آن ۵۴/۵۴ قرارداد و صفر finding است.

در این ادامه، زنجیره Golden/UAT result-parity و Promotion Guard، comparison adapter آفلاین، قراردادهای ایمنی/تاب‌آوری/تراکنش/مهاجرت/release/observability/configuration/provenance، semantics/concurrency/master-data/numbering/files/fiscal/integration/output/privacy/approval/tax/inventory و چرخه‌های جدید P2P، O2C، Payroll و Fixed Asset به قرارداد، تست، سند و checkpoint متصل شدند. قراردادهای دارای منطق تصمیم با vectorهای مصنوعی مستقل نیز پوشش داده شده‌اند.

برای کنترل تازگی از ریشه پروژه اجرا شود:

```powershell
.venv\Scripts\python.exe scripts/windows/audit_varanegar_checkpoint_freshness.py artifacts/varanegar_analysis/varanegar_10h_continuation_handoff_checkpoint_20260901.json
.venv\Scripts\python.exe scripts/windows/audit_varanegar_checkpoint_freshness.py artifacts/varanegar_analysis/varanegar_10h_continuation_handoff_checkpoint_20260901.json --all-checkpoints
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/windows/settle_varanegar_analysis_chain_20260831.ps1
```

مرز حقیقت تغییر نکرده است: اطمینان static/persisted بالا و vectorهای مصنوعی قابل‌بازتولیدند، اما runtime result parity، business-owner acceptance، provider selection، command-ready و pilot-ready ثابت نشده‌اند. ادامه عملیاتی فقط با مجوز جدا، محیط ایزوله، fixture تصویب‌شده و evidence receipt مجاز است.

حالت recursiveِ `--all-checkpoints` علاوه بر مسیر رأس، checkpointهای orphan معتبر در زیرپوشه‌ها را نیز ممیزی می‌کند؛ آخرین اجرای آن ۲۵۰ checkpoint، ۷۶۹ JSON و صفر stale/invalid را پوشش داد.
