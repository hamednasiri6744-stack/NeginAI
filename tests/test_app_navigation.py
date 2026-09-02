def test_web_app_registers_each_major_screen_in_browser_history(client):
    script = client.get("/static/assistant.js?v=151").text

    assert "const APP_HISTORY_MARKER = 'negin-app-navigation-v1';" in script
    assert "history.pushState(next, '', location.href);" in script
    assert "window.addEventListener('popstate'" in script
    assert "window.NeginAppNavigation = {back: backInsideApp};" in script

    for view in (
        "notifications",
        "organization",
        "seller-workspace",
        "route-map",
        "customer-profile",
        "previsit",
        "schema-catalog",
        "schema-detail",
    ):
        assert f"rememberAppView('{view}'" in script


def test_back_closes_transient_ui_before_leaving_the_current_screen(client):
    script = client.get("/static/assistant.js?v=151").text

    assert "function closeTransientAppUi()" in script
    assert "closePrevisitTableMode();" in script
    assert "const dialog = $('dialog[open]:not(#keyDialog)');" in script
    assert "document.body.classList.contains('sidebar-open')" in script
    assert script.index("if (closeTransientAppUi()) return true;") < script.index("history.back();", script.index("function backInsideApp()"))


def test_android_hardware_back_delegates_to_web_history_before_fallback():
    activity = open(
        "android/SellerNavigator/app/src/main/java/ir/neginpakhsh/seller/AssistantActivity.kt",
        encoding="utf-8",
    ).read()

    back_handler = activity[activity.index("private fun configureBackNavigation()") :]
    assert "window.NeginAppNavigation.back()" in back_handler
    assert "webView.evaluateJavascript" in back_handler
    assert "if (handled != \"true\")" in back_handler
    assert back_handler.index("window.NeginAppNavigation.back()") < back_handler.index("webView.canGoBack()")
    assert "if (webView.canGoBack()) webView.goBack() else finish()" in back_handler


def test_internal_visit_sections_replace_the_current_screen_history(client):
    script = client.get("/static/assistant.js?v=151").text

    assert "if (current?.view === view)" in script
    assert "history.replaceState({...current, detail}, '', location.href);" in script
    assert "sameAppViewDetail" not in script
    assert "navigatePrevisitState({section: button.dataset.previsitSection})" in script


def test_order_assistant_and_customer_context_are_shared_by_all_order_modes(client):
    script = client.get("/static/assistant.js?v=151").text
    styles = client.get("/static/previsit-workspace.css?v=3").text

    assert "orderCommon.id = 'previsitOrderCommon';" in script
    assert "orderCommon.append(orderConditions, assistant);" in script
    assert "cart.querySelector('.previsit-order-conditions')" in script
    assert "orderWorkspace.append(orderCommon, listView, groupedView, catalogView, quickView, cartView, mobileDock);" in script
    assert "quickView.append(legacyPicker);" in script
    assert "quickView.append(assistant" not in script
    assert "renderPrevisitCustomerHeader" in script
    assert 'id="previsitCustomerSummary"' in script
    assert "previsit-customer-sticky-header" in script
    assert "customer.address || 'نشانی مشتری ثبت نشده است'" in script
    assert "customer.mobile || customer.phone" in script
    assert ".previsit-customer-header-meta" in styles
    assert ".previsit-cart-header{position:sticky;top:0;z-index:30" in styles
    assert "body.previsit-table-open .previsit-order-common{display:none!important}" in styles
