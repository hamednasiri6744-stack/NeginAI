from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VaranegarRoute:
    name: str
    label: str
    phrases: tuple[str, ...]
    terms: tuple[str, ...]
    sources: tuple[str, ...]
    guidance: tuple[str, ...]
    report_basis: str
    activity: str = "read"
    risk_level: str = "read_only"
    required_context: tuple[str, ...] = ()
    guards: tuple[str, ...] = ()


# Order matters: specific business concepts must win over broad words such as
# «فاکتور»، «مشتری» and «فروش».
VARANEGAR_ROUTES: tuple[VaranegarRoute, ...] = (
    VaranegarRoute(
        name="profit_last_purchase",
        label="سود بر مبنای آخرین قیمت خرید",
        phrases=(
            "آخرین قیمت خرید",
            "اخرین قیمت خرید",
            "آخرین قبمت خرید",
            "اخرین قبمت خرید",
            "سود بر اساس قیمت خرید",
            "سود براساس قیمت خرید",
        ),
        terms=(),
        sources=(
            "dbo.SalesReviewFast",
            "dbo.SalesReturnReviewFast",
            "FRU.GoodsModel",
            "ICA.TblSupInvoiceHdr",
            "ICA.TblSupInvoiceItm",
            "Acc.vwRcvPaymentsReview",
        ),
        guidance=(
            "This is a profit report, even when settlement discounts are mentioned. Do not route it as a settlement-detail report and do not stop after price-coverage diagnostics.",
            "For each goods item, select the last confirmed purchase on or before the report end date from ICA.TblSupInvoiceHdr/Itm with h.Status=1 and h.ConfirmDate IS NOT NULL. Use ROW_NUMBER partitioned by GoodsRef and ordered by SupInvoiceDate DESC, header ID DESC, item ID DESC.",
            "Use FRU.GoodsModel.BrandRef and BrandName for brand. Brand and manufacturer are different; never substitute ManufacturerName for BrandName.",
            "Compute cost at last purchase price from net quantity after matching sales returns: (sale quantity - return quantity) multiplied by the selected last purchase price.",
            "When the user asks to deduct settlement discounts, aggregate Acc.vwRcvPaymentsReview by SaleId before joining to sales. Include PayTypeName values containing the discount stem تخف and respect Plusminus. Never join payment rows directly to sales detail rows because that duplicates invoice discounts.",
            "An invoice-level settlement discount spanning multiple brands must be allocated to each brand in proportion to that brand's pre-settlement SellNetAmount within the invoice. State this allocation basis in the answer.",
            "Return the requested final breakdown, including BrandName, net sales after returns, allocated settlement discount, cost at last purchase price, profit at last purchase price, and profit margin. Coverage counts may be included as validation but never replace the profit result.",
        ),
        report_basis="فروش خالص پس از برگشت و تخفیف تسویه، منهای بهای کالای فروش‌رفته بر مبنای آخرین خرید تأییدشده",
    ),
    VaranegarRoute(
        name="previsit_order",
        label="پیش ویزیت و ثبت کنترل شده سفارش",
        phrases=(
            "سفارش ثبت کن", "ثبت سفارش", "سفارش بزن", "درخواست ثبت کن",
            "پیش ویزیت", "پیش ویزیت", "سبد سفارش", "پیش نمایش سفارش",
        ),
        terms=(),
        sources=(
            "SLE.OrdersReview",
            "Acc.vwCustomerBalance",
            "dbo.SalesReviewFast",
        ),
        guidance=(
            "Route an order-creation request through the NGT-backed previsit workflow, not through free-form SQL or a direct table insert.",
            "Resolve the assigned seller route and customer first, then load the permitted warehouse, order/payment types, product catalogue, units, inventory, pricing, tax, discount, prize, and live credit controls.",
            "Run the official NGT preview before persistence. A preview or locally saved request is not a confirmed Varanegar order.",
            "Final Varanegar registration is allowed only when the server-side order bridge, transactional numbering verification, and commit feature flags are all enabled; otherwise stop after a safe preview/local save.",
        ),
        report_basis="گردش کار NGT از مشتری مسیر تا محاسبه رسمی، کنترل اعتبار و ثبت امن درخواست",
        activity="workflow",
        risk_level="controlled_write",
        required_context=(
            "seller", "route", "customer", "warehouse", "order_type",
            "payment_type", "order_lines",
        ),
        guards=(
            "Customer must belong to the selected seller route.",
            "Warehouse, order type, payment type, products, and sale units must be permitted by the live NGT context.",
            "Official NGT preview, inventory, pricing, tax, discount, prize, and credit controls must pass before save or submit.",
            "Never claim final registration unless the transactional bridge returns a verified positive final order number.",
        ),
    ),
    VaranegarRoute(
        name="returned_cheque",
        label="چک برگشتی و تاریخچه وضعیت چک",
        phrases=(
            "چک برگشتی", "چک های برگشتی", "چکهای برگشتی", "برگشتی فعال",
            "وصول بعد از برگشت", "استرداد بعد از برگشت", "پرونده حقوقی چک",
        ),
        terms=(),
        sources=(
            "Acc.vwRcvRetChequeReview",
            "Acc.vwRcvChequeReview",
            "Acc.vwRcvPaymentsReview",
            "Acc.vwCustomerBalance",
        ),
        guidance=(
            "Separate the cheque's current status from its status history. Distinguish active returned, collected after return, returned to owner after return, and legal follow-up.",
            "Keep cheque owner (TblCheque.CustRef) separate from the customer receiving a returned-cheque settlement allocation; they can differ.",
            "Do not classify every cheque that ever had a returned status as currently returned.",
        ),
        report_basis="وضعیت جاری و تاریخچه پایدار چک دریافتی با تفکیک مالک و مشتری تخصیص",
        required_context=("customer",),
        guards=(
            "Verify current status against status history before labeling a cheque as actively returned.",
            "Do not replace cheque owner with the allocation customer when they differ.",
        ),
    ),
    VaranegarRoute(
        name="invoice_balance",
        label="مانده و وضعیت تسویه فاکتور",
        phrases=(
            "مانده فاکتور", "فاکتور باز", "فاکتورهای باز", "وضعیت تسویه",
            "تسویه نشده کامل", "تسویه شده قسمتی", "remainingamount", "paymentstatus",
        ),
        terms=(),
        sources=(
            "Acc.vwRcvSaleReview",
            "dbo.vwReview_RcvAccountSale2",
            "dbo.vwReview_RcvAccountSettlement2",
            "Acc.vwRcvPaymentsReview",
            "dbo.SettlementFast",
            "dbo.InvoiceReceipt",
            "Acc.vwCustomerBalance",
        ),
        guidance=(
            "Use Acc.vwRcvSaleReview first for invoice balance and payment status; the Fast variant lacks RemainingAmount, PaymentStatus, and SettlementAmount.",
            "Treat RemainingAmount as SalesNetAmount minus SettlementAmount. Do not rebuild it from cash/cheque/bank-transfer components.",
            "A fully settled invoice may have zero or negative remaining amount; do not require exact zero unless the user explicitly asks for zero balance.",
        ),
        report_basis="مبلغ خالص فاکتور منهای مبلغ تسویه‌شده",
        required_context=("customer_or_scope", "period"),
        guards=(
            "Use invoice settlement status and RemainingAmount; do not infer balance from receipt components.",
            "Resolve whether the request is for one customer, one organizational scope, or all permitted records.",
        ),
    ),
    VaranegarRoute(
        name="customer_cardex",
        label="کاردکس و مانده حساب مشتری",
        phrases=("کاردکس مشتری", "کاردکسش", "گردش حساب مشتری", "گردش مشتری", "بدهکار بستانکار مشتری"),
        terms=("کاردکس", "cardex"),
        sources=(
            "dbo.vwReview_RcvAccountCardex2",
            "Acc.vwCustomerBalance",
            "Acc.vwRcvPaymentsReview",
            "Acc.vwRcvSaleReview",
        ),
        guidance=(
            "A customer cardex is the chronological debit/credit ledger with a running balance; it is not the same as the open-invoice list.",
            "Use the official cardex view for document type/no/date, debit, credit, and running balance; use vwCustomerBalance only for an overall balance.",
        ),
        report_basis="گردش بدهکار و بستانکار و مانده تجمعی مشتری",
        required_context=("customer", "period"),
        guards=("Keep the chronological cardex distinct from the open-invoice list.",),
    ),
    VaranegarRoute(
        name="settlement",
        label="تسویه و تخصیص دریافت به فاکتور",
        phrases=("تسویه فاکتور", "جزئیات تسویه", "اقلام تسویه", "تخصیص دریافت", "مصرف دریافت"),
        terms=("تسویه", "settlement"),
        sources=(
            "dbo.vwReview_RcvAccountSettlement2",
            "dbo.SettlementFast",
            "Acc.vwRcvPaymentsReview",
            "Acc.vwRcvSaleReview",
            "dbo.InvoiceReceipt",
            "dbo.Receipt2",
        ),
        guidance=(
            "Settlement is allocation of a receipt, payment instrument, return, discount, notice, credit, or adjustment to an invoice/debt; it is not the receipt header itself.",
            "Respect PayTypePlusMinus or the verified report sign. Settlement types can increase or decrease the applied balance.",
        ),
        report_basis="تخصیص ابزار پرداخت، برگشت یا تعدیل به فاکتور/بدهی",
        required_context=("customer_or_invoice", "period"),
        guards=("Respect the verified plus/minus sign for every settlement type.",),
    ),
    VaranegarRoute(
        name="receipt",
        label="دریافت و وصول خزانه",
        phrases=("دریافت خزانه", "رسید دریافت", "مانده دریافت", "دریافت باز", "مبلغ دریافت"),
        terms=("دریافت", "وصول", "receipt", "collection"),
        sources=(
            "dbo.Receipt2",
            "dbo.vwReview_TreasuryReceipt2",
            "Acc.vwRcvPaymentsReview",
            "dbo.InvoiceReceipt",
            "dbo.SettlementFast",
        ),
        guidance=(
            "A receipt records money/payment instruments entering treasury and can remain unallocated; do not present receipt creation as invoice settlement.",
            "ReceiptRemainAmount equals ReceiptAmount minus ReceiptExpendedAmount in the verified operational view.",
            "When using Acc.vwRcvPaymentsReview for customer collection totals, filter PayTypeName to external instruments before summing.",
        ),
        report_basis="ورود وجه یا اسناد به خزانه، مستقل از تخصیص بعدی",
        required_context=("period", "organization_scope"),
        guards=("Do not equate receipt registration with invoice settlement.",),
    ),
    VaranegarRoute(
        name="sales_voucher",
        label="حواله فروش",
        phrases=("حواله فروش", "حواله/فاکتور", "شماره حواله فروش", "sale voucher", "salevoucher"),
        terms=("حواله", "voucher"),
        sources=(
            "dbo.SalesReviewFast",
            "SLE.OrdersReview",
            "Acc.vwRcvSaleReview",
            "dbo.vwReview_RcvAccountSale2",
        ),
        guidance=(
            "A sales voucher is the operational sale/delivery document. Do not confuse it with a bank transfer or an inventory voucher.",
            "Use SaleVoucherNo/SellVocherNo for the sales voucher number and SaleNo/SellNo for the invoice number.",
        ),
        report_basis="حواله عملیاتی فروش؛ جدا از فاکتور، حواله بانکی و سند انبار",
        required_context=("period", "organization_scope"),
        guards=("Reject bank-transfer and inventory-voucher interpretations before selecting this route.",),
    ),
    VaranegarRoute(
        name="order",
        label="درخواست و سفارش مشتری",
        phrases=("درخواست مشتری", "سفارش مشتری", "تبدیل درخواست", "وضعیت سفارش"),
        terms=("سفارش", "درخواست", "order"),
        sources=(
            "SLE.OrdersReview",
            "dbo.SalesReviewFast",
        ),
        guidance=(
            "A customer order/request is not a finalized sale. Report its conversion and cancellation status separately from invoice sales.",
        ),
        report_basis="درخواست اولیه و وضعیت تبدیل آن به حواله یا فاکتور",
        required_context=("period", "customer_or_organization_scope"),
        guards=("Report conversion, confirmation, and cancellation separately from finalized sales.",),
    ),
    VaranegarRoute(
        name="distribution",
        label="توزیع و تحویل",
        phrases=("مدیریت توزیع", "پیگیری توزیع", "تیم توزیع", "مامور توزیع", "مأمور توزیع"),
        terms=("توزیع", "راننده", "distributor", "distribution"),
        sources=(
            "dbo.SalesReviewFast",
            "SLE.OrdersReview",
        ),
        guidance=(
            "Keep salesperson, supervisor, distributor, real distributor, driver, and distribution assistants as separate roles.",
            "Keep sales, visit, distribution, and collection paths as separate dimensions.",
        ),
        report_basis="اتصال فاکتور و سفارش به تور، تیم توزیع، مسیر و وضعیت تحویل",
        required_context=("period", "distribution_scope"),
        guards=(
            "Keep visit, sales, distribution, and collection paths separate.",
            "Keep seller, supervisor, distributor, real distributor, driver, and assistants separate.",
        ),
    ),
    VaranegarRoute(
        name="inventory",
        label="انبار و موجودی کالا",
        phrases=("کاردکس کالا", "گردش انبار", "سند انبار", "موجودی انبار"),
        terms=("انبار", "موجودی", "کالا", "stock", "inventory"),
        sources=(
            "dbo.vwReview_StockProduct2",
            "dbo.vwReview_StockProductGroup2",
            "dbo.vwReview_StockCardex2",
        ),
        guidance=(
            "An inventory voucher is a stock movement document and is distinct from a sales voucher and an accounting voucher.",
        ),
        report_basis="موجودی و گردش واقعی کالا در انبار/مرکز توزیع",
        required_context=("warehouse_or_dc", "as_of_date"),
        guards=("Resolve warehouse versus distribution center before aggregating stock.",),
    ),
    VaranegarRoute(
        name="sales",
        label="فروش و برگشت از فروش",
        phrases=("فروش خالص", "گزارش فروش", "برگشت از فروش", "فاکتور فروش"),
        terms=("فروش", "فاکتور", "مرجوعی", "برگشتی", "sale", "sales", "invoice", "factor"),
        sources=(
            "dbo.SalesReviewFast",
            "dbo.SalesReturnReviewFast",
            "dbo.vwReview_SellProduct2",
            "dbo.vwReview_SellProductGroup2",
            "Acc.vwRcvSaleReview",
        ),
        guidance=(
            "For a generic sales question, count unique sales: an invoice and voucher linked to the same sale are one sale, never two.",
            "Use returns from the same date/dimension basis when calculating verified net sales.",
        ),
        report_basis="مجموع فاکتور و حواله با کسر برگشت متناظر",
        required_context=("period", "organization_scope", "document_basis"),
        guards=(
            "Resolve distribution center, sales office, warehouse, and path as different dimensions.",
            "Count a linked invoice and sales voucher as one sale and subtract returns on the same dimension/date basis.",
        ),
    ),
)


_ROUTES_BY_NAME = {route.name: route for route in VARANEGAR_ROUTES}


def normalize_business_text(value: str) -> str:
    return " ".join(
        str(value or "")
        .replace("ي", "ی")
        .replace("ك", "ک")
        .replace("ۀ", "ه")
        .replace("ة", "ه")
        .replace("‌", " ")
        .casefold()
        .split()
    )


def get_varanegar_route(name: str) -> VaranegarRoute | None:
    return _ROUTES_BY_NAME.get(str(name or "").strip())


def detect_varanegar_route(value: str) -> VaranegarRoute | None:
    normalized = normalize_business_text(value)
    if not normalized:
        return None
    tokens = set(normalized.replace("/", " ").split())
    for route in VARANEGAR_ROUTES:
        if any(normalize_business_text(phrase) in normalized for phrase in route.phrases):
            return route
        if route.terms and any(normalize_business_text(term) in tokens for term in route.terms):
            # A bank transfer or an inventory voucher must not be routed as a
            # sales voucher merely because it contains the generic word حواله.
            if route.name == "sales_voucher" and any(
                marker in normalized for marker in ("حواله بانکی", "سند انبار", "حواله انبار")
            ):
                continue
            return route
    return None


def resolve_varanegar_route(question: str, recent_context: str = "") -> VaranegarRoute | None:
    # A fully specified current question always wins. Recent context is used
    # only for genuinely short follow-ups whose subject was omitted.
    current = detect_varanegar_route(question)
    if current is not None:
        return current
    return detect_varanegar_route(recent_context)


def route_definition(route: VaranegarRoute) -> dict[str, object]:
    return {
        "term": route.label,
        "definition": route.report_basis,
        "rules": " ".join(route.guidance),
        "approved_sql": None,
        "related_objects": list(route.sources),
        "knowledge_source": "varanegar_operational_ontology",
        "operational_contract": {
            "activity": route.activity,
            "risk_level": route.risk_level,
            "required_context": list(route.required_context),
            "guards": list(route.guards),
        },
    }
