// پنل کارگران: حسابدار (بدهی‌ها و ارجاع)، رییس بخش (واگذاری)، کارکن بخش (انجام کار)؛ مدیر سیستم همهٔ این‌ها را دارد
const canEditDebts = ROLE === "accountant" || ROLE === "admin";

const ICONS = {
    inbox: '<path d="M4 13l2-8h12l2 8"/><path d="M4 13v6h16v-6h-5l-1 2h-4l-1-2z"/>',
    flow: '<path d="M4 6h6v6H4zM14 12h6v6h-6z"/><path d="M10 9h2a2 2 0 012 2v1"/>',
    wallet: '<rect x="3" y="6" width="18" height="13" rx="2.5"/><path d="M3 10h18M16 14.5h2"/>',
    alert: '<path d="M12 3l9 16H3L12 3z"/><path d="M12 10v4M12 17v.5"/>',
    check: '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l2.7 2.7L16 9.5"/>',
    play: '<circle cx="12" cy="12" r="9"/><path d="M10 8.5l5 3.5-5 3.5z"/>',
};
const kpi = (title, value, hint, tint, icon) => `
    <div class="card" data-tilt style="--tint:${tint}">
        <div class="icon"><svg viewBox="0 0 24 24">${ICONS[icon]}</svg></div>
        <h3>${title}</h3><div class="value">${value}</div><div class="hint">${hint}</div>
    </div>`;

const workItem = r => `
    <button class="work-item" data-open-request="${r.id}">
        <span><b>${toFaDigits(esc(r.ref))} — ${esc(r.buyer_name)}</b><small>${itemsSummary(r.items)}</small></span>
        ${statusBadge(r.status)}
    </button>`;

async function requestsFor(status, limit = 6) {
    const list = await apiJson(`/requests/?status=${status}&limit=${limit}`);
    cacheRequests(list);
    return list;
}

// ---------------------------------------------------------------------------
// داشبورد کارگران
// ---------------------------------------------------------------------------
async function loadWorkHome() {
    const body = $("#homeBody");
    $("#homeTitle").textContent = `سلام، ${user.full_name}`;
    $("#homeSub").textContent = ({
        accountant: "درخواست‌های جدید و بدهی خریداران",
        admin: "نمای کلی درخواست‌های خرید و بدهی خریداران",
        manager: "نمای کلی درخواست‌های خرید و بدهی خریداران",
        dept_head: `رییس بخش ${user.department || ""}`,
        dept_staff: `کارکن بخش ${user.department || ""}`,
    })[ROLE] || "";

    let sum;
    try { sum = await apiJson("/requests/summary"); } catch (err) {
        body.innerHTML = `<div class="notice bad"><span class="ico">!</span><div>${esc(err.message)}</div></div>`;
        return;
    }
    const c = sum.counts;

    if (isAccounting) {
        let waiting = [], buyers = [];
        try { [waiting, buyers] = await Promise.all([requestsFor("submitted"), apiJson("/accounting/buyers")]); } catch (e) { toast(e.message, true); }
        const top = buyers.filter(b => Number(b.total_debt) > 0).sort((a, b) => b.total_debt - a.total_debt).slice(0, 5);
        body.innerHTML = `
            <div class="cards">
                ${kpi("درخواست‌های جدید", fmt(c.submitted), "منتظر ارجاع به بخش", "#f59e0b", "inbox")}
                ${kpi("در جریان بخش‌ها", fmt(c.forwarded + c.assigned + c.in_progress), "ارجاع‌شده تا در حال انجام", "#5b5bf0", "flow")}
                ${kpi("بدهی باز خریداران", fmtShort(sum.open_debt_total), "تومان", "#ec4899", "wallet")}
                ${kpi("خریداران بالای سقف", fmt(sum.buyers_over_limit), `بدهی بیش از ${fmtShort(sum.debt_limit)} تومان`, "#ef4444", "alert")}
            </div>
            <div class="grid-2">
                <div class="panel">
                    <div class="panel-head"><h2>منتظر ارجاع</h2><a class="sub" href="#/requests">همه</a></div>
                    <p class="sub">درخواست‌های جدید خریداران</p>
                    ${waiting.length ? waiting.map(workItem).join("") : '<div class="empty">درخواست جدیدی نیست 🎉</div>'}
                </div>
                <div class="panel">
                    <div class="panel-head"><h2>بیشترین بدهی</h2><a class="sub" href="#/buyers">همه</a></div>
                    <p class="sub">خریدارانی که بدهی باز دارند</p>
                    ${top.length ? `<div class="pill-list">${top.map(b => `
                        <div class="person"><span>${esc(b.full_name)}<small>${b.blocked ? "ثبت درخواست ممنوع" : "مجاز"}</small></span>
                        <b style="color:${b.blocked ? "var(--danger)" : "inherit"}">${fmtShort(b.total_debt)}</b></div>`).join("")}</div>`
                        : '<div class="empty">بدهی بازی ثبت نشده است</div>'}
                </div>
            </div>`;
    } else if (ROLE === "dept_head") {
        let waiting = [], staff = [];
        try { [waiting, staff] = await Promise.all([requestsFor("forwarded"), apiJson("/requests/staff")]); } catch (e) { toast(e.message, true); }
        body.innerHTML = `
            <div class="cards">
                ${kpi("منتظر واگذاری", fmt(c.forwarded), "به کارکنان بخش واگذار کنید", "#f59e0b", "inbox")}
                ${kpi("در جریان", fmt(c.assigned + c.in_progress), "واگذارشده و در حال انجام", "#5b5bf0", "play")}
                ${kpi("انجام‌شده", fmt(c.done), "تکمیل‌شده توسط بخش", "#14b8a6", "check")}
            </div>
            <div class="grid-2">
                <div class="panel">
                    <div class="panel-head"><h2>منتظر واگذاری</h2><a class="sub" href="#/requests">همه</a></div>
                    <p class="sub">درخواست‌هایی که حسابدار به بخش شما ارجاع داده است</p>
                    ${waiting.length ? waiting.map(workItem).join("") : '<div class="empty">درخواستی منتظر واگذاری نیست 🎉</div>'}
                </div>
                <div class="panel">
                    <h2>کارکنان بخش</h2><p class="sub">تعداد کارهای در جریان هر نفر</p>
                    ${staff.length ? `<div class="pill-list">${staff.map(s => `
                        <div class="person"><span>${esc(s.full_name)}<small>${esc(s.email)}</small></span><b>${fmt(s.active_requests)} کار</b></div>`).join("")}</div>`
                        : '<div class="empty">کارکنی برای بخش ثبت نشده است</div>'}
                </div>
            </div>`;
    } else {
        let mine = [];
        try { mine = [...await requestsFor("assigned", 10), ...await requestsFor("in_progress", 10)]; } catch (e) { toast(e.message, true); }
        body.innerHTML = `
            <div class="cards">
                ${kpi("کار جدید", fmt(c.assigned), "منتظر شروع", "#f59e0b", "inbox")}
                ${kpi("در حال انجام", fmt(c.in_progress), "کارهای در دست شما", "#5b5bf0", "play")}
                ${kpi("انجام‌شده", fmt(c.done), "تکمیل‌شده توسط شما", "#14b8a6", "check")}
            </div>
            <div class="panel">
                <div class="panel-head"><h2>کارهای من</h2><a class="sub" href="#/requests">همه</a></div>
                <p class="sub">برای شروع یا تکمیل، روی کار بزنید</p>
                ${mine.length ? mine.map(workItem).join("") : '<div class="empty">فعلاً کاری به شما واگذار نشده است 🎉</div>'}
            </div>`;
    }
    enableTilt();
}

// ---------------------------------------------------------------------------
// فهرست درخواست‌ها
// ---------------------------------------------------------------------------
const STATUS_OPTIONS = {
    acct: [["", "همهٔ وضعیت‌ها"], ["submitted", "ثبت‌شده (منتظر ارجاع)"], ["forwarded", "ارجاع‌شده"], ["assigned", "واگذار شده"],
        ["in_progress", "در حال انجام"], ["done", "انجام‌شده"], ["rejected", "رد شده"], ["cancelled", "لغو شده"]],
    head: [["", "همهٔ وضعیت‌ها"], ["forwarded", "منتظر واگذاری"], ["assigned", "واگذار شده"], ["in_progress", "در حال انجام"], ["done", "انجام‌شده"]],
    staff: [["", "همهٔ کارها"], ["assigned", "جدید"], ["in_progress", "در حال انجام"], ["done", "انجام‌شده"]],
};
const statusKind = isAccounting ? "acct" : ROLE === "dept_head" ? "head" : "staff";
const defaultStatus = { acct: "submitted", head: "forwarded", staff: "" }[statusKind];

$("#reqStatus").innerHTML = STATUS_OPTIONS[statusKind].map(([v, l]) => `<option value="${v}">${l}</option>`).join("");
$("#reqStatus").value = defaultStatus;
$("#reqStatus").addEventListener("change", () => requestList.reload());
$("#reqDept").addEventListener("change", () => requestList.reload());

const requestList = createList({
    endpoint: "/requests/", body: "#reqBody", search: "#reqSearch", more: "#reqMore", pageSize: 50, columns: 8,
    extraParams: () => ({ status: $("#reqStatus").value, department: $("#reqDept").hidden ? "" : $("#reqDept").value }),
    row: r => {
        cacheRequests([r]);
        const debt = r.buyer_debt !== null && r.buyer_debt !== undefined && Number(r.buyer_debt) > 0
            ? `<small class="rel">بدهی: ${fmtShort(r.buyer_debt)} تومان</small>` : "";
        return `
        <tr>
            <td>${toFaDigits(esc(r.ref))}</td>
            <td>${toFaDigits(fmtDate(r.created_at, true))}</td>
            <td><b>${esc(r.buyer_name)}</b>${debt}</td>
            <td style="white-space:normal;min-width:200px">${itemsSummary(r.items)}</td>
            <td>${esc(r.department) || "—"}</td>
            <td>${esc(r.assigned_to_name) || "—"}</td>
            <td>${statusBadge(r.status)}</td>
            <td><button class="btn sm ghost" data-act="open" data-id="${r.id}">جزئیات</button></td>
        </tr>`;
    },
    onAction: (act, r) => openRequest(r),
});

async function loadRequests() {
    $("#requestsTitle").textContent = ROLE === "dept_staff" ? "کارهای من" : ROLE === "dept_head" ? `درخواست‌های بخش ${user.department || ""}` : "درخواست‌های خرید";
    $("#requestsSub").textContent = {
        dept_staff: "درخواست‌هایی که به شما واگذار شده است",
        dept_head: "درخواست‌های ارجاع‌شده را به کارکنان بخش واگذار کنید",
    }[ROLE] || "درخواست‌ها را بررسی کنید و به بخش مربوط ارجاع دهید";

    const dept = $("#reqDept");
    if (isAccounting && dept.hidden) {
        dept.hidden = false;
        try {
            const list = await apiJson("/departments/");
            dept.innerHTML = '<option value="">همهٔ بخش‌ها</option>' + list.map(d => `<option>${esc(d.name)}</option>`).join("");
        } catch (e) { dept.hidden = true; }
    }
    requestList.reload();
}

// ---------------------------------------------------------------------------
// بدهی‌ها (حسابدار)
// ---------------------------------------------------------------------------
let debtBuyer = null;  // فیلتر روی یک خریدار
const debtStatus = segmented("#debtStatus", () => debtList.reload());

const debtList = createList({
    endpoint: "/accounting/debts", body: "#debtBody", search: "#debtSearch", more: "#debtMore", pageSize: 50, columns: 9,
    extraParams: () => ({ status: debtStatus(), buyer_id: debtBuyer ? debtBuyer.id : "" }),
    row: d => {
        const open = d.status === "open";
        const statusHtml = d.status === "paid" ? badge(["", "green"], "پرداخت‌شده")
            : d.status === "voided" ? badge(["", "gray"], "ابطال‌شده") : badge(["", "orange"], "باز");
        const actions = open && canEditDebts
            ? `<button class="btn sm success" data-act="pay" data-id="${d.id}">ثبت پرداخت</button>
               <button class="btn sm ghost" data-act="void" data-id="${d.id}">ابطال</button>` : "";
        return `
        <tr>
            <td><b>${esc(d.buyer_name)}</b></td>
            <td style="white-space:normal;min-width:160px">${esc(d.description) || "—"}</td>
            <td>${toFaDigits(fmtDate(d.created_at))}</td>
            <td>${d.due_date ? toFaDigits(fmtDate(d.due_date)) : "—"}</td>
            <td>${fmt(d.amount)}</td>
            <td>${fmt(d.paid_amount)}</td>
            <td><b>${open ? fmt(d.remaining) : "—"}</b></td>
            <td>${statusHtml}</td>
            <td style="white-space:nowrap">${actions}</td>
        </tr>`;
    },
    onAction: (act, d) => (act === "pay" ? openPayDebt(d) : openVoidDebt(d)),
});

function updateDebtChip() {
    const chip = $("#debtChip");
    chip.hidden = !debtBuyer;
    if (debtBuyer) {
        chip.innerHTML = `${esc(debtBuyer.name)} <button type="button" class="chip-x" aria-label="حذف فیلتر">×</button>`;
        $(".chip-x", chip).addEventListener("click", () => { debtBuyer = null; updateDebtChip(); debtList.reload(); });
    }
}

function openNewDebt(buyerId) {
    $("#newDebt").disabled = true;
    apiJson("/accounting/buyers").then(buyers => {
        if (!buyers.length) { toast("هنوز خریداری ثبت نشده است؛ مدیر سیستم باید خریدار بسازد", true); return; }
        const body = Modal.open("ثبت بدهی برای خریدار", `
            <div class="form-grid">
                ${field("خریدار", `<select class="select" id="ndBuyer">${buyers.map(b =>
                    `<option value="${b.id}" ${b.id === buyerId ? "selected" : ""}>${esc(b.full_name)} — بدهی فعلی ${fmtShort(b.total_debt)}</option>`).join("")}</select>`, true)}
                ${field("مبلغ (تومان)", '<input class="input" id="ndAmount" inputmode="numeric" placeholder="مثلاً ۵٬۰۰۰٬۰۰۰">')}
                ${field("سررسید (اختیاری)", '<input class="input" id="ndDue" type="date" dir="ltr">')}
                ${field("شرح", '<input class="input" id="ndDesc" maxlength="500" placeholder="مثلاً فاکتور ۱۰۳۵ — رنگ پلاستیک">', true)}
            </div>
            <div class="modal-actions"><button class="btn" id="ndSave">ثبت بدهی</button></div>
            <p class="error-line" id="ndError"></p>`);
        const save = $("#ndSave", body);
        save.addEventListener("click", () => submitForm(save, $("#ndError", body), async () => {
            const amount = parseNum($("#ndAmount", body).value);
            if (!(amount > 0)) throw new Error("مبلغ معتبر وارد کنید");
            await apiSend("POST", "/accounting/debts", {
                buyer_id: Number($("#ndBuyer", body).value),
                amount: String(amount),
                description: $("#ndDesc", body).value.trim() || null,
                due_date: $("#ndDue", body).value || null,
            });
            Modal.close();
            toast("بدهی ثبت شد");
            afterRequestChange();
        }));
    }).catch(e => toast(e.message, true)).finally(() => { $("#newDebt").disabled = false; });
}

function openPayDebt(d) {
    const body = Modal.open("ثبت پرداخت بدهی", `
        <div class="detail-grid">
            <div class="detail"><small>خریدار</small><b>${esc(d.buyer_name)}</b></div>
            <div class="detail"><small>مانده بدهی</small><b>${toman(d.remaining)}</b></div>
        </div>
        <div class="form-grid">
            ${field("مبلغ پرداختی (تومان)", `<input class="input" id="pdAmount" inputmode="numeric" value="${fmt(d.remaining)}">`)}
            ${field("توضیح (اختیاری)", '<input class="input" id="pdNote" maxlength="500" placeholder="مثلاً واریز بانکی">')}
        </div>
        <div class="modal-actions"><button class="btn success" id="pdSave">ثبت پرداخت</button></div>
        <p class="error-line" id="pdError"></p>`);
    const save = $("#pdSave", body);
    save.addEventListener("click", () => submitForm(save, $("#pdError", body), async () => {
        const amount = parseNum($("#pdAmount", body).value);
        if (!(amount > 0)) throw new Error("مبلغ معتبر وارد کنید");
        await apiSend("POST", `/accounting/debts/${d.id}/pay`, { amount: String(amount), note: $("#pdNote", body).value.trim() || null });
        Modal.close();
        toast("پرداخت ثبت شد");
        afterRequestChange();
    }));
}

function openVoidDebt(d) {
    const body = Modal.open("ابطال بدهی", `
        <div class="callout orange">بدهی «${esc(d.description) || "بدون شرح"}» به مبلغ ${toman(d.remaining)} برای ${esc(d.buyer_name)} ابطال می‌شود و از مجموع بدهی او کم می‌شود.</div>
        ${field("دلیل ابطال", '<input class="input" id="vdNote" maxlength="500" placeholder="مثلاً ثبت اشتباه">', true)}
        <div class="modal-actions"><button class="btn danger" id="vdSave">ابطال بدهی</button></div>
        <p class="error-line" id="vdError"></p>`);
    const save = $("#vdSave", body);
    save.addEventListener("click", () => submitForm(save, $("#vdError", body), async () => {
        const note = $("#vdNote", body).value.trim();
        if (note.length < 3) throw new Error("دلیل ابطال را بنویسید");
        await apiSend("POST", `/accounting/debts/${d.id}/void`, { note });
        Modal.close();
        toast("بدهی ابطال شد");
        afterRequestChange();
    }));
}

$("#newDebt").hidden = !canEditDebts;
$("#newDebt").addEventListener("click", () => openNewDebt());

// ---------------------------------------------------------------------------
// خریداران
// ---------------------------------------------------------------------------
const buyerList = createList({
    endpoint: "/accounting/buyers", body: "#buyerBody", search: "#buyerSearch", pageSize: 500, columns: 6,
    row: b => `
        <tr>
            <td><b>${esc(b.full_name)}</b>${b.is_active ? "" : ' <small class="rel">(غیرفعال)</small>'}</td>
            <td dir="ltr" class="ltr-cell">${esc(b.email)}</td>
            <td><b style="color:${b.blocked ? "var(--danger)" : "inherit"}">${fmt(b.total_debt)}</b></td>
            <td>${b.blocked ? badge(["", "red"], "ممنوع — بدهی بیش از سقف") : badge(["", "green"], "مجاز")}</td>
            <td>${fmt(b.open_requests)}</td>
            <td style="white-space:nowrap">
                <button class="btn sm ghost" data-act="debts" data-id="${b.id}">بدهی‌ها</button>
                ${canEditDebts ? `<button class="btn sm" data-act="newdebt" data-id="${b.id}">ثبت بدهی</button>` : ""}
            </td>
        </tr>`,
    onAction: (act, b) => {
        if (act === "newdebt") { openNewDebt(b.id); return; }
        debtBuyer = { id: b.id, name: b.full_name };
        updateDebtChip();
        location.hash = "#/debts";
    },
});

registerView("requests", loadRequests);
registerView("debts", () => { updateDebtChip(); debtList.reload(); });
registerView("buyers", () => buyerList.reload());

function enableTilt() {
    if (matchMedia("(prefers-reduced-motion: reduce)").matches || !matchMedia("(hover: hover)").matches) return;
    $$("[data-tilt]").forEach(card => {
        card.addEventListener("pointermove", e => {
            const r = card.getBoundingClientRect();
            const x = (e.clientX - r.left) / r.width - 0.5, y = (e.clientY - r.top) / r.height - 0.5;
            card.style.transform = `perspective(700px) rotateY(${x * 8}deg) rotateX(${-y * 8}deg) translateY(-3px)`;
        });
        card.addEventListener("pointerleave", () => { card.style.transform = ""; });
    });
}
