# اطلس فرایندهای انتها‌به‌انتهای ERP نگین

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS برای طراحی و ردیابی؛ صفر فرایند آماده‌ی اجرا/پایلوت/Production**

شناخت فرم‌ها، Workflowها، State machineها، Reportها، Golden caseها و Riskها در
ده مرز فرایندی مقصد کنار هم قرار گرفت. این نام‌گذاری مرز طراحی ERP نگین است و
ادعا نمی‌کند خود وارانگار دقیقاً همین Bounded contextها را نام‌گذاری کرده است.

| فرایند | Workflow | Report assignment | State machine | Golden case | ریسک باز |
|---|---:|---:|---:|---:|---:|
| Foundation/Governance | 1 | 0 | 0 | 119 | 15 |
| Master/Pricing | 0 | 2 | 0 | 196 | 9 |
| Order-to-Sale | 4 | 4 | 0 | 46 | 31 |
| Inventory-to-Delivery | 8 | 6 | Distribution | 153 | 30 |
| Return-to-Credit | 0 | 1 | 0 | 31 | 30 |
| Collection/Received cheque | 5 | 2 | Received cheque | 19 | 30 |
| Procure-to-Pay | 2 | 1 | Payable cheque | 50 | 26 |
| Ledger Posting | 0 | 0 | 0 | 18 | 27 |
| POS Session Replication | 0 | 0 | 0 | 70 | 39 |
| Reporting/Migration | 0 | 20 | 0 | 175 | 33 |

تمام ۲۰ Workflow دقیقاً به یک فرایند اصلی، هر سه State machine دقیقاً به یک
فرایند و هر ۲۰ Report حداقل به Reporting/Migration متصل شدند. چون Report می‌تواند
هم Cross-domain و هم جزئی از یک فرایند باشد، ۳۶ Assignment گزارش داریم.
Goldenهای `master` و `foundation` نیز اکنون صریحاً در تفکیک Source هر فرایند
شمرده می‌شوند و جمع تفکیک Source با `target_golden_case_count` برابر است.
هر ۸۷۷ Case دقیقاً به یک فرایند نگاشت شده و مورد بدون فرایند یا چندمالکیتی صفر
است؛ این قاعده در Builder و تست به‌صورت Invariant نگه‌داری می‌شود.

## ترتیب منطقی ساخت

1. Foundation/Governance و Master/Pricing؛
2. Read models و Reporting بدون Write؛
3. Order-to-Sale و Ledger با Commandهای محدود و Reconciliation؛
4. Inventory-to-Delivery؛
5. Return/Collection و State machineهای چک؛
6. Procure-to-Pay؛
7. POS replication فقط پس از Snapshot/hash/Quarantine و Fault injection.

## نکته‌ی اصلی

فرم به‌تنهایی واحد تحویل نیست. مثلاً «ارسال توزیع» باید با خروج انبار، Cardex،
مسیر معکوس و تاریخچه reconcile شود؛ «مرجوعی» باید Stock/Credit/Accounting را
یا باهم قطعی کند یا صریح Quarantine شود؛ و POS یک Batch چنددامنه‌ای است، نه یک
Save ساده.

Artifact:
`artifacts/varanegar_analysis/ui/negin_erp_end_to_end_process_atlas_20260827.json`

Builder:
`scripts/windows/build_negin_erp_end_to_end_process_atlas.py`
