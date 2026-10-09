// پنل خریدار و کارگران: تعریف‌های مشترک و پنجرهٔ جزئیات درخواست خرید
const ROLE = user.role;
const toman = n => `${fmt(n)} تومان`;

const REQ_STATUS = {
    submitted: ["ثبت‌شده", "blue"],
    forwarded: ["ارجاع‌شده به بخش", "orange"],
    assigned: ["واگذار شده", "orange"],
    in_progress: ["در حال انجام", "blue"],
    done: ["انجام‌شده", "green"],
    rejected: ["رد شده", "red"],
    cancelled: ["لغو شده", "gray"],
};

const EVENT_LABELS = {
    created: "ثبت درخواست", forwarded: "ارجاع به بخش", assigned: "واگذاری به کارکن",
    started: "شروع کار", completed: "تکمیل شد", rejected: "رد شد", cancelled: "لغو شد",
};

const STEPS = ["ثبت‌شده", "ارجاع به بخش", "واگذاری", "در حال انجام", "انجام‌شده"];
const STEP_INDEX = { submitted: 0, forwarded: 1, assigned: 2, in_progress: 3, done: 4 };

const ACCOUNTING_ROLES = ["accountant", "admin", "manager"];
const isAccounting = ACCOUNTING_ROLES.includes(ROLE);

// ---------------------------------------------------------------------------
// قطعه‌های قالب
// ---------------------------------------------------------------------------
function itemsSummary(items) {
    if (!items || !items.length) return "—";
    const first = items.slice(0, 2).map(i => `${esc(i.product_title)} (${toFaDigits(fmt(i.quantity))})`).join("، ");
    return items.length > 2 ? `${first} و ${fmt(items.length - 2)} قلم دیگر` : first;
}

function stepperHtml(status) {
    if (status === "rejected" || status === "cancelled") return "";
    const current = STEP_INDEX[status] ?? 0;
    return `<div class="stepper">${STEPS.map((label, i) =>
        `<div class="step ${i < current || (status === "done" && i <= current) ? "done" : ""} ${i === current ? "current" : ""}"><i></i>${label}</div>`).join("")}</div>`;
}

function timelineHtml(events) {
    if (!events || !events.length) return "";
    return `<ul class="timeline">${events.map(e => `
        <li><span class="dot"></span><span><b>${esc(EVENT_LABELS[e.action] || e.action)}</b>${e.note ? " — " + esc(e.note) : ""}
        <small>${esc(e.actor)} • ${toFaDigits(fmtDate(e.at, true))}</small></span></li>`).join("")}</ul>`;
}

function itemsTableHtml(items) {
    return `<table class="items-table"><thead><tr><th>کد</th><th>کالا</th><th>تعداد</th></tr></thead><tbody>${
        items.map(i => `<tr><td>${esc(i.product_code)}</td><td>${esc(i.product_title)}</td><td>${fmt(i.quantity)}</td></tr>`).join("")
    }</tbody></table>`;
}

const statusBadge = s => badge(REQ_STATUS[s] || ["", "gray"]);

// پس از هر تغییر: همهٔ نماها دوباره بارگذاری شوند و نشانگرها تازه شوند (تعریف در portal-boot.js)
let afterRequestChange = () => {};

// ---------------------------------------------------------------------------
// پنجرهٔ جزئیات درخواست (برای خریدار و همهٔ کارگران؛ دکمه‌ها بر اساس نقش و وضعیت)
// ---------------------------------------------------------------------------
async function openRequest(r) {
    // خریدار فهرست خودش را با تاریخچه دارد؛ کارگران جزئیات تازه را می‌گیرند
    if (ROLE !== "buyer") {
        try { r = await apiJson(`/requests/${r.id}`); } catch (e) { toast(e.message, true); return; }
    }

    const mine = ROLE === "dept_staff" && r.assigned_to_id === user.id;
    const canForward = (ROLE === "accountant" || ROLE === "admin") && ["submitted", "forwarded"].includes(r.status);
    const canAssign = (ROLE === "dept_head" || ROLE === "admin") && ["forwarded", "assigned"].includes(r.status);
    const canStart = r.status === "assigned" && (mine || ROLE === "dept_head" || ROLE === "admin");
    const canComplete = (r.status === "in_progress" && (mine || ROLE === "dept_head" || ROLE === "admin")) ||
        (r.status === "assigned" && (ROLE === "dept_head" || ROLE === "admin"));
    const canCancel = ROLE === "buyer" && r.status === "submitted";

    const debtLine = isAccounting && r.buyer_debt !== null && r.buyer_debt !== undefined
        ? `<div class="detail"><small>بدهی فعلی خریدار</small><b>${toman(r.buyer_debt)}</b></div>` : "";

    const body = Modal.open(`درخواست ${toFaDigits(r.ref || "")}`, `
        <div class="detail-grid">
            ${ROLE !== "buyer" ? `<div class="detail"><small>خریدار</small><b>${esc(r.buyer_name)}</b></div>` : ""}
            <div class="detail"><small>تاریخ ثبت</small><b>${toFaDigits(fmtDate(r.created_at, true))}</b></div>
            <div class="detail"><small>وضعیت</small><b>${statusBadge(r.status)}</b></div>
            <div class="detail"><small>بخش</small><b>${esc(r.department) || "—"}</b></div>
            <div class="detail"><small>مسئول</small><b>${esc(r.assigned_to_name) || "—"}</b></div>
            ${debtLine}
        </div>
        ${stepperHtml(r.status)}
        ${r.status === "rejected" ? `<div class="callout red"><b>درخواست رد شد:</b> ${esc(r.decision_note) || "—"}</div>` : ""}
        ${r.note ? `<div class="detail"><small>یادداشت خریدار</small><b>${esc(r.note)}</b></div>` : ""}
        ${itemsTableHtml(r.items)}
        <div><h4 class="mini-title">تاریخچه</h4>${timelineHtml(r.events)}</div>
        <div id="reqActions"></div>
        <p class="error-line" id="reqError"></p>`);

    const actions = $("#reqActions", body);
    const errBox = $("#reqError", body);

    // کمکی: اجرای یک اقدام روی درخواست
    const run = (btn, method, path, payload, message) => submitForm(btn, errBox, async () => {
        await apiSend(method, path, payload);
        Modal.close();
        toast(message);
        afterRequestChange();
    });

    if (canCancel) {
        actions.innerHTML = '<div class="modal-actions"><button class="btn danger" id="actCancel">لغو درخواست</button></div>';
        const b = $("#actCancel", body);
        b.addEventListener("click", () => run(b, "POST", `/buyer/requests/${r.id}/cancel`, undefined, "درخواست لغو شد"));
    }

    if (canForward) {
        let depts = [];
        try { depts = await apiJson("/departments/"); } catch (e) { errBox.textContent = e.message; }
        actions.innerHTML += `
            <div class="form-grid">
                ${field("ارجاع به بخش", `<select class="select" id="fwDept">${depts.map(d => `<option ${d.name === r.department ? "selected" : ""}>${esc(d.name)}</option>`).join("")}</select>`)}
                ${field("یادداشت / دلیل رد", '<input class="input" id="fwNote" maxlength="1000" placeholder="برای رد کردن الزامی است">')}
            </div>
            <div class="modal-actions">
                <button class="btn" id="actForward">${r.status === "forwarded" ? "ارجاع به بخش دیگر" : "ارجاع به بخش"}</button>
                <button class="btn danger" id="actReject">رد درخواست</button>
            </div>`;
        const f = $("#actForward", body), rj = $("#actReject", body);
        f.addEventListener("click", () => run(f, "POST", `/requests/${r.id}/forward`,
            { department: $("#fwDept", body).value, note: $("#fwNote", body).value.trim() || null }, "درخواست به بخش ارجاع شد"));
        rj.addEventListener("click", () => {
            const note = $("#fwNote", body).value.trim();
            if (note.length < 3) { errBox.textContent = "برای رد کردن، دلیل را بنویسید"; return; }
            run(rj, "POST", `/requests/${r.id}/reject`, { note }, "درخواست رد شد");
        });
    }

    if (canAssign) {
        let staff = [];
        try {
            staff = await apiJson(ROLE === "admin" ? `/requests/staff?department=${encodeURIComponent(r.department)}` : "/requests/staff");
        } catch (e) { errBox.textContent = e.message; }
        actions.innerHTML += staff.length ? `
            <div class="form-grid">
                ${field("واگذاری به", `<select class="select" id="asUser">${staff.map(s =>
                    `<option value="${s.id}" ${s.id === r.assigned_to_id ? "selected" : ""}>${esc(s.full_name)} — ${fmt(s.active_requests)} کار در جریان</option>`).join("")}</select>`)}
                ${field("یادداشت (اختیاری)", '<input class="input" id="asNote" maxlength="1000">')}
            </div>
            <div class="modal-actions"><button class="btn" id="actAssign">${r.status === "assigned" ? "تغییر کارکن" : "واگذاری به کارکن"}</button></div>`
            : '<div class="callout orange">برای این بخش کارکن فعالی ثبت نشده است. مدیر سیستم باید کارکن اضافه کند.</div>';
        const a = $("#actAssign", body);
        if (a) a.addEventListener("click", () => run(a, "POST", `/requests/${r.id}/assign`,
            { assignee_id: Number($("#asUser", body).value), note: $("#asNote", body).value.trim() || null }, "درخواست واگذار شد"));
    }

    if (canStart || canComplete) {
        actions.innerHTML += `
            ${canComplete ? field("یادداشت پایان کار (اختیاری)", '<input class="input" id="doneNote" maxlength="1000" placeholder="مثلاً آماده تحویل در انبار">', true) : ""}
            <div class="modal-actions">
                ${canStart ? '<button class="btn" id="actStart">شروع کار</button>' : ""}
                ${canComplete ? '<button class="btn success" id="actDone">تکمیل کار</button>' : ""}
            </div>`;
        const s = $("#actStart", body), d = $("#actDone", body);
        if (s) s.addEventListener("click", () => run(s, "POST", `/requests/${r.id}/start`, undefined, "کار شروع شد"));
        if (d) d.addEventListener("click", () => run(d, "POST", `/requests/${r.id}/complete`,
            { note: $("#doneNote", body).value.trim() || null }, "کار تکمیل شد"));
    }
}

// کلیک روی هر عنصر با data-open-request (در کارت‌های داشبورد)
const requestCache = new Map();
document.addEventListener("click", e => {
    const el = e.target.closest("[data-open-request]");
    if (!el) return;
    const r = requestCache.get(el.dataset.openRequest);
    if (r) openRequest(r);
});
const cacheRequests = list => list.forEach(r => requestCache.set(String(r.id), r));
