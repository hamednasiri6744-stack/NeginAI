# قرارداد Base template فرم‌های ورود داده

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS برای شش Template؛ Runtime binding صفر**

تمام ۴۶ فرمی که Field محلی اعلام‌شده نداشتند از شش Template مشترک ارث می‌برند:

- ۲۸ فرم `FormBaseWithListDataEntry`؛
- ۸ فرم `FormBaseV2SimpleDataEntry`؛
- ۴ فرم Filter-list، سه فرم Tree-list، دو Master-detail و یک Dialog.

شش Base type از DLL Hash‌شده حل شدند: ۴۳ Control field با ۳۵ نام یکتا و ۲۶۳
Method body دارند. ۱۰۴ Method نام‌دار شامل ۴۶ Write/Delete signal، ۱۹
Validation/Guard، سه Permission، ۲۷ Load/Refresh و ۹ Selection/Filter است.

Template ساده مشترک فرمان‌های New/Edit/Delete/Save/SaveClose/SaveNew/Refresh،
Print/Report/Attachment و navigation رکورد را مالک است؛ Templateهای List/Tree/
Master-detail Grid و Split-container مشترک می‌دهند. بنابراین این ۴۶ فرم «بی‌فیلد»
نیستند، بلکه Base-template-driven هستند.

Static template method اجرای Branch، مجوز مؤثر، Binding یا Write موفق را ثابت
نمی‌کند. ERP وب باید این رفتار مشترک را به Component/Policy/Commandهای صریح تبدیل کند.

Artifact: `artifacts/varanegar_analysis/ui/varanegar_data_entry_base_template_contracts_20260827.json`

Extractor: `scripts/windows/extract_varanegar_data_entry_base_template_contracts.py`
