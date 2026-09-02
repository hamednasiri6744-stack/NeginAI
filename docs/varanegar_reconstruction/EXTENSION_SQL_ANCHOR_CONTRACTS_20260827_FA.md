# قرارداد SQL Anchor افزونه‌های مادی

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS — ۴۸ Anchor برای ۱۲ Capability؛ دو Link اجرای استاتیک قطعی**

از میان ۱۳۲ Object candidate، فقط ۴۸ Anchor لازم برای Freeze قرارداد داده انتخاب
شد: ۱۷ Table، ۳۰ Stored procedure و یک View. برای آن‌ها ۲۶۶ Column، ۱۵۰
Parameter، ۵۱ FK، ۳۲ Trigger و ۲۰۷ Dependency بدون ذخیره Definition ثبت شد.

## پوشش Capability

| Capability | Anchorهای اصلی | Gate مقصد |
|---|---|---|
| Stock/accounting access | چهار Scope table و UserDC/UserSale Get/Save | Deny-by-default، SoD، delegated scope |
| Article template | `ArticleTemplate`، Before/GetList | Version، historical consumer، balanced-entry test |
| General config | Current، History، GetValue/GetList | typed allowlist، current/history reconciliation |
| Web service | `usp_sdsnet_WebConfigSetting_Save` | Vault، egress allowlist، rotation |
| Charge device | Table، next number، list/confirm | device/cashier/safe crosswalk و open-session guard |
| Instalment method | دو Table و دو GetList | schedule fixture و effective-version overlap |
| Linear discount | `POSLineDiscount`، validation/get/list | حذف `MAX(Id)+1` و price trace |
| POS safe | View و open/list procedure | scope، sensitive-balance capability، watermark |
| POS session | `usp_ReplicateSalesReceipt` | idempotency، per-receipt quarantine، amount/count recon |
| Subscriber | Table/group/code/credit/list | PII، duplicate/merge، identity crosswalk |
| Dealer day path | سه Procedure Save/List | اثبات Base Save path، conflict rule، offline ack |
| Visit template | چهار NGT Table و چهار Procedure | version، cardinality recon، client watermark |

## درجه اثبات

فقط دو Anchor نام SQL را مستقیماً در IL Allowlist‌شده دارند:

1. `dbo.POSLineDiscount` در `GenerateLinearDiscountId`؛
2. `dbo.usp_ReplicateSalesReceipt` در `POSSessionAdapter.Send`.

۴۶ Anchor دیگر Candidateهای قوی مبتنی بر نام Capability، Catalog و Dependency
هستند، اما هنوز Runtime execution آن‌ها اثبات نشده است. این تفکیک در Artifact با
`runtime_execution_proven` حفظ شده و نباید در گزارش‌های بعدی حذف شود.

## قواعد استفاده

- Column/Parameter/FK/Trigger این قرارداد برای طراحی Schema و Migration test است،
  نه اجازه Import یا Write؛
- `row_count_metadata` Watermark مهاجرت نیست و Clone ممکن است عقب باشد؛
- Trigger و Procedure فقط Fingerprint/Dependency دارند و اجرا نشده‌اند؛
- Freeze نهایی هر Capability به Gateهای ثبت‌شده، Role UAT و Owner acceptance
  وابسته است.

Artifact:
`artifacts/varanegar_analysis/ui/varanegar_extension_sql_anchor_contracts_20260827.json`

Builder:
`scripts/windows/build_varanegar_extension_sql_anchor_contracts.py`
