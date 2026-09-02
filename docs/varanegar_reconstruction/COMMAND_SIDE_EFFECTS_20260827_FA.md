# زنجیره Command تا SQL، Ledger و Audit

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **۱۱ Trace، ۱۲ SQL object، ۹۵ Reference رسمی؛ بدون اجرای Procedure**

## نتیجهٔ اصلی

هشت Command از ۱۱ Trace ماهیت Mutating دارند. در هیچ‌کدام از Signatureهای
فعلی پارامتر صریح `command_id`، `request_id`، `correlation_id` یا Idempotency
token دیده نشد. این به معنی وقوع Duplicate در وارانگار نیست، اما نشان می‌دهد
Idempotency مقصد نباید از قرارداد Legacy استنباط یا به UI واگذار شود.

هر Command وب مقصد باید:

```text
command_id + expected_version/current_state + actor/scope/date/reason
    -> permission + feature + workflow + domain validation
    -> one server transaction
    -> aggregate/current pointer + ledger/history + audit
    -> reconciliation result
```

## زنجیره‌های توزیع

### Create / Update

```text
FormDistManagementDataEntry.SaveCommand
  -> DistHandler.CreateDist
  -> DistAdapter.CreateDist
  -> SLE.usp_sdsnet_CreateDist
  -> dbo.GetMaxDistNo
```

References Mutating رسمی شامل `sle.tblDist`، `sle.tblSaleHdr` و
`sle.tblSaleDistHist` است. Procedure اصلی دو Insert، چهار Update و یک Delete
دارد؛ `GetMaxDistNo` نیز خودش Insert/Update و Begin/Commit دارد. پس تولید شماره
یک Query بی‌اثر نیست و باید در Transaction/Uniqueness contract مقصد قرار گیرد.

### صدور خروج

```text
FormDistManagementList.SetExitexportation
  -> DistHandler.CreateExitVocherByDist
  -> DistAdapter.CreateExitVocherByDist
  -> dbo.usp_CreateExitVocherByDist
```

Mutated references شامل `inv.tblExit`، `sle.tblSaleHdr` و `inv.tblVocherHdr`
است و قرارداد به Voucher header/item/detail، Cardex check و
`tblSaleDistHistFull` وصل می‌شود. Procedure ۸ Insert، یک Update، یک Delete و ۱۲
Exec دارد؛ این یک Orchestration مالی/انبار است، نه تغییر Status ساده.

### Merge/adjust خروج

`MergeGoodsExitData → DistHandler.MergeGoodsExit → inv.Usp_InsertGoodsExit_RD`
به `sle.tblGoodsExit_RD` می‌نویسد. پس RD باید به‌عنوان Staging/working set جدا از
خروج قطعی مدل شود.

### حذف خروج

`RemoveExitFromDist → DistHandler.RemoveExitFromDist → inv.Usp_RemoveExitFromDist`
گسترده‌ترین Reverse است: ۱۲ Delete، هفت Update و دو Insert در تعریف فعلی. خروج
را Cancel می‌کند، لینک Exit فروش را برمی‌گرداند، Dist را به Status ۱ می‌برد،
Voucherهای مرتبط و RDها را پاک/برمی‌گرداند و `tblSaleDistHistFull` را با Reason
ثبت می‌کند. در مقصد این Command باید SoD، Reason اجباری، Impact preview و
Reconciliation پس از Commit داشته باشد؛ CRUD delete نیست.

## زنجیره‌های چک

### چک دریافتی

```text
validate -> dbo.RchequeWorkFlow_IsValid       (read-only)
change   -> dbo.DoRCheque_AddRChequeHistory   (history + current cheque)
undo     -> dbo.DoRCheque_DeleteLastRChequeHistory
```

ChangeStatus به `dbo.RChequeHistory`/`acc.tblChqHist` و Current cheque متصل است؛
Undo History آخر را برمی‌گرداند. هر دو Procedure Add/Delete دارای Begin/Commit/
Rollback و TRY/CATCH محلی هستند.

### چک پرداختنی

```text
validate -> dbo.PChequeWorkFlow_IsValid       (read-only)
change   -> dbo.DoPCheque_AddPChequeHistory
undo     -> dbo.DoPCheque_DeleteLastPChequeHistory
```

Change/Undo علاوه بر `PChequeHistory`، Current cheque و `PChequeBookItem` را
Mutate می‌کنند؛ پس وضعیت برگ دفترچه بخشی از همان Consistency boundary است. این
دو Procedure نیز Transaction محلی کامل دارند.

## شاهد Transaction و محدودیت نتیجه‌گیری

در متن خود Moduleهای CreateDist و CreateExit، Begin/Commit/Rollback صریح دیده
نشد؛ InsertGoodsExit TRY/CATCH بدون Begin/Commit و RemoveExit Rollback بدون Begin
محلی دارد. این شاهد «نبود Transaction کل سیستم» نیست: Caller یا Procedureهای
تو‌در‌تو ممکن است Transaction را باز کنند. نتیجهٔ درست این است که Atomicity این
چهار مسیر هنوز Gate اثبات‌نشده است و در ERP مقصد باید صریح و قابل تست شود.

Hash Definition همه ۱۲ Object با Artifact قرارداد SQL قبلی یکسان است؛ بنابراین
Side-effect analysis روی همان Snapshot قرارداد انجام شده، نه نسخه‌ای متفاوت.

## قرارداد مقصد

1. `command_id` سمت Client تولید و در Server با Unique key نگهداری شود؛ Retry
   همان نتیجه قطعی قبلی را بدهد.
2. `expected_version` یا Expected current-history ID برای جلوگیری از Lost update
   اجباری باشد.
3. Aggregate، Current pointer، Ledger/History و Audit در یک Transaction Server
   commit شوند.
4. Reverse Commandها Reason، Scope و Permission سخت‌تر و Impact preview دارند.
5. SQL مستقیم برای Browser/Android ممنوع؛ مسیر رسمی Backend→Integration API است.
6. Post-conditionهای تراز تعداد/Batch/Cardex/Payment allocation به‌صورت Golden
   reconciliation اجرا شوند.

## مرز ایمنی

فقط Metadata، Signature، `sys.dm_sql_referenced_entities` و Definition در حافظه
خوانده شد. هیچ Procedure برنامه اجرا نشد، Definition خام یا Literal ذخیره نشد،
هیچ ردیف تجاری/مبلغ/هویت خوانده یا ثبت نشد و Database `READ_ONLY` بود.

## Artifact و بازتولید

- `scripts/sql/extract_varanegar_command_side_effects.py`
- `artifacts/varanegar_analysis/ui/varanegar_command_side_effects_20260827.json`
- `tests/test_varanegar_ui_evidence.py`
