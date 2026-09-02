# قرارداد Scope و Reconciliation گزارش سفارش تولید (`RPT-13`)

فرم `FormProductionOrderReport` بدون Load/Execute کردن Assembly و فقط از روی PE/CLR
metadata و IL هش‌پین‌شده بررسی شد. `InternalConfirmCommand` مستقیماً
`Thunderstruck.DataContext.Query` را برای `dbo.USP_SDSNET_ProductionOrderReport`
فراخوانی می‌کند. Catalog روی Clone فقط‌خواندنی، هشت پارامتر و پنج dependency
`ProductionOrder`، `ProductionOrderItem`، کالا، مشتری و انبار را تأیید کرد.

پارامترهای دقیق شامل بازه تاریخ تولید، انبار مبدأ، بازه کد کالا، نوع طرف‌حساب،
مشتری و انبار مقصد است. امضای Procedure پارامتر صریح `AccYear` یا `UserRef` ندارد؛
این مشاهده نبود مجوز در لایه‌های دیگر را ثابت نمی‌کند، اما ERP مقصد باید tenant،
سال مالی، actor و مجوز مستقل هر دو انبار را پیش از Query enforce کند.

خروجی در grain آیتم سفارش تولید مدل می‌شود و Projection است، نه منبع تغییر وضعیت
سفارش یا موجودی. ابتدا key-set سفارش/آیتم/کالا/انبار مبدأ و مقصد و سپس مقدار، null،
تاریخ تجاری و ترتیب مقایسه می‌شود. Result parity تنها روی snapshot منجمد UAT و با
Golden value مالک قابل اثبات است؛ اکنون صفر است.

مسیر Excel فقط به `InsertToExcelCommand` پایه تفویض می‌شود. Export رخداد فایل خارجی
است و مجاز به mutation در ERP نیست. شش Golden Case برای دو آیتم، تفکیک انبار مبدأ
و مقصد، بازه تاریخ معکوس، منع دسترسی، ناسازگاری مشتری/نوع حساب و export تکراری ثبت
شد. ریسک تازه‌ای ایجاد نشد؛ شمار ریسک ۸۴ باقی ماند و هیچ Query عملیاتی، Procedure،
فرم یا Export اجرا نشد.
