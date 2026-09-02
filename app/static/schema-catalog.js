(() => {
  let catalog = [];
  let activeDomain = null;
  let activeStructureType = null;
  const byId = (id) => document.getElementById(id);
  const escapeHtml = (value) => String(value ?? '').replace(/[&<>'"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));

  function matches(item, query) {
    const meta = item.catalog || {};
    return [item.schema, item.name, meta.persian_name, meta.description, meta.domain, ...(meta.aliases || [])]
      .join(' ').toLocaleLowerCase('fa').includes(query.toLocaleLowerCase('fa'));
  }

  function structureCards(items, formatter) {
    const structures = [
      { type: 'TABLE', title: 'جداول SQL', description: 'داده‌های پایه و عملیاتی', icon: '▦' },
      { type: 'VIEW', title: 'Viewها و گزارش‌های ورانگر', description: 'گزارش‌ها و ساختارهای نمایشی', icon: '◫' },
    ];
    return structures.map((structure) => {
      const count = items.filter((item) => item.type === structure.type).length;
      return `<button class="schema-group-card schema-structure-card" type="button" data-structure-type="${structure.type}"><span class="schema-group-icon">${structure.icon}</span><span><strong>${structure.title}</strong><small>${structure.description} · ${formatter.format(count)} مورد</small></span><b>›</b></button>`;
    }).join('');
  }

  function render(query = '') {
    const target = byId('schemaResults');
    const hint = byId('schemaHint');
    const formatter = new Intl.NumberFormat('fa-IR');
    const matching = catalog.filter((item) => !query || matches(item, query));
    target.className = 'object-grid schema-catalog-grid';

    if (!activeStructureType) {
      hint.textContent = `${formatter.format(matching.length)} منبع داده در دو ساختار جدا`;
      target.innerHTML = structureCards(matching, formatter);
      return;
    }

    const groups = new Map();
    matching.filter((item) => item.type === activeStructureType).forEach((item) => {
      const domain = item.catalog?.domain || 'سایر منابع';
      if (!groups.has(domain)) groups.set(domain, []);
      groups.get(domain).push(item);
    });
    const allItems = [...groups.values()].flat();
    const structureTitle = activeStructureType === 'VIEW' ? 'Viewها و گزارش‌های ورانگر' : 'جداول SQL';
    hint.textContent = activeDomain
      ? `${formatter.format(allItems.length)} مورد در گروه «${activeDomain}» از ${structureTitle}`
      : `${formatter.format(allItems.length)} مورد در ${structureTitle}`;

    if (!groups.size) {
      target.innerHTML = '<div class="empty-state">نتیجه‌ای پیدا نشد.</div>';
      return;
    }

    if (!activeDomain && !query) {
      target.innerHTML = `<button class="schema-back-button" type="button" data-back-schema-structures>‹ بازگشت به ساختارها</button>${[...groups.entries()].map(([domain, items]) => `
        <button class="schema-group-card" type="button" data-domain="${escapeHtml(domain)}"><span class="schema-group-icon">▪</span><span><strong>${escapeHtml(domain)}</strong><small>${formatter.format(items.length)} ${activeStructureType === 'VIEW' ? 'View' : 'جدول'}</small></span><b>›</b></button>`).join('')}`;
      return;
    }

    const displayed = activeDomain ? new Map([[activeDomain, groups.get(activeDomain) || []]]) : groups;
    target.innerHTML = `<button class="schema-back-button" type="button" data-back-schema-groups>‹ بازگشت به گروه‌ها</button>${[...displayed.entries()].map(([domain, items]) => `
      <section class="schema-domain"><header><h3>${escapeHtml(domain)}</h3><span>${items.length.toLocaleString('fa-IR')}</span></header>
      ${items.map((item) => `<details class="object-card schema-catalog-card"><summary>
        <span class="object-title"><strong>${escapeHtml(item.catalog?.persian_name || item.name)}</strong><small dir="ltr">${escapeHtml(item.schema)}.${escapeHtml(item.name)}</small></span>
        <span class="type">${escapeHtml(item.type)}</span><em>${item.column_count.toLocaleString('fa-IR')} ستون</em>
      </summary><p>${escapeHtml(item.catalog?.description || 'برای این منبع توضیحی ثبت نشده است.')}</p>
      <button type="button" class="schema-detail-button" data-schema="${escapeHtml(item.schema)}" data-name="${escapeHtml(item.name)}">نمایش ریز ستون‌ها</button><div class="schema-columns" data-columns></div></details>`).join('')}
      </section>`).join('')}`;
  }

  async function load() {
    try {
      const data = await api('/chat/schema-catalog');
      catalog = data.items || [];
      render(byId('schemaSearch').value.trim());
    } catch (error) { toast(error.message, true); }
  }

  async function showColumns(button) {
    const holder = button.parentElement.querySelector('[data-columns]');
    holder.textContent = 'در حال دریافت ستون‌ها…';
    try {
      const item = await api(`/chat/schema-catalog/object?schema=${encodeURIComponent(button.dataset.schema)}&name=${encodeURIComponent(button.dataset.name)}`);
      holder.innerHTML = (item.columns || []).map((column) => `<div><strong>${escapeHtml(column.persian_name || column.name)}</strong><small dir="ltr">${escapeHtml(column.name)} · ${escapeHtml(column.data_type || '')}</small>${column.primary_key ? '<b>کلید اصلی</b>' : ''}</div>`).join('') || 'ستونی ثبت نشده است.';
      button.remove();
    } catch (error) { holder.textContent = error.message; }
  }

  document.addEventListener('DOMContentLoaded', () => {
    const style = document.createElement('style');
    style.textContent = `.schema-catalog-grid{display:grid;gap:16px}.schema-domain{border:1px solid #e5e7eb;border-radius:14px;overflow:hidden;background:#fff}.schema-domain>header{display:flex;align-items:center;justify-content:space-between;padding:12px 16px;background:#f8fafc;border-bottom:1px solid #eef0f2}.schema-domain h3{margin:0;font-size:13px}.schema-domain header span{padding:3px 8px;border-radius:8px;background:#ece7ff;color:#6d3ee8;font-size:10px}.schema-catalog-card{margin:0;border:0;border-bottom:1px solid #edf0f2;border-radius:0}.schema-catalog-card:last-child{border-bottom:0}.schema-catalog-card summary{display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:12px;align-items:center;padding:12px 16px;cursor:pointer;list-style:none}.schema-catalog-card summary::-webkit-details-marker{display:none}.schema-catalog-card summary:hover{background:#fafbfc}.object-title{min-width:0;display:grid;gap:3px}.object-title strong,.object-title small{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.object-title strong{font-size:12px}.object-title small{color:#8b93a1;font-size:9px}.schema-catalog-card em{color:#8b93a1;font-size:10px;font-style:normal;white-space:nowrap}.schema-catalog-card>p{margin:0;padding:0 16px 9px;color:#687282;font-size:10px;line-height:1.8}.schema-detail-button{margin:0 16px 10px;border:1px solid #ddd6fe;border-radius:8px;background:#faf8ff;color:#6336d8;padding:6px 9px;font:inherit;font-size:10px;cursor:pointer}.schema-columns{display:grid;margin:0 16px 13px;border:1px solid #e5e7eb;border-radius:9px;overflow:hidden}.schema-columns:empty{display:none}.schema-columns>div{position:relative;display:grid;gap:2px;padding:8px 10px;border-bottom:1px solid #eef0f2}.schema-columns>div:last-child{border-bottom:0}.schema-columns strong{font-size:10px}.schema-columns small{color:#8b93a1;font-size:9px}.schema-columns b{position:absolute;left:8px;top:8px;padding:2px 5px;border-radius:5px;background:#dcfce7;color:#177244;font-size:8px}`;
    document.head.append(style);
    const groupStyle = document.createElement('style');
    groupStyle.textContent = `.schema-group-card{width:100%;display:grid;grid-template-columns:42px minmax(0,1fr) 28px;align-items:center;gap:12px;border:1px solid #e3e5e9;border-radius:15px;background:#fff;padding:15px;text-align:right;cursor:pointer;box-shadow:0 2px 8px #1f293708}.schema-group-card:hover{border-color:#b9a4fa;background:#fcfbff;box-shadow:0 7px 18px #6d3ee818}.schema-group-card span:nth-child(2){min-width:0;display:grid;gap:4px}.schema-group-card strong{font-size:13px}.schema-group-card small{color:#7d8795;font-size:10px}.schema-group-icon{width:38px;height:38px;display:grid;place-items:center;border-radius:11px;background:#eee9ff;color:#6740d6;font-size:20px}.schema-group-card b{font-size:25px;color:#8a68e8;font-weight:400}.schema-back-button{justify-self:start;border:0;border-radius:8px;background:#f0edff;color:#6540cb;padding:7px 10px;font:inherit;font-size:10px;cursor:pointer}`;
    document.head.append(groupStyle);
    document.querySelector('[data-page="schema"]').addEventListener('click', () => setTimeout(load, 0));
    byId('schemaSearch').oninput = () => {
      const query = byId('schemaSearch').value.trim();
      activeDomain = null;
      if (!catalog.length) return void load();
      render(query);
    };
    byId('schemaResults').addEventListener('click', (event) => {
      const structure = event.target.closest('[data-structure-type]');
      if (structure) {
        activeStructureType = structure.dataset.structureType;
        activeDomain = null;
        byId('schemaSearch').value = '';
        render();
        return;
      }
      const group = event.target.closest('[data-domain]');
      if (group) {
        activeDomain = group.dataset.domain;
        byId('schemaSearch').value = '';
        render();
        return;
      }
      if (event.target.closest('[data-back-schema-structures]')) {
        activeStructureType = null;
        activeDomain = null;
        render();
        return;
      }
      if (event.target.closest('[data-back-schema-groups]')) {
        activeDomain = null;
        render();
        return;
      }
      const button = event.target.closest('.schema-detail-button');
      if (button) void showColumns(button);
    });
  });
})();
