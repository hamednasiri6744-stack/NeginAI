# مرز Replication فروش و Idempotency تاریخچهٔ Type=8 — ۲۰۲۶-۰۸-۲۹

## نتیجه

`TourHistory(Type=8)` یک Attempt ledger یکتا نیست. Snapshot فقط‌خواندنی ۳٬۷۳۱
History برای ۳٬۵۹۳ Order Entity دارد. ۱۳۸ Entity دقیقاً دو History دارند؛ هر جفت
UUID، Ref، No و timestamp یکسان دارد. Multi-target، هدف مفقود، اختلاف UUID/Ref
با Header NGT و اختلاف با `SLE.tblSaleHdr` همگی صفرند.

بنابراین ۱۳۸ Duplicate **ردیف تاریخچه** قطعی است، اما Duplicate Sale، خروج انبار
یا سند حسابداری اثبات نشده است. دادهٔ جاری در واقع یک Target سالم برای هر ۳٬۵۹۳
Order نشان می‌دهد.

## Crosswalk جاری

| شاخص | مقدار |
|---|---:|
| History نوع ۸ | ۳٬۷۳۱ |
| Order Entity متمایز | ۳٬۵۹۳ |
| Entity با دو History | ۱۳۸ |
| History داخل گروه‌های تکراری | ۲۷۶ |
| Entity با بیش از یک Target | ۰ |
| Target Sale مفقود | ۰ |
| اختلاف Header UUID/Ref با History | ۰ |

تنها Unique index روی `TourHistory.EntityUniqueId` فیلتر `Type=1` دارد؛ از Type=8
محافظت نمی‌کند. ستون‌های `BackOfficeInvoiceUniqueId/Id` در
`NGT.CustomerCallOrders` نیز Unique index ندارند. نبود Multi-target فعلی به معنی
وجود Guard هم‌زمانی نیست.

## مسیر Runtime

```text
TourDomain.ReplicateTour
  ├─ NewReplicateTour
  ├─ سپس اولین BeginTransaction مدیریت‌شده
  ├─ Commit میانی
  ├─ BackOfficeInvoiceUniqueId setter
  ├─ BackOfficeInvoiceId setter
  ├─ BackOfficeInvoiceNo setter
  └─ Commitهای بعدی
```

سه Assembly به‌صورت PE metadata/IL و بدون Load/Execute خوانده شد. ترتیب IL نشان
می‌دهد `NewReplicateTour` پیش از Transaction مدیریت‌شده و پیش از سه setter
Crosswalk فروش است؛ Commit هم قبل و هم بعد از setterها وجود دارد. این یک failure
window ساختاری قوی است، ولی Reachability Branch و Frequency فقط با Fault test
ایزوله اثبات می‌شود.

## قرارداد مقصد

1. `SaleReplicationAttempt` با command id، source order و payload hash؛
2. History append-only جدا از `CurrentOrderSaleCrosswalk` یکتای نسخه‌دار؛
3. Outbox/Saga برای Sale، Stock effect، Accounting effect و NGT write-back؛
4. Same-key/same-payload نتیجه قبلی را برگرداند و different-payload قبل از Mutation
   رد شود؛
5. ۱۳۸ جفت تاریخ Legacy حفظ شوند، اما به یک Current target collapse شوند؛
6. Reconciliation چهارطرفهٔ NGT Header، History، Sale و آثار انبار/حسابداری؛
7. Fault injection و تست concurrent duplicate delivery.

`R-068` با شدت بحرانی افزوده شد. رجیستر فعلی ۶۸ ریسک، ۳۹ بحرانی، ۲۶ بالا، ۲۶۷
اتصال Traceability و صفر ماژول Command-ready دارد.

## Artifactها

- `scripts/sql/extract_varanegar_ngt_sale_replication_boundary.py`
- `scripts/sql/extract_varanegar_ngt_sale_replication_runtime_boundary.py`
- `artifacts/varanegar_analysis/domains/ngt_sale_replication_boundary_20260829.json`
- `artifacts/varanegar_analysis/domains/ngt_sale_replication_runtime_boundary_20260829.json`
- `tests/test_varanegar_ngt_sale_replication_boundary.py`
- `scripts/windows/build_varanegar_ngt_sale_replication_checkpoint_20260829.py`
- `artifacts/varanegar_analysis/varanegar_ngt_sale_replication_checkpoint_20260829.json`

## حدود شاهد

- هیچ Stored Procedure، Endpoint یا Assembly اجرا نشد؛
- هیچ UUID، شماره سند، مبلغ، مشتری، SQL definition یا ردیف خام ذخیره نشد؛
- Timestamp یکسان Duplicateها منبع دقیق درج دوباره را تعیین نمی‌کند؛
- نتیجه دربارهٔ Duplicate history است، نه Duplicate اثر مالی/انبار.
