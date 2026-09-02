const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

const messages = $('#messages');
const form = $('#chatForm');
const input = $('#message');
const sendBtn = $('#sendBtn');
const voiceBtn = $('#voiceBtn');
const attachBtn = $('#attachBtn');
const cameraBtn = $('#cameraBtn');
const fileBtn = $('#fileBtn');
const attachMenu = $('#attachMenu');
const attachmentPreview = $('#attachmentPreview');
const recordingBar = $('#recordingBar');
const statusEl = $('#status');
const loginDialog = $('#keyDialog');
const accountDialog = $('#accountDialog');
const notificationBtn = $('#notificationBtn');
const notificationsPanel = $('#notificationsPanel');
const notificationsList = $('#notificationsList');
const organizationStructurePanel = $('#organizationStructurePanel');
const organizationRulesList = $('#organizationRulesList');
const organizationProposalsList = $('#organizationProposalsList');
const sellerWorkspacePanel = $('#sellerWorkspacePanel');
const customerProfilePanel = $('#customerProfilePanel');
const previsitPanel = $('#previsitPanel');
const previsitBtn = $('#previsitBtn');
const sellerRecommendationsBtn = $('#sellerRecommendationsBtn');
const myRoutesList = $('#myRoutesList');
const myBrandsList = $('#myBrandsList');
const schemaCatalogPanel = $('#schemaCatalogPanel');
const routeMapPanel = $('#routeMapPanel');
const routeDayActionRail = $('#routeDayActionRail');
const schemaCatalogGroups = $('#schemaCatalogGroups');
const schemaDetailPanel = $('#schemaDetailPanel');
const inboxBadge = $('#inboxBadge');
const excelPreviewDialog = $('#excelPreviewDialog');
const excelPreviewStore = new Map();

let conversationId = null;
let conversations = [];
let activeController = null;
let lastUserMessage = '';
let installPrompt = null;
let serviceWorkerRegistration = null;
let notificationsCache = [];
let schemaCatalogCache = [];
let routeMapInstance = null;
let routeMapSession = null;
let customerProfileState = null;
let routeMapLocationWatch = null;
let routeMapSellerMarker = null;
let navigationAudioContext = null;
let navigationAudioSource = null;
let navigationSpeechAbortController = null;
let navigationSpeechSequence = 0;
const navigationSpeechCache = new Map();
let mediaRecorder = null;
let mediaStream = null;
let audioChunks = [];
let pcmAudioContext = null;
let pcmSource = null;
let pcmProcessor = null;
let pcmSilentGain = null;
let pcmChunks = [];
let pcmSampleRate = 48000;
let pcmRecorderActive = false;
let recordingStartedAt = 0;
let voiceTimerHandle = null;
let cancelRecording = false;
let pendingAttachment = null;
let currentProfile = null;
let forceAccountDialog = false;
let sellerCoachingSession = false;
let dayRouteSession = false;
let selectedDayRouteId = null;
let previsitSession = null;
let previsitContext = null;
let previsitPreview = null;
let previsitPolicy = null;
let previsitWorkspace = null;
let pendingPrevisitOutcome = null;
let pendingRouteNoVisit = null;
let previsitCatalogState = {query: '', brand: '', group: '', inStock: true, sort: 'code'};
let previsitQuickFilterState = {query: '', group: '', brand: ''};
let previsitListState = {query: '', group: '', brand: '', inStock: true};
let previsitListCompact = localStorage.getItem('negin-previsit-list-density') !== 'comfortable';
let previsitGroupedCatalogState = {query: '', group: '', brand: '', inStock: true};
const previsitProductUnitSelections = new Map();
const previsitProductUnitQuantities = new Map();
let previsitActiveView = 'catalog';
let previsitOrderMode = 'list';
let previsitVisitSection = 'profile';
let previsitEmbeddedProfile = null;
let previsitSavedRequests = [];
let previsitEditingSavedRequestId = null;
let previsitViewingSavedRequestId = null;
let previsitTableProducts = [];
let previsitTableIndex = 0;
let previsitTableSwipeStart = null;
let previsitStickyObserver = null;
let previsitVisitTimerHandle = null;
let previsitVisitStartedAt = null;
let previsitLocationPickerMap = null;
let previsitLocationPickerMarker = null;
let previsitLocationPickerCoordinates = null;
let orderCommandRecorder = null;
let orderCommandStream = null;
let orderCommandChunks = [];
let orderCommandAwaitingNativePermission = false;
let orderCommandNativeRecording = false;
let previsitListLastScrollY = window.scrollY;
let previsitListScrollFrame = 0;
let appNavigationReady = false;
let appHistoryApplying = false;

const APP_HISTORY_MARKER = 'negin-app-navigation-v1';

const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
const isAndroid = /Android/i.test(navigator.userAgent);
const isNeginAndroidApp = /NeginSellerAndroid\//i.test(navigator.userAgent);
if (isNeginAndroidApp) document.documentElement.classList.add('negin-android-app');
document.documentElement.classList.add('web-road-theme');
const standalone = matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
const isLocal = ['localhost', '127.0.0.1'].includes(location.hostname);
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function readJsonResponse(response, fallbackMessage) {
  const raw = await response.text();
  if (!raw) return {};
  try {
    return JSON.parse(raw);
  } catch (_error) {
    const detail = response.status >= 500
      ? 'ارتباط با سرویس سفارش‌گیری موقتاً قطع شد؛ چند لحظه بعد دوباره تلاش کنید.'
      : fallbackMessage;
    return {detail};
  }
}

function focusMessageInput() {
  // WebKit can leave a textarea visually focused after the software keyboard
  // was dismissed. A later programmatic focus does not reopen the keyboard and
  // makes the next tap look ineffective. Let iOS acquire focus only from the
  // user's own tap; desktop keeps the convenient automatic refocus behavior.
  if (!isIOS) input.focus();
}

function iosSoftwareKeyboardIsVisible() {
  if (!isIOS || !window.visualViewport) return false;
  return window.innerHeight - window.visualViewport.height > 120;
}

function prepareIOSKeyboardForNativeTap() {
  if (!isIOS || document.activeElement !== input || iosSoftwareKeyboardIsVisible()) return;
  // Release stale focus at the beginning of the gesture. WebKit's native click
  // that follows this touch can then focus the textarea and open the keyboard.
  // Calling focus ourselves at touchend only restores the caret/accessory bar.
  input.blur();
}

function finishIOSKeyboardNativeTap() {
  if (isIOS && document.activeElement !== input) input.focus({preventScroll: true});
}

function toast(text) {
  const element = $('#toast');
  element.textContent = text;
  element.classList.add('show');
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => element.classList.remove('show'), 2300);
}

function setStatus(text, healthy = true) {
  statusEl.lastChild.textContent = text;
  const dot = $('i', statusEl);
  dot.style.background = healthy ? '#19a474' : '#d33f3f';
}

function openSidebar() {
  document.body.classList.add('sidebar-open');
  $('#sidebarBackdrop').hidden = false;
}

function closeSidebar() {
  document.body.classList.remove('sidebar-open');
  $('#sidebarBackdrop').hidden = true;
}

function appHistoryState() {
  const state = history.state;
  return state?.marker === APP_HISTORY_MARKER ? state : null;
}

function applyAppView(state, {restore = true} = {}) {
  if (!state || state.marker !== APP_HISTORY_MARKER) return;
  appHistoryApplying = true;
  const mapWasVisible = !routeMapPanel.hidden;
  [notificationsPanel, organizationStructurePanel, sellerWorkspacePanel, customerProfilePanel, previsitPanel, schemaCatalogPanel, routeMapPanel]
    .forEach((panel) => { panel.hidden = true; });
  schemaDetailPanel.hidden = true;
  closeSidebar();

  if (state.view === 'notifications') notificationsPanel.hidden = false;
  else if (state.view === 'organization') organizationStructurePanel.hidden = false;
  else if (state.view === 'seller-workspace') sellerWorkspacePanel.hidden = false;
  else if (state.view === 'customer-profile') customerProfilePanel.hidden = false;
  else if (state.view === 'previsit') {
    previsitPanel.hidden = false;
    const detail = state.detail || {};
    if ($('#previsitCart')?.dataset.ngtUi === '2') {
      switchPrevisitOrderMode(detail.orderMode || 'list');
      switchPrevisitVisitSection(detail.section || 'order');
      switchPrevisitView(detail.activeView || 'catalog');
    }
  } else if (state.view === 'schema-catalog' || state.view === 'schema-detail') {
    schemaCatalogPanel.hidden = false;
    schemaDetailPanel.hidden = state.view !== 'schema-detail';
  } else if (state.view === 'route-map') {
    routeMapPanel.hidden = false;
    const detail = state.detail || {};
    if (restore && detail.pathId && String(routeMapSession?.pathId) !== String(detail.pathId)) {
      void openRouteMap(detail.pathId, detail.title || 'مسیر روز');
    } else {
      requestAnimationFrame(() => routeMapInstance?.resize());
    }
  }

  if (mapWasVisible && !['route-map', 'customer-profile'].includes(state.view)) stopRouteMap();
  if (state.view === 'home' && location.search) history.replaceState(state, '', '/assistant');
  appHistoryApplying = false;
}

function rememberAppView(view, detail = {}) {
  if (!appNavigationReady || appHistoryApplying) return;
  const current = appHistoryState();
  const next = {
    marker: APP_HISTORY_MARKER,
    view,
    detail,
    depth: current ? Number(current.depth || 0) + 1 : 1,
  };
  // Tabs, filters and sections inside one screen update that screen's state;
  // they must not consume extra Back presses. Only a different screen pushes.
  if (current?.view === view) {
    history.replaceState({...current, detail}, '', location.href);
    applyAppView({...current, detail}, {restore: false});
    return;
  }
  history.pushState(next, '', location.href);
  applyAppView(next, {restore: false});
}

function closeCurrentAppView(view, fallback) {
  const current = appHistoryState();
  if (current?.view === view && Number(current.depth || 0) > 0) {
    history.back();
    return true;
  }
  fallback?.();
  return false;
}

function closeTransientAppUi() {
  const tableOverlay = $('#previsitTableOverlay');
  if (tableOverlay && !tableOverlay.hidden) {
    closePrevisitTableMode();
    return true;
  }
  const dialog = $('dialog[open]:not(#keyDialog)');
  if (dialog) {
    if (dialog === accountDialog && forceAccountDialog) return true;
    dialog.close();
    return true;
  }
  if (document.body.classList.contains('sidebar-open')) {
    closeSidebar();
    return true;
  }
  return false;
}

function backInsideApp() {
  if (closeTransientAppUi()) return true;
  const current = appHistoryState();
  if (!current || Number(current.depth || 0) <= 0) return false;
  history.back();
  return true;
}

function initializeAppNavigation() {
  const initialState = {marker: APP_HISTORY_MARKER, view: 'home', detail: {}, depth: 0};
  history.replaceState(initialState, '', location.href);
  appNavigationReady = true;
  window.NeginAppNavigation = {back: backInsideApp};
}

window.addEventListener('popstate', (event) => {
  const state = event.state?.marker === APP_HISTORY_MARKER
    ? event.state
    : {marker: APP_HISTORY_MARKER, view: 'home', detail: {}, depth: 0};
  applyAppView(state);
});

function welcomeMarkup() {
  return `<div id="welcome" class="welcome">
    <div class="welcome-logo" aria-hidden="true">ن</div>
    <h1>چه کمکی از دستم برمیاد؟</h1>
    <p>گزارش‌های فروش، فاکتور، وصول، تسویه و انبار را بر پایهٔ ساختار واقعی ورانگر تحلیل کن.</p>
    <div class="suggestions">
      <button type="button" data-prompt="گزارش فروش من از ابتدای ماه تا امروز را بده: تعداد فاکتور، تعداد حواله، تعداد مشتری، فروش ناخالص، مبلغ برگشتی و فروش خالص پس از کسر برگشتی."><strong>خلاصه فروش ماه</strong><span>فاکتور، حواله، مشتری و فروش خالص</span></button>
      <button type="button" data-prompt="گزارش فروش من از ابتدای ماه تا امروز را به تفکیک تولیدکننده بده: تعداد فاکتور، تعداد حواله، تعداد مشتری، فروش ناخالص، مبلغ برگشتی و فروش خالص پس از کسر برگشتی."><strong>فروش بر اساس تولیدکننده</strong><span>عملکرد ماه جاری هر تولیدکننده</span></button>
      <button type="button" data-prompt="گزارش فروش من از ابتدای ماه تا امروز را به تفکیک برند بده. برای هر برند، فروش تعدادی و فروش کارتنی خالص را نشان بده. فروش تعدادی خالص هر SKU برابر تعداد فروش منهای تعداد برگشتی است؛ فروش کارتنی همان مقدار خالص هر SKU تقسیم بر ضریب تبدیل همان SKU است و سپس در سطح برند جمع می‌شود."><strong>فروش برند و کارتن</strong><span>تعداد خالص و کارتن خالص بر پایه SKU</span></button>
    </div>
  </div>`;
}

function scrollToEnd() {
  requestAnimationFrame(() => { messages.scrollTop = messages.scrollHeight; });
}

function hideWelcome() {
  $('#welcome')?.remove();
}

function renderInlineMarkdown(text) {
  return esc(text).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
}

function markdownTableCells(line) {
  return line.trim().replace(/^\||\|$/g, '').split('|').map((cell) => cell.trim());
}

function isMarkdownTableDivider(line = '') {
  const cells = markdownTableCells(line);
  return cells.length > 1 && cells.every((cell) => /^:?-{3,}:?$/.test(cell));
}

function renderAssistantText(element, text) {
  const lines = String(text || '').replace(/\r/g, '').split('\n');
  const html = [];
  for (let index = 0; index < lines.length;) {
    const line = lines[index];
    if (line.includes('|') && isMarkdownTableDivider(lines[index + 1])) {
      const headers = markdownTableCells(line);
      const rows = [];
      index += 2;
      while (index < lines.length && lines[index].includes('|') && lines[index].trim()) {
        rows.push(markdownTableCells(lines[index]));
        index += 1;
      }
      html.push(`<div class="message-table-wrap"><table><thead><tr>${headers.map((cell) => `<th>${renderInlineMarkdown(cell)}</th>`).join('')}</tr></thead><tbody>${rows.map((row) => `<tr>${headers.map((_, cellIndex) => `<td>${renderInlineMarkdown(row[cellIndex] || '')}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`);
      continue;
    }
    if (/^\s*[-•]\s+/.test(line)) {
      const items = [];
      while (index < lines.length && /^\s*[-•]\s+/.test(lines[index])) {
        items.push(lines[index].replace(/^\s*[-•]\s+/, ''));
        index += 1;
      }
      html.push(`<ul>${items.map((item) => `<li>${renderInlineMarkdown(item)}</li>`).join('')}</ul>`);
      continue;
    }
    if (!line.trim()) {
      index += 1;
      continue;
    }
    const paragraph = [];
    while (index < lines.length && lines[index].trim() && !(lines[index].includes('|') && isMarkdownTableDivider(lines[index + 1])) && !/^\s*[-•]\s+/.test(lines[index])) {
      paragraph.push(lines[index]);
      index += 1;
    }
    html.push(`<p>${paragraph.map(renderInlineMarkdown).join('<br>')}</p>`);
  }
  element.innerHTML = html.join('');
}

function messageActions() {
  const actions = document.createElement('div');
  actions.className = 'message-actions';
  actions.innerHTML = '<button type="button" data-copy>کپی</button><button type="button" data-retry>تلاش دوباره</button>';
  return actions;
}

function addMessage(text, kind = 'assistant', options = {}) {
  hideWelcome();
  const row = document.createElement('article');
  row.className = `message-row ${kind}`;
  if (kind === 'assistant') {
    const avatar = document.createElement('div');
    avatar.className = 'assistant-avatar';
    avatar.setAttribute('aria-hidden', 'true');
    avatar.textContent = 'ن';
    row.append(avatar);
  }
  const content = document.createElement('div');
  content.className = 'message-content';
  const bubble = document.createElement('div');
  bubble.className = 'message';
  if (kind === 'user' && options.attachment) {
    const attachment = document.createElement('div');
    attachment.className = 'message-attachment';
    if (options.attachment.kind === 'image' && options.attachment.previewUrl) {
      attachment.innerHTML = `<img src="${esc(options.attachment.previewUrl)}" alt=""><span>${esc(options.attachment.file.name)}</span>`;
    } else {
      attachment.innerHTML = `<i aria-hidden="true">📎</i><span>${esc(options.attachment.file.name)}</span>`;
    }
    content.append(attachment);
  }
  if (kind === 'assistant') renderAssistantText(bubble, text);
  else bubble.textContent = text;
  content.append(bubble);
  if (kind === 'assistant' && !options.pending) content.append(messageActions());
  row.append(content);
  messages.append(row);
  if (!options.noScroll) scrollToEnd();
  return {row, bubble, content};
}

function addThinking() {
  const item = addMessage('', 'assistant', {pending: true});
  item.bubble.innerHTML = `<div class="thinking-progress" aria-live="polite">
    <div class="thinking-head"><span class="thinking-spinner" aria-hidden="true"></span><strong data-thinking-title>در حال بررسی درخواست شما</strong><time data-thinking-time>۰ ثانیه</time></div>
    <p data-thinking-detail>درخواست دریافت شد و در صف پردازش قرار گرفت.</p>
    <div class="thinking-history" data-thinking-history></div>
  </div>`;
  item.progress = {
    startedAt: Date.now(),
    current: 'درخواست دریافت شد',
    completed: [],
    timeouts: [],
    interval: setInterval(() => {
      const seconds = Math.max(0, Math.floor((Date.now() - item.progress.startedAt) / 1000));
      const time = $('[data-thinking-time]', item.bubble);
      if (time) time.textContent = `${seconds.toLocaleString('fa-IR')} ثانیه`;
    }, 1000),
  };
  return item;
}

function setThinkingStage(item, title, detail) {
  if (!item?.progress || !item.bubble.isConnected) return;
  if (item.progress.current && item.progress.current !== title) {
    item.progress.completed.push(item.progress.current);
    item.progress.completed = item.progress.completed.slice(-2);
  }
  item.progress.current = title;
  const titleNode = $('[data-thinking-title]', item.bubble);
  const detailNode = $('[data-thinking-detail]', item.bubble);
  const historyNode = $('[data-thinking-history]', item.bubble);
  if (titleNode) titleNode.textContent = title;
  if (detailNode) detailNode.textContent = detail;
  if (historyNode) historyNode.innerHTML = item.progress.completed.map((step) => `<span>✓ ${esc(step)}</span>`).join('');
  scrollToEnd();
}

function scheduleThinkingStages(item, stages) {
  for (const timeout of item.progress?.timeouts || []) clearTimeout(timeout);
  if (!item.progress) return;
  item.progress.timeouts = stages.map(([delay, title, detail]) => setTimeout(() => {
    setThinkingStage(item, title, detail);
  }, delay));
}

function stopThinkingProgress(item) {
  if (!item?.progress) return;
  clearInterval(item.progress.interval);
  for (const timeout of item.progress.timeouts) clearTimeout(timeout);
  item.progress = null;
}

function excelRequested(message = '') {
  const normalized = String(message).replace(/\s+/g, ' ').trim();
  if (!/(?:اکسل|اِکسل|excel|xlsx)/i.test(normalized)) return false;
  return !/(?:اکسل|اِکسل|excel|xlsx).{0,18}(?:نمی\s*خوام|نمی\s*خواهم|نده|لازم نیست)|(?:بدون|نه).{0,12}(?:اکسل|اِکسل|excel|xlsx)/i.test(normalized);
}

function excelPreviewData(data = {}) {
  const sourceColumns = Array.isArray(data.columns) ? data.columns : [];
  const sourceRows = Array.isArray(data.rows) ? data.rows : [];
  if (sourceColumns.length) return {columns: sourceColumns, rows: sourceRows};
  const lines = String(data.answer || '').split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  return {columns: ['گزارش'], rows: (lines.length ? lines : ['گزارش آماده شد.']).map((line) => [line])};
}

function openExcelPreview(exportId) {
  const preview = excelPreviewStore.get(exportId);
  if (!preview) return toast('پیش‌نمایش فایل در دسترس نیست.');
  if (!excelPreviewDialog || !$('#excelPreviewMeta') || !$('#excelPreviewBody') || !$('#downloadExcelBtn')) {
    downloadExcel(exportId);
    return;
  }
  const visibleRows = preview.rows.slice(0, 100);
  $('#excelPreviewMeta').textContent = `Microsoft Excel · ${preview.rows.length.toLocaleString('fa-IR')} ردیف`;
  $('#downloadExcelBtn').dataset.downloadExcel = exportId;
  $('#downloadExcelBtn').textContent = isIOS || standalone ? 'بازکردن در صفحه جدید' : 'دانلود فایل اصلی';
  $('#excelPreviewBody').innerHTML = `<table><thead><tr>${preview.columns.map((column) => `<th>${esc(column)}</th>`).join('')}</tr></thead><tbody>${visibleRows.map((row) => `<tr>${preview.columns.map((_, index) => `<td>${esc(row?.[index] ?? '')}</td>`).join('')}</tr>`).join('')}</tbody></table>${preview.rows.length > visibleRows.length ? `<p class="excel-preview-limit">${visibleRows.length.toLocaleString('fa-IR')} ردیف اول نمایش داده شده؛ فایل دانلودی شامل همه ردیف‌هاست.</p>` : ''}`;
  if (!excelPreviewDialog.open) excelPreviewDialog.showModal();
}

function closeExcelPreview() {
  if (excelPreviewDialog?.open) excelPreviewDialog.close();
}

function downloadExcel(exportId) {
  if (!exportId) return;
  const link = document.createElement('a');
  link.href = `/chat/conversations/${encodeURIComponent(exportId)}/export.xlsx`;
  link.target = '_blank';
  link.rel = 'noopener noreferrer';
  if (!isIOS && !standalone) link.download = '';
  document.body.append(link);
  link.click();
  link.remove();
}

function renderReportContext(data, container) {
  const context = data?.report_context;
  if (!context || (!context.label && !context.basis && !context.period)) return;
  const card = document.createElement('section');
  card.className = 'report-context-card';
  card.setAttribute('aria-label', 'مبنای تحلیل گزارش');
  const chips = [];
  if (context.period) chips.push(`<span><b>بازه</b>${esc(context.period)}</span>`);
  if (context.basis) chips.push(`<span><b>مبنا</b>${esc(context.basis)}</span>`);
  if (Array.isArray(data.sources) && data.sources.length) {
    chips.push(`<span><b>منابع</b>${data.sources.length.toLocaleString('fa-IR')} View تأییدشده</span>`);
  }
  card.innerHTML = `<div class="report-context-head"><i aria-hidden="true">◎</i><div><small>مسیر تشخیص‌داده‌شده</small><strong>${esc(context.label || 'تحلیل عمومی داده')}</strong></div></div><div class="report-context-chips">${chips.join('')}</div>`;
  container.append(card);
}

function isMonetaryReportColumn(column = '') {
  return /(?:amount|sales|price|balance|remaining|debit|credit|payamount)/i.test(String(column).replace(/_/g, ''));
}

function renderReportCell(column, value) {
  if (!isMonetaryReportColumn(column) || typeof value !== 'number' || !Number.isFinite(value)) return esc(value);
  return `${esc((value / 10).toLocaleString('fa-IR', {maximumFractionDigits: 2}))} تومان`;
}

function renderResult(data, container, userMessage = '') {
  if (data?.presentation?.hide_result) return;
  const hasColumns = Boolean(data?.columns?.length);
  const shouldOfferExcel = excelRequested(userMessage);
  renderReportContext(data, container);
  if (hasColumns || data?.sql) {
    const card = document.createElement('details');
    card.className = 'result-card';
    card.open = Boolean(data?.presentation?.expand_result);
    let html = '';
    if (hasColumns) {
    const rows = Array.isArray(data.rows) ? data.rows : [];
      const requestedLimit = Number(data?.presentation?.visible_row_limit || 50);
      const visibleLimit = Math.max(1, Math.min(rows.length, requestedLimit));
      html += `<summary class="result-title">مشاهده داده‌های گزارش · ${rows.length.toLocaleString('fa-IR')} ردیف</summary><div class="result"><table><thead><tr>${data.columns.map((column) => `<th>${esc(column)}${isMonetaryReportColumn(column) ? ' (تومان)' : ''}</th>`).join('')}</tr></thead><tbody>${rows.slice(0, visibleLimit).map((row) => `<tr>${row.map((cell, index) => `<td>${renderReportCell(data.columns[index], cell)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
    }
    if (!hasColumns) html += '<summary class="result-title">مشاهده جزئیات گزارش</summary>';
    if (data.sql || data?.sources?.length) {
      const sources = Array.isArray(data.sources) ? data.sources : [];
      html += `<details class="sql-details"><summary>نمایش منابع و جزئیات فنی</summary>${sources.length ? `<div class="result-sources">${sources.map((source) => `<span dir="ltr">${esc(source)}</span>`).join('')}</div>` : ''}${data.sql ? `<pre class="meta">${esc(data.sql)}</pre>` : ''}</details>`;
    }
    card.innerHTML = html;
    container.append(card);
  }
  if (shouldOfferExcel) {
    const exportId = data?.conversation_id || conversationId || '';
    const rowCount = Number(data?.row_count ?? data?.rows?.length ?? 0);
    excelPreviewStore.set(exportId, excelPreviewData(data));
    const file = document.createElement('button');
    file.type = 'button';
    file.className = 'excel-file-card';
    file.dataset.exportExcel = exportId;
    file.setAttribute('aria-label', 'پیش‌نمایش فایل Excel گزارش');
    file.innerHTML = `<span class="excel-file-icon" aria-hidden="true">X</span><span class="excel-file-copy"><strong>گزارش نگین پخش.xlsx</strong><small>Microsoft Excel${rowCount ? ` · ${rowCount.toLocaleString('fa-IR')} ردیف` : ''}</small></span><span class="excel-download-icon" aria-hidden="true">⌕</span>`;
    container.append(file);
  }
}

function resizeInput() {
  input.style.height = 'auto';
  input.style.height = `${Math.min(input.scrollHeight, 145)}px`;
  sendBtn.disabled = !input.value.trim() && !pendingAttachment && !activeController;
}

function setBusy(busy) {
  input.disabled = busy;
  voiceBtn.disabled = busy;
  attachBtn.disabled = busy;
  cameraBtn.disabled = busy;
  fileBtn.disabled = busy;
  sendBtn.classList.toggle('stop', busy);
  sendBtn.setAttribute('aria-label', busy ? 'توقف پاسخ' : 'ارسال پیام');
  sendBtn.textContent = busy ? '' : '↑';
  if (busy) sendBtn.disabled = false;
  else resizeInput();
}

function showLogin() {
  if (!loginDialog.open) {
    loginDialog.showModal();
  }
}

function applyProfile(profile) {
  if (!profile) return;
  currentProfile = profile;
  const displayName = profile.full_name || profile.username;
  localStorage.setItem('negin-display-user', displayName);
  $('#profileName').textContent = displayName;
  const isSeller = String(profile.role || '').trim() === '\u0641\u0631\u0648\u0634\u0646\u062f\u0647';
  const normalizedRole = String(profile.role || '').trim().toLocaleLowerCase('fa');
  const isAdmin = ['admin', 'administrator', '\u0645\u062f\u06cc\u0631', '\u0645\u062f\u06cc\u0631 \u0633\u06cc\u0633\u062a\u0645', '\u0645\u062f\u06cc\u0631 \u0633\u0627\u0645\u0627\u0646\u0647'].includes(normalizedRole)
    || String(profile.username || '').trim().toLocaleLowerCase('en') === 'admin';
  const permissions = profile.permissions || [];
  $('#planningBtn').hidden = !(isAdmin || permissions.includes('planning.manage'));
  $('#organizationStructureBtn').hidden = !(isAdmin || permissions.includes('organization.manage'));
  $('#controlBtn').hidden = !(isAdmin || permissions.includes('control.manage'));
  $('#myRoutesBtn').hidden = !isSeller;
  $('#dayRouteBtn').hidden = !isSeller;
  $('#myOpenInvoicesBtn').hidden = !isSeller;
  $('#myDistributionInProgressBtn').hidden = !isSeller;
  $('#myReturnedChequesBtn').hidden = !isSeller;
  $('#myVoucherReturnReportBtn').hidden = !isSeller;
  $('#myBrandsBtn').hidden = !isSeller;
  previsitBtn.hidden = !isSeller;
  sellerRecommendationsBtn.hidden = !isSeller;
}

async function loadCurrentProfile() {
  const response = await fetch('/auth/me', {headers: {'Accept': 'application/json'}});
  if (response.status === 401) return null;
  if (!response.ok) throw Error('دریافت اطلاعات حساب انجام نشد.');
  const profile = await response.json();
  applyProfile(profile);
  return profile;
}

function openAccountDialog(profile, force = false) {
  applyProfile(profile);
  forceAccountDialog = Boolean(force);
  $('#accountDialogTitle').textContent = force ? 'رمز موقت را تغییر دهید' : 'تنظیمات حساب';
  $('#accountDialogHint').textContent = force
    ? 'برای حفاظت از اطلاعات شرکت، پیش از ادامه یک رمز شخصی حداقل ۸ کاراکتری بسازید.'
    : 'اطلاعات حساب سازمانی و رمز ورود خود را مدیریت کنید.';
  $('#accountFullName').textContent = profile.full_name || '—';
  $('#accountUsername').textContent = profile.username || '—';
  $('#accountPhone').textContent = profile.phone || 'ثبت نشده';
  $('#closeAccountDialog').hidden = force;
  $('#changePasswordError').textContent = '';
  $('#currentPassword').value = '';
  $('#newPassword').value = '';
  $('#confirmPassword').value = '';
  if (!accountDialog.open) accountDialog.showModal();
  setTimeout(() => $('#currentPassword').focus(), 50);
}

function conversationItem(item) {
  const pin = item.pinned ? '<span class="pin-mark" aria-label="سنجاق‌شده">●</span>' : '';
  return `<article class="conversation-item${item.id === conversationId ? ' active' : ''}" data-conversation-item="${esc(item.id)}">
    <button class="conversation-main" type="button" data-open-conversation="${esc(item.id)}">${pin}<span class="conversation-title">${esc(item.title)}</span></button>
    <button class="conversation-more" type="button" data-conversation-more="${esc(item.id)}" aria-label="گزینه‌های گفتگو">•••</button>
    <div class="conversation-menu" hidden>
      <button type="button" data-pin-conversation="${esc(item.id)}">${item.pinned ? 'برداشتن سنجاق' : 'سنجاق‌کردن'}</button>
      <button type="button" data-rename-conversation="${esc(item.id)}">تغییر نام</button>
      <button class="danger" type="button" data-delete-conversation="${esc(item.id)}">حذف</button>
    </div>
  </article>`;
}

function renderConversations() {
  const query = $('#conversationSearch').value.trim().toLocaleLowerCase('fa');
  const filtered = conversations.filter((item) => !query || item.title.toLocaleLowerCase('fa').includes(query));
  const pinned = filtered.filter((item) => item.pinned);
  const recent = filtered.filter((item) => !item.pinned);
  $('#pinnedSection').hidden = pinned.length === 0;
  $('#pinnedList').innerHTML = pinned.map(conversationItem).join('');
  $('#recentList').innerHTML = recent.length ? recent.map(conversationItem).join('') : '<div class="conversation-empty">هنوز گفت‌وگویی ثبت نشده است.</div>';
}

async function loadConversations() {
  const response = await fetch('/chat/conversations');
  if (response.status === 401) {
    showLogin();
    return false;
  }
  if (!response.ok) throw Error('دریافت گفتگوها انجام نشد.');
  const data = await response.json();
  conversations = data.conversations || [];
  renderConversations();
  return true;
}

async function openConversation(id) {
  if (activeController || id === conversationId) {
    closeSidebar();
    return;
  }
  setStatus('در حال دریافت…');
  const response = await fetch(`/chat/conversations/${encodeURIComponent(id)}/messages`);
  if (response.status === 401) {
    showLogin();
    return;
  }
  if (!response.ok) {
    toast('این گفتگو در دسترس نیست.');
    await loadConversations();
    return;
  }
  const data = await response.json();
  conversationId = id;
  sellerCoachingSession = (data.messages || []).some((item) => item.response?.presentation?.mode === 'seller_coaching');
  dayRouteSession = (data.messages || []).some((item) => item.response?.presentation?.mode === 'day_route');
  selectedDayRouteId = [...(data.messages || [])].reverse().find((item) => item.response?.presentation?.day_route_id)?.response?.presentation?.day_route_id || null;
  lastUserMessage = '';
  messages.innerHTML = '';
  for (const item of data.messages || []) {
    if (!['user', 'assistant'].includes(item.role)) continue;
    const rendered = addMessage(item.content, item.role, {noScroll: true});
    if (item.role === 'user') lastUserMessage = item.content;
    if (item.role === 'assistant' && item.response) renderResult(item.response, rendered.content, lastUserMessage);
  }
  if (!data.messages?.length) messages.innerHTML = welcomeMarkup();
  renderConversations();
  closeSidebar();
  setStatus('آماده');
  scrollToEnd();
  focusMessageInput();
}

function resetChat() {
  activeController?.abort();
  stopVoice(true);
  conversationId = null;
  sellerCoachingSession = false;
  dayRouteSession = false;
  selectedDayRouteId = null;
  lastUserMessage = '';
  clearAttachment();
  messages.innerHTML = welcomeMarkup();
  renderConversations();
  closeSidebar();
  setStatus('آماده');
  focusMessageInput();
}

function openSellerRecommendations() {
  resetChat();
  sellerCoachingSession = true;
  submitMessage('تحلیل عملکرد فروش من از ابتدای ماه تا امروز را شروع کن.', {sellerCoachingStart: true});
}

function coachingNextSteps() {
  const element = document.createElement('div');
  element.className = 'coaching-next-steps';
  element.innerHTML = `<p>ادامهٔ تحلیل را از اینجا انتخاب کن:</p>
    <button type="button" data-prompt="برو سراغ ضعیف‌ترین برند یا گروه کالای من و دلیل فاصله‌ام را دقیق‌تر بگو.">برند یا گروه ضعیف</button>
    <button type="button" data-prompt="مشتری‌های مناسب برای پیگیری و فروش مکمل را معرفی کن.">مشتری‌های هدف</button>
    <button type="button" data-prompt="برای رسیدن به فروش ماه قبل، یک برنامه عملی تا پایان ماه بده.">برنامه جبران فروش</button>`;
  return element;
}

async function warmPrevisitRouteContext(routeId) {
  if (!routeId) return null;
  const response = await fetch(`/seller-workspace/previsit/warmup?path_id=${encodeURIComponent(routeId)}`, {method: 'POST'});
  if (!response.ok) return null;
  return response.json();
}

function startDayRoutePlan(routeId, routeTitle) {
  resetChat();
  dayRouteSession = true;
  selectedDayRouteId = routeId;
  void warmPrevisitRouteContext(routeId).catch(() => null);
  submitMessage(`برای مسیر روز «${routeTitle}» برنامه ویزیت بساز. همه مشتریان این مسیر را بررسی کن، VIPها و مشتریان دارای بیشترین احتمال خرید را مشخص کن و برای گرفتن ۱۰ سفارش برنامه بده.`);
}

async function patchConversation(id, payload) {
  const response = await fetch(`/chat/conversations/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw Error('تغییر گفتگو ذخیره نشد.');
  await loadConversations();
}

async function recoverLatest() {
  if (!conversationId) return null;
  for (let index = 0; index < 8; index += 1) {
    await wait(2500);
    try {
      const response = await fetch(`/chat/latest/${encodeURIComponent(conversationId)}`);
      if (response.ok) return response.json();
      if (response.status === 401) {
        showLogin();
        return null;
      }
    } catch (_) {}
  }
  return null;
}

async function requestAnswer(message, attachment = null, {sellerCoachingStart = false, sellerCoachingMode = sellerCoachingSession, dayRouteMode = dayRouteSession, dayRouteId = selectedDayRouteId} = {}) {
  if (!conversationId) conversationId = crypto.randomUUID();
  const pending = addThinking();
  setThinkingStage(pending, 'در حال فهم درخواست شما', 'متن سؤال و زمینه گفت‌وگو در حال بررسی است.');
  setBusy(true);
  setStatus('در حال تحلیل…');
  activeController = new AbortController();
  let data;
  try {
    try {
      let attachmentContext = null;
      if (attachment) {
        setThinkingStage(
          pending,
          attachment.kind === 'image' ? 'در حال ارسال و بررسی تصویر' : 'در حال ارسال و خواندن فایل',
          attachment.kind === 'image' ? 'تصویر با کیفیت اصلی برای تحلیل آماده می‌شود.' : 'محتوای فایل در حال استخراج و آماده‌سازی است.',
        );
        scheduleThinkingStages(pending, attachment.kind === 'image' ? [
          [1800, 'در حال دیدن جزئیات تصویر', 'سوژه، متن و اعداد قابل مشاهده بررسی می‌شوند.'],
          [5200, 'در حال تحلیل محتوای تصویر', 'نتیجه فقط بر اساس خود تصویر آماده می‌شود.'],
        ] : [
          [1800, 'در حال استخراج محتوای فایل', 'ساختار، جدول‌ها و متن فایل بررسی می‌شوند.'],
          [5200, 'در حال تحلیل فایل', 'اطلاعات مرتبط با سؤال شما در حال جمع‌بندی است.'],
        ]);
        setStatus(attachment.kind === 'image' ? 'در حال تحلیل تصویر…' : 'در حال خواندن فایل…');
        const formData = new FormData();
        formData.append('file', attachment.file, attachment.file.name);
        formData.append('question', message);
        const attachmentResponse = await fetch('/attachments/analyze', {
          method: 'POST',
          body: formData,
          signal: activeController.signal,
        });
        const attachmentData = await attachmentResponse.json();
        if (attachmentResponse.status === 401) {
          showLogin();
          throw Error('ابتدا وارد سامانه شوید.');
        }
        if (!attachmentResponse.ok) throw Error(attachmentData.detail || 'تحلیل پیوست انجام نشد.');
        attachmentContext = attachmentData.analysis;
        setThinkingStage(pending, 'بررسی پیوست انجام شد', 'نتیجه تحلیل با سؤال شما ترکیب می‌شود.');
        setStatus('در حال تحلیل درخواست…');
      }
      setThinkingStage(pending, 'در حال تشخیص فرایند ورانگر', 'نوع درخواست، فاکتور، دریافت، تسویه یا گزارش مرتبط مشخص می‌شود.');
      scheduleThinkingStages(pending, [
        [1400, 'در حال انتخاب گزارش مرجع', 'Viewهای تخصصی و قواعد همان فرایند بررسی می‌شوند.'],
        [4800, 'در حال اجرای گزارش و ساخت پاسخ', 'نتیجه‌ها کنترل و به پاسخ روشن فارسی تبدیل می‌شوند.'],
        [10500, 'در حال کنترل نتیجه نهایی', 'دقت اعداد، تاریخ‌ها و ارتباط پاسخ با سؤال بررسی می‌شود.'],
        [20000, 'بررسی دقیق‌تر ادامه دارد', 'درخواست پیچیده است؛ پردازش همچنان فعال است.'],
      ]);
      const response = await fetch('/chat', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          message,
          conversation_id: conversationId,
          attachment_context: attachmentContext,
          attachment_name: attachment?.file?.name || null,
          seller_coaching_start: sellerCoachingStart,
          seller_coaching_mode: sellerCoachingMode,
          day_route_mode: dayRouteMode,
          day_route_id: dayRouteMode ? dayRouteId : null,
        }),
        signal: activeController.signal,
      });
      data = await response.json();
      if (response.status === 401) {
        showLogin();
        throw Error('ابتدا وارد سامانه شوید.');
      }
      if (!response.ok) throw Error(data.detail || 'خطا در ارتباط با سرویس');
    } catch (error) {
      if (error.name === 'AbortError') {
        stopThinkingProgress(pending);
        pending.row.remove();
        setStatus('متوقف شد', false);
        return;
      }
      if (String(error.message).includes('وارد سامانه')) throw error;
      setThinkingStage(pending, 'در حال بازیابی پاسخ', 'ارتباط لحظه‌ای قطع شده؛ پاسخ ذخیره‌شده در حال بازیابی است.');
      scheduleThinkingStages(pending, [
        [5000, 'بازیابی هنوز ادامه دارد', 'سامانه در حال بررسی آخرین نتیجه کامل‌شده است.'],
      ]);
      setStatus('بازیابی پاسخ…');
      data = await recoverLatest();
      if (!data) throw Error('ارتباط موقتاً قطع شد؛ دوباره تلاش کنید.');
    }
    conversationId = data.conversation_id;
    stopThinkingProgress(pending);
    renderAssistantText(pending.bubble, data.answer);
    pending.content.append(messageActions());
    if (sellerCoachingStart) pending.content.append(coachingNextSteps());
    renderResult(data, pending.content, message);
    setStatus('آماده');
    await loadConversations();
    scrollToEnd();
  } catch (error) {
    stopThinkingProgress(pending);
    pending.bubble.textContent = `متأسفانه مشکلی پیش آمد: ${error.message}`;
    pending.row.classList.add('error');
    const retry = document.createElement('button');
    retry.type = 'button';
    retry.className = 'retry-answer';
    retry.textContent = 'تلاش دوباره';
    retry.addEventListener('click', () => {
      pending.row.remove();
      requestAnswer(message, attachment, {sellerCoachingStart, sellerCoachingMode, dayRouteMode, dayRouteId});
    });
    pending.content.append(retry);
    setStatus('خطا در ارتباط', false);
  } finally {
    stopThinkingProgress(pending);
    activeController = null;
    setBusy(false);
    focusMessageInput();
  }
}

function submitMessage(value = input.value.trim(), {sellerCoachingStart = false} = {}) {
  if ((!value && !pendingAttachment) || activeController) return;
  const attachment = pendingAttachment;
  if (!value) value = attachment?.kind === 'image' ? 'این تصویر را دقیق بررسی کن.' : 'این فایل را دقیق بررسی کن.';
  lastUserMessage = value;
  addMessage(value, 'user', {attachment});
  clearAttachment(false);
  input.value = '';
  resizeInput();
  requestAnswer(value, attachment, {sellerCoachingStart, sellerCoachingMode: sellerCoachingSession, dayRouteMode: dayRouteSession, dayRouteId: selectedDayRouteId});
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  if (activeController) activeController.abort();
  else submitMessage();
});
input.addEventListener('input', resizeInput);
input.addEventListener('touchstart', prepareIOSKeyboardForNativeTap, {passive: true});
input.addEventListener('click', finishIOSKeyboardNativeTap);
input.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    form.requestSubmit();
  }
});
document.addEventListener('keydown', (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault();
    resetChat();
  }
});
messages.addEventListener('click', (event) => {
  const suggestion = event.target.closest('[data-prompt]');
  if (suggestion) return submitMessage(suggestion.dataset.prompt);
  const excel = event.target.closest('[data-export-excel]');
  if (excel?.dataset.exportExcel) {
    openExcelPreview(excel.dataset.exportExcel);
    return;
  }
  const copy = event.target.closest('[data-copy]');
  if (copy) {
    const text = copy.closest('.message-content').querySelector('.message').textContent;
    navigator.clipboard?.writeText(text).then(() => toast('پاسخ کپی شد')).catch(() => toast('امکان کپی وجود ندارد'));
    return;
  }
  if (event.target.closest('[data-retry]') && lastUserMessage && !activeController) requestAnswer(lastUserMessage);
});

$('.conversation-scroll').addEventListener('click', async (event) => {
  const open = event.target.closest('[data-open-conversation]');
  if (open) return openConversation(open.dataset.openConversation);
  const more = event.target.closest('[data-conversation-more]');
  if (more) {
    const item = more.closest('.conversation-item');
    $$('.conversation-item.menu-open').filter((other) => other !== item).forEach((other) => {
      other.classList.remove('menu-open');
      $('.conversation-menu', other).hidden = true;
    });
    item.classList.toggle('menu-open');
    $('.conversation-menu', item).hidden = !item.classList.contains('menu-open');
    return;
  }
  const pin = event.target.closest('[data-pin-conversation]');
  if (pin) {
    const item = conversations.find((value) => value.id === pin.dataset.pinConversation);
    try { await patchConversation(item.id, {pinned: !item.pinned}); } catch (error) { toast(error.message); }
    return;
  }
  const rename = event.target.closest('[data-rename-conversation]');
  if (rename) {
    const item = conversations.find((value) => value.id === rename.dataset.renameConversation);
    const title = prompt('نام جدید گفتگو:', item.title)?.trim();
    if (title) {
      try { await patchConversation(item.id, {title}); } catch (error) { toast(error.message); }
    }
    return;
  }
  const remove = event.target.closest('[data-delete-conversation]');
  if (remove && confirm('این گفتگو حذف شود؟')) {
    const id = remove.dataset.deleteConversation;
    const response = await fetch(`/chat/conversations/${encodeURIComponent(id)}`, {method: 'DELETE'});
    if (!response.ok) return toast('حذف گفتگو انجام نشد.');
    if (id === conversationId) resetChat();
    await loadConversations();
    toast('گفتگو حذف شد');
  }
});
$('#conversationSearch').addEventListener('input', renderConversations);
$('#newChatBtn').addEventListener('click', resetChat);
$('#mobileNewChatBtn').addEventListener('click', resetChat);
$('#openSidebarBtn').addEventListener('click', openSidebar);
$('#closeSidebarBtn').addEventListener('click', closeSidebar);
$('#sidebarBackdrop').addEventListener('click', closeSidebar);
$('#closeExcelPreview')?.addEventListener('click', closeExcelPreview);
$('#closeExcelPreviewFooter')?.addEventListener('click', closeExcelPreview);
$('#downloadExcelBtn')?.addEventListener('click', (event) => downloadExcel(event.currentTarget.dataset.downloadExcel));
excelPreviewDialog?.addEventListener('click', (event) => {
  if (event.target === excelPreviewDialog) closeExcelPreview();
});

function readableFileSize(bytes) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024)).toLocaleString('fa-IR')} کیلوبایت`;
  return `${(bytes / 1024 / 1024).toLocaleString('fa-IR', {maximumFractionDigits: 1})} مگابایت`;
}

function clearAttachment(revoke = true) {
  if (revoke && pendingAttachment?.previewUrl) URL.revokeObjectURL(pendingAttachment.previewUrl);
  pendingAttachment = null;
  attachmentPreview.hidden = true;
  $('#attachmentThumb').innerHTML = '📎';
  $('#attachmentName').textContent = '';
  $('#attachmentMeta').textContent = '';
  for (const picker of [$('#cameraInput'), $('#imageInput'), $('#fileInput')]) picker.value = '';
  attachMenu.hidden = true;
  attachBtn.setAttribute('aria-expanded', 'false');
  resizeInput();
}

function selectAttachment(file) {
  if (!file) return;
  if (file.size > 20 * 1024 * 1024) {
    toast('حجم فایل باید حداکثر ۲۰ مگابایت باشد.');
    return;
  }
  clearAttachment();
  const kind = file.type.startsWith('image/') ? 'image' : 'file';
  const previewUrl = kind === 'image' ? URL.createObjectURL(file) : null;
  pendingAttachment = {file, kind, previewUrl};
  $('#attachmentName').textContent = file.name || (kind === 'image' ? 'تصویر دوربین' : 'فایل');
  $('#attachmentMeta').textContent = `${kind === 'image' ? 'تصویر' : 'فایل'} · ${readableFileSize(file.size)}`;
  if (previewUrl) $('#attachmentThumb').innerHTML = `<img src="${esc(previewUrl)}" alt="">`;
  else $('#attachmentThumb').textContent = '📎';
  attachmentPreview.hidden = false;
  resizeInput();
}

attachBtn.addEventListener('click', (event) => {
  event.stopPropagation();
  attachMenu.hidden = !attachMenu.hidden;
  attachBtn.setAttribute('aria-expanded', String(!attachMenu.hidden));
});
cameraBtn.addEventListener('click', () => $('#cameraInput').click());
fileBtn.addEventListener('click', () => $('#fileInput').click());
attachMenu.addEventListener('click', (event) => {
  const source = event.target.closest('[data-attachment-source]')?.dataset.attachmentSource;
  if (!source) return;
  attachMenu.hidden = true;
  attachBtn.setAttribute('aria-expanded', 'false');
  ({camera: $('#cameraInput'), image: $('#imageInput'), file: $('#fileInput'), audio: $('#audioCaptureInput')})[source]?.click();
});
$('#cameraInput').addEventListener('change', (event) => selectAttachment(event.target.files?.[0]));
$('#imageInput').addEventListener('change', (event) => selectAttachment(event.target.files?.[0]));
$('#fileInput').addEventListener('change', (event) => selectAttachment(event.target.files?.[0]));
$('#audioCaptureInput').addEventListener('change', (event) => {
  const file = event.target.files?.[0];
  if (file) transcribeRecording(file);
  event.target.value = '';
});

$('#removeAttachment').addEventListener('click', () => clearAttachment());
document.addEventListener('click', (event) => {
  if (!attachMenu.hidden && !event.target.closest('#attachMenu') && !event.target.closest('#attachBtn')) {
    attachMenu.hidden = true;
    attachBtn.setAttribute('aria-expanded', 'false');
  }
});
$('#automationsBtn').addEventListener('click', () => { closeSidebar(); submitMessage('اتوماسیون‌های فعال من را نشان بده'); });

function faDigits(value) {
  return String(value).replace(/\d/g, (digit) => '۰۱۲۳۴۵۶۷۸۹'[digit]);
}

function updateVoiceTimer() {
  const seconds = Math.floor((Date.now() - recordingStartedAt) / 1000);
  $('#voiceTimer').textContent = `${faDigits(Math.floor(seconds / 60))}:${faDigits(String(seconds % 60).padStart(2, '0'))}`;
}

function writeWavText(view, offset, value) {
  for (let index = 0; index < value.length; index += 1) view.setUint8(offset + index, value.charCodeAt(index));
}

function encodePcmWav(chunks, sampleRate) {
  const sampleCount = chunks.reduce((total, chunk) => total + chunk.length, 0);
  const buffer = new ArrayBuffer(44 + sampleCount * 2);
  const view = new DataView(buffer);
  writeWavText(view, 0, 'RIFF');
  view.setUint32(4, 36 + sampleCount * 2, true);
  writeWavText(view, 8, 'WAVE');
  writeWavText(view, 12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeWavText(view, 36, 'data');
  view.setUint32(40, sampleCount * 2, true);
  let offset = 44;
  for (const chunk of chunks) {
    for (const rawSample of chunk) {
      const sample = Math.max(-1, Math.min(1, rawSample));
      view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
      offset += 2;
    }
  }
  return new Blob([buffer], {type: 'audio/wav'});
}

async function preparePcmAudioContext() {
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) throw new Error('Web Audio is unavailable');
  if (!pcmAudioContext || pcmAudioContext.state === 'closed') pcmAudioContext = new AudioContextClass();
  if (pcmAudioContext.state !== 'running') await pcmAudioContext.resume();
  pcmSampleRate = pcmAudioContext.sampleRate || 48000;
}

async function startPcmVoiceCapture(stream) {
  await preparePcmAudioContext();
  pcmChunks = [];
  pcmSource = pcmAudioContext.createMediaStreamSource(stream);
  pcmProcessor = pcmAudioContext.createScriptProcessor(4096, 1, 1);
  pcmProcessor.onaudioprocess = (event) => {
    if (!pcmRecorderActive) return;
    pcmChunks.push(new Float32Array(event.inputBuffer.getChannelData(0)));
  };
  pcmSource.connect(pcmProcessor);
  pcmSilentGain = pcmAudioContext.createGain();
  pcmSilentGain.gain.value = 0;
  pcmProcessor.connect(pcmSilentGain);
  pcmSilentGain.connect(pcmAudioContext.destination);
  pcmRecorderActive = true;
}

function closePcmGraph() {
  if (pcmProcessor) pcmProcessor.onaudioprocess = null;
  try { pcmProcessor?.disconnect(); } catch (_) {}
  try { pcmSilentGain?.disconnect(); } catch (_) {}
  try { pcmSource?.disconnect(); } catch (_) {}
  pcmProcessor = null;
  pcmSilentGain = null;
  pcmSource = null;
}

async function closePcmAudioSession() {
  const context = pcmAudioContext;
  pcmAudioContext = null;
  if (!context || context.state === 'closed') return;
  try { await context.close(); } catch (_) {}
}

async function resetVoiceCapture() {
  pcmRecorderActive = false;
  closePcmGraph();
  releaseMicrophone();
  await closePcmAudioSession();
}

function stopPcmVoiceCapture(cancel) {
  const capturedChunks = pcmChunks;
  const capturedRate = pcmSampleRate;
  pcmRecorderActive = false;
  pcmChunks = [];
  closePcmGraph();
  releaseMicrophone();
  void closePcmAudioSession();
  if (cancel) return resetVoiceUi();
  const blob = encodePcmWav(capturedChunks, capturedRate);
  if (blob.size <= 44) {
    const error = new Error(`PCM capture contains ${capturedChunks.length} chunks`);
    error.name = 'PCMEmptyError';
    reportVoiceFailure('pcm-empty', error, 'audio/wav');
    toast('صدایی ضبط نشد؛ دوباره امتحان کنید.');
    return resetVoiceUi();
  }
  transcribeRecording(blob);
}

function releaseMicrophone() {
  clearInterval(voiceTimerHandle);
  voiceTimerHandle = null;
  mediaStream?.getTracks().forEach((track) => track.stop());
  mediaStream = null;
  mediaRecorder = null;
  voiceBtn.classList.remove('pending');
  voiceBtn.classList.remove('recording');
}

function resetVoiceUi() {
  recordingBar.hidden = true;
  recordingBar.classList.remove('transcribing');
  $('#voiceStatus').textContent = 'در حال شنیدن…';
  setStatus('آماده');
  focusMessageInput();
}

function reportVoiceFailure(stage, error, mimeType = '') {
  fetch('/audio/client-events', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      stage,
      name: error?.name || 'Error',
      message: String(error?.message || error || '').slice(0, 1000),
      mime_type: mimeType,
      secure_context: window.isSecureContext,
      user_agent: navigator.userAgent,
    }),
    keepalive: true,
  }).catch(() => {});
}

async function requestHealthyMicrophoneStream() {
  let lastError = null;
  for (let attempt = 0; attempt < 2; attempt += 1) {
    let stream = null;
    try {
      stream = await navigator.mediaDevices.getUserMedia({audio: true});
      // On iOS a permission prompt can succeed while the system hands back an
      // already-ended track. Give WebKit a moment, then reconnect once.
      await wait(180);
      if (stream.getAudioTracks().some((track) => track.readyState === 'live')) return stream;
      lastError = new Error('iPhone returned an ended microphone track');
      lastError.name = 'AudioDeviceUnavailableError';
    } catch (error) {
      lastError = error;
      if (error?.name === 'NotAllowedError' || error?.name === 'SecurityError') throw error;
    }
    stream?.getTracks().forEach((track) => track.stop());
    if (attempt === 0) await wait(350);
  }
  throw lastError || new Error('No live microphone track was received');
}

async function transcribeRecording(blob) {
  recordingBar.classList.add('transcribing');
  $('#voiceStatus').textContent = 'تبدیل صدا به متن…';
  setStatus('تبدیل صدا…');
  try {
    let mediaType = (blob.type || (isIOS ? 'audio/mp4' : 'audio/webm')).split(';', 1)[0].toLowerCase();
    if (mediaType === 'video/mp4' || mediaType === 'audio/x-m4a' || mediaType === 'audio/aac') mediaType = 'audio/mp4';
    const response = await fetch('/audio/transcriptions', {method: 'POST', headers: {'Content-Type': mediaType}, body: blob});
    const data = await response.json();
    if (response.status === 401) {
      showLogin();
      throw Error('ابتدا وارد سامانه شوید.');
    }
    if (!response.ok) throw Error(data.detail || 'تبدیل صدا به متن انجام نشد.');
    input.value = [input.value.trim(), data.text].filter(Boolean).join(' ');
    resizeInput();
    toast('صدا به متن تبدیل شد؛ متن را بررسی و ارسال کنید.');
  } catch (error) {
    reportVoiceFailure('transcription', error, blob.type || '');
    toast(error.message);
  } finally {
    resetVoiceUi();
  }
}

function stopVoice(cancel = true) {
  if (pcmRecorderActive) {
    stopPcmVoiceCapture(cancel);
    return;
  }
  if (!mediaRecorder) {
    resetVoiceUi();
    return;
  }
  cancelRecording = cancel;
  if (mediaRecorder.state !== 'inactive') {
    try { mediaRecorder.requestData(); } catch (_) {}
    mediaRecorder.stop();
  }
}

sessionStorage.removeItem('negin-ios-native-voice');
sessionStorage.removeItem('negin-ios-voice-recovery');
sessionStorage.removeItem('negin-ios-voice-reload-at');

async function startVoice() {
  if (!navigator.mediaDevices?.getUserMedia) {
    reportVoiceFailure('unsupported', new Error('Audio capture APIs are unavailable'));
    toast('ضبط مستقیم در این مرورگر پشتیبانی نمی‌شود.');
    return;
  }
  let startStage = 'request-stream';
  try {
    voiceBtn.classList.add('pending');
    setStatus('در حال اتصال به میکروفن…');
    mediaStream = await requestHealthyMicrophoneStream();
    audioChunks = [];
    cancelRecording = false;
    if (window.MediaRecorder) {
      startStage = 'create-recorder';
      const preferredTypes = isIOS
        ? ['audio/mp4;codecs=mp4a.40.2', 'audio/mp4']
        : ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg;codecs=opus'];
      let recorder = null;
      let recorderError = null;
      for (const mimeType of preferredTypes) {
        try {
          recorder = new MediaRecorder(mediaStream, {mimeType});
          break;
        } catch (error) { recorderError = error; }
      }
      if (!recorder) {
        if (isIOS) throw recorderError || new Error('iPhone does not support AAC/MP4 recording');
        recorder = new MediaRecorder(mediaStream);
      }
      mediaRecorder = recorder;
      recorder.ondataavailable = (event) => { if (event.data.size) audioChunks.push(event.data); };
      recorder.onstop = () => {
        const trackState = mediaStream?.getAudioTracks()
          .map((track) => `${track.readyState}:${track.enabled}:${track.muted}`).join(',') || 'none';
        const blob = new Blob(audioChunks, {type: recorder.mimeType || 'audio/webm'});
        releaseMicrophone();
        if (cancelRecording) return resetVoiceUi();
        if (blob.size < 128) {
          const error = new Error(
            `Recorded blob is only ${blob.size} bytes; requested=${preferredTypes.join(',')}; actual=${recorder.mimeType}; `
            + `tracks=${trackState}`,
          );
          reportVoiceFailure('empty-recording', error, blob.type || '');
          toast('صدایی از میکروفون دریافت نشد؛ دسترسی Microphone را در Settings آیفون بررسی کنید.');
          return resetVoiceUi();
        }
        transcribeRecording(blob);
      };
      recorder.onerror = (event) => {
        reportVoiceFailure('recorder-error', event.error || new Error('MediaRecorder error'), recorder.mimeType || '');
        releaseMicrophone();
        resetVoiceUi();
      toast('ضبط صدا متوقف شد؛ دوباره امتحان کنید.');
      };
      // iOS Safari is more reliable when it flushes audio while recording,
      // rather than waiting until the audio session is closed.
      recorder.start(250);
    } else {
      throw new Error('MediaRecorder is unavailable');
    }
    recordingStartedAt = Date.now();
    updateVoiceTimer();
    voiceTimerHandle = setInterval(updateVoiceTimer, 1000);
    voiceBtn.classList.remove('pending');
    voiceBtn.classList.add('recording');
    recordingBar.hidden = false;
    setStatus('در حال شنیدن…');
  } catch (error) {
    reportVoiceFailure(`start-${startStage}`, error);
    await resetVoiceCapture();
    resetVoiceUi();
    if (error.name === 'NotAllowedError') {
      toast('دسترسی میکروفن را برای این سایت روی Allow بگذارید و دوباره امتحان کنید.');
    } else if (error.name === 'SecurityError' || !window.isSecureContext) {
      toast('ضبط صدا فقط روی آدرس HTTPS یا localhost کار می‌کند.');
    } else {
      toast('ضبط مستقیم شروع نشد؛ دوباره امتحان کنید.');
    }
  }
}

voiceBtn.addEventListener('click', () => {
  if (mediaRecorder || pcmRecorderActive) return stopVoice(false);
  // iOS Safari can grant microphone permission but return an already-ended
  // MediaStream. Its native audio capture sheet is reliable and produces an
  // M4A file that the existing transcription endpoint already supports.
  if (isIOS) {
    $('#audioCaptureInput').click();
    return;
  }
  startVoice();
});
$('#cancelVoice').addEventListener('click', () => stopVoice(true));
$('#finishVoice').addEventListener('click', () => stopVoice(false));
window.addEventListener('pagehide', () => { void resetVoiceCapture(); });
document.addEventListener('visibilitychange', () => {
  if (document.hidden && (mediaRecorder || pcmRecorderActive || mediaStream)) void resetVoiceCapture();
});

function base64UrlBytes(value) {
  const padded = value + '='.repeat((4 - value.length % 4) % 4);
  const raw = atob(padded.replace(/-/g, '+').replace(/_/g, '/'));
  return Uint8Array.from(raw, (char) => char.charCodeAt(0));
}

async function pushStatus() {
  const response = await fetch('/push/status');
  if (response.status === 401) return null;
  if (!response.ok) throw Error('وضعیت اعلان دریافت نشد.');
  return response.json();
}

async function waitForPushWorker() {
  let registration = serviceWorkerRegistration || await navigator.serviceWorker.register('/service-worker.js', {scope: '/', updateViaCache: 'none'});
  serviceWorkerRegistration = registration;
  await registration.update();
  registration = await navigator.serviceWorker.ready;
  serviceWorkerRegistration = registration;
  return registration;
}

function setPushButton(active) {
  notificationBtn.classList.toggle('notification-button-active', active);
  notificationBtn.lastElementChild.textContent = active ? 'اعلان فعال است' : 'فعال‌کردن اعلان';
}

async function refreshPushState() {
  try {
    const status = await pushStatus();
    if (status === null) return false;
    const registration = await waitForPushWorker();
    const subscription = await registration.pushManager?.getSubscription();
    const active = Boolean(subscription && status.subscription_count);
    setPushButton(active);
    return active;
  } catch (_) { return false; }
}

async function enablePush() {
  if (!('serviceWorker' in navigator) || !('PushManager' in window) || !('Notification' in window)) {
    toast('اعلان در این مرورگر پشتیبانی نمی‌شود.');
    return;
  }
  if (isIOS && !standalone) {
    $('#installDialog').showModal();
    toast('ابتدا اپ را روی صفحه اصلی نصب کنید.');
    return;
  }
  notificationBtn.disabled = true;
  try {
    const permission = await Notification.requestPermission();
    if (permission !== 'granted') throw Error('اجازه اعلان داده نشد.');
    const status = await pushStatus();
    if (status === null) {
      showLogin();
      throw Error('ابتدا وارد سامانه شوید.');
    }
    const registration = await waitForPushWorker();
    let subscription = await registration.pushManager.getSubscription();
    if (!subscription) subscription = await registration.pushManager.subscribe({userVisibleOnly: true, applicationServerKey: base64UrlBytes(status.public_key)});
    const saved = await fetch('/push/subscriptions', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(subscription.toJSON())});
    if (!saved.ok) throw Error('ثبت اعلان انجام نشد.');
    setPushButton(true);
    await fetch('/push/test', {method: 'POST'});
    toast('اعلان فعال شد و پیام آزمایشی ارسال شد.');
  } catch (error) {
    toast(error.message);
  } finally {
    notificationBtn.disabled = false;
  }
}

function setInboxBadge() {
  const count = notificationsCache.filter((item) => !item.read).length;
  inboxBadge.hidden = count === 0;
  inboxBadge.textContent = count > 99 ? '۹۹+' : count.toLocaleString('fa-IR');
}

function notificationTime(value) {
  try { return new Date(value).toLocaleString('fa-IR', {dateStyle: 'medium', timeStyle: 'short'}); }
  catch (_) { return value || ''; }
}

function renderNotifications(selectedId = null) {
  if (!notificationsCache.length) {
    notificationsList.innerHTML = '<div class="notifications-empty"><div>♧</div><h3>هنوز اعلانی ندارید</h3><p>گزارش‌ها و هشدارهای اتوماتیک اینجا نمایش داده می‌شوند.</p></div>';
    return;
  }
  notificationsList.innerHTML = notificationsCache.map((item) => `<article class="notification-card${item.read ? '' : ' unread'}${Number(item.id) === Number(selectedId) ? ' expanded selected' : ''}" data-notification-card="${item.id}"><button type="button" data-notification-id="${item.id}"><div class="notification-card-head"><span class="notification-dot"></span><strong>${esc(item.title)}</strong><time>${esc(notificationTime(item.created_at))}</time></div><p>${esc(item.body)}</p></button></article>`).join('');
}

async function markNotificationsRead(ids) {
  const unread = ids.filter((id) => notificationsCache.some((item) => Number(item.id) === Number(id) && !item.read));
  if (!unread.length) return;
  const response = await fetch('/automations/notifications/read', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({notification_ids: unread})});
  if (!response.ok) return;
  notificationsCache = notificationsCache.map((item) => unread.includes(Number(item.id)) ? {...item, read: true} : item);
  setInboxBadge();
}

function requestedNotificationId() {
  const value = Number(new URLSearchParams(location.search).get('notification'));
  return Number.isInteger(value) && value > 0 ? value : null;
}

async function loadNotifications(openPanel = false, selectedId = null) {
  try {
    const response = await fetch('/automations/notifications?limit=100');
    if (response.status === 401) {
      if (openPanel) showLogin();
      return;
    }
    if (!response.ok) throw Error('دریافت اعلان‌ها انجام نشد.');
    const data = await response.json();
    notificationsCache = data.notifications || [];
    setInboxBadge();
    renderNotifications(selectedId);
    if (openPanel) {
      rememberAppView('notifications', selectedId ? {selectedId: Number(selectedId)} : {});
      notificationsPanel.hidden = false;
      if (selectedId) await markNotificationsRead([selectedId]);
      renderNotifications(selectedId);
      closeSidebar();
    }
  } catch (error) { if (openPanel) toast(error.message); }
}

function closeNotificationsPanel() {
  closeCurrentAppView('notifications', () => {
    notificationsPanel.hidden = true;
    if (location.search) history.replaceState(appHistoryState(), '', '/assistant');
  });
}

function teamSplitLabel(value) {
  return value === 'brand' ? '\u062a\u0641\u06a9\u06cc\u06a9 \u0628\u0631\u0646\u062f' : value === 'region_or_customer' ? '\u062a\u0641\u06a9\u06cc\u06a9 \u0645\u0646\u0637\u0642\u0647 / \u0645\u0634\u062a\u0631\u06cc' : '\u0646\u0627\u0645\u0634\u062e\u0635';
}

function renderOrganizationStructure(rules, proposals) {
  organizationRulesList.innerHTML = rules.length ? rules.map((rule) => `<article class="organization-card"><strong>${esc(rule.branch)} / ${esc(rule.sales_line)}</strong>${rule.supervisor_name ? `<small>${esc(rule.supervisor_name)}</small>` : ''}<label>\u0646\u0648\u0639 \u0633\u0627\u062e\u062a\u0627\u0631<select data-rule-split="${rule.id}"><option value="brand"${rule.team_split === 'brand' ? ' selected' : ''}>\u0628\u0631\u0646\u062f\u06cc</option><option value="region_or_customer"${rule.team_split === 'region_or_customer' ? ' selected' : ''}>\u0645\u0646\u0637\u0642\u0647\u200c\u0627\u06cc / \u0645\u0634\u062a\u0631\u06cc</option><option value="unspecified"${rule.team_split === 'unspecified' ? ' selected' : ''}>\u0646\u0627\u0645\u0634\u062e\u0635</option></select></label><label>\u0633\u0628\u062f \u0628\u0631\u0646\u062f (\u062c\u062f\u0627\u0634\u062f\u0647 \u0628\u0627 \u0648\u06cc\u0631\u06af\u0648\u0644)<input data-rule-brands="${rule.id}" value="${esc((rule.brand_portfolio || []).join(', '))}"></label><label>\u06cc\u0627\u062f\u062f\u0627\u0634\u062a<input data-rule-notes="${rule.id}" value="${esc(rule.notes || '')}"></label><footer><button type="button" data-save-rule="${rule.id}">\u0630\u062e\u06cc\u0631\u0647 \u062a\u0646\u0638\u06cc\u0645\u0627\u062a</button></footer></article>`).join('') : '<p class="organization-empty">\u0642\u0627\u0639\u062f\u0647\u200c\u0627\u06cc \u062b\u0628\u062a \u0646\u0634\u062f\u0647 \u0627\u0633\u062a.</p>';
  organizationProposalsList.innerHTML = proposals.length ? proposals.map((proposal) => `<article class="organization-card proposal"><strong>${esc(proposal.branch)} / ${esc(proposal.sales_line || '\u0633\u0627\u062e\u062a\u0627\u0631')}</strong><span>${Math.round(Number(proposal.confidence || 0) * 100)}% \u0627\u0637\u0645\u06cc\u0646\u0627\u0646</span><small>${esc(JSON.stringify(proposal.proposed_value || {}))}</small><footer><button type="button" data-proposal-decision="approved" data-proposal-id="${proposal.id}">\u062a\u0623\u06cc\u06cc\u062f</button><button type="button" data-proposal-decision="rejected" data-proposal-id="${proposal.id}">\u0631\u062f</button></footer></article>`).join('') : '<p class="organization-empty">\u0641\u0639\u0644\u0627\u064b \u067e\u06cc\u0634\u0646\u0647\u0627\u062f\u06cc \u0628\u0631\u0627\u06cc \u0628\u0631\u0631\u0633\u06cc \u0646\u06cc\u0633\u062a.</p>';
}

async function openOrganizationStructure() {
  rememberAppView('organization');
  try {
    organizationStructurePanel.hidden = false;
    notificationsPanel.hidden = true;
    schemaCatalogPanel.hidden = true;
    organizationRulesList.innerHTML = '<p class="organization-empty">\u062f\u0631 \u062d\u0627\u0644 \u062f\u0631\u06cc\u0627\u0641\u062a \u062a\u0646\u0638\u06cc\u0645\u0627\u062a\u2026</p>';
    const [structureResponse, proposalsResponse] = await Promise.all([
      fetch('/organization-structure'), fetch('/organization-structure/proposals?status=pending'),
    ]);
    if (structureResponse.status === 401) return showLogin();
    if (structureResponse.status === 403) throw Error('\u0627\u06cc\u0646 \u0628\u062e\u0634 \u0641\u0642\u0637 \u0628\u0631\u0627\u06cc \u0645\u062f\u06cc\u0631 \u062f\u0631 \u062f\u0633\u062a\u0631\u0633 \u0627\u0633\u062a.');
    if (!structureResponse.ok || !proposalsResponse.ok) throw Error('\u062f\u0631\u06cc\u0627\u0641\u062a \u062a\u0646\u0638\u06cc\u0645\u0627\u062a \u0627\u0646\u062c\u0627\u0645 \u0646\u0634\u062f.');
    const [structure, proposalData] = await Promise.all([structureResponse.json(), proposalsResponse.json()]);
    renderOrganizationStructure(structure.rules || [], proposalData.proposals || []);
    closeSidebar();
  } catch (error) {
    organizationStructurePanel.hidden = true;
    closeCurrentAppView('organization');
    toast(error.message);
  }
}

async function decideOrganizationProposal(id, decision) {
  const response = await fetch(`/organization-structure/proposals/${encodeURIComponent(id)}/decision`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({decision})});
  if (!response.ok) throw Error('\u062b\u0628\u062a \u0646\u0638\u0631 \u0627\u0646\u062c\u0627\u0645 \u0646\u0634\u062f.');
  await openOrganizationStructure();
}

async function saveOrganizationRule(id) {
  const team_split = $(`[data-rule-split="${id}"]`).value;
  const brand_portfolio = $(`[data-rule-brands="${id}"]`).value.split(',').map((value) => value.trim()).filter(Boolean);
  const notes = $(`[data-rule-notes="${id}"]`).value;
  const response = await fetch(`/organization-structure/rules/${encodeURIComponent(id)}`, {method: 'PATCH', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({team_split, brand_portfolio, notes})});
  if (!response.ok) throw Error('\u0630\u062e\u06cc\u0631\u0647\u200c\u0633\u0627\u0632\u06cc \u0627\u0646\u062c\u0627\u0645 \u0646\u0634\u062f.');
  toast('\u062a\u0646\u0638\u06cc\u0645\u0627\u062a \u062a\u06cc\u0645 \u0630\u062e\u06cc\u0631\u0647 \u0634\u062f.');
  await openOrganizationStructure();
}

function renderSellerWorkspace(routesData, brandsData) {
  const isDayRouteSelection = sellerWorkspacePanel.dataset.dayRouteSelection === 'true';
  const assignmentLabel = routesData.visit_template ? `تخصیص فعلی: ${routesData.visit_template}` : 'تخصیص فعلی';
  const dayRouteLabel = routesData.day_route?.title ? ` · تور امروز: ${routesData.day_route.title}` : ' · برای امروز تور فعالی تعیین نشده';
  $('#myRoutesSource').textContent = isDayRouteSelection ? `${assignmentLabel}${dayRouteLabel}` : assignmentLabel;
  myRoutesList.innerHTML = (routesData.routes || []).length ? routesData.routes.map((route) => {
    const customerCount = Number(route.customer_count || 0);
    const routeId = esc(route.id);
    const rowLabel = route.row_index != null ? `\u0631\u062f\u06cc\u0641 ${Number(route.row_index).toLocaleString('fa-IR')}` : '\u0645\u0633\u06cc\u0631 \u0641\u0639\u0627\u0644';
    const canStartDayRoute = Boolean(route.can_start_day_route);
    const startDayRouteButton = canStartDayRoute
      ? `<button class="seller-route-map-button is-day-route" type="button" data-route-map-id="${routeId}" data-route-map-title="${esc(route.title)}">ورود به تور ویزیت</button>`
      : '<button class="seller-route-map-button" type="button" disabled title="این مسیر برای تور امروز تعیین نشده است">خارج از تور امروز</button>';
    return `<article class="seller-route-card">
      <button class="seller-route-summary" type="button" data-route-customers="${routeId}" aria-expanded="false">
        <span class="seller-route-mark">\u2316</span><span class="seller-route-copy"><strong>${esc(route.title)}</strong><small>${rowLabel} <b>\u00b7</b> ${customerCount.toLocaleString('fa-IR')} \u0645\u0634\u062a\u0631\u06cc</small></span><span class="seller-route-chevron">\u2304</span>
      </button>${isDayRouteSelection ? `<button class="seller-route-day-plan" type="button" data-day-route-id="${routeId}" data-day-route-title="${esc(route.title)}">برنامه تحلیلی این مسیر</button><label class="seller-route-map-mode">حالت چیدمان<select data-route-map-mode><option value="sales_priority">اولویت فروش: بالا و متوسط اول</option><option value="shortest">کوتاه‌ترین مسیر</option></select></label>${startDayRouteButton}` : ''}<div class="seller-route-customer-list" data-route-customer-list="${routeId}" hidden></div>
    </article>`;
  }).join('') : '<p class="organization-empty">هیچ مسیر فعالی در تخصیص فعلی برای شما ثبت نشده است.</p>';
  $('#myBrandsSupervisor').textContent = brandsData.product_template ? `کاتالوگ فعلی: ${brandsData.product_template}` : 'کاتالوگ فعلی';
  const brandDetails = brandsData.brand_details || [];
  myBrandsList.innerHTML = brandDetails.length ? brandDetails.map((brand) => `<span class="seller-brand-chip" title="${Number(brand.product_count || 0).toLocaleString('fa-IR')} \u06a9\u0627\u0644\u0627">${esc(brand.name)}</span>`).join('') : '<p class="organization-empty">هیچ برند قابل‌فروشی در کاتالوگ فعلی برای شما ثبت نشده است.</p>';
}

function decodePolyline(encoded) {
  let index = 0, latitude = 0, longitude = 0;
  const points = [];
  while (index < encoded.length) {
    let shift = 0, value = 0, byte;
    do { byte = encoded.charCodeAt(index++) - 63; value |= (byte & 31) << shift; shift += 5; } while (byte >= 32);
    latitude += (value & 1) ? ~(value >> 1) : (value >> 1);
    shift = 0; value = 0;
    do { byte = encoded.charCodeAt(index++) - 63; value |= (byte & 31) << shift; shift += 5; } while (byte >= 32);
    longitude += (value & 1) ? ~(value >> 1) : (value >> 1);
    points.push([longitude / 1e5, latitude / 1e5]);
  }
  return points;
}

function currentCoordinates(options = {}) {
  return new Promise((resolve) => {
    if (!navigator.geolocation) return resolve(null);
    navigator.geolocation.getCurrentPosition(
      (position) => resolve({
        latitude: position.coords.latitude, longitude: position.coords.longitude,
        heading: Number.isFinite(position.coords.heading) ? position.coords.heading : null,
        accuracy: Number.isFinite(position.coords.accuracy) ? position.coords.accuracy : null,
        speed: Number.isFinite(position.coords.speed) ? position.coords.speed : null,
        timestamp: position.timestamp || Date.now(),
      }),
      () => resolve(null), {
        enableHighAccuracy: true,
        timeout: options.timeout ?? 7000,
        maximumAge: options.maximumAge ?? 60000,
      },
    );
  });
}

function routeMapLegFor(index) {
  return routeMapSession?.currentLeg || null;
}

function focusRouteMapStop() {
  const session = routeMapSession;
  const customer = session?.plan.ordered_customers?.[session.activeIndex];
  if (!customer || !routeMapInstance || session.started) return;
  routeMapInstance.flyTo({ center: [customer.longitude, customer.latitude], zoom: 15, essential: true });
}

function unlockNavigationAudio() {
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) return null;
  if (!navigationAudioContext || navigationAudioContext.state === 'closed') navigationAudioContext = new AudioContextClass();
  if (navigationAudioContext.state !== 'running') void navigationAudioContext.resume();
  return navigationAudioContext;
}

function browserSpeakRouteInstruction(text) {
  if (!text || !('speechSynthesis' in window)) { toast('راهنمای صوتی در این مرورگر در دسترس نیست.'); return; }
  window.speechSynthesis.cancel();
  window.speechSynthesis.resume();
  const utterance = new SpeechSynthesisUtterance(String(text).replace(/<[^>]*>/g, ''));
  utterance.lang = 'fa-IR';
  // انتخاب صریح صدای فارسی، خوانش دستورات را روی دستگاه‌هایی که صدای پیش‌فرض
  // انگلیسی دارند بسیار واضح‌تر می‌کند.
  const voices = window.speechSynthesis.getVoices();
  const persianVoice = voices.find((voice) => /^fa[-_]?ir$/i.test(voice.lang))
    || voices.find((voice) => /^fa/i.test(voice.lang));
  if (persianVoice) utterance.voice = persianVoice;
  utterance.rate = .88;
  utterance.volume = 1;
  utterance.onerror = (event) => {
    if (!['canceled', 'interrupted'].includes(event.error)) toast('پخش صوتی مسیریاب در گوشی غیرفعال است؛ صدای فارسی مرورگر را فعال کنید.');
  };
  window.speechSynthesis.speak(utterance);
  window.setTimeout(() => window.speechSynthesis.resume(), 120);
}

async function speakRouteInstruction(text) {
  const phrase = String(text || '').replace(/<[^>]*>/g, '').trim();
  if (!phrase || routeMapSession?.voiceEnabled === false) return;
  try {
    if (window.NeginAndroid?.isPersianVoiceReady?.() && window.NeginAndroid.speakPersian(phrase)) {
      navigationSpeechAbortController?.abort();
      navigationSpeechSequence += 1;
      return;
    }
  } catch (_) {
    // Debug browsers and older APKs do not expose the native voice bridge.
  }
  const requestSequence = ++navigationSpeechSequence;
  navigationSpeechAbortController?.abort();
  navigationSpeechAbortController = new AbortController();
  const context = unlockNavigationAudio();
  if (!context) return browserSpeakRouteInstruction(phrase);
  try {
    let encoded = navigationSpeechCache.get(phrase);
    if (!encoded) {
      const response = await fetch('/audio/navigation-speech', {
        method: 'POST', headers: {'Content-Type': 'application/json'}, signal: navigationSpeechAbortController.signal,
        body: JSON.stringify({text: phrase}),
      });
      if (!response.ok) throw Error('صدای اختصاصی مسیریاب آماده نشد.');
      encoded = await response.arrayBuffer();
      navigationSpeechCache.set(phrase, encoded.slice(0));
      if (navigationSpeechCache.size > 32) navigationSpeechCache.delete(navigationSpeechCache.keys().next().value);
    }
    if (requestSequence !== navigationSpeechSequence) return;
    if (context.state !== 'running') await context.resume();
    const buffer = await context.decodeAudioData(encoded.slice(0));
    if (requestSequence !== navigationSpeechSequence) return;
    navigationAudioSource?.stop();
    navigationAudioSource = context.createBufferSource();
    navigationAudioSource.buffer = buffer;
    navigationAudioSource.connect(context.destination);
    navigationAudioSource.onended = () => { if (requestSequence === navigationSpeechSequence) navigationAudioSource = null; };
    navigationAudioSource.start();
  } catch (error) {
    if (error.name !== 'AbortError' && requestSequence === navigationSpeechSequence) browserSpeakRouteInstruction(phrase);
  }
}

function prepareRouteInstructions() {
  if (!routeMapSession) return;
  routeMapSession.navigationStepIndex = 0;
  routeMapSession.navigationSteps = routeMapSession.currentLeg?.steps || [];
  routeMapSession.navigationCueKeys = new Set();
  routeMapSession.navigationStepMinimumDistance = Infinity;
  routeMapSession.currentManeuverDistance = null;
  renderRouteMapInstruction();
}

function routeStepPosition(step) {
  const point = step?.start_location;
  if (!Array.isArray(point) || point.length < 2) return null;
  const longitude = Number(point[0]), latitude = Number(point[1]);
  return Number.isFinite(latitude) && Number.isFinite(longitude) ? { latitude, longitude } : null;
}

function navigationDistanceLabel(meters) {
  if (!Number.isFinite(meters)) return 'مسیر پیش رو';
  if (meters < 50) return 'اکنون';
  if (meters < 1000) return `${Math.max(10, Math.round(meters / 10) * 10).toLocaleString('fa-IR')} متر دیگر`;
  return `${(meters / 1000).toLocaleString('fa-IR', {maximumFractionDigits: 1})} کیلومتر دیگر`;
}

function routeManeuverSymbol(step) {
  const type = String(step?.type || '').toLowerCase();
  const modifier = String(step?.modifier || '').toLowerCase();
  const instruction = String(step?.instruction || '');
  if (type.includes('roundabout') || type.includes('rotary') || instruction.includes('فلکه') || instruction.includes('میدان')) return '↻';
  if (type.includes('uturn') || instruction.includes('دوربرگردان')) return '↶';
  if (modifier.includes('left') || instruction.includes('چپ')) return modifier.includes('slight') ? '↖' : '←';
  if (modifier.includes('right') || instruction.includes('راست')) return modifier.includes('slight') ? '↗' : '→';
  if (type === 'arrive') return '●';
  return '↑';
}

function routeInstructionText(step) {
  return String(step?.instruction || 'مستقیم حرکت کنید.').replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').trim();
}

function renderRouteMapInstruction() {
  const card = $('#routeMapInstruction');
  const session = routeMapSession;
  if (!card) return;
  if (!session?.started) {
    card.hidden = true;
    return;
  }
  const step = session.navigationSteps?.[session.navigationStepIndex];
  if (!step) {
    card.hidden = false;
    card.innerHTML = '<span class="route-maneuver-icon">●</span><small>نزدیک مقصد</small><strong>مستقیم تا پایگاه فعال حرکت کنید.</strong>';
    return;
  }
  const prefix = navigationDistanceLabel(session.currentManeuverDistance);
  const instruction = esc(routeInstructionText(step));
  card.hidden = false;
  card.innerHTML = `<span class="route-maneuver-icon">${routeManeuverSymbol(step)}</span><small>${esc(prefix)}</small><strong>${instruction}</strong>`;
}

function openRouteSummary() {
  const session = routeMapSession;
  const dialog = $('#routeSummaryDialog');
  const destination = session?.plan.ordered_customers?.[session.activeIndex];
  if (!session?.started || !dialog || !destination) return;
  const leg = session.currentLeg || {};
  $('#routeSummaryTitle').textContent = `تا ${routeMapCustomerName(destination)}`;
  $('#routeSummaryMeta').textContent = [leg.duration?.text, leg.distance?.text].filter(Boolean).join(' · ') || 'جزئیات مسیر در حال محاسبه است';
  const currentIndex = session.navigationStepIndex || 0;
  const steps = session.navigationSteps || [];
  $('#routeSummarySteps').innerHTML = steps.length
    ? steps.map((step, index) => {
      const distance = step?.distance?.text || step?.duration?.text || '';
      return `<li class="${index === currentIndex ? 'is-current' : ''}">${esc(routeInstructionText(step))}${distance ? `<small>${esc(distance)}</small>` : ''}</li>`;
    }).join('')
    : '<li class="is-current">مسیر در حال دریافت است.</li>';
  if (!dialog.open) dialog.showModal();
}

function navigationCue(step, meters, threshold) {
  const instruction = routeInstructionText(step);
  if (threshold <= 25) return `اکنون، ${instruction}`;
  return `${navigationDistanceLabel(meters)}، ${instruction}`;
}

function advanceNavigationStep(session) {
  session.navigationStepIndex += 1;
  session.navigationStepMinimumDistance = Infinity;
  session.currentManeuverDistance = null;
}

function updateRouteNavigationProgress(position) {
  const session = routeMapSession;
  if (!session?.started || !session.navigationSteps?.length) return;
  let step = session.navigationSteps[session.navigationStepIndex];
  let stepPosition = routeStepPosition(step);
  if (!step || !stepPosition) return;
  let distance = distanceToRouteStopMeters(position, stepPosition);

  // If GPS starts after a manoeuvre or jumps across it, move to the closest
  // upcoming manoeuvre instead of leaving navigation stuck on an old step.
  if (distance > 150) {
    let closestIndex = session.navigationStepIndex, closestDistance = distance;
    for (let index = session.navigationStepIndex + 1; index <= Math.min(session.navigationStepIndex + 3, session.navigationSteps.length - 1); index += 1) {
      const candidatePosition = routeStepPosition(session.navigationSteps[index]);
      if (!candidatePosition) continue;
      const candidateDistance = distanceToRouteStopMeters(position, candidatePosition);
      if (candidateDistance + 90 < closestDistance) { closestIndex = index; closestDistance = candidateDistance; }
    }
    if (closestIndex > session.navigationStepIndex) {
      session.navigationStepIndex = closestIndex;
      session.navigationStepMinimumDistance = Infinity;
      step = session.navigationSteps[closestIndex];
      stepPosition = routeStepPosition(step);
      distance = closestDistance;
    }
  }

  session.currentManeuverDistance = distance;
  const previousMinimum = session.navigationStepMinimumDistance;
  session.navigationStepMinimumDistance = Math.min(previousMinimum, distance);
  if (previousMinimum < 65 && distance > previousMinimum + 40) {
    advanceNavigationStep(session);
    renderRouteMapInstruction();
    return;
  }

  const threshold = distance <= 25 ? 25 : (distance <= 80 ? 80 : (distance <= 250 ? 250 : (distance <= 600 ? 600 : null)));
  if (threshold) {
    const cueKey = `${session.navigationStepIndex}:${threshold}`;
    if (!session.navigationCueKeys.has(cueKey)) {
      session.navigationCueKeys.add(cueKey);
      if (!isIOS) void speakRouteInstruction(navigationCue(step, distance, threshold));
    }
  }
  if (distance <= 25) advanceNavigationStep(session);
  renderRouteMapInstruction();
}

function distanceToRouteLineMeters(position, polyline) {
  const line = decodePolyline(polyline || '');
  if (line.length < 2) return 0;
  // For the short segments around the seller, a local planar projection is
  // sufficiently accurate and avoids a costly routing request on every fix.
  const latitudeScale = 111320;
  const longitudeScale = latitudeScale * Math.cos(position.latitude * Math.PI / 180);
  const pointX = position.longitude * longitudeScale;
  const pointY = position.latitude * latitudeScale;
  let nearest = Infinity;
  for (let index = 1; index < line.length; index += 1) {
    const [startLongitude, startLatitude] = line[index - 1];
    const [endLongitude, endLatitude] = line[index];
    const startX = startLongitude * longitudeScale, startY = startLatitude * latitudeScale;
    const deltaX = endLongitude * longitudeScale - startX, deltaY = endLatitude * latitudeScale - startY;
    const lengthSquared = deltaX ** 2 + deltaY ** 2;
    const ratio = lengthSquared ? Math.max(0, Math.min(1, ((pointX - startX) * deltaX + (pointY - startY) * deltaY) / lengthSquared)) : 0;
    nearest = Math.min(nearest, Math.hypot(pointX - (startX + ratio * deltaX), pointY - (startY + ratio * deltaY)));
  }
  return nearest;
}

async function refreshActiveRouteLeg(position, { announce = false } = {}) {
  const session = routeMapSession;
  const destination = session?.plan.ordered_customers?.[session.activeIndex];
  if (!session || !destination || !position || session.rerouting) return false;
  session.rerouting = true;
  setRouteMapStatus(session.started ? 'در حال محاسبه مسیر جدید…' : 'در حال محاسبه مسیر…');
  try {
    const params = new URLSearchParams({
      destination_id: String(destination.id), origin_latitude: String(position.latitude), origin_longitude: String(position.longitude),
    });
    const response = await fetch(`/seller-workspace/routes/${encodeURIComponent(session.pathId)}/map-leg?${params}`);
    if (!response.ok) throw Error('مسیر جدید دریافت نشد.');
    const leg = await response.json();
    // Ignore a response belonging to a route that has since been closed or advanced.
    if (routeMapSession !== session || session.plan.ordered_customers?.[session.activeIndex]?.id !== destination.id) return false;
    session.currentLeg = leg.leg || null;
    session.currentLegPolyline = leg.polyline || '';
    session.lastRerouteAt = Date.now();
    prepareRouteInstructions();
    drawRouteMapLine(session.currentLegPolyline || session.plan.polyline);
    focusRouteMapLeg(session.currentLegPolyline);
    renderRouteMapStops();
    if (announce && !isIOS) {
      const firstInstruction = routeInstructionText(session.navigationSteps?.[0]) || `حرکت به سمت ${destination.store_name || destination.name || 'پایگاه بعدی'} را شروع کنید.`;
      void speakRouteInstruction(`${session.lastRerouteAt && session.hasNavigationRoute ? 'مسیر اصلاح شد. ' : ''}${firstInstruction}`);
      if (session.navigationSteps.length > 1) session.navigationStepIndex = 1;
      session.navigationStepMinimumDistance = Infinity;
      session.currentManeuverDistance = null;
      session.hasNavigationRoute = true;
      renderRouteMapInstruction();
    }
    renderRouteMapTripSummary();
    return true;
  } catch (error) {
    if (announce) toast(error.message || 'به‌روزرسانی مسیر انجام نشد.');
    return false;
  } finally {
    if (routeMapSession === session) {
      session.rerouting = false;
      setRouteMapStatus('');
    }
  }
}

function maybeRerouteActiveRoute(position) {
  const session = routeMapSession;
  if (!session?.started || session.rerouting || !session.currentLegPolyline) return;
  if (Date.now() - (session.lastRerouteAt || 0) < 15000) return;
  const threshold = Math.max(65, Number(position.accuracy || 0) * 1.5);
  const offRoute = distanceToRouteLineMeters(position, session.currentLegPolyline) > threshold;
  if (!offRoute) { session.offRouteSince = null; return; }
  session.offRouteSince ||= Date.now();
  if (Date.now() - session.offRouteSince >= 5000) {
    session.offRouteSince = null;
    if (!isIOS) void speakRouteInstruction('از مسیر خارج شدید. مسیر جدید در حال محاسبه است.');
    void refreshActiveRouteLeg(position, { announce: true });
  }
}

function setRouteMapStatus(message) {
  const status = $('#routeMapStatus');
  if (!status) return;
  status.textContent = message || '';
  status.hidden = !message;
}

function renderRouteMapTripSummary() {
  const summary = $('#routeMapTripSummary');
  const session = routeMapSession;
  if (!summary) return;
  const destination = session?.plan.ordered_customers?.[session.activeIndex];
  if (!session?.started || !destination) { summary.hidden = true; return; }
  const duration = session.currentLeg?.duration?.text || 'زمان نامشخص';
  const distance = session.currentLeg?.distance?.text || 'فاصله نامشخص';
  summary.hidden = false;
  summary.innerHTML = `<strong>${esc(routeMapCustomerName(destination))}</strong><span>${esc(duration)} · ${esc(distance)}</span>`;
}

function followRouteMapPosition(position, immediate = false) {
  const session = routeMapSession;
  if (!routeMapInstance || !session?.started || !session.followUser) return;
  routeMapInstance.easeTo({
    center: [position.longitude, position.latitude],
    zoom: 16.5,
    bearing: Number.isFinite(session.heading) ? session.heading : 0,
    pitch: 42,
    duration: immediate ? 0 : 650,
    essential: true,
  });
}

function routeMapMoney(value) {
  return `${Number(value || 0).toLocaleString('fa-IR')} ریال`;
}

function routeMapCustomerName(customer) {
  const store = String(customer.store_name || '').trim();
  const person = String(customer.name || '').trim();
  return store && person && store !== person ? `${store} · ${person}` : (store || person || 'مشتری');
}

function routeCustomerListIdentity(customer) {
  const store = String(customer.store_name || '').trim() || 'نام فروشگاه ثبت نشده';
  const person = String(customer.name || '').trim() || 'نام مشتری ثبت نشده';
  const address = String(customer.address || '').trim() || 'نشانی ثبت نشده';
  const resolution = customer.visit_resolution || {};
  const count = Number(resolution.saved_request_count || 0);
  const outcome = String(resolution.outcome || '');
  const resolutionLabel = outcome === 'order'
    ? `ویزیت‌شده · ${count.toLocaleString('fa-IR')} درخواست ذخیره‌شده`
    : (outcome === 'no_order' ? 'ویزیت‌شده · بدون سفارش' : (outcome === 'skipped' || outcome === 'no_visit' ? 'عدم ویزیت ثبت شد' : ''));
  return `<strong class="route-customer-store">${esc(store)}</strong><small class="route-customer-person">${esc(person)}</small><small class="route-customer-address">${esc(address)}</small>${resolutionLabel ? `<small class="route-customer-resolution">✓ ${esc(resolutionLabel)}</small>` : ''}`;
}

function routeCustomerResolutionStatus(customer) {
  const outcome = String(customer?.visit_resolution?.outcome || '');
  if (outcome === 'order') return 'order';
  if (outcome === 'no_order') return 'no_order';
  if (outcome === 'no_visit' || outcome === 'skipped') return 'no_visit';
  return '';
}

function routeCustomerResolutionStatuses(customers = []) {
  return customers.reduce((statuses, customer) => {
    const status = routeCustomerResolutionStatus(customer);
    if (status) statuses[String(customer.id)] = status;
    return statuses;
  }, {});
}

function updateRouteCustomerResolution(customerId, outcome, savedRequestCount = 0) {
  if (!routeMapSession) return;
  const status = outcome === 'order' ? 'order' : (outcome === 'no_order' ? 'no_order' : 'no_visit');
  routeMapSession.stopStatuses[String(customerId)] = status;
  const plan = routeMapSession.plan || {};
  const customers = [...(plan.customers || []), ...(plan.ordered_customers || []), ...(plan.unlocated_customers || [])];
  customers.filter((customer) => String(customer.id) === String(customerId)).forEach((customer) => {
    customer.visit_resolution = {
      status: 'completed', outcome: status, saved_request_count: Number(savedRequestCount || 0), ended_at: new Date().toISOString(),
    };
  });
}

function hasRouteMapDebt(customer) {
  return Number(customer.cardex_balance || 0) !== 0 || Number(customer.open_invoice_remaining || 0) > 0;
}

function renderRouteMapLocationPolicy(policy = {}) {
  const target = $('#routeMapLocationPolicy');
  if (!target) return;
  target.classList.toggle('is-enabled', Boolean(policy.enforced));
  if (!policy.enabled) {
    target.textContent = 'کنترل فاصله در تنظیمات این بازاریاب خاموش است.';
    return;
  }
  const radius = Number(policy.max_distance_meters || 0);
  const scope = policy.scope ? ` · ${policy.scope}` : '';
  if (!policy.enforced) {
    target.textContent = `قانون فاصله خوانده شد${radius ? ` · شعاع ${radius.toLocaleString('fa-IR')} متر` : ''}${scope} · اجرای آن در شروع ویزیت موقتاً غیرفعال است`;
    return;
  }
  target.textContent = `کنترل مکان فعال${radius ? ` · شعاع ${radius.toLocaleString('fa-IR')} متر` : ''}${scope} · هنگام شروع ویزیت اعمال می‌شود`;
}

function routeMapLocationObservation(customer) {
  const session = routeMapSession;
  const policy = session?.plan?.visit_location_policy || {};
  if (!policy.enabled) return '';
  if (!policy.enforced) return ' · کنترل فاصله شروع ویزیت موقتاً غیرفعال';
  if (customer.location_check_exempt) return ' · مستثنا از کنترل مکان';
  const maxDistance = Number(policy.max_distance_meters || 0);
  if (!session?.position || !Number.isFinite(Number(customer.latitude)) || !Number.isFinite(Number(customer.longitude))) {
    return maxDistance ? ` · شعاع ${maxDistance.toLocaleString('fa-IR')} متر` : ' · کنترل مکان';
  }
  const distance = Math.round(distanceToRouteStopMeters(session.position, customer));
  const state = maxDistance && distance <= maxDistance ? 'داخل شعاع' : 'خارج شعاع';
  return ` · فاصله فعلی ${distance.toLocaleString('fa-IR')} متر · ${state}`;
}

function routeMapCustomerPopup(customer) {
  const analysis = customer.analysis || {};
  const financial = customer.financial_snapshot || {};
  const brands = (analysis.line_purchased_brands || []).map((brand) => brand.name).join('، ') || 'خریدی از برندهای لاین ثبت نشده';
  const invoices = Number(analysis.company_invoice_count_12m || 0);
  const cardex = Number(customer.cardex_balance || 0);
  const openRemaining = Number(customer.open_invoice_remaining || 0);
  const purchaseStatus = invoices ? `${invoices.toLocaleString('fa-IR')} فاکتور` : 'بدون خرید در ۱۲ ماه اخیر';
  const returnedCheque = Number(financial.returned_cheque_amount || 0);
  return `<div class="route-map-customer-popup"><strong>${esc(routeMapCustomerName(customer))}</strong><small>امتیاز احتمال خرید: ${Number(customer.visit_score || 0).toLocaleString('fa-IR')} · خرید ۱۲ ماه: ${purchaseStatus}</small><small>فروش ۱۲ ماه: ${routeMapMoney(analysis.company_net_sales_12m || 0)} · آخرین خرید: ${esc(analysis.last_invoice_date || 'ثبت نشده')}</small><div class="route-map-customer-popup-grid"><span><small>مانده کاردکس</small><b>${routeMapMoney(cardex)}</b></span><span><small>فاکتور باز این فروشنده</small><b>${routeMapMoney(openRemaining)} · ${Number(customer.open_invoice_count || 0).toLocaleString('fa-IR')} فقره</b></span><span><small>اعتبار بدهکاری</small><b>${routeMapMoney(financial.bed_credit)}</b></span><span><small>مانده اعتبار بدهکاری</small><b>${routeMapMoney(financial.remaining_bed_credit)}</b></span><span><small>اعتبار اسنادی</small><b>${routeMapMoney(financial.asn_credit)}</b></span><span><small>مانده اعتبار اسنادی</small><b>${routeMapMoney(financial.remaining_asn_credit)}</b></span><span><small>مانده حساب</small><b>${routeMapMoney(financial.customer_remaining)}</b></span><span><small>جمع مانده اعتبار</small><b>${routeMapMoney(financial.combined_remaining)}</b></span><span><small>اسناد/چک‌های باز</small><b>${routeMapMoney(financial.open_cheque_amount)} · ${Number(financial.open_cheque_count || 0).toLocaleString('fa-IR')} فقره</b></span><span><small>چک برگشتی</small><b class="${returnedCheque ? 'route-map-popup-warning' : ''}">${routeMapMoney(returnedCheque)} · ${Number(financial.returned_cheque_count || 0).toLocaleString('fa-IR')} فقره</b></span></div><small>برندهای لاین: ${esc(brands)}</small><button type="button" class="route-map-popup-visit" data-route-popup-previsit-customer="${esc(customer.id)}">ورود به ویزیت و سفارش این مشتری</button></div>`;
}

function routeMapCustomerPopupContent(customer, pathId) {
  const holder = document.createElement('div');
  holder.innerHTML = routeMapCustomerPopup(customer);
  const content = holder.firstElementChild;
  const visitButton = content.querySelector('[data-route-popup-previsit-customer]');
  visitButton.addEventListener('click', async (event) => {
    event.preventDefault();
    event.stopPropagation();
    if (visitButton.disabled) return;
    const idleLabel = visitButton.textContent;
    visitButton.disabled = true;
    visitButton.textContent = 'در حال ورود به سفارش‌گیری…';
    try {
      await openRouteCustomerProfile(pathId, customer.id, 'map');
    } catch (error) {
      toast(error.message || 'ورود به سفارش‌گیری انجام نشد.');
    } finally {
      if (visitButton.isConnected) {
        visitButton.disabled = false;
        visitButton.textContent = idleLabel;
      }
    }
  });
  return content;
}

function customerProfileMoney(value) {
  return `${Number(value || 0).toLocaleString('fa-IR')} ریال`;
}

function customerProfileLookupOptions(profile, kind, selectedValue) {
  const selected = String(selectedValue ?? '');
  return `<option value="">بدون انتخاب</option>${(profile.lookups?.[kind] || []).map((item) => `<option value="${esc(item.id)}" ${String(item.id) === selected ? 'selected' : ''}>${esc(item.title)}</option>`).join('')}`;
}

function customerProfileFieldValue(values, field) {
  const value = values[field];
  return value == null ? '' : value;
}

function renderCustomerProfile() {
  const profile = customerProfileState?.profile;
  if (!profile) return;
  const customer = profile.customer || {};
  const financial = customer.financial_snapshot || {};
  const controls = profile.visit_controls || {};
  const reports = controls.reports || {};
  const unrestrictedReports = !Object.keys(reports).length;
  const financialCards = [
    (unrestrictedReports || reports.cardex) && `<div class="customer-profile-card"><small>مانده کاردکس</small><b>${customerProfileMoney(customer.cardex_balance)}</b></div>`,
    (unrestrictedReports || reports.open_invoices) && `<div class="customer-profile-card"><small>فاکتور باز این فروشنده</small><b>${customerProfileMoney(customer.open_invoice_remaining)} · ${Number(customer.open_invoice_count || 0).toLocaleString('fa-IR')} فقره</b></div>`,
    (unrestrictedReports || reports.finance) && `<div class="customer-profile-card"><small>اعتبار بدهکاری</small><b>${customerProfileMoney(financial.bed_credit)}</b></div>`,
    (unrestrictedReports || reports.finance) && `<div class="customer-profile-card"><small>مانده اعتبار بدهکاری</small><b>${customerProfileMoney(financial.remaining_bed_credit)}</b></div>`,
    (unrestrictedReports || reports.finance) && `<div class="customer-profile-card"><small>اعتبار اسنادی</small><b>${customerProfileMoney(financial.asn_credit)}</b></div>`,
    (unrestrictedReports || reports.finance) && `<div class="customer-profile-card"><small>مانده اعتبار اسنادی</small><b>${customerProfileMoney(financial.remaining_asn_credit)}</b></div>`,
    (unrestrictedReports || reports.finance) && `<div class="customer-profile-card"><small>اسناد/چک باز</small><b>${customerProfileMoney(financial.open_cheque_amount)} · ${Number(financial.open_cheque_count || 0).toLocaleString('fa-IR')} فقره</b></div>`,
    (unrestrictedReports || reports.finance) && `<div class="customer-profile-card${Number(financial.returned_cheque_amount || 0) > 0 ? ' is-warning' : ''}"><small>چک برگشتی</small><b>${customerProfileMoney(financial.returned_cheque_amount)} · ${Number(financial.returned_cheque_count || 0).toLocaleString('fa-IR')} فقره</b></div>`,
  ].filter(Boolean).join('');
  const values = {...(customer.editable || {}), ...(profile.draft || {})};
  const registeredLatitude = Number(customerProfileFieldValue(values, 'latitude'));
  const registeredLongitude = Number(customerProfileFieldValue(values, 'longitude'));
  const hasRegisteredLocation = Number.isFinite(registeredLatitude) && Number.isFinite(registeredLongitude)
    && registeredLatitude !== 0 && registeredLongitude !== 0;
  const draftBadge = profile.draft ? `<span class="customer-profile-draft-badge">پیش‌نویس تغییرات ذخیره شده</span>` : '';
  $('#customerProfileTitle').textContent = customer.store_name || customer.name || 'اطلاعات مشتری';
  $('#customerProfileHint').textContent = `${profile.route?.title || 'مسیر روز'} · اطلاعات به‌روز مشتری`;
  $('#customerProfileBody').innerHTML = `
    <section class="customer-profile-hero"><div><small>مشتری مسیر روز</small><h3>${esc(customer.store_name || customer.name || 'مشتری')}</h3><p>${esc(customer.name || '')}${customer.code ? ` · کد ${esc(customer.code)}` : ''}</p><small>${esc(customer.address || 'نشانی ثبت نشده')}</small></div><span>${Number(customer.visit_count || 0).toLocaleString('fa-IR')} ویزیت · ${Number(customer.order_count || 0).toLocaleString('fa-IR')} سفارش</span></section>
    <section class="customer-profile-grid" aria-label="وضعیت مالی مشتری">
      ${financialCards || '<p>گزارش‌های مالی مشتری در تنظیمات این بازاریاب فعال نیست.</p>'}
    </section>
    <section class="customer-profile-section"><header><div><h3>مشخصات کامل و قابل‌ویرایش مشتری</h3><small>نام شخص مشتری فقط نمایشی است؛ سایر فیلدها بر اساس دسترسی فعال قابل ویرایش‌اند.</small></div>${draftBadge}</header>
      <form id="customerProfileForm" class="customer-profile-form">
        <label>نام مشتری<input value="${esc(customer.name || '')}" disabled></label>
        <label>نام فروشگاه<input data-customer-profile-field="store_name" maxlength="300" value="${esc(customerProfileFieldValue(values, 'store_name'))}" disabled></label>
        <label>کد مشتری<input data-customer-profile-field="customer_code" maxlength="50" value="${esc(customerProfileFieldValue(values, 'customer_code'))}" disabled></label>
        <label>تلفن<input data-customer-profile-field="phone" inputmode="tel" maxlength="50" value="${esc(customerProfileFieldValue(values, 'phone'))}" disabled></label>
        <label>موبایل<input data-customer-profile-field="mobile" inputmode="tel" maxlength="50" value="${esc(customerProfileFieldValue(values, 'mobile'))}" disabled></label>
        <label>کد ملی<input data-customer-profile-field="national_code" inputmode="numeric" maxlength="20" value="${esc(customerProfileFieldValue(values, 'national_code'))}" disabled></label>
        <label>کد اقتصادی<input data-customer-profile-field="economic_code" maxlength="50" value="${esc(customerProfileFieldValue(values, 'economic_code'))}" disabled></label>
        <label>کد پستی<input data-customer-profile-field="postal_code" inputmode="numeric" maxlength="20" value="${esc(customerProfileFieldValue(values, 'postal_code'))}" disabled></label>
        <label>فعالیت مشتری<select data-customer-profile-field="customer_activity_id" disabled>${customerProfileLookupOptions(profile, 'activity', customerProfileFieldValue(values, 'customer_activity_id'))}</select></label>
        <label>گروه مشتری<select data-customer-profile-field="customer_category_id" disabled>${customerProfileLookupOptions(profile, 'category', customerProfileFieldValue(values, 'customer_category_id'))}</select></label>
        <label>سطح مشتری<select data-customer-profile-field="customer_level_id" disabled>${customerProfileLookupOptions(profile, 'level', customerProfileFieldValue(values, 'customer_level_id'))}</select></label>
        <label>نوع مالکیت<select data-customer-profile-field="owner_type_ref" data-value-type="integer" disabled>${customerProfileLookupOptions(profile, 'owner_type', customerProfileFieldValue(values, 'owner_type_ref'))}</select></label>
        <label>استان<select data-customer-profile-field="state_id" disabled>${customerProfileLookupOptions(profile, 'state', customerProfileFieldValue(values, 'state_id'))}</select></label>
        <label>شهر<select data-customer-profile-field="city_id" disabled>${customerProfileLookupOptions(profile, 'city', customerProfileFieldValue(values, 'city_id'))}</select></label>
        <label>شهرستان<select data-customer-profile-field="county_id" disabled>${customerProfileLookupOptions(profile, 'county', customerProfileFieldValue(values, 'county_id'))}</select></label>
        <label>منطقه شهری<input data-customer-profile-field="city_zone" data-value-type="integer" type="number" min="0" value="${esc(customerProfileFieldValue(values, 'city_zone'))}" disabled></label>
        <label>عرض جغرافیایی<input data-customer-profile-field="latitude" data-value-type="number" type="number" min="-90" max="90" step="any" value="${esc(customerProfileFieldValue(values, 'latitude'))}" disabled></label>
        <label>طول جغرافیایی<input data-customer-profile-field="longitude" data-value-type="number" type="number" min="-180" max="180" step="any" value="${esc(customerProfileFieldValue(values, 'longitude'))}" disabled></label>
        <div class="customer-profile-location-capture is-wide">
          <button id="captureCustomerLocation" type="button" ${controls.set_customer_location === false ? 'hidden disabled' : ''}><span aria-hidden="true">＋</span> ثبت موقعیت فعلی مشتری</button>
          <small id="customerProfileLocationStatus">${hasRegisteredLocation ? 'این مشتری موقعیت ثبت‌شده دارد؛ با این دکمه می‌توانید آن را با GPS فعلی جایگزین کنید.' : 'این مشتری موقعیت ثبت‌شده ندارد؛ کنار محل مشتری بایستید و این دکمه را بزنید.'}</small>
        </div>
        <label class="is-wide">نشانی<textarea data-customer-profile-field="address" maxlength="1000" disabled>${esc(customerProfileFieldValue(values, 'address'))}</textarea></label>
      </form>
      <p class="customer-profile-note">ویرایش‌ها به‌صورت پیش‌نویس امن ذخیره می‌شوند و پس از تأیید در همگام‌سازی بعدی ارسال خواهند شد.</p>
      <div class="customer-profile-actions"><button id="editCustomerProfile" type="button" ${controls.allow_edit_customer === false ? 'hidden disabled' : ''}>ویرایش اطلاعات مشتری</button><button id="saveCustomerProfileDraft" type="button" hidden>ذخیره پیش‌نویس تغییرات</button><button id="cancelCustomerProfileEdit" type="button" class="dialog-secondary" hidden>انصراف از ویرایش</button><button id="continueCustomerProfileOrder" type="button">ادامه و ورود به سفارش‌گیری</button></div>
    </section>`;
}

async function openRouteCustomerProfile(routeId, customerId, origin = 'map') {
  rememberAppView('customer-profile', {routeId: String(routeId), customerId: String(customerId), origin});
  const previousMapHidden = routeMapPanel.hidden;
  const previousWorkspaceHidden = sellerWorkspacePanel.hidden;
  customerProfileState = {routeId: String(routeId), customerId: String(customerId), origin, previousMapHidden, previousWorkspaceHidden, profile: null};
  routeMapPanel.hidden = true;
  sellerWorkspacePanel.hidden = true;
  previsitPanel.hidden = true;
  customerProfilePanel.hidden = false;
  $('#customerProfileTitle').textContent = 'اطلاعات مشتری';
  $('#customerProfileHint').textContent = 'در حال دریافت اطلاعات کامل مشتری…';
  $('#customerProfileBody').innerHTML = '<p class="customer-profile-loading">در حال دریافت مشخصات، وضعیت مالی و گزینه‌های قابل‌ویرایش…</p>';
  try {
    const response = await fetch(`/seller-workspace/routes/${encodeURIComponent(routeId)}/customers/${encodeURIComponent(customerId)}/profile`);
    const data = await readJsonResponse(response, 'اطلاعات مشتری دریافت نشد.');
    if (!response.ok) throw Error(data.detail || 'اطلاعات مشتری دریافت نشد.');
    if (!customerProfileState || customerProfileState.routeId !== String(routeId) || customerProfileState.customerId !== String(customerId)) return false;
    customerProfileState.profile = data;
    renderCustomerProfile();
    return true;
  } catch (error) {
    closeCustomerProfile();
    closeCurrentAppView('customer-profile');
    toast(error.message || 'اطلاعات مشتری دریافت نشد.');
    return false;
  }
}

function closeCustomerProfile() {
  const state = customerProfileState;
  customerProfilePanel.hidden = true;
  customerProfileState = null;
  if (!state) return;
  if (state.origin === 'map' && routeMapSession) {
    routeMapPanel.hidden = false;
    requestAnimationFrame(() => routeMapInstance?.resize());
  } else if (state.origin === 'workspace') {
    sellerWorkspacePanel.hidden = false;
  }
}

function setCustomerProfileEditMode(editing) {
  const form = $('#customerProfileForm');
  if (!form) return;
  $$('[data-customer-profile-field]', form).forEach((field) => { field.disabled = !editing; });
  $('#editCustomerProfile').hidden = editing;
  $('#saveCustomerProfileDraft').hidden = !editing;
  $('#cancelCustomerProfileEdit').hidden = !editing;
}

function customerProfileDraftPayload() {
  const payload = {};
  $$('[data-customer-profile-field]', $('#customerProfileForm')).forEach((field) => {
    const raw = String(field.value || '').trim();
    const type = field.dataset.valueType;
    payload[field.dataset.customerProfileField] = raw === '' && type ? null : (type === 'integer' ? Number.parseInt(raw, 10) : (type === 'number' ? Number(raw) : raw));
  });
  return payload;
}

async function captureCustomerProfileLocation() {
  if (!customerProfileState?.profile) return;
  const button = $('#captureCustomerLocation');
  if (!button || button.disabled) return;
  const idleLabel = button.innerHTML;
  button.disabled = true;
  button.setAttribute('aria-busy', 'true');
  button.textContent = 'در حال دریافت GPS…';
  try {
    const position = await currentCoordinates({maximumAge: 0, timeout: 12000});
    if (!position) {
      toast('موقعیت دریافت نشد؛ دسترسی Location دستگاه را روشن و دوباره تلاش کنید.');
      return;
    }
    setCustomerProfileEditMode(true);
    const form = $('#customerProfileForm');
    const latitudeInput = $('[data-customer-profile-field="latitude"]', form);
    const longitudeInput = $('[data-customer-profile-field="longitude"]', form);
    if (!latitudeInput || !longitudeInput) return;
    latitudeInput.value = position.latitude.toFixed(7);
    longitudeInput.value = position.longitude.toFixed(7);
    const accuracy = Number.isFinite(position.accuracy) ? ` · دقت تقریبی ${Math.round(position.accuracy).toLocaleString('fa-IR')} متر` : '';
    const status = $('#customerProfileLocationStatus');
    if (status) status.textContent = `موقعیت فعلی در فرم قرار گرفت${accuracy}. هنوز ذخیره نهایی نشده است.`;
    toast('موقعیت فعلی مشتری در فرم قرار گرفت؛ برای نگهداری این موقعیت، پیش‌نویس تغییرات را ذخیره کنید.');
  } finally {
    if (button.isConnected) {
      button.disabled = false;
      button.removeAttribute('aria-busy');
      button.innerHTML = idleLabel;
    }
  }
}

async function saveCustomerProfileDraft() {
  const state = customerProfileState;
  if (!state?.profile) return;
  const button = $('#saveCustomerProfileDraft');
  button.disabled = true;
  button.textContent = 'در حال ذخیره…';
  try {
    const response = await fetch(`/seller-workspace/routes/${encodeURIComponent(state.routeId)}/customers/${encodeURIComponent(state.customerId)}/profile-draft`, {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(customerProfileDraftPayload())});
    const data = await readJsonResponse(response, 'ذخیره تغییرات مشتری انجام نشد.');
    if (!response.ok) throw Error(data.detail || 'ذخیره تغییرات مشتری انجام نشد.');
    state.profile.draft = data.draft;
    state.profile.draft_updated_at = data.updated_at;
    renderCustomerProfile();
    toast('پیش‌نویس تغییرات مشتری امن و محلی ذخیره شد.');
  } finally {
    if (button.isConnected) { button.disabled = false; button.textContent = 'ذخیره پیش‌نویس تغییرات'; }
  }
}

function distanceToRouteStopMeters(position, customer) {
  const radius = 6371000;
  const radians = (value) => value * Math.PI / 180;
  const latitudeDelta = radians(customer.latitude - position.latitude);
  const longitudeDelta = radians(customer.longitude - position.longitude);
  const a = Math.sin(latitudeDelta / 2) ** 2 + Math.cos(radians(position.latitude)) * Math.cos(radians(customer.latitude)) * Math.sin(longitudeDelta / 2) ** 2;
  return 2 * radius * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function bearingBetweenPositions(from, to) {
  const radians = (value) => value * Math.PI / 180;
  const latitudeDelta = radians(to.latitude - from.latitude);
  const longitudeDelta = radians(to.longitude - from.longitude);
  const y = Math.sin(longitudeDelta) * Math.cos(radians(to.latitude));
  const x = Math.cos(radians(from.latitude)) * Math.sin(radians(to.latitude))
    - Math.sin(radians(from.latitude)) * Math.cos(radians(to.latitude)) * Math.cos(longitudeDelta);
  return (Math.atan2(y, x) * 180 / Math.PI + 360) % 360;
}

function sellerHeading(position) {
  if (Number.isFinite(position.heading) && position.heading >= 0) return position.heading;
  const previous = routeMapSession?.lastPositionForHeading;
  if (previous && distanceToRouteStopMeters(previous, position) >= 5) return bearingBetweenPositions(previous, position);
  return routeMapSession?.heading || 0;
}

function drawRouteMapLine(polyline) {
  if (!routeMapInstance?.isStyleLoaded()) return;
  const line = decodePolyline(polyline || '');
  if (routeMapInstance.getLayer('route-line')) routeMapInstance.removeLayer('route-line');
  if (routeMapInstance.getSource('route-line')) routeMapInstance.removeSource('route-line');
  if (line.length < 2) return;
  routeMapInstance.addSource('route-line', { type: 'geojson', data: { type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates: line } } });
  routeMapInstance.addLayer({ id: 'route-line', type: 'line', source: 'route-line', paint: { 'line-color': '#176b54', 'line-width': 5, 'line-opacity': .85 } });
}

function focusRouteMapLeg(polyline) {
  if (!routeMapInstance?.isStyleLoaded()) return;
  const line = decodePolyline(polyline || '');
  if (line.length < 2) return;
  const bounds = line.reduce(
    (current, coordinate) => current.extend(coordinate),
    new routeMapSession.maplibregl.LngLatBounds(line[0], line[0]),
  );
  routeMapInstance.fitBounds(bounds, { padding: { top: 72, right: 48, bottom: 150, left: 48 }, maxZoom: 16, duration: 550 });
}

async function activateNextRouteStop() {
  const session = routeMapSession;
  const next = session?.plan.ordered_customers?.[session.activeIndex];
  if (!session || !next) return;
  session.currentLeg = null;
  session.currentLegPolyline = '';
  session.arrivedPrompted = false;
  prepareRouteInstructions();
  const position = session.position || await currentCoordinates();
  if (position) {
    session.position = position;
    await refreshActiveRouteLeg(position);
  }
  updateRouteMapCustomerMarkerVisibility();
  renderRouteMapStops();
}

async function completeActiveRouteStop(automatic = false, outcome = 'skipped') {
  if (!routeMapSession) return;
  const total = (routeMapSession.plan.ordered_customers || []).length;
  if (routeMapSession.activeIndex >= total) return;
  const completed = routeMapSession.plan.ordered_customers?.[routeMapSession.activeIndex];
  if (completed) routeMapSession.stopStatuses[String(completed.id)] = automatic ? 'visited' : outcome;
  if (automatic && !isIOS) void speakRouteInstruction('به پایگاه رسیدید.');
  routeMapSession.activeIndex += 1;
  if (routeMapSession.activeIndex >= total) $('#routeMapStartBtn').textContent = 'مسیر روز کامل شد';
  const resultLabel = automatic || outcome === 'visited' ? 'ویزیت شد' : 'رد شد';
  toast(routeMapSession.activeIndex >= total ? `مسیر روز تکمیل شد؛ آخرین مشتری ${resultLabel}.` : (automatic ? 'به پایگاه رسیدی؛ مسیر پایگاه بعدی فعال شد.' : `مشتری ${resultLabel}؛ مسیر پایگاه بعدی در حال نمایش است.`));
  await activateNextRouteStop();
  if (routeMapSession.activeIndex < total && !isIOS) {
    void speakRouteInstruction(routeMapSession.navigationSteps?.[0]?.instruction || 'حرکت به پایگاه بعدی را شروع کنید.');
  }
  renderRouteMapInstruction();
}

function renderRouteMapStops() {
  const session = routeMapSession;
  if (!session) return;
  const ordered = session.plan.ordered_customers || [];
  const customerListOnly = routeMapPanel.dataset.routeDayView === 'customers';
  if (!ordered.length) {
    $('#routeMapStops').innerHTML = '<p class="organization-empty">مشتری دارای موقعیت مکانی در این مسیر پیدا نشد.</p>';
    return;
  }
  if (session.activeIndex >= ordered.length) {
    $('#routeMapTitle').textContent = customerListOnly ? `لیست مشتریان روز · ${session.title}` : `تور ویزیت · ${session.title}`;
    $('#routeMapHint').textContent = customerListOnly ? `${ordered.length.toLocaleString('fa-IR')} مشتری در برنامه امروز` : 'همه پایگاه‌های برنامه امروز ثبت شد.';
    $('#routeMapStops').innerHTML = ordered.map((customer, index) => {
      const status = session.stopStatuses[String(customer.id)] || routeCustomerResolutionStatus(customer) || 'visited';
      const debtClass = !customerListOnly && hasRouteMapDebt(customer) ? 'has-debt' : '';
      const identity = customerListOnly ? routeCustomerListIdentity(customer)
        : `<strong>${esc(routeMapCustomerName(customer))}</strong><small>${status === 'visited' ? 'ویزیت شد' : 'عدم ویزیت ثبت شد'} · لمس برای اطلاعات مشتری</small>`;
      return `<article class="route-map-stop is-complete route-status-${status} ${routeMapPriorityClass(customer, ordered)} ${debtClass}" data-route-map-previsit-customer="${esc(customer.id)}" role="button" tabindex="0"><b>✓</b><span>${identity}${renderRouteCustomerVisitActions(customer, status)}</span></article>`;
    }).join('') + renderUnlocatedRouteCustomers(session.plan.unlocated_customers || []);
    return;
  }
  const active = ordered[session.activeIndex];
  const leg = routeMapLegFor(session.activeIndex);
  const eta = leg?.duration?.text ? `زمان رسیدن ${esc(leg.duration.text)}` : (session.position ? 'زمان رسیدن در حال محاسبه است' : 'موقعیت فعلی در دسترس نیست');
  const distance = leg?.distance?.text ? ` · ${esc(leg.distance.text)}` : '';
  $('#routeMapTitle').textContent = customerListOnly ? `لیست مشتریان روز · ${session.title}` : `تور ویزیت · ${session.title}`;
  $('#routeMapHint').textContent = customerListOnly
    ? `${ordered.length.toLocaleString('fa-IR')} مشتری · ورود به ویزیت یا ثبت عدم ویزیت`
    : `حرکت به پایگاه ${(session.activeIndex + 1).toLocaleString('fa-IR')} از ${ordered.length.toLocaleString('fa-IR')} · ${eta}${distance}`;
  // The day list must remain complete while navigation is running.  Only the
  // action buttons follow the active stop; every customer stays selectable.
  const visibleStops = ordered;
  $('#routeMapStops').innerHTML = visibleStops.map((customer, index) => {
    const completedStatus = session.stopStatuses[String(customer.id)] || routeCustomerResolutionStatus(customer);
    const state = completedStatus ? ` is-complete route-status-${completedStatus}` : (!customerListOnly && index === session.activeIndex ? ' is-active' : '');
    const badge = completedStatus ? '✓' : (index + 1).toLocaleString('fa-IR');
    const action = !customerListOnly && index === session.activeIndex ? (session.starting
      ? '<button type="button" class="route-map-arrived is-loading" disabled aria-busy="true">در حال دریافت مسیر و GPS…</button>'
      : (session.started ? '<div class="route-map-actions"><button type="button" class="route-map-visited" data-route-map-visited>ویزیت شد</button><button type="button" class="route-map-skipped" data-route-map-skipped>رد کردن</button></div>' : '<button type="button" class="route-map-arrived" data-route-map-start>شروع حرکت به پایگاه اول</button>')) : '';
    const hasAnalytics = session.plan.analytics_available !== false
      && customer.analysis && Object.keys(customer.analysis).length > 0;
    const purchase = !hasAnalytics
      ? 'اولویت تحلیلی در حال تکمیل'
      : (Number(customer.analysis?.company_invoice_count_12m || 0) === 0
        ? 'بدون خرید ۱۲ ماه'
        : `امتیاز ویزیت ${Number(customer.visit_score || 0).toLocaleString('fa-IR')}`);
    const debt = hasRouteMapDebt(customer) ? ` · مانده‌دار: ${routeMapMoney(customer.cardex_balance)}` : '';
    const observation = routeMapLocationObservation(customer);
    const subtext = completedStatus
      ? (completedStatus === 'visited' ? 'ویزیت شد' : 'عدم ویزیت ثبت شد')
      : (index === session.activeIndex ? `${eta}${distance}${observation}` : `${purchase}${debt}${observation} · ${esc(customer.address || 'موقعیت ثبت‌شده')}`);
    const debtClass = !customerListOnly && hasRouteMapDebt(customer) ? 'has-debt' : '';
    const identity = customerListOnly ? routeCustomerListIdentity(customer)
      : `<strong>${esc(routeMapCustomerName(customer))}</strong><small>${subtext} · لمس برای اطلاعات مشتری</small>`;
    return `<article class="route-map-stop${state} ${routeMapPriorityClass(customer, ordered)} ${debtClass}" data-route-map-previsit-customer="${esc(customer.id)}" role="button" tabindex="0"><b>${badge}</b><span>${identity}${renderRouteCustomerVisitActions(customer, completedStatus)}${action}</span></article>`;
  }).join('') + renderUnlocatedRouteCustomers(session.plan.unlocated_customers || []);
  focusRouteMapStop();
}

function updateRouteMapCustomerMarkerVisibility() {
  const session = routeMapSession;
  if (!session?.customerMarkers) return;
  const finalVisibleIndex = session.started ? session.activeIndex : Infinity;
  session.customerMarkers.forEach(({ marker, index }) => {
    marker.getElement().style.display = index <= finalVisibleIndex ? '' : 'none';
  });
}

function routeMapPriorityClass(customer, customers) {
  const hasAnalytics = routeMapSession?.plan?.analytics_available !== false
    && customer.analysis && Object.keys(customer.analysis).length > 0;
  if (!hasAnalytics) return 'priority-low';
  if (Number(customer.analysis?.company_invoice_count_12m || 0) === 0) return 'priority-no-purchase';
  const max = Math.max(1, ...customers.map((item) => Number(item.visit_score || 0)));
  const ratio = Number(customer.visit_score || 0) / max;
  return ratio >= .67 ? 'priority-high' : (ratio >= .34 ? 'priority-medium' : 'priority-low');
}

function renderUnlocatedRouteCustomers(customers) {
  if (!customers.length) return '';
  const customerListOnly = routeMapPanel.dataset.routeDayView === 'customers';
  const heading = customerListOnly ? '' : '<p class="route-map-unlocated-title">مشتری‌های بدون موقعیت ثبت‌شده</p>';
  return `${heading}${customers.map((customer) => {
    const completedStatus = routeMapSession?.stopStatuses?.[String(customer.id)] || routeCustomerResolutionStatus(customer);
    const identity = customerListOnly ? routeCustomerListIdentity(customer)
      : `<strong>${esc(customer.store_name || customer.name || 'مشتری')}</strong><small>امتیاز ویزیت ${Number(customer.visit_score || 0).toLocaleString('fa-IR')}${routeMapLocationObservation(customer)} · لمس برای اطلاعات مشتری</small>`;
    return `<article class="route-map-stop ${completedStatus ? `is-complete route-status-${completedStatus}` : (customerListOnly ? '' : 'is-unlocated')} ${routeMapPriorityClass(customer, customers)}" data-route-map-previsit-customer="${esc(customer.id)}" role="button" tabindex="0"><b>${completedStatus ? '✓' : '•'}</b><span>${identity}${renderRouteCustomerVisitActions(customer, completedStatus)}</span></article>`;
  }).join('')}`;
}

function renderRouteCustomerVisitActions(customer, completedStatus = '') {
  if (completedStatus) return '';
  return `<div class="route-tour-customer-actions"><button type="button" data-route-customer-enter-visit="${esc(customer.id)}">ورود به ویزیت</button><button type="button" data-route-customer-no-visit="${esc(customer.id)}">عدم ویزیت</button></div>`;
}

function updateRouteMapSellerPosition(position) {
  if (!routeMapSession || !routeMapInstance || !routeMapSession.maplibregl) return;
  routeMapSession.position = position;
  routeMapSession.heading = sellerHeading(position);
  routeMapSession.lastPositionForHeading = position;
  if (!routeMapInstance.isStyleLoaded()) return;
  const coordinates = [position.longitude, position.latitude];
  if (routeMapSellerMarker) {
    routeMapSellerMarker.setLngLat(coordinates);
    routeMapSellerMarker.getElement().style.setProperty('--seller-heading', `${routeMapSession.heading}deg`);
  } else {
    const element = document.createElement('div');
    element.className = 'route-map-seller-arrow';
    element.title = 'جهت حرکت شما';
    element.style.setProperty('--seller-heading', `${routeMapSession.heading}deg`);
    element.innerHTML = '<span aria-hidden="true"></span>';
    routeMapSellerMarker = new routeMapSession.maplibregl.Marker({ element, rotationAlignment: 'map' })
      .setLngLat(coordinates).setPopup(new routeMapSession.maplibregl.Popup().setText('موقعیت فعلی و جهت حرکت شما')).addTo(routeMapInstance);
  }
  const active = routeMapSession.plan.ordered_customers?.[routeMapSession.activeIndex];
  updateRouteNavigationProgress(position);
  renderRouteMapInstruction();
  maybeRerouteActiveRoute(position);
  followRouteMapPosition(position);
  if (routeMapSession.started && active && distanceToRouteStopMeters(position, active) <= 70 && !routeMapSession.arrivedPrompted) {
    routeMapSession.arrivedPrompted = true;
    routeMapSession.followUser = false;
    $('#routeMapRecenterBtn').hidden = true;
    if (!isIOS) void speakRouteInstruction(`به مقصد رسیدید. ${routeMapCustomerName(active)}`);
    setRouteMapStatus('به مقصد رسیدید');
    window.setTimeout(() => { if (routeMapSession?.arrivedPrompted) setRouteMapStatus(''); }, 5000);
    toast('به مشتری رسیدید؛ «ویزیت شد» یا «رد کردن» را انتخاب کنید.');
  }
  renderRouteMapStops();
  renderRouteMapTripSummary();
}

function applyRouteMapLocation(position) {
  if (!position || (Number.isFinite(position.accuracy) && position.accuracy > 100)) return;
  updateRouteMapSellerPosition(position);
}

window.addEventListener('negin-native-location', (event) => {
  if (!routeMapSession?.started) return;
  const detail = event.detail || {};
  applyRouteMapLocation({
    latitude: Number(detail.latitude), longitude: Number(detail.longitude),
    accuracy: Number(detail.accuracy), heading: Number(detail.heading),
    speed: Number(detail.speed), timestamp: Number(detail.timestamp) || Date.now(),
  });
});

function stopRouteMap() {
  if (routeMapLocationWatch !== null) navigator.geolocation?.clearWatch(routeMapLocationWatch);
  routeMapLocationWatch = null;
  navigationSpeechAbortController?.abort();
  navigationSpeechAbortController = null;
  try { navigationAudioSource?.stop(); } catch (_) {}
  try { window.NeginAndroid?.stopNavigationVoice?.(); } catch (_) {}
  try { window.NeginAndroid?.stopNavigationLocationTracking?.(); } catch (_) {}
  navigationAudioSource = null;
  routeMapSellerMarker = null;
  routeMapSession = null;
  routeMapInstance?.remove();
  routeMapInstance = null;
  setRouteMapStatus('');
  const summary = $('#routeMapTripSummary');
  if (summary) summary.hidden = true;
  const recenter = $('#routeMapRecenterBtn');
  if (recenter) recenter.hidden = true;
  const startButton = $('#routeMapStartBtn');
  if (startButton) { startButton.disabled = false; startButton.textContent = 'شروع مسیر'; }
}

function toggleRouteDayMenu(open = !routeDayActionRail?.classList.contains('is-open')) {
  if (!routeDayActionRail) return;
  routeDayActionRail.classList.toggle('is-open', open);
  $('#routeDayMenuToggle')?.setAttribute('aria-expanded', String(open));
  const backdrop = $('#routeDayMenuBackdrop');
  if (backdrop) backdrop.hidden = !open;
}

function setRouteDayActiveAction(action = 'customers') {
  if (!routeDayActionRail) return;
  $$('[data-route-day-action]', routeDayActionRail).forEach((button) => {
    const active = button.dataset.routeDayAction === action;
    button.classList.toggle('is-active', active);
    if (active) button.setAttribute('aria-current', 'page');
      else button.removeAttribute('aria-current');
  });
  routeMapPanel.dataset.routeDayView = action;
  const savedRequests = $('#routeDaySavedRequests');
  if (savedRequests) savedRequests.hidden = action !== 'requests';
  toggleRouteDayMenu(false);
  if (routeMapSession) renderRouteMapStops();
  if (action === 'map') requestAnimationFrame(() => routeMapInstance?.resize());
}

function routeDayCustomerById(customerId) {
  const plan = routeMapSession?.plan || {};
  return [...(plan.customers || []), ...(plan.ordered_customers || []), ...(plan.unlocated_customers || [])]
    .find((customer) => String(customer.id) === String(customerId));
}

async function loadRouteDaySavedRequests() {
  if (!routeMapSession) return;
  const list = $('#routeDaySavedRequestList');
  const count = $('#routeDaySavedRequestCount');
  list.innerHTML = '<p class="organization-empty">در حال دریافت درخواست‌های امروز…</p>';
  const response = await fetch(`/seller-workspace/routes/${encodeURIComponent(routeMapSession.pathId)}/saved-requests`);
  const data = await readJsonResponse(response, 'درخواست‌های ثبت‌شده دریافت نشد.');
  if (!response.ok) throw Error(data.detail || 'درخواست‌های ثبت‌شده دریافت نشد.');
  const requests = data.requests || [];
  count.textContent = `${requests.length.toLocaleString('fa-IR')} درخواست`;
  list.innerHTML = requests.length ? requests.map((saved) => {
    const customer = routeDayCustomerById(saved.customer_id) || {};
    const customerName = routeMapCustomerName(customer) || `مشتری ${saved.customer_id}`;
    return `<article><header><div><small>مشتری</small><strong>${esc(customerName)}</strong></div><b>درخواست ${Number(saved.request_number || 0).toLocaleString('fa-IR')}</b></header><dl><div><dt>تعداد اقلام</dt><dd>${Number(saved.line_count || 0).toLocaleString('fa-IR')} قلم</dd></div><div><dt>مبلغ</dt><dd>${Number(saved.total_amount || 0).toLocaleString('fa-IR')} ریال</dd></div><div><dt>انبار</dt><dd>${esc(saved.warehouse_name || '—')}</dd></div></dl><button type="button" data-route-saved-request-customer="${esc(saved.customer_id)}">ورود به مشتری</button></article>`;
  }).join('') : '<p class="organization-empty">برای مشتریان این تور هنوز درخواستی ذخیره نشده است.</p>';
}

function provisionalRouteMapPlan(routeData) {
  const customers = Array.isArray(routeData?.customers) ? routeData.customers : [];
  const hasLocation = (customer) => {
    const latitude = Number(customer?.latitude);
    const longitude = Number(customer?.longitude);
    return Number.isFinite(latitude) && Number.isFinite(longitude) && latitude !== 0 && longitude !== 0;
  };
  return {
    route: routeData?.route || {},
    customers,
    ordered_customers: customers.filter(hasLocation),
    unlocated_customers: customers.filter((customer) => !hasLocation(customer)),
    missing_location_count: customers.filter((customer) => !hasLocation(customer)).length,
    polyline: '', initial_leg: null, route_mode: 'sales_priority',
    visit_location_policy: routeData?.visit_location_policy || {},
    analytics_available: false,
  };
}

async function openRouteMap(pathId, title) {
  rememberAppView('route-map', {pathId: String(pathId), title: String(title || '')});
  stopRouteMap();
  setRouteDayActiveAction('customers');
  routeMapPanel.hidden = false;
  const voiceButton = $('#routeMapVoiceBtn');
  voiceButton.textContent = isIOS ? 'راهنمای مسیر' : '🔊 صدا روشن';
  voiceButton.classList.remove('route-map-voice-off');
  const mapStartButton = $('#routeMapStartBtn');
  mapStartButton.disabled = true;
  mapStartButton.textContent = 'در حال آماده‌سازی…';
  $('#routeMapTitle').textContent = `تور ویزیت · ${title}`;
  $('#routeMapHint').textContent = 'در حال دریافت موقعیت و مسیر بهینه…';
  $('#routeMapLocationPolicy').textContent = 'در حال خواندن تنظیم کنترل مکان…';
  $('#routeMapLocationPolicy').classList.remove('is-enabled');
  $('#routeMapStops').innerHTML = '';
  try {
    // The customer list is the primary tour workspace and must not wait for
    // GPS permission or the map provider to become available.
    const routeResponse = await fetch(`/seller-workspace/routes/${encodeURIComponent(pathId)}/customers`);
    if (!routeResponse.ok) throw Error('لیست مشتریان مسیر دریافت نشد.');
    const routeData = await routeResponse.json();
    const provisionalPlan = provisionalRouteMapPlan(routeData);
    renderRouteMapLocationPolicy(provisionalPlan.visit_location_policy);
    routeMapSession = {
      pathId, title, plan: provisionalPlan, routeMode: 'sales_priority', position: null,
      activeIndex: 0, stopStatuses: routeCustomerResolutionStatuses(provisionalPlan.customers || []), currentLeg: null, currentLegPolyline: '',
      started: false, starting: true, customerMarkers: [], maplibregl: null,
      voiceEnabled: true, followUser: true, offRouteSince: null, hasNavigationRoute: false,
    };
    $('#routeMapHint').textContent = 'لیست مشتریان آماده است؛ اولویت و مسیر در حال تکمیل است…';
    renderRouteMapStops();
    setRouteDayActiveAction('customers');
    const [configResponse, position] = await Promise.all([
      fetch('/seller-workspace/map-config'),
      currentCoordinates(),
    ]);
    if (!configResponse.ok) throw Error('کلید نقشه نشان آماده نیست.');
    const config = await configResponse.json();
    const params = new URLSearchParams();
    if (position) { params.set('origin_latitude', position.latitude); params.set('origin_longitude', position.longitude); }
    params.set('route_mode', $('#routeMapMode').value || 'sales_priority');
    params.set('start_day_route', 'true');
    const planResponse = await fetch(`/seller-workspace/routes/${encodeURIComponent(pathId)}/map-plan?${params}`);
    if (!planResponse.ok) {
      const errorData = await planResponse.json().catch(() => ({}));
      throw Error(errorData.detail || 'مسیر بهینه دریافت نشد.');
    }
    const plan = await planResponse.json();
    renderRouteMapLocationPolicy(plan.visit_location_policy || {});
    mapStartButton.disabled = !(plan.ordered_customers || []).length;
    mapStartButton.textContent = mapStartButton.disabled ? 'مشتری دارای موقعیت نیست' : 'شروع مسیر';
    // UMD نسخهٔ نشان maplibregl را مستقیم روی window می‌گذارد؛ بعضی نسخه‌ها آن را زیر default می‌گذارند.
    const maplibregl = window.maplibregl?.default || window.maplibregl;
    if (!maplibregl) throw Error('نقشه نشان بارگذاری نشد.');
    routeMapSession = {
      pathId, title, plan, routeMode: plan.route_mode || 'sales_priority', position,
      activeIndex: 0, stopStatuses: routeCustomerResolutionStatuses([...(plan.ordered_customers || []), ...(plan.unlocated_customers || [])]), currentLeg: plan.initial_leg || null,
      currentLegPolyline: plan.polyline || '', started: false, customerMarkers: [], maplibregl,
      voiceEnabled: true, followUser: true, offRouteSince: null, hasNavigationRoute: false,
    };
    prepareRouteInstructions();
    routeMapInstance = new maplibregl.Map({ container: 'routeMapCanvas', style: 'https://static.neshan.org/sdk/maplibre/styles/light.json', center: [51.4, 35.7], zoom: 10, apiKey: config.api_key, rtl: { lazy: false } });
    routeMapInstance.addControl(new maplibregl.NavigationControl());
    routeMapInstance.on('error', (event) => {
      const message = event?.error?.message || 'بارگذاری نقشه نشان با خطا روبه‌رو شد.';
      $('#routeMapHint').textContent = `خطای نقشه: ${message}`;
    });
    routeMapInstance.on('dragstart', (event) => {
      if (!event.originalEvent || !routeMapSession?.started) return;
      routeMapSession.followUser = false;
      $('#routeMapRecenterBtn').hidden = false;
    });
    routeMapInstance.on('zoomstart', (event) => {
      if (!event.originalEvent || !routeMapSession?.started) return;
      routeMapSession.followUser = false;
      $('#routeMapRecenterBtn').hidden = false;
    });
    routeMapInstance.on('load', () => {
      const bounds = new maplibregl.LngLatBounds();
      const ordered = plan.ordered_customers || [];
      (plan.ordered_customers || []).forEach((customer, index) => {
        const priority = routeMapPriorityClass(customer, ordered);
        const markerColor = priority === 'priority-no-purchase' ? '#c94d4d' : (hasRouteMapDebt(customer) ? '#7c3aed' : (priority === 'priority-high' ? '#1d6fea' : (priority === 'priority-medium' ? '#d38b18' : '#71807c')));
        const marker = new maplibregl.Marker({ color: markerColor }).setLngLat([customer.longitude, customer.latitude]).addTo(routeMapInstance);
        routeMapSession.customerMarkers.push({ marker, index });
        marker.getElement().title = `${index + 1}. ${routeMapCustomerName(customer)}`;
        marker.getElement().setAttribute('role', 'button');
        marker.getElement().setAttribute('tabindex', '0');
        marker.getElement().addEventListener('click', (event) => {
          event.preventDefault();
          event.stopPropagation();
          void openRouteCustomerProfile(pathId, customer.id, 'map');
        });
        marker.getElement().addEventListener('keydown', (event) => {
          if (event.key !== 'Enter' && event.key !== ' ') return;
          event.preventDefault();
          void openRouteCustomerProfile(pathId, customer.id, 'map');
        });
        bounds.extend([customer.longitude, customer.latitude]);
      });
      drawRouteMapLine(routeMapSession.currentLegPolyline);
      if (position) {
        bounds.extend([position.longitude, position.latitude]);
        updateRouteMapSellerPosition(position);
        // Route-plan orders the whole day; the displayed navigation line must
        // be only the live leg to the first active stop.
        void refreshActiveRouteLeg(position);
      }
      if (!bounds.isEmpty()) routeMapInstance.fitBounds(bounds, { padding: 45, maxZoom: 14 });
      renderRouteMapStops();
      setRouteDayActiveAction('customers');
    });
    if (navigator.geolocation) routeMapLocationWatch = navigator.geolocation.watchPosition(
      (next) => {
        // Ignore visibly inaccurate fixes; they otherwise cause premature arrival and spurious reroutes.
        if (Number.isFinite(next.coords.accuracy) && next.coords.accuracy > 100) return;
        applyRouteMapLocation({
          latitude: next.coords.latitude, longitude: next.coords.longitude,
          heading: Number.isFinite(next.coords.heading) ? next.coords.heading : null,
          accuracy: Number.isFinite(next.coords.accuracy) ? next.coords.accuracy : null,
          speed: Number.isFinite(next.coords.speed) ? next.coords.speed : null,
          timestamp: next.timestamp || Date.now(),
        });
      },
      () => {}, { enableHighAccuracy: true, maximumAge: 15000, timeout: 20000 },
    );
  } catch (error) {
    const hasCustomers = Boolean(routeMapSession?.plan?.customers?.length);
    $('#routeMapHint').textContent = hasCustomers
      ? `لیست مشتریان آماده است؛ مسیریابی فعلاً کامل نشد: ${error.message}`
      : error.message;
    if (!hasCustomers) $('#routeMapStops').innerHTML = `<p class="organization-empty">${esc(error.message)}</p>`;
  }
}

function renderRouteCustomers(target, data) {
  const customers = data.customers || [];
  const money = (value) => `${Number(value || 0).toLocaleString('fa-IR')} \u0631\u06cc\u0627\u0644`;
  target.innerHTML = customers.length ? customers.map((customer) => {
    const title = customer.store_name || customer.name || `\u0645\u0634\u062a\u0631\u06cc ${customer.code || ''}`;
    const person = customer.store_name && customer.name ? `<small>${esc(customer.name)}</small>` : '';
    const code = customer.code ? `<span>\u06a9\u062f ${esc(customer.code)}</span>` : '';
    const contact = [customer.phone, customer.mobile].filter((value) => value && value !== '*').map(esc).join(' \u00b7 ');
    const latitude = Number(customer.latitude);
    const longitude = Number(customer.longitude);
    const hasCoordinates = Number.isFinite(latitude) && Number.isFinite(longitude) && latitude !== 0 && longitude !== 0;
    const coordinates = hasCoordinates ? `${latitude},${longitude}` : '';
    const addressDestination = customer.address ? encodeURIComponent([customer.address, title].filter(Boolean).join('، ')) : '';
    const destination = coordinates || addressDestination;
    const wazeDestination = coordinates ? `ll=${coordinates}` : `q=${addressDestination}`;
    const navigation = destination ? `<nav class="seller-navigation-links" aria-label="\u0645\u0633\u06cc\u0631\u06cc\u0627\u0628\u06cc \u0628\u0647 ${esc(title)}"><a class="seller-navigation-waze" href="https://www.waze.com/ul?${wazeDestination}&navigate=yes" target="_blank" rel="noopener">Waze</a><a href="https://maps.apple.com/?daddr=${destination}&dirflg=d" target="_blank" rel="noopener">Apple Maps</a><a href="https://www.google.com/maps/dir/?api=1&destination=${destination}&travelmode=driving" target="_blank" rel="noopener">Google Maps</a></nav>` : '';
    const locationStatus = hasCoordinates ? '<span class="seller-location-status" title="مسیریابی با مختصات ثبت‌شده انجام می‌شود">⌖ موقعیت مکانی ثبت شده</span>' : '';
    return `<article class="seller-customer-card"><header><div><strong>${esc(title)}</strong>${person}${locationStatus}</div>${code}</header><div class="seller-customer-balances"><span><small>\u0645\u0627\u0646\u062f\u0647 \u06a9\u0627\u0631\u062f\u06a9\u0633 \u0645\u0634\u062a\u0631\u06cc</small><b>${money(customer.cardex_balance)}</b></span><span><small>\u0645\u0627\u0646\u062f\u0647 \u0641\u0627\u06a9\u062a\u0648\u0631\u0647\u0627\u06cc \u0628\u0627\u0632 \u0645\u0646</small><b>${money(customer.open_invoice_remaining)}</b>${Number(customer.open_invoice_count || 0) ? `<em>${Number(customer.open_invoice_count).toLocaleString('fa-IR')} \u0641\u0627\u06a9\u062a\u0648\u0631</em>` : ''}</span></div>${contact ? `<p class="seller-customer-contact" dir="ltr">${contact}</p>` : ''}${customer.address ? `<p>${esc(customer.address)}</p>` : ''}${navigation}</article>`;
  }).join('') : '<p class="organization-empty">\u062f\u0631 \u062d\u0627\u0644 \u062d\u0627\u0636\u0631 \u0645\u0634\u062a\u0631\u06cc \u0641\u0639\u0627\u0644\u06cc \u0628\u0631\u0627\u06cc \u0627\u06cc\u0646 \u0645\u0633\u06cc\u0631 \u062b\u0628\u062a \u0646\u0634\u062f\u0647 \u0627\u0633\u062a.</p>';
}

function renderOpenInvoices(data) {
  const total = Number(data.open_invoice_remaining || 0).toLocaleString('fa-IR');
  $('#myOpenInvoicesSummary').textContent = `${Number(data.customer_count || 0).toLocaleString('fa-IR')} مشتری · ${total} ریال`;
  const money = (value) => `${Number(value || 0).toLocaleString('fa-IR')} ریال`;
  const date = (value) => {
    if (!value) return 'تاریخ نامشخص';
    const raw = String(value).trim();
    if (/^(13|14)\d{2}[/-]\d{1,2}[/-]\d{1,2}/.test(raw)) return esc(raw.replaceAll('-', '/'));
    const parsed = new Date(raw);
    return Number.isNaN(parsed.valueOf()) ? esc(raw) : parsed.toLocaleDateString('fa-IR');
  };
  const customers = data.customers || [];
  myOpenInvoicesList.innerHTML = customers.length ? customers.map((customer) => {
    const title = customer.store_name || customer.name || `مشتری ${customer.code || ''}`;
    const person = customer.store_name && customer.name ? `<small>${esc(customer.name)}</small>` : '';
    const code = customer.code ? `<span>کد ${esc(customer.code)}</span>` : '';
    const customerId = esc(customer.id);
    const returnedCheque = Number(customer.return_cheque_count || 0) ? `<em class="seller-returned-cheque">چک برگشتی: ${Number(customer.return_cheque_count).toLocaleString('fa-IR')} فقره · ${money(customer.return_cheque_amount)}</em>` : '';
    return `<article class="seller-open-invoice-customer"><button class="seller-open-invoice-summary" type="button" data-customer-open-invoices="${customerId}" aria-expanded="false"><span><strong>${esc(title)}</strong>${person}</span>${code}<span class="seller-open-invoice-meta"><b>${Number(customer.open_invoice_count || 0).toLocaleString('fa-IR')} فاکتور باز</b><small>قدیمی‌ترین: ${date(customer.oldest_open_invoice_date)}</small><em>مانده فاکتورهای باز: ${money(customer.open_invoice_remaining)}</em><em>مانده کاردکس مشتری: ${money(customer.cardex_balance)}</em>${returnedCheque}</span><span class="seller-route-chevron">⌄</span></button><div class="seller-open-invoice-list" data-customer-open-invoice-list="${customerId}" hidden></div></article>`;
  }).join('') : '<p class="organization-empty">در حال حاضر فاکتور بازی برای مشتری‌های مسیر فعال شما ثبت نشده است.</p>';
}

function renderCustomerOpenInvoices(target, data) {
  const invoices = data.invoices || [];
  const money = (value) => `${Number(value || 0).toLocaleString('fa-IR')} ریال`;
  const date = (value) => {
    if (!value) return 'تاریخ نامشخص';
    const raw = String(value).trim();
    if (/^(13|14)\d{2}[/-]\d{1,2}[/-]\d{1,2}/.test(raw)) return esc(raw.replaceAll('-', '/'));
    const parsed = new Date(raw);
    return Number.isNaN(parsed.valueOf()) ? esc(raw) : parsed.toLocaleDateString('fa-IR');
  };
  target.innerHTML = invoices.length ? invoices.map((invoice) => `<article class="seller-open-invoice-card"><header><strong>فاکتور ${esc(invoice.number || invoice.id)}</strong><time>${date(invoice.date)}</time></header><span>مبلغ فاکتور: ${money(invoice.amount)}</span><b>مانده: ${money(invoice.remaining_amount)}</b></article>`).join('') : '<p class="organization-empty">فاکتور باز فعالی برای این مشتری پیدا نشد.</p>';
}

function renderReturnedCheques(data) {
  const money = (value) => `${Number(value || 0).toLocaleString('fa-IR')} ریال`;
  const date = (value) => {
    if (!value) return 'تاریخ نامشخص';
    const raw = String(value).trim();
    if (/^(13|14)\d{2}[/-]\d{1,2}[/-]\d{1,2}/.test(raw)) return esc(raw.replaceAll('-', '/'));
    const parsed = new Date(raw);
    return Number.isNaN(parsed.valueOf()) ? esc(raw) : parsed.toLocaleDateString('fa-IR');
  };
  $('#myReturnedChequesSummary').textContent = `${Number(data.cheque_count || 0).toLocaleString('fa-IR')} فقره · سهم من ${money(data.seller_share)}`;
  const cheques = data.cheques || [];
  myReturnedChequesList.innerHTML = cheques.length ? cheques.map((cheque) => {
    const customer = cheque.customer_store || cheque.customer_name || `مشتری ${cheque.customer_code || ''}`;
    const bank = [cheque.bank, cheque.branch].filter(Boolean).map(esc).join(' · ');
    const contact = [cheque.customer_phone, cheque.customer_mobile].filter((value) => value && value !== '*').map((value) => {
      const display = String(value).trim();
      const dial = display.replace(/[^\d+]/g, '');
      return dial ? `<a class="seller-call-link" href="tel:${esc(dial)}">${esc(display)}</a>` : esc(display);
    }).join(' · ');
    return `<article class="seller-open-invoice-card seller-returned-cheque-card"><header><strong>چک ${esc(cheque.number || cheque.id)}</strong><time>${date(cheque.date)}</time></header><span><b>${esc(customer)}</b>${cheque.customer_name && cheque.customer_store ? ` · ${esc(cheque.customer_name)}` : ''}</span>${cheque.account_name ? `<span>صاحب حساب: ${esc(cheque.account_name)}</span>` : ''}${bank ? `<span>${bank}</span>` : ''}${contact ? `<span dir="ltr">${contact}</span>` : ''}<span>مبلغ کل چک: ${money(cheque.amount)}</span><b>سهم من: ${money(cheque.seller_share)}</b><em>تسویه‌شده: ${money(cheque.settled_amount)}</em></article>`;
  }).join('') : '<p class="organization-empty">چک برگشتی مرتبطی برای شما ثبت نشده است.</p>';
}

function renderVoucherReturnReport(data) {
  $('#myVoucherReturnReportPeriod').textContent = data.report_month ? `ماه ${data.report_month}` : 'ماه جاری';
  const issued = Number(data.voucher_count || 0);
  const invoiced = Number(data.invoiced_count || 0);
  const fullReturned = Number(data.full_returned_count ?? data.returned_count ?? 0);
  const undistributed = Number(data.undistributed_count || 0);
  myVoucherReturnReportList.innerHTML = `<article class="seller-open-invoice-card"><header><strong>عملکرد حواله</strong><time>${data.report_month ? `ماه ${esc(data.report_month)}` : 'ماه جاری'}</time></header><span>حواله صادرشده: ${issued.toLocaleString('fa-IR')} فقره</span><span>فاکتور‌شده: ${invoiced.toLocaleString('fa-IR')} فقره</span><span>برگشت کامل حواله: ${fullReturned.toLocaleString('fa-IR')} فقره</span><span>توزیع‌نشده / بدون شماره فاکتور: ${undistributed.toLocaleString('fa-IR')} فقره</span><b>کنترل تعداد: ${invoiced.toLocaleString('fa-IR')} + ${fullReturned.toLocaleString('fa-IR')} + ${undistributed.toLocaleString('fa-IR')} = ${issued.toLocaleString('fa-IR')}</b><em>درصد برگشت کامل: ${Number(data.return_percentage || 0).toLocaleString('fa-IR')}٪</em></article>`;
}

function renderDistributionInProgress(data) {
  const money = (value) => `${Number(value || 0).toLocaleString('fa-IR')} \u0631\u06cc\u0627\u0644`;
  const date = (value) => {
    const raw = String(value || '').trim();
    if (!raw) return '\u2014';
    if (/^(13|14)\d{2}[/-]\d{1,2}[/-]\d{1,2}/.test(raw)) return esc(raw.replaceAll('-', '/'));
    const parsed = new Date(raw);
    return Number.isNaN(parsed.valueOf()) ? esc(raw) : parsed.toLocaleDateString('fa-IR');
  };
  const invoices = data.invoices || [];
  const distributionDates = (data.distribution_dates || []).filter(Boolean);
  const dateSummary = distributionDates.length ? distributionDates.join('، ') : data.distribution_date;
  $('#myDistributionInProgressSummary').textContent = `${Number(data.invoice_count || 0).toLocaleString('fa-IR')} \u0641\u0642\u0631\u0647${dateSummary ? ` \u00b7 ${dateSummary}` : ''}`;
  $('#myDistributionInProgressList').innerHTML = invoices.length ? invoices.map((invoice) => {
    const customer = invoice.customer_store || invoice.customer_name || `\u0645\u0634\u062a\u0631\u06cc ${invoice.customer_code || ''}`;
    const mobile = String(invoice.driver_mobile || '').trim();
    const dial = mobile.replace(/[^\d+]/g, '');
    const driver = invoice.driver_name || '\u0631\u0627\u0646\u0646\u062f\u0647 \u0646\u0627\u0645\u0634\u062e\u0635';
    const contact = dial ? `<a class="seller-call-link" href="tel:${esc(dial)}">${esc(mobile)}</a>` : (mobile ? esc(mobile) : '—');
    return `<article class="seller-open-invoice-card"><header><strong>\u0641\u0627\u06a9\u062a\u0648\u0631 ${esc(invoice.number)}</strong><time>\u062a\u0648\u0632\u06cc\u0639: ${date(invoice.distribution_date)}</time></header><span><b>${esc(customer)}</b>${invoice.customer_name && invoice.customer_store ? ` \u00b7 ${esc(invoice.customer_name)}` : ''}</span><span>\u0634\u0645\u0627\u0631\u0647 \u062a\u0648\u0632\u06cc\u0639: ${esc(invoice.distribution_number || '—')}</span><span>\u0631\u0627\u0646\u0646\u062f\u0647: ${esc(driver)} \u00b7 <span dir="ltr">${contact}</span></span><b>\u0645\u0628\u0644\u063a: ${money(invoice.amount)}</b></article>`;
  }).join('') : '<p class="organization-empty">\u0641\u0627\u06a9\u062a\u0648\u0631 \u062f\u0631 \u062c\u0631\u06cc\u0627\u0646 \u062a\u0648\u0632\u06cc\u0639 \u06cc\u0627 \u0628\u0631\u0646\u0627\u0645\u0647\u200c\u0631\u06cc\u0632\u06cc\u200c\u0634\u062f\u0647 \u0628\u0631\u0627\u06cc \u0627\u0645\u0631\u0648\u0632 \u0648 \u0641\u0631\u062f\u0627 \u067e\u06cc\u062f\u0627 \u0646\u0634\u062f.</p>';
}

async function toggleCustomerOpenInvoices(button) {
  const customerId = button.dataset.customerOpenInvoices;
  const target = myOpenInvoicesList.querySelector(`[data-customer-open-invoice-list="${CSS.escape(customerId)}"]`);
  const opening = target.hidden;
  target.hidden = !opening;
  button.setAttribute('aria-expanded', String(opening));
  if (!opening || target.dataset.loaded === 'true') return;
  target.innerHTML = '<p class="organization-empty">در حال دریافت فاکتورهای باز…</p>';
  try {
    const response = await fetch(`/seller-workspace/open-invoices/${encodeURIComponent(customerId)}`);
    if (response.status === 401) return showLogin();
    if (!response.ok) throw Error('فاکتورهای باز این مشتری دریافت نشد.');
    renderCustomerOpenInvoices(target, await response.json());
    target.dataset.loaded = 'true';
  } catch (error) {
    target.hidden = true;
    button.setAttribute('aria-expanded', 'false');
    toast(error.message);
  }
}

async function toggleRouteCustomers(button) {
  const routeId = button.dataset.routeCustomers;
  const target = myRoutesList.querySelector(`[data-route-customer-list="${CSS.escape(routeId)}"]`);
  const opening = target.hidden;
  target.hidden = !opening;
  button.setAttribute('aria-expanded', String(opening));
  if (!opening || target.dataset.loaded === 'true') return;
  target.innerHTML = '<p class="organization-empty">در حال دریافت مشتری‌ها…</p>';
  try {
    const response = await fetch(`/seller-workspace/routes/${encodeURIComponent(routeId)}/customers`);
    if (response.status === 401) return showLogin();
    if (!response.ok) throw Error('\u0644\u06cc\u0633\u062a \u0645\u0634\u062a\u0631\u06cc\u200c\u0647\u0627\u06cc \u0627\u06cc\u0646 \u0645\u0633\u06cc\u0631 \u062f\u0631\u06cc\u0627\u0641\u062a \u0646\u0634\u062f.');
    renderRouteCustomers(target, await response.json());
    target.dataset.loaded = 'true';
  } catch (error) {
    target.hidden = true;
    button.setAttribute('aria-expanded', 'false');
    toast(error.message);
  }
}

async function openSellerWorkspace(focus = 'routes', {dayRouteSelection = false} = {}) {
  rememberAppView('seller-workspace', {focus, dayRouteSelection});
  try {
    sellerWorkspacePanel.hidden = false;
    sellerWorkspacePanel.dataset.focus = focus;
    sellerWorkspacePanel.dataset.dayRouteSelection = String(dayRouteSelection);
    $('#sellerWorkspaceTitle').textContent = dayRouteSelection ? 'تورهای ویزیت' : 'مسیرها و برندهای من';
    notificationsPanel.hidden = true;
    schemaCatalogPanel.hidden = true;
    organizationStructurePanel.hidden = true;
    const sections = {
      routes: 'myRoutesSection', brands: 'myBrandsSection', openInvoices: 'myOpenInvoicesSection',
      distributionInProgress: 'myDistributionInProgressSection', returnedCheques: 'myReturnedChequesSection',
      voucherReport: 'myVoucherReturnReportSection',
    };
    Object.values(sections).forEach((id) => { $(`#${id}`).hidden = id !== sections[focus]; });
    const targets = {
      routes: { url: '/seller-workspace/routes', loading: ['#myRoutesList', '\u062f\u0631 \u062d\u0627\u0644 \u062f\u0631\u06cc\u0627\u0641\u062a \u0645\u0633\u06cc\u0631\u0647\u0627\u2026'], render: (data) => renderSellerWorkspace(data, {}) },
      brands: { url: '/seller-workspace/brands', loading: ['#myBrandsList', '\u062f\u0631 \u062d\u0627\u0644 \u062f\u0631\u06cc\u0627\u0641\u062a \u0633\u0628\u062f \u0628\u0631\u0646\u062f\u2026'], render: (data) => renderSellerWorkspace({}, data) },
      openInvoices: { url: '/seller-workspace/open-invoices', loading: ['#myOpenInvoicesList', '\u062f\u0631 \u062d\u0627\u0644 \u062f\u0631\u06cc\u0627\u0641\u062a \u0641\u0627\u06a9\u062a\u0648\u0631\u0647\u0627\u06cc \u0628\u0627\u0632\u2026'], render: renderOpenInvoices },
      distributionInProgress: { url: '/seller-workspace/distribution-in-progress', loading: ['#myDistributionInProgressList', '\u062f\u0631 \u062d\u0627\u0644 \u062f\u0631\u06cc\u0627\u0641\u062a \u0641\u0627\u06a9\u062a\u0648\u0631\u0647\u0627\u06cc \u062f\u0631 \u062c\u0631\u06cc\u0627\u0646 \u062a\u0648\u0632\u06cc\u0639\u2026'], render: renderDistributionInProgress },
      returnedCheques: { url: '/seller-workspace/returned-cheques', loading: ['#myReturnedChequesList', '\u062f\u0631 \u062d\u0627\u0644 \u062f\u0631\u06cc\u0627\u0641\u062a \u0686\u06a9\u200c\u0647\u0627\u06cc \u0628\u0631\u06af\u0634\u062a\u06cc\u2026'], render: renderReturnedCheques },
      voucherReport: { url: '/seller-workspace/voucher-return-report', loading: ['#myVoucherReturnReportList', '\u062f\u0631 \u062d\u0627\u0644 \u062f\u0631\u06cc\u0627\u0641\u062a \u06af\u0632\u0627\u0631\u0634 \u062d\u0648\u0627\u0644\u0647\u2026'], render: renderVoucherReturnReport },
    };
    const target = targets[focus] || targets.routes;
    const [loadingSelector, loadingText] = target.loading;
    $(loadingSelector).innerHTML = `<p class="organization-empty">${loadingText}</p>`;
    const response = await fetch(target.url);
    if (response.status === 401) return showLogin();
    if (!response.ok) throw Error('\u062f\u0631\u06cc\u0627\u0641\u062a \u0627\u0637\u0644\u0627\u0639\u0627\u062a \u0641\u0631\u0648\u0634\u0646\u062f\u0647 \u0627\u0646\u062c\u0627\u0645 \u0646\u0634\u062f.');
    target.render(await response.json());
    closeSidebar();
    requestAnimationFrame(() => $(`#${sections[focus] || sections.routes}`).scrollIntoView({behavior: 'smooth', block: 'start'}));
    return;
    myRoutesList.innerHTML = '<p class="organization-empty">در حال دریافت مسیرها…</p>';
    myBrandsList.innerHTML = '<p class="organization-empty">\u062f\u0631 \u062d\u0627\u0644 \u062f\u0631\u06cc\u0627\u0641\u062a \u0633\u0628\u062f \u0628\u0631\u0646\u062f\u2026</p>';
    const openInvoicesResponse = focus === 'openInvoices'
      ? fetch('/seller-workspace/open-invoices')
      : null;
    const returnedChequesResponse = focus === 'returnedCheques'
      ? fetch('/seller-workspace/returned-cheques')
      : null;
    const distributionInProgressResponse = focus === 'distributionInProgress'
      ? fetch('/seller-workspace/distribution-in-progress')
      : null;
    const voucherReportResponse = focus === 'voucherReport'
      ? fetch('/seller-workspace/voucher-return-report')
      : null;
    if (openInvoicesResponse) myOpenInvoicesList.innerHTML = '<p class="organization-empty">\u062f\u0631 \u062d\u0627\u0644 \u062f\u0631\u06cc\u0627\u0641\u062a \u0641\u0627\u06a9\u062a\u0648\u0631\u0647\u0627\u06cc \u0628\u0627\u0632\u2026</p>';
    if (returnedChequesResponse) myReturnedChequesList.innerHTML = '<p class="organization-empty">در حال دریافت چک‌های برگشتی…</p>';
    if (voucherReportResponse) myVoucherReturnReportList.innerHTML = '<p class="organization-empty">در حال دریافت گزارش حواله…</p>';
    const [routesResponse, brandsResponse, invoiceResponse, chequeResponse, voucherResponse] = await Promise.all([
      fetch('/seller-workspace/routes'), fetch('/seller-workspace/brands'),
      openInvoicesResponse, returnedChequesResponse, voucherReportResponse,
    ]);
    if (routesResponse.status === 401) return showLogin();
    if (!routesResponse.ok || !brandsResponse.ok || (invoiceResponse && !invoiceResponse.ok) || (chequeResponse && !chequeResponse.ok) || (voucherResponse && !voucherResponse.ok)) throw Error('\u062f\u0631\u06cc\u0627\u0641\u062a \u0627\u0637\u0644\u0627\u0639\u0627\u062a \u0641\u0631\u0648\u0634\u0646\u062f\u0647 \u0627\u0646\u062c\u0627\u0645 \u0646\u0634\u062f.');
    renderSellerWorkspace(await routesResponse.json(), await brandsResponse.json());
    if (invoiceResponse) renderOpenInvoices(await invoiceResponse.json());
    if (chequeResponse) renderReturnedCheques(await chequeResponse.json());
    if (voucherResponse) renderVoucherReturnReport(await voucherResponse.json());
    closeSidebar();
    requestAnimationFrame(() => $(`#my${focus === 'brands' ? 'Brands' : focus === 'openInvoices' ? 'OpenInvoices' : focus === 'returnedCheques' ? 'ReturnedCheques' : focus === 'voucherReport' ? 'VoucherReturnReport' : 'Routes'}Section`).scrollIntoView({behavior: 'smooth', block: 'start'}));
  } catch (error) {
    sellerWorkspacePanel.hidden = true;
    closeCurrentAppView('seller-workspace');
    toast(error.message);
  }
}

function schemaCatalogText(item) {
  const catalog = item.catalog || {};
  return [item.schema, item.name, catalog.persian_name, catalog.description, catalog.domain, ...(catalog.aliases || [])]
    .join(' ').toLocaleLowerCase('fa');
}

function renderSchemaCatalog() {
  const query = $('#schemaCatalogSearch').value.trim().toLocaleLowerCase('fa');
  const visible = schemaCatalogCache.filter((item) => !query || schemaCatalogText(item).includes(query));
  const groups = new Map();
  visible.forEach((item) => {
    const domain = item.catalog?.domain || 'سایر منابع';
    if (!groups.has(domain)) groups.set(domain, []);
    groups.get(domain).push(item);
  });
  $('#schemaCatalogCount').textContent = `${visible.length.toLocaleString('fa-IR')} جدول`;
  schemaCatalogGroups.innerHTML = groups.size ? [...groups.entries()].map(([domain, items]) => `
    <section class="schema-domain"><header><h3>${esc(domain)}</h3><span>${items.length.toLocaleString('fa-IR')}</span></header>
      <div class="schema-table-list">${items.map((item) => {
        const catalog = item.catalog || {};
        return `<button class="schema-table-card" type="button" data-schema-object="${esc(item.schema)}" data-schema-name="${esc(item.name)}">
          <span class="schema-table-icon">${item.type === 'VIEW' ? '◫' : '▦'}</span><span class="schema-table-copy"><strong>${esc(catalog.persian_name || item.name)}</strong><small dir="ltr">${esc(item.schema)}.${esc(item.name)}</small></span><span class="schema-table-meta">${item.column_count.toLocaleString('fa-IR')} ستون</span>
        </button>`;
      }).join('')}</div>
    </section>`).join('') : '<div class="schema-catalog-empty">جدولی با این عبارت پیدا نشد.</div>';
}

function closeSchemaCatalog() {
  closeCurrentAppView(appHistoryState()?.view === 'schema-detail' ? 'schema-detail' : 'schema-catalog', () => {
    schemaCatalogPanel.hidden = true;
    schemaDetailPanel.hidden = true;
  });
}

async function openSchemaCatalog() {
  rememberAppView('schema-catalog');
  try {
    $('#schemaCatalogHint').textContent = 'در حال دریافت ساختار داده…';
    schemaCatalogPanel.hidden = false;
    notificationsPanel.hidden = true;
    schemaDetailPanel.hidden = true;
    const response = await fetch('/chat/schema-catalog');
    if (response.status === 401) return showLogin();
    if (!response.ok) throw Error('دریافت فهرست جداول انجام نشد.');
    const data = await response.json();
    schemaCatalogCache = data.items || [];
    $('#schemaCatalogHint').textContent = 'منابع بر اساس حوزهٔ کسب‌وکار دسته‌بندی شده‌اند.';
    renderSchemaCatalog();
    closeSidebar();
  } catch (error) {
    schemaCatalogPanel.hidden = true;
    schemaDetailPanel.hidden = true;
    closeCurrentAppView('schema-catalog');
    toast(error.message);
  }
}

async function showSchemaDetail(schema, name) {
  rememberAppView('schema-detail', {schema, name});
  try {
    schemaDetailPanel.hidden = false;
    schemaDetailPanel.innerHTML = '<div class="schema-detail-loading">در حال دریافت ستون‌ها…</div>';
    const response = await fetch(`/chat/schema-catalog/object?schema=${encodeURIComponent(schema)}&name=${encodeURIComponent(name)}`);
    if (!response.ok) throw Error('جزئیات جدول در دسترس نیست.');
    const item = await response.json();
    const catalog = item.catalog || {};
    const columns = item.columns || [];
    schemaDetailPanel.innerHTML = `<header><button type="button" data-close-schema-detail aria-label="بستن">×</button><div><strong>${esc(catalog.persian_name || item.name)}</strong><small dir="ltr">${esc(item.schema)}.${esc(item.name)}</small></div></header>
      <p>${esc(catalog.description || 'برای این جدول توضیحی ثبت نشده است.')}</p>
      <div class="schema-detail-tags"><span>${esc(item.type)}</span><span>${columns.length.toLocaleString('fa-IR')} ستون</span>${(catalog.aliases || []).slice(0, 4).map((alias) => `<span>${esc(alias)}</span>`).join('')}</div>
      <h3>ستون‌ها</h3><div class="schema-columns">${columns.map((column) => `<div><strong>${esc(column.persian_name || column.name)}</strong><small dir="ltr">${esc(column.name)} · ${esc(column.data_type || '')}</small>${column.primary_key ? '<b>کلید اصلی</b>' : ''}</div>`).join('')}</div>`;
  } catch (error) {
    schemaDetailPanel.innerHTML = `<div class="schema-detail-loading">${esc(error.message)}</div>`;
  }
}

function addPrevisitLine(line = {}) {
  const row = document.createElement('div');
  row.className = 'previsit-line';
  row.innerHTML = `<label>کد کالا<input data-field="product_id" required value="${esc(line.product_id || '')}"></label><label>نام کالا<input data-field="title" value="${esc(line.title || '')}"></label><label>تعداد<input data-field="quantity" type="number" min="0.001" step="any" required value="${esc(line.quantity || 1)}"></label><label>قیمت واحد<input data-field="unit_price" type="number" min="0" step="any" required value="${esc(line.unit_price || 0)}"></label><label>تخفیف<input data-field="discount_amount" type="number" min="0" step="any" value="${esc(line.discount_amount || 0)}"></label><button type="button" aria-label="حذف ردیف">×</button>`;
  row.querySelector('button').addEventListener('click', () => row.remove());
  $('#previsitLines').append(row);
}

async function openPrevisit(options = {}) {
  previsitPanel.hidden = false;
  $('#previsitForm').classList.remove('is-visit-active');
  $('#previsitCart').hidden = true;
  previsitSession = null;
  stopPrevisitVisitTimer();
  previsitWorkspace = null;
  previsitPolicy = null;
  $('#previsitPolicySummary').hidden = true;
  const routeSelect = $('#previsitRoute');
  routeSelect.innerHTML = '<option value="">در حال دریافت مسیرها…</option>';
  try {
    const response = await fetch('/seller-workspace/routes');
    if (!response.ok) throw Error('دریافت مسیرها انجام نشد.');
    const data = await response.json();
    const dayRoutes = (data.routes || []).filter((route) => route.can_start_visit);
    routeSelect.innerHTML = dayRoutes.length
      ? '<option value="">انتخاب مسیر روز</option>' + dayRoutes.map((route) => `<option value="${esc(route.id)}">${esc(route.title)}</option>`).join('')
      : '<option value="">برای امروز مسیر روز فعالی تعیین نشده</option>';
    routeSelect.disabled = !dayRoutes.length;
  } catch (error) { toast(error.message); }
}

async function loadPrevisitCustomers() {
  const routeId = $('#previsitRoute').value;
  const customerSelect = $('#previsitCustomer');
  customerSelect.disabled = true;
  previsitPolicy = null;
  $('#previsitPolicySummary').hidden = true;
  customerSelect.innerHTML = '<option value="">در حال دریافت مشتری‌ها…</option>';
  if (!routeId) { customerSelect.innerHTML = '<option value="">ابتدا مسیر را انتخاب کنید</option>'; return; }
  try {
    const response = await fetch(`/seller-workspace/routes/${encodeURIComponent(routeId)}/customers`);
    if (!response.ok) throw Error('دریافت مشتری‌ها انجام نشد.');
    const data = await response.json();
    customerSelect.innerHTML = '<option value="">انتخاب مشتری</option>' + (data.customers || []).map((customer) => `<option value="${esc(customer.id)}">${esc(customer.store_name || customer.name)} · ${esc(customer.code || '')}</option>`).join('');
    customerSelect.disabled = false;
  } catch (error) { customerSelect.innerHTML = '<option value="">خطا در دریافت مشتری‌ها</option>'; toast(error.message); }
}

function renderPrevisitPolicy() {
  const panel = $('#previsitPolicySummary');
  if (!previsitPolicy) { panel.hidden = true; return; }
  const controls = previsitPolicy.controls || {};
  const blockers = previsitPolicy.start_blockers || [];
  const chips = [];
  const distanceSuspended = Boolean(controls.enabled && !controls.enforced);
  if (controls.enforced) chips.push(`کنترل فاصله ${Number(controls.max_distance_meters || 0).toLocaleString('fa-IR')} متر`);
  else if (distanceSuspended) chips.push('کنترل فاصله موقتاً غیرفعال');
  if (controls.gps_enabled) chips.push('GPS اجباری');
  if (controls.mandatory_customer_visit) chips.push('تعیین تکلیف مشتری اجباری');
  if (controls.set_customer_location) chips.push('ثبت موقعیت مشتری مجاز');
  if (controls.allow_edit_customer) chips.push('ویرایش مشتری مجاز');
  panel.classList.toggle('is-blocked', blockers.length > 0);
  const readyMessage = distanceSuspended
    ? 'مشتری آماده شروع ویزیت است؛ کنترل فاصله در این مرحله برای تست موقتاً غیرفعال است.'
    : 'مشتری آماده شروع ویزیت است.';
  panel.innerHTML = `<strong>${blockers.length ? 'پیش از شروع ویزیت' : 'کنترل‌های ویزیت'}</strong><div class="previsit-policy-chips">${chips.map((item) => `<span>${esc(item)}</span>`).join('')}</div><p>${blockers.length ? blockers.map(esc).join(' · ') : readyMessage}</p>`;
  panel.hidden = false;
  $('#startPrevisit').disabled = blockers.length > 0;
}

async function loadPrevisitPolicy(routeId = $('#previsitRoute').value, customerId = $('#previsitCustomer').value) {
  previsitPolicy = null;
  if (!routeId || !customerId) { renderPrevisitPolicy(); return null; }
  const query = new URLSearchParams({path_id: routeId, customer_id: customerId});
  const response = await fetch(`/seller-workspace/previsit/policy?${query}`);
  const data = await readJsonResponse(response, 'کنترل‌های ویزیت دریافت نشد.');
  if (!response.ok) throw Error(data.detail || 'کنترل‌های ویزیت دریافت نشد.');
  previsitPolicy = data;
  renderPrevisitPolicy();
  return data;
}

function previsitLines() {
  return $$('.previsit-line', $('#previsitLines')).map((row) => ({
    product_id: row.querySelector('[data-field="product_id"]').value.trim(),
    title: row.querySelector('[data-field="title"]').value.trim(),
    quantity: Number(row.querySelector('[data-field="quantity"]').value),
    unit_price: Number(row.querySelector('[data-field="unit_price"]').value),
    discount_amount: Number(row.querySelector('[data-field="discount_amount"]').value || 0),
  })).filter((line) => line.product_id && line.quantity > 0 && line.unit_price >= 0);
}

async function savePrevisitDraft() {
  if (!previsitSession) throw Error('ابتدا ویزیت را شروع کنید.');
  const response = await fetch(`/seller-workspace/previsit/visits/${encodeURIComponent(previsitSession.visit_id)}/draft`, {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({lines: previsitLines(), payment_type: $('#previsitPaymentType').value, order_type: $('#previsitOrderType').value})});
  const data = await response.json();
  if (!response.ok) throw Error(data.detail || 'ذخیره پیش‌نویس انجام نشد.');
  previsitSession = data;
  toast(`پیش‌نویس ذخیره شد · ${data.line_count} ردیف`);
}

async function completePrevisit(outcome, reasonId = null) {
  await savePrevisitDraft();
  const response = await fetch(`/seller-workspace/previsit/visits/${encodeURIComponent(previsitSession.visit_id)}/complete`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({outcome, reason: ''})});
  const data = await response.json();
  if (!response.ok) throw Error(data.detail || 'پایان ویزیت انجام نشد.');
  previsitSession = null;
  $('#previsitCart').hidden = true;
  toast(outcome === 'order' ? 'ویزیت ذخیره شد؛ ثبت نهایی هنوز غیرفعال است.' : 'ویزیت بدون سفارش ثبت شد.');
}

// Official pre-visit UI. This replaces the early manual-price prototype
// while preserving its local draft/visit lifecycle.
function prepareNgtPrevisitUi() {
  const cart = $('#previsitCart');
  if (cart.dataset.ngtUi === '1') return;
  cart.dataset.ngtUi = '1';
  cart.innerHTML = `
    <header><div><h3>سبد سفارش</h3></div><span id="previsitContextStatus" class="previsit-status"></span></header>
    <div class="previsit-context-grid">
      <label>&#1606;&#1608;&#1593; &#1587;&#1601;&#1575;&#1585;&#1588;<select id="previsitOrderType"></select></label>
      <label>&#1585;&#1608;&#1588; &#1662;&#1585;&#1583;&#1575;&#1582;&#1578;<select id="previsitPaymentType"></select></label>
    </div>
    <section class="previsit-product-picker">
      <label>&#1580;&#1587;&#1578;&#8204;&#1608;&#1580;&#1608;&#1740; &#1705;&#1575;&#1604;&#1575;<input id="previsitProductSearch" type="search" placeholder="&#1606;&#1575;&#1605;&#1548; &#1705;&#1583; &#1740;&#1575; &#1576;&#1585;&#1606;&#1583;"></label>
      <label>کالا<select id="previsitProductPicker"><option value="">ابتدا اطلاعات کالا دریافت شود</option></select></label>
      <label>&#1578;&#1593;&#1583;&#1575;&#1583;<input id="previsitNewQuantity" type="number" min="0.001" step="any" value="1"></label>
      <button id="addPrevisitLine" type="button">+ &#1575;&#1601;&#1586;&#1608;&#1583;&#1606; &#1576;&#1607; &#1587;&#1576;&#1583;</button>
    </section>
    <div class="previsit-invoice-scroll">
      <div class="previsit-invoice-head" aria-hidden="true">
        <span>کالا</span><span>تعداد</span><span>قیمت واحد</span><span>ناخالص</span>
        <span>کالایی<br><small>درصد / مبلغ</small></span>
        <span>حجمی<br><small>درصد / مبلغ</small></span>
        <span>نقدی<br><small>درصد / مبلغ</small></span>
        <span>مالیات و عوارض</span><span>خالص</span><span></span>
      </div>
      <div id="previsitLines" class="previsit-lines"></div>
    </div>
    <button id="previewPrevisit" type="button" class="previsit-preview-button">محاسبه قیمت، تخفیف و جوایز</button>
    <section id="previsitPreviewResult" class="previsit-preview-result" hidden aria-live="polite"></section>
    <button id="savePrevisitDraft" type="button">&#1584;&#1582;&#1740;&#1585;&#1607; &#1662;&#1740;&#1588;&#8204;&#1606;&#1608;&#1740;&#1587;</button>
    <button id="completePrevisitOrder" type="button" disabled>&#1662;&#1575;&#1740;&#1575;&#1606; &#1608;&#1740;&#1586;&#1740;&#1578; &#1608; &#1579;&#1576;&#1578; &#1662;&#1740;&#1588;&#8204;&#1606;&#1608;&#1740;&#1587;</button>`;
  $('#previsitProductSearch').addEventListener('input', renderPrevisitProductOptions);
  $('#addPrevisitLine').addEventListener('click', () => addPrevisitLine());
  $('#previewPrevisit').addEventListener('click', () => void previewNgtPrevisit().catch((error) => toast(error.message)));
  $('#savePrevisitDraft').addEventListener('click', () => void savePrevisitDraft().catch((error) => toast(error.message)));
  $('#completePrevisitOrder').addEventListener('click', () => void completePrevisit('order').catch((error) => toast(error.message)));
}

function renderPrevisitProductOptions() {
  const picker = $('#previsitProductPicker');
  if (!picker || !previsitContext) return;
  const needle = ($('#previsitProductSearch').value || '').trim().toLocaleLowerCase('fa');
  const products = (previsitContext.products || []).filter((product) => {
    const haystack = `${product.id} ${product.code} ${product.name} ${product.brand}`.toLocaleLowerCase('fa');
    return !needle || haystack.includes(needle);
  }).slice(0, 150);
  picker.innerHTML = '<option value="">&#1575;&#1606;&#1578;&#1582;&#1575;&#1576; &#1705;&#1575;&#1604;&#1575;</option>' + products.map((product) =>
    `<option value="${esc(product.id)}">${esc(product.name)} &#183; ${esc(product.code)} &#183; &#1605;&#1608;&#1580;&#1608;&#1583;&#1740; ${Number(product.available_qty).toLocaleString('fa-IR')}</option>`
  ).join('');
}

function fillPrevisitContextSelectors() {
  const order = $('#previsitOrderType');
  const payment = $('#previsitPaymentType');
  const warehouse = $('#previsitWarehouse');
  order.innerHTML = (previsitContext.order_types || []).map((item) => `<option value="${esc(item.id)}">${esc(item.name)}</option>`).join('');
  payment.innerHTML = (previsitContext.payment_types || []).map((item) => `<option value="${esc(item.id)}">${esc(item.name)}</option>`).join('');
  warehouse.innerHTML = (previsitContext.warehouses || []).map((item) => `<option value="${esc(item.ref)}">${esc(item.name || `انبار ${item.ref}`)}</option>`).join('');
  const defaultWarehouseRef = String(previsitContext.warehouse_selection?.default_ref || '');
  if (defaultWarehouseRef) warehouse.value = defaultWarehouseRef;
  warehouse.disabled = !previsitContext.warehouse_selection?.enabled;
  warehouse.title = warehouse.disabled ? 'انبار برای این بازاریاب ثابت است.' : 'انبارهای مجاز دریافت شده‌اند.';
  $('#previsitContextStatus').textContent = `${Number(previsitContext.catalog_count || 0).toLocaleString('fa-IR')} &#1705;&#1575;&#1604;&#1575;`;
  $('#previsitContextStatus').innerHTML = `${Number(previsitContext.catalog_count || 0).toLocaleString('fa-IR')} &#1705;&#1575;&#1604;&#1575; &#183; &#1605;&#1608;&#1580;&#1608;&#1583;&#1740; ${previsitContext.inventory?.online_refresh ? '&#1570;&#1606;&#1604;&#1575;&#1740;&#1606;' : '&#1604;&#1581;&#1592;&#1607;&#8204;&#1575;&#1740;'}`;
  renderPrevisitProductOptions();
}

async function loadPrevisitContext(routeId = $('#previsitRoute').value, customerId = $('#previsitCustomer').value) {
  prepareNgtPrevisitUi();
  previsitContext = null;
  previsitPreview = null;
  $('#previsitContextStatus').textContent = 'در حال دریافت…';
  const query = new URLSearchParams({path_id: routeId, customer_id: customerId, limit: '1000'});
  const response = await fetch(`/seller-workspace/previsit/context?${query}`);
  const data = await readJsonResponse(response, 'دریافت کاتالوگ انجام نشد.');
  if (!response.ok) throw Error(data.detail || 'دریافت کاتالوگ انجام نشد.');
  previsitContext = data;
  fillPrevisitContextSelectors();
  return data;
}

function productForPrevisit(productId) {
  const product = (previsitContext?.products || []).find((item) => String(item.id) === String(productId));
  return product ? previsitProductAtSelectedConditions(product) : product;
}

function previsitSaleUnits(product) {
  const units = [];
  const seen = new Set();
  const append = (unit) => {
    const factor = Number(unit?.factor || 0);
    if (!(factor > 0)) return;
    const name = String(unit?.name || (factor === 1 ? product?.unit || 'عدد' : 'واحد فروش')).trim();
    const ref = unit?.ref ?? null;
    const identity = `${ref ?? ''}|${name}|${factor}`;
    if (seen.has(identity)) return;
    seen.add(identity);
    units.push({ref, name, factor, is_default: Boolean(unit?.is_default)});
  };
  (Array.isArray(product?.sale_units) ? product.sale_units : []).forEach(append);
  if (!units.some((unit) => unit.factor === 1)) append({name: product?.unit || 'عدد', factor: 1});
  const cartonFactor = Number(product?.carton_size || 0);
  if (cartonFactor > 1 && !units.some((unit) => unit.factor === cartonFactor)) append({name: 'کارتن', factor: cartonFactor});
  return units.sort((a, b) => a.factor - b.factor || a.name.localeCompare(b.name, 'fa'));
}

function previsitInvoiceUnitBreakdown(product, baseQuantity) {
  const quantity = Math.max(0, Number(baseQuantity || 0));
  const largestUnit = previsitSaleUnits(product)
    .filter((unit) => Number(unit.factor) > 1)
    .sort((a, b) => Number(b.factor) - Number(a.factor))[0];
  const unitsPerCarton = Number(largestUnit?.factor || 0);
  if (!(unitsPerCarton > 1)) {
    return {cartonQuantity: 0, remainderQuantity: quantity, unitsPerCarton: 0};
  }
  const cartonQuantity = Math.floor(quantity / unitsPerCarton);
  const remainderQuantity = Math.round((quantity - cartonQuantity * unitsPerCarton) * 1000) / 1000;
  return {cartonQuantity, remainderQuantity, unitsPerCarton};
}

function previsitInvoiceBaseQuantity(cartonQuantity, remainderQuantity, unitsPerCarton) {
  const cartons = Math.max(0, Math.trunc(Number(cartonQuantity || 0)));
  const remainder = Math.max(0, Math.trunc(Number(remainderQuantity || 0)));
  const factor = Math.max(0, Number(unitsPerCarton || 0));
  return cartons * factor + remainder;
}

function syncPrevisitInvoiceUnitBreakdown(row, product, baseQuantity) {
  const breakdown = previsitInvoiceUnitBreakdown(product, baseQuantity);
  const values = {
    carton_quantity: breakdown.cartonQuantity,
    remainder_quantity: breakdown.remainderQuantity,
    units_per_carton: breakdown.unitsPerCarton || '—',
  };
  Object.entries(values).forEach(([field, value]) => {
    const output = row?.querySelector(`[data-field="${field}"]`);
    if (!output) return;
    if (output.matches('input')) output.value = typeof value === 'number' ? String(value) : '';
    else output.textContent = typeof value === 'number' ? formatPrevisitUnitQuantity(value) : value;
  });
  const available = previsitAvailableBaseQuantity(product);
  row?.querySelectorAll('[data-previsit-invoice-unit-input="carton"],[data-previsit-invoice-unit-step="carton"]').forEach((control) => {
    const isIncrease = control.matches('[data-previsit-invoice-unit-step][data-delta="1"]');
    control.disabled = !(breakdown.unitsPerCarton > 1)
      || (isIncrease && Number(baseQuantity || 0) + breakdown.unitsPerCarton > available);
  });
  row?.querySelectorAll('[data-previsit-invoice-unit-step="remainder"][data-delta="1"]').forEach((control) => {
    control.disabled = Number(baseQuantity || 0) + 1 > available;
  });
  return breakdown;
}

function applyPrevisitInvoiceUnitEditors(row, normalize = false) {
  const product = productForPrevisit(row?.dataset.productId);
  const cartonInput = row?.querySelector('[data-previsit-invoice-unit-input="carton"]');
  const remainderInput = row?.querySelector('[data-previsit-invoice-unit-input="remainder"]');
  const finalInput = row?.querySelector('[data-field="quantity"]');
  if (!product || !cartonInput || !remainderInput || !finalInput) return;
  const factor = previsitInvoiceUnitBreakdown(product, 0).unitsPerCarton;
  let cartons = parsePrevisitUnitQuantity(cartonInput.value);
  let remainder = parsePrevisitUnitQuantity(remainderInput.value);
  let total = previsitInvoiceBaseQuantity(cartons, remainder, factor);
  const requestedTotal = total;
  total = clampPrevisitQuantityToInventory(product, requestedTotal);
  if (normalize || total !== requestedTotal) {
    const normalized = previsitInvoiceUnitBreakdown(product, total);
    cartons = normalized.cartonQuantity;
    remainder = normalized.remainderQuantity;
    total = previsitInvoiceBaseQuantity(cartons, remainder, normalized.unitsPerCarton);
    cartonInput.value = String(cartons);
    remainderInput.value = String(remainder);
  }
  finalInput.value = String(total);
  const units = previsitSaleUnits(product);
  const quantities = Object.fromEntries(units.map((unit) => [previsitUnitKey(unit), 0]));
  const baseUnit = units.find((unit) => Number(unit.factor) === 1) || units[0];
  const largestUnit = units.filter((unit) => Number(unit.factor) > 1).sort((a, b) => Number(b.factor) - Number(a.factor))[0];
  if (largestUnit) quantities[previsitUnitKey(largestUnit)] = cartons;
  if (baseUnit) quantities[previsitUnitKey(baseUnit)] = remainder;
  previsitProductUnitQuantities.set(String(product.id), quantities);
  resetPrevisitLineCalculation(row);
  previsitPreview = null;
  $('#previsitPreviewResult').hidden = true;
  syncPrevisitCartSummary();
}

function previsitUnitKey(unit) {
  return `${unit?.ref ?? ''}|${unit?.name || ''}|${Number(unit?.factor || 1)}`;
}

function selectedPrevisitSaleUnit(product) {
  const units = previsitSaleUnits(product);
  const selectedKey = previsitProductUnitSelections.get(String(product?.id));
  return units.find((unit) => previsitUnitKey(unit) === selectedKey) || units[0] || {ref: null, name: 'عدد', factor: 1};
}

function setPrevisitProductUnit(productId, unitKey) {
  const product = productForPrevisit(productId);
  const unit = previsitSaleUnits(product).find((item) => previsitUnitKey(item) === unitKey);
  if (!unit) return;
  previsitProductUnitSelections.set(String(productId), previsitUnitKey(unit));
  renderPrevisitProductOptions();
  renderPrevisitProductList();
}

function previsitQuantityForSelectedUnit(product) {
  const factor = selectedPrevisitSaleUnit(product).factor || 1;
  return previsitCartQuantity(product?.id) / factor;
}

function formatPrevisitUnitQuantity(value) {
  return Number(value || 0).toLocaleString('fa-IR', {maximumFractionDigits: 3});
}

function previsitAvailableBaseQuantity(product) {
  const available = Number(product?.available_qty);
  return Number.isFinite(available) ? Math.max(0, Math.floor(available)) : 0;
}

function clampPrevisitQuantityToInventory(product, requestedQuantity, notify = true) {
  const requested = Math.max(0, Math.floor(Number(requestedQuantity || 0)));
  const available = previsitAvailableBaseQuantity(product);
  if (requested <= available) return requested;
  if (notify) {
    toast(`موجودی ${product?.name || 'کالا'} فقط ${available.toLocaleString('fa-IR')} ${product?.unit || 'عدد'} است؛ مقدار سبد از موجودی بیشتر نمی‌شود.`);
  }
  return available;
}

function normalizePrevisitUnitQuantitiesToBase(product, baseQuantity) {
  const units = previsitSaleUnits(product);
  const quantities = Object.fromEntries(units.map((unit) => [previsitUnitKey(unit), 0]));
  let remainder = Math.max(0, Math.floor(Number(baseQuantity || 0)));
  [...units].sort((a, b) => Number(b.factor) - Number(a.factor)).forEach((unit) => {
    const factor = Math.max(1, Number(unit.factor || 1));
    const quantity = Math.floor(remainder / factor);
    quantities[previsitUnitKey(unit)] = quantity;
    remainder -= quantity * factor;
  });
  previsitProductUnitQuantities.set(String(product?.id || ''), quantities);
  return quantities;
}

function changePrevisitProductQuantityByUnit(productId, unitDelta) {
  const product = productForPrevisit(productId);
  const factor = selectedPrevisitSaleUnit(product).factor || 1;
  changePrevisitProductQuantity(productId, Number(unitDelta || 0) * factor);
}

function setPrevisitProductQuantityByUnit(productId, unitQuantity) {
  const product = productForPrevisit(productId);
  const factor = selectedPrevisitSaleUnit(product).factor || 1;
  setPrevisitProductQuantity(productId, Number(unitQuantity || 0) * factor);
}

function previsitListUnitQuantities(product) {
  const productId = String(product?.id || '');
  const units = previsitSaleUnits(product);
  const stored = previsitProductUnitQuantities.get(productId) || {};
  const quantities = Object.fromEntries(units.map((unit) => {
    const key = previsitUnitKey(unit);
    return [key, Math.max(0, Math.trunc(Number(stored[key] || 0)))];
  }));
  const representedTotal = units.reduce((sum, unit) => sum + quantities[previsitUnitKey(unit)] * unit.factor, 0);
  const cartTotal = previsitCartQuantity(productId);
  if (Math.abs(representedTotal - cartTotal) > 0.0001) {
    const baseUnit = units.find((unit) => unit.factor === 1) || units[0];
    const baseKey = previsitUnitKey(baseUnit);
    const adjustedBaseQuantity = Number(quantities[baseKey] || 0) + (cartTotal - representedTotal) / baseUnit.factor;
    if (baseUnit && adjustedBaseQuantity >= 0) {
      quantities[baseKey] = adjustedBaseQuantity;
    } else {
      Object.keys(quantities).forEach((key) => { quantities[key] = 0; });
      if (baseUnit) quantities[baseKey] = cartTotal / baseUnit.factor;
    }
  }
  previsitProductUnitQuantities.set(productId, quantities);
  return quantities;
}

function parsePrevisitUnitQuantity(value) {
  const normalized = String(value ?? '')
    .replace(/[۰-۹]/g, (digit) => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(digit)))
    .replace(/[٠-٩]/g, (digit) => String('٠١٢٣٤٥٦٧٨٩'.indexOf(digit)))
    .replace(/[^0-9]/g, '');
  return Math.max(0, Math.trunc(Number(normalized || 0)));
}

function previsitListUnitComposition(product, quantities = previsitListUnitQuantities(product)) {
  return previsitSaleUnits(product)
    .map((unit) => ({unit, quantity: Number(quantities[previsitUnitKey(unit)] || 0)}))
    .filter((item) => item.quantity > 0)
    .map((item) => `${formatPrevisitUnitQuantity(item.quantity)} ${item.unit.name}`)
    .join(' + ');
}

function setPrevisitListUnitQuantity(productId, unitKey, value) {
  const product = productForPrevisit(productId);
  const units = previsitSaleUnits(product);
  if (!units.some((unit) => previsitUnitKey(unit) === unitKey)) return;
  const quantities = {...previsitListUnitQuantities(product)};
  quantities[unitKey] = parsePrevisitUnitQuantity(value);
  previsitProductUnitQuantities.set(String(productId), quantities);
  const baseQuantity = units.reduce((sum, unit) => sum + Number(quantities[previsitUnitKey(unit)] || 0) * unit.factor, 0);
  const acceptedQuantity = setPrevisitProductQuantity(productId, baseQuantity);
  if (acceptedQuantity < baseQuantity) normalizePrevisitUnitQuantitiesToBase(product, acceptedQuantity);
}

function changePrevisitListUnitQuantity(productId, unitKey, delta) {
  const product = productForPrevisit(productId);
  const quantities = previsitListUnitQuantities(product);
  setPrevisitListUnitQuantity(productId, unitKey, Number(quantities[unitKey] || 0) + Number(delta || 0));
}

function updatePrevisitListUnitFeedback(input) {
  const product = productForPrevisit(input?.dataset.previsitListUnitQuantity);
  const card = input?.closest('[data-previsit-list-product]');
  if (!product || !card) return;
  const quantities = previsitListUnitQuantities(product);
  const quantity = Number(quantities[input.dataset.previsitUnitKey] || 0);
  const composition = previsitListUnitComposition(product, quantities);
  const decrease = input.closest('.previsit-list-unit-row')?.querySelector('[data-previsit-list-unit-decrease]');
  const increase = input.closest('.previsit-list-unit-row')?.querySelector('[data-previsit-list-unit-increase]');
  const unit = previsitSaleUnits(product).find((item) => previsitUnitKey(item) === input.dataset.previsitUnitKey);
  input.value = String(quantity);
  if (decrease) decrease.disabled = quantity <= 0;
  if (increase) increase.disabled = inCart + Number(unit?.factor || 1) > previsitAvailableBaseQuantity(product);
  card.classList.toggle('is-in-cart', inCart > 0);
  const summary = card.querySelector('[data-previsit-list-unit-summary]');
  if (summary) summary.textContent = `${composition ? `${composition} = ` : ''}${formatPrevisitUnitQuantity(inCart)} ${product.unit || 'عدد'} در سبد`;
}

function previsitCatalogUnitRows(product) {
  const quantities = previsitListUnitQuantities(product);
  const inCart = previsitCartQuantity(product.id);
  const available = previsitAvailableBaseQuantity(product);
  const rows = previsitSaleUnits(product).map((unit) => {
    const unitKey = previsitUnitKey(unit);
    const quantity = Number(quantities[unitKey] || 0);
    return `<div class="previsit-list-unit-row"><span><b>${esc(unit.name)}</b>${unit.factor === 1 ? '' : `<small>هر ${formatPrevisitUnitQuantity(unit.factor)} ${esc(product.unit || 'عدد')}</small>`}</span><div><button type="button" data-previsit-catalog-unit-decrease="${esc(product.id)}" data-previsit-unit-key="${esc(unitKey)}" ${quantity <= 0 ? 'disabled' : ''} aria-label="کم کردن یک ${esc(unit.name)}">−</button><input data-previsit-catalog-unit-quantity="${esc(product.id)}" data-previsit-unit-key="${esc(unitKey)}" type="text" pattern="[0-9۰-۹٠-٩]*" value="${esc(quantity)}" inputmode="numeric" autocomplete="off" enterkeyhint="done" aria-label="تعداد ${esc(unit.name)} سفارش ${esc(product.name)}"><button type="button" data-previsit-catalog-unit-increase="${esc(product.id)}" data-previsit-unit-key="${esc(unitKey)}" ${inCart + Number(unit.factor || 1) > available ? 'disabled' : ''} aria-label="افزودن یک ${esc(unit.name)}">+</button></div></div>`;
  }).join('');
  const composition = previsitListUnitComposition(product, quantities);
  return `<div class="previsit-product-unit-grid" aria-label="تعداد واحدهای سفارش ${esc(product.name)}"><div class="previsit-list-unit-rows">${rows}</div><em data-previsit-catalog-unit-summary>${composition ? `${esc(composition)} = ` : ''}${formatPrevisitUnitQuantity(inCart)} ${esc(product.unit || 'عدد')} در سبد</em></div>`;
}

function updatePrevisitCatalogUnitFeedback(input) {
  const product = productForPrevisit(input?.dataset.previsitCatalogUnitQuantity);
  const card = input?.closest('.previsit-product-card, .previsit-grouped-product');
  if (!product || !card) return;
  const quantities = previsitListUnitQuantities(product);
  const quantity = Number(quantities[input.dataset.previsitUnitKey] || 0);
  const inCart = previsitCartQuantity(product.id);
  const composition = previsitListUnitComposition(product, quantities);
  const decrease = input.closest('.previsit-list-unit-row')?.querySelector('[data-previsit-catalog-unit-decrease]');
  const increase = input.closest('.previsit-list-unit-row')?.querySelector('[data-previsit-catalog-unit-increase]');
  const unit = previsitSaleUnits(product).find((item) => previsitUnitKey(item) === input.dataset.previsitUnitKey);
  input.value = String(quantity);
  if (decrease) decrease.disabled = quantity <= 0;
  if (increase) increase.disabled = inCart + Number(unit?.factor || 1) > previsitAvailableBaseQuantity(product);
  card.classList.toggle('is-in-cart', inCart > 0);
  const summary = card.querySelector('[data-previsit-catalog-unit-summary]');
  if (summary) summary.textContent = `${composition ? `${composition} = ` : ''}${formatPrevisitUnitQuantity(inCart)} ${product.unit || 'عدد'} در سبد`;
}

function updatePrevisitOrderStickyTop() {
  const cart = $('#previsitCart');
  const header = cart?.querySelector('.previsit-cart-header');
  if (!cart || !header) return;
  const headerTop = Number.parseFloat(getComputedStyle(header).top) || 0;
  const stickyTop = Math.max(0, Math.ceil(header.getBoundingClientRect().height + headerTop + 4));
  cart.style.setProperty('--previsit-order-sticky-top', `${stickyTop}px`);
  const listStickyTop = stickyTop + 2;
  cart.style.setProperty('--previsit-list-sticky-top', `${listStickyTop}px`);
}

function togglePrevisitVisitMenu(forceOpen) {
  const rail = $('.previsit-visit-rail');
  const toggle = $('#previsitVisitMenuToggle');
  const backdrop = $('#previsitVisitMenuBackdrop');
  if (!rail || !toggle || !backdrop) return;
  const open = typeof forceOpen === 'boolean' ? forceOpen : !rail.classList.contains('is-open');
  rail.classList.toggle('is-open', open);
  toggle.setAttribute('aria-expanded', String(open));
  backdrop.hidden = !open;
  document.body.classList.toggle('previsit-visit-menu-open', open);
  if (open) requestAnimationFrame(() => $('#previsitVisitMenuClose')?.focus());
}

function startPrevisitVisitTimer(startedAt = previsitSession?.started_at) {
  if (previsitVisitTimerHandle) window.clearInterval(previsitVisitTimerHandle);
  const parsed = Date.parse(startedAt || '');
  previsitVisitStartedAt = Number.isFinite(parsed) ? parsed : Date.now();
  const render = () => {
    const timer = $('#previsitVisitTimer');
    if (!timer || !previsitVisitStartedAt) return;
    const elapsed = Math.max(0, Math.floor((Date.now() - previsitVisitStartedAt) / 1000));
    const hours = Math.floor(elapsed / 3600);
    const minutes = Math.floor((elapsed % 3600) / 60);
    const seconds = elapsed % 60;
    const value = `${hours ? `${String(hours).padStart(2, '0')}:` : ''}${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    timer.textContent = value.replace(/\d/g, (digit) => '۰۱۲۳۴۵۶۷۸۹'[Number(digit)]);
    timer.dateTime = `PT${hours}H${minutes}M${seconds}S`;
  };
  render();
  previsitVisitTimerHandle = window.setInterval(render, 1000);
}

function stopPrevisitVisitTimer() {
  if (previsitVisitTimerHandle) window.clearInterval(previsitVisitTimerHandle);
  previsitVisitTimerHandle = null;
  previsitVisitStartedAt = null;
}

function updatePrevisitVisitMenuCurrent(section = previsitVisitSection) {
  const current = $('#previsitVisitMenuCurrent');
  const active = $(`.previsit-visit-rail [data-previsit-section="${section}"] b`);
  if (current && active) current.textContent = active.textContent;
}

function updatePrevisitOrderContextSummary() {
  const root = $('#previsitOrderContextSummary');
  if (!root) return;
  const values = [
    ['درخواست', $('#previsitOrderType')?.selectedOptions?.[0]?.textContent],
    ['انبار', $('#previsitWarehouse')?.selectedOptions?.[0]?.textContent],
    ['پرداخت', $('#previsitPaymentType')?.selectedOptions?.[0]?.textContent],
  ];
  root.innerHTML = values.map(([label, value]) => `<span><small>${label}</small><b>${esc(String(value || 'تعیین نشده').trim())}</b></span>`).join('');
}

function togglePrevisitOrderPanel(panelName, forceOpen) {
  const panels = {
    assistant: $('#previsitOrderAssistantPanel'),
  };
  const target = panels[panelName];
  if (!target) return;
  const shouldOpen = typeof forceOpen === 'boolean' ? forceOpen : target.hidden;
  Object.values(panels).forEach((panel) => { if (panel) panel.hidden = true; });
  $$('[data-previsit-order-panel]').forEach((button) => {
    button.classList.remove('is-active');
    button.setAttribute('aria-expanded', 'false');
  });
  if (shouldOpen) {
    target.hidden = false;
    const button = $(`[data-previsit-order-panel="${panelName}"]`);
    button?.classList.add('is-active');
    button?.setAttribute('aria-expanded', 'true');
  }
  $('#previsitOrderCommon')?.classList.toggle('is-panel-open', shouldOpen);
  requestAnimationFrame(updatePrevisitOrderStickyTop);
}

function togglePrevisitCatalogFilters(forceOpen) {
  const panel = $('#previsitCatalogFilterPanel');
  const button = $('#previsitCatalogFilterToggle');
  if (!panel || !button) return;
  const open = typeof forceOpen === 'boolean' ? forceOpen : panel.hidden;
  panel.hidden = !open;
  button.classList.toggle('is-active', open);
  button.setAttribute('aria-expanded', String(open));
}

function selectedPrevisitWarehouseRef() {
  return String($('#previsitWarehouse')?.value || previsitContext?.warehouse_selection?.default_ref || '');
}

function previsitProductAtSelectedConditions(product) {
  const warehouseRef = selectedPrevisitWarehouseRef();
  const stock = product?.warehouse_inventory?.[warehouseRef];
  const orderTypeRef = String($('#previsitOrderType')?.value || previsitContext?.pricing?.catalog_order_type_ref || product?.indicative_order_type_ref || '');
  const baseOrderTypeRef = String(product?.indicative_order_type_ref || '');
  const selectedPrice = product?.indicative_prices?.[orderTypeRef];
  const selectedConsumerPrice = product?.consumer_prices?.[orderTypeRef];
  const selectedManufacturerPrice = product?.manufacturer_prices?.[orderTypeRef];
  const pricePatch = orderTypeRef && orderTypeRef !== baseOrderTypeRef
    ? {
      indicative_price: Number(selectedPrice || 0),
      consumer_price: Number(selectedConsumerPrice || 0),
      manufacturer_price: Number(selectedManufacturerPrice || 0),
      catalog_tax_inclusive_price: Number(selectedPrice || 0) > 0
        ? Math.round(Number(selectedPrice) * (1 + Number(product?.catalog_tax_percent || 0) / 100))
        : 0,
      price_status: Number(selectedPrice || 0) > 0 ? 'selected_order_type_base_contract' : 'official_preview_required',
      indicative_order_type_ref: Number(orderTypeRef),
    }
    : {};
  if (stock) return {...product, ...stock, ...pricePatch, selected_warehouse_ref: warehouseRef};
  if (warehouseRef && product?.warehouse_inventory && warehouseRef !== String(product.stock_ref || '')) {
    return {...product, on_hand_qty: 0, reserved_qty: 0, available_qty: 0, ...pricePatch, selected_warehouse_ref: warehouseRef};
  }
  return {...product, ...pricePatch};
}

function resetPrevisitLineCalculation(row) {
  clearPrevisitGiftLines();
  const product = productForPrevisit(row.dataset.productId);
  const quantity = Number(row.querySelector('[data-field="quantity"]')?.value || 0);
  const indicativePrice = Number(product?.indicative_price || row.dataset.indicativePrice || 0);
  row.dataset.officialPrice = '0';
  row.dataset.discount = '0';
  row.classList.remove('is-calculated');
  row.querySelector('[data-field="price_label"]').textContent = 'قیمت پایه';
  row.querySelector('[data-field="unit_price"]').textContent = `${indicativePrice.toLocaleString('fa-IR')} ریال`;
  row.querySelector('[data-field="gross_amount"]').textContent = quantity && indicativePrice
    ? `${(quantity * indicativePrice).toLocaleString('fa-IR')} ریال`
    : '—';
  row.querySelector('[data-field="discount_percent"]').textContent = '—';
  row.querySelector('[data-field="discount_amount"]').textContent = '—';
  ['cash', 'volume', 'goods'].forEach((category) => {
    row.querySelector(`[data-field="${category}_discount_percent"]`).textContent = '—';
    row.querySelector(`[data-field="${category}_discount_amount"]`).textContent = '—';
  });
  row.querySelector('[data-field="tax_and_charge_amount"]').textContent = '—';
  row.querySelector('[data-field="net_amount"]').textContent = '—';
}

function addPrevisitLine(line = {}) {
  prepareNgtPrevisitUi();
  const productId = String(line.product_id || $('#previsitProductPicker')?.value || '');
  const product = productForPrevisit(productId);
  if (!productId || !product) {
    if (!line.product_id) toast('\u06a9\u0627\u0644\u0627 \u0631\u0627 \u0627\u0646\u062a\u062e\u0627\u0628 \u06a9\u0646\u06cc\u062f.');
    return;
  }
  const existing = previsitOrderRows().find((row) => row.dataset.productId === productId);
  const requestedIncrement = Math.max(0, Math.floor(Number(line.quantity || $('#previsitNewQuantity')?.value || 1)));
  const currentQuantity = existing ? Number(existing.querySelector('[data-field="quantity"]').value || 0) : 0;
  const requestedTotal = currentQuantity + requestedIncrement;
  const acceptedTotal = clampPrevisitQuantityToInventory(product, requestedTotal);
  const quantity = acceptedTotal - currentQuantity;
  if (!(quantity > 0)) return;
  if (acceptedTotal < requestedTotal) normalizePrevisitUnitQuantitiesToBase(product, acceptedTotal);
  if (existing) {
    const input = existing.querySelector('[data-field="quantity"]');
    input.value = acceptedTotal;
    syncPrevisitInvoiceUnitBreakdown(existing, product, Number(input.value || 0));
    resetPrevisitLineCalculation(existing);
    previsitPreview = null;
    $('#previsitPreviewResult').hidden = true;
    syncPrevisitCartSummary();
    return;
  }
  const row = document.createElement('article');
  row.className = 'previsit-line';
  row.dataset.productId = productId;
  row.dataset.title = product.name;
  row.dataset.indicativePrice = String(line.unit_price || product.indicative_price || 0);
  row.dataset.officialPrice = String(line.unit_price || 0);
  row.dataset.discount = String(line.discount_amount || 0);
  row.innerHTML = `<div class="previsit-line-product"><strong>${esc(product.name)}</strong><small>${esc(product.code)} &#183; ${esc(product.brand || product.stock_name)} &#183; &#1605;&#1608;&#1580;&#1608;&#1583;&#1740; ${Number(product.available_qty).toLocaleString('fa-IR')} ${esc(product.unit)}</small></div><label class="previsit-line-quantity">&#1578;&#1593;&#1583;&#1575;&#1583; &#1606;&#1607;&#1575;&#1740;&#1740;<input data-field="quantity" type="number" min="0" step="1" value="${esc(quantity)}" readonly aria-readonly="true" tabindex="-1"></label><span class="previsit-invoice-unit-cell is-carton"><span class="previsit-invoice-unit-editor"><button type="button" data-previsit-invoice-unit-step="carton" data-delta="-1" aria-label="&#1705;&#1575;&#1607;&#1588; &#1705;&#1575;&#1585;&#1578;&#1606;"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3 7h10v2H3z"/></svg></button><input data-field="carton_quantity" data-previsit-invoice-unit-input="carton" type="text" inputmode="numeric" pattern="[0-9&#1776;-&#1785;&#1632;-&#1641;]*" value="0" aria-label="&#1578;&#1593;&#1583;&#1575;&#1583; &#1705;&#1575;&#1585;&#1578;&#1606;"><button type="button" data-previsit-invoice-unit-step="carton" data-delta="1" aria-label="&#1575;&#1601;&#1586;&#1575;&#1740;&#1588; &#1705;&#1575;&#1585;&#1578;&#1606;"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M7 3h2v4h4v2H9v4H7V9H3V7h4z"/></svg></button></span></span><span class="previsit-invoice-unit-cell is-remainder"><span class="previsit-invoice-unit-editor"><button type="button" data-previsit-invoice-unit-step="remainder" data-delta="-1" aria-label="&#1705;&#1575;&#1607;&#1588; &#1593;&#1583;&#1583;"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3 7h10v2H3z"/></svg></button><input data-field="remainder_quantity" data-previsit-invoice-unit-input="remainder" type="text" inputmode="numeric" pattern="[0-9&#1776;-&#1785;&#1632;-&#1641;]*" value="0" aria-label="&#1578;&#1593;&#1583;&#1575;&#1583; &#1593;&#1583;&#1583;"><button type="button" data-previsit-invoice-unit-step="remainder" data-delta="1" aria-label="&#1575;&#1601;&#1586;&#1575;&#1740;&#1588; &#1593;&#1583;&#1583;"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M7 3h2v4h4v2H9v4H7V9H3V7h4z"/></svg></button></span></span><span class="previsit-invoice-unit-cell is-units-per-carton"><output data-field="units_per_carton">—</output></span><button class="previsit-remove-line" type="button" aria-label="&#1581;&#1584;&#1601; &#1585;&#1583;&#1740;&#1601;">&#215;</button><div class="previsit-line-breakdown"><span><small data-field="price_label">&#1602;&#1740;&#1605;&#1578; &#1662;&#1575;&#1740;&#1607;</small><output data-field="unit_price">${Number(line.unit_price || product.indicative_price || 0).toLocaleString('fa-IR')} &#1585;&#1740;&#1575;&#1604;</output></span><span><small>&#1606;&#1575;&#1582;&#1575;&#1604;&#1589; &#1582;&#1591;</small><output data-field="gross_amount">&#8212;</output></span><span class="previsit-line-discount"><small>&#1578;&#1582;&#1601;&#1740;&#1601; &#1575;&#1740;&#1606; &#1582;&#1591;</small><output data-field="discount_percent">&#8212;</output><em data-field="discount_amount">&#8212;</em></span><span><small>&#1605;&#1575;&#1604;&#1740;&#1575;&#1578; &#1608; &#1593;&#1608;&#1575;&#1585;&#1590; &#1582;&#1591;</small><output data-field="tax_and_charge_amount">&#8212;</output></span><span class="previsit-line-net"><small>&#1605;&#1576;&#1604;&#1594; &#1606;&#1607;&#1575;&#1740;&#1740; &#1582;&#1591;</small><output data-field="net_amount">&#8212;</output></span></div><div class="previsit-line-rules" data-field="line_rules"></div><p class="previsit-line-formula" data-field="line_formula"></p>`;
  const [basePriceCell, grossCell, totalDiscountCell, taxCell, netCell] = row.querySelector('.previsit-line-breakdown').children;
  basePriceCell.classList.add('previsit-line-base');
  grossCell.classList.add('previsit-line-gross');
  totalDiscountCell.classList.add('previsit-line-total-discount');
  taxCell.classList.add('previsit-line-tax');
  netCell.classList.add('previsit-line-net');
  const optionalPrice = (value) => Number(value || 0) > 0
    ? `${Number(value).toLocaleString('fa-IR')} \u0631\u06cc\u0627\u0644`
    : '\u2014';
  basePriceCell.insertAdjacentHTML('afterend', `<span class="previsit-line-producer"><small>\u0642\u06cc\u0645\u062a \u062a\u0648\u0644\u06cc\u062f\u06a9\u0646\u0646\u062f\u0647</small><output>${optionalPrice(product.manufacturer_price)}</output></span><span class="previsit-line-consumer"><small>\u0642\u06cc\u0645\u062a \u0645\u0635\u0631\u0641\u200c\u06a9\u0646\u0646\u062f\u0647</small><output>${optionalPrice(product.consumer_price)}</output></span>`);
  const removeButton = row.querySelector('.previsit-remove-line');
  removeButton.title = '\u062d\u0630\u0641 \u0631\u062f\u06cc\u0641';
  removeButton.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 3h6l1 2h4v2H4V5h4l1-2Zm-2 6h10l-1 11H8L7 9Zm3 2v7h2v-7h-2Zm4 0v7h2v-7h-2Z"/></svg>';
  row.querySelector('.previsit-line-breakdown').insertAdjacentHTML('afterend', `<div class="previsit-line-discount-columns"><span class="is-cash"><small>تخفیف نقدی</small><output data-field="cash_discount_percent">—</output><em data-field="cash_discount_amount">—</em></span><span class="is-volume"><small>تخفیف حجمی</small><output data-field="volume_discount_percent">—</output><em data-field="volume_discount_amount">—</em></span><span class="is-goods"><small>تخفیف کالایی</small><output data-field="goods_discount_percent">—</output><em data-field="goods_discount_amount">—</em></span></div><p class="previsit-line-unclassified" data-field="unclassified_discount" hidden></p>`);
  syncPrevisitInvoiceUnitBreakdown(row, product, quantity);
  row.querySelectorAll('[data-previsit-invoice-unit-input]').forEach((input) => {
    input.addEventListener('input', () => applyPrevisitInvoiceUnitEditors(row, false));
    input.addEventListener('change', () => applyPrevisitInvoiceUnitEditors(row, true));
  });
  row.querySelectorAll('[data-previsit-invoice-unit-step]').forEach((button) => {
    button.addEventListener('click', () => {
      const input = row.querySelector(`[data-previsit-invoice-unit-input="${button.dataset.previsitInvoiceUnitStep}"]`);
      if (!input || button.disabled) return;
      input.value = String(Math.max(0, parsePrevisitUnitQuantity(input.value) + Number(button.dataset.delta || 0)));
      applyPrevisitInvoiceUnitEditors(row, true);
    });
  });
  removeButton.addEventListener('click', () => { row.remove(); clearPrevisitGiftLines(); previsitPreview = null; $('#previsitPreviewResult').hidden = true; syncPrevisitCartSummary(); });
  $('#previsitLines').append(row);
  resetPrevisitLineCalculation(row);
  syncPrevisitCartSummary();
}

function previsitLines() {
  return previsitOrderRows().map((row) => ({
    product_id: row.dataset.productId,
    title: row.dataset.title || '',
    quantity: Number(row.querySelector('[data-field="quantity"]').value),
    unit_price: Number(row.dataset.officialPrice || 0) > 0
      ? Number(row.dataset.officialPrice)
      : Number(row.dataset.indicativePrice || 0),
    discount_amount: Number(row.dataset.discount || 0),
  })).filter((line) => line.product_id && line.quantity > 0);
}

function previsitOrderRows() {
  return $$('.previsit-line:not(.previsit-gift-line)', $('#previsitLines'));
}

function clearPrevisitGiftLines() {
  $$('.previsit-gift-line', $('#previsitLines')).forEach((row) => row.remove());
}

function officialPrevisitGiftLines(data) {
  if (Array.isArray(data.gift_lines) && data.gift_lines.length) return data.gift_lines;
  const lookup = (item, ...names) => {
    const entries = Object.entries(item || {});
    const match = entries.find(([key]) => names.some((name) => key.toLocaleLowerCase() === name.toLocaleLowerCase()));
    return match?.[1];
  };
  return (Array.isArray(data.prizes) ? data.prizes : []).filter((item) => item && typeof item === 'object').map((item) => ({
    product_id: String(lookup(item, 'GoodsRef', 'ProductRef', 'PrizeRef') || ''),
    parent_product_id: String(lookup(item, 'BaseGoodsRef', 'SourceGoodsRef', 'OrderGoodsRef', 'ParentGoodsRef') || ''),
    title: String(lookup(item, 'GoodsName', 'ProductName', 'PrizeName') || ''),
    quantity: Number(lookup(item, 'TotalQty', 'PrizeQty', 'Quantity', 'UnitQty') || 0),
    unit_price: Number(lookup(item, 'CustPrice', 'UserPrice', 'Unit' + 'Price', 'Price') || 0),
    gross_amount: Number(lookup(item, 'GrossAmount', 'Amount') || 0),
    discount_amount: Number(lookup(item, 'Discount', 'DiscountAmount', 'PrizeAmount') || 0),
    discount_percent: 100,
    net_amount: 0,
    source: 'official prize',
  })).filter((gift) => gift.product_id && gift.quantity > 0);
}

function renderPrevisitGiftLines(data, officialGifts = officialPrevisitGiftLines(data)) {
  clearPrevisitGiftLines();
  const gifts = officialGifts;
  if (!gifts.length) return;
  const orderRows = previsitOrderRows();
  const rowByProduct = new Map(orderRows.map((row) => [String(row.dataset.productId), row]));
  const itemByProduct = new Map((data.items || []).map((item) => [String(item.product_id), item]));
  const perParent = new Map();
  gifts.forEach((gift) => {
    const parentId = String(gift.parent_product_id || '');
    perParent.set(parentId, (perParent.get(parentId) || 0) + 1);
  });
  const lastInsertedByParent = new Map();
  gifts.forEach((gift) => {
    const productId = String(gift.product_id || '');
    const parentId = String(gift.parent_product_id || (rowByProduct.has(productId) ? productId : ''));
    const parentRow = rowByProduct.get(parentId) || (orderRows.length === 1 ? orderRows[0] : null);
    if (!parentRow) return;
    const parentItem = itemByProduct.get(String(parentRow.dataset.productId)) || {};
    const parentGoodsDiscount = Number(parentItem.discount_breakdown?.goods?.amount || 0);
    const quantity = Number(gift.quantity || 0);
    const canUseParentGoodsAmount = (perParent.get(parentId) || 0) === 1;
    const discountAmount = Number(gift.discount_amount || 0) || (canUseParentGoodsAmount ? parentGoodsDiscount : 0);
    const unitPrice = Number(gift.unit_price || 0) || (quantity > 0 && discountAmount > 0 ? discountAmount / quantity : 0);
    const gross = Number(gift.gross_amount || 0) || discountAmount || (quantity * unitPrice);
    const title = gift.title || productForPrevisit(productId)?.name || `کالای اشانتیون ${productId}`;
    const money = (value) => Number(value || 0) > 0 ? `${Number(value).toLocaleString('fa-IR')} ریال` : '—';
    const row = document.createElement('article');
    row.className = 'previsit-line previsit-gift-line is-calculated';
    row.dataset.productId = productId;
    row.dataset.parentProductId = String(parentRow.dataset.productId);
    const giftProduct = productForPrevisit(productId) || {};
    const giftUnits = previsitInvoiceUnitBreakdown(giftProduct, quantity);
    row.innerHTML = `<div class="previsit-line-product"><strong>🎁 ${esc(title)}</strong><small>اشانتیون قطعی · زیر کالای مرتبط</small></div><span class="previsit-gift-cell is-quantity"><small>تعداد نهایی</small><b>${quantity.toLocaleString('fa-IR')}</b></span><span class="previsit-gift-cell is-carton"><small>کارتن</small><b>${formatPrevisitUnitQuantity(giftUnits.cartonQuantity)}</b></span><span class="previsit-gift-cell is-remainder"><small>عدد</small><b>${formatPrevisitUnitQuantity(giftUnits.remainderQuantity)}</b></span><span class="previsit-gift-cell is-units-per-carton"><small>تعداد در کارتن</small><b>${giftUnits.unitsPerCarton ? formatPrevisitUnitQuantity(giftUnits.unitsPerCarton) : '—'}</b></span><span class="previsit-gift-cell is-unit"><small>قیمت واحد</small><b>${money(unitPrice)}</b></span><span class="previsit-gift-cell is-producer"><small>تولیدکننده</small><b>—</b></span><span class="previsit-gift-cell is-consumer"><small>مصرف‌کننده</small><b>—</b></span><span class="previsit-gift-cell is-gross"><small>ارزش اشانتیون</small><b>${money(gross)}</b></span><span class="previsit-gift-cell is-goods"><small>تخفیف کالایی</small><b>۱۰۰٪ تخفیف</b><em>${money(discountAmount || gross)}</em></span><span class="previsit-gift-cell is-volume"><small>حجمی</small><b>—</b></span><span class="previsit-gift-cell is-cash"><small>نقدی</small><b>—</b></span><span class="previsit-gift-cell is-tax"><small>مالیات</small><b>۰ ریال</b></span><span class="previsit-gift-cell is-net"><small>قابل پرداخت</small><b>۰ ریال</b></span><span class="previsit-gift-badge">هدیه</span><p class="previsit-gift-note">این ردیف به‌عنوان جایزه محاسبه شده و دوباره به جمع فاکتور اضافه نمی‌شود.</p>`;
    const anchor = lastInsertedByParent.get(parentRow) || parentRow;
    anchor.after(row);
    lastInsertedByParent.set(parentRow, row);
  });
}

function renderNgtPreview(data) {
  const byProduct = new Map((data.items || []).map((item) => [String(item.product_id), item]));
  const officialGifts = officialPrevisitGiftLines(data);
  const giftParents = new Set(officialGifts.map((gift) => String(gift.parent_product_id || '')));
  if (officialGifts.length && ![...giftParents].some(Boolean) && previsitOrderRows().length === 1) {
    giftParents.add(String(previsitOrderRows()[0].dataset.productId));
  }
  previsitOrderRows().forEach((row) => {
    const item = byProduct.get(row.dataset.productId);
    if (!item) return;
    const gross = Number(item.gross_amount ?? (Number(item.quantity || 0) * Number(item.unit_price || 0)));
    const discount = Number(item.discount_amount || 0);
    const discountPercent = Number(item.discount_percent ?? (gross ? (discount / gross) * 100 : 0));
    const taxAndCharge = Number(item.tax_and_charge_amount ?? (Number(item.tax_amount || 0) + Number(item.charge_amount || 0)));
    const net = Number(item.net_amount || 0);
    row.dataset.officialPrice = String(item.unit_price || 0);
    row.dataset.discount = String(discount);
    row.classList.add('is-calculated');
    syncPrevisitInvoiceUnitBreakdown(row, productForPrevisit(row.dataset.productId), Number(item.quantity || row.querySelector('[data-field="quantity"]')?.value || 0));
    row.querySelector('[data-field="price_label"]').textContent = 'قیمت نهایی';
    row.querySelector('[data-field="unit_price"]').textContent = `${Number(item.unit_price || 0).toLocaleString('fa-IR')} \u0631\u06cc\u0627\u0644`;
    row.querySelector('[data-field="gross_amount"]').textContent = `${gross.toLocaleString('fa-IR')} \u0631\u06cc\u0627\u0644`;
    row.querySelector('[data-field="discount_percent"]').textContent = `${discountPercent.toLocaleString('fa-IR', {maximumFractionDigits: 2})}\u066a \u0645\u0624\u062b\u0631`;
    row.querySelector('[data-field="discount_amount"]').textContent = `${discount.toLocaleString('fa-IR')} \u0631\u06cc\u0627\u0644`;
    const breakdown = item.discount_breakdown || {};
    ['cash', 'volume', 'goods'].forEach((category) => {
      const part = breakdown[category] || {};
      const amount = Number(part.amount || 0);
      const percent = Number(part.percent || 0);
      const hasOfficialGift = category === 'goods' && giftParents.has(row.dataset.productId);
      row.querySelector(`[data-field="${category}_discount_percent"]`).textContent = hasOfficialGift
        ? 'اشانتیون در ردیف زیر ↓'
        : `${percent.toLocaleString('fa-IR', {maximumFractionDigits: 2})}٪ مؤثر`;
      row.querySelector(`[data-field="${category}_discount_amount"]`).textContent = hasOfficialGift
        ? (amount > 0 ? `ارزش ${amount.toLocaleString('fa-IR')} ریال` : 'محاسبه‌شده')
        : `${amount.toLocaleString('fa-IR')} ریال`;
    });
    row.querySelector('[data-field="tax_and_charge_amount"]').textContent = `${taxAndCharge.toLocaleString('fa-IR')} \u0631\u06cc\u0627\u0644`;
    row.querySelector('[data-field="net_amount"]').textContent = `${net.toLocaleString('fa-IR')} \u0631\u06cc\u0627\u0644`;
  });
  renderPrevisitGiftLines(data, officialGifts);
  const result = $('#previsitPreviewResult');
  const totals = data.totals || {};
  const credit = data.credit_control || {};
  const money = (value) => Number(value || 0).toLocaleString('fa-IR');
  const creditWarning = credit.allowed === false
    ? `<section class="previsit-credit-warning"><strong>&#9888; امکان ثبت سفارش وجود ندارد</strong><span>${esc(credit.message || 'اعتبار مشتری برای این سفارش کافی نیست.')}</span>${Number(credit.deficit || 0) > 0 ? `<b>کسری ${money(credit.deficit)} ریال</b>` : ''}</section>`
    : '';
  const calculationMessage = !data.ok && data.message ? `<span>${esc(data.message)}</span>` : '';
  result.innerHTML = `<header><strong>${data.ok ? '&#10003; محاسبه نهایی' : 'هشدار محاسبه'}</strong>${calculationMessage}</header><div class="previsit-totals"><span>&#1606;&#1575;&#1582;&#1575;&#1604;&#1589;<b>${Number(totals.gross || 0).toLocaleString('fa-IR')}</b></span><span>&#1578;&#1582;&#1601;&#1740;&#1601;<b>${Number(totals.discount || 0).toLocaleString('fa-IR')}</b></span><span>&#1605;&#1575;&#1604;&#1740;&#1575;&#1578; &#1608; &#1593;&#1608;&#1575;&#1585;&#1590;<b>${Number((totals.tax || 0) + (totals.charge || 0)).toLocaleString('fa-IR')}</b></span><span>&#1605;&#1576;&#1604;&#1594; &#1606;&#1607;&#1575;&#1740;&#1740;<b>${Number(totals.net || 0).toLocaleString('fa-IR')} &#1585;&#1740;&#1575;&#1604;</b></span></div>${creditWarning}`;
  result.hidden = false;
  syncPrevisitCartSummary();
}

async function previewNgtPrevisit() {
  if (!previsitSession || !previsitContext) throw Error('\u0627\u0628\u062a\u062f\u0627 \u0648\u06cc\u0632\u06cc\u062a \u0631\u0627 \u0634\u0631\u0648\u0639 \u06a9\u0646\u06cc\u062f.');
  const lines = previsitLines();
  if (!lines.length) throw Error('\u062d\u062f\u0627\u0642\u0644 \u06cc\u06a9 \u06a9\u0627\u0644\u0627 \u0628\u0647 \u0633\u0628\u062f \u0627\u0636\u0627\u0641\u0647 \u06a9\u0646\u06cc\u062f.');
  const button = $('#previewPrevisit');
  button.disabled = true;
  button.textContent = 'در حال محاسبه…';
  try {
    const response = await fetch('/seller-workspace/previsit/preview', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({route_id: $('#previsitRoute').value, customer_id: $('#previsitCustomer').value, order_type_ref: Number($('#previsitOrderType').value), payment_usance_ref: $('#previsitPaymentType').value, warehouse_ref: Number($('#previsitWarehouse').value) || null, lines: lines.map(({product_id, quantity}) => ({product_id, quantity}))})});
    const data = await readJsonResponse(response, 'محاسبه نهایی انجام نشد.');
    if (!response.ok) throw Error(data.detail || 'محاسبه نهایی انجام نشد.');
    previsitPreview = data;
    renderNgtPreview(data);
    return data;
  } finally {
    button.disabled = false;
    button.textContent = 'محاسبه قیمت، تخفیف و جوایز';
  }
}

async function openPrevisit(options = {}) {
  const deferReveal = options.deferReveal === true;
  stopPrevisitVisitTimer();
  if (!deferReveal) rememberAppView('previsit', {
    routeId: String(options.routeId || ''),
    customerId: String(options.customerId || ''),
    section: 'order',
    orderMode: 'list',
    activeView: 'catalog',
  });
  prepareNgtPrevisitUi();
  $('#previsitTitle').textContent = '\u0633\u0641\u0627\u0631\u0634\u200c\u06af\u06cc\u0631\u06cc \u0648 \u06a9\u0627\u062a\u0627\u0644\u0648\u06af';
  $('#previsitTitle').nextElementSibling.textContent = 'سفارش مشتری را از کاتالوگ یا ثبت سریع تکمیل کنید.';
  previsitPanel.hidden = deferReveal;
  $('#previsitCart').hidden = true;
  previsitSession = null;
  previsitContext = null;
  previsitPreview = null;
  previsitSavedRequests = [];
  previsitEditingSavedRequestId = null;
  closePrevisitSavedRequestReview();
  const routeSelect = $('#previsitRoute');
  routeSelect.innerHTML = '<option value="">\u062f\u0631 \u062d\u0627\u0644 \u062f\u0631\u06cc\u0627\u0641\u062a \u0645\u0633\u06cc\u0631\u0647\u0627\u2026</option>';
  try {
    const response = await fetch('/seller-workspace/routes');
    if (!response.ok) throw Error('\u062f\u0631\u06cc\u0627\u0641\u062a \u0645\u0633\u06cc\u0631\u0647\u0627 \u0627\u0646\u062c\u0627\u0645 \u0646\u0634\u062f.');
    const data = await response.json();
    const dayRoutes = (data.routes || []).filter((route) => route.can_start_visit);
    routeSelect.innerHTML = dayRoutes.length
      ? '<option value="">انتخاب مسیر روز</option>' + dayRoutes.map((route) => `<option value="${esc(route.id)}">${esc(route.title)}</option>`).join('')
      : '<option value="">برای امروز مسیر روز فعالی تعیین نشده</option>';
    routeSelect.disabled = !dayRoutes.length;
    const requestedRouteId = String(options.routeId || '');
    if (requestedRouteId) {
      if (!dayRoutes.some((route) => String(route.id) === requestedRouteId)) throw Error('این مشتری در مسیر روز فعال قابل ویزیت نیست.');
      routeSelect.value = requestedRouteId;
      await loadPrevisitCustomers();
      const customerId = String(options.customerId || '');
      if (customerId) {
        const customerSelect = $('#previsitCustomer');
        if (![...customerSelect.options].some((option) => option.value === customerId)) throw Error('این مشتری در فهرست مسیر روز پیدا نشد.');
        customerSelect.value = customerId;
      }
    }
    return true;
  } catch (error) {
    closeCurrentAppView('previsit');
    toast(error.message);
    return false;
  }
}

async function openPrevisitForRouteCustomer(routeId, customerId, {deferReveal = false} = {}) {
  const routeMapWasHidden = routeMapPanel.hidden;
  const sellerWorkspaceWasHidden = sellerWorkspacePanel.hidden;
  if (!deferReveal) {
    routeMapPanel.hidden = true;
    sellerWorkspacePanel.hidden = true;
  }
  const opened = await openPrevisit({routeId: String(routeId), customerId: String(customerId), deferReveal});
  if (!opened || $('#previsitRoute').value !== String(routeId) || $('#previsitCustomer').value !== String(customerId)) {
    previsitPanel.hidden = true;
    routeMapPanel.hidden = routeMapWasHidden;
    sellerWorkspacePanel.hidden = sellerWorkspaceWasHidden;
    return false;
  }
  if (!deferReveal) {
    stopRouteMap();
    routeMapPanel.hidden = true;
    sellerWorkspacePanel.hidden = true;
  }
  return true;
}

function revealActivePrevisit(routeId, customerId) {
  rememberAppView('previsit', {
    routeId: String(routeId || ''),
    customerId: String(customerId || ''),
    section: 'profile',
    orderMode: 'list',
    activeView: 'catalog',
  });
  stopRouteMap();
  routeMapPanel.hidden = true;
  sellerWorkspacePanel.hidden = true;
  customerProfilePanel.hidden = true;
  previsitPanel.hidden = false;
}

async function startPrevisitVisit({deferReveal = false} = {}) {
  const startButton = $('#startPrevisit');
  const idleLabel = startButton.textContent;
  try {
    const route_id = $('#previsitRoute').value;
    const customer_id = $('#previsitCustomer').value;
    if (!route_id || !customer_id) throw Error('مسیر و مشتری را انتخاب کنید.');
    const policy = previsitPolicy || await loadPrevisitPolicy(route_id, customer_id);
    if (policy?.start_blockers?.length) throw Error(policy.start_blockers.join(' · '));
    startButton.disabled = true;
    startButton.classList.add('is-loading');
    startButton.setAttribute('aria-busy', 'true');
    startButton.textContent = 'در حال شروع ویزیت…';
    const needsPosition = Boolean(policy?.controls?.enforced);
    const position = needsPosition ? await currentCoordinates({maximumAge: 0, timeout: 12000}) : null;
    if (needsPosition && !position) throw Error('برای شروع ویزیت، دسترسی موقعیت دستگاه را روشن کنید.');
    const response = await fetch('/seller-workspace/previsit/visits', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({
      route_id,
      customer_id,
      latitude: position?.latitude ?? null,
      longitude: position?.longitude ?? null,
      accuracy: position?.accuracy ?? null,
    })});
    const data = await response.json();
    if (!response.ok) throw Error(data.detail || 'شروع ویزیت انجام نشد.');
    previsitSession = data;
    startPrevisitVisitTimer(data.started_at);
    startButton.textContent = 'در حال دریافت کالا، موجودی و قیمت‌ها…';
    await Promise.all([
      loadPrevisitContext(route_id, customer_id),
      loadPrevisitCustomerWorkspace(route_id, customer_id).catch((error) => {
        renderPrevisitWorkspaceError(error.message);
        return null;
      }),
      loadEmbeddedPrevisitCustomerProfile(route_id, customer_id),
      loadPrevisitSavedRequests(),
    ]);
    $('#previsitLines').innerHTML = '';
    (data.lines || []).forEach(addPrevisitLine);
    const savedPayment = (previsitContext.payment_types || []).find((item) => item.name === data.payment_type);
    const savedOrder = (previsitContext.order_types || []).find((item) => item.name === data.order_type);
    if (savedPayment) $('#previsitPaymentType').value = String(savedPayment.id);
    if (savedOrder) $('#previsitOrderType').value = String(savedOrder.id);
    if (data.warehouse_ref && (previsitContext.warehouses || []).some((item) => Number(item.ref) === Number(data.warehouse_ref))) $('#previsitWarehouse').value = String(data.warehouse_ref);
    renderPrevisitCatalogFilterOptions();
    renderPrevisitQuickFilterOptions();
    renderPrevisitProductOptions();
    updatePrevisitPriceContextNote();
    updatePrevisitOrderContextSummary();
    $('#previsitForm').classList.add('is-visit-active');
    $('#previsitCart').hidden = false;
    switchPrevisitVisitSection('profile');
    applyPrevisitRequirementGate();
    if (deferReveal) revealActivePrevisit(route_id, customer_id);
    $('#previsitCart').scrollIntoView({behavior: 'smooth', block: 'start'});
    toast('ویزیت آغاز شد؛ صفحه مشتری آماده سفارش‌گیری است.');
    return true;
  } catch (error) {
    toast(error.message);
    return false;
  } finally {
    startButton.disabled = Boolean(previsitPolicy?.start_blockers?.length);
    startButton.classList.remove('is-loading');
    startButton.removeAttribute('aria-busy');
    startButton.textContent = idleLabel;
  }
}

async function enterRouteCustomerVisit(routeId, customerId) {
  const opened = await openPrevisitForRouteCustomer(routeId, customerId, {deferReveal: true});
  if (!opened) return false;
  const policy = previsitPolicy || await loadPrevisitPolicy(routeId, customerId);
  if (policy?.start_blockers?.length) {
    prepareNgtPrevisitUi();
    await Promise.all([
      loadPrevisitCustomerWorkspace(routeId, customerId),
      loadEmbeddedPrevisitCustomerProfile(routeId, customerId),
      loadPrevisitSavedRequests(),
    ]);
    $('#previsitForm').classList.add('is-visit-active', 'is-requirement-gated');
    $('#previsitCart').hidden = false;
    applyPrevisitRequirementGate(policy);
    switchPrevisitVisitSection('profile');
    revealActivePrevisit(routeId, customerId);
    toast('ابتدا اطلاعات اجباری مشتری را تکمیل کنید.');
    return true;
  }
  return await startPrevisitVisit({deferReveal: true});
}

async function openRouteCustomerNoVisit(routeId, customerId) {
  const query = new URLSearchParams({path_id: String(routeId), customer_id: String(customerId)});
  const response = await fetch(`/seller-workspace/previsit/policy?${query}`);
  const policy = await readJsonResponse(response, 'کنترل‌های عدم ویزیت دریافت نشد.');
  if (!response.ok) throw Error(policy.detail || 'کنترل‌های عدم ویزیت دریافت نشد.');
  if (policy.start_blockers?.length) throw Error(policy.start_blockers.join(' · '));
  const reasons = policy.reasons?.no_visit || [];
  if (!reasons.length) throw Error('دلیل فعال برای عدم ویزیت این مشتری تعریف نشده است.');
  pendingRouteNoVisit = {routeId: String(routeId), customerId: String(customerId), policy};
  pendingPrevisitOutcome = null;
  $('#previsitOutcomeTitle').textContent = 'ثبت عدم ویزیت مشتری';
  $('#previsitOutcomeHint').textContent = 'دلیل عدم ویزیت را از فهرست فعال انتخاب کنید.';
  $('#previsitOutcomeReason').innerHTML = '<option value="">انتخاب دلیل</option>' + reasons.map((reason) => `<option value="${esc(reason.id)}">${esc(reason.title)}</option>`).join('');
  $('#previsitOutcomeDialog').showModal();
}

async function completeRouteCustomerNoVisit(reasonId) {
  if (!pendingRouteNoVisit) throw Error('مشتری تور برای عدم ویزیت انتخاب نشده است.');
  const {routeId, customerId, policy} = pendingRouteNoVisit;
  const controls = policy.controls || {};
  const needsPosition = Boolean(controls.enforced);
  const position = needsPosition ? await currentCoordinates({maximumAge: 0, timeout: 12000}) : null;
  if (needsPosition && !position) throw Error('برای ثبت عدم ویزیت، دسترسی موقعیت دستگاه را روشن کنید.');
  const startResponse = await fetch('/seller-workspace/previsit/visits', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({
    route_id: routeId,
    customer_id: customerId,
    latitude: position?.latitude ?? null,
    longitude: position?.longitude ?? null,
    accuracy: position?.accuracy ?? null,
  })});
  const visit = await readJsonResponse(startResponse, 'شروع ثبت عدم ویزیت انجام نشد.');
  if (!startResponse.ok) throw Error(visit.detail || 'شروع ثبت عدم ویزیت انجام نشد.');
  const completeResponse = await fetch(`/seller-workspace/previsit/visits/${encodeURIComponent(visit.visit_id)}/complete`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({
    outcome: 'no_visit',
    reason_id: reasonId,
    latitude: position?.latitude ?? null,
    longitude: position?.longitude ?? null,
    accuracy: position?.accuracy ?? null,
  })});
  const result = await readJsonResponse(completeResponse, 'ثبت عدم ویزیت انجام نشد.');
  if (!completeResponse.ok) throw Error(result.detail || 'ثبت عدم ویزیت انجام نشد.');
  if (routeMapSession) routeMapSession.stopStatuses[String(customerId)] = 'no_visit';
  pendingRouteNoVisit = null;
  $('#previsitOutcomeDialog').close();
  renderRouteMapStops();
  toast('عدم ویزیت مشتری با دلیل انتخاب‌شده ثبت شد.');
}

async function savePrevisitDraft() {
  if (!previsitSession) throw Error('\u0627\u0628\u062a\u062f\u0627 \u0648\u06cc\u0632\u06cc\u062a \u0631\u0627 \u0634\u0631\u0648\u0639 \u06a9\u0646\u06cc\u062f.');
  const payment = previsitContext?.payment_types?.find((item) => String(item.id) === $('#previsitPaymentType').value);
  const order = previsitContext?.order_types?.find((item) => String(item.id) === $('#previsitOrderType').value);
  const warehouse = previsitContext?.warehouses?.find((item) => String(item.ref) === $('#previsitWarehouse').value);
  const response = await fetch(`/seller-workspace/previsit/visits/${encodeURIComponent(previsitSession.visit_id)}/draft`, {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({lines: previsitLines(), payment_type: payment?.name || $('#previsitPaymentType').value, order_type: order?.name || $('#previsitOrderType').value, warehouse_ref: warehouse?.ref || null, warehouse_name: warehouse?.name || ''})});
  const data = await response.json();
  if (!response.ok) throw Error(data.detail || '\u0630\u062e\u06cc\u0631\u0647 \u067e\u06cc\u0634\u200c\u0646\u0648\u06cc\u0633 \u0627\u0646\u062c\u0627\u0645 \u0646\u0634\u062f.');
  previsitSession = data;
  toast(`\u067e\u06cc\u0634\u200c\u0646\u0648\u06cc\u0633 \u0630\u062e\u06cc\u0631\u0647 \u0634\u062f \u00b7 ${data.line_count} \u0631\u062f\u06cc\u0641`);
}

function previsitSavedRequestPayload() {
  const payment = previsitContext?.payment_types?.find((item) => String(item.id) === $('#previsitPaymentType').value);
  const order = previsitContext?.order_types?.find((item) => String(item.id) === $('#previsitOrderType').value);
  const warehouse = previsitContext?.warehouses?.find((item) => String(item.ref) === $('#previsitWarehouse').value);
  return {
    lines: previsitLines(),
    payment_type: payment?.name || $('#previsitPaymentType').value,
    order_type: order?.name || $('#previsitOrderType').value,
    warehouse_ref: warehouse?.ref || null,
    warehouse_name: warehouse?.name || '',
    preview: previsitPreview || {},
  };
}

function clearPrevisitWorkingCart() {
  $('#previsitLines').innerHTML = '';
  previsitProductUnitSelections.clear();
  previsitProductUnitQuantities.clear();
  previsitPreview = null;
  clearPrevisitGiftLines();
  if ($('#previsitPreviewResult')) {
    $('#previsitPreviewResult').hidden = true;
    $('#previsitPreviewResult').innerHTML = '';
  }
  if (previsitSession) previsitSession = {...previsitSession, lines: [], line_count: 0, total_amount: 0};
  renderPrevisitProductOptions();
  renderPrevisitProductList();
  renderPrevisitGroupedCatalogs();
  syncPrevisitCartSummary();
}

async function savePrevisitRequest() {
  if (!previsitSession) throw Error('ابتدا ویزیت را شروع کنید.');
  if (!previsitLines().length) throw Error('برای ذخیره درخواست، حداقل یک کالا به سبد اضافه کنید.');
  const button = $('#savePrevisitDraft');
  const idle = button.innerHTML;
  button.disabled = true;
  button.textContent = 'در حال محاسبه قیمت و جوایز…';
  try {
    const validation = await previewNgtPrevisit();
    if (!validation.ok) throw Error(validation.message || 'محاسبه نهایی، ذخیره درخواست را تأیید نکرد.');
    if (validation.credit_control?.allowed === false) throw Error(validation.credit_control?.message || 'کنترل اعتبار، ذخیره درخواست را تأیید نکرد.');
    const payload = previsitSavedRequestPayload();
    button.textContent = 'در حال ذخیره درخواست…';
    const requestId = previsitEditingSavedRequestId;
    const endpoint = `/seller-workspace/previsit/visits/${encodeURIComponent(previsitSession.visit_id)}/saved-requests${requestId ? `/${encodeURIComponent(requestId)}` : ''}`;
    const response = await fetch(endpoint, {
      method: requestId ? 'PUT' : 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload),
    });
    const data = await readJsonResponse(response, 'ذخیره درخواست انجام نشد.');
    if (!response.ok) throw Error(data.detail || 'ذخیره درخواست انجام نشد.');
    previsitEditingSavedRequestId = null;
    closePrevisitSavedRequestReview();
    clearPrevisitWorkingCart();
    await loadPrevisitSavedRequests();
    navigatePrevisitState({section: 'saved-requests'});
    toast(`درخواست شماره ${Number(data.request_number).toLocaleString('fa-IR')} ذخیره شد و سبد خالی شد.`);
    return data;
  } finally {
    button.disabled = false;
    button.innerHTML = idle;
    updatePrevisitSaveRequestButton();
  }
}

function updatePrevisitSaveRequestButton() {
  const button = $('#savePrevisitDraft');
  if (!button) return;
  const saved = previsitSavedRequests.find((item) => item.id === previsitEditingSavedRequestId);
  button.innerHTML = saved
    ? `<span>✓</span><b>ذخیره تغییرات درخواست ${Number(saved.request_number).toLocaleString('fa-IR')}</b><small>پس از ذخیره، سبد خالی می‌شود</small>`
    : '<span>＋</span><b>ذخیره درخواست</b><small>نگهداری پیش‌فاکتور و خالی‌کردن سبد</small>';
}

async function loadPrevisitSavedRequests() {
  if (!previsitSession) return [];
  const response = await fetch(`/seller-workspace/previsit/visits/${encodeURIComponent(previsitSession.visit_id)}/saved-requests`);
  const data = await readJsonResponse(response, 'دریافت درخواست‌های ذخیره‌شده انجام نشد.');
  if (!response.ok) throw Error(data.detail || 'دریافت درخواست‌های ذخیره‌شده انجام نشد.');
  previsitSavedRequests = Array.isArray(data.requests) ? data.requests : [];
  const badge = $('#previsitSavedRequestRailBadge');
  if (badge) badge.textContent = previsitSavedRequests.length
    ? `${previsitSavedRequests.length.toLocaleString('fa-IR')} درخواست`
    : 'بدون درخواست';
  updatePrevisitFinishVisitAction();
  renderPrevisitSavedRequests();
  updatePrevisitSaveRequestButton();
  return previsitSavedRequests;
}

function updatePrevisitFinishVisitAction() {
  const button = $('.previsit-visit-rail [data-previsit-finish-visit]');
  const badge = $('#previsitFinishVisitRailBadge');
  if (!button || !badge) return;
  const count = previsitSavedRequests.length;
  button.disabled = !previsitSession || count < 1;
  button.classList.toggle('is-locked', button.disabled);
  badge.textContent = count
    ? `${count.toLocaleString('fa-IR')} درخواست آماده پایان ویزیت`
    : 'ابتدا یک درخواست ذخیره کنید';
}

function savedRequestProduct(saved, productId) {
  const product = (previsitContext?.products || []).find((item) => String(item.id) === String(productId));
  if (!product) return {};
  const orderType = (previsitContext?.order_types || []).find((item) => item.name === saved.order_type);
  const orderTypeRef = String(orderType?.id || '');
  if (!orderTypeRef) return product;
  return {
    ...product,
    manufacturer_price: Number(product.manufacturer_prices?.[orderTypeRef] || product.manufacturer_price || 0),
    consumer_price: Number(product.consumer_prices?.[orderTypeRef] || product.consumer_price || 0),
  };
}

function savedRequestInvoiceRows(saved, officialGifts = officialPrevisitGiftLines(saved.preview || {})) {
  const official = new Map((saved.preview?.items || []).map((item) => [String(item.product_id), item]));
  const mainRows = (saved.lines || []).map((line) => {
    const item = official.get(String(line.product_id)) || line;
    const product = savedRequestProduct(saved, line.product_id);
    const quantity = Number(item.quantity ?? line.quantity ?? 0);
    const unitPrice = Number(item.unit_price ?? line.unit_price ?? 0);
    const gross = Number(item.gross_amount ?? quantity * unitPrice);
    const discount = Number(item.discount_amount ?? line.discount_amount ?? 0);
    const tax = Number(item.tax_and_charge_amount ?? (Number(item.tax_amount || 0) + Number(item.charge_amount || 0)));
    const net = Number(item.net_amount ?? (gross - discount + tax));
    const units = previsitInvoiceUnitBreakdown(product, quantity);
    const breakdown = item.discount_breakdown || {};
    return {
      title: line.title || product.name || line.product_id,
      product_id: line.product_id,
      quantity,
      cartonQuantity: units.cartonQuantity,
      remainderQuantity: units.remainderQuantity,
      unitsPerCarton: units.unitsPerCarton,
      unitPrice,
      manufacturerPrice: Number(product.manufacturer_price || 0),
      consumerPrice: Number(product.consumer_price || 0),
      gross,
      goods: {percent: Number(breakdown.goods?.percent || 0), amount: Number(breakdown.goods?.amount || 0)},
      volume: {percent: Number(breakdown.volume?.percent || 0), amount: Number(breakdown.volume?.amount || 0)},
      cash: {percent: Number(breakdown.cash?.percent || 0), amount: Number(breakdown.cash?.amount || 0)},
      discount,
      tax,
      net,
      isGift: false,
    };
  });
  const singleParentId = mainRows.length === 1 ? String(mainRows[0].product_id) : '';
  const giftRows = officialGifts.map((gift, index) => {
    const product = savedRequestProduct(saved, gift.product_id);
    const quantity = Number(gift.quantity || 0);
    const unitPrice = Number(gift.unit_price || 0);
    const gross = Number(gift.gross_amount || 0) || Number(gift.discount_amount || 0) || quantity * unitPrice;
    const discount = Number(gift.discount_amount || 0) || gross;
    const units = previsitInvoiceUnitBreakdown(product, quantity);
    return {
      title: `🎁 ${gift.title || product.name || `کالای اشانتیون ${gift.product_id}`}`,
      product_id: gift.product_id,
      parent_product_id: String(gift.parent_product_id || singleParentId),
      quantity,
      cartonQuantity: units.cartonQuantity,
      remainderQuantity: units.remainderQuantity,
      unitsPerCarton: units.unitsPerCarton,
      unitPrice,
      manufacturerPrice: Number(product.manufacturer_price || 0),
      consumerPrice: Number(product.consumer_price || 0),
      gross,
      goods: {percent: 100, amount: discount},
      volume: {percent: 0, amount: 0},
      cash: {percent: 0, amount: 0},
      discount,
      tax: 0,
      net: 0,
      isGift: true,
      giftIndex: index,
    };
  }).filter((row) => row.product_id && row.quantity > 0);
  const result = [];
  const insertedGifts = new Set();
  mainRows.forEach((row) => {
    result.push(row);
    giftRows.forEach((gift) => {
      if (gift.parent_product_id !== String(row.product_id)) return;
      result.push(gift);
      insertedGifts.add(gift.giftIndex);
    });
  });
  giftRows.forEach((gift) => {
    if (!insertedGifts.has(gift.giftIndex)) result.push(gift);
  });
  return result;
}

function savedRequestInvoiceTable(saved, printable = false) {
  const rows = savedRequestInvoiceRows(saved, officialPrevisitGiftLines(saved.preview || {}));
  const billedRows = rows.filter((row) => !row.isGift);
  const totals = saved.preview?.totals || {};
  const sum = (field) => billedRows.reduce((total, row) => total + Number(row[field] || 0), 0);
  const sumDiscount = (category) => billedRows.reduce((total, row) => total + Number(row[category]?.amount || 0), 0);
  const discountCell = (part) => `<b>${Number(part?.percent || 0).toLocaleString('fa-IR', {maximumFractionDigits: 2})}٪</b><small>${previsitMoney(part?.amount || 0)}</small>`;
  const optionalMoney = (value) => Number(value || 0) > 0 ? previsitMoney(value) : '—';
  const gross = Number(totals.gross ?? sum('gross'));
  const discount = Number(totals.discount ?? sum('discount'));
  const tax = Number((totals.tax ?? 0) + (totals.charge ?? 0)) || sum('tax');
  const net = Number(totals.net ?? sum('net'));
  return `<div class="previsit-saved-invoice ${printable ? 'is-printable' : ''}"><header><div><small>پیش‌فاکتور ذخیره‌شده</small><strong>درخواست شماره ${Number(saved.request_number).toLocaleString('fa-IR')}</strong></div><dl><div><dt>نوع درخواست</dt><dd>${esc(saved.order_type || 'ثبت نشده')}</dd></div><div><dt>شرایط پرداخت</dt><dd>${esc(saved.payment_type || 'ثبت نشده')}</dd></div><div><dt>انبار</dt><dd>${esc(saved.warehouse_name || 'ثبت نشده')}</dd></div></dl></header><div class="previsit-saved-invoice-scroll"><table><thead><tr><th>کالا و کد</th><th>تعداد نهایی</th><th>کارتن</th><th>عدد</th><th>تعداد در کارتن</th><th>قیمت پایه / نهایی</th><th>قیمت تولیدکننده</th><th>قیمت مصرف‌کننده</th><th>ناخالص</th><th>تخفیف کالایی</th><th>تخفیف حجمی</th><th>تخفیف نقدی</th><th>مالیات و عوارض</th><th>خالص</th></tr></thead><tbody>${rows.map((row) => `<tr class="${row.isGift ? 'is-gift' : ''}"><td><strong>${esc(row.title)}</strong><small>کد ${esc(row.product_id)}${row.isGift ? ' · اشانتیون' : ''}</small></td><td>${row.quantity.toLocaleString('fa-IR')}</td><td>${formatPrevisitUnitQuantity(row.cartonQuantity)}</td><td>${formatPrevisitUnitQuantity(row.remainderQuantity)}</td><td>${row.unitsPerCarton ? formatPrevisitUnitQuantity(row.unitsPerCarton) : '—'}</td><td>${optionalMoney(row.unitPrice)}</td><td>${optionalMoney(row.manufacturerPrice)}</td><td>${optionalMoney(row.consumerPrice)}</td><td>${previsitMoney(row.gross)}</td><td class="is-discount">${discountCell(row.goods)}</td><td class="is-discount">${discountCell(row.volume)}</td><td class="is-discount">${discountCell(row.cash)}</td><td>${previsitMoney(row.tax)}</td><td>${previsitMoney(row.net)}</td></tr>`).join('')}</tbody><tfoot><tr><th colspan="8">جمع درخواست · تخفیف کل ${previsitMoney(discount)}</th><td>${previsitMoney(gross)}</td><td>${previsitMoney(sumDiscount('goods'))}</td><td>${previsitMoney(sumDiscount('volume'))}</td><td>${previsitMoney(sumDiscount('cash'))}</td><td>${previsitMoney(tax)}</td><td>${previsitMoney(net)}</td></tr></tfoot></table></div></div>`;
}

function renderPrevisitSavedRequests(selectedId = null) {
  const root = $('#previsitSavedRequestsContent');
  if (!root) return;
  root.innerHTML = `<section class="previsit-saved-requests"><header><div><strong>درخواست‌های ذخیره‌شده مشتری</strong><small>هر درخواست مستقل نگهداری می‌شود؛ مشاهده آن خواندنی است و فقط با دکمه «ویرایش» وارد سفارش‌گیری می‌شوید.</small></div><b>${previsitSavedRequests.length.toLocaleString('fa-IR')} درخواست</b></header>${previsitSavedRequests.length ? `<div class="previsit-saved-request-list">${previsitSavedRequests.map((saved) => `<article><div><small>درخواست شماره</small><strong>${Number(saved.request_number).toLocaleString('fa-IR')}</strong><span>${Number(saved.line_count).toLocaleString('fa-IR')} قلم · ${previsitMoney(saved.total_amount)}</span></div><dl><div><dt>نوع</dt><dd>${esc(saved.order_type || '—')}</dd></div><div><dt>انبار</dt><dd>${esc(saved.warehouse_name || '—')}</dd></div></dl><button type="button" data-previsit-saved-request-open="${esc(saved.id)}">مشاهده پیش‌فاکتور</button></article>`).join('')}</div>` : '<div class="previsit-empty-state"><span>▤</span><strong>هنوز درخواستی ذخیره نشده است</strong><small>در پیش‌فاکتور، دکمه «ذخیره درخواست» را بزنید.</small></div>'}</section>`;
}

function openPrevisitSavedRequest(requestId) {
  showPrevisitSavedRequestReview(requestId);
}

function showPrevisitSavedRequestReview(requestId) {
  const saved = previsitSavedRequests.find((item) => item.id === requestId);
  const viewer = $('#previsitSavedRequestReview');
  const savedRoot = $('#previsitSavedRequestsContent');
  if (!saved || !viewer || !savedRoot) return;
  previsitViewingSavedRequestId = saved.id;
  viewer.innerHTML = `<header class="previsit-saved-review-heading"><div><small>پیش‌نمایش خواندنی درخواست ذخیره‌شده</small><strong>پیش‌فاکتور درخواست ${Number(saved.request_number).toLocaleString('fa-IR')}</strong></div><div class="previsit-saved-request-actions"><button type="button" data-previsit-saved-request-back>بازگشت به درخواست‌ها</button><button type="button" data-previsit-saved-request-edit="${esc(saved.id)}">✎ ویرایش</button><button type="button" data-previsit-saved-request-pdf="${esc(saved.id)}">⇩ پیش‌نمایش و ارسال PDF</button></div></header>${savedRequestInvoiceTable(saved)}`;
  savedRoot.hidden = true;
  viewer.hidden = false;
  viewer.scrollIntoView({block: 'start'});
}

function closePrevisitSavedRequestReview() {
  previsitViewingSavedRequestId = null;
  const viewer = $('#previsitSavedRequestReview');
  const savedRoot = $('#previsitSavedRequestsContent');
  if (viewer) {
    viewer.hidden = true;
    viewer.innerHTML = '';
  }
  if (savedRoot) savedRoot.hidden = false;
}

function editPrevisitSavedRequest(requestId) {
  const saved = previsitSavedRequests.find((item) => item.id === requestId);
  if (!saved) return;
  if (previsitLines().length && !window.confirm('سبد فعلی با درخواست ذخیره‌شده جایگزین شود؟')) return;
  closePrevisitSavedRequestReview();
  clearPrevisitWorkingCart();
  const payment = (previsitContext?.payment_types || []).find((item) => item.name === saved.payment_type);
  const order = (previsitContext?.order_types || []).find((item) => item.name === saved.order_type);
  if (payment) $('#previsitPaymentType').value = String(payment.id);
  if (order) $('#previsitOrderType').value = String(order.id);
  if (saved.warehouse_ref && (previsitContext?.warehouses || []).some((item) => Number(item.ref) === Number(saved.warehouse_ref))) $('#previsitWarehouse').value = String(saved.warehouse_ref);
  (saved.lines || []).forEach(addPrevisitLine);
  previsitEditingSavedRequestId = saved.id;
  if (saved.preview?.items?.length) {
    previsitPreview = saved.preview;
    renderNgtPreview(saved.preview);
  }
  updatePrevisitOrderContextSummary();
  updatePrevisitSaveRequestButton();
  navigatePrevisitState({section: 'order', activeView: 'cart'});
  toast(`درخواست شماره ${Number(saved.request_number).toLocaleString('fa-IR')} برای ویرایش باز شد.`);
}

function printPrevisitSavedRequest(requestId) {
  const saved = previsitSavedRequests.find((item) => item.id === requestId);
  if (!saved) return;
  const customer = previsitWorkspace?.customer || {};
  const customerName = customer.store_name || customer.name || customer.full_name || customer.id || 'مشتری';
  const title = `پیش‌فاکتور ${Number(saved.request_number).toLocaleString('fa-IR')}`;
  const printableHtml = `<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8"><title>${esc(title)}</title><style>*{box-sizing:border-box}body{font-family:Tahoma,Arial,sans-serif;margin:18px;color:#18352c}.print-actions{display:flex;justify-content:flex-start;gap:8px;margin-bottom:10px}.print-actions button{padding:8px 20px;border:1px solid #176f56;border-radius:8px;background:#fff;color:#176f56;font:700 12px Tahoma;cursor:pointer}.print-actions #printPdf{background:#176f56;color:#fff}.customer{margin-bottom:12px;padding:9px 11px;border:1px solid #bfd6cd;border-radius:9px}.customer b{display:block;font-size:13px}.customer span{font-size:8px}.previsit-saved-invoice>header{display:flex;justify-content:space-between;gap:12px;margin-bottom:9px}.previsit-saved-invoice>header>div{display:grid;gap:2px}.previsit-saved-invoice>header strong{font-size:12px}.previsit-saved-invoice dl{display:flex;gap:7px;margin:0}.previsit-saved-invoice dl>div{padding:5px 7px;background:#eef6f3;border-radius:6px}.previsit-saved-invoice dt{font-size:6px;color:#687b74}.previsit-saved-invoice dd{margin:0;font-size:7px;font-weight:bold}.previsit-saved-invoice-scroll{margin-top:8px}table{width:100%;table-layout:fixed;border-collapse:collapse;font-size:5.8px}th,td{padding:4px 2px;border:1px solid #ccdcd6;text-align:center;vertical-align:middle;overflow-wrap:anywhere}thead th,tfoot th,tfoot td{background:#e8f4ef;font-weight:900}thead th:first-child{width:16%}tbody td:first-child{text-align:right}tbody td:first-child strong,tbody td:first-child small{display:block}tbody td:first-child small,.is-discount small{margin-top:2px;font-size:5px;color:#64766f}.is-discount b{display:block}.is-gift{background:#f0faf5}.is-gift td:first-child strong{color:#0b7656}@media print{.print-actions{display:none!important}body{margin:0}}@page{size:A4 landscape;margin:7mm}</style></head><body><div class="print-actions"><button id="printPdf" type="button">ذخیره یا ارسال PDF</button><button id="printClose" type="button">بستن پیش‌نمایش</button></div><section class="customer"><small>مشتری</small><b>${esc(customerName)}</b><span>${esc(customer.code || customer.customer_code || '')} ${esc(customer.address || '')}</span></section>${savedRequestInvoiceTable(saved, true)}</body></html>`;
  if (isNeginAndroidApp && typeof window.NeginAndroid?.printHtml === 'function') {
    try {
      if (window.NeginAndroid.printHtml(title, printableHtml)) {
        toast('پنجره ذخیره PDF باز شد.');
        return;
      }
    } catch (_) {}
  }
  const printWindow = window.open('', '_blank');
  if (!printWindow) return toast('برای ساخت PDF، اجازه بازشدن پنجره جدید را فعال کنید.');
  printWindow.opener = null;
  printWindow.document.write(printableHtml);
  printWindow.document.close();
  const closePrintWindow = () => {
    if (!printWindow.closed) printWindow.close();
  };
  printWindow.document.getElementById('printPdf')?.addEventListener('click', () => printWindow.print());
  printWindow.document.getElementById('printClose')?.addEventListener('click', closePrintWindow);
  printWindow.addEventListener('afterprint', closePrintWindow, {once: true});
  printWindow.focus();
}

async function returnToRouteCustomerList(routeId, routeTitle) {
  previsitPanel.hidden = true;
  sellerWorkspacePanel.hidden = true;
  customerProfilePanel.hidden = true;
  routeMapPanel.hidden = false;
  const current = appHistoryState();
  if (current?.view === 'previsit') {
    history.replaceState({...current, view: 'route-map', detail: {pathId: String(routeId), title: String(routeTitle || '')}}, '', location.href);
  }
  await openRouteMap(routeId, routeTitle || 'مسیر روز');
  setRouteDayActiveAction('customers');
}

async function completePrevisit(outcome, reasonId = null) {
  if (!previsitSession) throw Error('ویزیت فعالی برای پایان‌دادن وجود ندارد.');
  const routeId = String(previsitSession.route_id || $('#previsitRoute')?.value || '');
  const customerId = String(previsitSession.customer_id || $('#previsitCustomer')?.value || '');
  const routeTitle = String($('#previsitRoute')?.selectedOptions?.[0]?.textContent || 'مسیر روز').trim();
  const savedRequestCount = previsitSavedRequests.length;
  if (outcome === 'order' && savedRequestCount < 1) {
    throw Error('ابتدا حداقل یک درخواست را با محاسبه نهایی ذخیره کنید.');
  }
  if (outcome !== 'order') await savePrevisitDraft();
  const needsPosition = Boolean(previsitPolicy?.controls?.enforced);
  const position = needsPosition ? await currentCoordinates({maximumAge: 0, timeout: 12000}) : null;
  if (needsPosition && !position) throw Error('برای پایان ویزیت، دسترسی موقعیت دستگاه را روشن کنید.');
  const response = await fetch(`/seller-workspace/previsit/visits/${encodeURIComponent(previsitSession.visit_id)}/complete`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({
    outcome,
    reason_id: reasonId,
    latitude: position?.latitude ?? null,
    longitude: position?.longitude ?? null,
    accuracy: position?.accuracy ?? null,
  })});
  const data = await response.json();
  if (!response.ok) throw Error(data.detail || '\u067e\u0627\u06cc\u0627\u0646 \u0648\u06cc\u0632\u06cc\u062a \u0627\u0646\u062c\u0627\u0645 \u0646\u0634\u062f.');
  updateRouteCustomerResolution(customerId, outcome, savedRequestCount);
  previsitSession = null;
  stopPrevisitVisitTimer();
  previsitContext = null;
  previsitWorkspace = null;
  previsitPreview = null;
  previsitPolicy = null;
  previsitSavedRequests = [];
  previsitEditingSavedRequestId = null;
  previsitViewingSavedRequestId = null;
  $('#previsitCart').hidden = true;
  $('#previsitForm').classList.remove('is-visit-active');
  $('#previsitOutcomeDialog').close();
  toast(outcome === 'order' ? 'ویزیت با درخواست‌های ذخیره‌شده پایان یافت.' : 'عدم سفارش مشتری ثبت شد.');
  await returnToRouteCustomerList(routeId, routeTitle);
}

function openPrevisitOutcome(outcome) {
  if (!previsitSession) return toast('ابتدا ویزیت را شروع کنید.');
  const reasons = previsitPolicy?.reasons?.[outcome] || [];
  if (!reasons.length) return toast('دلیل فعالی برای این نتیجه تعریف نشده است.');
  pendingPrevisitOutcome = outcome;
  $('#previsitOutcomeTitle').textContent = outcome === 'no_visit' ? 'ثبت عدم ویزیت مشتری' : 'ثبت عدم سفارش مشتری';
  $('#previsitOutcomeHint').textContent = 'فقط دلایل فعال و قابل نمایش پذیرفته می‌شوند.';
  $('#previsitOutcomeReason').innerHTML = '<option value="">انتخاب دلیل</option>' + reasons.map((reason) => `<option value="${esc(reason.id)}">${esc(reason.title)}</option>`).join('');
  $('#previsitOutcomeDialog').showModal();
}

// Mobile-first production catalogue. These later declarations intentionally
// Replace the first pre-visit renderer while keeping the proven pricing preview.
function prepareNgtPrevisitUi() {
  const cart = $('#previsitCart');
  if (cart.dataset.ngtUi === '2') return;
  cart.dataset.ngtUi = '2';
  cart.innerHTML = `
    <header class="previsit-cart-header previsit-customer-sticky-header"><section id="previsitCustomerSummary" class="previsit-customer-summary" aria-live="polite"><div class="previsit-customer-header-copy"><span class="previsit-eyebrow">مشتری فعال این ویزیت</span><h3>در حال دریافت اطلاعات مشتری…</h3><p>اطلاعات معتبر مشتری از مسیر جاری دریافت می‌شود.</p></div></section><span id="previsitContextStatus" class="previsit-status" hidden></span></header>
    <section id="previsitOrderAssistantPanel" class="previsit-order-assistant" aria-labelledby="previsitOrderAssistantTitle"><div><strong id="previsitOrderAssistantTitle">دستیار سفارش</strong><small>مثال: ۵ تا خمیر دندان ضد زردی و ۱۰ تا خمیر دندان لمینت میسویک بزن</small></div><label><span class="sr-only">دستور سفارش</span><input id="previsitOrderCommand" type="text" enterkeyhint="send" placeholder="کالا و تعداد را بنویسید یا بگویید"></label><button id="recordPrevisitOrderCommand" type="button" aria-pressed="false">🎙 گفتن دستور</button><button id="runPrevisitOrderCommand" type="button">افزودن هوشمند</button><div id="previsitOrderAssistantResult" class="previsit-order-assistant-result" aria-live="polite" hidden></div></section>
    <section id="previsitOrderConditionsPanel" class="previsit-order-conditions previsit-order-conditions-inline" aria-label="تنظیمات مستقیم سفارش"><div class="previsit-context-grid"><label><span>نوع درخواست</span><select id="previsitOrderType"></select></label><label><span>انبار</span><select id="previsitWarehouse"></select></label><label><span>شرایط پرداخت</span><select id="previsitPaymentType"></select></label></div></section>
    <section id="previsitCatalogView" class="previsit-catalog-view">
      <div class="previsit-catalog-toolbar">
        <label class="previsit-search-field"><span>\u062c\u0633\u062a\u200c\u0648\u062c\u0648\u06cc \u06a9\u0627\u0644\u0627</span><input id="previsitProductSearch" type="search" inputmode="search" placeholder="\u0646\u0627\u0645\u060c \u06a9\u062f\u060c \u0628\u0627\u0631\u06a9\u062f \u06cc\u0627 \u0628\u0631\u0646\u062f"></label>
        <label><span>\u0628\u0631\u0646\u062f</span><select id="previsitBrandFilter"><option value="">\u0647\u0645\u0647 \u0628\u0631\u0646\u062f\u0647\u0627</option></select></label>
        <label><span>\u06af\u0631\u0648\u0647 \u06a9\u0627\u0644\u0627</span><select id="previsitGroupFilter"><option value="">\u0647\u0645\u0647 \u06af\u0631\u0648\u0647\u200c\u0647\u0627</option></select></label>
        <label><span>\u0645\u0631\u062a\u0628\u200c\u0633\u0627\u0632\u06cc</span><select id="previsitSort"><option value="code">\u0628\u0631\u0646\u062f\u060c \u06af\u0631\u0648\u0647\u060c \u06a9\u062f \u06a9\u0627\u0644\u0627</option><option value="stock_desc">\u0628\u0631\u0646\u062f\u060c \u06af\u0631\u0648\u0647\u060c \u0645\u0648\u062c\u0648\u062f\u06cc \u0628\u06cc\u0634\u062a\u0631</option><option value="price_asc">\u0628\u0631\u0646\u062f\u060c \u06af\u0631\u0648\u0647\u060c \u0642\u06cc\u0645\u062a \u06a9\u0645\u062a\u0631</option><option value="price_desc">\u0628\u0631\u0646\u062f\u060c \u06af\u0631\u0648\u0647\u060c \u0642\u06cc\u0645\u062a \u0628\u06cc\u0634\u062a\u0631</option></select></label>
        <button id="previsitStockToggle" type="button" class="is-active" aria-pressed="true">\u0641\u0642\u0637 \u0645\u0648\u062c\u0648\u062f</button>
      </div>
      <div class="previsit-catalog-meta"><strong id="previsitCatalogCount">\u06f0 \u06a9\u0627\u0644\u0627</strong><button id="previsitTableMode" type="button">\u26f6 \u062d\u0627\u0644\u062a \u0645\u06cc\u0632 \u0645\u0634\u062a\u0631\u06cc</button></div>
      <div id="previsitCatalogGrid" class="previsit-catalog-grid" aria-live="polite"></div>
      <div class="previsit-legacy-picker" hidden><select id="previsitProductPicker"><option value="">\u0627\u0646\u062a\u062e\u0627\u0628 \u06a9\u0627\u0644\u0627</option></select><input id="previsitNewQuantity" type="number" min="0.001" step="any" value="1"><button id="addPrevisitLine" type="button">\u0627\u0641\u0632\u0648\u062f\u0646 \u0628\u0647 \u0633\u0628\u062f</button></div>
    </section>
    <section id="previsitCartView" class="previsit-cart-view" hidden>
      <header class="previsit-section-title"><div><strong>\u067e\u06cc\u0634\u200c\u0641\u0627\u06a9\u062a\u0648\u0631 \u0645\u0634\u062a\u0631\u06cc</strong><small>\u062a\u062e\u0641\u06cc\u0641 \u06a9\u0627\u0644\u0627\u06cc\u06cc\u060c \u062d\u062c\u0645\u06cc \u0648 \u0646\u0642\u062f\u06cc \u0647\u0631 \u0631\u062f\u06cc\u0641 \u062c\u062f\u0627 \u0646\u0645\u0627\u06cc\u0634 \u062f\u0627\u062f\u0647 \u0645\u06cc\u200c\u0634\u0648\u062f.</small></div><span id="previsitCartCount">\u06f0 \u0631\u062f\u06cc\u0641</span></header>
      <div id="previsitCartEmpty" class="previsit-cart-empty"><span>\ud83d\uded2</span><strong>\u0633\u0628\u062f \u0647\u0646\u0648\u0632 \u062e\u0627\u0644\u06cc \u0627\u0633\u062a</strong><small>\u0627\u0632 \u06a9\u0627\u062a\u0627\u0644\u0648\u06af \u06a9\u0627\u0644\u0627 \u0627\u0646\u062a\u062e\u0627\u0628 \u06a9\u0646\u06cc\u062f.</small></div>
      <div class="previsit-invoice-scroll"><div class="previsit-invoice-head" aria-hidden="true"><span>\u06a9\u0627\u0644\u0627</span><span>\u062a\u0639\u062f\u0627\u062f \u0646\u0647\u0627\u06cc\u06cc</span><span>\u06a9\u0627\u0631\u062a\u0646</span><span>\u0639\u062f\u062f</span><span>\u062a\u0639\u062f\u0627\u062f \u062f\u0631 \u06a9\u0627\u0631\u062a\u0646</span><span>\u0642\u06cc\u0645\u062a \u0648\u0627\u062d\u062f</span><span>\u0646\u0627\u062e\u0627\u0644\u0635</span><span>\u06a9\u0627\u0644\u0627\u06cc\u06cc<br><small>\u062f\u0631\u0635\u062f / \u0645\u0628\u0644\u063a</small></span><span>\u062d\u062c\u0645\u06cc<br><small>\u062f\u0631\u0635\u062f / \u0645\u0628\u0644\u063a</small></span><span>\u0646\u0642\u062f\u06cc<br><small>\u062f\u0631\u0635\u062f / \u0645\u0628\u0644\u063a</small></span><span>\u0645\u0627\u0644\u06cc\u0627\u062a \u0648 \u0639\u0648\u0627\u0631\u0636</span><span>\u062e\u0627\u0644\u0635</span><span></span></div><div id="previsitLines" class="previsit-lines"></div></div>
      <button id="previewPrevisit" type="button" class="previsit-preview-button">محاسبه قیمت، تخفیف و جوایز</button>
      <section id="previsitPreviewResult" class="previsit-preview-result" hidden aria-live="polite"></section>
      <div class="previsit-save-request-bar"><button id="savePrevisitDraft" type="button" class="previsit-invoice-save-request">\u0630\u062e\u06cc\u0631\u0647 \u062f\u0631\u062e\u0648\u0627\u0633\u062a</button><small>درخواست در منوی «درخواست‌های ذخیره‌شده» نگهداری می‌شود و سبد پس از ذخیره خالی خواهد شد.</small></div>
      <div class="previsit-order-actions" hidden><button id="completePrevisitOrder" type="button" disabled>\u067e\u0627\u06cc\u0627\u0646 \u0648\u06cc\u0632\u06cc\u062a</button></div>
    </section>
    <nav class="previsit-mobile-dock" aria-label="\u06a9\u0627\u062a\u0627\u0644\u0648\u06af \u0648 \u0633\u0628\u062f \u0633\u0641\u0627\u0631\u0634"><button type="button" data-previsit-view="catalog" class="is-active"><span>\u25a6</span><b>\u06a9\u0627\u062a\u0627\u0644\u0648\u06af</b><small>\u0627\u062f\u0627\u0645\u0647 \u0627\u0646\u062a\u062e\u0627\u0628 \u06a9\u0627\u0644\u0627</small></button><button type="button" data-previsit-view="cart" class="previsit-dock-cart"><span>\ud83d\uded2</span><b>\u0645\u0634\u0627\u0647\u062f\u0647 \u0633\u0628\u062f</b><span class="previsit-dock-metrics"><em><i id="previsitDockCount">\u06f0 \u0642\u0644\u0645</i><i id="previsitDockQuantity">\u06f0 \u0639\u062f\u062f</i><i id="previsitDockGiftCount" hidden></i></em><small><label id="previsitDockTotalLabel">\u0646\u0627\u062e\u0627\u0644\u0635 \u0641\u0639\u0644\u06cc</label><strong id="previsitDockTotal">\u06f0 \u0631\u06cc\u0627\u0644</strong></small></span></button></nav>
    <button id="previsitFloatingVoice" class="previsit-floating-voice" type="button" hidden aria-label="گفتن دستور سفارش" aria-pressed="false"><span aria-hidden="true">🎙</span><b data-voice-label>صوتی</b></button>
    <section id="previsitTableOverlay" class="previsit-table-overlay" hidden aria-label="\u06a9\u0627\u062a\u0627\u0644\u0648\u06af \u0645\u06cc\u0632 \u0645\u0634\u062a\u0631\u06cc">
      <div class="previsit-table-customer"><div id="previsitTableCustomer"></div></div>
      <div class="previsit-table-seller"><header><button id="previsitTableClose" type="button">\u2715 \u0628\u0633\u062a\u0646</button><strong id="previsitTablePosition"></strong><button id="previsitTableCart" type="button">\ud83d\uded2 \u0633\u0628\u062f</button></header><div id="previsitTableSeller"></div><div class="previsit-table-controls"><button id="previsitTablePrevious" type="button" aria-label="\u06a9\u0627\u0644\u0627\u06cc \u0642\u0628\u0644\u06cc">\u2192</button><button id="previsitTableMinus" type="button" aria-label="\u06a9\u0645 \u06a9\u0631\u062f\u0646">\u2212</button><output id="previsitTableQuantity">\u06f0</output><button id="previsitTablePlus" type="button" aria-label="\u0627\u0636\u0627\u0641\u0647 \u06a9\u0631\u062f\u0646">+</button><button id="previsitTableNext" type="button" aria-label="\u06a9\u0627\u0644\u0627\u06cc \u0628\u0639\u062f\u06cc">\u2190</button></div></div>
    </section>`;
  const tableOverlay = $('#previsitTableOverlay');
  const visitShell = document.createElement('div');
  visitShell.className = 'previsit-visit-shell';
  visitShell.innerHTML = `
    <aside class="previsit-visit-rail" aria-label="منوی ویزیت مشتری">
      <button id="previsitVisitMenuToggle" class="previsit-visit-menu-toggle" type="button" aria-label="باز کردن منوی مشتری" title="منوی مشتری" aria-expanded="false" aria-controls="previsitVisitRailPanel"><span aria-hidden="true">⋮</span><b id="previsitVisitMenuCurrent" class="sr-only">اطلاعات مشتری</b></button>
      <div id="previsitVisitRailPanel" class="previsit-visit-rail-panel">
      <header class="previsit-visit-drawer-head"><strong>منوی مشتری</strong><button id="previsitVisitMenuClose" type="button" aria-label="بستن منوی مشتری">×</button></header>
      <div id="previsitVisitIdentity" class="previsit-visit-identity"><span class="previsit-identity-mark">م</span><div><strong>مشتری مسیر روز</strong><small>در حال دریافت اطلاعات…</small></div></div>
      <nav>
        <button type="button" data-previsit-section="profile" class="is-active" aria-current="page"><span>♙</span><b>اطلاعات مشتری</b><small>مشخصات، ویرایش و ثبت موقعیت</small></button>
        <button type="button" data-previsit-section="order"><span>＋</span><b>سفارش‌گیری</b><small>لیست کالا، صوت و کاتالوگ گروهی</small></button>
        <button type="button" data-previsit-finish-visit disabled><span>✓</span><b>پایان ویزیت</b><small id="previsitFinishVisitRailBadge">ابتدا یک درخواست ذخیره کنید</small></button>
        <button type="button" data-previsit-outcome="no_order"><span>×</span><b>عدم سفارش</b><small id="previsitNoOrderRailBadge">انتخاب دلیل ثبت‌شده</small></button>
        <button type="button" data-previsit-section="saved-requests"><span>▥</span><b>درخواست‌های ذخیره‌شده</b><small id="previsitSavedRequestRailBadge">در حال دریافت</small></button>
        <button type="button" data-previsit-section="invoices"><span>▤</span><b>فاکتورهای باز</b><small id="previsitInvoiceRailBadge">در حال دریافت</small></button>
        <button type="button" data-previsit-section="cardex"><span>◫</span><b>اطلاعات مالی</b><small>مانده، اعتبار و چک‌ها</small></button>
        <button type="button" data-previsit-section="returned-cheques"><span>!</span><b>چک‌های برگشتی</b><small id="previsitReturnedChequeRailBadge">در حال دریافت</small></button>
        <button type="button" data-previsit-section="history"><span>◷</span><b>سابقه خرید</b><small>رفتار ۱۲ ماهه</small></button>
        <button type="button" data-previsit-section="interests"><span>♡</span><b>علایق مشتری</b><small>برندها و فرصت فروش</small></button>
      </nav>
      <div class="previsit-rail-status"><i></i><span>ویزیت فعال</span><time id="previsitVisitTimer" datetime="PT0S">۰۰:۰۰</time><small>ذخیره پیش‌نویس امن است</small></div>
      </div>
    </aside>
    <button id="previsitVisitMenuBackdrop" class="previsit-visit-menu-backdrop" type="button" aria-label="بستن منوی مشتری" hidden></button>
    <dialog id="previsitLocationPickerDialog" class="previsit-location-picker-dialog" aria-labelledby="previsitLocationPickerTitle">
      <section class="previsit-location-picker-shell">
        <header><div><small>ثبت موقعیت مشتری</small><strong id="previsitLocationPickerTitle">نقطه دقیق را روی نقشه انتخاب کنید</strong></div><button id="previsitLocationPickerClose" type="button" aria-label="بستن نقشه">×</button></header>
        <div id="previsitLocationPickerMap" class="previsit-location-picker-map" aria-label="نقشه انتخاب موقعیت مشتری"></div>
        <footer><div><b id="previsitLocationPickerCoordinates">در حال دریافت موقعیت…</b><small id="previsitLocationPickerStatus">می‌توانید نشانگر را جابه‌جا کنید یا روی نقشه بزنید.</small></div><button id="previsitLocationPickerCurrent" type="button" class="dialog-secondary">⌖ موقعیت فعلی من</button><button type="button" data-previsit-location-confirm>ثبت این نقطه</button></footer>
      </section>
    </dialog>
    <main class="previsit-workspace-main">
      <section class="previsit-order-workspace" data-previsit-section-panel="order" hidden></section>
      <section class="previsit-intelligence-panel" data-previsit-section-panel="saved-requests" hidden><div id="previsitSavedRequestsContent" class="previsit-workspace-content previsit-loading-card">در حال دریافت درخواست‌های ذخیره‌شده…</div><section id="previsitSavedRequestReview" class="previsit-saved-request-review" hidden></section></section>
      <section class="previsit-intelligence-panel" data-previsit-section-panel="invoices" hidden><div id="previsitInvoicesContent" class="previsit-workspace-content previsit-loading-card">در حال دریافت فاکتورهای باز…</div></section>
      <section class="previsit-intelligence-panel" data-previsit-section-panel="cardex" hidden><div id="previsitCardexContent" class="previsit-workspace-content previsit-loading-card">در حال دریافت مانده و اعتبار…</div></section>
      <section class="previsit-intelligence-panel" data-previsit-section-panel="returned-cheques" hidden><div id="previsitReturnedChequesContent" class="previsit-workspace-content previsit-loading-card">در حال دریافت سابقه چک‌های برگشتی…</div></section>
      <section class="previsit-intelligence-panel" data-previsit-section-panel="history" hidden><div id="previsitHistoryContent" class="previsit-workspace-content previsit-loading-card">در حال دریافت سابقه خرید…</div></section>
      <section class="previsit-intelligence-panel" data-previsit-section-panel="interests" hidden><div id="previsitInterestsContent" class="previsit-workspace-content previsit-loading-card">در حال تحلیل برندهای مشتری…</div></section>
      <section class="previsit-intelligence-panel" data-previsit-section-panel="profile"><div id="previsitProfileContent" class="previsit-workspace-content previsit-loading-card">در حال دریافت اطلاعات مشتری…</div></section>
    </main>`;
  cart.insertBefore(visitShell, tableOverlay);
  updatePrevisitSaveRequestButton();
  const orderWorkspace = visitShell.querySelector('[data-previsit-section-panel="order"]');
  const assistant = cart.querySelector('.previsit-order-assistant');
  const orderConditions = cart.querySelector('.previsit-order-conditions');
  const orderCommon = document.createElement('section');
  orderCommon.id = 'previsitOrderCommon';
  orderCommon.className = 'previsit-order-common';
  orderCommon.insertAdjacentHTML('beforeend', '<header class="previsit-order-heading"><div><strong>ثبت سفارش این ویزیت</strong><small>لیست کالا و کاتالوگ گروهی یک سبد مشترک دارند.</small></div><div class="previsit-order-mode-switch" role="tablist" aria-label="روش سفارش‌گیری"><button type="button" class="is-active" data-previsit-order-mode="list" role="tab" aria-selected="true">☷ لیست کالا</button><button type="button" data-previsit-order-mode="grouped" role="tab" aria-selected="false">▦ کاتالوگ گروهی</button></div></header>');
  orderConditions.hidden = false;
  assistant.hidden = true;
  orderCommon.append(orderConditions, assistant);
  const catalogView = $('#previsitCatalogView');
  const catalogToolbar = catalogView.querySelector('.previsit-catalog-toolbar');
  const catalogMeta = catalogView.querySelector('.previsit-catalog-meta');
  const tableModeButton = catalogMeta.querySelector('#previsitTableMode');
  const catalogQuickbar = document.createElement('div');
  catalogQuickbar.className = 'previsit-catalog-quickbar';
  catalogQuickbar.innerHTML = '<button id="previsitCatalogFilterToggle" type="button" aria-expanded="false" aria-controls="previsitCatalogFilterPanel"><span aria-hidden="true">☷</span> فیلترها</button>';
  catalogQuickbar.prepend(catalogToolbar.querySelector('.previsit-search-field'));
  catalogQuickbar.append(catalogMeta, catalogQuickbar.querySelector('#previsitCatalogFilterToggle'));
  catalogToolbar.id = 'previsitCatalogFilterPanel';
  catalogToolbar.classList.add('previsit-catalog-filter-panel');
  catalogToolbar.append(tableModeButton);
  catalogToolbar.hidden = true;
  catalogView.prepend(catalogQuickbar);
  const cartView = $('#previsitCartView');
  const mobileDock = cart.querySelector('.previsit-mobile-dock');
  const quickView = document.createElement('section');
  quickView.id = 'previsitQuickOrderView';
  quickView.className = 'previsit-quick-order-view';
  quickView.hidden = true;
  const legacyPicker = cart.querySelector('.previsit-legacy-picker');
  legacyPicker.hidden = false;
  legacyPicker.className = 'previsit-quick-picker';
  legacyPicker.insertAdjacentHTML('afterbegin', '<header><strong>ثبت سریع از لیست کالا</strong><small>ابتدا برند را انتخاب کنید؛ سپس فقط گروه‌های کالای همان برند نمایش داده می‌شوند.</small></header><label class="previsit-quick-search-label">جست‌وجو<input id="previsitQuickSearch" type="search" placeholder="نام، کد یا برند کالا"></label><label>برند<select id="previsitQuickBrandFilter"><option value="">همه برندها</option></select></label><label>گروه کالا<select id="previsitQuickGroupFilter"><option value="">همه گروه‌ها</option></select></label>');
  $('#previsitProductPicker').setAttribute('aria-label', 'انتخاب کالا از لیست');
  $('#previsitNewQuantity').setAttribute('aria-label', 'تعداد کالا');
  quickView.append(legacyPicker);
  const listView = document.createElement('section');
  listView.id = 'previsitProductListView';
  listView.className = `previsit-product-list-view${previsitListCompact ? ' is-compact' : ''}`;
  listView.hidden = true;
  listView.innerHTML = `
    <section id="previsitListControls" class="previsit-list-sticky-controls" aria-label="جست‌وجو و فیلتر ثابت کالا"><header class="previsit-list-heading"><div><strong>سفارش‌گیری از لیست کالا</strong><small>فیلتر برند و گروه با شروع اسکرول جمع می‌شود.</small></div><label><span class="sr-only">جست‌وجوی کالا</span><input id="previsitListSearch" type="search" inputmode="search" placeholder="نام، کد یا بارکد کالا"></label></header><div id="previsitListHierarchy" class="previsit-list-hierarchy previsit-list-hierarchy-inline"><div><strong>برندها</strong><nav id="previsitListBrands" aria-label="فیلتر برند"></nav></div><div><strong>گروه‌ها</strong><nav id="previsitListGroups" aria-label="فیلتر گروه کالا"></nav></div></div><div class="previsit-list-meta"><strong id="previsitListCount">۰ کالا</strong><div class="previsit-list-view-actions"><button id="previsitListFiltersToggle" type="button" aria-expanded="true" aria-controls="previsitListHierarchy">جمع‌کردن فیلترها</button><button id="previsitListDensityToggle" type="button" aria-pressed="${previsitListCompact}">${previsitListCompact ? '↕ نمایش باز' : '↕ نمایش فشرده'}</button><button id="previsitListStockToggle" type="button" class="is-active" aria-pressed="true">✓ فقط کالاهای موجود</button></div></div></section>
    <div id="previsitListProducts" class="previsit-list-products" aria-live="polite"></div>`;
  const groupedView = document.createElement('section');
  groupedView.id = 'previsitGroupedCatalogView';
  groupedView.className = 'previsit-grouped-catalog-view';
  groupedView.hidden = true;
  groupedView.innerHTML = `
    <header class="previsit-grouped-heading"><div><strong>کاتالوگ گروهی</strong><small>هر تصویر شامل چند کالای مرتبط است؛ تعداد هر کالا را همان زیر تصویر ثبت کنید.</small></div><div><button id="previsitGroupedDownload" type="button">⇩ دانلود تصاویر تبلت</button><button id="previsitGroupedTableMode" type="button">⛶ میز مشتری</button></div></header>
    <div class="previsit-grouped-toolbar"><label><span>جست‌وجو</span><input id="previsitGroupedSearch" type="search" inputmode="search" placeholder="نام کاتالوگ، کالا یا برند"></label><label><span>برند</span><select id="previsitGroupedBrand"><option value="">همه برندها</option></select></label><label><span>گروه کالا</span><select id="previsitGroupedGroup"><option value="">همه گروه‌ها</option></select></label><button id="previsitGroupedStockToggle" type="button" class="is-active" aria-pressed="true">✓ فقط کالاهای موجود</button></div>
    <div class="previsit-grouped-meta"><strong id="previsitGroupedCount">۰ تصویر</strong><span id="previsitGroupedDownloadStatus" aria-live="polite"></span></div>
    <div id="previsitGroupedCatalogs" class="previsit-grouped-catalogs" aria-live="polite"></div>`;
  catalogView.hidden = true;
  quickView.hidden = true;
  orderWorkspace.append(orderCommon, listView, groupedView, catalogView, quickView, cartView, mobileDock);
  if ('ResizeObserver' in window) {
    previsitStickyObserver = new ResizeObserver(updatePrevisitOrderStickyTop);
    previsitStickyObserver.observe(cart.querySelector('.previsit-cart-header'));
  }
  window.addEventListener('resize', updatePrevisitOrderStickyTop, {passive: true});
  requestAnimationFrame(updatePrevisitOrderStickyTop);
  $('#previsitVisitMenuToggle').addEventListener('click', () => togglePrevisitVisitMenu());
  $('#previsitVisitMenuClose').addEventListener('click', () => togglePrevisitVisitMenu(false));
  $('#previsitVisitMenuBackdrop').addEventListener('click', () => togglePrevisitVisitMenu(false));
  $('#previsitLocationPickerClose').addEventListener('click', closePrevisitLocationPicker);
  $('#previsitLocationPickerCurrent').addEventListener('click', () => void locatePrevisitCustomerOnMap());
  $('[data-previsit-location-confirm]').addEventListener('click', confirmPrevisitLocationPicker);
  $('#previsitSavedRequestsContent').addEventListener('click', (event) => {
    const open = event.target.closest('[data-previsit-saved-request-open]');
    if (open) openPrevisitSavedRequest(open.dataset.previsitSavedRequestOpen);
  });
  $('#previsitSavedRequestReview').addEventListener('click', (event) => {
    const edit = event.target.closest('[data-previsit-saved-request-edit]');
    const pdf = event.target.closest('[data-previsit-saved-request-pdf]');
    if (edit) editPrevisitSavedRequest(edit.dataset.previsitSavedRequestEdit);
    else if (pdf) printPrevisitSavedRequest(pdf.dataset.previsitSavedRequestPdf);
    else if (event.target.closest('[data-previsit-saved-request-back]')) {
      closePrevisitSavedRequestReview();
      $('#previsitSavedRequestsContent')?.scrollIntoView({block: 'start'});
    }
  });
  $$('[data-previsit-order-panel]').forEach((button) => button.addEventListener('click', () => togglePrevisitOrderPanel(button.dataset.previsitOrderPanel)));
  $('#previsitCatalogFilterToggle').addEventListener('click', () => togglePrevisitCatalogFilters());
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && $('.previsit-visit-rail')?.classList.contains('is-open')) togglePrevisitVisitMenu(false);
  });
  const invoiceScroll = cartView.querySelector('.previsit-invoice-scroll');
  let invoiceScrollSettleTimer = null;
  invoiceScroll.addEventListener('scroll', () => {
    clearTimeout(invoiceScrollSettleTimer);
    invoiceScrollSettleTimer = setTimeout(() => settlePrevisitInvoiceEdge(invoiceScroll), 140);
  }, {passive: true});
  invoiceScroll.addEventListener('touchend', () => {
    clearTimeout(invoiceScrollSettleTimer);
    invoiceScrollSettleTimer = setTimeout(() => settlePrevisitInvoiceEdge(invoiceScroll), 180);
  }, {passive: true});
  const invoiceHeader = cart.querySelector('.previsit-invoice-head');
  invoiceHeader.children[5].textContent = '\u0642\u06cc\u0645\u062a \u067e\u0627\u06cc\u0647';
  invoiceHeader.children[5].insertAdjacentHTML('afterend', '<span>\u0642\u06cc\u0645\u062a \u062a\u0648\u0644\u06cc\u062f\u06a9\u0646\u0646\u062f\u0647</span><span>\u0642\u06cc\u0645\u062a \u0645\u0635\u0631\u0641\u200c\u06a9\u0646\u0646\u062f\u0647</span>');
  $('#previsitLines').insertAdjacentHTML('afterend', `<footer id="previsitInvoiceTotals" class="previsit-invoice-totals" hidden><strong class="is-product" data-total-label>\u062c\u0645\u0639 \u0627\u0648\u0644\u06cc\u0647</strong><output class="is-quantity" data-total="quantity">\u06f0</output><span class="is-carton">\u2014</span><span class="is-remainder">\u2014</span><span class="is-units-per-carton">\u2014</span><span class="is-unit">\u2014</span><span class="is-producer">\u2014</span><span class="is-consumer">\u2014</span><output class="is-gross" data-total="gross">\u06f0</output><output class="is-goods" data-total="goods">\u06f0</output><output class="is-volume" data-total="volume">\u06f0</output><output class="is-cash" data-total="cash">\u06f0</output><output class="is-tax" data-total="tax">\u06f0</output><output class="is-net" data-total="net">\u06f0</output><span class="is-remove"></span></footer>`);
  $('#previsitProductSearch').addEventListener('input', renderPrevisitProductOptions);
  $('#previsitBrandFilter').addEventListener('change', (event) => { previsitCatalogState.brand = event.currentTarget.value; renderPrevisitCatalogFilterOptions(); renderPrevisitProductOptions(); });
  $('#previsitGroupFilter').addEventListener('change', (event) => { previsitCatalogState.group = event.currentTarget.value; renderPrevisitProductOptions(); });
  $('#previsitSort').addEventListener('change', renderPrevisitProductOptions);
  $('#previsitStockToggle').addEventListener('click', (event) => { previsitCatalogState.inStock = !previsitCatalogState.inStock; event.currentTarget.classList.toggle('is-active', previsitCatalogState.inStock); event.currentTarget.setAttribute('aria-pressed', String(previsitCatalogState.inStock)); renderPrevisitProductOptions(); });
  $('#previsitCatalogGrid').addEventListener('click', (event) => {
    const decrease = event.target.closest('[data-previsit-catalog-unit-decrease]');
    const increase = event.target.closest('[data-previsit-catalog-unit-increase]');
    const productId = decrease?.dataset.previsitCatalogUnitDecrease || increase?.dataset.previsitCatalogUnitIncrease;
    if (!productId) return;
    changePrevisitListUnitQuantity(productId, (decrease || increase).dataset.previsitUnitKey, decrease ? -1 : 1);
    renderPrevisitProductOptions();
  });
  $('#previsitCatalogGrid').addEventListener('input', (event) => {
    const input = event.target.closest('[data-previsit-catalog-unit-quantity]');
    if (!input) return;
    setPrevisitListUnitQuantity(input.dataset.previsitCatalogUnitQuantity, input.dataset.previsitUnitKey, input.value);
    updatePrevisitCatalogUnitFeedback(input);
  });
  $('#previsitCatalogGrid').addEventListener('change', (event) => {
    const input = event.target.closest('[data-previsit-catalog-unit-quantity]');
    if (input) renderPrevisitProductOptions();
  });
  $('#previsitTableMode').addEventListener('click', () => void openPrevisitTableMode());
  $('#previsitTableClose').addEventListener('click', closePrevisitTableMode);
  $('#previsitTableCart').addEventListener('click', () => { closePrevisitTableMode(); switchPrevisitView('cart'); });
  $('#previsitTablePrevious').addEventListener('click', () => movePrevisitTableProduct(-1));
  $('#previsitTableNext').addEventListener('click', () => movePrevisitTableProduct(1));
  $('#previsitTableMinus').addEventListener('click', () => changePrevisitTableQuantity(-1));
  $('#previsitTablePlus').addEventListener('click', () => changePrevisitTableQuantity(1));
  $('#previsitTableSeller').addEventListener('click', (event) => {
    const decrease = event.target.closest('[data-previsit-catalog-unit-decrease]');
    const increase = event.target.closest('[data-previsit-catalog-unit-increase]');
    const productId = decrease?.dataset.previsitCatalogUnitDecrease || increase?.dataset.previsitCatalogUnitIncrease;
    if (!productId) return;
    changePrevisitListUnitQuantity(productId, (decrease || increase).dataset.previsitUnitKey, decrease ? -1 : 1);
    renderPrevisitTableProduct();
  });
  $('#previsitTableSeller').addEventListener('input', (event) => {
    const input = event.target.closest('[data-previsit-catalog-unit-quantity]');
    if (!input) return;
    setPrevisitListUnitQuantity(input.dataset.previsitCatalogUnitQuantity, input.dataset.previsitUnitKey, input.value);
    updatePrevisitCatalogUnitFeedback(input);
  });
  $('#previsitTableSeller').addEventListener('change', (event) => {
    if (event.target.closest('[data-previsit-catalog-unit-quantity]')) renderPrevisitTableProduct();
  });
  tableOverlay.addEventListener('pointerdown', beginPrevisitTableSwipe);
  tableOverlay.addEventListener('pointerup', finishPrevisitTableSwipe);
  tableOverlay.addEventListener('pointercancel', cancelPrevisitTableSwipe);
  document.addEventListener('fullscreenchange', () => {
    const overlay = $('#previsitTableOverlay');
    if (overlay && !document.fullscreenElement && !overlay.hidden) closePrevisitTableMode(false);
  });
  $('#addPrevisitLine').addEventListener('click', () => addPrevisitLine());
  $('#runPrevisitOrderCommand').addEventListener('click', runPrevisitOrderCommand);
  $('#recordPrevisitOrderCommand').addEventListener('click', () => void toggleOrderCommandVoice());
  $('#previsitFloatingVoice').addEventListener('click', () => void toggleOrderCommandVoice());
  $('#previsitOrderCommand').addEventListener('keydown', (event) => {
    if (event.key === 'Enter') { event.preventDefault(); runPrevisitOrderCommand(); }
  });
  $('#previsitQuickSearch').addEventListener('input', (event) => { previsitQuickFilterState.query = event.currentTarget.value.trim().toLocaleLowerCase('fa'); renderPrevisitProductOptions(); });
  $('#previsitQuickBrandFilter').addEventListener('change', (event) => { previsitQuickFilterState.brand = event.currentTarget.value; renderPrevisitQuickFilterOptions(); renderPrevisitProductOptions(); });
  $('#previsitQuickGroupFilter').addEventListener('change', (event) => { previsitQuickFilterState.group = event.currentTarget.value; renderPrevisitProductOptions(); });
  $('#previsitListSearch').addEventListener('input', (event) => { previsitListState.query = event.currentTarget.value.trim().toLocaleLowerCase('fa'); renderPrevisitProductList(); });
  $('#previsitListDensityToggle').addEventListener('click', (event) => {
    previsitListCompact = !previsitListCompact;
    $('#previsitProductListView').classList.toggle('is-compact', previsitListCompact);
    event.currentTarget.setAttribute('aria-pressed', String(previsitListCompact));
    event.currentTarget.textContent = previsitListCompact ? '↕ نمایش باز' : '↕ نمایش فشرده';
    localStorage.setItem('negin-previsit-list-density', previsitListCompact ? 'compact' : 'comfortable');
  });
  $('#previsitListStockToggle').addEventListener('click', (event) => {
    previsitListState.inStock = !previsitListState.inStock;
    event.currentTarget.classList.toggle('is-active', previsitListState.inStock);
    event.currentTarget.setAttribute('aria-pressed', String(previsitListState.inStock));
    renderPrevisitProductList();
  });
  $('#previsitListFiltersToggle').addEventListener('click', () => updatePrevisitListScrollChrome({toggle: true}));
  $('#previsitListHierarchy').addEventListener('click', (event) => {
    const brand = event.target.closest('[data-previsit-list-brand]');
    const group = event.target.closest('[data-previsit-list-group]');
    if (brand) {
      previsitListState.brand = brand.dataset.previsitListBrand || '';
      previsitListState.group = '';
    } else if (group) {
      previsitListState.group = group.dataset.previsitListGroup || '';
    } else return;
    renderPrevisitListFilters();
    renderPrevisitProductList();
  });
  $('#previsitListProducts').addEventListener('click', (event) => {
    const decrease = event.target.closest('[data-previsit-list-unit-decrease]');
    const increase = event.target.closest('[data-previsit-list-unit-increase]');
    const productId = decrease?.dataset.previsitListUnitDecrease || increase?.dataset.previsitListUnitIncrease;
    if (!productId) return;
    const unitKey = (decrease || increase).dataset.previsitUnitKey;
    changePrevisitListUnitQuantity(productId, unitKey, decrease ? -1 : 1);
    renderPrevisitProductList();
  });
  $('#previsitListProducts').addEventListener('input', (event) => {
    const input = event.target.closest('[data-previsit-list-unit-quantity]');
    if (!input) return;
    setPrevisitListUnitQuantity(input.dataset.previsitListUnitQuantity, input.dataset.previsitUnitKey, input.value);
    updatePrevisitListUnitFeedback(input);
  });
  $('#previsitListProducts').addEventListener('change', (event) => {
    const input = event.target.closest('[data-previsit-list-unit-quantity]');
    if (!input) return;
    renderPrevisitProductList();
  });
  $('#previsitGroupedSearch').addEventListener('input', (event) => {
    previsitGroupedCatalogState.query = event.currentTarget.value.trim().toLocaleLowerCase('fa');
    renderPrevisitGroupedCatalogs();
  });
  $('#previsitGroupedBrand').addEventListener('change', (event) => {
    previsitGroupedCatalogState.brand = event.currentTarget.value;
    previsitGroupedCatalogState.group = '';
    renderPrevisitGroupedCatalogFilters();
    renderPrevisitGroupedCatalogs();
  });
  $('#previsitGroupedGroup').addEventListener('change', (event) => {
    previsitGroupedCatalogState.group = event.currentTarget.value;
    renderPrevisitGroupedCatalogs();
  });
  $('#previsitGroupedStockToggle').addEventListener('click', (event) => {
    previsitGroupedCatalogState.inStock = !previsitGroupedCatalogState.inStock;
    event.currentTarget.classList.toggle('is-active', previsitGroupedCatalogState.inStock);
    event.currentTarget.setAttribute('aria-pressed', String(previsitGroupedCatalogState.inStock));
    renderPrevisitGroupedCatalogs();
  });
  $('#previsitGroupedCatalogs').addEventListener('click', (event) => {
    const decrease = event.target.closest('[data-previsit-catalog-unit-decrease]');
    const increase = event.target.closest('[data-previsit-catalog-unit-increase]');
    const productId = decrease?.dataset.previsitCatalogUnitDecrease || increase?.dataset.previsitCatalogUnitIncrease;
    if (!productId) return;
    changePrevisitListUnitQuantity(productId, (decrease || increase).dataset.previsitUnitKey, decrease ? -1 : 1);
    renderPrevisitGroupedCatalogs();
  });
  $('#previsitGroupedCatalogs').addEventListener('input', (event) => {
    const input = event.target.closest('[data-previsit-catalog-unit-quantity]');
    if (!input) return;
    setPrevisitListUnitQuantity(input.dataset.previsitCatalogUnitQuantity, input.dataset.previsitUnitKey, input.value);
    updatePrevisitCatalogUnitFeedback(input);
  });
  $('#previsitGroupedCatalogs').addEventListener('change', (event) => {
    if (event.target.closest('[data-previsit-catalog-unit-quantity]')) renderPrevisitGroupedCatalogs();
  });
  $('#previsitGroupedDownload').addEventListener('click', () => void downloadPrevisitGroupedCatalog());
  $('#previsitGroupedTableMode').addEventListener('click', () => void openPrevisitTableMode());
  $('#previsitOrderAssistantResult').addEventListener('click', (event) => {
    const choice = event.target.closest('[data-previsit-command-product]');
    if (!choice) return;
    const product = productForPrevisit(choice.dataset.previsitCommandProduct);
    const outcome = addPrevisitVoiceLine(
      product,
      Number(choice.dataset.previsitCommandQuantity || 1),
      choice.dataset.previsitCommandUnit || 'عدد',
    );
    if (!outcome.ok) return toast(outcome.message);
    choice.closest('[data-previsit-command-group]')?.remove();
    const result = $('#previsitOrderAssistantResult');
    if (!result.querySelector('[data-previsit-command-group]')) {
      result.hidden = true;
      switchPrevisitView('cart');
    }
  });
  $$('.previsit-mobile-dock [data-previsit-view]').forEach((button) => button.addEventListener('click', () => {
    const requestedView = button.dataset.previsitView;
    const activeView = requestedView === 'cart' && previsitActiveView === 'cart' ? 'catalog' : requestedView;
    navigatePrevisitState({activeView});
  }));
  $$('.previsit-order-mode-switch [data-previsit-order-mode]').forEach((button) => button.addEventListener('click', () => navigatePrevisitState({orderMode: button.dataset.previsitOrderMode, activeView: 'catalog'})));
  $$('.previsit-visit-rail [data-previsit-section]').forEach((button) => button.addEventListener('click', () => navigatePrevisitState({section: button.dataset.previsitSection})));
  $('.previsit-visit-rail [data-previsit-outcome="no_order"]').addEventListener('click', () => {
    togglePrevisitVisitMenu(false);
    openPrevisitOutcome('no_order');
  });
  $('.previsit-visit-rail [data-previsit-finish-visit]').addEventListener('click', () => {
    togglePrevisitVisitMenu(false);
    void completePrevisit('order').catch((error) => toast(error.message));
  });
  $('#previsitProfileContent').addEventListener('click', async (event) => {
    const capture = event.target.closest('[data-previsit-capture-location]');
    if (capture) void openPrevisitLocationPicker().catch((error) => toast(error.message));
  });
  $('#previsitProfileContent').addEventListener('submit', (event) => {
    if (!event.target.closest('#previsitCustomerProfileForm')) return;
    event.preventDefault();
    void saveEmbeddedPrevisitCustomerProfile().catch((error) => toast(error.message));
  });
  $('#previsitOrderType').addEventListener('change', () => {
    invalidatePrevisitCalculation();
    renderPrevisitCatalogFilterOptions();
    renderPrevisitQuickFilterOptions();
    renderPrevisitListFilters();
    renderPrevisitProductOptions();
    renderPrevisitProductList();
    renderPrevisitGroupedCatalogFilters();
    renderPrevisitGroupedCatalogs();
    renderPrevisitTableProduct();
    updatePrevisitPriceContextNote();
    updatePrevisitOrderContextSummary();
  });
  $('#previsitPaymentType').addEventListener('change', () => { invalidatePrevisitCalculation(); renderPrevisitProductList(); renderPrevisitGroupedCatalogs(); updatePrevisitPriceContextNote(); updatePrevisitOrderContextSummary(); });
  $('#previsitWarehouse').addEventListener('change', () => { invalidatePrevisitCalculation(); renderPrevisitCatalogFilterOptions(); renderPrevisitQuickFilterOptions(); renderPrevisitListFilters(); renderPrevisitProductOptions(); renderPrevisitProductList(); renderPrevisitGroupedCatalogFilters(); renderPrevisitGroupedCatalogs(); updatePrevisitPriceContextNote(); updatePrevisitOrderContextSummary(); });
  $('#previewPrevisit').addEventListener('click', () => void previewNgtPrevisit().then(syncPrevisitCartSummary).catch((error) => toast(error.message)));
  $('#savePrevisitDraft').addEventListener('click', () => void savePrevisitRequest().catch((error) => toast(error.message)));
  $('#completePrevisitOrder').addEventListener('click', () => void completePrevisit('order').catch((error) => toast(error.message)));
  $('#previsitLines').addEventListener('input', () => queueMicrotask(syncPrevisitCartSummary));
  new MutationObserver(() => queueMicrotask(syncPrevisitCartSummary)).observe($('#previsitLines'), {childList: true});
  window.addEventListener('scroll', queuePrevisitListScrollChrome, {passive: true});
}

function settlePrevisitInvoiceEdge(scroller = $('#previsitCartView')?.querySelector('.previsit-invoice-scroll')) {
  if (!scroller) return;
  const maximum = Math.max(0, scroller.scrollWidth - scroller.clientWidth);
  const current = Math.max(0, Number(scroller.scrollLeft || 0));
  const threshold = Math.min(64, Math.max(28, scroller.clientWidth * 0.12));
  if (current <= threshold) scroller.scrollLeft = 0;
  else if (maximum - current <= threshold) scroller.scrollLeft = maximum;
}

function positionPrevisitInvoice(position = 'product', behavior = 'smooth') {
  const scroller = $('#previsitCartView')?.querySelector('.previsit-invoice-scroll');
  if (!scroller) return;
  const maximum = Math.max(0, scroller.scrollWidth - scroller.clientWidth);
  const left = position === 'totals' ? 0 : position === 'discounts' ? maximum * 0.5 : maximum;
  const edgePosition = position === 'totals' || position === 'product';
  if (typeof scroller.scrollTo === 'function') scroller.scrollTo({left, top: 0, behavior: edgePosition ? 'auto' : behavior});
  else scroller.scrollLeft = left;
  if (edgePosition) requestAnimationFrame(() => { scroller.scrollLeft = left; });
}

function setPrevisitListFiltersCollapsed(collapsed) {
  const controls = $('#previsitListControls');
  const toggle = $('#previsitListFiltersToggle');
  if (!controls || !toggle) return;
  controls.classList.toggle('is-filter-rail-collapsed', collapsed);
  toggle.setAttribute('aria-expanded', String(!collapsed));
  toggle.textContent = collapsed ? 'فیلتر برند و گروه' : 'جمع‌کردن فیلترها';
}

function updatePrevisitListScrollChrome(options = {}) {
  const controls = $('#previsitListControls');
  const listView = $('#previsitProductListView');
  const active = controls && listView && !listView.hidden
    && previsitVisitSection === 'order' && previsitActiveView === 'catalog' && previsitOrderMode === 'list';
  const scrollY = Math.max(0, window.scrollY || document.documentElement.scrollTop || 0);
  if (!active || options.reset) {
    setPrevisitListFiltersCollapsed(false);
    previsitListLastScrollY = scrollY;
    return;
  }
  if (options.toggle) {
    setPrevisitListFiltersCollapsed(!controls.classList.contains('is-filter-rail-collapsed'));
    previsitListLastScrollY = scrollY;
    return;
  }
  const delta = scrollY - previsitListLastScrollY;
  const stickyTop = Number.parseFloat(getComputedStyle(controls).top) || 0;
  const controlsReachedStickyEdge = controls.getBoundingClientRect().top <= stickyTop + 3;
  if (delta > 3 && controlsReachedStickyEdge) setPrevisitListFiltersCollapsed(true);
  else if (delta < -5) setPrevisitListFiltersCollapsed(false);
  previsitListLastScrollY = scrollY;
}

function queuePrevisitListScrollChrome() {
  if (previsitListScrollFrame) return;
  previsitListScrollFrame = requestAnimationFrame(() => {
    previsitListScrollFrame = 0;
    updatePrevisitListScrollChrome();
  });
}

function switchPrevisitView(view) {
  previsitActiveView = view === 'cart' ? 'cart' : 'catalog';
  $('#previsitCatalogView').hidden = true;
  $('#previsitQuickOrderView').hidden = true;
  $('#previsitProductListView').hidden = previsitActiveView !== 'catalog' || previsitOrderMode !== 'list';
  $('#previsitGroupedCatalogView').hidden = previsitActiveView !== 'catalog' || previsitOrderMode !== 'grouped';
  $('#previsitCartView').hidden = previsitActiveView !== 'cart';
  const floatingVoice = $('#previsitFloatingVoice');
  if (floatingVoice) floatingVoice.hidden = previsitVisitSection !== 'order';
  $$('.previsit-mobile-dock [data-previsit-view]').forEach((button) => button.classList.toggle('is-active', button.dataset.previsitView === previsitActiveView));
  const dockCart = $('.previsit-mobile-dock [data-previsit-view="cart"]');
  if (dockCart) {
    const cartIsOpen = previsitActiveView === 'cart';
    dockCart.setAttribute('aria-label', cartIsOpen ? 'بازگشت به فهرست کالا' : 'مشاهده سبد خرید');
    dockCart.querySelector('b').textContent = cartIsOpen ? 'بازگشت' : 'سبد';
  }
  if (previsitActiveView === 'cart') {
    $('#previsitCartView').scrollIntoView({block: 'start'});
    requestAnimationFrame(() => positionPrevisitInvoice('product', 'auto'));
  }
  requestAnimationFrame(() => updatePrevisitListScrollChrome({reset: true}));
}

function navigatePrevisitState(changes = {}) {
  const current = appHistoryState();
  const base = current?.view === 'previsit' ? current.detail || {} : {};
  const detail = {
    ...base,
    section: changes.section || previsitVisitSection,
    orderMode: changes.orderMode || previsitOrderMode,
    activeView: changes.activeView || previsitActiveView,
  };
  rememberAppView('previsit', detail);
  switchPrevisitOrderMode(detail.orderMode);
  switchPrevisitVisitSection(detail.section);
  switchPrevisitView(detail.activeView);
}

function switchPrevisitOrderMode(mode) {
  previsitOrderMode = mode === 'grouped' ? 'grouped' : 'list';
  previsitActiveView = 'catalog';
  $$('.previsit-order-mode-switch [data-previsit-order-mode]').forEach((button) => {
    const active = button.dataset.previsitOrderMode === previsitOrderMode;
    button.classList.toggle('is-active', active);
    button.setAttribute('aria-selected', String(active));
  });
  const dockCatalog = $('.previsit-mobile-dock [data-previsit-view="catalog"]');
  if (dockCatalog) {
    const labels = {list: ['لیست کالا', 'فهرست کالاها'], grouped: ['کاتالوگ گروهی', 'تصویر و کالاهای مرتبط']};
    dockCatalog.querySelector('b').textContent = labels[previsitOrderMode][0];
    dockCatalog.querySelector('small').textContent = labels[previsitOrderMode][1];
  }
  switchPrevisitView('catalog');
  if (previsitOrderMode === 'list') {
    renderPrevisitListFilters();
    renderPrevisitProductList();
  } else {
    renderPrevisitGroupedCatalogFilters();
    renderPrevisitGroupedCatalogs();
  }
}

function switchPrevisitVisitSection(section) {
  const button = $(`.previsit-visit-rail [data-previsit-section="${section}"]`);
  if (!button || button.disabled) return;
  previsitVisitSection = section;
  $$('[data-previsit-section-panel]', $('#previsitCart')).forEach((panel) => {
    panel.hidden = panel.dataset.previsitSectionPanel !== section;
  });
  $$('.previsit-visit-rail [data-previsit-section]').forEach((item) => {
    const active = item.dataset.previsitSection === section;
    item.classList.toggle('is-active', active);
    if (active) item.setAttribute('aria-current', 'page');
    else item.removeAttribute('aria-current');
  });
  updatePrevisitVisitMenuCurrent(section);
  const floatingVoice = $('#previsitFloatingVoice');
  if (floatingVoice) floatingVoice.hidden = section !== 'order';
  togglePrevisitVisitMenu(false);
  if (section === 'order') switchPrevisitView(previsitActiveView);
  if (section === 'saved-requests') void loadPrevisitSavedRequests().catch((error) => toast(error.message));
}

const previsitMoney = (value) => `${Number(value || 0).toLocaleString('fa-IR')} ریال`;
const previsitCount = (value, unit = '') => `${Number(value || 0).toLocaleString('fa-IR')}${unit ? ` ${unit}` : ''}`;

function previsitMetricCard(label, value, note = '', tone = '') {
  return `<article class="previsit-metric-card ${tone}"><small>${esc(label)}</small><strong>${esc(value)}</strong>${note ? `<span>${esc(note)}</span>` : ''}</article>`;
}

function previsitSellerContact(name, mobile) {
  if (!name && !mobile) return '';
  const callable = String(mobile || '').replace(/[^\d+]/g, '');
  return `<div class="previsit-seller-contact"><dt>آخرین بازاریاب</dt><dd><span>${esc(name || 'نام ثبت نشده')}</span>${callable ? `<a href="tel:${esc(callable)}" aria-label="تماس با ${esc(name || 'بازاریاب')}">☎ ${esc(mobile)}</a>` : '<small>شماره تماس ثبت نشده</small>'}</dd></div>`;
}

function previsitBrandCards(brands = []) {
  if (!brands.length) return '<p class="previsit-muted">برای این بخش سابقه‌ای دیده نشد.</p>';
  return `<div class="previsit-brand-card-grid">${brands.map((brand) => `<article class="previsit-brand-card"><header><strong>${esc(brand.name)}</strong><b>${previsitCount(brand.invoice_count, 'فاکتور')}</b></header><dl><div><dt>خرید خالص</dt><dd>${previsitMoney(brand.net_sales)}</dd></div><div><dt>آخرین خرید</dt><dd>${esc(brand.last_purchase_date || 'ثبت نشده')}</dd></div>${brand.sales_line ? `<div><dt>لاین خرید</dt><dd>${esc(brand.sales_line)}</dd></div>` : ''}${previsitSellerContact(brand.last_seller_name, brand.last_seller_mobile)}</dl></article>`).join('')}</div>`;
}

function previsitLinePurchaseCards(lines = []) {
  if (!lines.length) return '<p class="previsit-muted">تفکیک خرید بر اساس لاین برای این مشتری دیده نشد.</p>';
  return `<div class="previsit-line-purchase-grid">${lines.map((line) => `<article><header><strong>${esc(line.name)}</strong><span>${previsitCount(line.invoice_count, 'فاکتور')}</span></header><b>${previsitMoney(line.net_sales)}</b><small>آخرین خرید ${esc(line.last_purchase_date || 'ثبت نشده')}</small>${line.last_seller_name ? `<p>آخرین بازاریاب: <strong>${esc(line.last_seller_name)}</strong></p>` : ''}${line.last_seller_mobile ? `<a class="previsit-line-seller-phone" href="tel:${esc(String(line.last_seller_mobile).replace(/[^\d+]/g, ''))}">☎ ${esc(line.last_seller_mobile)}</a>` : ''}${line.branch ? `<em>${esc(line.branch)}</em>` : ''}</article>`).join('')}</div>`;
}

function previsitReturnedChequeCards(cheques = []) {
  if (!cheques.length) return '<div class="previsit-empty-state"><span>✓</span><strong>سابقه چک برگشتی برای این مشتری دیده نشد</strong><small>اطلاعات از وضعیت و تاریخچه پایدار چک‌های ورانگر خوانده شده است.</small></div>';
  const labels = {active_returned: 'برگشتی فعال', collected_after_return: 'وصول پس از برگشت', refunded_after_return: 'تسویه و استرداد', legal_returned: 'پیگیری حقوقی'};
  return `<div class="previsit-returned-cheque-list">${cheques.map((cheque) => `<article class="is-${esc(cheque.lifecycle || 'returned-history')}"><header><div><strong>چک ${esc(cheque.number || cheque.id)}</strong><small>${esc(cheque.bank || 'بانک ثبت نشده')} ${cheque.branch ? `· ${esc(cheque.branch)}` : ''}</small></div><b>${esc(labels[cheque.lifecycle] || cheque.status || 'سابقه برگشت')}</b></header><dl><div><dt>مبلغ چک</dt><dd>${previsitMoney(cheque.amount)}</dd></div><div><dt>تاریخ چک</dt><dd>${esc(cheque.date || 'ثبت نشده')}</dd></div><div><dt>اولین برگشت</dt><dd>${esc(cheque.first_return_date || 'ثبت نشده')}</dd></div><div><dt>آخرین وضعیت</dt><dd>${esc(cheque.status_date || 'ثبت نشده')}</dd></div><div><dt>تسویه ثبت‌شده</dt><dd>${previsitMoney(cheque.settled_amount)}</dd></div><div><dt>وضعیت تسویه</dt><dd>${cheque.fully_settled ? 'کامل' : 'ناقص یا ثبت‌نشده'}</dd></div></dl></article>`).join('')}</div>`;
}

function renderPrevisitCustomerHeader(customer = {}, route = {}, seller = {}) {
  const header = $('#previsitCustomerSummary');
  if (!header) return;
  const fullName = customer.name || customer.full_name || customer.store_name || customer.title || customer.id || 'مشتری مسیر روز';
  const storeName = customer.store_name && customer.store_name !== fullName ? customer.store_name : '';
  const customerCode = customer.code || customer.customer_code || '';
  const phone = customer.mobile || customer.phone || '';
  const callable = String(phone).replace(/[^\d+]/g, '');
  const address = customer.address || 'نشانی مشتری ثبت نشده است';
  const location = [customer.city_name, customer.county_name].filter(Boolean).join('، ');
  const chips = [
    storeName ? `<span><small>فروشگاه</small><b>${esc(storeName)}</b></span>` : '',
    customer.activity_name ? `<span><small>فعالیت</small><b>${esc(customer.activity_name)}</b></span>` : '',
    location ? `<span><small>محدوده</small><b>${esc(location)}</b></span>` : '',
  ].filter(Boolean).join('');
  header.innerHTML = `<div class="previsit-customer-header-copy"><span class="previsit-eyebrow">مشتری فعال این ویزیت</span><div class="previsit-customer-name-row"><h3>${esc(fullName)}</h3>${customerCode ? `<b class="previsit-customer-code">کد ${esc(customerCode)}</b>` : ''}</div><p title="${esc(address)}"><i aria-hidden="true">⌖</i>${esc(address)}</p><div class="previsit-customer-header-meta">${chips}${callable ? `<a href="tel:${esc(callable)}" aria-label="تماس با ${esc(fullName)}"><small>تماس</small><b>${esc(phone)}</b></a>` : ''}</div></div>`;
  requestAnimationFrame(updatePrevisitOrderStickyTop);
}

function setPrevisitReportGate(section, allowed) {
  const button = $(`.previsit-visit-rail [data-previsit-section="${section}"]`);
  if (!button) return;
  button.dataset.reportAllowed = String(Boolean(allowed));
  button.disabled = !allowed;
  button.classList.toggle('is-locked', !allowed);
  if (!allowed) button.querySelector('small').textContent = 'غیرفعال در تنظیمات';
}

function previsitRequiredFieldLabel(field) {
  const normalized = String(field || '').replace(/[\s-]/g, '').toLocaleLowerCase('en');
  return ({phone: 'تلفن', mobile: 'موبایل', storename: 'نام فروشگاه', address: 'نشانی',
    nationalcode: 'کد ملی', economiccode: 'کد اقتصادی', postalcode: 'کد پستی', postcode: 'کد پستی',
    customeractivityid: 'فعالیت مشتری', customeractivityuniqueid: 'فعالیت مشتری', stateid: 'استان', stateuniqueid: 'استان',
    cityid: 'شهر', cityuniqueid: 'شهر', countyid: 'شهرستان', countyuniqueid: 'شهرستان', cityzone: 'منطقه شهری',
    customerlevelid: 'سطح مشتری', customerleveluniqueid: 'سطح مشتری', customercategoryid: 'گروه مشتری',
    customercategoryuniqueid: 'گروه مشتری', ownertyperef: 'نوع مالکیت', customercode: 'کد مشتری',
    latitude: 'عرض جغرافیایی', longitude: 'طول جغرافیایی'}[normalized] || String(field || 'اطلاعات مشتری'));
}

function previsitCustomerProfileFieldName(field) {
  const normalized = String(field || '').replace(/[_\s-]/g, '').toLocaleLowerCase('en');
  return ({phone: 'phone', mobile: 'mobile', storename: 'store_name', address: 'address', nationalcode: 'national_code',
    economiccode: 'economic_code', postalcode: 'postal_code', postcode: 'postal_code', customeractivityid: 'customer_activity_id',
    customeractivityuniqueid: 'customer_activity_id', stateid: 'state_id', stateuniqueid: 'state_id', cityid: 'city_id',
    cityuniqueid: 'city_id', countyid: 'county_id', countyuniqueid: 'county_id', cityzone: 'city_zone',
    customerlevelid: 'customer_level_id', customerleveluniqueid: 'customer_level_id', customercategoryid: 'customer_category_id',
    customercategoryuniqueid: 'customer_category_id', ownertyperef: 'owner_type_ref', customercode: 'customer_code',
    latitude: 'latitude', longitude: 'longitude'}[normalized] || '');
}

function setPrevisitLocationPickerPosition(position, {moveMap = false} = {}) {
  if (!position || !Number.isFinite(Number(position.latitude)) || !Number.isFinite(Number(position.longitude))) return;
  previsitLocationPickerCoordinates = {latitude: Number(position.latitude), longitude: Number(position.longitude), accuracy: position.accuracy};
  const coordinates = [previsitLocationPickerCoordinates.longitude, previsitLocationPickerCoordinates.latitude];
  previsitLocationPickerMarker?.setLngLat(coordinates);
  if (moveMap) previsitLocationPickerMap?.flyTo({center: coordinates, zoom: Math.max(previsitLocationPickerMap.getZoom?.() || 16, 16)});
  const output = $('#previsitLocationPickerCoordinates');
  if (output) output.textContent = `${previsitLocationPickerCoordinates.latitude.toFixed(7)} ، ${previsitLocationPickerCoordinates.longitude.toFixed(7)}`;
  const status = $('#previsitLocationPickerStatus');
  if (status) status.textContent = Number.isFinite(position.accuracy)
    ? `دقت تقریبی GPS: ${Math.round(position.accuracy).toLocaleString('fa-IR')} متر؛ نشانگر را در صورت نیاز جابه‌جا کنید.`
    : 'برای اصلاح نقطه، نشانگر را جابه‌جا کنید یا روی نقشه بزنید.';
}

async function locatePrevisitCustomerOnMap() {
  const button = $('#previsitLocationPickerCurrent');
  if (button) { button.disabled = true; button.textContent = 'در حال دریافت GPS…'; }
  try {
    const position = await currentCoordinates({maximumAge: 0, timeout: 15000});
    if (!position) throw Error('موقعیت دریافت نشد؛ دسترسی Location دستگاه را روشن کنید.');
    setPrevisitLocationPickerPosition(position, {moveMap: true});
  } finally {
    if (button?.isConnected) { button.disabled = false; button.textContent = '⌖ موقعیت فعلی من'; }
  }
}

async function openPrevisitLocationPicker() {
  const dialog = $('#previsitLocationPickerDialog');
  if (!dialog) return;
  const form = $('#previsitCustomerProfileForm');
  const latitudeControl = $('[data-previsit-profile-field="latitude"]', form);
  const longitudeControl = $('[data-previsit-profile-field="longitude"]', form);
  if (!latitudeControl || !longitudeControl) throw Error('مجوز ثبت موقعیت برای این مشتری فعال نیست.');
  const savedPosition = {
    latitude: Number(latitudeControl.value),
    longitude: Number(longitudeControl.value),
  };
  if (!dialog.open) dialog.showModal();
  const [configResponse, currentPosition] = await Promise.all([
    fetch('/seller-workspace/map-config'),
    currentCoordinates({maximumAge: 30000, timeout: 12000}),
  ]);
  if (!configResponse.ok) throw Error('نقشه انتخاب موقعیت آماده نیست.');
  const config = await configResponse.json();
  const maplibregl = window.maplibregl?.default || window.maplibregl;
  if (!maplibregl) throw Error('نقشه نشان بارگذاری نشد.');
  const initial = currentPosition || (Number.isFinite(savedPosition.latitude) && Number.isFinite(savedPosition.longitude) && savedPosition.latitude && savedPosition.longitude
    ? savedPosition : {latitude: 35.8285, longitude: 50.9482});
  if (previsitLocationPickerMap) previsitLocationPickerMap.remove();
  previsitLocationPickerMap = new maplibregl.Map({
    container: 'previsitLocationPickerMap',
    style: 'https://static.neshan.org/sdk/maplibre/styles/light.json',
    center: [initial.longitude, initial.latitude], zoom: 16, apiKey: config.api_key, rtl: {lazy: false},
  });
  previsitLocationPickerMap.addControl(new maplibregl.NavigationControl());
  previsitLocationPickerMarker = new maplibregl.Marker({color: '#c99b2f', draggable: true})
    .setLngLat([initial.longitude, initial.latitude]).addTo(previsitLocationPickerMap);
  previsitLocationPickerMarker.on('dragend', () => {
    const point = previsitLocationPickerMarker.getLngLat();
    setPrevisitLocationPickerPosition({latitude: point.lat, longitude: point.lng});
  });
  previsitLocationPickerMap.on('click', (event) => setPrevisitLocationPickerPosition({latitude: event.lngLat.lat, longitude: event.lngLat.lng}));
  previsitLocationPickerMap.on('load', () => previsitLocationPickerMap?.resize());
  setPrevisitLocationPickerPosition(initial);
}

function closePrevisitLocationPicker() {
  const dialog = $('#previsitLocationPickerDialog');
  if (dialog?.open) dialog.close();
}

function confirmPrevisitLocationPicker() {
  if (!previsitLocationPickerCoordinates) return toast('ابتدا نقطه مشتری را روی نقشه مشخص کنید.');
  const form = $('#previsitCustomerProfileForm');
  const latitudeControl = $('[data-previsit-profile-field="latitude"]', form);
  const longitudeControl = $('[data-previsit-profile-field="longitude"]', form);
  if (!latitudeControl || !longitudeControl) return toast('مجوز ثبت موقعیت برای این مشتری فعال نیست.');
  latitudeControl.value = previsitLocationPickerCoordinates.latitude.toFixed(7);
  longitudeControl.value = previsitLocationPickerCoordinates.longitude.toFixed(7);
  const status = $('[data-previsit-location-status]');
  if (status) status.textContent = 'نقطه روی نقشه انتخاب شد؛ برای ثبت نهایی، دکمه ذخیره اطلاعات را بزنید.';
  closePrevisitLocationPicker();
}

function applyPrevisitRequirementGate(policy = previsitPolicy) {
  const blockers = policy?.order_blockers || policy?.start_blockers || [];
  const locked = blockers.length > 0;
  $$('.previsit-visit-rail [data-previsit-section]').forEach((item) => {
    const requirementLocked = locked && item.dataset.previsitSection === 'order';
    const reportLocked = item.dataset.reportAllowed === 'false';
    item.disabled = requirementLocked || reportLocked;
    item.classList.toggle('is-requirement-locked', requirementLocked);
    if (requirementLocked) item.title = 'ابتدا موارد اجباری اطلاعات مشتری را تکمیل کنید.';
    else item.removeAttribute('title');
  });
  const status = $('.previsit-rail-status');
  if (status) {
    status.classList.toggle('is-blocked', locked);
    status.querySelector('span').textContent = locked ? 'تکمیل اطلاعات الزامی است' : 'ویزیت آماده است';
    status.querySelector('small').textContent = locked ? blockers.join(' · ') : 'همه منوهای مجاز در دسترس‌اند';
  }
  const noOrder = $('.previsit-visit-rail [data-previsit-outcome="no_order"]');
  if (noOrder) {
    const reasons = policy?.reasons?.no_order || [];
    noOrder.disabled = !previsitSession || !reasons.length;
    noOrder.classList.toggle('is-locked', noOrder.disabled);
    const badge = $('#previsitNoOrderRailBadge');
    if (badge) badge.textContent = reasons.length ? `${reasons.length.toLocaleString('fa-IR')} دلیل فعال` : 'دلیل فعالی تعریف نشده';
  }
  updatePrevisitFinishVisitAction();
  return !locked;
}

function renderEmbeddedPrevisitCustomerProfile() {
  const profile = previsitEmbeddedProfile;
  const root = $('#previsitProfileContent');
  if (!profile || !root) return;
  const customer = profile.customer || {};
  const controls = profile.visit_controls || {};
  const values = {...(customer.editable || {}), ...(profile.draft || {})};
  const missing = previsitPolicy?.missing_required_fields || [];
  const requiredFields = new Set(missing.map(previsitCustomerProfileFieldName).filter(Boolean));
  const contractFields = new Set(profile.editable_contract?.fields || []);
  const activeFields = new Set(profile.editable_contract?.active_fields || []);
  const canEdit = activeFields.size > 0;
  const labelTitle = (name, label, editable) => `<span>${esc(label)}${requiredFields.has(name) ? '<b class="customer-profile-field-badge is-required">اجباری</b>' : (editable ? '<b class="customer-profile-field-badge">قابل ویرایش</b>' : '')}</span>`;
  const field = (name, label, type = 'text', extra = '') => {
    if (!contractFields.has(name)) return '';
    const editable = activeFields.has(name);
    return `<label class="${editable ? 'is-editable' : 'is-readonly'} ${requiredFields.has(name) ? 'is-required' : ''}">${labelTitle(name, label, editable)}<input ${editable ? `data-previsit-profile-field="${name}"` : 'disabled aria-readonly="true"'} type="${type}" ${extra} value="${esc(customerProfileFieldValue(values, name))}"></label>`;
  };
  const select = (name, label, kind, valueType = '') => {
    if (!contractFields.has(name)) return '';
    const editable = activeFields.has(name);
    return `<label class="${editable ? 'is-editable' : 'is-readonly'} ${requiredFields.has(name) ? 'is-required' : ''}">${labelTitle(name, label, editable)}<select ${editable ? `data-previsit-profile-field="${name}"` : 'disabled aria-readonly="true"'} ${valueType ? `data-value-type="${valueType}"` : ''}>${customerProfileLookupOptions(profile, kind, customerProfileFieldValue(values, name))}</select></label>`;
  };
  const addressEditable = activeFields.has('address');
  root.classList.remove('previsit-loading-card');
  root.innerHTML = `<header class="previsit-content-heading"><div><span>شروع ویزیت از این بخش</span><h4>اطلاعات مشتری</h4><p>${esc(customer.store_name || customer.name || 'مشتری')} · ${esc(customer.code || '')}</p></div><b>${missing.length ? `${missing.length.toLocaleString('fa-IR')} مورد اجباری` : 'اطلاعات آماده'}</b></header>
    <section class="previsit-requirement-banner ${missing.length ? 'is-required' : 'is-complete'}"><strong>${missing.length ? 'پیش از ادامه، موارد اجباری را تکمیل کنید' : 'اطلاعات اجباری تکمیل است'}</strong><p>${missing.length ? missing.map(previsitRequiredFieldLabel).map(esc).join('، ') : 'اکنون سایر منوهای مجاز ویزیت در دسترس هستند.'}</p></section>
    <form id="previsitCustomerProfileForm" class="customer-profile-form previsit-customer-profile-form">
      <label class="is-readonly"><span>نام مشتری</span><input value="${esc(customer.name || '')}" disabled aria-readonly="true"></label>
      ${field('store_name', 'نام فروشگاه')}${field('customer_code', 'کد مشتری')}${field('phone', 'تلفن', 'tel')}${field('mobile', 'موبایل', 'tel')}
      ${field('national_code', 'کد ملی')}${field('economic_code', 'کد اقتصادی')}${field('postal_code', 'کد پستی')}
      ${select('customer_activity_id', 'فعالیت مشتری', 'activity')}${select('customer_category_id', 'گروه مشتری', 'category')}${select('customer_level_id', 'سطح مشتری', 'level')}${select('owner_type_ref', 'نوع مالکیت', 'owner_type', 'integer')}
      ${select('state_id', 'استان', 'state')}${select('city_id', 'شهر', 'city')}${select('county_id', 'شهرستان', 'county')}${field('city_zone', 'منطقه شهری', 'number', 'data-value-type="integer"')}
      ${field('latitude', 'عرض جغرافیایی', 'number', 'data-value-type="number" step="any"')}${field('longitude', 'طول جغرافیایی', 'number', 'data-value-type="number" step="any"')}
      ${controls.set_customer_location && activeFields.has('latitude') && activeFields.has('longitude') ? '<div class="customer-profile-location-capture is-wide"><button type="button" data-previsit-capture-location>⌖ انتخاب موقعیت مشتری روی نقشه</button><small data-previsit-location-status>GPS دستگاه نقطه اولیه را مشخص می‌کند؛ روی نقشه می‌توانید آن را دقیق کنید.</small></div>' : ''}
      ${contractFields.has('address') ? `<label class="is-wide ${addressEditable ? 'is-editable' : 'is-readonly'} ${requiredFields.has('address') ? 'is-required' : ''}">${labelTitle('address', 'نشانی', addressEditable)}<textarea ${addressEditable ? 'data-previsit-profile-field="address"' : 'disabled aria-readonly="true"'}>${esc(customerProfileFieldValue(values, 'address'))}</textarea></label>` : ''}
      ${customer.alarm ? `<div class="customer-profile-alert is-wide"><strong>یادداشت مشتری</strong><p>${esc(customer.alarm)}</p></div>` : ''}
      <div class="customer-profile-actions is-wide"><button type="submit" ${canEdit ? '' : 'disabled'}>${canEdit ? 'ذخیره اطلاعات و ادامه' : 'اطلاعات فقط قابل مشاهده است'}</button></div>
    </form>`;
  applyPrevisitRequirementGate();
}

async function loadEmbeddedPrevisitCustomerProfile(routeId, customerId) {
  const response = await fetch(`/seller-workspace/routes/${encodeURIComponent(routeId)}/customers/${encodeURIComponent(customerId)}/profile`);
  const data = await readJsonResponse(response, 'اطلاعات کامل مشتری دریافت نشد.');
  if (!response.ok) throw Error(data.detail || 'اطلاعات کامل مشتری دریافت نشد.');
  previsitEmbeddedProfile = data;
  renderEmbeddedPrevisitCustomerProfile();
  return data;
}

function embeddedPrevisitProfilePayload() {
  const payload = {};
  $$('[data-previsit-profile-field]', $('#previsitCustomerProfileForm')).forEach((control) => {
    const raw = String(control.value || '').trim();
    const type = control.dataset.valueType;
    payload[control.dataset.previsitProfileField] = raw === '' && type ? null : (type === 'integer' ? Number.parseInt(raw, 10) : (type === 'number' ? Number(raw) : raw));
  });
  return payload;
}

async function saveEmbeddedPrevisitCustomerProfile() {
  if (!previsitEmbeddedProfile || !previsitWorkspace) return;
  const form = $('#previsitCustomerProfileForm');
  const button = form?.querySelector('[type="submit"]');
  if (!button) return;
  button.disabled = true;
  button.textContent = 'در حال ذخیره و بررسی…';
  try {
    const routeId = previsitWorkspace.route.id;
    const customerId = previsitWorkspace.customer.id;
    const response = await fetch(`/seller-workspace/routes/${encodeURIComponent(routeId)}/customers/${encodeURIComponent(customerId)}/profile-draft`, {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(embeddedPrevisitProfilePayload())});
    const data = await readJsonResponse(response, 'ذخیره اطلاعات مشتری انجام نشد.');
    if (!response.ok) throw Error(data.detail || 'ذخیره اطلاعات مشتری انجام نشد.');
    previsitEmbeddedProfile.draft = data.draft;
    await loadPrevisitPolicy(routeId, customerId);
    renderEmbeddedPrevisitCustomerProfile();
    if (!previsitPolicy?.start_blockers?.length && !previsitSession) {
      toast('اطلاعات تکمیل شد؛ در حال آماده‌سازی ویزیت…');
      await startPrevisitVisit();
      switchPrevisitVisitSection('profile');
    } else toast((previsitPolicy?.order_blockers || []).length ? 'اطلاعات ذخیره شد؛ موارد اجباری باقی‌مانده را تکمیل کنید.' : 'اطلاعات مشتری ذخیره شد و سفارش‌گیری آزاد شد.');
  } finally {
    if (button.isConnected) { button.disabled = false; button.textContent = 'ذخیره اطلاعات و ادامه'; }
  }
}

function renderPrevisitWorkspaceWithOverview() {
  if (!previsitWorkspace) return;
  const customer = previsitWorkspace.customer || {};
  const analytics = previsitWorkspace.analytics || {};
  const openInvoices = previsitWorkspace.open_invoices || {invoice_count: 0, invoices: []};
  const finance = customer.financial_snapshot || {};
  const title = customer.store_name || customer.name || customer.id;
  renderPrevisitCustomerHeader(customer, previsitWorkspace.route, previsitWorkspace.seller || previsitContext?.seller);
  const identity = $('#previsitVisitIdentity');
  identity.innerHTML = `<span class="previsit-identity-mark">${esc(String(title || 'م').trim().slice(0, 1))}</span><div><strong>${esc(title)}</strong><small>${esc(customer.code || '')} · ${esc(previsitWorkspace.route?.title || '')}</small></div>`;
  $('#previsitInvoiceRailBadge').textContent = `${previsitCount(openInvoices.invoice_count, 'فاکتور')} باز`;

  const reportControls = previsitPolicy?.controls?.reports || {};
  const canSeeInvoices = reportControls.open_invoices !== false;
  const canSeeCardex = reportControls.cardex !== false || reportControls.finance !== false;
  const canSeeHistory = reportControls.sale_history !== false || reportControls.invoices !== false;
  setPrevisitReportGate('invoices', canSeeInvoices);
  setPrevisitReportGate('cardex', canSeeCardex);
  setPrevisitReportGate('history', canSeeHistory);
  setPrevisitReportGate('interests', canSeeHistory);

  const lineBrands = analytics.line_purchased_brands || [];
  const allBrands = analytics.purchased_brands || [];
  const linePurchases = analytics.line_purchase_summary || [];
  const lineBrandNames = new Set(lineBrands.map((item) => String(item.name || '').trim()));
  const otherBrands = allBrands.filter((item) => !lineBrandNames.has(String(item.name || '').trim()));
  const invoiceRows = openInvoices.invoices || [];
  const overview = $('#previsitOverviewContent');
  overview.classList.remove('previsit-loading-card');
  overview.innerHTML = `<header class="previsit-content-heading"><div><span>همه اطلاعات در یک نگاه</span><h4>نمای ویزیت ${esc(title)}</h4><p>${canSeeHistory && lineBrands.length ? `این مشتری از لاین شما ${previsitCount(lineBrands.length, 'برند')} خریده است؛ جزئیات مالی، لاین‌ها، برندها و آخرین بازاریاب‌ها پیش از سفارش آماده است.` : canSeeHistory ? 'سابقه خرید برندهای لاین برای این مشتری دیده نشد؛ اطلاعات مالی و سوابق موجود را مرور کنید.' : 'نمایش تحلیل خرید برای این کاربر غیرفعال است.'}</p></div><b>امتیاز ویزیت ${canSeeHistory ? previsitCount(analytics.visit_score) : '—'}</b></header><div class="previsit-metric-grid">${previsitMetricCard('مانده کاردکس', canSeeCardex ? previsitMoney(customer.cardex_balance) : 'غیرفعال', canSeeCardex ? 'مانده فعلی حساب' : '', 'is-finance')}${previsitMetricCard('مانده فاکتور باز', canSeeInvoices ? previsitMoney(customer.open_invoice_remaining) : 'غیرفعال', canSeeInvoices ? previsitCount(openInvoices.invoice_count, 'سند') : '', canSeeInvoices && Number(customer.open_invoice_remaining || 0) > 0 ? 'is-warning' : 'is-good')}${previsitMetricCard('خرید ۱۲ ماهه شرکت', canSeeHistory ? previsitMoney(analytics.company_net_sales_12m) : 'غیرفعال', canSeeHistory ? previsitCount(analytics.company_invoice_count_12m, 'فاکتور') : '')}${previsitMetricCard('آخرین خرید', canSeeHistory ? (analytics.last_invoice_date || 'بدون سابقه') : 'غیرفعال', 'کل شرکت')}</div>${canSeeCardex ? `<section class="previsit-dashboard-section"><header><div><span>حساب و اعتبار</span><strong>وضعیت مالی مشتری</strong></div><small>اطلاعات لحظه ویزیت</small></header><div class="previsit-metric-grid is-compact">${previsitMetricCard('اعتبار بدهکاری', previsitMoney(finance.remaining_bed_credit), finance.has_bed_credit ? 'فعال' : 'بدون اعتبار')}${previsitMetricCard('اعتبار اسنادی', previsitMoney(finance.remaining_asn_credit), finance.has_asn_credit ? 'فعال' : 'بدون اعتبار')}${previsitMetricCard('چک باز', previsitMoney(finance.open_cheque_amount), previsitCount(finance.open_cheque_count, 'فقره'))}${previsitMetricCard('چک برگشتی', previsitMoney(finance.returned_cheque_amount), previsitCount(finance.returned_cheque_count, 'فقره'), Number(finance.returned_cheque_count || 0) ? 'is-danger' : 'is-good')}</div></section>` : ''}${canSeeHistory ? `<section class="previsit-dashboard-section"><header><div><span>سبد خرید واقعی مشتری</span><strong>خرید به تفکیک لاین</strong></div><small>۱۲ ماه اخیر</small></header>${previsitLinePurchaseCards(linePurchases)}</section><section class="previsit-dashboard-section"><header><div><span>بهترین نقطه شروع مذاکره</span><strong>برندهای لاین من</strong></div><small>${previsitCount(lineBrands.length, 'برند')}</small></header>${previsitBrandCards(lineBrands)}</section><section class="previsit-dashboard-section"><header><div><span>فرصت شناخت و فروش مکمل</span><strong>برندهای سایر لاین‌ها</strong></div><small>${previsitCount(otherBrands.length, 'برند')}</small></header>${previsitBrandCards(otherBrands)}</section>` : ''}${canSeeInvoices ? `<section class="previsit-dashboard-section"><header><div><span>مطالبات پیش از سفارش</span><strong>فاکتورهای باز مشتری</strong></div><small>${previsitCount(openInvoices.invoice_count, 'سند')}</small></header>${invoiceRows.length ? `<div class="previsit-overview-invoices">${invoiceRows.slice(0, 3).map((invoice) => `<article><div><strong>فاکتور ${esc(invoice.number || invoice.id)}</strong><small>${esc(invoice.date || 'بدون تاریخ')}</small></div><span>${previsitMoney(invoice.remaining_amount)}</span></article>`).join('')}</div>` : '<p class="previsit-muted">فاکتور بازی برای این فروشنده دیده نشد.</p>'}</section>` : ''}<section class="previsit-dashboard-section"><header><div><span>شناخت عملیاتی مشتری</span><strong>پروفایل و سابقه ویزیت</strong></div><small>${esc(customer.activity_name || 'نوع فعالیت ثبت نشده')}</small></header><div class="previsit-profile-grid is-overview"><article><small>نشانی</small><strong>${esc(customer.address || 'ثبت نشده')}</strong></article><article><small>تماس</small><strong>${esc(customer.mobile || customer.phone || 'ثبت نشده')}</strong></article><article><small>ویزیت / سفارش</small><strong>${previsitCount(customer.visit_count, 'ویزیت')} · ${previsitCount(customer.order_count, 'سفارش')}</strong></article><article><small>موفقیت ویزیت</small><strong>${Number(customer.avg_successful_visit || 0).toLocaleString('fa-IR', {style: 'percent', maximumFractionDigits: 0})}</strong></article></div></section><section class="previsit-next-best-action"><strong>پیشنهاد اقدام</strong><div><span>۱</span><p>${canSeeInvoices || canSeeCardex ? 'مانده و فاکتورهای باز را مرور کنید.' : 'نیاز اصلی مشتری را مشخص کنید.'}</p></div><div><span>۲</span><p>${canSeeHistory && lineBrands.length ? `از ${lineBrands.slice(0, 3).map((item) => esc(item.name)).join('، ')} شروع کنید.` : 'نیاز مشتری را با سفارش سریع ثبت کنید.'}</p></div><div><span>۳</span><p>سبد را نهایی کنید.</p></div></section>`;

  $('#previsitInvoicesContent').classList.remove('previsit-loading-card');
  $('#previsitInvoicesContent').innerHTML = `<header class="previsit-content-heading"><div><span>مطالبات این فروشنده از مشتری</span><h4>فاکتورهای باز</h4><p>مبلغ باقیمانده هر سند برای گفت‌وگوی مالی پیش از سفارش.</p></div><b>${previsitCount(openInvoices.invoice_count, 'سند')}</b></header>${invoiceRows.length ? `<div class="previsit-open-invoice-list">${invoiceRows.map((invoice) => `<article><div><strong>فاکتور ${esc(invoice.number || invoice.id)}</strong><small>${esc(invoice.date || 'بدون تاریخ')}</small></div><span><small>مبلغ فاکتور</small><b>${previsitMoney(invoice.amount)}</b></span><span class="is-remaining"><small>مانده</small><b>${previsitMoney(invoice.remaining_amount)}</b></span></article>`).join('')}</div>` : '<div class="previsit-empty-state"><span>✓</span><strong>فاکتور بازی برای این فروشنده دیده نشد</strong><small>داده از گزارش جاری وصول دریافت شده است.</small></div>'}`;

  $('#previsitCardexContent').classList.remove('previsit-loading-card');
  $('#previsitCardexContent').innerHTML = `<header class="previsit-content-heading"><div><span>وضعیت مالی لحظه ویزیت</span><h4>کاردکس و اعتبار مشتری</h4><p>در این نسخه مانده معتبر نمایش داده می‌شود؛ ریز گردش کاردکس هنوز به این میزکار متصل نشده است.</p></div></header><div class="previsit-metric-grid">${previsitMetricCard('مانده کاردکس', previsitMoney(customer.cardex_balance), 'Acc.vwCustomerBalance', 'is-finance')}${previsitMetricCard('اعتبار بدهکاری باقی‌مانده', previsitMoney(finance.remaining_bed_credit), finance.has_bed_credit ? 'فعال' : 'بدون اعتبار')}${previsitMetricCard('اعتبار اسنادی باقی‌مانده', previsitMoney(finance.remaining_asn_credit), finance.has_asn_credit ? 'فعال' : 'بدون اعتبار')}${previsitMetricCard('جمع اعتبار قابل مشاهده', previsitMoney(finance.combined_remaining), `به‌روزرسانی ${finance.updated_at || 'نامشخص'}`)}${previsitMetricCard('چک باز', previsitMoney(finance.open_cheque_amount), previsitCount(finance.open_cheque_count, 'فقره'))}${previsitMetricCard('چک برگشتی', previsitMoney(finance.returned_cheque_amount), previsitCount(finance.returned_cheque_count, 'فقره'), Number(finance.returned_cheque_count || 0) ? 'is-danger' : 'is-good')}</div>`;

  $('#previsitHistoryContent').classList.remove('previsit-loading-card');
  $('#previsitHistoryContent').innerHTML = `<header class="previsit-content-heading"><div><span>تحلیل ثابت ۱۲ ماه اخیر</span><h4>سابقه و ریتم خرید</h4><p>مقایسه خرید کل شرکت با فروش همین بازاریاب.</p></div><b>آخرین خرید ${esc(analytics.last_invoice_date || 'ثبت نشده')}</b></header><div class="previsit-history-compare"><article><span>کل شرکت</span><strong>${previsitMoney(analytics.company_net_sales_12m)}</strong><small>${previsitCount(analytics.company_invoice_count_12m, 'فاکتور')}</small></article><article><span>فروش من</span><strong>${previsitMoney(analytics.seller_net_sales_12m)}</strong><small>${previsitCount(analytics.seller_invoice_count_12m, 'فاکتور')}</small></article></div><div class="previsit-metric-grid">${previsitMetricCard('ویزیت ثبت‌شده', previsitCount(customer.visit_count, 'بار'))}${previsitMetricCard('سفارش ثبت‌شده', previsitCount(customer.order_count, 'سفارش'))}${previsitMetricCard('ردیف سفارش', previsitCount(customer.order_line_count, 'ردیف'))}${previsitMetricCard('میانگین موفقیت ویزیت', `${Number(customer.avg_successful_visit || 0).toLocaleString('fa-IR', {style: 'percent', maximumFractionDigits: 0})}`)}</div>`;

  $('#previsitInterestsContent').classList.remove('previsit-loading-card');
  $('#previsitInterestsContent').innerHTML = `<header class="previsit-content-heading"><div><span>برگرفته از خرید واقعی</span><h4>علایق و برندهای مشتری</h4><p>این موارد «علاقه اعلام‌شده» نیستند؛ از خرید واقعی ۱۲ ماهه همراه با تعداد فاکتور، مبلغ، آخرین تاریخ و بازاریاب استخراج شده‌اند.</p></div></header><section class="previsit-brand-interest"><header><strong>برندهای لاین من</strong><small>بهترین نقطه شروع مذاکره</small></header>${previsitBrandCards(lineBrands)}</section><section class="previsit-brand-interest is-all"><header><strong>تمام برندهای خریداری‌شده</strong><small>شناخت سبد واقعی مشتری</small></header>${previsitBrandCards(allBrands)}</section>`;

  if (previsitEmbeddedProfile) renderEmbeddedPrevisitCustomerProfile();
  else applyPrevisitRequirementGate();
}

function renderPrevisitWorkspace() {
  if (!previsitWorkspace) return;
  const customer = previsitWorkspace.customer || {};
  const analytics = previsitWorkspace.analytics || {};
  const openInvoices = previsitWorkspace.open_invoices || {invoice_count: 0, invoices: []};
  const chequeIntelligence = previsitWorkspace.cheques || {summary: {}, cheques: []};
  const chequeSummary = chequeIntelligence.summary || {};
  const finance = customer.financial_snapshot || {};
  const title = customer.store_name || customer.name || customer.id;
  renderPrevisitCustomerHeader(customer, previsitWorkspace.route, previsitWorkspace.seller || previsitContext?.seller);
  const identity = $('#previsitVisitIdentity');
  identity.innerHTML = `<span class="previsit-identity-mark">${esc(String(title || 'م').trim().slice(0, 1))}</span><div><strong>${esc(title)}</strong><small>${esc(customer.code || '')} · ${esc(previsitWorkspace.route?.title || '')}</small></div>`;
  $('#previsitInvoiceRailBadge').textContent = `${previsitCount(openInvoices.invoice_count, 'فاکتور')} باز`;
  $('#previsitReturnedChequeRailBadge').textContent = chequeSummary.active_returned_count
    ? `${previsitCount(chequeSummary.active_returned_count, 'فقره')} فعال`
    : 'بدون برگشتی فعال';

  const reportControls = previsitPolicy?.controls?.reports || {};
  const canSeeInvoices = reportControls.open_invoices !== false;
  const canSeeCardex = reportControls.cardex !== false || reportControls.finance !== false;
  const canSeeHistory = reportControls.sale_history !== false || reportControls.invoices !== false;
  setPrevisitReportGate('invoices', canSeeInvoices);
  setPrevisitReportGate('cardex', canSeeCardex);
  setPrevisitReportGate('returned-cheques', canSeeCardex);
  setPrevisitReportGate('history', canSeeHistory);
  setPrevisitReportGate('interests', canSeeHistory);

  const lineBrands = analytics.line_purchased_brands || [];
  const allBrands = analytics.purchased_brands || [];
  const linePurchases = analytics.line_purchase_summary || [];
  const lineBrandNames = new Set(lineBrands.map((item) => String(item.name || '').trim()));
  const otherBrands = allBrands.filter((item) => !lineBrandNames.has(String(item.name || '').trim()));
  const invoiceRows = openInvoices.invoices || [];

  $('#previsitInvoicesContent').classList.remove('previsit-loading-card');
  $('#previsitInvoicesContent').innerHTML = `<header class="previsit-content-heading"><div><span>مطالبات این فروشنده از مشتری</span><h4>فاکتورهای باز</h4><p>فقط فاکتورهای باز متعلق به همین بازاریاب، مرتب‌شده از قدیمی‌ترین سند.</p></div><b>${previsitCount(openInvoices.invoice_count, 'سند')}</b></header>${invoiceRows.length ? `<div class="previsit-open-invoice-list">${invoiceRows.map((invoice) => `<article><div><strong>فاکتور ${esc(invoice.number || invoice.id)}</strong><small>${esc(invoice.date || 'بدون تاریخ')}</small></div><span><small>مبلغ فاکتور</small><b>${previsitMoney(invoice.amount)}</b></span><span class="is-remaining"><small>مانده</small><b>${previsitMoney(invoice.remaining_amount)}</b></span></article>`).join('')}</div>` : '<div class="previsit-empty-state"><span>✓</span><strong>فاکتور بازی برای این فروشنده دیده نشد</strong><small>داده از گزارش جاری وصول دریافت شده است.</small></div>'}`;

  $('#previsitCardexContent').classList.remove('previsit-loading-card');
  $('#previsitCardexContent').innerHTML = `<header class="previsit-content-heading"><div><span>تصویر کامل مالی در لحظه ویزیت</span><h4>اطلاعات مالی مشتری</h4><p>مانده کل مشتری و وضعیت چک‌ها شرکتی است؛ مانده فاکتور باز فقط به همین بازاریاب تعلق دارد.</p></div></header><section class="previsit-dashboard-section"><header><div><span>مانده و مطالبات</span><strong>حساب مشتری</strong></div><small>اطلاعات جاری</small></header><div class="previsit-metric-grid">${previsitMetricCard('مانده کاردکس کل مشتری', previsitMoney(customer.cardex_balance), 'Acc.vwCustomerBalance', 'is-finance')}${previsitMetricCard('مانده جاری', previsitMoney(finance.customer_remaining), 'آخرین تصویر اعتبار مشتری')}${previsitMetricCard('فاکتور باز این بازاریاب', previsitMoney(customer.open_invoice_remaining), previsitCount(openInvoices.invoice_count, 'فاکتور'), Number(customer.open_invoice_remaining || 0) ? 'is-warning' : 'is-good')}${previsitMetricCard('جمع اعتبار باقی‌مانده', previsitMoney(finance.combined_remaining), `به‌روزرسانی ${finance.updated_at || 'نامشخص'}`)}</div></section><section class="previsit-dashboard-section"><header><div><span>اعتبار و اسناد باز</span><strong>کنترل مالی پیش از سفارش</strong></div></header><div class="previsit-metric-grid">${previsitMetricCard('اعتبار بدهکاری باقی‌مانده', previsitMoney(finance.remaining_bed_credit), finance.has_bed_credit ? 'فعال' : 'بدون اعتبار')}${previsitMetricCard('اعتبار اسنادی باقی‌مانده', previsitMoney(finance.remaining_asn_credit), finance.has_asn_credit ? 'فعال' : 'بدون اعتبار')}${previsitMetricCard('چک باز', previsitMoney(finance.open_cheque_amount), previsitCount(finance.open_cheque_count, 'فقره'))}${previsitMetricCard('چک برگشتی فعال', previsitMoney(chequeSummary.active_returned_amount ?? finance.returned_cheque_amount), previsitCount(chequeSummary.active_returned_count ?? finance.returned_cheque_count, 'فقره'), Number(chequeSummary.active_returned_count ?? finance.returned_cheque_count ?? 0) ? 'is-danger' : 'is-good')}</div></section><section class="previsit-dashboard-section"><header><div><span>رفتار چک مشتری</span><strong>۱۲ ماه اخیر و رفع اثر برگشتی‌ها</strong></div><small>براساس شناسه پایدار هر چک</small></header><div class="previsit-metric-grid">${previsitMetricCard('چک‌های وصولی ۱۲ ماه اخیر', previsitMoney(chequeSummary.paid_12m_amount), previsitCount(chequeSummary.paid_12m_count, 'فقره'), 'is-good')}${previsitMetricCard('وصول پس از برگشت', previsitMoney(chequeSummary.collected_after_return_amount), previsitCount(chequeSummary.collected_after_return_count, 'فقره'))}${previsitMetricCard('برگشتی سپس مستردشده', previsitMoney(chequeSummary.refunded_after_return_amount), previsitCount(chequeSummary.refunded_after_return_count, 'فقره'))}${previsitMetricCard('برگشتی کاملاً تسویه‌شده', previsitMoney(chequeSummary.returned_settlement_amount), previsitCount(chequeSummary.fully_settled_returned_count, 'فقره'))}${previsitMetricCard('برگشتی در وضعیت حقوقی', previsitMoney(chequeSummary.legal_returned_amount), previsitCount(chequeSummary.legal_returned_count, 'فقره'), Number(chequeSummary.legal_returned_count || 0) ? 'is-danger' : '')}</div><p class="previsit-finance-note">«مستردشده» یعنی چک در تاریخچه برگشتی بوده و وضعیت جاری آن استرداد است؛ «کاملاً تسویه‌شده» فقط وقتی ثبت می‌شود که جمع تسویه‌های متصل به چک به مبلغ چک رسیده باشد.</p></section>`;

  $('#previsitReturnedChequesContent').classList.remove('previsit-loading-card');
  $('#previsitReturnedChequesContent').innerHTML = `<header class="previsit-content-heading"><div><span>ردیابی وضعیت واقعی ورانگر</span><h4>چک‌های برگشتی مشتری</h4><p>برگشتی فعال، وصول پس از برگشت، استرداد پس از برگشت و پرونده حقوقی از تاریخچه وضعیت چک تفکیک شده‌اند.</p></div><b>${previsitCount(chequeSummary.active_returned_count, 'برگشتی فعال')}</b></header>${previsitReturnedChequeCards(chequeIntelligence.cheques || [])}`;

  $('#previsitHistoryContent').classList.remove('previsit-loading-card');
  $('#previsitHistoryContent').innerHTML = `<header class="previsit-content-heading"><div><span>تحلیل ثابت ۱۲ ماه اخیر</span><h4>سابقه و ریتم خرید</h4><p>مقایسه خرید کل شرکت با فروش همین بازاریاب.</p></div><b>آخرین خرید ${esc(analytics.last_invoice_date || 'ثبت نشده')}</b></header><div class="previsit-history-compare"><article><span>کل شرکت</span><strong>${previsitMoney(analytics.company_net_sales_12m)}</strong><small>${previsitCount(analytics.company_invoice_count_12m, 'فاکتور')}</small></article><article><span>فروش من</span><strong>${previsitMoney(analytics.seller_net_sales_12m)}</strong><small>${previsitCount(analytics.seller_invoice_count_12m, 'فاکتور')}</small></article></div><div class="previsit-metric-grid">${previsitMetricCard('ویزیت ثبت‌شده', previsitCount(customer.visit_count, 'بار'))}${previsitMetricCard('سفارش ثبت‌شده', previsitCount(customer.order_count, 'سفارش'))}${previsitMetricCard('ردیف سفارش', previsitCount(customer.order_line_count, 'ردیف'))}${previsitMetricCard('میانگین موفقیت ویزیت', `${Number(customer.avg_successful_visit || 0).toLocaleString('fa-IR', {style: 'percent', maximumFractionDigits: 0})}`)}</div>`;

  $('#previsitInterestsContent').classList.remove('previsit-loading-card');
  $('#previsitInterestsContent').innerHTML = `<header class="previsit-content-heading"><div><span>برگرفته از خرید واقعی</span><h4>علایق و برندهای مشتری</h4><p>سبد واقعی ۱۲ ماهه، خرید هر لاین، برندها و آخرین بازاریاب همراه با شماره تماس در همین صفحه جمع شده‌اند.</p></div><b>امتیاز ویزیت ${previsitCount(analytics.visit_score)}</b></header><div class="previsit-metric-grid is-compact">${previsitMetricCard('خرید ۱۲ ماهه شرکت', previsitMoney(analytics.company_net_sales_12m), previsitCount(analytics.company_invoice_count_12m, 'فاکتور'))}${previsitMetricCard('خرید از من', previsitMoney(analytics.seller_net_sales_12m), previsitCount(analytics.seller_invoice_count_12m, 'فاکتور'))}${previsitMetricCard('آخرین خرید', analytics.last_invoice_date || 'ثبت نشده', 'کل شرکت')}${previsitMetricCard('برندهای خریداری‌شده', previsitCount(allBrands.length, 'برند'), previsitCount(lineBrands.length, 'برند از لاین من'))}</div><section class="previsit-brand-interest"><header><strong>خرید به تفکیک لاین</strong><small>مبلغ، تعداد فاکتور و آخرین بازاریاب</small></header>${previsitLinePurchaseCards(linePurchases)}</section><section class="previsit-brand-interest"><header><strong>برندهای لاین من</strong><small>بهترین نقطه شروع مذاکره</small></header>${previsitBrandCards(lineBrands)}</section><section class="previsit-brand-interest is-all"><header><strong>برندهای سایر لاین‌ها</strong><small>فرصت شناخت و فروش مکمل</small></header>${previsitBrandCards(otherBrands)}</section><section class="previsit-next-best-action"><strong>پیشنهاد اقدام</strong><div><span>۱</span><p>${lineBrands.length ? `از ${lineBrands.slice(0, 3).map((item) => esc(item.name)).join('، ')} شروع کنید.` : 'نیاز اصلی مشتری را مشخص کنید.'}</p></div><div><span>۲</span><p>برای هماهنگی بین لاین‌ها از شماره آخرین بازاریاب همان برند استفاده کنید.</p></div><div><span>۳</span><p>سبد را نهایی کنید.</p></div></section>`;

  if (previsitEmbeddedProfile) renderEmbeddedPrevisitCustomerProfile();
  else applyPrevisitRequirementGate();
}

function renderPrevisitWorkspaceError(message) {
  ['Invoices', 'Cardex', 'ReturnedCheques', 'History', 'Interests', 'Profile'].forEach((name) => {
    const panel = $(`#previsit${name}Content`);
    if (panel) panel.innerHTML = `<div class="previsit-empty-state is-error"><span>!</span><strong>اطلاعات مشتری در دسترس نیست</strong><small>${esc(message)}</small></div>`;
  });
  $('#previsitInvoiceRailBadge').textContent = 'خطا در دریافت';
  $('#previsitReturnedChequeRailBadge').textContent = 'خطا در دریافت';
}

async function loadPrevisitCustomerWorkspace(routeId, customerId) {
  previsitWorkspace = null;
  const response = await fetch(`/seller-workspace/routes/${encodeURIComponent(routeId)}/customers/${encodeURIComponent(customerId)}/visit-workspace`);
  const data = await readJsonResponse(response, 'اطلاعات میزکار مشتری دریافت نشد.');
  if (!response.ok) throw Error(data.detail || 'اطلاعات میزکار مشتری دریافت نشد.');
  previsitWorkspace = data;
  renderPrevisitWorkspace();
  return data;
}

const orderSpeechTokenAliases = Object.freeze({
  مسوک:'میسویک', میسوک:'میسویک', میسیوک:'میسویک', میسوییک:'میسویک',
  امبرلا:'آمبرلا', امبرللا:'آمبرلا', جنٹل:'جنتل', کانفیدچت:'کانفیدنت',
  کانفیدنتت:'کانفیدنت', شاینن:'شاین', لمنت:'لمینت', لامینت:'لمینت',
  دندون:'دندان', دونه:'عدد', پک:'بسته', پکت:'بسته',
  کارتون:'کارتن', کرتن:'کارتن', کارتُن:'کارتن',
});

function normalizeOrderCommand(value) {
  const digits = '۰۱۲۳۴۵۶۷۸۹';
  let normalized = String(value || '').toLocaleLowerCase('fa').replace(/[يى]/g, 'ی').replace(/ك/g, 'ک')
    .replace(/خمیر\s*دند(?:ان|ون)/g, 'خمیر دندان')
    .replace(/ضد\s*زردی/g, 'ضد زردی').replace(/ضد\s*تعریق/g, 'ضدتعریق')
    .replace(/[۰-۹]/g, (digit) => String(digits.indexOf(digit)))
    .replace(/[٠-٩]/g, (digit) => String('٠١٢٣٤٥٦٧٨٩'.indexOf(digit)))
    .replace(/[‌\-_،,؛;:.!؟?()[\]{}]/g, ' ').replace(/\s+/g, ' ').trim();
  return normalized.split(' ').map((token) => orderSpeechTokenAliases[token] || token).join(' ');
}

function catalogPhoneticSignature(value) {
  let token = normalizeOrderCommand(value).replace(/\s+/g, '');
  if (/[a-z]/i.test(token)) {
    token = token.toLowerCase()
      .replace(/sh/g, 'ش').replace(/ch/g, 'چ').replace(/zh/g, 'ژ')
      .replace(/kh/g, 'خ').replace(/gh/g, 'ق').replace(/ph/g, 'ف')
      .replace(/th/g, 'ت').replace(/ck/g, 'ک').replace(/qu/g, 'ک')
      .replace(/[aeiouy]/g, '')
      .replace(/[a-z]/g, (letter) => ({b:'ب',c:'ک',d:'د',f:'ف',g:'گ',h:'ه',j:'ج',k:'ک',l:'ل',m:'م',n:'ن',p:'پ',q:'ق',r:'ر',s:'س',t:'ت',v:'و',w:'و',x:'کس',z:'ز'}[letter] || letter));
  }
  return token.replace(/[اآإأویيى]/g, '')
    .replace(/[صث]/g, 'س').replace(/[ذضظ]/g, 'ز').replace(/ط/g, 'ت')
    .replace(/ة/g, 'ه').replace(/ه$/g, '');
}

function crossScriptCatalogToken(left, right) {
  const leftLatin = /[a-z]/i.test(left);
  const rightLatin = /[a-z]/i.test(right);
  const leftPersian = /[\u0600-\u06ff]/.test(left);
  const rightPersian = /[\u0600-\u06ff]/.test(right);
  if (!((leftLatin && rightPersian) || (rightLatin && leftPersian))) return false;
  const leftSignature = catalogPhoneticSignature(left);
  const rightSignature = catalogPhoneticSignature(right);
  return leftSignature.length >= 3 && leftSignature === rightSignature;
}

function commandProductTokens(product) {
  const stopWords = new Set(['برای', 'با', 'و', 'از', 'در', 'به', 'مدل', 'نوع', 'عدد', 'دونه']);
  return [...new Set(normalizeOrderCommand(`${product.name || ''} ${product.brand || ''} ${product.description || ''} ${product.group || ''} ${product.manufacturer || ''}`).split(' ')
    .filter((token) => token.length > 1 && !stopWords.has(token)))];
}

const spokenOrderNumberValues = Object.freeze({
  صفر: 0, یه: 1, یک: 1, دو: 2, سه: 3, چهار: 4, پنج: 5, شش: 6, هفت: 7, هشت: 8, نه: 9,
  ده: 10, یازده: 11, دوازده: 12, سیزده: 13, چهارده: 14, پانزده: 15, شانزده: 16,
  هفده: 17, هجده: 18, نوزده: 19, بیست: 20, سی: 30, چهل: 40, پنجاه: 50,
  شصت: 60, هفتاد: 70, هشتاد: 80, نود: 90, صد: 100, یکصد: 100,
  دویست: 200, سیصد: 300, چهارصد: 400, پانصد: 500, ششصد: 600,
  هفتصد: 700, هشتصد: 800, نهصد: 900,
});

const spokenOrderUnitAliases = Object.freeze({
  تا: 'عدد', عدد: 'عدد', دانه: 'عدد', واحد: 'عدد',
  بسته: 'بسته', کارتن: 'کارتن',
});

function spokenOrderUnitName(value) {
  const normalized = normalizeOrderCommand(value);
  if (spokenOrderUnitAliases[normalized]) return spokenOrderUnitAliases[normalized];
  const knownUnit = (previsitContext?.products || []).flatMap((product) => previsitSaleUnits(product))
    .find((unit) => normalizeOrderCommand(unit.name) === normalized);
  return knownUnit ? normalizeOrderCommand(knownUnit.name) : '';
}

function parseSpokenOrderNumber(tokens) {
  if (!tokens.length || tokens.some((token) => token !== 'و' && token !== 'هزار' && spokenOrderNumberValues[token] === undefined)) return null;
  let total = 0;
  let section = 0;
  let hasNumber = false;
  tokens.forEach((token) => {
    if (token === 'و') return;
    hasNumber = true;
    if (token === 'هزار') {
      total += (section || 1) * 1000;
      section = 0;
    } else {
      section += spokenOrderNumberValues[token];
    }
  });
  return hasNumber ? total + section : null;
}

function commandQuantityMentions(command) {
  const source = normalizeOrderCommand(command);
  const tokens = source.split(' ');
  const mentions = [];
  for (let unitIndex = 0; unitIndex < tokens.length; unitIndex += 1) {
    const unit = spokenOrderUnitName(tokens[unitIndex]);
    if (!unit) continue;
    const numeric = tokens[unitIndex - 1]?.match(/^\d+(?:\.\d+)?$/);
    if (numeric) {
      mentions.push({quantity: Number(numeric[0]), unit, start: unitIndex - 1, end: unitIndex});
      continue;
    }
    const numberTokens = [];
    let numberStart = unitIndex;
    for (let index = unitIndex - 1; index >= 0 && numberTokens.length < 9; index -= 1) {
      const token = tokens[index];
      if (token !== 'و' && token !== 'هزار' && spokenOrderNumberValues[token] === undefined) break;
      numberTokens.unshift(token);
      numberStart = index;
    }
    const quantity = parseSpokenOrderNumber(numberTokens);
    if (quantity !== null) mentions.push({quantity, unit, start: numberStart, end: unitIndex});
  }
  return {source, tokens, mentions};
}

function commandQuantity(command) {
  return commandQuantityMentions(command).mentions[0]?.quantity ?? null;
}

function commandDetectedBrands(command) {
  const source = normalizeOrderCommand(command);
  const products = previsitContext?.products || [];
  const catalogueBrands = [...new Set(products.map((product) => normalizeOrderCommand(product.brand || '')).filter((brand) => brand.length > 1))];
  const exact = catalogueBrands.filter((brand) => source.includes(brand)).sort((a, b) => b.length - a.length);
  if (exact.length) return exact;
  const sourceTokens = source.split(' ').filter((token) => token.length > 1);
  const phonetic = catalogueBrands.map((brand) => {
    const tokens = brand.split(' ').filter((token) => token.length > 1);
    const matched = tokens.filter((token) => sourceTokens.some((heard) => crossScriptCatalogToken(heard, token))).length;
    return {brand, matched, score: tokens.length ? matched / tokens.length : 0};
  }).filter((item) => item.matched > 0)
    .sort((a, b) => b.score - a.score || b.matched - a.matched || b.brand.length - a.brand.length);
  if (!phonetic.length) return [];
  return phonetic.filter((item) => item.score === phonetic[0].score && item.matched === phonetic[0].matched).map((item) => item.brand);
}

function parseOrderCommandItems(command) {
  const {source, tokens, mentions} = commandQuantityMentions(command);
  if (!mentions.length) return [];
  const leadingFillers = new Set(['لطفا', 'لطفاً', 'بزن', 'بده', 'اضافه', 'کن', 'واسه', 'برای', 'از', 'هر', 'کدام']);
  const prefixQuantities = tokens.slice(0, mentions[0].start).every((token) => leadingFillers.has(token));
  const cleanItem = (itemTokens) => {
    const cleaned = [...itemTokens];
    while (['و', 'بعد', 'سپس', 'همچنین'].includes(cleaned[0])) cleaned.shift();
    while (['و', 'بعد', 'سپس', 'همچنین'].includes(cleaned[cleaned.length - 1])) cleaned.pop();
    return cleaned.join(' ').trim();
  };
  return mentions.map((mention, index) => {
    const itemTokens = prefixQuantities
      ? tokens.slice(mention.end + 1, mentions[index + 1]?.start ?? tokens.length)
      : tokens.slice(index ? mentions[index - 1].end + 1 : 0, mention.start);
    return {quantity: mention.quantity, unit: mention.unit, command: cleanItem(itemTokens)};
  }).filter((item) => item.quantity > 0 && item.command);
}

function commandMatches(command) {
  const source = normalizeOrderCommand(command);
  const products = previsitContext?.products || [];
  const catalogueBrands = [...new Set(products.map((product) => normalizeOrderCommand(product.brand || '')).filter((brand) => brand.length > 1))];
  const brands = catalogueBrands
    .filter((brand) => source.includes(brand)).sort((a, b) => b.length - a.length);
  let brand = brands[0] || '';
  if (!brand) {
    const sourceTokens = source.split(' ').filter((token) => token.length > 1);
    const phoneticBrands = catalogueBrands.map((candidate) => {
      const tokens = candidate.split(' ').filter((token) => token.length > 1);
      const matched = tokens.filter((token) => sourceTokens.some((heard) => crossScriptCatalogToken(heard, token))).length;
      return {candidate, matched, score: tokens.length ? matched / tokens.length : 0};
    }).filter((item) => item.matched > 0)
      .sort((a, b) => b.score - a.score || b.matched - a.matched || b.candidate.length - a.candidate.length);
    if (phoneticBrands.length && !(phoneticBrands[1] && phoneticBrands[1].score === phoneticBrands[0].score && phoneticBrands[1].matched === phoneticBrands[0].matched)) {
      brand = phoneticBrands[0].candidate;
    }
  }
  const ignored = new Set(['بزن', 'بده', 'اضافه', 'کن', 'کنید', 'واسه', 'برای', 'هر', 'کدام', 'تا', 'عدد', 'دونه', 'بسته', 'کارتن', 'لطفا']);
  const brandTokens = brand.split(' ').filter((token) => token.length > 1);
  const queryTokens = [...new Set(source.split(' ').filter((token) => token.length > 1 && !/^\d+(?:\.\d+)?$/.test(token) && spokenOrderNumberValues[token] === undefined && token !== 'هزار' && !ignored.has(token) && !brandTokens.some((brandToken) => token === brandToken || crossScriptCatalogToken(token, brandToken))))];
  const equivalents = {
    مام: new Set(['مام', 'استیک', 'دئودورانت', 'ضدتعریق']),
    استیک: new Set(['مام', 'استیک', 'دئودورانت']),
    دندان: new Set(['دندان', 'دندون']),
  };
  const closeToken = (query, candidate) => {
    if (query === candidate || equivalents[query]?.has(candidate) || equivalents[candidate]?.has(query) || crossScriptCatalogToken(query, candidate)) return true;
    if (query.length >= 4 && candidate.length >= 4 && (query.includes(candidate) || candidate.includes(query))) return true;
    if (Math.abs(query.length - candidate.length) > 1 || query.length < 4) return false;
    let edits = 0, left = 0, right = 0;
    while (left < query.length && right < candidate.length) {
      if (query[left] === candidate[right]) { left += 1; right += 1; continue; }
      edits += 1;
      if (edits > 1) return false;
      if (query.length > candidate.length) left += 1;
      else if (candidate.length > query.length) right += 1;
      else { left += 1; right += 1; }
    }
    return edits + (query.length - left) + (candidate.length - right) <= 1;
  };
  const exactToken = (query, candidate) => query === candidate
    || equivalents[query]?.has(candidate)
    || equivalents[candidate]?.has(query)
    || crossScriptCatalogToken(query, candidate);
  const brandProducts = products.filter((product) => {
    if (!brand) return true;
    const productBrand = normalizeOrderCommand(product.brand || '');
    return productBrand === brand || normalizeOrderCommand(product.name || '').includes(brand);
  }).map((product) => ({
    product,
    skuTokens: commandProductTokens({...product, brand: ''}).filter((token) => !brandTokens.some((brandToken) => token === brandToken || crossScriptCatalogToken(token, brandToken))),
  }));
  // Exact words in this brand win globally. For example, when a real "شاین"
  // SKU exists, edit-distance matching must never turn "فاین" into a result.
  const exactQueries = new Set(queryTokens.filter((query) =>
    brandProducts.some(({skuTokens}) => skuTokens.some((candidate) => exactToken(query, candidate)))));
  const candidates = brandProducts.map(({product, skuTokens}) => {
    const matchedTerms = queryTokens.filter((query) => skuTokens.some((candidate) =>
      exactQueries.has(query) ? exactToken(query, candidate) : closeToken(query, candidate)));
    const score = queryTokens.length ? matchedTerms.length / queryTokens.length : 0;
    const satisfiesExactTerms = [...exactQueries].every((query) =>
      skuTokens.some((candidate) => exactToken(query, candidate)));
    return {product, score, matched: matchedTerms.length, matchedTerms, brand, satisfiesExactTerms};
  }).filter((item) => item.satisfiesExactTerms && (queryTokens.length ? item.matched > 0 : true))
    .sort((a, b) => b.score - a.score || b.matched - a.matched || Number(b.product.available_qty || 0) - Number(a.product.available_qty || 0));
  if (!candidates.length) return [];
  const bestScore = candidates[0].score;
  return candidates.filter((item) => item.score >= Math.max(0.25, bestScore - 0.15)).slice(0, 6);
}

function syncOrderCommandVoiceButtons(label = '🎙 گفتن دستور', options = {}) {
  const recording = Boolean(options.recording);
  const disabled = Boolean(options.disabled);
  const compactLabel = recording ? 'پایان' : label.includes('تبدیل') ? 'تبدیل صدا' : label.includes('اتصال') ? 'اتصال…' : 'صوتی';
  [$('#recordPrevisitOrderCommand'), $('#previsitFloatingVoice')].filter(Boolean).forEach((button) => {
    button.disabled = disabled;
    button.classList.toggle('is-recording', recording);
    button.setAttribute('aria-pressed', String(recording));
    button.setAttribute('aria-label', label.replace(/^[🎙■]\s*/, ''));
    const compact = button.querySelector('[data-voice-label]');
    if (compact) compact.textContent = compactLabel;
    else button.textContent = label;
  });
}

async function toggleOrderCommandVoice() {
  const button = $('#recordPrevisitOrderCommand');
  if (orderCommandNativeRecording) {
    syncOrderCommandVoiceButtons('■ پایان گفتن', {recording: true, disabled: true});
    try {
      if (!window.NeginAndroid?.stopOrderVoiceRecording?.()) throw new Error('Native recorder is unavailable');
    } catch (error) {
      orderCommandNativeRecording = false;
      syncOrderCommandVoiceButtons();
      reportVoiceFailure('native-order-voice-stop', error, 'audio/mp4');
      toast('پایان ضبط دستور انجام نشد؛ دوباره تلاش کنید.');
    }
    return;
  }
  if (orderCommandRecorder) {
    syncOrderCommandVoiceButtons('■ پایان گفتن', {recording: true, disabled: true});
    orderCommandRecorder.stop();
    return;
  }
  if (isNeginAndroidApp && window.NeginAndroid?.requestMicrophonePermission) {
    let granted = false;
    try { granted = Boolean(window.NeginAndroid.hasMicrophonePermission?.()); } catch (_) {}
    if (!granted) {
      orderCommandAwaitingNativePermission = true;
      try { granted = Boolean(window.NeginAndroid.requestMicrophonePermission()); } catch (_) {}
      if (!granted) {
        toast('در پنجره اندروید، دسترسی میکروفن را مجاز کنید.');
        return;
      }
      orderCommandAwaitingNativePermission = false;
    }
    if (window.NeginAndroid?.startOrderVoiceRecording) {
      syncOrderCommandVoiceButtons('در حال اتصال به میکروفن…', {disabled: true});
      try {
        if (!window.NeginAndroid.startOrderVoiceRecording()) throw new Error('Microphone permission is unavailable');
      } catch (error) {
        syncOrderCommandVoiceButtons();
        reportVoiceFailure('native-order-voice-start', error, 'audio/mp4');
        toast('ضبط دستور شروع نشد؛ دسترسی میکروفن را بررسی کنید.');
      }
      return;
    }
  }
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) return toast('ضبط صدا در این مرورگر پشتیبانی نمی‌شود.');
  try {
    orderCommandStream = await navigator.mediaDevices.getUserMedia({audio: true});
    orderCommandChunks = [];
    orderCommandRecorder = new MediaRecorder(orderCommandStream);
    orderCommandRecorder.ondataavailable = (event) => { if (event.data.size) orderCommandChunks.push(event.data); };
    orderCommandRecorder.onstop = () => void transcribeOrderCommandVoice();
    orderCommandRecorder.start(250);
    syncOrderCommandVoiceButtons('■ پایان گفتن', {recording: true});
  } catch (error) {
    reportVoiceFailure('order-voice-start', error, orderCommandRecorder?.mimeType || '');
    toast(error.name === 'NotAllowedError' ? 'اجازه میکروفن را برای این سایت فعال کنید.' : 'ضبط دستور شروع نشد.');
  }
}

window.addEventListener('negin-microphone-permission', (event) => {
  if (!orderCommandAwaitingNativePermission) return;
  orderCommandAwaitingNativePermission = false;
  if (event.detail?.granted) void toggleOrderCommandVoice();
  else toast('مجوز میکروفن رد شد؛ آن را از تنظیمات «نگین فروش» فعال کنید.');
});

function base64AudioBlob(base64, mimeType = 'audio/mp4') {
  const binary = atob(String(base64 || ''));
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
  return new Blob([bytes], {type: mimeType});
}

window.addEventListener('negin-native-order-voice', (event) => {
  const button = $('#recordPrevisitOrderCommand');
  if (!button) return;
  const state = event.detail?.state;
  if (state === 'started') {
    orderCommandNativeRecording = true;
    syncOrderCommandVoiceButtons('■ پایان گفتن', {recording: true});
    return;
  }
  orderCommandNativeRecording = false;
  syncOrderCommandVoiceButtons();
  if (state === 'completed' && event.detail?.audioBase64) {
    try {
      void transcribeOrderCommandVoice(base64AudioBlob(event.detail.audioBase64, event.detail.mimeType));
    } catch (error) {
      reportVoiceFailure('native-order-voice-decode', error, event.detail?.mimeType || 'audio/mp4');
      toast('فایل ضبط‌شده خوانده نشد؛ دوباره تلاش کنید.');
    }
  } else {
    reportVoiceFailure('native-order-voice-failed', new Error(event.detail?.message || 'Native recording failed'), 'audio/mp4');
    toast('ضبط دستور شروع نشد؛ برنامه‌های دیگری که از میکروفن استفاده می‌کنند را ببندید.');
  }
});

async function transcribeOrderCommandVoice(recordedBlob = null) {
  const button = $('#recordPrevisitOrderCommand');
  const stream = orderCommandStream;
  const recorder = orderCommandRecorder;
  orderCommandStream = null;
  orderCommandRecorder = null;
  stream?.getTracks().forEach((track) => track.stop());
  syncOrderCommandVoiceButtons();
  const blob = recordedBlob || new Blob(orderCommandChunks, {type: recorder?.mimeType || 'audio/webm'});
  if (blob.size < 128) return toast('صدایی دریافت نشد؛ دوباره امتحان کنید.');
  syncOrderCommandVoiceButtons('در حال تبدیل صدا…', {disabled: true});
  try {
    const transcriptionQuery = new URLSearchParams({
      mode: 'order',
      path_id: $('#previsitRoute').value,
      customer_id: $('#previsitCustomer').value,
    });
    const response = await fetch(`/audio/transcriptions?${transcriptionQuery}`, {method: 'POST', headers: {'Content-Type': blob.type}, body: blob});
    const data = await response.json();
    if (!response.ok) throw Error(data.detail || 'تبدیل صدا انجام نشد.');
    const spokenCommand = String(data.text || '').trim();
    if (!spokenCommand) throw Error('متنی از صدای دستور دریافت نشد؛ دوباره امتحان کنید.');
    $('#previsitOrderCommand').value = spokenCommand;
    runPrevisitOrderCommand({source: 'voice'});
  } catch (error) {
    toast(error.message);
  } finally {
    syncOrderCommandVoiceButtons();
  }
}

function spokenOrderSaleUnit(product, requestedUnit) {
  const requested = spokenOrderUnitName(requestedUnit) || normalizeOrderCommand(requestedUnit);
  const units = previsitSaleUnits(product);
  const exact = units.find((unit) => normalizeOrderCommand(unit.name) === requested);
  if (exact) return exact;
  if (requested === 'عدد') return units.find((unit) => Number(unit.factor) === 1) || null;
  if (requested === 'کارتن') {
    const cartonFactor = Number(product?.carton_size || 0);
    return units.find((unit) => normalizeOrderCommand(unit.name).split(' ').includes('کارتن'))
      || units.find((unit) => cartonFactor > 1 && Number(unit.factor) === cartonFactor)
      || null;
  }
  if (requested === 'بسته') {
    return units.find((unit) => ['بسته', 'پک'].some((word) => normalizeOrderCommand(unit.name).split(' ').includes(word))) || null;
  }
  return null;
}

function previsitVoiceOrderConversion(product, quantity, requestedUnit) {
  const amount = Math.max(0, Number(quantity || 0));
  const saleUnit = spokenOrderSaleUnit(product, requestedUnit);
  if (!product || !(amount > 0) || !saleUnit) {
    return {ok: false, message: `واحد «${requestedUnit || 'نامشخص'}» برای این کالا مجاز نیست.`};
  }
  const baseQuantity = amount * Number(saleUnit.factor || 1);
  const available = Number(product.available_qty || 0);
  const currentQuantity = previsitCartQuantity(product.id);
  if (available < currentQuantity + baseQuantity) {
    return {
      ok: false,
      saleUnit,
      baseQuantity,
      message: `موجودی ${product.name} با احتساب مقدار فعلی سبد برای ${amount.toLocaleString('fa-IR')} ${saleUnit.name} کافی نیست.`,
    };
  }
  return {ok: true, saleUnit, baseQuantity, amount};
}

function addPrevisitVoiceLine(product, quantity, requestedUnit) {
  const conversion = previsitVoiceOrderConversion(product, quantity, requestedUnit);
  if (!conversion.ok) return conversion;
  const quantities = {...previsitListUnitQuantities(product)};
  const unitKey = previsitUnitKey(conversion.saleUnit);
  quantities[unitKey] = Number(quantities[unitKey] || 0) + conversion.amount;
  previsitProductUnitQuantities.set(String(product.id), quantities);
  addPrevisitLine({product_id: product.id, quantity: conversion.baseQuantity});
  return conversion;
}

function renderOrderCommandChoices(matches, quantity, unit, message) {
  const result = $('#previsitOrderAssistantResult');
  result.hidden = false;
  result.innerHTML = orderCommandChoiceGroupHtml(matches, quantity, unit, message);
}

function orderCommandChoiceGroupHtml(matches, quantity, unit, message) {
  return `<section data-previsit-command-group><strong>${esc(message)}</strong>${matches.map(({product, matchedTerms = []}) => {
    const available = Number(product.available_qty || 0);
    const conversion = previsitVoiceOrderConversion(product, quantity, unit);
    const unitLabel = conversion.saleUnit?.name || unit;
    const quantityLabel = conversion.saleUnit && Number(conversion.saleUnit.factor || 1) !== 1
      ? `${quantity.toLocaleString('fa-IR')} ${unitLabel} = ${Number(conversion.baseQuantity || 0).toLocaleString('fa-IR')} ${product.unit || 'عدد'}`
      : `${quantity.toLocaleString('fa-IR')} ${unitLabel}`;
    return `<button type="button" data-previsit-command-product="${esc(product.id)}" data-previsit-command-quantity="${esc(quantity)}" data-previsit-command-unit="${esc(unit)}" ${conversion.ok ? '' : 'disabled'}><span>${esc(product.name)}</span><small>${esc(product.brand || '')} · ${esc(quantityLabel)} · کد ${esc(product.code || product.id)} · موجودی ${available.toLocaleString('fa-IR')}${matchedTerms.length ? ` · تطبیق ${matchedTerms.map(esc).join('، ')}` : ''}${conversion.ok ? '' : ` · ${esc(conversion.message)}`}</small></button>`;
  }).join('')}</section>`;
}

function revealPrevisitVoiceOrderResult() {
  togglePrevisitOrderPanel('assistant', true);
  requestAnimationFrame(() => $('#previsitOrderAssistantResult')?.scrollIntoView({block: 'center', behavior: 'smooth'}));
}

function runPrevisitOrderCommand(options = {}) {
  const voiceSource = options?.source === 'voice';
  const command = $('#previsitOrderCommand')?.value || '';
  const result = $('#previsitOrderAssistantResult');
  if (!previsitContext?.products?.length) {
    toast('ابتدا کاتالوگ مجاز فروشنده را دریافت کنید.');
    return {addedCount: 0, requiresAttention: true};
  }
  const items = parseOrderCommandItems(command);
  if (!items.length) {
    result.hidden = false;
    result.textContent = 'تعداد را هم بگویید؛ مثلاً «از هر کدام ۱۰ تا». ';
    if (voiceSource) revealPrevisitVoiceOrderResult();
    return {addedCount: 0, requiresAttention: true};
  }
  const detectedBrands = commandDetectedBrands(command);
  const sharedBrand = detectedBrands.length === 1 ? detectedBrands[0] : '';
  const added = [];
  const unresolved = [];
  const choiceGroups = [];
  items.forEach((item, itemIndex) => {
    const itemSource = sharedBrand && !normalizeOrderCommand(item.command).includes(sharedBrand)
      ? `${item.command} ${sharedBrand}` : item.command;
    const matches = commandMatches(itemSource);
    const unique = matches.filter((match, index, all) => !all.slice(0, index).some((other) => other.product.id === match.product.id));
    if (!unique.length) {
      unresolved.push(`قلم ${itemIndex + 1}: «${item.command}»`);
      return;
    }
    if (unique.length > 1) {
      choiceGroups.push(orderCommandChoiceGroupHtml(unique, item.quantity, item.unit, `قلم ${itemIndex + 1} با تعداد ${item.quantity.toLocaleString('fa-IR')} ${item.unit}: کالای درست را انتخاب کنید.`));
      return;
    }
    const exact = unique[0];
    const conversion = addPrevisitVoiceLine(exact.product, item.quantity, item.unit);
    if (!conversion.ok) {
      choiceGroups.push(orderCommandChoiceGroupHtml(unique, item.quantity, item.unit, conversion.message));
      return;
    }
    const conversionText = Number(conversion.saleUnit.factor || 1) === 1
      ? `${item.quantity.toLocaleString('fa-IR')} ${conversion.saleUnit.name}`
      : `${item.quantity.toLocaleString('fa-IR')} ${conversion.saleUnit.name} (${conversion.baseQuantity.toLocaleString('fa-IR')} ${exact.product.unit || 'عدد'})`;
    added.push(`${exact.product.name} × ${conversionText}`);
  });
  result.hidden = false;
  const summaries = [];
  if (sharedBrand) summaries.push(`برند مشترک تشخیص‌داده‌شده: ${sharedBrand}`);
  if (added.length) summaries.push(`به سبد اضافه شد: ${added.join('، ')}`);
  if (unresolved.length) summaries.push(`تطبیق نشد: ${unresolved.join('، ')}`);
  result.innerHTML = `<strong>${esc(summaries.join(' — ') || 'نتیجه تطبیق')}</strong>${choiceGroups.join('')}`;
  const requiresAttention = Boolean(choiceGroups.length || unresolved.length);
  if (!requiresAttention) {
    $('#previsitOrderCommand').value = '';
    if (voiceSource) toast(`${added.length.toLocaleString('fa-IR')} قلم از دستور صوتی به سبد اضافه شد.`);
    switchPrevisitView('cart');
  } else if (voiceSource) revealPrevisitVoiceOrderResult();
  return {addedCount: added.length, requiresAttention};
}

function previsitCatalogTextCompare(left, right) {
  const leftText = String(left || '').trim();
  const rightText = String(right || '').trim();
  if (!leftText && rightText) return 1;
  if (leftText && !rightText) return -1;
  return leftText.localeCompare(rightText, 'fa', {numeric: true, sensitivity: 'base'});
}

function previsitProductHierarchyCompare(a, b, withinGroup = 'code') {
  const brandOrder = previsitCatalogTextCompare(a.brand || a.manufacturer, b.brand || b.manufacturer);
  if (brandOrder) return brandOrder;
  const parentGroupOrder = previsitCatalogTextCompare(
    a.group_parent || a.group,
    b.group_parent || b.group,
  );
  if (parentGroupOrder) return parentGroupOrder;
  const smallestGroupOrder = previsitCatalogTextCompare(
    a.smallest_group || a.group,
    b.smallest_group || b.group,
  );
  if (smallestGroupOrder) return smallestGroupOrder;
  if (withinGroup === 'stock_desc') {
    const stockOrder = Number(b.available_qty || 0) - Number(a.available_qty || 0);
    if (stockOrder) return stockOrder;
  }
  if (withinGroup === 'price_asc') {
    const priceOrder = Number(a.indicative_price || 0) - Number(b.indicative_price || 0);
    if (priceOrder) return priceOrder;
  }
  if (withinGroup === 'price_desc') {
    const priceOrder = Number(b.indicative_price || 0) - Number(a.indicative_price || 0);
    if (priceOrder) return priceOrder;
  }
  const codeOrder = previsitCatalogTextCompare(a.code || a.id, b.code || b.id);
  if (codeOrder) return codeOrder;
  return previsitCatalogTextCompare(a.name, b.name);
}

function currentPrevisitCatalogProducts() {
  if (!previsitContext) return [];
  return (previsitContext.products || []).map(previsitProductAtSelectedConditions).filter((product) => {
    const haystack = `${product.id} ${product.code} ${product.barcode || ''} ${product.name} ${product.brand} ${product.group_parent || ''} ${product.smallest_group || product.group || ''} ${product.manufacturer || ''}`.toLocaleLowerCase('fa');
    return (!previsitCatalogState.query || haystack.includes(previsitCatalogState.query))
      && (!previsitCatalogState.brand || product.brand === previsitCatalogState.brand)
      && (!previsitCatalogState.group || String(product.group_id) === previsitCatalogState.group)
      && (!previsitCatalogState.inStock || Number(product.available_qty) > 0);
  }).sort((a, b) => previsitProductHierarchyCompare(a, b, previsitCatalogState.sort));
}

function currentPrevisitQuickProducts() {
  if (!previsitContext) return [];
  return (previsitContext.products || []).map(previsitProductAtSelectedConditions).filter((product) => {
    const haystack = `${product.id} ${product.code} ${product.barcode || ''} ${product.name} ${product.brand} ${product.group_parent || ''} ${product.smallest_group || product.group || ''}`.toLocaleLowerCase('fa');
    return (!previsitQuickFilterState.query || haystack.includes(previsitQuickFilterState.query))
      && (!previsitQuickFilterState.group || String(product.group_id) === previsitQuickFilterState.group)
      && (!previsitQuickFilterState.brand || product.brand === previsitQuickFilterState.brand);
  }).sort((a, b) => previsitProductHierarchyCompare(a, b));
}

function currentPrevisitListProducts() {
  if (!previsitContext) return [];
  return (previsitContext.products || []).map(previsitProductAtSelectedConditions).filter((product) => {
    const haystack = `${product.id} ${product.code} ${product.barcode || ''} ${product.name} ${product.brand || ''} ${product.group_parent || ''} ${product.smallest_group || product.group || ''} ${product.manufacturer || ''}`.toLocaleLowerCase('fa');
    return (!previsitListState.query || haystack.includes(previsitListState.query))
      && (!previsitListState.brand || product.brand === previsitListState.brand)
      && (!previsitListState.group || String(product.group_id) === previsitListState.group)
      && (!previsitListState.inStock || Number(product.available_qty) > 0);
  }).sort((a, b) => previsitProductHierarchyCompare(a, b));
}

function renderPrevisitListFilters() {
  const brandRail = $('#previsitListBrands');
  const groupRail = $('#previsitListGroups');
  if (!brandRail || !groupRail || !previsitContext) return;
  const products = (previsitContext.products || []).map(previsitProductAtSelectedConditions);
  const brands = [...new Set(products.map((item) => item.brand).filter(Boolean))]
    .sort((a, b) => String(a).localeCompare(String(b), 'fa'));
  if (previsitListState.brand && !brands.includes(previsitListState.brand)) {
    previsitListState.brand = '';
    previsitListState.group = '';
  }
  brandRail.innerHTML = `<button type="button" data-previsit-list-brand="" class="${previsitListState.brand ? '' : 'is-active'}">همه برندها</button>`
    + brands.map((name) => `<button type="button" data-previsit-list-brand="${esc(name)}" class="${previsitListState.brand === name ? 'is-active' : ''}">${esc(name)}</button>`).join('');
  const groups = [...new Map(products
    .filter((item) => (!previsitListState.brand || item.brand === previsitListState.brand) && item.group)
    .map((item) => [String(item.group_id), item.group])).entries()]
    .sort((a, b) => String(a[1]).localeCompare(String(b[1]), 'fa'));
  if (!groups.some(([id]) => id === previsitListState.group)) previsitListState.group = '';
  groupRail.innerHTML = `<button type="button" data-previsit-list-group="" class="${previsitListState.group ? '' : 'is-active'}">${previsitListState.brand ? 'همه گروه‌های این برند' : 'همه گروه‌ها'}</button>`
    + groups.map(([id, name]) => `<button type="button" data-previsit-list-group="${esc(id)}" class="${previsitListState.group === id ? 'is-active' : ''}">${esc(name)}</button>`).join('');
}

function renderPrevisitProductList() {
  const root = $('#previsitListProducts');
  if (!root || !previsitContext) return;
  const products = currentPrevisitListProducts();
  $('#previsitListCount').textContent = `${products.length.toLocaleString('fa-IR')} ${previsitListState.inStock ? 'کالای موجود' : 'کالا'}`;
  const stockToggle = $('#previsitListStockToggle');
  stockToggle.classList.toggle('is-active', previsitListState.inStock);
  stockToggle.setAttribute('aria-pressed', String(previsitListState.inStock));
  const money = (value) => Number(value || 0) > 0 ? `${Number(value).toLocaleString('fa-IR')} ریال` : '—';
  root.innerHTML = products.length ? products.map((product) => {
    const inCart = previsitCartQuantity(product.id);
    const available = previsitAvailableBaseQuantity(product);
    const saleUnits = previsitSaleUnits(product);
    const unitQuantities = previsitListUnitQuantities(product);
    const unitRows = saleUnits.map((unit) => {
      const unitKey = previsitUnitKey(unit);
      const quantity = Number(unitQuantities[unitKey] || 0);
      return `<div class="previsit-list-unit-row"><span><b>${esc(unit.name)}</b>${unit.factor === 1 ? '' : `<small>هر ${formatPrevisitUnitQuantity(unit.factor)} ${esc(product.unit || 'عدد')}</small>`}</span><div><button type="button" data-previsit-list-unit-decrease="${esc(product.id)}" data-previsit-unit-key="${esc(unitKey)}" ${quantity <= 0 ? 'disabled' : ''} aria-label="کم کردن یک ${esc(unit.name)}">−</button><input data-previsit-list-unit-quantity="${esc(product.id)}" data-previsit-unit-key="${esc(unitKey)}" type="text" pattern="[0-9۰-۹٠-٩]*" value="${esc(quantity)}" inputmode="numeric" autocomplete="off" enterkeyhint="done" aria-label="تعداد ${esc(unit.name)} سفارش ${esc(product.name)}"><button type="button" data-previsit-list-unit-increase="${esc(product.id)}" data-previsit-unit-key="${esc(unitKey)}" ${inCart + Number(unit.factor || 1) > available ? 'disabled' : ''} aria-label="افزودن یک ${esc(unit.name)}">+</button></div></div>`;
    }).join('');
    const composition = previsitListUnitComposition(product, unitQuantities);
    const stock = Number(product.available_qty || 0);
    const carton = Number(product.carton_size || 0);
    const taxPercent = Number(product.catalog_tax_percent || 0);
    let taxInclusivePrice = Number(product.indicative_price || 0);
    if (taxPercent > 0 && Number(product.catalog_tax_inclusive_price || 0) > 0) {
      taxInclusivePrice = Number(product.catalog_tax_inclusive_price);
    }
    const purchaseLabel = taxPercent > 0
      ? `قیمت پایه با ${taxPercent.toLocaleString('fa-IR', {maximumFractionDigits: 2})}٪ ارزش افزوده`
      : 'قیمت پایه';
    return `<article class="previsit-list-product ${inCart ? 'is-in-cart' : ''} ${stock <= 0 ? 'is-unavailable' : ''}" data-previsit-list-product="${esc(product.id)}"><div class="previsit-list-product-copy"><small>${esc([product.brand, product.group].filter(Boolean).join(' · ') || product.manufacturer || 'کالا')}</small><strong>${esc(product.name)}</strong><span>کد ${esc(product.code || product.id)}${product.barcode ? ` · بارکد ${esc(product.barcode)}` : ''}</span><div><b>تعداد در کارتن: ${carton > 0 ? carton.toLocaleString('fa-IR') : '—'}</b><b class="${stock > 0 ? 'is-stocked' : 'is-empty'}">موجودی: ${stock.toLocaleString('fa-IR')} ${esc(product.unit || '')}</b></div></div><div class="previsit-list-prices"><span class="is-purchase"><small>${purchaseLabel}</small><b>${money(taxInclusivePrice)}</b></span><span><small>قیمت تولیدکننده</small><b>${money(product.manufacturer_price)}</b></span><span><small>قیمت مصرف‌کننده</small><b>${money(product.consumer_price)}</b></span></div><div class="previsit-list-quantity"><small>تعداد به تفکیک واحد</small><div class="previsit-list-unit-rows" aria-label="تعداد واحدهای سفارش ${esc(product.name)}">${unitRows}</div><em data-previsit-list-unit-summary>${composition ? `${esc(composition)} = ` : ''}${formatPrevisitUnitQuantity(inCart)} ${esc(product.unit || 'عدد')} در سبد</em></div></article>`;
  }).join('') : '<div class="previsit-list-empty"><strong>کالایی با این فیلتر پیدا نشد</strong><span>برند، گروه یا عبارت جست‌وجو را تغییر دهید.</span></div>';
}

function previsitGroupedImageUrl(group, size = 'display') {
  const source = String(group?.image_url || '');
  return source ? source.replace(/([?&]size=)[^&]+/, `$1${size}`) : '';
}

function currentPrevisitGroupedCatalogs() {
  if (!previsitContext) return [];
  const productsById = new Map((previsitContext.products || [])
    .map(previsitProductAtSelectedConditions)
    .map((product) => [String(product.id), product]));
  return (previsitContext.grouped_catalogs || []).map((group) => {
    const products = (group.product_ids || []).map((id) => productsById.get(String(id))).filter(Boolean)
      .filter((product) => !previsitGroupedCatalogState.brand || product.brand === previsitGroupedCatalogState.brand)
      .filter((product) => !previsitGroupedCatalogState.group || String(product.group_id) === previsitGroupedCatalogState.group)
      .filter((product) => !previsitGroupedCatalogState.inStock || Number(product.available_qty) > 0);
    return {...group, catalog_products: products};
  }).filter((group) => {
    if (!group.catalog_products.length) return false;
    if (!previsitGroupedCatalogState.query) return true;
    const haystack = `${group.name} ${group.catalog_products.map((product) => `${product.name} ${product.code} ${product.brand} ${product.group}`).join(' ')}`.toLocaleLowerCase('fa');
    return haystack.includes(previsitGroupedCatalogState.query);
  });
}

function renderPrevisitGroupedCatalogFilters() {
  const brandSelect = $('#previsitGroupedBrand');
  const groupSelect = $('#previsitGroupedGroup');
  if (!brandSelect || !groupSelect || !previsitContext) return;
  const products = (previsitContext.products || []).map(previsitProductAtSelectedConditions);
  const brands = [...new Set(products.map((product) => product.brand).filter(Boolean))]
    .sort((a, b) => previsitCatalogTextCompare(a, b));
  if (previsitGroupedCatalogState.brand && !brands.includes(previsitGroupedCatalogState.brand)) {
    previsitGroupedCatalogState.brand = '';
    previsitGroupedCatalogState.group = '';
  }
  brandSelect.innerHTML = '<option value="">همه برندها</option>' + brands.map((brand) => `<option value="${esc(brand)}">${esc(brand)}</option>`).join('');
  brandSelect.value = previsitGroupedCatalogState.brand;
  const groups = [...new Map(products
    .filter((product) => !previsitGroupedCatalogState.brand || product.brand === previsitGroupedCatalogState.brand)
    .filter((product) => product.group)
    .map((product) => [String(product.group_id), product.group])).entries()]
    .sort((a, b) => previsitCatalogTextCompare(a[1], b[1]));
  if (!groups.some(([id]) => id === previsitGroupedCatalogState.group)) previsitGroupedCatalogState.group = '';
  groupSelect.innerHTML = `<option value="">${previsitGroupedCatalogState.brand ? 'همه گروه‌های این برند' : 'همه گروه‌ها'}</option>`
    + groups.map(([id, name]) => `<option value="${esc(id)}">${esc(name)}</option>`).join('');
  groupSelect.value = previsitGroupedCatalogState.group;
}

function previsitGroupedProductHtml(product) {
  const stock = Number(product.available_qty || 0);
  const taxPercent = Number(product.catalog_tax_percent || 0);
  const basePrice = Number(product.indicative_price || 0);
  let price = basePrice;
  if (taxPercent > 0 && basePrice > 0) {
    price = Number(product.catalog_tax_inclusive_price || 0) > 0
      ? Number(product.catalog_tax_inclusive_price)
      : Math.round(basePrice * (1 + taxPercent / 100));
  }
  const displayPrice = (value) => Number(value || 0) > 0
    ? `${Number(value).toLocaleString('fa-IR')} ریال`
    : '—';
  const baseLabel = taxPercent > 0 && price > 0
    ? `قیمت پایه با احتساب ${taxPercent.toLocaleString('fa-IR', {maximumFractionDigits: 2})}٪ ارزش افزوده`
    : 'قیمت پایه';
  const prices = `<div class="previsit-grouped-prices"><span class="is-base"><small>${baseLabel}</small><b>${displayPrice(price)}</b></span><span><small>قیمت تولیدکننده</small><b>${displayPrice(product.manufacturer_price)}</b></span><span><small>قیمت مصرف‌کننده</small><b>${displayPrice(product.consumer_price)}</b></span></div>`;
  return `<section class="previsit-grouped-product ${previsitCartQuantity(product.id) ? 'is-in-cart' : ''}"><header><span><small>${esc([product.brand, product.group].filter(Boolean).join(' · '))}</small><strong>${esc(product.name)}</strong><i>کد ${esc(product.code || product.id)} · موجودی ${stock.toLocaleString('fa-IR')} ${esc(product.unit || '')}</i></span></header>${prices}${previsitCatalogUnitRows(product)}</section>`;
}

function renderPrevisitGroupedCatalogs() {
  const root = $('#previsitGroupedCatalogs');
  if (!root || !previsitContext) return;
  const groups = currentPrevisitGroupedCatalogs();
  $('#previsitGroupedCount').textContent = `${groups.length.toLocaleString('fa-IR')} تصویر · ${groups.reduce((sum, group) => sum + group.catalog_products.length, 0).toLocaleString('fa-IR')} کالا`;
  const stockToggle = $('#previsitGroupedStockToggle');
  stockToggle.classList.toggle('is-active', previsitGroupedCatalogState.inStock);
  stockToggle.setAttribute('aria-pressed', String(previsitGroupedCatalogState.inStock));
  root.innerHTML = groups.length ? groups.map((group) => {
    const imageUrl = previsitGroupedImageUrl(group);
    return `<article class="previsit-grouped-card"><figure>${imageUrl ? `<img loading="lazy" decoding="async" src="${esc(imageUrl)}" alt="${esc(group.name)}">` : '<span>تصویر ثبت نشده</span>'}</figure><header><div><small>${esc(group.brands.join(' · '))}</small><strong>${esc(group.name)}</strong></div><b>${group.catalog_products.length.toLocaleString('fa-IR')} کالا</b></header><div class="previsit-grouped-products">${group.catalog_products.map(previsitGroupedProductHtml).join('')}</div></article>`;
  }).join('') : '<div class="previsit-list-empty"><strong>کاتالوگ گروهی پیدا نشد</strong><span>فیلترها را تغییر دهید یا کالاهای ناموجود را هم نمایش دهید.</span></div>';
}

async function downloadPrevisitGroupedCatalog() {
  const button = $('#previsitGroupedDownload');
  const status = $('#previsitGroupedDownloadStatus');
  const urls = [...new Set(currentPrevisitGroupedCatalogs().map((group) => previsitGroupedImageUrl(group, 'thumb')).filter(Boolean))];
  if (!urls.length) return toast('تصویری برای دانلود در فیلتر فعلی وجود ندارد.');
  button.disabled = true;
  let completed = 0;
  try {
    const cache = 'caches' in window ? await caches.open('neginai-catalog-images-v1') : null;
    for (let index = 0; index < urls.length; index += 6) {
      await Promise.all(urls.slice(index, index + 6).map(async (url) => {
        const response = await fetch(url, {credentials: 'same-origin', cache: 'force-cache'});
        if (!response.ok) throw Error('دریافت یکی از تصاویر انجام نشد.');
        if (cache) await cache.put(url, response.clone());
        completed += 1;
        status.textContent = `${completed.toLocaleString('fa-IR')} از ${urls.length.toLocaleString('fa-IR')}`;
      }));
    }
    status.textContent = `${urls.length.toLocaleString('fa-IR')} تصویر آماده استفاده آفلاین`;
    toast('تصاویر کاتالوگ روی تبلت آماده شد.');
  } catch (error) {
    status.textContent = `${completed.toLocaleString('fa-IR')} تصویر دانلود شد`;
    toast(error.message || 'دانلود تصاویر کامل نشد.');
  } finally {
    button.disabled = false;
  }
}

function renderPrevisitQuickFilterOptions() {
  const groupSelect = $('#previsitQuickGroupFilter');
  const brandSelect = $('#previsitQuickBrandFilter');
  if (!groupSelect || !brandSelect || !previsitContext) return;
  const products = (previsitContext.products || []).map(previsitProductAtSelectedConditions);
  const brands = [...new Set(products.map((item) => item.brand).filter(Boolean))]
    .sort((a, b) => String(a).localeCompare(String(b), 'fa'));
  brandSelect.innerHTML = '<option value="">همه برندها</option>' + brands.map((name) => `<option value="${esc(name)}">${esc(name)}</option>`).join('');
  brandSelect.value = brands.includes(previsitQuickFilterState.brand) ? previsitQuickFilterState.brand : '';
  previsitQuickFilterState.brand = brandSelect.value;
  const groups = [...new Map(products
    .filter((item) => !previsitQuickFilterState.brand || item.brand === previsitQuickFilterState.brand)
    .filter((item) => item.group)
    .map((item) => [String(item.group_id), item.group])).entries()]
    .sort((a, b) => String(a[1]).localeCompare(String(b[1]), 'fa'));
  const currentGroup = previsitQuickFilterState.group;
  groupSelect.innerHTML = `<option value="">${previsitQuickFilterState.brand ? 'همه گروه‌های این برند' : 'همه گروه‌ها'}</option>` + groups.map(([id, name]) => `<option value="${esc(id)}">${esc(name)}</option>`).join('');
  groupSelect.value = groups.some(([id]) => id === currentGroup) ? currentGroup : '';
  previsitQuickFilterState.group = groupSelect.value;
}

function renderPrevisitCatalogFilterOptions() {
  const brandSelect = $('#previsitBrandFilter');
  const groupSelect = $('#previsitGroupFilter');
  if (!brandSelect || !groupSelect || !previsitContext) return;
  const products = (previsitContext.products || []).map(previsitProductAtSelectedConditions);
  const brands = [...new Set(products.map((item) => item.brand).filter(Boolean))]
    .sort((a, b) => String(a).localeCompare(String(b), 'fa'));
  brandSelect.innerHTML = '<option value="">همه برندها</option>' + brands.map((name) => `<option value="${esc(name)}">${esc(name)}</option>`).join('');
  brandSelect.value = brands.includes(previsitCatalogState.brand) ? previsitCatalogState.brand : '';
  previsitCatalogState.brand = brandSelect.value;
  const groups = [...new Map(products
    .filter((item) => !previsitCatalogState.brand || item.brand === previsitCatalogState.brand)
    .filter((item) => item.group)
    .map((item) => [String(item.group_id), item.group])).entries()]
    .sort((a, b) => String(a[1]).localeCompare(String(b[1]), 'fa'));
  const currentGroup = previsitCatalogState.group;
  groupSelect.innerHTML = `<option value="">${previsitCatalogState.brand ? 'همه گروه‌های این برند' : 'همه گروه‌ها'}</option>` + groups.map(([id, name]) => `<option value="${esc(id)}">${esc(name)}</option>`).join('');
  groupSelect.value = groups.some(([id]) => id === currentGroup) ? currentGroup : '';
  previsitCatalogState.group = groupSelect.value;
}

function updatePrevisitPriceContextNote() {
  const note = $('#previsitPriceContextNote');
  if (!note || !previsitContext) return;
  const order = $('#previsitOrderType')?.selectedOptions?.[0]?.textContent || 'نوع سفارش';
  const payment = $('#previsitPaymentType')?.selectedOptions?.[0]?.textContent || 'روش پرداخت';
  const warehouse = $('#previsitWarehouse')?.selectedOptions?.[0]?.textContent || 'انبار';
  note.textContent = `مبلغ نهایی برای «${order} / ${payment} / ${warehouse}» پس از محاسبه سبد مشخص می‌شود.`;
}

function renderPrevisitTableProduct() {
  const overlay = $('#previsitTableOverlay');
  if (!overlay || overlay.hidden || !previsitTableProducts.length) return;
  const product = previsitTableProducts[previsitTableIndex];
  const tableControls = overlay.querySelector('.previsit-table-controls');
  if (product.catalog_products) {
    overlay.classList.add('is-grouped-catalog');
    const singleGroupedProduct = product.catalog_products.length === 1;
    overlay.classList.toggle('is-single-grouped-product', singleGroupedProduct);
    $('#previsitTableSeller').classList.add('is-grouped-products');
    const visibleProductCount = Math.min(Math.max(product.catalog_products.length, 1), 5);
    const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 800;
    const systemClearance = isAndroid ? 56 : 0;
    const groupedStripHeight = singleGroupedProduct
      ? Math.min(Math.round(viewportHeight * 0.48), 380 + systemClearance)
      : Math.min(Math.round(viewportHeight * 0.52), 54 + systemClearance + (visibleProductCount * 160));
    const minimumStripHeight = singleGroupedProduct ? 310 + systemClearance : 220;
    overlay.style.setProperty('--previsit-group-strip-height', `${Math.max(minimumStripHeight, groupedStripHeight)}px`);
    tableControls.hidden = true;
    const imageUrl = previsitGroupedImageUrl(product, 'display');
    $('#previsitTableCustomer').innerHTML = `<div class="previsit-table-hero">${imageUrl ? `<img src="${esc(imageUrl)}" alt="${esc(product.name)}">` : '<span>تصویر ثبت نشده</span>'}</div><div class="previsit-table-customer-copy"><small>${esc(product.brands.join(' · '))}</small><h2>${esc(product.name)}</h2><p>${product.catalog_products.length.toLocaleString('fa-IR')} کالای مرتبط در این تصویر؛ انتخاب تعداد از پنل فروشنده انجام می‌شود.</p></div>`;
    $('#previsitTableSeller').innerHTML = `<div class="previsit-table-group-products">${product.catalog_products.map(previsitGroupedProductHtml).join('')}</div>`;
    $('#previsitTablePosition').textContent = `${(previsitTableIndex + 1).toLocaleString('fa-IR')} از ${previsitTableProducts.length.toLocaleString('fa-IR')} تصویر`;
    $('#previsitTableCart').innerHTML = `🛒 سبد <b>${previsitLines().length.toLocaleString('fa-IR')}</b>`;
    return;
  }
  overlay.classList.remove('is-grouped-catalog');
  overlay.classList.remove('is-single-grouped-product');
  overlay.style.removeProperty('--previsit-group-strip-height');
  $('#previsitTableSeller').classList.remove('is-grouped-products');
  tableControls.hidden = false;
  const quantity = previsitCartQuantity(product.id);
  const taxPercent = Number(product.catalog_tax_percent || 0);
  let purchasePrice = Number(product.indicative_price || 0);
  if (taxPercent > 0 && Number(product.catalog_tax_inclusive_price || 0) > 0) {
    purchasePrice = Number(product.catalog_tax_inclusive_price);
  }
  const purchaseLabel = taxPercent > 0
    ? `\u0642\u06cc\u0645\u062a \u062e\u0631\u06cc\u062f \u0628\u0627 ${taxPercent.toLocaleString('fa-IR', {maximumFractionDigits: 2})}\u066a \u0627\u0631\u0632\u0634 \u0627\u0641\u0632\u0648\u062f\u0647`
    : '\u0642\u06cc\u0645\u062a \u067e\u0627\u06cc\u0647';
  const initial = String(product.brand || product.name || '\u06a9').trim().slice(0, 1);
  const visual = product.image_url
    ? `<img src="${esc(product.image_url)}" alt="${esc(product.name)}">`
    : `<span aria-label="\u062a\u0635\u0648\u06cc\u0631 \u06a9\u0627\u0644\u0627 \u062b\u0628\u062a \u0646\u0634\u062f\u0647">${esc(initial)}</span>`;
  const tablePrice = (value) => Number(value || 0) > 0
    ? `${Number(value).toLocaleString('fa-IR')} \u0631\u06cc\u0627\u0644`
    : '\u2014';
  $('#previsitTableCustomer').innerHTML = `<div class="previsit-table-hero">${visual}</div><div class="previsit-table-customer-copy"><small>${esc(product.brand || product.manufacturer || product.group || '')}</small><h2>${esc(product.name)}</h2>${product.description ? `<p>${esc(product.description)}</p>` : ''}<div><span><small>${purchaseLabel}</small><b>${tablePrice(purchasePrice)}</b></span><span><small>\u0642\u06cc\u0645\u062a \u062a\u0648\u0644\u06cc\u062f\u06a9\u0646\u0646\u062f\u0647</small><b>${tablePrice(product.manufacturer_price)}</b></span><span><small>\u0642\u06cc\u0645\u062a \u0645\u0635\u0631\u0641\u200c\u06a9\u0646\u0646\u062f\u0647</small><b>${tablePrice(product.consumer_price)}</b></span></div></div>`;
  $('#previsitTableSeller').innerHTML = `<div><small>${esc(product.brand || product.group || '')}</small><strong>${esc(product.name)}</strong><span>\u06a9\u062f ${esc(product.code || product.id)} \u00b7 \u0645\u0648\u062c\u0648\u062f\u06cc ${Number(product.available_qty || 0).toLocaleString('fa-IR')} ${esc(product.unit)}</span></div><b>${purchasePrice.toLocaleString('fa-IR')} \u0631\u06cc\u0627\u0644</b>`;
  $('#previsitTablePosition').textContent = `${(previsitTableIndex + 1).toLocaleString('fa-IR')} \u0627\u0632 ${previsitTableProducts.length.toLocaleString('fa-IR')}`;
  $('#previsitTableQuantity').innerHTML = `<small>\u062a\u0639\u062f\u0627\u062f \u062f\u0631 \u0633\u0628\u062f</small><b>${Number(quantity || 0).toLocaleString('fa-IR')}</b>`;
  $('#previsitTableMinus').disabled = quantity <= 0;
  $('#previsitTablePlus').disabled = previsitCartQuantity(product.id) + 1 > previsitAvailableBaseQuantity(product);
  $('#previsitTableCart').innerHTML = `\ud83d\uded2 \u0633\u0628\u062f <b>${previsitLines().length.toLocaleString('fa-IR')}</b>`;
}

async function openPrevisitTableMode() {
  previsitTableProducts = previsitOrderMode === 'grouped'
    ? currentPrevisitGroupedCatalogs()
    : currentPrevisitListProducts();
  if (!previsitTableProducts.length) return toast('\u062f\u0631 \u0641\u06cc\u0644\u062a\u0631 \u0641\u0639\u0644\u06cc \u06a9\u0627\u0644\u0627\u06cc\u06cc \u0628\u0631\u0627\u06cc \u0646\u0645\u0627\u06cc\u0634 \u0646\u06cc\u0633\u062a.');
  previsitTableIndex = 0;
  const overlay = $('#previsitTableOverlay');
  overlay.style.setProperty('--previsit-android-bottom-clearance', isAndroid ? '56px' : '0px');
  overlay.hidden = false;
  document.body.classList.add('previsit-table-open');
  renderPrevisitTableProduct();
  try {
    if (previsitOrderMode !== 'grouped') {
      if (!isNeginAndroidApp && !document.fullscreenElement && overlay.requestFullscreen) {
        await overlay.requestFullscreen({navigationUI: 'hide'});
      }
    }
  } catch (_) {
    // Fixed-position fallback remains fully usable where Fullscreen API is blocked.
  }
}

function closePrevisitTableMode(exitFullscreen = true) {
  const overlay = $('#previsitTableOverlay');
  if (!overlay) return;
  overlay.hidden = true;
  overlay.classList.remove('is-grouped-catalog');
  overlay.classList.remove('is-single-grouped-product');
  overlay.style.removeProperty('--previsit-group-strip-height');
  overlay.style.removeProperty('--previsit-android-bottom-clearance');
  $('#previsitTableSeller')?.classList.remove('is-grouped-products');
  document.body.classList.remove('previsit-table-open');
  if (exitFullscreen && document.fullscreenElement === overlay) void document.exitFullscreen().catch(() => {});
}

function movePrevisitTableProduct(offset) {
  if (!previsitTableProducts.length) return;
  previsitTableIndex = (previsitTableIndex + offset + previsitTableProducts.length) % previsitTableProducts.length;
  renderPrevisitTableProduct();
  const customer = $('#previsitTableCustomer');
  if (!customer) return;
  const animationClass = offset > 0 ? 'is-page-next' : 'is-page-previous';
  customer.classList.remove('is-page-next', 'is-page-previous');
  void customer.offsetWidth;
  customer.classList.add(animationClass);
  window.setTimeout(() => customer.classList.remove(animationClass), 260);
}

function beginPrevisitTableSwipe(event) {
  if (event.pointerType === 'mouse' && event.button !== 0) return;
  const target = event.target instanceof Element ? event.target : null;
  if (target && target.closest('button,input,select,textarea,a')) return;
  previsitTableSwipeStart = {pointerId: event.pointerId, x: event.clientX, y: event.clientY};
  try { event.currentTarget.setPointerCapture(event.pointerId); } catch (_) {}
}

function finishPrevisitTableSwipe(event) {
  const start = previsitTableSwipeStart;
  previsitTableSwipeStart = null;
  if (!start || start.pointerId !== event.pointerId) return;
  const deltaX = event.clientX - start.x;
  const deltaY = event.clientY - start.y;
  if (Math.abs(deltaX) < 45 || Math.abs(deltaX) <= Math.abs(deltaY) * 1.15) return;
  movePrevisitTableProduct(deltaX < 0 ? 1 : -1);
}

function cancelPrevisitTableSwipe() {
  previsitTableSwipeStart = null;
}

function changePrevisitTableQuantity(delta) {
  const product = previsitTableProducts[previsitTableIndex];
  if (!product || product.catalog_products) return;
  changePrevisitProductQuantity(product.id, delta);
  renderPrevisitTableProduct();
}

function previsitCartQuantity(productId) {
  const row = previsitOrderRows().find((item) => item.dataset.productId === String(productId));
  return row ? Number(row.querySelector('[data-field="quantity"]').value || 0) : 0;
}

function setPrevisitProductQuantity(productId, value) {
  const product = productForPrevisit(productId);
  const requestedQuantity = Math.max(0, Math.floor(Number(value || 0)));
  const quantity = product ? clampPrevisitQuantityToInventory(product, requestedQuantity) : 0;
  const current = previsitCartQuantity(productId);
  if (!Number.isFinite(quantity) || quantity === current) return quantity;
  if (quantity < requestedQuantity && product) normalizePrevisitUnitQuantitiesToBase(product, quantity);
  changePrevisitProductQuantity(productId, quantity - current);
  return quantity;
}

function changePrevisitProductQuantity(productId, delta) {
  const product = productForPrevisit(productId);
  const row = previsitOrderRows().find((item) => item.dataset.productId === String(productId));
  if (!row) {
    if (delta > 0) addPrevisitLine({product_id: productId, quantity: delta});
    renderPrevisitTableProduct();
    return;
  }
  const input = row.querySelector('[data-field="quantity"]');
  const requestedQuantity = Math.max(0, Math.floor(Number(input.value || 0) + Number(delta || 0)));
  const nextQuantity = product ? clampPrevisitQuantityToInventory(product, requestedQuantity) : 0;
  if (nextQuantity < requestedQuantity && product) normalizePrevisitUnitQuantitiesToBase(product, nextQuantity);
  if (nextQuantity <= 0) {
    row.remove();
    clearPrevisitGiftLines();
  }
  else {
    input.value = String(nextQuantity);
    syncPrevisitInvoiceUnitBreakdown(row, product, nextQuantity);
    resetPrevisitLineCalculation(row);
  }
  previsitPreview = null;
  if ($('#previsitPreviewResult')) $('#previsitPreviewResult').hidden = true;
  syncPrevisitCartSummary();
}

function syncPrevisitInvoiceTotals() {
  const footer = $('#previsitInvoiceTotals');
  if (!footer) return;
  const lines = previsitLines();
  footer.hidden = lines.length === 0;
  if (!lines.length) return;
  const officialItems = Array.isArray(previsitPreview?.items) ? previsitPreview.items : [];
  const isOfficial = officialItems.length > 0;
  const totals = previsitPreview?.totals || {};
  const sumItems = (reader) => officialItems.reduce((sum, item) => sum + Number(reader(item) || 0), 0);
  const quantity = isOfficial ? sumItems((item) => item.quantity) : lines.reduce((sum, line) => sum + line.quantity, 0);
  const gross = isOfficial
    ? Number(totals.gross ?? sumItems((item) => item.gross_amount ?? (Number(item.quantity || 0) * Number(item.unit_price || 0))))
    : lines.reduce((sum, line) => sum + (line.quantity * line.unit_price), 0);
  const categoryAmount = (category) => isOfficial ? sumItems((item) => item.discount_breakdown?.[category]?.amount) : 0;
  const tax = isOfficial ? Number(totals.tax || 0) + Number(totals.charge || 0) : 0;
  const net = isOfficial ? Number(totals.net ?? sumItems((item) => item.net_amount)) : gross;
  const values = {
    quantity,
    gross,
    goods: categoryAmount('goods'),
    volume: categoryAmount('volume'),
    cash: categoryAmount('cash'),
    tax,
    net,
  };
  Object.entries(values).forEach(([name, value]) => {
    const output = footer.querySelector(`[data-total="${name}"]`);
    output.textContent = `${Number(value || 0).toLocaleString('fa-IR')}${name === 'quantity' ? '' : ' \u0631\u06cc\u0627\u0644'}`;
  });
  footer.querySelector('[data-total-label]').textContent = isOfficial ? 'جمع نهایی' : 'جمع اولیه';
  footer.classList.toggle('is-official', isOfficial);
}

function syncPrevisitCartSummary() {
  if (!$('#previsitDockCount') || !$('#previsitLines')) return;
  const lines = previsitLines();
  const count = lines.length;
  const quantity = lines.reduce((sum, line) => sum + Number(line.quantity || 0), 0);
  const total = previsitPreview?.totals?.gross ?? lines.reduce((sum, line) => sum + (line.quantity * line.unit_price), 0);
  const giftQuantity = officialPrevisitGiftLines(previsitPreview || {}).reduce((sum, gift) => sum + Number(gift.quantity || 0), 0);
  $('#previsitCartCount').textContent = `${count.toLocaleString('fa-IR')} \u0631\u062f\u06cc\u0641`;
  $('#previsitDockCount').textContent = `${count.toLocaleString('fa-IR')} قلم`;
  $('#previsitDockQuantity').textContent = `${quantity.toLocaleString('fa-IR')} عدد`;
  $('#previsitDockGiftCount').hidden = giftQuantity <= 0;
  $('#previsitDockGiftCount').textContent = giftQuantity > 0 ? `+ ${giftQuantity.toLocaleString('fa-IR')} اشانتیون` : '';
  $('#previsitDockTotalLabel').textContent = previsitPreview ? 'ناخالص نهایی' : 'ناخالص فعلی';
  $('#previsitDockTotal').textContent = `${Number(total || 0).toLocaleString('fa-IR')} \u0631\u06cc\u0627\u0644`;
  $('#previsitCartEmpty').hidden = count > 0;
  const orderButton = $('#completePrevisitOrder');
  if (orderButton) {
    const creditAllowed = previsitPreview?.credit_control?.allowed === true;
    orderButton.disabled = !count || !previsitPreview?.ok || !creditAllowed;
    orderButton.title = orderButton.disabled
      ? (count ? 'ابتدا محاسبه نهایی و کنترل اعتبار باید تأیید شود.' : 'حداقل یک کالا به سبد اضافه کنید.')
      : '\u0627\u0639\u062a\u0628\u0627\u0631 \u0645\u0634\u062a\u0631\u06cc \u062a\u0623\u06cc\u06cc\u062f \u0634\u062f\u0647 \u0627\u0633\u062a.';
  }
  syncPrevisitInvoiceTotals();
  if (previsitContext && !document.activeElement?.matches('[data-previsit-catalog-unit-quantity]')) renderPrevisitProductOptions();
  renderPrevisitTableProduct();
}

function invalidatePrevisitCalculation() {
  previsitPreview = null;
  if ($('#previsitPreviewResult')) $('#previsitPreviewResult').hidden = true;
  clearPrevisitGiftLines();
  previsitOrderRows().forEach(resetPrevisitLineCalculation);
  syncPrevisitCartSummary();
}

function renderPrevisitProductOptions() {
  const picker = $('#previsitProductPicker');
  if (!picker || !previsitContext) return;
  previsitCatalogState.query = ($('#previsitProductSearch').value || '').trim().toLocaleLowerCase('fa');
  previsitCatalogState.brand = $('#previsitBrandFilter').value;
  previsitCatalogState.group = $('#previsitGroupFilter').value;
  previsitCatalogState.sort = $('#previsitSort').value;
  const products = currentPrevisitCatalogProducts();
  const quickProducts = currentPrevisitQuickProducts();
  picker.innerHTML = '<option value="">\u0627\u0646\u062a\u062e\u0627\u0628 \u06a9\u0627\u0644\u0627</option>' + quickProducts.map((product) => `<option value="${esc(product.id)}" ${Number(product.available_qty) <= 0 ? 'disabled' : ''}>${esc(product.name)} \u00b7 ${esc(product.code)} \u00b7 \u0645\u0648\u062c\u0648\u062f\u06cc ${Number(product.available_qty).toLocaleString('fa-IR')}</option>`).join('');
  $('#previsitCatalogCount').textContent = `${products.length.toLocaleString('fa-IR')} \u06a9\u0627\u0644\u0627`;
  $('#previsitCatalogGrid').innerHTML = products.length ? products.map((product) => {
    const inCart = previsitCartQuantity(product.id);
    const carton = Number(product.carton_size || 0);
    const initial = String(product.brand || product.name || '\u06a9').trim().slice(0, 1);
    return `<article class="previsit-product-card ${inCart ? 'is-in-cart' : ''}"><div class="previsit-product-visual" aria-hidden="true"><span>${esc(initial)}</span>${product.can_be_free ? '<b>\u062c\u0627\u06cc\u0632\u0647</b>' : ''}</div><div class="previsit-product-info"><small>${esc([product.brand, product.group].filter(Boolean).join(' \u00b7 ') || product.manufacturer || '\u06a9\u0627\u0644\u0627')}</small><strong>${esc(product.name)}</strong><span>\u06a9\u062f ${esc(product.code || product.id)}${product.barcode ? ` \u00b7 \u0628\u0627\u0631\u06a9\u062f ${esc(product.barcode)}` : ''}</span></div><div class="previsit-product-facts"><span class="${Number(product.available_qty) > 0 ? 'is-stocked' : 'is-empty'}">\u0645\u0648\u062c\u0648\u062f\u06cc ${Number(product.available_qty).toLocaleString('fa-IR')} ${esc(product.unit)}</span>${carton ? `<span>\u062a\u0639\u062f\u0627\u062f \u062f\u0631 \u06a9\u0627\u0631\u062a\u0646 ${carton.toLocaleString('fa-IR')}</span>` : ''}</div><div class="previsit-product-price"><small>\u0642\u06cc\u0645\u062a \u067e\u0627\u06cc\u0647</small><b>${Number(product.indicative_price || 0).toLocaleString('fa-IR')} \u0631\u06cc\u0627\u0644</b></div><button type="button" data-previsit-add-product="${esc(product.id)}" ${Number(product.available_qty) <= 0 ? 'disabled' : ''}>${inCart ? `+ \u0627\u0641\u0632\u0648\u062f\u0646 \u00b7 ${inCart.toLocaleString('fa-IR')} \u062f\u0631 \u0633\u0628\u062f` : '+ \u0627\u0641\u0632\u0648\u062f\u0646 \u0628\u0647 \u0633\u0628\u062f'}</button></article>`;
  }).join('') : '<div class="previsit-catalog-empty"><strong>\u06a9\u0627\u0644\u0627\u06cc\u06cc \u067e\u06cc\u062f\u0627 \u0646\u0634\u062f</strong><span>\u0641\u06cc\u0644\u062a\u0631\u0647\u0627 \u06cc\u0627 \u0639\u0628\u0627\u0631\u062a \u062c\u0633\u062a\u200c\u0648\u062c\u0648 \u0631\u0627 \u062a\u063a\u06cc\u06cc\u0631 \u062f\u0647\u06cc\u062f.</span></div>';
  const catalogPrice = (value) => Number(value || 0) > 0 ? `${Number(value).toLocaleString('fa-IR')} \u0631\u06cc\u0627\u0644` : '\u2014';
  $$('.previsit-product-card', $('#previsitCatalogGrid')).forEach((card, index) => {
    const product = products[index];
    const taxPercent = Number(product.catalog_tax_percent || 0);
    const hasCatalogTax = taxPercent > 0 && Number(product.catalog_tax_inclusive_price || 0) > 0;
    const baseLabel = hasCatalogTax
      ? `\u0642\u06cc\u0645\u062a \u062e\u0631\u06cc\u062f \u0628\u0627 \u0627\u0631\u0632\u0634 \u0627\u0641\u0632\u0648\u062f\u0647 (${taxPercent.toLocaleString('fa-IR', {maximumFractionDigits: 2})}\u066a)`
      : '\u0642\u06cc\u0645\u062a \u067e\u0627\u06cc\u0647';
    const displayedBasePrice = hasCatalogTax ? product.catalog_tax_inclusive_price : product.indicative_price;
    const basePriceNote = hasCatalogTax
      ? `<em>\u067e\u0627\u06cc\u0647 \u0628\u062f\u0648\u0646 \u0645\u0627\u0644\u06cc\u0627\u062a: ${catalogPrice(product.indicative_price)} \u00b7 \u06af\u0631\u0648\u0647 \u0645\u0627\u0644\u06cc\u0627\u062a\u06cc ${taxPercent.toLocaleString('fa-IR', {maximumFractionDigits: 2})}\u066a</em>`
      : '';
    card.querySelector('.previsit-product-price').innerHTML = `<span class="${hasCatalogTax ? 'is-tax-inclusive' : ''}"><small>${baseLabel}</small><b>${catalogPrice(displayedBasePrice)}</b>${basePriceNote}</span><span><small>\u0642\u06cc\u0645\u062a \u062a\u0648\u0644\u06cc\u062f\u06a9\u0646\u0646\u062f\u0647</small><b>${catalogPrice(product.manufacturer_price)}</b></span><span><small>\u0642\u06cc\u0645\u062a \u0645\u0635\u0631\u0641\u200c\u06a9\u0646\u0646\u062f\u0647</small><b>${catalogPrice(product.consumer_price)}</b></span>`;
    const actionButton = card.querySelector('[data-previsit-add-product]');
    actionButton.outerHTML = previsitCatalogUnitRows(product);
  });
}

function fillPrevisitContextSelectors() {
  const order = $('#previsitOrderType');
  const payment = $('#previsitPaymentType');
  const warehouse = $('#previsitWarehouse');
  order.innerHTML = (previsitContext.order_types || []).map((item) => `<option value="${esc(item.id)}">${esc(item.name)}</option>`).join('');
  payment.innerHTML = (previsitContext.payment_types || []).map((item) => `<option value="${esc(item.id)}">${esc(item.name)}</option>`).join('');
  const warehouses = previsitContext.warehouses || [];
  warehouse.innerHTML = warehouses.length
    ? warehouses.map((item) => `<option value="${esc(item.ref)}">${esc(item.name || `انبار ${item.ref}`)}</option>`).join('')
    : '<option value="">انبار مجاز دریافت نشد</option>';
  const defaultWarehouseRef = String(previsitContext.warehouse_selection?.default_ref || '');
  if (defaultWarehouseRef && warehouses.some((item) => String(item.ref) === defaultWarehouseRef)) {
    warehouse.value = defaultWarehouseRef;
  }
  warehouse.disabled = !warehouses.length || !previsitContext.warehouse_selection?.enabled;
  warehouse.title = !warehouses.length
    ? 'تنظیمات انبار فروشنده پیدا نشد.'
    : (warehouse.disabled
      ? 'انبار برای این بازاریاب ثابت است.'
      : 'انبارهای مجاز دریافت شده‌اند.');
  $('#previsitContextStatus').innerHTML = `${Number(previsitContext.catalog_count || 0).toLocaleString('fa-IR')} \u06a9\u0627\u0644\u0627 \u00b7 \u0645\u0648\u062c\u0648\u062f\u06cc ${previsitContext.inventory?.online_refresh ? '\u0622\u0646\u0644\u0627\u06cc\u0646' : '\u0644\u062d\u0638\u0647\u200c\u0627\u06cc'}`;
  const customer = previsitContext.customer || {};
  renderPrevisitCustomerHeader(
    previsitWorkspace?.customer || customer,
    previsitWorkspace?.route || previsitContext.route,
    previsitWorkspace?.seller || previsitContext.seller,
  );
  previsitCatalogState = {query: '', brand: '', group: '', inStock: true, sort: 'code'};
  previsitQuickFilterState = {query: '', group: '', brand: ''};
  previsitListState = {query: '', group: '', brand: '', inStock: true};
  previsitGroupedCatalogState = {query: '', group: '', brand: '', inStock: true};
  previsitProductUnitSelections.clear();
  previsitProductUnitQuantities.clear();
  $('#previsitQuickSearch').value = '';
  $('#previsitListSearch').value = '';
  renderPrevisitCatalogFilterOptions();
  renderPrevisitQuickFilterOptions();
  renderPrevisitListFilters();
  renderPrevisitProductList();
  renderPrevisitGroupedCatalogFilters();
  renderPrevisitGroupedCatalogs();
  updatePrevisitPriceContextNote();
  updatePrevisitOrderContextSummary();
  $('#previsitOrderConditionsPanel').hidden = false;
  $('#previsitOrderAssistantPanel').hidden = true;
  $('#previsitOrderCommon').classList.remove('is-panel-open');
  $$('[data-previsit-order-panel]').forEach((button) => { button.classList.remove('is-active'); button.setAttribute('aria-expanded', 'false'); });
  togglePrevisitCatalogFilters(false);
  previsitOrderMode = 'list';
  previsitVisitSection = 'profile';
  switchPrevisitOrderMode('list');
  switchPrevisitVisitSection('profile');
  switchPrevisitView('catalog');
  syncPrevisitCartSummary();
}

$('#inboxBtn').addEventListener('click', () => loadNotifications(true));
$('#schemaCatalogBtn').addEventListener('click', openSchemaCatalog);
$('#organizationStructureBtn').addEventListener('click', openOrganizationStructure);
$('#planningBtn').addEventListener('click', () => { window.location.href = '/planning'; });
$('#controlBtn').addEventListener('click', () => { window.location.href = '/control'; });
$('#myRoutesBtn').addEventListener('click', () => openSellerWorkspace('routes'));
$('#dayRouteBtn').addEventListener('click', () => openSellerWorkspace('routes', {dayRouteSelection: true}));
$('#myOpenInvoicesBtn').addEventListener('click', () => openSellerWorkspace('openInvoices'));
$('#myDistributionInProgressBtn').addEventListener('click', () => openSellerWorkspace('distributionInProgress'));
$('#myReturnedChequesBtn').addEventListener('click', () => openSellerWorkspace('returnedCheques'));
$('#myVoucherReturnReportBtn').addEventListener('click', () => openSellerWorkspace('voucherReport'));
$('#myBrandsBtn').addEventListener('click', () => openSellerWorkspace('brands'));
previsitBtn.addEventListener('click', () => void openPrevisit());
sellerRecommendationsBtn.addEventListener('click', openSellerRecommendations);
myRoutesList.addEventListener('click', (event) => {
  const routeMap = event.target.closest('[data-route-map-id]');
  if (routeMap) {
    const mode = routeMap.closest('.seller-route-card')?.querySelector('[data-route-map-mode]')?.value || 'sales_priority';
    $('#routeMapMode').value = mode;
    return openRouteMap(routeMap.dataset.routeMapId, routeMap.dataset.routeMapTitle);
  }
  const dayRoute = event.target.closest('[data-day-route-id]');
  if (dayRoute) {
    startDayRoutePlan(dayRoute.dataset.dayRouteId, dayRoute.dataset.dayRouteTitle);
    sellerWorkspacePanel.hidden = true;
    return;
  }
  const button = event.target.closest('[data-route-customers]');
  if (button) toggleRouteCustomers(button);
});
$('#routeMapStops').addEventListener('click', async (event) => {
  if (!routeMapSession) return;
  const enterVisit = event.target.closest('[data-route-customer-enter-visit]');
  if (enterVisit) {
    event.preventDefault();
    event.stopPropagation();
    if (enterVisit.disabled) return;
    const idleLabel = enterVisit.textContent;
    enterVisit.disabled = true;
    enterVisit.classList.add('is-loading');
    enterVisit.setAttribute('aria-busy', 'true');
    enterVisit.textContent = 'در حال ورود…';
    try {
      await enterRouteCustomerVisit(routeMapSession.pathId, enterVisit.dataset.routeCustomerEnterVisit);
    } finally {
      if (enterVisit.isConnected) {
        enterVisit.disabled = false;
        enterVisit.classList.remove('is-loading');
        enterVisit.removeAttribute('aria-busy');
        enterVisit.textContent = idleLabel;
      }
    }
    return;
  }
  const noVisit = event.target.closest('[data-route-customer-no-visit]');
  if (noVisit) {
    event.preventDefault();
    event.stopPropagation();
    await openRouteCustomerNoVisit(routeMapSession.pathId, noVisit.dataset.routeCustomerNoVisit).catch((error) => toast(error.message));
    return;
  }
  const visitCustomer = event.target.closest('[data-route-map-previsit-customer]');
  const navigationAction = event.target.closest('[data-route-map-start], [data-route-map-visited], [data-route-map-skipped]');
  if (visitCustomer && !navigationAction) {
    await openRouteCustomerProfile(routeMapSession.pathId, visitCustomer.dataset.routeMapPrevisitCustomer, 'map');
    return;
  }
  const startNavigationButton = event.target.closest('[data-route-map-start]');
  if (startNavigationButton) {
    if (routeMapSession.starting) return;
    routeMapSession.starting = true;
    routeMapSession.started = true;
    routeMapSession.followUser = true;
    routeMapSession.arrivedPrompted = false;
    startNavigationButton.disabled = true;
    startNavigationButton.classList.add('is-loading');
    startNavigationButton.textContent = 'در حال دریافت مسیر و GPS…';
    $('#routeMapStartBtn').disabled = true;
    $('#routeMapStartBtn').textContent = 'مسیر فعال است';
    setRouteMapStatus('در حال آماده‌سازی راهنمای مسیر…');
    if (!isIOS) unlockNavigationAudio();
    try { window.NeginAndroid?.startNavigationLocationTracking?.(); } catch (_) {}
    updateRouteMapCustomerMarkerVisibility();
    renderRouteMapStops();
    toast('حرکت به پایگاه اول شروع شد.');
    // این اعلان باید در همان رویداد لمس اجرا شود؛ در برخی مرورگرهای موبایل
    // اجرای آن پس از await مجوز پخش صدا ندارد.
    if (!isIOS) void speakRouteInstruction('مسیر شروع شد.');
    // The saved daily plan is useful for ordering stops, but turn-by-turn
    // guidance must begin from the seller's current GPS position.
    const position = routeMapSession.position || await currentCoordinates();
    if (routeMapSession) routeMapSession.position = position || routeMapSession.position;
    const refreshed = position && await refreshActiveRouteLeg(position, { announce: true });
    if (!refreshed && routeMapSession) {
      if (!isIOS) void speakRouteInstruction(`مسیر به پایگاه اول شروع شد. ${routeMapSession.navigationSteps?.[0]?.instruction || 'مستقیم حرکت کنید.'}`);
      routeMapSession.navigationStepIndex = 1;
      renderRouteMapInstruction();
    }
    if (routeMapSession) {
      routeMapSession.starting = false;
      setRouteMapStatus('');
      if (routeMapSession.position) followRouteMapPosition(routeMapSession.position, true);
      renderRouteMapTripSummary();
      renderRouteMapStops();
    }
    return;
  }
  if (event.target.closest('[data-route-map-visited]')) void completeActiveRouteStop(false, 'visited');
  if (event.target.closest('[data-route-map-skipped]')) void completeActiveRouteStop(false, 'skipped');
});
$('#routeMapStops').addEventListener('keydown', (event) => {
  if ((event.key !== 'Enter' && event.key !== ' ') || !routeMapSession) return;
  const visitCustomer = event.target.closest('[data-route-map-previsit-customer]');
  if (!visitCustomer) return;
  event.preventDefault();
  void openRouteCustomerProfile(routeMapSession.pathId, visitCustomer.dataset.routeMapPrevisitCustomer, 'map');
});
$('#routeMapStartBtn').addEventListener('click', () => {
  const listStartButton = $('#routeMapStops').querySelector('[data-route-map-start]');
  if (!listStartButton) return toast('برای شروع مسیر، ابتدا برنامه مشتریان روز را دریافت کنید.');
  listStartButton.click();
});
routeDayActionRail?.addEventListener('click', async (event) => {
  const button = event.target.closest('[data-route-day-action]');
  if (!button) return;
  const action = button.dataset.routeDayAction;
  if (action === 'customers') {
    setRouteDayActiveAction('customers');
    $('#routeMapStops').scrollIntoView({behavior: 'smooth', block: 'nearest'});
    return;
  }
  if (action === 'map') {
    setRouteDayActiveAction('map');
    $('#routeMapCanvas').scrollIntoView({behavior: 'smooth', block: 'nearest'});
    toast('نقشه و مسیریابی تور فعال است.');
    return;
  }
  if (action === 'requests') {
    setRouteDayActiveAction('requests');
    await loadRouteDaySavedRequests().catch((error) => toast(error.message));
    return;
  }
});
$('#routeDayMenuToggle')?.addEventListener('click', () => toggleRouteDayMenu());
$('#routeDayMenuBackdrop')?.addEventListener('click', () => toggleRouteDayMenu(false));
$('#routeDaySavedRequestList')?.addEventListener('click', async (event) => {
  const button = event.target.closest('[data-route-saved-request-customer]');
  if (!button || !routeMapSession) return;
  await openRouteCustomerProfile(routeMapSession.pathId, button.dataset.routeSavedRequestCustomer, 'map');
});
$('#routeMapInstruction').addEventListener('click', openRouteSummary);
$('#routeMapInstruction').addEventListener('keydown', (event) => {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault();
    openRouteSummary();
  }
});
$('#closeRouteSummary').addEventListener('click', () => $('#routeSummaryDialog').close());
myOpenInvoicesList.addEventListener('click', (event) => {
  const button = event.target.closest('[data-customer-open-invoices]');
  if (button) toggleCustomerOpenInvoices(button);
});
$('#closeSellerWorkspace').addEventListener('click', () => closeCurrentAppView('seller-workspace', () => { sellerWorkspacePanel.hidden = true; }));
$('#closeCustomerProfile').addEventListener('click', () => closeCurrentAppView('customer-profile', closeCustomerProfile));
customerProfilePanel.addEventListener('click', async (event) => {
  if (event.target.closest('#editCustomerProfile')) return setCustomerProfileEditMode(true);
  if (event.target.closest('#captureCustomerLocation')) {
    void captureCustomerProfileLocation();
    return;
  }
  if (event.target.closest('#cancelCustomerProfileEdit')) return renderCustomerProfile();
  if (event.target.closest('#saveCustomerProfileDraft')) {
    try { await saveCustomerProfileDraft(); } catch (error) { toast(error.message || 'ذخیره تغییرات مشتری انجام نشد.'); }
    return;
  }
  if (event.target.closest('#continueCustomerProfileOrder')) {
    const state = customerProfileState;
    if (!state) return;
    customerProfilePanel.hidden = true;
    const opened = await openPrevisitForRouteCustomer(state.routeId, state.customerId);
    if (!opened && customerProfileState === state) customerProfilePanel.hidden = false;
  }
});
$('#closePrevisit').addEventListener('click', () => closeCurrentAppView('previsit', () => { previsitPanel.hidden = true; }));
$('#previsitRoute').addEventListener('change', () => void loadPrevisitCustomers());
$('#previsitCustomer').addEventListener('change', () => {
  $('#startPrevisit').disabled = false;
  void loadPrevisitPolicy().catch((error) => toast(error.message));
});
$('#addPrevisitLine').addEventListener('click', () => addPrevisitLine());
$('#startPrevisit').addEventListener('click', () => void startPrevisitVisit());
$('#savePrevisitDraft').addEventListener('click', () => void savePrevisitRequest().catch((error) => toast(error.message)));
$('#completePrevisitOrder').addEventListener('click', () => void completePrevisit('order').catch((error) => toast(error.message)));
$('#cancelPrevisitOutcome').addEventListener('click', () => {
  pendingRouteNoVisit = null;
  pendingPrevisitOutcome = null;
  $('#previsitOutcomeDialog').close();
});
$('#previsitOutcomeForm').addEventListener('submit', (event) => {
  event.preventDefault();
  const reasonId = $('#previsitOutcomeReason').value;
  if ((!pendingPrevisitOutcome && !pendingRouteNoVisit) || !reasonId) return toast('دلیل را انتخاب کنید.');
  const button = $('#confirmPrevisitOutcome');
  button.disabled = true;
  const submission = pendingRouteNoVisit
    ? completeRouteCustomerNoVisit(reasonId)
    : completePrevisit(pendingPrevisitOutcome, reasonId);
  void submission
    .catch((error) => toast(error.message))
    .finally(() => { button.disabled = false; });
});
$('#closeRouteMap').addEventListener('click', () => closeCurrentAppView('route-map', () => { stopRouteMap(); routeMapPanel.hidden = true; }));
$('#routeMapLocateBtn').addEventListener('click', () => {
  if (!routeMapSession?.position || !routeMapInstance) return toast('موقعیت فعلی هنوز دریافت نشده است.');
  routeMapSession.followUser = true;
  $('#routeMapRecenterBtn').hidden = true;
  if (routeMapSession.started) followRouteMapPosition(routeMapSession.position, true);
  else routeMapInstance.flyTo({ center: [routeMapSession.position.longitude, routeMapSession.position.latitude], zoom: 15, essential: true });
});
$('#routeMapVoiceBtn').addEventListener('click', () => {
  if (isIOS) {
    renderRouteMapInstruction();
    return toast('راهنمای نوشتاری روی نقشه نمایش داده می‌شود.');
  }
  if (!routeMapSession) return;
  routeMapSession.voiceEnabled = !routeMapSession.voiceEnabled;
  const button = $('#routeMapVoiceBtn');
  button.textContent = routeMapSession.voiceEnabled ? '🔊 صدا روشن' : '🔇 صدا خاموش';
  button.classList.toggle('route-map-voice-off', !routeMapSession.voiceEnabled);
  if (!routeMapSession.voiceEnabled) {
    navigationSpeechAbortController?.abort();
    try { navigationAudioSource?.stop(); } catch (_) {}
    try { window.NeginAndroid?.stopNavigationVoice?.(); } catch (_) {}
    return toast('راهنمای صوتی خاموش شد.');
  }
  const step = routeMapSession.navigationSteps?.[routeMapSession.navigationStepIndex];
  void speakRouteInstruction(step ? navigationCue(step, routeMapSession.currentManeuverDistance, 250) : 'راهنمای صوتی روشن شد.');
});
$('#routeMapRecenterBtn').addEventListener('click', () => {
  if (!routeMapSession?.position) return;
  routeMapSession.followUser = true;
  $('#routeMapRecenterBtn').hidden = true;
  followRouteMapPosition(routeMapSession.position, true);
});
$('#routeMapMode').addEventListener('change', () => {
  if (!routeMapSession) return;
  void openRouteMap(routeMapSession.pathId, routeMapSession.title);
});
$('#refreshSellerWorkspace').addEventListener('click', () => openSellerWorkspace(
  sellerWorkspacePanel.dataset.focus || 'routes',
  {dayRouteSelection: sellerWorkspacePanel.dataset.dayRouteSelection === 'true'},
));
$('#closeOrganizationStructure').addEventListener('click', () => closeCurrentAppView('organization', () => { organizationStructurePanel.hidden = true; }));
$('#refreshOrganizationStructure').addEventListener('click', openOrganizationStructure);
organizationProposalsList.addEventListener('click', (event) => {
  const button = event.target.closest('[data-proposal-decision]');
  if (button) void decideOrganizationProposal(button.dataset.proposalId, button.dataset.proposalDecision).catch((error) => toast(error.message));
});
organizationRulesList.addEventListener('click', (event) => {
  const button = event.target.closest('[data-save-rule]');
  if (button) void saveOrganizationRule(button.dataset.saveRule).catch((error) => toast(error.message));
});
$('#closeSchemaCatalog').addEventListener('click', closeSchemaCatalog);
$('#schemaCatalogSearch').addEventListener('input', renderSchemaCatalog);
schemaCatalogGroups.addEventListener('click', (event) => {
  const card = event.target.closest('[data-schema-object]');
  if (card) void showSchemaDetail(card.dataset.schemaObject, card.dataset.schemaName);
});
schemaDetailPanel.addEventListener('click', (event) => {
  if (event.target.closest('[data-close-schema-detail]')) closeCurrentAppView('schema-detail', () => { schemaDetailPanel.hidden = true; });
});
$('#mobileInboxBtn').addEventListener('click', () => loadNotifications(true));
$('#closeNotifications').addEventListener('click', closeNotificationsPanel);
$('#markAllNotifications').addEventListener('click', async () => {
  await markNotificationsRead(notificationsCache.map((item) => Number(item.id)));
  renderNotifications();
  toast('همه اعلان‌ها خوانده شد');
});
notificationsList.addEventListener('click', async (event) => {
  const button = event.target.closest('[data-notification-id]');
  if (!button) return;
  const id = Number(button.dataset.notificationId);
  const card = button.closest('.notification-card');
  card.classList.toggle('expanded');
  await markNotificationsRead([id]);
  card.classList.remove('unread');
});
notificationBtn.addEventListener('click', enablePush);

$('#loginForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  const username = $('#username').value.trim();
  $('#loginError').textContent = '';
  const response = await fetch('/auth/login', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({username, password: $('#password').value})});
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    $('#loginError').textContent = data.detail || 'ورود ناموفق بود.';
    return;
  }
  applyProfile(data);
  loginDialog.close();
  $('#password').value = '';
  if (data.must_change_password) {
    openAccountDialog(data, true);
    return;
  }
  await onAuthenticated();
});
loginDialog.addEventListener('cancel', (event) => event.preventDefault());
accountDialog.addEventListener('cancel', (event) => {
  if (forceAccountDialog) event.preventDefault();
});
$$('#accountSettingsBtn, #accountSettingsBtnHeader').forEach((settingsButton) => settingsButton.addEventListener('click', async () => {
  try {
    const profile = await loadCurrentProfile();
    if (!profile) return showLogin();
    openAccountDialog(profile, profile.must_change_password);
    closeSidebar();
  } catch (error) { toast(error.message); }
}));
$('#closeAccountDialog').addEventListener('click', () => {
  if (!forceAccountDialog) accountDialog.close();
});
$('#changePasswordForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  const currentPassword = $('#currentPassword').value;
  const newPassword = $('#newPassword').value;
  const confirmPassword = $('#confirmPassword').value;
  const errorEl = $('#changePasswordError');
  errorEl.textContent = '';
  if (newPassword !== confirmPassword) {
    errorEl.textContent = 'تکرار رمز جدید یکسان نیست.';
    return;
  }
  const response = await fetch('/auth/change-password', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({current_password: currentPassword, new_password: newPassword}),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    errorEl.textContent = data.detail || 'تغییر رمز انجام نشد.';
    return;
  }
  forceAccountDialog = false;
  applyProfile(data);
  accountDialog.close();
  toast('رمز ورود با موفقیت تغییر کرد.');
  await onAuthenticated();
});
$('#logoutBtn').addEventListener('click', async () => {
  await fetch('/auth/logout', {method: 'POST'});
  conversations = [];
  renderConversations();
  showLogin();
});

async function onAuthenticated() {
  const profile = await loadCurrentProfile().catch(() => null);
  if (!profile && !isLocal) {
    showLogin();
    return;
  }
  if (profile?.must_change_password) {
    openAccountDialog(profile, true);
    return;
  }
  const loaded = await loadConversations().catch(() => false);
  if (!loaded) return;
  const selected = requestedNotificationId();
  await loadNotifications(Boolean(selected), selected);
  refreshPushState();
}

window.addEventListener('beforeinstallprompt', (event) => {
  event.preventDefault();
  installPrompt = event;
  $('#installBtn').hidden = false;
});
$('#installBtn').addEventListener('click', async () => {
  if (isNeginAndroidApp && window.NeginAndroid?.checkForUpdate) {
    window.NeginAndroid.checkForUpdate();
    closeSidebar();
    return;
  }
  if (isAndroid) {
    location.href = '/download/android';
    return;
  }
  if (installPrompt) {
    await installPrompt.prompt();
    installPrompt = null;
    $('#installBtn').hidden = true;
  } else if (isIOS) $('#installDialog').showModal();
  else toast('برای نصب، گزینه Install app مرورگر را انتخاب کنید.');
});
$('#closeInstallHelp').addEventListener('click', () => $('#installDialog').close());

if (isAndroid) {
  const installButton = $('#installBtn');
  installButton.hidden = false;
  const label = installButton.querySelector('span:last-child');
  if (label) label.textContent = isNeginAndroidApp ? 'بررسی به‌روزرسانی اپ' : 'دانلود اپ اندروید';
}

if (isAndroid && !isNeginAndroidApp) {
  $('#androidDownloadHeader').hidden = false;
  $('#androidDownloadLogin').hidden = false;
}

$('#profileName').textContent = localStorage.getItem('negin-display-user') || 'کاربر نگین پخش';
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/service-worker.js', {scope: '/', updateViaCache: 'none'}).then((registration) => {
    serviceWorkerRegistration = registration;
    void registration.update().catch(() => {});
  }).catch(() => {});
}
resizeInput();
initializeAppNavigation();
onAuthenticated();
