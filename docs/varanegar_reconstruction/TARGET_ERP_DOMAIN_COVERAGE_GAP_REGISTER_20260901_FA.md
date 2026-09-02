# دفتر پوشش و شکاف دامنه‌های ERP مقصد

این بسته تمام Artifactهای `varanegar_target_erp_*contract*.json` را به‌صورت بازتولیدپذیر inventory و PASS بودن آن‌ها را کنترل می‌کند. پس از بسته Project/Job Costing، inventory شامل ۵۴ قرارداد است. وجود قرارداد به معنی قابلیت runtime نیست؛ accepted operational receipt، command-ready و pilot-ready همچنان صفر هستند.

شکاف P0 باقی نمانده است. P1 شامل Budget/Planning، Intercompany/Consolidation، Lease Accounting و Service/Field-Service/Warranty/Maintenance است. P2 شامل CRM pre-order و certified analytics/regulatory reporting است.

هر شکاف dependency و حداقل بسته لازم دارد: قرارداد، مرجع مصنوعی در صورت وجود منطق تصمیم، سند فارسی، تست و checkpoint. اولویت‌بندی architectural sequencing است، نه تصویب business owner یا مجوز UAT.
