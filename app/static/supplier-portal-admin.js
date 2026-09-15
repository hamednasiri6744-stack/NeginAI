const $ = (s) => document.querySelector(s),
  esc = (v) =>
    String(v ?? "").replace(
      /[&<>'"]/g,
      (c) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          "'": "&#39;",
          '"': "&quot;",
        })[c],
    );
$('#accountMobile').addEventListener('input',()=>{$('#accountUsername').value=$('#accountMobile').value});
async function api(url, options = {}) {
  const r = await fetch(url, {
    ...options,
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(options.headers || {}),
    },
  });
  let b = {};
  try {
    b = await r.json();
  } catch {}
  if (r.status === 401) {
    location.href = "/warehouse-assistant";
    throw new Error("ابتدا وارد دستیار انبار شوید.");
  }
  if (!r.ok) throw new Error(b.detail || "خطا در ارتباط با سامانه");
  return b;
}
function error(m = "") {
  const e = $("#adminError");
  e.textContent = m;
  e.classList.toggle("hidden", !m);
  if (m) scrollTo({ top: 0, behavior: "smooth" });
}
$("#accountForm").onsubmit = async (e) => {
  e.preventDefault();
  error();
  const b = e.submitter;
  b.disabled = true;
  try {
    const a = await api("/warehouse-assistant/api/supplier-portal/accounts", {
      method: "POST",
      body: JSON.stringify({
        supplier_name: $("#accountSupplier").value,
        mobile: $("#accountMobile").value,
        username: $("#accountUsername").value,
        temporary_password: $("#accountPassword").value,
      }),
    });
    $("#accountResult").textContent =
      `حساب ${a.username} برای ${a.supplier_name} ساخته شد. رمز موقت را فقط از مسیر امن تحویل دهید.`;
    $("#accountResult").classList.remove("hidden");
    e.target.reset();
    await loadAccounts();
  } catch (x) {
    error(x.message);
  } finally {
    b.disabled = false;
  }
};
async function loadAccounts() {
  const a =
    (await api("/warehouse-assistant/api/supplier-portal/accounts")).accounts ||
    [];
  $("#accountList").innerHTML =
    `<table class="admin-table"><thead><tr><th>تأمین‌کننده</th><th>نام کاربری</th><th>موبایل</th><th>وضعیت</th><th>آخرین ورود</th></tr></thead><tbody>${a.map((x) => `<tr><td>${esc(x.supplier_name)}</td><td class="ltr">${esc(x.username)}</td><td class="ltr">${esc(x.mobile || "—")}</td><td>${x.active ? (x.must_change_password ? "فعال؛ رمز موقت" : "فعال") : "غیرفعال"}</td><td>${x.last_login_at ? esc(new Date(x.last_login_at).toLocaleString("fa-IR")) : "هنوز وارد نشده"}</td></tr>`).join("") || '<tr><td colspan="5">حسابی ثبت نشده است.</td></tr>'}</tbody></table>`;
  window.dispatchEvent(new Event('portal-accounts-updated'));
}
$("#refreshAccounts").onclick = () => loadAccounts().catch((x) => error(x.message));
loadAccounts().catch((x) => error(x.message));
