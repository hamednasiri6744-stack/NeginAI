# فیلدهای اعلام‌شدهٔ فرم‌های مبهم وارانگار

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS متادیتای فقط‌خواندنی؛ کنترل Runtime و Binding هنوز اثبات نشده**

## نتیجهٔ روشن

متادیتای CLR هر هفت فرم اولویت‌بالا بدون Load یا اجرای DLL خوانده شد. شش فرم
در کلاس خودشان مجموعاً ۲۲۹ Field امن و قابل‌گزارش دارند. فرم
`FormSpecialOptionsDistrict` در کلاس مشتق صفر Field مستقل دارد، اما از زنجیرهٔ
Framework شامل `FormBaseSimpleDialog`، `FormBaseV2SimpleDataEntry` و
`FormBaseV2` ارث می‌برد؛ در این زنجیره ۸۸ Field امن دیده شد.

این نتیجه به معنی وجود ۸۸ کنترل قابل‌مشاهده روی فرم منطقه نیست. آن‌ها قابلیت‌های
عمومی Framework مانند Command bar، Save/Edit/Delete، Layout و Context فرم هستند
و Visibility، Enabled state، Label، Binding، Requiredness و Branch زمان اجرا
همچنان `UNPROVEN` است.

## پوشش عددی

| فرم | Field مستقیم | Field زنجیرهٔ Base | Signal فرمان/مجوز |
|---|---:|---:|---|
| `frmBankReconciliation` | ۱۳ | ۲ | فایل/جدول جزئیات |
| `frmBankReconciliationList` | ۳۸ | ۲ | `SetFormPermission` |
| `frmChek` | ۵۵ | ۲ | `btnSave_Click` |
| `frmList` | ۴۱ | ۰ | `btnCancel_Click` |
| `frmReconciliation` | ۶۲ | ۲ | Add/Delete item |
| `frmReconciliationSetup` | ۲۰ | ۲ | Save/Delete/Cancel و `SetFormPermission` |
| `FormSpecialOptionsDistrict` | ۰ | ۸۸ | فقط قابلیت عمومی Base؛ Command دامنه‌ای اثبات نشد |

در ۲۲۹ Field مستقیم، ۱۹ Command، هشت Container، هفت Grid، سه Date، یک Choice،
یک Boolean، ۲۴ Text و ۳۰ Label از روی Prefix نام Field دسته‌بندی شد؛ ۱۳۶ نام
بدون حدس نوع کنترل با عنوان `unclassified_declared_field` باقی ماند. هیچ Field
حساس حذف‌شده، اختلاف Hash، Type گمشده یا خطای Metadata وجود نداشت.

## پیامد برای بازسازی

- شش فرم Treasury دیگر صرفاً اسم مبهم نیستند؛ سطح ورودی/لیست/دکمهٔ احتمالی آن‌ها
  برای طراحی Prototype قابل‌فهرست است، اما Binding به ستون و Requiredness باید
  با شاهد جداگانه اثبات شود.
- صفر بودن Field مستقیم `FormSpecialOptionsDistrict` فرض «صفحهٔ تنظیمات مستقل با
  فیلدهای مشخص» را رد می‌کند. تا کشف Runtime factory، Resource، DataObject یا
  launcher، Route و Schema مقصد از نام این فرم ساخته نمی‌شود.
- Commandهای عمومی Framework مالک Business mutation نیستند. Save/Delete مقصد
  فقط بعد از قرارداد دامنه، Permission، Scope و State transition تعریف می‌شود.

## ایمنی و حدود اطمینان

- DLLها فقط به‌صورت فایل PE/.NET Metadata Parse شدند و Load/Execute نشدند؛
- هیچ اتصال دیتابیس، شبکه، UI action یا Application command انجام نشد؛
- مقدار Field، String literal، Resource و Config payload خوانده یا ذخیره نشد؛
- نام Field فقط Signal ساختاری است و اثبات رفتار واقعی نیست.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/varanegar_priority_gap_declared_fields_20260827.json`
- `scripts/windows/extract_varanegar_priority_gap_declared_fields.py`
- `tests/test_varanegar_ui_evidence.py`

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\windows\extract_varanegar_priority_gap_declared_fields.py `
  --source-directory "\\192.168.1.171\exe\VN.SDS.Container" `
  --binary-inventory G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_binary_inventory_20260827.json `
  --form-gaps G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_form_evidence_gaps_20260827.json `
  --call-graph G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_priority_gap_call_graph_20260827.json `
  --output G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_priority_gap_declared_fields_20260827.json
```
