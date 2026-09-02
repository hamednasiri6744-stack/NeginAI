# مرز Viewer و مالکیت ReportDocument خزانه (`RPT-01/RPT-02`)

شش Method از `TreasuryOld.Forms.dll` با IL ایستا بررسی شد. هر دو Viewer یک یا چند
Crystal `ReportDocument` آماده را از caller می‌گیرند، connection فعلی را روی Tableها
اعمال می‌کنند و ReportSource را تنظیم می‌کنند. در Methodهای منتخب `ReportDocument.Load`
وجود ندارد؛ بنابراین Template، Query، Formula، Subreport و Layout مالک caller یا
فایل خارجی‌اند، نه Viewer عمومی.

`RPT-01` viewer تک‌سندی modal است. `RPT-02` چند سند را در tabها نشان می‌دهد،
drilldown را کنترل می‌کند، visibility دکمه Print/Export را از permission object
می‌گیرد و هنگام close سندها را می‌بندد. UI visibility به‌تنهایی authorization امن
نیست؛ Export service و trusted spooler نیز باید deny-first باشند.

Parity Viewer شامل تعداد و mapping سندها، bind همه Table/Subreportها، capabilityها،
drilldown و lifecycle است. Result parity واقعی باید برای هر caller/template با hash،
پارامتر، command/table/subreport، Formula، key-set و totals جدا اثبات شود. اطلاعات
connection و Viewer type هویت Query را ثابت نمی‌کند.

شش Golden Case برای سند تک، subreport bind failure، شکست tab میانی، print denied،
export denied و close پس از partial load ثبت شد. هیچ credential یا connection string
ذخیره نشد؛ هیچ Report/Template/Form/Query اجرا نشد و Risk count ۸۴ باقی ماند.
