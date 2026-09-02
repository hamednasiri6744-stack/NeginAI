# Playbook تخصصی Master Data

هفت مسیر برای duplicate candidate، sentinel، mode-dependent route، child-set ناقص، supplier-role flattening، merge غیرقابل‌برگشت و نشت PII/role collapse تعریف شده است.

هر مسیر نه گام evidence-first دارد و فقط hash و receiptهای versioned را به‌کار می‌برد. تشخیص پیش از Save/Delete/Merge/Crosswalk approval/redirect/reindex/repair متوقف می‌شود و نتیجه یکی از `NATURAL_BEHAVIOR/DATA_DEBT/BUG/UNPROVEN` است.
