# Semantic footprint ماژول‌های SQL حساس Extension

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS — هشت Module، تعریف ذخیره‌شده صفر، اجرای SQL صفر**

تعریف هشت Stored procedure حساس فقط در حافظه Clone فقط‌خواندنی تحلیل شد. Comment
و String literal پیش از Lexical parsing Mask شدند؛ Artifact فقط Hash/Length،
Parameter، Dependency، Operation candidate و Signalهای ساختاری دارد.

## خلاصه

- هشت Module از هشت مورد پیدا شد؛
- ۴۲ Parameter و ۱۱۴ Dependency؛
- ۳۱ Lexical mutation operation و ۱۱ Target حل‌شده؛
- پنج Module دارای Begin/Commit صریح؛
- یک Module دارای Error propagation صریح؛
- Dynamic SQL signal در متن Mask‌شده صفر؛
- Definition، String literal، Credential و Business row ذخیره‌شده صفر.

## `usp_ReplicateSalesReceipt`

این Procedure با سه پارامتر سال مالی، کاربر و `PSessionId`، یک Orchestrator
چنددامنه‌ای است:

- ۶۶ Dependency؛
- ۱۷ Operation candidate: پنج Insert، یازده Update و یک Delete؛
- Targetهای حل‌شده شامل `Acc.tblPayments`، `POrderXBO`، `PRetSaleXBO`،
  `PSession`، `tblPayWithPaymentRelation`، `inv.tblVocherHdr` و `PCredit`؛
- Transaction Begin/Commit/Rollback، TRY/CATCH و RAISERROR صریح؛
- چهار Cursor، ۲۶ EXEC token و ۱۳۳ Temp-table token.

این شاهد ثابت می‌کند Receipt replication یک CRUD ساده Session نیست. مقصد باید
آن را Batch orchestrator با Crosswalk هر رسید، Idempotency، Per-item quarantine،
Outbox و Reconciliation شمارش/مبلغ/اثر دفتر نگه دارد. انتقال یک‌مرحله‌ای یا
Dual-write بدون این کنترل‌ها ممنوع است.

## سایر Moduleها

| Module | Operation/Target مهم | Transaction/Error note |
|---|---|---|
| DealerDayPathList SAVE | Update روی `NGT.DayPaths` | Transaction صریح؛ Error propagation صریح مشاهده نشد |
| DealerDayPath SAVE | Insert/Update روی `NGT.DayPaths` | Transaction صریح |
| POSLineDiscountValidation | Mutation صفر؛ چهار Dependency | Validation query، یک NOLOCK |
| WebConfigSetting Save | Update با Alias و Dependency `WebService_Config` | Transaction صریح مشاهده نشد |
| UserDCAccessRights Save | Insert/Update روی `GNR.tblUserDCAccess` | Transaction صریح؛ سه Rollback token |
| ConfirmBaseChargeDevice | Update روی `BaseChargeDevice` و `PSession` | TRY/CATCH؛ Transaction صریح مشاهده نشد |
| VisitTemplate Save | Insert/Update روی `NGT.VisitTemplates` | Transaction صریح |

نبود Transaction/Error signal در Procedure به معنی نبودن Transaction در Caller،
Trigger یا Nested module نیست؛ همین‌طور وجود Transaction به‌تنهایی Atomicity
سرتاسری اثرهای nested را ثابت نمی‌کند.

## پیام برای ERP شخصی نگین

1. POS receipt replication باید از Sales/Treasury/Inventory current tables جدا و
   به Event/Crosswalk/Projectionهای قابل Rebuild شکسته شود.
2. Device confirmation روی `PSession` اثر جانبی دارد؛ Retirement/Confirmation
   device باید با Session invariant تست شود.
3. Web configuration بدون Transaction signal، Version append و Secret reference
   atomic در مقصد می‌خواهد.
4. User/DC access یک Command امنیتی است؛ Audit diff و delegated-scope validation
   بخشی از همان Transaction است.
5. Dealer path و Visit template هر دو NGT write surface هستند، ولی در ERP جدید
   باید Version و Offline acknowledgement جدا داشته باشند.

Artifact:
`artifacts/varanegar_analysis/ui/varanegar_extension_sql_semantics_20260827.json`

Extractor:
`scripts/sql/extract_varanegar_extension_sql_semantics.py`
