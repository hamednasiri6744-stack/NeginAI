def test_assistant_ui_has_camera_files_excel_and_right_sidebar(client):
    page = client.get("/assistant").text
    script = client.get("/static/assistant.js?v=151").text
    styles = client.get("/static/assistant.css?v=90").text

    assert 'assistant.css?v=106' in page
    assert 'assistant.js?v=213' in page
    assert 'id="previsitOrderCommand"' not in page  # The order UI is rendered only after a visit starts.
    assert "function runPrevisitOrderCommand" in script
    assert "runPrevisitOrderCommand({source: 'voice'})" in script
    assert "togglePrevisitOrderPanel('assistant', true)" in script
    assert "دستور شنیده شد؛ برای افزودن هوشمند بزنید." not in script
    assert "function toggleOrderCommandVoice" in script
    assert "commandMatches(command)" in script
    assert "const exactQueries = new Set" in script
    assert "exactQueries.has(query) ? exactToken(query, candidate) : closeToken(query, candidate)" in script
    assert "const satisfiesExactTerms = [...exactQueries].every" in script
    assert "item.satisfiesExactTerms" in script
    assert "async function readJsonResponse" in script
    assert "میسیوک:'میسویک'" in script
    assert "لمنت:'لمینت'" in script
    assert "لامینت:'لمینت'" in script
    assert "کارتون:'کارتن'" in script
    assert "پک:'بسته'" in script
    assert "mode: 'order'" in script
    assert "function catalogPhoneticSignature" in script
    assert "function crossScriptCatalogToken" in script
    assert "crossScriptCatalogToken(query, candidate)" in script
    assert "requestMicrophonePermission" in script
    assert "negin-microphone-permission" in script
    assert "startOrderVoiceRecording" in script
    assert "negin-native-order-voice" in script
    assert "function parseSpokenOrderNumber" in script
    assert "سه: 3" in script
    assert "بیست: 20" in script
    assert "function commandQuantityMentions" in script
    assert "function parseOrderCommandItems" in script
    assert "unit: mention.unit" in script
    assert "function spokenOrderSaleUnit" in script
    assert "function previsitVoiceOrderConversion" in script
    assert "function addPrevisitVoiceLine" in script
    assert "amount * Number(saleUnit.factor || 1)" in script
    assert "function commandDetectedBrands" in script
    assert "const sharedBrand = detectedBrands.length === 1" in script
    assert "items.forEach((item, itemIndex)" in script
    assert "data-previsit-command-group" in script
    assert "reportVoiceFailure('order-voice-start'" in script
    assert 'id="androidDownloadHeader"' in page
    assert 'id="androidDownloadLogin"' in page
    assert 'href="/download/android"' in page
    assert "location.href = '/download/android';" in script
    assert 'autocapitalize="none"' in page
    assert 'enterkeyhint="next"' in page
    assert "font-size:16px" in styles
    assert 'inputmode="text"' in page
    assert 'enterkeyhint="send"' in page
    assert 'autocapitalize="sentences"' in page
    assert "function focusMessageInput()" in script
    assert "if (!isIOS) input.focus();" in script
    assert "function prepareIOSKeyboardForNativeTap()" in script
    assert "input.addEventListener('touchstart', prepareIOSKeyboardForNativeTap" in script
    assert "input.addEventListener('click', finishIOSKeyboardNativeTap)" in script
    assert "document.activeElement !== input" in script
    assert "iosSoftwareKeyboardIsVisible()" in script
    assert "input.blur();\n  input.focus" not in script
    assert "card.open = Boolean(data?.presentation?.expand_result)" in script
    assert "visible_row_limit" in script
    assert "rows.slice(0, visibleLimit)" in script
    assert "iosAuthFocusRecoveryPending" not in script
    assert "field.blur()" not in script
    assert 'id="accountSettingsBtn"' in page
    assert 'id="accountDialog"' in page
    assert "/auth/change-password" in script
    assert "profile?.must_change_password" in script
    assert 'id="cameraInput"' in page
    assert 'capture="environment"' in page
    assert 'id="fileInput"' in page
    assert 'id="audioCaptureInput"' in page
    assert '<input id="audioCaptureInput" type="file" accept="audio/*" capture hidden>' in page
    assert 'aria-label="ضبط صدا و تبدیل به متن"' in page
    assert "/attachments/analyze" in script
    assert "async function requestHealthyMicrophoneStream" in script
    assert "getUserMedia({audio: true})" in script
    assert "AudioDeviceUnavailableError" in script
    assert "new MediaRecorder(mediaStream" in script
    assert "audio/mp4;codecs=mp4a.40.2" in script
    assert "recorder.start(250);" in script
    assert "/audio/client-events" in script
    assert "createScriptProcessor(4096, 1, 1)" in script
    assert "pcmSilentGain.gain.value = 0" in script
    assert "encodePcmWav" in script
    assert "type: 'audio/wav'" in script
    assert "await preparePcmAudioContext()" in script
    assert "async function resetVoiceCapture" in script
    assert "window.addEventListener('pagehide'" in script
    assert "pcmAudioContext.state === 'closed'" in script
    assert "mediaStream = await requestHealthyMicrophoneStream();" in script
    assert "if (isIOS) {\n      startStage = 'connect-pcm'" not in script
    assert "reportVoiceFailure(`start-${startStage}`, error)" in script
    assert "resetIOSVoicePage" not in script
    assert "settleIOSVoiceAfterRecovery" not in script
    assert "location.replace(`/assistant?audio-reset=" not in script
    assert "webkitSpeechRecognition" not in script
    assert "transcribeRecording(blob)" in script
    assert "sessionStorage.removeItem('negin-ios-native-voice')" in script
    assert "در حال تشخیص فرایند ورانگر" in script
    assert "در حال انتخاب گزارش مرجع" in script
    assert "در حال اجرای گزارش و ساخت پاسخ" in script
    assert "data-thinking-time" in script
    assert ".thinking-progress" in styles
    assert "excel-file-card" in script
    assert "گزارش نگین پخش.xlsx" in script
    assert "excelRequested" in script
    assert "const shouldOfferExcel = excelRequested(userMessage);" in script
    assert "const shouldOfferExcel = hasColumns || excelRequested(userMessage);" not in script
    assert "function isMarkdownTableDivider" in script
    assert 'class="message-table-wrap"' in script
    assert ".message-table-wrap table" in styles
    assert ".excel-file-card" in styles
    assert "mediaRecorder.requestData()" in script
    assert 'id="cameraBtn"' in page
    assert 'id="fileBtn"' in page
    assert "data-export-excel" in script
    assert 'id="excelPreviewDialog"' in page
    assert 'id="closeExcelPreview"' in page
    assert 'id="downloadExcelBtn"' in page
    assert "openExcelPreview(excel.dataset.exportExcel)" in script
    assert "link.target = '_blank'" in script
    assert "if (!isIOS && !standalone) link.download = '';" in script
    assert "بازکردن در صفحه جدید" in script
    assert "$('#closeExcelPreview')?.addEventListener" in script
    assert "excelPreviewDialog?.addEventListener" in script
    assert ".excel-preview-dialog" in styles
    assert "report-context-card" in script
    assert ".report-context-card" in styles
    assert "direction:rtl" in styles
    assert "inset:0 0 0 auto" in styles
    assert "https://www.waze.com/ul?${wazeDestination}&navigate=yes" in script
    assert "const wazeDestination = coordinates ? `ll=${coordinates}` : `q=${addressDestination}`;" in script
    assert "موقعیت مکانی ثبت شده" in script
    assert ".seller-location-status" in styles
    assert "routeMapPanel" in script
    assert "window.maplibregl?.default || window.maplibregl" in script
    assert "SpeechSynthesisUtterance" in script
    assert "routeMapCustomerPopup" in script
    assert 'id="routeMapVoiceBtn"' in page
    assert 'id="routeMapRecenterBtn"' in page
    assert "updateRouteNavigationProgress" in script
    assert "speakPersian" in script
    assert "از مسیر خارج شدید" in script
    assert "SpeechSynthesisUtterance" in script
    assert "https://static.neshan.org/sdk/maplibre/5.24.3/neshan-maplibre-sdk.umd.js" in page
    assert "https://maps.apple.com/?daddr=${destination}&dirflg=d" in script
    assert "https://www.google.com/maps/dir/?api=1&destination=${destination}&travelmode=driving" in script
