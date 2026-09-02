const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
document.documentElement.dataset.controlRuntime = 'started';
const DB_NAME = 'negin-control-v1';
const SNAPSHOT_STORE = 'state';
const operationQueue = 'operationQueue';
let snapshot = null;
let pendingOperations = [];
let syncing = false;
let toastTimer = null;
let personnelPage = 1;
let personnelColumnFilters = {};
let personnelVisibleColumns = null;
let activePersonnelViewId = '';
let personnelViewInitialized = false;
let personnelViewManuallySelected = false;
let personnelTemporaryViewActive = false;
let selectedBranchCode = 'alborz';
let branchDraftSelection = null;
let branchDraftDirty = false;

function esc(value) {
  return String(value ?? '').replace(/[&<>'"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
}

function uid(prefix) {
  const id = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return `${prefix}-${id}`;
}

function fa(value) { return Number(value || 0).toLocaleString('fa-IR'); }

function normalizeSearch(value) {
  return String(value ?? '').replace(/ي/g, 'ی').replace(/ك/g, 'ک').toLocaleLowerCase('fa').trim();
}

function formatDateTime(value) {
  if (!value) return 'نامشخص';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat('fa-IR', {dateStyle: 'short', timeStyle: 'short'}).format(date);
}

function toast(message, error = false) {
  const node = $('#toast');
  node.textContent = message;
  node.className = `toast show${error ? ' error' : ''}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { node.className = 'toast'; }, 3500);
}

function openDatabase() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(SNAPSHOT_STORE)) db.createObjectStore(SNAPSHOT_STORE);
      if (!db.objectStoreNames.contains(operationQueue)) db.createObjectStore(operationQueue, {keyPath: 'id'});
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function idbRequest(storeName, mode, operation) {
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(storeName, mode);
    const request = operation(transaction.objectStore(storeName));
    let result;
    request.onsuccess = () => { result = request.result; };
    request.onerror = () => reject(request.error);
    transaction.oncomplete = () => { db.close(); resolve(result); };
    transaction.onerror = () => { db.close(); reject(transaction.error); };
  });
}

const loadCachedSnapshot = () => idbRequest(SNAPSHOT_STORE, 'readonly', store => store.get('snapshot'));
const saveSnapshot = value => idbRequest(SNAPSHOT_STORE, 'readwrite', store => store.put(value, 'snapshot'));
const loadOperations = () => idbRequest(operationQueue, 'readonly', store => store.getAll());
const saveOperation = operation => idbRequest(operationQueue, 'readwrite', store => store.put(operation));
const removeOperation = id => idbRequest(operationQueue, 'readwrite', store => store.delete(id));

async function responseJson(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(data.detail || 'ارتباط با سرور انجام نشد.');
    error.status = response.status;
    throw error;
  }
  return data;
}

function setConnection(mode, text) {
  const node = $('#connectionState');
  node.className = `connection ${mode}`;
  $('b', node).textContent = text;
}

function showGate(message) {
  $('#controlApp').hidden = true;
  $('#accessGate').hidden = false;
  $('#accessGateMessage').textContent = message;
}

function showApp() {
  $('#accessGate').hidden = true;
  $('#controlApp').hidden = false;
}

function currentEntityRevision(operation, working = snapshot) {
  if (operation.entity === 'branch_roster') {
    return Number(working?.branch_rosters?.find(item => item.code === operation.entity_id)?.revision || 0);
  }
  const collection = operation.entity === 'personnel'
    ? working?.personnel
    : (operation.entity === 'personnel_view' ? working?.personnel_views : working?.positions);
  return Number(collection?.find(item => item.id === operation.entity_id)?.revision || 0);
}

function applyOptimistic(target, operation) {
  if (!target) return;
  if (operation.entity === 'position' && operation.action === 'upsert') {
    const index = target.positions.findIndex(item => item.id === operation.entity_id);
    const existing = index >= 0 ? target.positions[index] : {id: operation.entity_id, permission_keys: [], source: 'local'};
    const next = {...existing, ...operation.payload, revision: operation.base_revision + 1, deleted_at: null};
    if (index >= 0) target.positions[index] = next; else target.positions.push(next);
  } else if (operation.entity === 'position_permissions' && operation.action === 'replace') {
    const position = target.positions.find(item => item.id === operation.entity_id);
    if (position) {
      position.permission_keys = [...operation.payload.permission_keys];
      position.revision = operation.base_revision + 1;
    }
  } else if (operation.entity === 'personnel' && operation.action === 'upsert') {
    const index = target.personnel.findIndex(item => item.id === operation.entity_id);
    const position = target.positions.find(item => item.id === operation.payload.position_id);
    const existing = index >= 0 ? target.personnel[index] : {id: operation.entity_id, source: 'local'};
    const next = {...existing, ...operation.payload, position_title: position?.title || '', revision: operation.base_revision + 1, deleted_at: null};
    if (index >= 0) target.personnel[index] = next; else target.personnel.push(next);
  } else if (operation.entity === 'personnel_view' && operation.action === 'upsert') {
    target.personnel_views ||= [];
    if (operation.payload.is_default) {
      target.personnel_views.forEach(item => {
        if (item.id !== operation.entity_id && item.is_default) {
          item.is_default = false;
          item.revision = Number(item.revision || 0) + 1;
        }
      });
    }
    const index = target.personnel_views.findIndex(item => item.id === operation.entity_id);
    const existing = index >= 0 ? target.personnel_views[index] : {id: operation.entity_id};
    const next = {...existing, ...operation.payload, revision: operation.base_revision + 1, deleted_at: null};
    if (index >= 0) target.personnel_views[index] = next; else target.personnel_views.push(next);
  } else if (operation.entity === 'branch_roster' && operation.action === 'replace') {
    target.branch_rosters ||= [];
    const selectedIds = new Set(operation.payload.personnel_ids.map(Number));
    target.branch_rosters.forEach(roster => {
      roster.personnel_ids = roster.code === operation.entity_id
        ? [...selectedIds]
        : (roster.personnel_ids || []).filter(personnelId => !selectedIds.has(Number(personnelId)));
      roster.revision = operation.base_revision + 1;
    });
  } else if (operation.action === 'delete') {
    const key = operation.entity === 'personnel'
      ? 'personnel'
      : (operation.entity === 'personnel_view' ? 'personnel_views' : 'positions');
    target[key] = target[key].filter(item => item.id !== operation.entity_id);
  }
}

async function queueOperation(operation) {
  operation.created_at = Date.now();
  await saveOperation(operation);
  pendingOperations = await loadOperations();
  applyOptimistic(snapshot, operation);
  await saveSnapshot(snapshot);
  render();
  if (navigator.onLine) void syncQueue();
}

async function fetchSnapshot() {
  const response = await fetch('/control/api/bootstrap', {headers: {'Accept': 'application/json'}, cache: 'no-store'});
  return responseJson(response);
}

async function fetchPersonnelDirectory() {
  const response = await fetch('/control/api/personnel-directory', {headers: {'Accept': 'application/json'}, cache: 'no-store'});
  return responseJson(response);
}

function applyPersonnelView(view = null, {renderNow = true} = {}) {
  personnelTemporaryViewActive = false;
  activePersonnelViewId = view?.id || '';
  personnelColumnFilters = {...(view?.filters || {})};
  personnelVisibleColumns = view?.visible_columns ? [...view.visible_columns] : null;
  $('#personnelPageSize').value = String(view?.page_size || 50);
  $('#personnelStatusFilter').value = view?.status_filter || 'all';
  personnelPage = 1;
  personnelViewInitialized = true;
  if (renderNow && snapshot) render();
}

function restorePersonnelView(working) {
  const views = working?.personnel_views || [];
  let view = activePersonnelViewId ? views.find(item => item.id === activePersonnelViewId) : null;
  if (!view && !personnelViewManuallySelected) view = views.find(item => item.is_default) || null;
  if (view) applyPersonnelView(view, {renderNow: false});
  else if (!personnelViewInitialized || activePersonnelViewId) applyPersonnelView(null, {renderNow: false});
}

async function refreshFromServer({includeDirectory = true} = {}) {
  const cachedDirectory = snapshot?.personnel_directory || null;
  const fresh = await fetchSnapshot();
  fresh.personnel_directory = cachedDirectory;
  if (includeDirectory) {
    try {
      fresh.personnel_directory = await fetchPersonnelDirectory();
      delete fresh.personnel_directory_error;
    } catch (error) {
      if (error.status === 401 || error.status === 403) throw error;
      fresh.personnel_directory_error = error.message;
    }
  }
  pendingOperations = (await loadOperations()).sort((a, b) => a.created_at - b.created_at);
  for (const operation of pendingOperations) applyOptimistic(fresh, operation);
  snapshot = fresh;
  if (!branchDraftDirty) branchDraftSelection = null;
  restorePersonnelView(snapshot);
  await saveSnapshot(snapshot);
  showApp();
  render();
  return fresh;
}

async function syncQueue() {
  if (syncing || !navigator.onLine) return;
  pendingOperations = (await loadOperations()).sort((a, b) => a.created_at - b.created_at);
  if (!pendingOperations.length) {
    setConnection('online', 'آنلاین و همگام');
    renderStatus();
    return;
  }
  syncing = true;
  $('#syncButton').disabled = true;
  setConnection('pending', 'در حال همگام‌سازی');
  try {
    const response = await fetch('/control/api/sync', {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
      body: JSON.stringify({operations: pendingOperations.map(({blocked, error, created_at, ...operation}) => operation)}),
    });
    const data = await responseJson(response);
    const byId = new Map(data.results.map(result => [result.id, result]));
    for (const operation of pendingOperations) {
      const result = byId.get(operation.id);
      if (result?.status === 'applied' || result?.status === 'replayed') {
        await removeOperation(operation.id);
      } else if (result) {
        operation.blocked = true;
        operation.error = result.detail || 'این تغییر قابل اعمال نیست.';
        await saveOperation(operation);
      }
    }
    await refreshFromServer({includeDirectory: false});
    const blocked = pendingOperations.filter(item => item.blocked);
    setConnection(blocked.length ? 'error' : 'online', blocked.length ? 'نیاز به بررسی' : 'آنلاین و همگام');
    if (!blocked.length) toast('همگام‌سازی با موفقیت انجام شد.');
  } catch (error) {
    if (error.status === 401) showGate('نشست شما پایان یافته است؛ دوباره وارد شوید.');
    else if (error.status === 403) showGate(error.message);
    else setConnection('offline', 'آفلاین؛ تغییرات محفوظ است');
  } finally {
    syncing = false;
    $('#syncButton').disabled = false;
    pendingOperations = await loadOperations();
    renderStatus();
  }
}

function renderStatus() {
  const blocked = pendingOperations.filter(item => item.blocked);
  $('#pendingCount').textContent = fa(pendingOperations.length);
  $('#queueCount').textContent = fa(pendingOperations.length);
  $('#syncIssues').hidden = !blocked.length;
  $('#syncIssueText').textContent = blocked.map(item => item.error).filter(Boolean).join(' · ');
  $('#lastSyncText').textContent = blocked.length ? `${fa(blocked.length)} تغییر مشکل‌دار` : (pendingOperations.length ? 'در انتظار اتصال' : 'همه تغییرات همگام است');
}

function permissionTitle(key) {
  return snapshot.permissions.find(item => item.key === key)?.title || key;
}

function isPersonnelActive(item) {
  if (item.status === true || Number(item.status) === 1) return true;
  return normalizeSearch(item.status_title) === 'فعال';
}

function personnelCellValue(item, key) {
  if (key === 'branch_name' && Number(item.branch_id) === 0) return 'بدون شعبه';
  const value = item[key];
  if (value === null || value === undefined || value === '') return '—';
  if (key === 'credit' || key === 'cheque_credit') {
    const number = Number(value);
    return Number.isFinite(number) ? number.toLocaleString('fa-IR') : String(value);
  }
  return String(value);
}

function renderPersonnelViews() {
  const views = snapshot.personnel_views || [];
  const temporaryOption = personnelTemporaryViewActive ? '<option value="__temporary">نمایش موقت (ذخیره نشده)</option>' : '';
  $('#personnelViewSelect').innerHTML = `<option value="">نمایش کامل (سیستمی)</option>${temporaryOption}${views.map(item => `<option value="${esc(item.id)}">${item.is_default ? '★ ' : ''}${esc(item.name)}</option>`).join('')}`;
  $('#personnelViewSelect').value = personnelTemporaryViewActive ? '__temporary' : (views.some(item => item.id === activePersonnelViewId) ? activePersonnelViewId : '');
  $('#editPersonnelView').disabled = !activePersonnelViewId;
}

function directoryColumnOptions(directory, key) {
  const values = new Set();
  directory.rows.forEach(item => {
    const value = personnelCellValue(item, key);
    if (value !== '—') values.add(value);
  });
  return [...values].sort((left, right) => left.localeCompare(right, 'fa', {numeric: true}));
}

function filteredPersonnelRows(directory) {
  const query = normalizeSearch($('#personnelSearch').value);
  const statusFilter = $('#personnelStatusFilter').value;
  const filters = Object.entries(personnelColumnFilters).filter(([, value]) => normalizeSearch(value));
  const exactFilters = new Map(filters.map(([key, value]) => {
    const normalized = normalizeSearch(value);
    return [key, directory.rows.some(item => normalizeSearch(personnelCellValue(item, key)) === normalized)];
  }));
  return directory.rows.filter(item => {
    const active = isPersonnelActive(item);
    if (statusFilter === 'active' && !active) return false;
    if (statusFilter === 'inactive' && active) return false;
    if (query && !normalizeSearch(Object.values(item).join(' ')).includes(query)) return false;
    return filters.every(([key, requested]) => {
      const actual = normalizeSearch(personnelCellValue(item, key));
      const expected = normalizeSearch(requested);
      return exactFilters.get(key) ? actual === expected : actual.includes(expected);
    });
  });
}

function visiblePersonnelColumns(directory) {
  const requestedColumns = personnelVisibleColumns ? new Set(personnelVisibleColumns) : null;
  const columns = requestedColumns ? directory.columns.filter(column => requestedColumns.has(column.key)) : directory.columns;
  return columns.length ? columns : directory.columns;
}

function renderPersonnel() {
  renderPersonnelViews();
  const directory = snapshot.personnel_directory;
  if (!directory) {
    $('#personnelList').innerHTML = '<div class="empty directory-empty">فهرست پرسنل هنوز از ورانگر دریافت نشده است. در حالت آنلاین «دریافت از ورانگر» را بزنید.</div>';
    $('#directorySummary').textContent = '۰ رکورد';
    $('#personnelPageState').textContent = 'صفحه ۰ از ۰';
    $('#personnelPrevPage').disabled = true;
    $('#personnelNextPage').disabled = true;
    $('#directoryFreshness').textContent = snapshot.personnel_directory_error ? 'خطا در دریافت؛ نسخه ذخیره‌شده موجود نیست' : 'هنوز دریافت نشده';
    return;
  }
  const pageSize = Number($('#personnelPageSize').value || 50);
  const rows = filteredPersonnelRows(directory);
  const columns = visiblePersonnelColumns(directory);
  const pageCount = Math.max(1, Math.ceil(rows.length / pageSize));
  personnelPage = Math.min(Math.max(1, personnelPage), pageCount);
  const start = (personnelPage - 1) * pageSize;
  const visibleRows = rows.slice(start, start + pageSize);
  const ltrKeys = new Set(['personnel_code', 'mobile', 'dl_code', 'credit_no']);
  const numberKeys = new Set(['credit', 'cheque_credit']);
  const titleHeaders = columns.map(column => `<th scope="col"><span>${esc(column.title)}</span><small>${esc(column.source)}</small></th>`).join('');
  const filterHeaders = columns.map(column => {
    const options = directoryColumnOptions(directory, column.key);
    const listId = `personnel-filter-${column.key}`;
    return `<th><input data-column-filter="${esc(column.key)}" value="${esc(personnelColumnFilters[column.key] || '')}" list="${listId}" placeholder="تایپ یا انتخاب دقیق" aria-label="فیلتر ${esc(column.title)}"><datalist id="${listId}">${options.map(value => `<option value="${esc(value)}"></option>`).join('')}</datalist></th>`;
  }).join('');
  const body = visibleRows.map(item => `<tr>${columns.map(column => {
    const value = personnelCellValue(item, column.key);
    const classes = [ltrKeys.has(column.key) ? 'ltr-cell' : '', numberKeys.has(column.key) ? 'number-cell' : '', column.key === 'full_name' ? 'primary-cell' : ''].filter(Boolean).join(' ');
    if (column.key === 'status_title') return `<td><span class="status-pill${isPersonnelActive(item) ? '' : ' inactive'}">${esc(value)}</span></td>`;
    return `<td class="${classes}" title="${esc(value)}">${esc(value)}</td>`;
  }).join('')}</tr>`).join('');
  $('#personnelList').innerHTML = visibleRows.length ? `<table class="personnel-table"><thead><tr class="column-title-row">${titleHeaders}</tr><tr class="column-filter-row">${filterHeaders}</tr></thead><tbody>${body}</tbody></table>` : '<div class="empty directory-empty">رکوردی مطابق جست‌وجو و فیلتر پیدا نشد.</div>';
  const shownFrom = rows.length ? start + 1 : 0;
  const shownTo = Math.min(start + pageSize, rows.length);
  $('#directorySummary').textContent = `نمایش ${fa(shownFrom)} تا ${fa(shownTo)} از ${fa(rows.length)} رکورد · کل ورانگر ${fa(directory.row_count)}`;
  $('#personnelPageState').textContent = `صفحه ${fa(personnelPage)} از ${fa(rows.length ? pageCount : 0)}`;
  $('#personnelPrevPage').disabled = personnelPage <= 1 || !rows.length;
  $('#personnelNextPage').disabled = personnelPage >= pageCount || !rows.length;
  $('#directorySourceState').textContent = `منبع فقط‌خواندنی: ${directory.source}`;
  $('#directoryFreshness').textContent = `${snapshot.personnel_directory_error ? 'نسخه ذخیره‌شده' : 'آخرین دریافت'}: ${formatDateTime(directory.fetched_at)}`;
}

function branchRoster(code = selectedBranchCode) {
  return (snapshot.branch_rosters || []).find(item => item.code === code) || null;
}

function ensureBranchDraft() {
  if (branchDraftSelection === null) {
    branchDraftSelection = new Set((branchRoster()?.personnel_ids || []).map(Number));
  }
  return branchDraftSelection;
}

function personnelBranchMap() {
  const assignments = new Map();
  (snapshot.branch_rosters || []).forEach(roster => {
    (roster.personnel_ids || []).forEach(personnelId => assignments.set(Number(personnelId), roster));
  });
  return assignments;
}

function branchSearchRows() {
  const rows = snapshot.personnel_directory?.rows || [];
  const query = normalizeSearch($('#branchPersonnelSearch').value);
  if (!query) return rows;
  return rows.filter(item => normalizeSearch([
    item.full_name, item.first_name, item.last_name, item.personnel_code, item.mobile,
  ].join(' ')).includes(query));
}

function renderBranches() {
  const rosters = snapshot.branch_rosters || [];
  if (rosters.length && !rosters.some(item => item.code === selectedBranchCode)) selectedBranchCode = rosters[0].code;
  const selectedRoster = branchRoster();
  const draft = ensureBranchDraft();
  const assignments = personnelBranchMap();
  $('#branchSelector').innerHTML = rosters.map(roster => {
    const count = roster.code === selectedBranchCode ? draft.size : (roster.personnel_ids || []).length;
    return `<button type="button" class="branch-choice${roster.code === selectedBranchCode ? ' active' : ''}" data-branch-code="${esc(roster.code)}"><span>${esc(roster.title)}</span><b>${fa(count)} نفر</b></button>`;
  }).join('');
  $('#branchRosterTitle').textContent = selectedRoster ? `پرسنل شعبه ${selectedRoster.title}` : 'پرسنل شعبه';
  $('#branchRosterSummary').textContent = `${fa(draft.size)} نفر انتخاب شده${branchDraftDirty ? ' · ثبت‌نشده' : ''}`;
  $('#saveBranchRoster').disabled = !selectedRoster || !branchDraftDirty;
  const directory = snapshot.personnel_directory;
  if (!directory) {
    $('#branchRosterList').innerHTML = '<div class="empty">برای انتخاب پرسنل شعب، ابتدا فهرست ورانگر را در بخش پرسنل دریافت کنید.</div>';
    return;
  }
  const rows = branchSearchRows();
  $('#branchRosterList').innerHTML = rows.length ? rows.map(item => {
    const personnelId = Number(item.personnel_id);
    const assignedRoster = assignments.get(personnelId);
    const assignedTitle = draft.has(personnelId)
      ? selectedRoster?.title
      : (assignedRoster?.code === selectedBranchCode ? null : assignedRoster?.title);
    return `<label class="branch-personnel-row${draft.has(personnelId) ? ' selected' : ''}">
      <input type="checkbox" data-branch-personnel-id="${personnelId}" ${draft.has(personnelId) ? 'checked' : ''}>
      <span class="branch-personnel-main"><b>${esc(item.full_name || `${item.first_name || ''} ${item.last_name || ''}`.trim() || 'بدون نام')}</b><small>کد پرسنلی ${esc(personnelCellValue(item, 'personnel_code'))} · ${esc(personnelCellValue(item, 'mobile'))}</small></span>
      <span class="status-pill${isPersonnelActive(item) ? '' : ' inactive'}">${esc(personnelCellValue(item, 'status_title'))}</span>
      <span class="branch-assignment${assignedTitle ? '' : ' unassigned'}">${assignedTitle ? `عضو ${esc(assignedTitle)}` : 'بدون شعبه'}</span>
    </label>`;
  }).join('') : '<div class="empty">پرسنلی مطابق جست‌وجو پیدا نشد.</div>';
}

async function exportPersonnelExcel() {
  const directory = snapshot.personnel_directory;
  if (!directory) {
    toast('ابتدا فهرست پرسنل را از ورانگر دریافت کنید.', true);
    return;
  }
  if (!navigator.onLine) {
    toast('ساخت فایل Excel به اتصال سرور نیاز دارد؛ فیلتر فعلی محفوظ است.', true);
    return;
  }
  const button = $('#exportPersonnelExcel');
  button.disabled = true;
  button.textContent = 'در حال ساخت…';
  try {
    const response = await fetch('/control/api/personnel-directory/export.xlsx', {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'Accept': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'},
      body: JSON.stringify({
        column_keys: visiblePersonnelColumns(directory).map(column => column.key),
        personnel_ids: filteredPersonnelRows(directory).map(item => Number(item.personnel_id)),
      }),
    });
    if (!response.ok) await responseJson(response);
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement('a');
    link.href = url;
    link.download = 'فهرست-پرسنل-ورانگر.xlsx';
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    toast('خروجی Excel از جدول فیلترشده آماده شد.');
  } catch (error) {
    toast(error.message || 'ساخت خروجی Excel ممکن نشد.', true);
  } finally {
    button.disabled = false;
    button.textContent = 'خروجی Excel';
  }
}

function renderPositions() {
  $('#positionList').innerHTML = snapshot.positions.length ? snapshot.positions.map(item => `
    <article class="position-card" data-position-id="${esc(item.id)}">
      <header><div><h3>${esc(item.title)}</h3><p class="code">${esc(item.code)}</p></div><span class="pill${item.active ? '' : ' inactive'}">${item.active ? 'فعال' : 'غیرفعال'}</span></header>
      <p>${esc(item.description || 'بدون شرح')}</p>
      <div class="permission-summary">${item.permission_keys.length ? item.permission_keys.map(key => `<span>${esc(permissionTitle(key))}</span>`).join('') : '<span>بدون دسترسی</span>'}</div>
      <div class="card-actions"><button type="button" data-edit-position="${esc(item.id)}">ویرایش</button><button class="delete" type="button" data-delete-position="${esc(item.id)}">حذف</button></div>
    </article>`).join('') : '<div class="empty">سمتی تعریف نشده است.</div>';
}

function renderPermissions() {
  $('#permissionMatrix').innerHTML = snapshot.positions.map(position => `
    <article class="permission-card" data-access-position="${esc(position.id)}">
      <header><div><h3>${esc(position.title)}</h3><p class="code">${esc(position.code)}</p></div><span class="pill${position.active ? '' : ' inactive'}">${position.active ? 'فعال' : 'غیرفعال'}</span></header>
      <div class="permission-options">${snapshot.permissions.map(permission => `<label class="permission-option"><input type="checkbox" value="${esc(permission.key)}" ${position.permission_keys.includes(permission.key) ? 'checked' : ''}><span><strong>${esc(permission.title)}</strong><small>${esc(permission.description)}</small></span></label>`).join('')}</div>
      <button class="primary" type="button" data-save-access="${esc(position.id)}">ذخیره دسترسی‌های این سمت</button>
    </article>`).join('');
}

function render() {
  if (!snapshot) return;
  showApp();
  const directoryRows = snapshot.personnel_directory?.rows || [];
  $('#activePersonnelCount').textContent = fa(directoryRows.filter(isPersonnelActive).length);
  $('#personnelCount').textContent = `از ${fa(directoryRows.length)} نفر`;
  $('#activePositionCount').textContent = fa(snapshot.positions.filter(item => item.active).length);
  $('#positionCount').textContent = `از ${fa(snapshot.positions.length)} سمت`;
  $('#permissionCount').textContent = fa(snapshot.permissions.length);
  renderPersonnel();
  renderBranches();
  renderPositions();
  renderPermissions();
  renderStatus();
}

function openPosition(item = null) {
  $('#positionDialogTitle').textContent = item ? 'ویرایش سمت' : 'سمت جدید';
  $('#positionId').value = item?.id || '';
  $('#positionRevision').value = item?.revision || 0;
  $('#positionCode').value = item?.code || '';
  $('#positionTitle').value = item?.title || '';
  $('#positionDescription').value = item?.description || '';
  $('#positionActive').checked = item ? Boolean(item.active) : true;
  $('#positionDialog').showModal();
}

function renderPersonnelViewColumns(selectedKeys) {
  const columns = snapshot.personnel_directory?.columns || [];
  const selected = new Set(selectedKeys);
  $('#personnelViewColumns').innerHTML = columns.map(column => `<label><input type="checkbox" value="${esc(column.key)}" ${selected.has(column.key) ? 'checked' : ''}><span><b>${esc(column.title)}</b><small>${esc(column.source)}</small></span></label>`).join('');
}

function openPersonnelView(view = null) {
  const directory = snapshot.personnel_directory;
  if (!directory) {
    toast('ابتدا فهرست پرسنل را از ورانگر دریافت کنید.', true);
    return;
  }
  const selectedColumns = view?.visible_columns || personnelVisibleColumns || directory.columns.map(column => column.key);
  $('#personnelViewDialogTitle').textContent = view ? 'ویرایش طرح نمایش' : 'طرح نمایش جدید';
  $('#personnelViewId').value = view?.id || '';
  $('#personnelViewRevision').value = view?.revision || 0;
  $('#personnelViewName').value = view?.name || '';
  $('#personnelViewPageSize').value = String(view?.page_size || $('#personnelPageSize').value || 50);
  $('#personnelViewStatusFilter').value = view?.status_filter || $('#personnelStatusFilter').value || 'all';
  $('#personnelViewDefault').checked = Boolean(view?.is_default);
  $('#deletePersonnelView').hidden = !view;
  renderPersonnelViewColumns(selectedColumns);
  $('#personnelViewDialog').showModal();
}

async function rebaseBlocked() {
  try {
    const fresh = await fetchSnapshot();
    fresh.personnel_directory = snapshot?.personnel_directory || null;
    const operations = (await loadOperations()).sort((a, b) => a.created_at - b.created_at);
    for (const operation of operations) {
      if (operation.blocked) {
        operation.base_revision = currentEntityRevision(operation, fresh);
        delete operation.blocked;
        delete operation.error;
        await saveOperation(operation);
      }
      applyOptimistic(fresh, operation);
    }
    snapshot = fresh;
    if (!branchDraftDirty) branchDraftSelection = null;
    restorePersonnelView(snapshot);
    pendingOperations = operations;
    await saveSnapshot(snapshot);
    render();
    await syncQueue();
  } catch (error) { toast(error.message, true); }
}

async function discardBlocked() {
  for (const operation of await loadOperations()) if (operation.blocked) await removeOperation(operation.id);
  try { await refreshFromServer(); await syncQueue(); } catch (error) { toast(error.message, true); }
}

async function refreshPersonnelFromVaranegar() {
  if (!navigator.onLine) {
    toast('برای دریافت نسخه تازه باید اتصال شبکه برقرار باشد.', true);
    return;
  }
  const button = $('#refreshPersonnel');
  button.disabled = true;
  button.textContent = 'در حال دریافت…';
  try {
    const directory = await fetchPersonnelDirectory();
    snapshot.personnel_directory = directory;
    delete snapshot.personnel_directory_error;
    personnelPage = 1;
    await saveSnapshot(snapshot);
    render();
    toast(`${fa(directory.row_count)} رکورد پرسنلی از ورانگر دریافت شد.`);
  } catch (error) {
    if (error.status === 401) showGate('نشست شما پایان یافته است؛ دوباره وارد شوید.');
    else if (error.status === 403) showGate(error.message);
    else {
      snapshot.personnel_directory_error = error.message;
      renderPersonnel();
      toast('دریافت فهرست تازه ممکن نشد؛ نسخه ذخیره‌شده باقی ماند.', true);
    }
  } finally {
    button.disabled = false;
    button.textContent = 'دریافت از ورانگر';
  }
}

$$('[data-tab]').forEach(button => button.addEventListener('click', () => {
  $$('[data-tab]').forEach(item => item.classList.toggle('active', item === button));
  $$('.tab-panel').forEach(panel => panel.classList.toggle('active', panel.id === `tab-${button.dataset.tab}`));
}));
$$('[data-close]').forEach(button => button.addEventListener('click', () => $(`#${button.dataset.close}`).close()));
$('#newPosition').addEventListener('click', () => openPosition());
$('#personnelSearch').addEventListener('input', () => { personnelPage = 1; renderPersonnel(); });
$('#personnelStatusFilter').addEventListener('change', () => { personnelPage = 1; renderPersonnel(); });
$('#personnelPageSize').addEventListener('change', () => { personnelPage = 1; renderPersonnel(); });
$('#personnelViewSelect').addEventListener('change', event => {
  if (event.target.value === '__temporary') return;
  personnelViewManuallySelected = true;
  const view = (snapshot.personnel_views || []).find(item => item.id === event.target.value) || null;
  applyPersonnelView(view);
});
$('#newPersonnelView').addEventListener('click', () => openPersonnelView());
$('#editPersonnelView').addEventListener('click', () => {
  const view = (snapshot.personnel_views || []).find(item => item.id === activePersonnelViewId);
  if (view) openPersonnelView(view);
});
$('#clearPersonnelFilters').addEventListener('click', () => {
  personnelColumnFilters = {};
  $('#personnelSearch').value = '';
  $('#personnelStatusFilter').value = 'all';
  personnelPage = 1;
  renderPersonnel();
});
$('#exportPersonnelExcel').addEventListener('click', exportPersonnelExcel);
$('#refreshPersonnel').addEventListener('click', refreshPersonnelFromVaranegar);
$('#personnelPrevPage').addEventListener('click', () => { personnelPage -= 1; renderPersonnel(); });
$('#personnelNextPage').addEventListener('click', () => { personnelPage += 1; renderPersonnel(); });
$('#syncButton').addEventListener('click', syncQueue);
$('#retryIssues').addEventListener('click', rebaseBlocked);
$('#discardIssues').addEventListener('click', discardBlocked);

let personnelFilterTimer = null;
$('#personnelList').addEventListener('input', event => {
  const key = event.target.dataset.columnFilter;
  if (!key) return;
  personnelColumnFilters[key] = event.target.value;
  personnelPage = 1;
  clearTimeout(personnelFilterTimer);
  personnelFilterTimer = setTimeout(() => {
    renderPersonnel();
    const input = $(`[data-column-filter="${key}"]`);
    if (input) {
      input.focus();
      input.setSelectionRange(input.value.length, input.value.length);
    }
  }, 220);
});

$('#personnelViewForm').addEventListener('submit', async event => {
  event.preventDefault();
  const visibleColumns = $$('#personnelViewColumns input:checked').map(input => input.value);
  if (!visibleColumns.length) {
    toast('حداقل یک ستون را برای نمایش انتخاب کنید.', true);
    return;
  }
  const entityId = $('#personnelViewId').value || uid('view');
  const payload = {
    name: $('#personnelViewName').value.trim(),
    is_default: $('#personnelViewDefault').checked,
    page_size: Number($('#personnelViewPageSize').value),
    status_filter: $('#personnelViewStatusFilter').value,
    visible_columns: visibleColumns,
    filters: Object.fromEntries(Object.entries(personnelColumnFilters).filter(([, value]) => String(value).trim())),
  };
  activePersonnelViewId = entityId;
  personnelViewManuallySelected = true;
  applyPersonnelView({id: entityId, ...payload}, {renderNow: false});
  await queueOperation({
    id: uid('op'), entity: 'personnel_view', action: 'upsert', entity_id: entityId,
    base_revision: Number($('#personnelViewRevision').value || 0), payload,
  });
  $('#personnelViewDialog').close();
  toast('طرح نمایش در صف امن دستگاه ذخیره شد.');
});

$('#applyTemporaryPersonnelView').addEventListener('click', () => {
  const visibleColumns = $$('#personnelViewColumns input:checked').map(input => input.value);
  if (!visibleColumns.length) {
    toast('حداقل یک ستون را برای نمایش انتخاب کنید.', true);
    return;
  }
  activePersonnelViewId = '';
  personnelTemporaryViewActive = true;
  personnelViewManuallySelected = true;
  personnelViewInitialized = true;
  personnelVisibleColumns = visibleColumns;
  $('#personnelPageSize').value = $('#personnelViewPageSize').value;
  $('#personnelStatusFilter').value = $('#personnelViewStatusFilter').value;
  personnelPage = 1;
  $('#personnelViewDialog').close();
  renderPersonnel();
  toast('طرح فقط برای همین اجرا اعمال شد و ذخیره نشد.');
});

$('#deletePersonnelView').addEventListener('click', async () => {
  const view = (snapshot.personnel_views || []).find(item => item.id === $('#personnelViewId').value);
  if (!view || !confirm(`طرح «${view.name}» حذف شود؟`)) return;
  $('#personnelViewDialog').close();
  personnelViewManuallySelected = true;
  applyPersonnelView(null, {renderNow: false});
  await queueOperation({id: uid('op'), entity: 'personnel_view', action: 'delete', entity_id: view.id, base_revision: view.revision, payload: {}});
  toast('حذف طرح نمایش در صف امن دستگاه ذخیره شد.');
});

$('#branchSelector').addEventListener('click', event => {
  const button = event.target.closest('[data-branch-code]');
  if (!button || button.dataset.branchCode === selectedBranchCode) return;
  if (branchDraftDirty && !confirm('انتخاب‌های ثبت‌نشده این شعبه کنار گذاشته شود؟')) return;
  selectedBranchCode = button.dataset.branchCode;
  branchDraftSelection = null;
  branchDraftDirty = false;
  renderBranches();
});

$('#branchPersonnelSearch').addEventListener('input', renderBranches);

$('#branchRosterList').addEventListener('change', event => {
  const personnelId = Number(event.target.dataset.branchPersonnelId);
  if (!Number.isInteger(personnelId)) return;
  const draft = ensureBranchDraft();
  if (event.target.checked) draft.add(personnelId); else draft.delete(personnelId);
  branchDraftDirty = true;
  event.target.closest('.branch-personnel-row')?.classList.toggle('selected', event.target.checked);
  $('#branchRosterSummary').textContent = `${fa(draft.size)} نفر انتخاب شده · ثبت‌نشده`;
  $('#saveBranchRoster').disabled = false;
});

$('#selectAllBranchPersonnel').addEventListener('click', () => {
  const draft = ensureBranchDraft();
  branchSearchRows().forEach(item => draft.add(Number(item.personnel_id)));
  branchDraftDirty = true;
  renderBranches();
});

$('#clearBranchPersonnel').addEventListener('click', () => {
  branchDraftSelection = new Set();
  branchDraftDirty = true;
  renderBranches();
});

$('#saveBranchRoster').addEventListener('click', async () => {
  const roster = branchRoster();
  if (!roster || !branchDraftDirty) return;
  const personnelIds = [...ensureBranchDraft()].sort((left, right) => left - right);
  const previousDraft = new Set(personnelIds);
  branchDraftDirty = false;
  branchDraftSelection = null;
  try {
    await queueOperation({
      id: uid('op'), entity: 'branch_roster', action: 'replace', entity_id: roster.code,
      base_revision: Number(roster.revision || 0), payload: {personnel_ids: personnelIds},
    });
    toast(`پرسنل شعبه ${roster.title} در صف امن دستگاه ثبت شد.`);
  } catch (error) {
    branchDraftSelection = previousDraft;
    branchDraftDirty = true;
    renderBranches();
    toast(error.message || 'ثبت پرسنل شعبه ممکن نشد.', true);
  }
});

$('#positionForm').addEventListener('submit', async event => {
  event.preventDefault();
  const entityId = $('#positionId').value || uid('position');
  await queueOperation({
    id: uid('op'), entity: 'position', action: 'upsert', entity_id: entityId,
    base_revision: Number($('#positionRevision').value || 0),
    payload: {code: $('#positionCode').value.trim(), title: $('#positionTitle').value.trim(), description: $('#positionDescription').value.trim(), active: $('#positionActive').checked},
  });
  $('#positionDialog').close();
  toast('تغییر سمت در صف امن دستگاه ذخیره شد.');
});

$('#positionList').addEventListener('click', async event => {
  const editId = event.target.dataset.editPosition;
  const deleteId = event.target.dataset.deletePosition;
  if (editId) openPosition(snapshot.positions.find(item => item.id === editId));
  if (deleteId) {
    const item = snapshot.positions.find(position => position.id === deleteId);
    if (item && confirm(`سمت «${item.title}» حذف شود؟`)) await queueOperation({id: uid('op'), entity: 'position', action: 'delete', entity_id: item.id, base_revision: item.revision, payload: {}});
  }
});

$('#permissionMatrix').addEventListener('click', async event => {
  const positionId = event.target.dataset.saveAccess;
  if (!positionId) return;
  const card = event.target.closest('[data-access-position]');
  const position = snapshot.positions.find(item => item.id === positionId);
  const permissionKeys = $$('input[type="checkbox"]:checked', card).map(input => input.value);
  await queueOperation({id: uid('op'), entity: 'position_permissions', action: 'replace', entity_id: positionId, base_revision: position.revision, payload: {permission_keys: permissionKeys}});
  toast('دسترسی‌های سمت در صف امن دستگاه ذخیره شد.');
});

window.addEventListener('online', () => { setConnection('pending', 'اتصال برقرار شد'); void syncQueue(); });
window.addEventListener('offline', () => setConnection('offline', 'آفلاین؛ تغییرات محفوظ است'));

async function start() {
  try {
    snapshot = await loadCachedSnapshot();
    pendingOperations = (await loadOperations()).sort((a, b) => a.created_at - b.created_at);
    if (snapshot) { restorePersonnelView(snapshot); showApp(); render(); setConnection('offline', 'نمایش نسخه ذخیره‌شده'); }
    if (!navigator.onLine) {
      if (!snapshot) showGate('این دستگاه هنوز نسخه آفلاین کنسول را دریافت نکرده است. یک بار در حالت آنلاین وارد شوید.');
      return;
    }
    await refreshFromServer();
    setConnection('online', pendingOperations.length ? 'آنلاین؛ در انتظار همگام‌سازی' : 'آنلاین و همگام');
    await syncQueue();
  } catch (error) {
    if (error.status === 401) showGate('برای استفاده از کنسول کنترل، ابتدا وارد حساب سازمانی شوید.');
    else if (error.status === 403) showGate(error.message);
    else if (snapshot) setConnection('offline', 'آفلاین؛ نسخه ذخیره‌شده');
    else showGate('دریافت کنسول کنترل ممکن نشد. اتصال شبکه را بررسی کنید.');
  }
}

if ('serviceWorker' in navigator) navigator.serviceWorker.register('/service-worker.js', {scope: '/'}).catch(() => {});
start();
