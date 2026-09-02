import json
from dataclasses import replace


def _verified_invoice_result():
    return {
        "columns": [
            "CustomerId",
            "RealName",
            "InvoiceNo",
            "InvoiceDate",
            "InvoiceAmount",
            "CancelFlag",
        ],
        "rows": [[5375, "جامبو", 19731, "1405/03/25", 1768041000, 0]],
        "row_count": 1,
        "execution_time": 0.01,
        "truncated": False,
        "sources": ["dbo.Invoice_Fast"],
        "sql": "SELECT TOP (1) * FROM dbo.Invoice_Fast WHERE CustomerId=5375 ORDER BY InvoiceDate DESC",
    }


def test_professional_editor_has_no_tools_and_receives_verified_evidence(
    settings, monkeypatch
):
    from app.chat_service import ProfessionalAnswer, _professionalize_answer

    captured = {}

    class FakeResult:
        final_output = ProfessionalAnswer(
            answer="آخرین فاکتور جامبو در تاریخ ۱۴۰۵/۰۳/۲۵ صادر شده است."
        )

    def fake_run_sync(agent, *args, **kwargs):
        captured["agent"] = agent
        captured["payload"] = json.loads(kwargs["input"].split("\n", 1)[1])
        return FakeResult()

    monkeypatch.setattr("app.chat_service.Runner.run_sync", fake_run_sync)
    tuned = replace(settings, openai_api_key="test-key")
    answer = _professionalize_answer(
        tuned,
        "آخرین فاکتور مشتری کاظمی جامبو کی بوده؟",
        [],
        "پیش‌نویس پاسخ",
        _verified_invoice_result(),
        {},
    )

    assert answer.startswith("آخرین فاکتور جامبو")
    assert captured["agent"].tools == []
    assert captured["payload"]["verified_evidence"]["rows"][0][2] == 19731
    assert captured["payload"]["verified_evidence"]["sources"] == ["dbo.Invoice_Fast"]


def test_professional_editor_falls_back_to_verified_draft_on_failure(
    settings, monkeypatch
):
    from app.chat_service import _professionalize_answer

    monkeypatch.setattr(
        "app.chat_service.Runner.run_sync",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("temporary failure")),
    )
    tuned = replace(settings, openai_api_key="test-key")

    answer = _professionalize_answer(
        tuned,
        "گزارش",
        [],
        "پاسخ معتبر اولیه",
        _verified_invoice_result(),
        {},
    )

    assert answer == "پاسخ معتبر اولیه"


def test_named_user_chat_returns_polished_answer_without_changing_evidence(
    settings, monkeypatch
):
    from app.chat_service import AgentReply, ProfessionalAnswer, chat

    calls = []
    verified = _verified_invoice_result()

    class MainResult:
        final_output = AgentReply(
            answer="پاسخ خام ولی معتبر",
            evidence_status="database_result",
        )

    class EditorResult:
        final_output = ProfessionalAnswer(
            answer=(
                "آخرین فاکتور فروشگاه جامبو در تاریخ ۱۴۰۵/۰۳/۲۵ صادر شده است؛ "
                "شماره فاکتور ۱۹۷۳۱ و مبلغ آن ۱٬۷۶۸٬۰۴۱٬۰۰۰ است."
            )
        )

    def fake_run_sync(agent, *args, **kwargs):
        calls.append(agent.name)
        if "context" in kwargs:
            kwargs["context"].last_result = dict(verified)
            return MainResult()
        return EditorResult()

    monkeypatch.setattr("app.chat_service.Runner.run_sync", fake_run_sync)
    monkeypatch.setattr("app.chat_service.prepare_analysis_context", lambda *_args: {})
    tuned = replace(settings, openai_api_key="test-key")

    response = chat(
        tuned,
        "آخرین فاکتور مشتری کاظمی جامبو کی بوده؟",
        "professional-answer-test",
        "Admin",
    )

    assert response["answer"].startswith("آخرین فاکتور فروشگاه جامبو")
    assert response["rows"] == verified["rows"]
    assert response["sql"] == verified["sql"]
    assert len(calls) == 2


def test_breakdown_preserves_all_rows_metrics_and_required_sales_basis(
    settings, monkeypatch
):
    from app.chat_service import ProfessionalAnswer, _professionalize_answer

    verified = {
        "columns": [
            "DealerName",
            "SaleDocumentCount",
            "ReturnDocumentCount",
            "GrossSales",
            "ReturnAmount",
            "NetSales",
            "IsTotal",
        ],
        "rows": [
            [f"فروشنده {index}", index, 0, index * 1000, 0, index * 1000, 0]
            for index in range(1, 13)
        ] + [["جمع کل", 78, 0, 78000, 0, 78000, 1]],
        "row_count": 13,
        "truncated": False,
        "sources": ["dbo.SalesReviewFast", "dbo.SalesReturnReviewFast"],
        "sql": "SELECT DealerName, GrossSales FROM dbo.SalesReviewFast",
    }

    class FakeResult:
        final_output = ProfessionalAnswer(
            answer="فروش امروز به تفکیک ۱۰ فروشنده برتر آماده است."
        )

    monkeypatch.setattr("app.chat_service.Runner.run_sync", lambda *_args, **_kwargs: FakeResult())
    tuned = replace(settings, openai_api_key="test-key")
    answer = _professionalize_answer(
        tuned,
        "فروش امروز را به تفکیک فروشنده بگو",
        [],
        "پاسخ اولیه",
        verified,
        {},
    )

    assert "فروشنده ۱۲" in answer
    assert "اسناد فروش" in answer
    assert "اسناد برگشتی" in answer
    assert "فروش ناخالص" in answer
    assert "مبلغ برگشتی" in answer
    assert "فروش خالص" in answer
    assert "۱۰ فروشنده برتر" not in answer
    assert "مبنای گزارش: مجموع حواله و فاکتور." not in answer
