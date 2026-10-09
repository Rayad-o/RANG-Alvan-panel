// پنل خریدار: بدهی‌ها، ثبت درخواست خرید (با قانون سقف بدهی) و پیگیری مراحل
// پیام دقیق مورد نیاز وقتی بدهی از سقف بیشتر است
const DEBT_BLOCK_MESSAGE = "لطفا اول بدهی خود را پرداخت کنید";

let buyerSummary = null;

async function loadBuyerSummary() {
    buyerSummary = await apiJson("/buyer/summary");
    renderBuyerNotice();
    return buyerSummary;
}

// بنر بالای صفحه‌های خریدار: اگر بدهی از سقف بیشتر باشد پیام ممنوعیت، وگرنه وضعیت مجاز
function renderBuyerNotice() {
    const s = buyerSummary;
    if (!s) return;
    const html = s.blocked
        ? `<div class="notice bad" role="alert"><span class="ico">!</span><div><b>${DEBT_BLOCK_MESSAGE}</b>
              بدهی شما ${toman(s.total_debt)} است و از سقف مجاز (${toman(s.debt_limit)}) بیشتر است؛ تا پرداخت آن امکان ثبت درخواست خرید وجود ندارد.</div></div>`
        : "";
    $$(".buyer-notice").forEach(el => { el.innerHTML = html; });
}

// ---------------------------------------------------------------------------
// داشبورد خریدار
// ---------------------------------------------------------------------------
async function loadBuyerHome() {
    $("#homeTitle").textContent = `سلام، ${user.full_name}`;
    $("#homeSub").textContent = "وضعیت بدهی و درخواست‌های خرید شما";
    const body = $("#homeBody");

    let s, requests, debts;
    try {
        [s, requests, debts] = await Promise.all([loadBuyerSummary(), apiJson("/buyer/requests"), apiJson("/buyer/debts")]);
    } catch (err) {
        body.innerHTML = `<div class="notice bad"><span class="ico">!</span><div>${esc(err.message)}</div></div>`;
        return;
    }
    cacheRequests(requests);

    const total = Number(s.total_debt), limit = Number(s.debt_limit);
    const used = limit > 0 ? Math.min((total / limit) * 100, 100) : (total > 0 ? 100 : 0);
    const level = s.blocked ? "bad" : used >= 70 ? "warn" : "";
    const openDebts = debts.filter(d => d.status === "open").slice(0, 3);

    body.innerHTML = `
        <div class="buyer-notice"></div>
        <div class="hero">
            <div class="card debt-hero">
                <h3>مجموع بدهی شما</h3>
                <div class="big num">${fmt(total)}<small>تومان</small></div>
                <div class="limit-bar" aria-hidden="true"><i class="${level}" style="width:0" data-w="${used}"></i></div>
                <div class="limit-meta"><span>سقف مجاز برای ثبت درخواست: ${toman(limit)}</span><span>${fmt(Math.round(used))}٪ از سقف</span></div>
            </div>
            <div class="panel">
                <h2>درخواست خرید</h2>
                <p class="sub">${s.blocked ? "تا پرداخت بدهی، ثبت درخواست ممکن نیست" : "از کارخانهٔ رنگ سفارش دهید"}</p>
                <div class="stat-list">
                    <div class="s"><span>درخواست‌های در جریان</span><b>${fmt(s.open_requests)}</b></div>
                    <div class="s"><span>بدهی‌های باز</span><b>${fmt(s.open_debts)}</b></div>
                </div>
                <button class="btn block" id="homeNewRequest" style="margin-top:14px">＋ درخواست خرید جدید</button>
            </div>
        </div>
        <div class="grid-2">
            <div class="panel">
                <div class="panel-head"><h2>آخرین درخواست‌ها</h2><a class="sub" href="#/myRequests">همه</a></div>
                <div id="homeRequests">${requests.length ? requests.slice(0, 5).map(r => `
                    <button class="work-item" data-open-request="${r.id}">
                        <span><b>${toFaDigits(esc(r.ref))} — ${itemsSummary(r.items)}</b><small>${toFaDigits(fmtDate(r.created_at, true))}</small></span>
                        ${statusBadge(r.status)}
                    </button>`).join("") : '<div class="empty">هنوز درخواستی ثبت نکرده‌اید</div>'}</div>
            </div>
            <div class="panel">
                <div class="panel-head"><h2>بدهی‌های باز</h2><a class="sub" href="#/myDebts">همه</a></div>
                ${openDebts.length ? `<div class="pill-list">${openDebts.map(d => `
                    <div class="person"><span>${esc(d.description) || "بدهی"}<small>${d.due_date ? "سررسید " + toFaDigits(fmtDate(d.due_date)) : "بدون سررسید"}</small></span><b>${toman(d.remaining)}</b></div>`).join("")}</div>`
                    : '<div class="empty">بدهی بازی ندارید 🎉</div>'}
            </div>
        </div>`;

    renderBuyerNotice();
    requestAnimationFrame(() => requestAnimationFrame(() => $$(".limit-bar i").forEach(i => { i.style.width = i.dataset.w + "%"; })));
    $("#homeNewRequest").addEventListener("click", openNewRequest);
}

// ---------------------------------------------------------------------------
// بدهی‌های من
// ---------------------------------------------------------------------------
const myDebtList = createList({
    endpoint: "/buyer/debts", body: "#myDebtBody", pageSize: 500, columns: 7,
    row: d => `
        <tr>
            <td>${esc(d.description) || "—"}</td>
            <td>${toFaDigits(fmtDate(d.created_at))}</td>
            <td>${d.due_date ? toFaDigits(fmtDate(d.due_date)) : "—"}</td>
            <td>${fmt(d.amount)}</td>
            <td>${fmt(d.paid_amount)}</td>
            <td><b>${d.status === "paid" ? "—" : fmt(d.remaining)}</b></td>
            <td>${d.status === "paid" ? badge(["", "green"], "پرداخت‌شده") : badge(["", "orange"], "باز")}</td>
        </tr>`,
});

// ---------------------------------------------------------------------------
// درخواست‌های من
// ---------------------------------------------------------------------------
const myRequestList = createList({
    endpoint: "/buyer/requests", body: "#myRequestBody", pageSize: 200, columns: 6,
    row: r => {
        cacheRequests([r]);
        const hint = r.status === "rejected" ? esc(r.decision_note)
            : r.department ? `بخش ${esc(r.department)}${r.assigned_to_name ? " • " + esc(r.assigned_to_name) : ""}` : "در انتظار بررسی حسابدار";
        return `
        <tr>
            <td>${toFaDigits(esc(r.ref))}</td>
            <td>${toFaDigits(fmtDate(r.created_at, true))}</td>
            <td style="white-space:normal;min-width:200px">${itemsSummary(r.items)}</td>
            <td>${statusBadge(r.status)}</td>
            <td style="white-space:normal;min-width:160px;color:var(--muted)">${hint || "—"}</td>
            <td><button class="btn sm ghost" data-act="open" data-id="${r.id}">جزئیات</button></td>
        </tr>`;
    },
    onAction: (act, r) => openRequest(r),
});

// ---------------------------------------------------------------------------
// فرم درخواست خرید جدید
// ---------------------------------------------------------------------------
async function openNewRequest() {
    let s;
    try { s = await loadBuyerSummary(); } catch (e) { toast(e.message, true); return; }

    // قانون اصلی: بدهی بیشتر از سقف → فرم باز نمی‌شود و فقط پیام نمایش داده می‌شود
    if (s.blocked) {
        Modal.open("امکان ثبت درخواست وجود ندارد", `
            <div class="notice bad" role="alert" style="margin:0"><span class="ico">!</span><div><b>${DEBT_BLOCK_MESSAGE}</b>
                بدهی شما ${toman(s.total_debt)} است؛ سقف مجاز ${toman(s.debt_limit)} می‌باشد.</div></div>
            <div class="modal-actions"><a class="btn" href="#/myDebts" id="goDebts">مشاهدهٔ بدهی‌های من</a></div>`);
        $("#goDebts").addEventListener("click", Modal.close);
        return;
    }

    let products = [];
    try { products = await apiJson("/buyer/products"); } catch (e) { toast(e.message, true); return; }
    if (!products.length) { toast("فعلاً کالایی برای سفارش ثبت نشده است", true); return; }

    const options = products.map(p =>
        `<option value="${p.id}">${esc(p.title)} — ${esc(p.code)}${p.available > 0 ? "" : " (ناموجود)"}</option>`).join("");
    const rowHtml = `
        <div class="item-row">
            <select class="select it-product">${options}</select>
            <input class="input it-qty" inputmode="decimal" placeholder="تعداد" value="1">
            <button type="button" class="rm" title="حذف" aria-label="حذف ردیف">×</button>
        </div>`;

    const body = Modal.open("درخواست خرید جدید", `
        <p class="hint-line">کالاهای مورد نیاز خود را از فهرست کارخانه انتخاب کنید. حسابدار درخواست را بررسی و به بخش مربوط ارجاع می‌دهد.</p>
        <div class="item-rows" id="itemRows">${rowHtml}</div>
        <button type="button" class="link-add" id="addRow">＋ افزودن کالای دیگر</button>
        ${field("یادداشت (اختیاری)", '<textarea class="input" id="reqNote" maxlength="1000" placeholder="مثلاً زمان یا محل تحویل"></textarea>', true)}
        <div class="modal-actions"><button class="btn" id="sendRequest">ثبت درخواست</button></div>
        <p class="error-line" id="reqFormError" role="alert"></p>`);

    const rows = $("#itemRows", body);
    $("#addRow", body).addEventListener("click", () => {
        if (rows.children.length >= 30) return;
        rows.insertAdjacentHTML("beforeend", rowHtml);
    });
    rows.addEventListener("click", e => {
        if (e.target.closest(".rm") && rows.children.length > 1) e.target.closest(".item-row").remove();
    });

    const send = $("#sendRequest", body);
    send.addEventListener("click", () => submitForm(send, $("#reqFormError", body), async () => {
        const items = [...rows.children].map(row => ({
            product_id: Number($(".it-product", row).value),
            quantity: parseNum($(".it-qty", row).value),
        }));
        if (items.some(i => !(i.quantity > 0))) throw new Error("تعداد هر کالا باید عددی بزرگ‌تر از صفر باشد");
        try {
            await apiSend("POST", "/buyer/requests", {
                items: items.map(i => ({ product_id: i.product_id, quantity: String(i.quantity) })),
                note: $("#reqNote", body).value.trim() || null,
            });
        } catch (err) {
            // اگر هم‌زمان بدهی ثبت شده باشد، سرور همان پیام را برمی‌گرداند؛ بنر را هم به‌روز می‌کنیم
            if (err.message === DEBT_BLOCK_MESSAGE) loadBuyerSummary().catch(() => {});
            throw err;
        }
        Modal.close();
        toast("درخواست خرید ثبت شد");
        afterRequestChange();
    }));
}

$("#newRequest").addEventListener("click", openNewRequest);

registerView("home", () => (ROLE === "buyer" ? loadBuyerHome() : loadWorkHome()));
registerView("myDebts", () => { loadBuyerSummary().catch(() => {}); myDebtList.reload(); });
registerView("myRequests", () => { loadBuyerSummary().catch(() => {}); myRequestList.reload(); });
