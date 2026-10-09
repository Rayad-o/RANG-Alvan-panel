// ماژول کنترل: پرداخت‌ها، فاکتور خرید، تأمین‌کنندگان و وظایف

async function loadSuppliersOptions() {
    const list = await apiJson("/suppliers/?limit=500");
    return list.map(s => `<option value="${s.id}">${esc(s.name)} (${esc(s.code)})</option>`).join("");
}

// بعد از هر تغییر داده‌ای: نشانگرهای منو و داشبورد تازه شوند
function afterChange(...views) {
    invalidate("overview", ...views);
    refreshBadges();
}

// ---------------------------------------------------------------------------
// کنترل پرداخت
// ---------------------------------------------------------------------------
const paymentStatus = segmented("#paymentStatus", () => paymentList.reload());
$("#paymentRisk").addEventListener("change", () => paymentList.reload());

const paymentList = createList({
    endpoint: "/payments/", body: "#paymentBody", search: "#paymentSearch", more: "#paymentMore", pageSize: 50, columns: 8,
    extraParams: () => ({ status: paymentStatus(), risk: $("#paymentRisk").value }),
    row: p => `
        <tr>
            <td>${toFaDigits(esc(p.ref))}</td>
            <td>${toFaDigits(fmtDate(p.created_at, true))}</td>
            <td><b>${esc(p.party_name)}</b></td>
            <td>${esc(p.description) || "—"}</td>
            <td>${fmt(p.amount)}</td>
            <td><span class="badge ${riskClass(p.risk_score)}">${fmt(p.risk_score)}/۱۰۰</span></td>
            <td>${badge(PAY_STATUS[p.status])}</td>
            <td><button class="btn sm ghost" data-act="open" data-id="${p.id}">جزئیات</button></td>
        </tr>`,
    onAction: (act, p) => openPayment(p),
});

async function loadPayments() {
    paymentList.reload();
    const c = await refreshBadges();
    if (!c) return;
    const card = (title, value, hint, tint) =>
        `<div class="card" style="--tint:${tint}"><h3>${title}</h3><div class="value">${value}</div><div class="hint">${hint}</div></div>`;
    $("#paymentKpis").innerHTML =
        card("در انتظار تأیید", fmt(c.pending_count) + " مورد", fmtShort(c.pending_amount) + " تومان", "#f59e0b") +
        card("متوقف‌شده", fmt(c.stopped_count) + " مورد", fmtShort(c.stopped_amount) + " تومان", "#ef4444") +
        card("پرداخت‌های پرریسک", fmt(c.focus.high_risk_payments), "در انتظار تأیید مدیر سیستم", "#ec4899");
}

function openPayment(p) {
    const lvl = riskClass(p.risk_score);
    const needsLabel = p.required_role === "admin" ? "مدیر سیستم" : "مدیر";
    const canApprove = atLeast("manager") && atLeast(p.required_role) && p.status !== "approved";
    const canStop = atLeast("manager") && p.status === "pending";

    const body = Modal.open(`جزئیات پرداخت ${toFaDigits(p.ref)}`, `
        <div class="detail-grid">
            <div class="detail"><small>طرف‌حساب</small><b>${esc(p.party_name)}</b></div>
            <div class="detail"><small>مبلغ</small><b>${fmt(p.amount)} تومان</b></div>
            <div class="detail"><small>شرح</small><b>${esc(p.description) || "—"}</b></div>
            <div class="detail"><small>سفارش خرید</small><b>${esc(p.po_ref) || "—"}</b></div>
            <div class="detail"><small>ثبت‌کننده</small><b>${esc(p.created_by) || "—"}</b></div>
            <div class="detail"><small>تاریخ ثبت</small><b>${toFaDigits(fmtDate(p.created_at, true))}</b></div>
        </div>
        <div class="risk-box">
            <div class="risk-line"><b>امتیاز ریسک</b><span class="badge ${lvl}">${fmt(p.risk_score)}/۱۰۰</span></div>
            <div class="progress"><i style="width:${p.risk_score}%;background:${RISK_VAR[lvl]}"></i></div>
            ${p.risk_reasons.length
                ? `<ul class="reasons">${p.risk_reasons.map(r => `<li>${toFaDigits(esc(r))}</li>`).join("")}</ul>`
                : '<div class="risk-reason">نشانهٔ ریسکی شناسایی نشد.</div>'}
            <div class="risk-reason">این امتیاز فقط ناهنجاری را نشان می‌دهد؛ تصمیم نهایی با شماست.</div>
        </div>
        <div class="detail-grid">
            <div class="detail"><small>وضعیت</small><b>${badge(PAY_STATUS[p.status])}</b></div>
            <div class="detail"><small>تأییدکنندهٔ لازم</small><b>${needsLabel} یا بالاتر</b></div>
            ${p.decided_by ? `<div class="detail"><small>تصمیم توسط</small><b>${esc(p.decided_by)} — ${toFaDigits(fmtDate(p.decided_at, true))}</b></div>` : ""}
            ${p.decision_note ? `<div class="detail"><small>یادداشت</small><b>${esc(p.decision_note)}</b></div>` : ""}
        </div>
        ${canApprove || canStop ? `
            <label class="fld full"><span>یادداشت تصمیم (اختیاری)</span><input class="input" id="payNote" maxlength="1000"></label>
            <div class="modal-actions">
                ${canApprove ? '<button class="btn" id="payApprove">تأیید پرداخت</button>' : ""}
                ${canStop ? '<button class="btn danger" id="payStop">رد / توقف</button>' : ""}
            </div>` : (p.status !== "approved" && atLeast("manager")
                ? `<p class="hint-line">تأیید این پرداخت نیازمند نقش ${needsLabel} است.</p>` : "")}
        <p class="error-line" id="payError"></p>`);

    const act = (path, message) => async () => {
        await apiSend("POST", `/payments/${p.id}/${path}`, { note: $("#payNote").value.trim() || null });
        Modal.close();
        toast(message);
        afterChange("payments");
        loadPayments();
    };
    const approve = $("#payApprove", body), stop = $("#payStop", body), err = $("#payError", body);
    if (approve) approve.addEventListener("click", () => submitForm(approve, err, act("approve", "پرداخت تأیید شد")));
    if (stop) stop.addEventListener("click", () => submitForm(stop, err, act("stop", "پرداخت متوقف شد")));
}

$("#newPayment").addEventListener("click", async () => {
    let options;
    try { options = await loadSuppliersOptions(); } catch (e) { toast(e.message, true); return; }
    if (!options) { toast("ابتدا یک تأمین‌کننده ثبت کنید", true); return; }

    const body = Modal.open("ثبت درخواست پرداخت", `
        <div class="form-grid">
            ${field("تأمین‌کننده", `<select class="select" id="npSupplier">${options}</select>`)}
            ${field("مبلغ (تومان)", '<input class="input" id="npAmount" inputmode="numeric" placeholder="مثلاً ۸۷۰٬۰۰۰٬۰۰۰">')}
            ${field("شرح", '<input class="input" id="npDesc" maxlength="500" placeholder="خرید مواد اولیه">')}
            ${field("مرجع سفارش (اختیاری)", '<input class="input" id="npPo" maxlength="50" placeholder="PO-5721" dir="ltr">')}
        </div>
        <div class="modal-actions"><button class="btn" id="npSubmit">ثبت و محاسبهٔ ریسک</button></div>
        <p class="error-line" id="npError"></p>`);
    const submit = $("#npSubmit", body);
    submit.addEventListener("click", () => submitForm(submit, $("#npError", body), async () => {
        const amount = parseNum($("#npAmount", body).value);
        if (!(amount > 0)) throw new Error("مبلغ معتبر وارد کنید");
        const created = await apiSend("POST", "/payments/", {
            supplier_id: Number($("#npSupplier", body).value),
            amount: String(amount),
            description: $("#npDesc", body).value.trim() || null,
            po_ref: $("#npPo", body).value.trim() || null,
        });
        afterChange("payments");
        loadPayments();
        openPayment(created);  // بلافاصله امتیاز و دلایل ریسک را نشان بده
    }));
});

// ---------------------------------------------------------------------------
// فاکتور خرید (تطبیق سه‌طرفه)
// ---------------------------------------------------------------------------
const invoiceStatus = segmented("#invoiceStatus", () => invoiceList.reload());
const qty = (v, unit) => `${fmt(v)} ${esc(unit)}`;

const invoiceList = createList({
    endpoint: "/purchase-invoices/", body: "#invoiceBody", search: "#invoiceSearch", more: "#invoiceMore", pageSize: 50, columns: 9,
    extraParams: () => ({ status: invoiceStatus() }),
    row: i => `
        <tr>
            <td>${toFaDigits(esc(i.number))}</td>
            <td>${esc(i.supplier_name)}</td>
            <td>${esc(i.po_number) || "—"}</td>
            <td>${i.ordered_qty === null ? "—" : qty(i.ordered_qty, i.unit)}</td>
            <td>${qty(i.received_qty, i.unit)}</td>
            <td>${qty(i.invoiced_qty, i.unit)}</td>
            <td>${fmt(i.amount)}</td>
            <td>${badge(INV_STATUS[i.status])}</td>
            <td><button class="btn sm ghost" data-act="open" data-id="${i.id}">جزئیات تطبیق</button></td>
        </tr>`,
    onAction: (act, i) => openInvoice(i),
});

function openInvoice(i) {
    const diff = Number(i.invoiced_qty) - Number(i.received_qty);
    const bad = i.status === "mismatch", review = i.status === "review";
    const canResolve = atLeast("manager") && (bad || review);

    const body = Modal.open(`تطبیق فاکتور ${toFaDigits(i.number)}`, `
        <div class="detail-grid">
            <div class="detail"><small>تأمین‌کننده</small><b>${esc(i.supplier_name)}</b></div>
            <div class="detail"><small>سفارش خرید</small><b>${esc(i.po_number) || "—"}</b></div>
            <div class="detail"><small>سفارش‌شده</small><b>${i.ordered_qty === null ? "—" : qty(i.ordered_qty, i.unit)}</b></div>
            <div class="detail"><small>رسید انبار</small><b>${qty(i.received_qty, i.unit)}</b></div>
            <div class="detail"><small>فاکتور</small><b>${qty(i.invoiced_qty, i.unit)}</b></div>
            <div class="detail"><small>مبلغ</small><b>${fmt(i.amount)} تومان</b></div>
        </div>
        <div class="callout ${bad ? "red" : review ? "orange" : "green"}">
            <b>${bad ? "هشدار کنترل:" : review ? "نیازمند بررسی:" : i.status === "resolved" ? "رفع‌شده:" : "کنترل موفق:"}</b>
            ${diff === 0 ? "مقدار رسید انبار و فاکتور برابر است."
                : `فاکتور ${fmt(Math.abs(diff))} ${esc(i.unit)} ${diff > 0 ? "بیشتر" : "کمتر"} از رسید انبار است.`}
            ${i.note ? `<br>یادداشت: ${esc(i.note)}` : ""}
        </div>
        ${canResolve ? `
            <label class="fld full"><span>توضیح رفع مغایرت</span><input class="input" id="invNote" maxlength="1000"></label>
            <div class="modal-actions"><button class="btn" id="invResolve">ثبت به‌عنوان رفع‌شده</button></div>` : ""}
        <p class="error-line" id="invError"></p>`);

    const btn = $("#invResolve", body);
    if (btn) btn.addEventListener("click", () => submitForm(btn, $("#invError", body), async () => {
        await apiSend("POST", `/purchase-invoices/${i.id}/resolve`, { note: $("#invNote", body).value.trim() || null });
        Modal.close();
        toast("مغایرت رفع‌شده ثبت شد");
        afterChange("purchase");
        invoiceList.reload();
    }));
}

$("#newInvoice").addEventListener("click", async () => {
    let options;
    try { options = await loadSuppliersOptions(); } catch (e) { toast(e.message, true); return; }
    if (!options) { toast("ابتدا یک تأمین‌کننده ثبت کنید", true); return; }

    const body = Modal.open("ثبت فاکتور خرید", `
        <div class="form-grid">
            ${field("شمارهٔ فاکتور", '<input class="input" id="niNumber" maxlength="50" dir="ltr">')}
            ${field("تأمین‌کننده", `<select class="select" id="niSupplier">${options}</select>`)}
            ${field("شمارهٔ سفارش", '<input class="input" id="niPo" maxlength="50" dir="ltr" placeholder="PO-5730">')}
            ${field("واحد", '<input class="input" id="niUnit" value="kg" maxlength="20" dir="ltr">')}
            ${field("مقدار سفارش‌شده", '<input class="input" id="niOrdered" inputmode="decimal">')}
            ${field("مقدار رسیدشده (انبار)", '<input class="input" id="niReceived" inputmode="decimal">')}
            ${field("مقدار فاکتورشده", '<input class="input" id="niInvoiced" inputmode="decimal">')}
            ${field("مبلغ (تومان)", '<input class="input" id="niAmount" inputmode="numeric">')}
        </div>
        <div class="modal-actions"><button class="btn" id="niSubmit">ثبت و تطبیق</button></div>
        <p class="error-line" id="niError"></p>`);
    const submit = $("#niSubmit", body);
    submit.addEventListener("click", () => submitForm(submit, $("#niError", body), async () => {
        const num = id => parseNum($(id, body).value);
        const number = $("#niNumber", body).value.trim();
        if (!number) throw new Error("شمارهٔ فاکتور را وارد کنید");
        const received = num("#niReceived"), invoiced = num("#niInvoiced"), amount = num("#niAmount");
        if ([received, invoiced].some(v => !(v >= 0))) throw new Error("مقدار رسیدشده و فاکتورشده را درست وارد کنید");
        if (!(amount > 0)) throw new Error("مبلغ معتبر وارد کنید");
        const ordered = $("#niOrdered", body).value.trim() ? num("#niOrdered") : null;
        if (ordered !== null && !(ordered >= 0)) throw new Error("مقدار سفارش‌شده معتبر نیست");

        const created = await apiSend("POST", "/purchase-invoices/", {
            number,
            supplier_id: Number($("#niSupplier", body).value),
            po_number: $("#niPo", body).value.trim() || null,
            ordered_qty: ordered === null ? null : String(ordered),
            received_qty: String(received),
            invoiced_qty: String(invoiced),
            unit: $("#niUnit", body).value.trim() || "kg",
            amount: String(amount),
        });
        afterChange("purchase");
        invoiceList.reload();
        openInvoice(created);
    }));
});

// ---------------------------------------------------------------------------
// تأمین‌کنندگان
// ---------------------------------------------------------------------------
const supplierRisk = segmented("#supplierRisk", () => supplierList.reload());

const supplierList = createList({
    endpoint: "/suppliers/", body: "#supplierBody", search: "#supplierSearch", pageSize: 200, columns: 7,
    extraParams: () => ({ risk: supplierRisk() }),
    row: s => `
        <tr>
            <td><b>${esc(s.name)}</b></td>
            <td>${esc(s.code)}</td>
            <td>${esc(s.category) || "—"}</td>
            <td dir="ltr" class="ltr-cell">${esc(s.bank_account) || "—"}${!s.bank_verified ? ' <span class="badge orange">تأییدنشده</span>' : ""}</td>
            <td>${s.is_high_risk ? badge(["", "red"], "پرریسک") : badge(["", "green"], "عادی")}</td>
            <td>${s.bank_changed_at ? toFaDigits(fmtDate(s.bank_changed_at, true)) : "—"}</td>
            <td><button class="btn sm ghost" data-act="open" data-id="${s.id}">پرونده</button></td>
        </tr>`,
    onAction: (act, s) => openSupplier(s),
});

async function openSupplier(s) {
    const manager = atLeast("manager");
    const body = Modal.open(`پروندهٔ ${s.name}`, `
        <div class="form-grid">
            ${field("نام", `<input class="input" id="spName" value="${esc(s.name)}" maxlength="255">`)}
            ${field("دسته", `<input class="input" id="spCat" value="${esc(s.category || "")}" maxlength="100">`)}
            ${field("حساب بانکی (تغییر آن نیازمند تأیید مدیر است)", `<input class="input" id="spBank" value="${esc(s.bank_account || "")}" maxlength="60" dir="ltr">`, true)}
        </div>
        ${manager ? `<label class="check"><input type="checkbox" id="spRisk" ${s.is_high_risk ? "checked" : ""}> علامت‌گذاری به‌عنوان تأمین‌کنندهٔ پرریسک</label>` : ""}
        ${!s.bank_verified ? `<div class="callout orange"><b>حساب بانکی تأییدنشده:</b> تغییر توسط ${esc(s.bank_changed_by || "نامشخص")} — ${toFaDigits(fmtDate(s.bank_changed_at, true))}
            ${manager ? '<br><button class="btn sm" id="spVerify" style="margin-top:8px">تأیید اطلاعات بانکی</button>' : ""}</div>` : ""}
        <div class="modal-actions"><button class="btn" id="spSave">ذخیره</button></div>
        <p class="error-line" id="spError"></p>
        <h4 class="mini-title">آخرین پرداخت‌ها</h4>
        <div id="spPayments" class="mini-list">در حال بارگذاری...</div>`);

    const err = $("#spError", body);
    const save = $("#spSave", body);
    save.addEventListener("click", () => submitForm(save, err, async () => {
        const payload = { name: $("#spName", body).value.trim(), category: $("#spCat", body).value.trim() || null };
        if (!payload.name) throw new Error("نام تأمین‌کننده را وارد کنید");
        const bank = $("#spBank", body).value.trim();
        if (bank !== (s.bank_account || "")) payload.bank_account = bank;
        if ($("#spRisk", body) && $("#spRisk", body).checked !== s.is_high_risk) payload.is_high_risk = $("#spRisk", body).checked;
        await apiSend("PATCH", `/suppliers/${s.id}`, payload);
        Modal.close();
        toast(payload.bank_account !== undefined ? "ذخیره شد؛ حساب بانکی جدید تا تأیید مدیر پرریسک است" : "ذخیره شد");
        afterChange("suppliers");
        supplierList.reload();
    }));

    const verify = $("#spVerify", body);
    if (verify) verify.addEventListener("click", () => submitForm(verify, err, async () => {
        await apiSend("POST", `/suppliers/${s.id}/verify-bank`);
        Modal.close();
        toast("اطلاعات بانکی تأیید شد");
        afterChange("suppliers");
        supplierList.reload();
    }));

    try {
        const pays = await apiJson(`/payments/?supplier_id=${s.id}&limit=5`);
        $("#spPayments", body).innerHTML = pays.length
            ? pays.map(p => `<div class="mini-row"><span>${toFaDigits(esc(p.ref))} • ${toFaDigits(fmtDate(p.created_at))}</span><span>${fmt(p.amount)}</span>${badge(PAY_STATUS[p.status])}</div>`).join("")
            : "پرداختی ثبت نشده است.";
    } catch (e) {
        $("#spPayments", body).textContent = e.message;
    }
}

$("#newSupplier").addEventListener("click", () => {
    const body = Modal.open("تأمین‌کنندهٔ جدید", `
        <div class="form-grid">
            ${field("نام شرکت", '<input class="input" id="nsName" maxlength="255">')}
            ${field("کد (اختیاری)", '<input class="input" id="nsCode" maxlength="30" dir="ltr" placeholder="خودکار">')}
            ${field("دسته", '<input class="input" id="nsCat" maxlength="100" placeholder="مواد اولیه">')}
            ${field("شمارهٔ حساب", '<input class="input" id="nsBank" maxlength="60" dir="ltr" placeholder="IR...">')}
        </div>
        <div class="modal-actions"><button class="btn" id="nsSubmit">ثبت تأمین‌کننده</button></div>
        <p class="error-line" id="nsError"></p>`);
    const submit = $("#nsSubmit", body);
    submit.addEventListener("click", () => submitForm(submit, $("#nsError", body), async () => {
        const name = $("#nsName", body).value.trim();
        if (!name) throw new Error("نام شرکت را وارد کنید");
        await apiSend("POST", "/suppliers/", {
            name,
            code: $("#nsCode", body).value.trim() || null,
            category: $("#nsCat", body).value.trim() || null,
            bank_account: $("#nsBank", body).value.trim() || null,
        });
        Modal.close();
        toast("تأمین‌کننده ثبت شد");
        afterChange("suppliers");
        supplierList.reload();
    }));
});

// ---------------------------------------------------------------------------
// کنترل عملکرد (وظایف)
// ---------------------------------------------------------------------------
const taskStatus = segmented("#taskStatus", () => taskList.reload());

const taskList = createList({
    endpoint: "/tasks/", body: "#taskBody", search: "#taskSearch", more: "#taskMore", pageSize: 50, columns: 7,
    extraParams: () => ({ status: taskStatus() }),
    row: t => `
        <tr>
            <td>${esc(t.unit)}</td>
            <td><b>${esc(t.title)}</b></td>
            <td>${esc(t.owner)}</td>
            <td>${toFaDigits(fmtDate(t.due_at, true))}${t.status !== "done" ? `<small class="rel">${relDue(t.due_at)}</small>` : ""}</td>
            <td>${badge(TASK_STATUS[t.status])}</td>
            <td>${badge(PRIORITY[t.priority] || PRIORITY.medium)}</td>
            <td>${t.status !== "done" ? `<button class="btn sm success" data-act="complete" data-id="${t.id}">تکمیل شد</button>` : '<span class="done-mark">✓ ثبت شد</span>'}</td>
        </tr>`,
    onAction: async (act, t, btn) => {
        btn.disabled = true;
        try {
            await apiSend("POST", `/tasks/${t.id}/complete`);
            toast("وظیفه تکمیل شد");
            afterChange("tasks");
            taskList.reload();
        } catch (e) {
            btn.disabled = false;
            toast(e.message, true);
        }
    },
});

$("#newTask").addEventListener("click", () => {
    const tomorrow = new Date(Date.now() + 864e5);
    tomorrow.setHours(17, 0, 0, 0);
    const local = new Date(tomorrow - tomorrow.getTimezoneOffset() * 6e4).toISOString().slice(0, 16);

    const body = Modal.open("ایجاد وظیفه", `
        <div class="form-grid">
            ${field("واحد", '<input class="input" id="ntUnit" maxlength="100" placeholder="حسابداری">')}
            ${field("مسئول", '<input class="input" id="ntOwner" maxlength="100">')}
            ${field("شرح وظیفه", '<input class="input" id="ntTitle" maxlength="500" placeholder="مثلاً بررسی فاکتورهای معوق">', true)}
            ${field("اولویت", '<select class="select" id="ntPriority"><option value="medium">متوسط</option><option value="high">بالا</option><option value="critical">بحرانی</option><option value="low">پایین</option></select>')}
            ${field("سررسید", `<input class="input" id="ntDue" type="datetime-local" value="${local}" dir="ltr">`)}
        </div>
        <div class="modal-actions"><button class="btn" id="ntSubmit">ایجاد وظیفه</button></div>
        <p class="error-line" id="ntError"></p>`);
    const submit = $("#ntSubmit", body);
    submit.addEventListener("click", () => submitForm(submit, $("#ntError", body), async () => {
        const unit = $("#ntUnit", body).value.trim(), owner = $("#ntOwner", body).value.trim(), title = $("#ntTitle", body).value.trim();
        if (!unit || !owner || !title) throw new Error("واحد، مسئول و شرح وظیفه را وارد کنید");
        const due = new Date($("#ntDue", body).value);
        if (isNaN(due)) throw new Error("سررسید معتبر وارد کنید");
        await apiSend("POST", "/tasks/", { unit, owner, title, priority: $("#ntPriority", body).value, due_at: due.toISOString() });
        Modal.close();
        toast("وظیفه ایجاد شد");
        afterChange("tasks");
        taskList.reload();
    }));
});

registerView("payments", loadPayments);
registerView("purchase", () => invoiceList.reload());
registerView("suppliers", () => supplierList.reload());
registerView("tasks", () => taskList.reload());
