# راهنمای تشخیص مغایرت موجودی وارانگار

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **تأییدشده روی Clone فقط‌خواندنی؛ اجرای Repair صفر**

## نتیجهٔ اصلاحی

عدد ۱٬۵۹۴ که قبلاً «مغایرت Stock با Cardex» نامیده شده بود، خرابی داده نیست.
مقایسهٔ قبلی فقط این دو عدد را کنار هم گذاشته بود:

```text
GNR.tblStockGoods.OnHandQty
SUM(inv.vwHealthyCardex.Qty)
```

اما قرارداد رسمی خود وارانگار در `dbo.usp_ModifyStockGoods` این است:

```text
موجودی عملیاتی صحیح
= SUM(inv.vwHealthyCardexForCheck.Qty)
- فروش فعالِ هنوز خارج‌نشده
- فروش متصل به خروجِ هنوز تغییرنیافته
- سفارش خرید Legacy در Branch فعال
- سفارش تأییدشدهٔ اثرگذار بر موجودی
- رزرو جایزه
- (برگشت خرید با علامت منفی؛ پس عملاً به مانده اضافه می‌شود)
```

در Snapshot فعلی تنها مؤلفهٔ غیرصفر، «فروش فعالِ هنوز خارج‌نشده» است:

| سنجه | مقدار |
|---|---:|
| کلید کالا–انبار سال ۱۴۰۵ | ۳۳٬۳۱۴ |
| فاصلهٔ Cardex-only | ۱٬۵۹۴ کلید / ۱۰۴٬۴۷۰ واحد |
| کلید تعهد فروشِ بدون خروج | ۱٬۵۹۴ کلید / ۱۰۴٬۴۷۰ واحد |
| مغایرت پس از فرمول رسمی | **صفر کلید / صفر واحد** |

پس `OnHandQty` فقط Projection کاردکس نیست؛ Projection «کاردکس منهای تعهدهای
عملیاتی هنوز خارج‌نشده» است. حذف این مؤلفه در نسخهٔ وب موجودی قابل‌فروش را
۱۰۴٬۴۷۰ واحد بیش‌اظهار می‌کند.

## توزیع فعلی تعهد

چهار انبار درگیرند: ۱، ۲، ۳ و ۹. تعداد کلید/قدر مطلق تعهد آن‌ها به‌ترتیب
۸۲۸/۵۳٬۵۹۸، ۵۰۸/۳۳٬۵۱۱، ۱/۲۴ و ۲۵۷/۱۷٬۳۳۷ است. این دقیقاً با فاصلهٔ
Cardex-only همان انبارها برابر است.

تعهد جاری از ۸۲۱ فروش و ۵٬۱۸۰ ردیف تشکیل شده است. ۷۶۸ فروش با ۹۶٬۹۰۹ واحد
در بازهٔ سنی ۳ تا ۷ روز و ۵۳ فروش با ۷٬۵۶۱ واحد در بازهٔ ۸ تا ۳۰ روزند.
این Aging بر اساس `CreationDate` فعلی است و Event log تغییر وضعیت محسوب نمی‌شود.

در پنجرهٔ سه‌ماههٔ سیستمی، تنها فروش‌های ایجادشده در ماه اوت هنوز بدون خروج
مانده‌اند. شمار ماهانه صرفاً وضعیت فعلی اسنادِ ایجادشده در هر ماه را نشان
می‌دهد، نه تاریخچهٔ انتقال وضعیت.

## مسیر عیب‌یابی عملی

اگر کاربر می‌گوید «کاردکس از موجودی بیشتر است»:

1. سال، DC و انبار را تثبیت کن؛ `OnHandQty` را با Cardex-only تعمیر نکن.
2. تفاوت `ledger_for_check - stored` را محاسبه کن.
3. شش خانوادهٔ تعهد فرمول رسمی را جداگانه جمع بزن.
4. اگر تفاوت دقیقاً با تعهدها برابر است، وضعیت `EXPECTED_OPERATIONAL_OBLIGATION`
   است، نه مغایرت.
5. فقط باقی‌ماندهٔ پس از فرمول کامل را `UNEXPLAINED_STOCK_RESIDUAL` بنام.
6. برای باقی‌ماندهٔ واقعی، Snapshot آرام یا Snapshot isolation لازم است؛ فرمول
   Legacy چند منبع را با `NOLOCK` می‌خواند و در زمان ترافیک می‌تواند Mixed-time
   باشد.
7. نوع سند را بررسی کن. Trigger عمومی تأیید مسیرهای ۶۰، ۲۱، ۶۴، ۶۵ و
   نوع ۲۰/Health=3 را عمداً رد می‌کند؛ این‌ها مسیر تخصصی دارند.

## هشدار بحرانی

`dbo.usp_ModifyStockGoods` فقط گزارش نیست. با `@OnlyCheck=0` وارد تراکنش می‌شود،
Triggerهای Stock را غیرفعال می‌کند و Snapshot موجودی را Update می‌کند. در تحلیل
یا عیب‌یابی نباید آن را اجرا کرد. Extractor این سند فقط SELECT متناظر را روی
Clone `READ_ONLY` اجرا کرده است.

## یافته‌های ثبت‌شده

| شناسه | شدت | معنا |
|---|---|---|
| STK-001 | CRITICAL | Cardex-only فرمول رسمی موجودی نیست |
| STK-002 | CRITICAL | Procedure تشخیص، Branch تعمیر مخرب هم دارد |
| STK-003 | HIGH | چند نوع سند از Trigger عمومی عبور نمی‌کنند |
| STK-004 | HIGH | فرمول رسمی به‌علت NOLOCK به زمان Snapshot حساس است |
| STK-005 | HIGH | یکی از دو AllowNegative برای بیشتر انواع Pre-check را رد می‌کند |

## قرارداد مقصد وب

- `InventoryMovementLedger` مستقل و تغییرناپذیر؛
- `OpenSaleStockObligation` مستقل، نسخه‌دار و قابل Rebuild؛
- `InventoryOperationalProjection = ledger - obligations`؛
- خروجی Explain برای هر اختلاف با سهم هر مؤلفه؛
- `UNEXPLAINED_STOCK_RESIDUAL` تنها Blocker واقعی؛
- هیچ Repair خودکار یا Trigger-disable در Command عادی.

## شواهد و بازتولید

- Artifact:
  `artifacts/varanegar_analysis/ui/varanegar_stock_reconciliation_diagnostic_contract_20260827.json`
- Extractor:
  `scripts/sql/extract_varanegar_stock_reconciliation_diagnostic_contract.py`
- اجرای امن:

```powershell
.\.venv\Scripts\python.exe scripts\sql\extract_varanegar_stock_reconciliation_diagnostic_contract.py `
  --output artifacts\varanegar_analysis\ui\varanegar_stock_reconciliation_diagnostic_contract_20260827.json
```

محدودیت: نتیجه روی Clone فقط‌خواندنی فعلی است؛ برای پذیرش مهاجرت باید همین
فرمول روی Snapshot مجاز، هم‌زمان و آرام Production با Watermark تکرار شود.
