import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _png_size(path: Path) -> tuple[int, int]:
    payload = path.read_bytes()
    assert payload[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", payload[16:24])


def test_company_road_mark_is_used_by_web_app_and_cache():
    static = ROOT / "app" / "static"
    html = (static / "assistant.html").read_text(encoding="utf-8")
    manifest = json.loads((static / "manifest.webmanifest").read_text(encoding="utf-8"))
    worker = (static / "service-worker.js").read_text(encoding="utf-8")

    assert _png_size(static / "negin-brand-icon-192.png") == (192, 192)
    assert _png_size(static / "negin-brand-icon-512.png") == (512, 512)
    assert html.count("/static/negin-brand-icon-192.png") >= 3
    assert html.count('class="brand-mark-image"') >= 3
    assert manifest["background_color"] == "#11100e"
    assert manifest["theme_color"] == "#0d0e0c"
    assert {item["src"] for item in manifest["icons"]} >= {
        "/static/negin-brand-icon-192.png",
        "/static/negin-brand-icon-512.png",
    }
    assert "neginai-shell-v214" in worker
    assert "/static/assistant.css?v=106" in worker
    assert "/static/previsit-workspace.css?v=50" in worker
    assert "/static/assistant.js?v=213" in worker


def test_graphite_gold_theme_is_shared_by_web_and_android_webview():
    static = ROOT / "app" / "static"
    script = (static / "assistant.js").read_text(encoding="utf-8")
    shell_styles = (static / "assistant.css").read_text(encoding="utf-8")
    previsit_styles = (static / "previsit-workspace.css").read_text(encoding="utf-8")

    assert "document.documentElement.classList.add('web-road-theme');" in script
    assert "if (!isNeginAndroidApp) document.documentElement.classList.add('web-road-theme')" not in script
    assert "html.web-road-theme .sidebar" in shell_styles
    assert "html.web-road-theme .main-header" in shell_styles
    assert "html.web-road-theme .panel-header" in shell_styles
    assert "html.web-road-theme .previsit-cart-header" in previsit_styles
    assert "html.web-road-theme .previsit-visit-rail" in previsit_styles
    assert "html.web-road-theme .previsit-preview-button" in previsit_styles


def test_web_road_theme_uses_a_consistent_dark_gold_surface_contract():
    static = ROOT / "app" / "static"
    shell_styles = (static / "assistant.css").read_text(encoding="utf-8")
    previsit_styles = (static / "previsit-workspace.css").read_text(encoding="utf-8")

    assert "--road-bg:#090a09" in shell_styles
    assert "html.web-road-theme .main-panel{background:var(--road-bg)" in shell_styles
    assert "html.web-road-theme .seller-route-card" in shell_styles
    assert "html.web-road-theme .customer-profile-card" in shell_styles
    assert "html.web-road-theme .previsit-panel{background:var(--road-bg)!important" in previsit_styles
    assert "html.web-road-theme .previsit-list-product" in previsit_styles
    assert "html.web-road-theme .previsit-invoice-scroll" in previsit_styles


def test_web_order_workspace_defaults_to_stock_uses_compact_cart_and_keeps_voice_at_hand():
    static = ROOT / "app" / "static"
    script = (static / "assistant.js").read_text(encoding="utf-8")
    styles = (static / "previsit-workspace.css").read_text(encoding="utf-8")

    assert "let previsitListState = {query: '', group: '', brand: '', inStock: true}" in script
    assert "previsitListState = {query: '', group: '', brand: '', inStock: true}" in script
    assert 'id="previsitListStockToggle" type="button" class="is-active" aria-pressed="true"' in script
    assert 'requestedView === \'cart\' && previsitActiveView === \'cart\' ? \'catalog\'' in script
    assert 'html.web-road-theme .previsit-mobile-dock [data-previsit-view="catalog"]{display:none!important}' in styles
    assert "floatingVoice.hidden = previsitVisitSection !== 'order';" in script
    assert "floatingVoice.hidden = previsitVisitSection !== 'order' || previsitActiveView !== 'cart';" not in script
    assert "html.web-road-theme .previsit-invoice-head" in styles
    assert "background:#1b1c18!important" in styles


def test_order_quantities_are_capped_to_selected_inventory_and_saved_requests_are_dark():
    static = ROOT / "app" / "static"
    script = (static / "assistant.js").read_text(encoding="utf-8")
    styles = (static / "previsit-workspace.css").read_text(encoding="utf-8")

    assert "function clampPrevisitQuantityToInventory" in script
    assert "inCart + Number(unit.factor || 1) > available" in script
    assert "normalizePrevisitUnitQuantitiesToBase(product, acceptedQuantity)" in script
    assert "html.web-road-theme .previsit-saved-requests>header" in styles
    assert "html.web-road-theme .previsit-saved-invoice table" in styles


def test_final_calculation_and_credit_panels_do_not_fall_back_to_white():
    styles = (ROOT / "app" / "static" / "previsit-workspace.css").read_text(encoding="utf-8")

    assert "html.web-road-theme .previsit-preview-result{border-color:#5b4e2c!important;background:#171815!important" in styles
    assert "html.web-road-theme .previsit-preview-result .previsit-totals span" in styles
    assert "html.web-road-theme .previsit-credit-control" in styles
    assert "html.web-road-theme .previsit-credit-warning" in styles
    assert "html.web-road-theme .previsit-outcome-dialog" in styles


def test_company_road_mark_is_configured_as_android_launcher_icon():
    android_root = ROOT / "android" / "SellerNavigator" / "app" / "src" / "main"
    manifest = (android_root / "AndroidManifest.xml").read_text(encoding="utf-8")

    assert 'android:icon="@mipmap/ic_launcher"' in manifest
    assert 'android:roundIcon="@mipmap/ic_launcher_round"' in manifest
    for density, size in {
        "mdpi": 48,
        "hdpi": 72,
        "xhdpi": 96,
        "xxhdpi": 144,
        "xxxhdpi": 192,
    }.items():
        icon = android_root / "res" / f"mipmap-{density}" / "ic_launcher.png"
        round_icon = android_root / "res" / f"mipmap-{density}" / "ic_launcher_round.png"
        assert _png_size(icon) == (size, size)
        assert _png_size(round_icon) == (size, size)
