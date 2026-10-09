// گزارش‌ها، کاربران و تنظیمات کنترل

// ---------------------------------------------------------------------------
// گزارش‌ها
// ---------------------------------------------------------------------------
const EXPORTS = [
    {
        title: "فاکتورهای فروش", file: "sales.csv", endpoint: "/sales/",
        cols: [
            { title: "تاریخ", value: r => r.sale_date }, { title: "شماره", value: r => r.invoice_number },
            { title: "مشتری", value: r => r.customer_name }, { title: "مبلغ", value: r => r.amount },
            { title: "مانده", value: r => r.remaining_amount }, { title: "توضیحات", value: r => r.description },
        ],
    },
    {
        title: "درخواست‌های پرداخت", file: "payments.csv", endpoint: "/payments/",
        cols: [
            { title: "شناسه", value: r => r.ref }, { title: "تاریخ", value: r => fmtDate(r.created_at, true) },
            { title: "طرف‌حساب", value: r => r.party_name }, { title: "شرح", value: r => r.description },
            { title: "مبلغ", value: r => r.amount }, { title: "امتیاز ریسک", value: r => r.risk_score },
            { title: "وضعیت", value: r => PAY_STATUS[r.status][0] }, { title: "دلایل ریسک", value: r => r.risk_reasons.join(" | ") },
        ],
    },
    {
        title: "فاکتورهای خرید", file: "purchase-invoices.csv", endpoint: "/purchase-invoices/",
        cols: [
            { title: "شماره", value: r => r.number }, { title: "تأمین‌کننده", value: r => r.supplier_name },
            { title: "سفارش", value: r => r.po_number }, { title: "رسیدشده", value: r => r.received_qty },
            { title: "فاکتورشده", value: r => r.invoiced_qty }, { title: "واحد", value: r => r.unit },
            { title: "مبلغ", value: r => r.amount }, { title: "نتیجه", value: r => INV_STATUS[r.status][0] },
        ],
    },
    {
        title: "تأمین‌کنندگان", file: "suppliers.csv", endpoint: "/suppliers/",
        cols: [
            { title: "نام", value: r => r.name }, { title: "کد", value: r => r.code }, { title: "دسته", value: r => r.category },
            { title: "حساب بانکی", value: r => r.bank_account }, { title: "پرریسک", value: r => (r.is_high_risk ? "بله" : "خیر") },
        ],
    },
    {
        title: "وظایف", file: "tasks.csv", endpoint: "/tasks/",
        cols: [
            { title: "واحد", value: r => r.unit }, { title: "وظیفه", value: r => r.title }, { title: "مسئول", value: r => r.owner },
            { title: "سررسید", value: r => fmtDate(r.due_at, true) }, { title: "وضعیت", value: r => TASK_STATUS[r.status][0] },
            { title: "اولویت", value: r => (PRIORITY[r.priority] || ["", ""])[0] },
        ],
    },
    {
        title: "مطالبات و بستانکاری", file: "ledger.csv", endpoint: "/finance/",
        cols: [
            { title: "طرف‌حساب", value: r => r.party_name }, { title: "نوع", value: r => (r.type === "receivable" ? "مطالبات" : "بستانکاری") },
            { title: "مبلغ", value: r => r.amount }, { title: "توضیحات", value: r => r.description },
        ],
    },
];

$("#exportList").innerHTML = EXPORTS.map((x, i) =>
    `<button class="export-btn" data-i="${i}"><span>↧</span> ${x.title}</button>`).join("");

$("#exportList").addEventListener("click", async e => {
    const btn = e.target.closest("[data-i]");
    if (!btn) return;
    const x = EXPORTS[btn.dataset.i];
    btn.disabled = true;
    try {
        const rows = await apiJson(`${x.endpoint}?limit=1000`);
        if (!rows.length) { toast("دادهای برای خروجی وجود ندارد", true); return; }
        downloadCSV(x.file, x.cols, rows);
        toast(`${x.title}: ${fmt(rows.length)} ردیف`);
    } catch (err) {
        toast(err.message, true);
    } finally {
        btn.disabled = false;
    }
});

$("#printReport").addEventListener("click", () => window.print());

async function loadReports() {
    $("#reportDate").textContent = toFaDigits(todayJalali());
    let c, s;
    try {
        [c, s] = await Promise.all([apiJson("/dashboard/control"), apiJson(`/dashboard/summary?today=${encodeURIComponent(todayJalali())}`)]);
    } catch (err) {
        toast(err.message, true);
        return;
    }
    const card = (title, value, hint, tint) =>
        `<div class="card" style="--tint:${tint}"><h3>${title}</h3><div class="value">${value}</div><div class="hint">${hint}</div></div>`;
    $("#reportKpis").innerHTML =
        card("کل فروش", fmtShort(s.sales_total), `${fmt(s.sales_count)} فاکتور`, "#14b8a6") +
        card("مطالبات", fmtShort(s.receivables), "حساب‌های دریافتنی", "#f59e0b") +
        card("پرداخت در انتظار", fmtShort(c.pending_amount), `${fmt(c.pending_count)} مورد`, "#5b5bf0") +
        card("امتیاز سلامت", fmt(c.health_score), c.health_score >= 80 ? "مطلوب" : "نیازمند توجه", "#ec4899");

    const line = (label, value, cls = "") => `<div class="s"><span>${label}</span><b class="${cls}">${value}</b></div>`;
    $("#reportStats").innerHTML =
        line("پرداخت‌های در انتظار تأیید", `${fmt(c.pending_count)} (${fmtShort(c.pending_amount)})`) +
        line("پرداخت‌های متوقف‌شده", `${fmt(c.stopped_count)} (${fmtShort(c.stopped_amount)})`, c.stopped_count ? "red" : "") +
        line("پرداخت‌های پرریسک در انتظار", fmt(c.focus.high_risk_payments), c.focus.high_risk_payments ? "red" : "") +
        line("فاکتورهای مغایرت‌دار", fmt(c.focus.invoice_mismatches), c.focus.invoice_mismatches ? "orange" : "") +
        line("تغییرات بانکی تأییدنشده", fmt(c.focus.sensitive_changes), c.focus.sensitive_changes ? "orange" : "") +
        line("وظایف عقب‌افتاده", `${fmt(c.overdue_tasks)} (بحرانی: ${fmt(c.critical_overdue)})`, c.overdue_tasks ? "orange" : "") +
        line("انجام به‌موقع وظایف", fmt(c.task_performance.on_time_pct) + "٪") +
        line("فاکتورهای فروش تسویه‌نشده", `${fmt(s.unpaid_invoices)} (${fmtShort(s.unpaid_amount)})`);
}

// ---------------------------------------------------------------------------
// کاربران
// ---------------------------------------------------------------------------
const DEPT_ROLES = ["dept_head", "dept_staff"];
const ROLE_BADGE = {
    admin: "red", manager: "blue", staff: "gray",
    buyer: "pink", accountant: "orange", dept_head: "orange", dept_staff: "orange",
};
const PANEL_NOTE = {
    admin: "دسترسی کامل به داشبورد، کاربران و تنظیمات",
    manager: "داشبورد مدیریتی؛ تأیید پرداخت تا سقف مجاز",
    staff: "داشبورد مدیریتی؛ ثبت و مشاهده",
    buyer: "پنل خریدار: بدهی‌ها و ثبت درخواست خرید",
    accountant: "پنل کارگران: ثبت بدهی و ارجاع درخواست‌ها به بخش",
    dept_head: "پنل کارگران: واگذاری درخواست‌های بخش به کارکنان",
    dept_staff: "پنل کارگران: انجام کارهای واگذارشده",
};

const userList = createList({
    endpoint: "/users/", body: "#userBody", pageSize: 200, columns: 6,
    row: u => `
        <tr>
            <td><b>${esc(u.full_name)}</b>${u.id === user.id ? ' <small class="rel">(شما)</small>' : ""}</td>
            <td dir="ltr" class="ltr-cell">${esc(u.email)}</td>
            <td>${badge(["", ROLE_BADGE[u.role] || "gray"], ROLES[u.role] || u.role)}</td>
            <td>${esc(u.department) || "—"}</td>
            <td>${u.is_active ? badge(["", "green"], "فعال") : badge(["", "gray"], "غیرفعال")}</td>
            <td><button class="btn sm ghost" data-act="edit" data-id="${u.id}">ویرایش</button></td>
        </tr>`,
    onAction: (act, u) => openUser(u),
});

const roleOptions = selected => Object.entries(ROLES)
    .map(([v, l]) => `<option value="${v}" ${v === selected ? "selected" : ""}>${l}</option>`).join("");

async function departmentOptions(selected) {
    const list = await apiJson("/departments/");
    return list.length
        ? list.map(d => `<option ${d.name === selected ? "selected" : ""}>${esc(d.name)}</option>`).join("")
        : '<option value="">— ابتدا بخش بسازید —</option>';
}

// بخش فقط برای رییس/کارکن بخش نمایش داده می‌شود؛ توضیح پنل هر نقش زیر فرم نشان داده می‌شود
function bindRoleFields(body, roleSel, deptWrap, noteEl) {
    const sync = () => {
        deptWrap.hidden = !DEPT_ROLES.includes(roleSel.value);
        noteEl.textContent = PANEL_NOTE[roleSel.value] || "";
    };
    roleSel.addEventListener("change", sync);
    sync();
}

async function openUser(u) {
    const self = u.id === user.id;
    let deptOpts;
    try { deptOpts = await departmentOptions(u.department); } catch (e) { toast(e.message, true); return; }
    const body = Modal.open(`ویرایش ${u.full_name}`, `
        <div class="form-grid">
            ${field("نام", `<input class="input" id="euName" value="${esc(u.full_name)}" maxlength="255">`)}
            ${field("نقش", `<select class="select" id="euRole" ${self ? "disabled" : ""}>${roleOptions(u.role)}</select>`)}
            <div id="euDeptWrap" class="full">${field("بخش", `<select class="select" id="euDept">${deptOpts}</select>`, true)}</div>
            ${field("رمز جدید (اختیاری)", '<input class="input" id="euPass" type="password" autocomplete="new-password" dir="ltr" placeholder="حداقل ۶ نویسه">', true)}
        </div>
        <p class="hint-line" id="euNote"></p>
        <label class="check"><input type="checkbox" id="euActive" ${u.is_active ? "checked" : ""} ${self ? "disabled" : ""}> حساب فعال است</label>
        ${self ? '<p class="hint-line">نقش و وضعیت حساب خودتان قابل کاهش نیست.</p>' : ""}
        <div class="modal-actions"><button class="btn" id="euSave">ذخیره</button></div>
        <p class="error-line" id="euError"></p>`);
    bindRoleFields(body, $("#euRole", body), $("#euDeptWrap", body), $("#euNote", body));
    const save = $("#euSave", body);
    save.addEventListener("click", () => submitForm(save, $("#euError", body), async () => {
        const payload = { full_name: $("#euName", body).value.trim() };
        if (!payload.full_name) throw new Error("نام را وارد کنید");
        if (!self) {
            payload.role = $("#euRole", body).value;
            payload.is_active = $("#euActive", body).checked;
        }
        if (DEPT_ROLES.includes(self ? u.role : payload.role)) payload.department = $("#euDept", body).value;
        const pass = $("#euPass", body).value;
        if (pass) payload.password = pass;
        await apiSend("PATCH", `/users/${u.id}`, payload);
        Modal.close();
        toast("کاربر ذخیره شد");
        userList.reload();
    }));
}

$("#newUser").addEventListener("click", async () => {
    let deptOpts;
    try { deptOpts = await departmentOptions(); } catch (e) { toast(e.message, true); return; }
    const body = Modal.open("کاربر جدید", `
        <div class="form-grid">
            ${field("نام کامل", '<input class="input" id="nuName" maxlength="255">')}
            ${field("ایمیل", '<input class="input" id="nuEmail" type="email" dir="ltr" autocomplete="off">')}
            ${field("رمز عبور", '<input class="input" id="nuPass" type="password" autocomplete="new-password" dir="ltr" placeholder="حداقل ۶ نویسه">')}
            ${field("نقش", `<select class="select" id="nuRole">${roleOptions("buyer")}</select>`)}
            <div id="nuDeptWrap" class="full">${field("بخش", `<select class="select" id="nuDept">${deptOpts}</select>`, true)}</div>
        </div>
        <p class="hint-line" id="nuNote"></p>
        <div class="modal-actions"><button class="btn" id="nuSave">ایجاد کاربر</button></div>
        <p class="error-line" id="nuError"></p>`);
    bindRoleFields(body, $("#nuRole", body), $("#nuDeptWrap", body), $("#nuNote", body));
    const save = $("#nuSave", body);
    save.addEventListener("click", () => submitForm(save, $("#nuError", body), async () => {
        const full_name = $("#nuName", body).value.trim(), email = $("#nuEmail", body).value.trim(), password = $("#nuPass", body).value;
        if (!full_name || !email) throw new Error("نام و ایمیل را وارد کنید");
        if (password.length < 6) throw new Error("رمز عبور باید حداقل ۶ نویسه باشد");
        const role = $("#nuRole", body).value;
        const payload = { full_name, email, password, role };
        if (DEPT_ROLES.includes(role)) payload.department = $("#nuDept", body).value;
        await apiSend("POST", "/auth/register", payload);
        Modal.close();
        toast("کاربر ایجاد شد");
        userList.reload();
    }));
});

// ---- بخش‌ها (برای رییس و کارکنان بخش) ----
async function loadDepartments() {
    const box = $("#deptList");
    try {
        const list = await apiJson("/departments/");
        box.innerHTML = list.length
            ? list.map(d => `<span class="badge blue">${esc(d.name)}</span>`).join(" ")
            : '<span class="hint-line">هنوز بخشی ساخته نشده است.</span>';
    } catch (e) { box.textContent = e.message; }
}

$("#deptAdd").addEventListener("click", () => {
    const input = $("#deptName");
    submitForm($("#deptAdd"), $("#deptError"), async () => {
        const name = input.value.trim();
        if (name.length < 2) throw new Error("نام بخش را وارد کنید");
        await apiSend("POST", "/departments/", { name });
        input.value = "";
        toast("بخش ساخته شد");
        loadDepartments();
    });
});

$("#changePassword").addEventListener("click", () => {
    const body = Modal.open("تغییر رمز من", `
        <div class="form-grid">
            ${field("رمز فعلی", '<input class="input" id="cpOld" type="password" autocomplete="current-password" dir="ltr">', true)}
            ${field("رمز جدید", '<input class="input" id="cpNew" type="password" autocomplete="new-password" dir="ltr" placeholder="حداقل ۶ نویسه">', true)}
        </div>
        <div class="modal-actions"><button class="btn" id="cpSave">تغییر رمز</button></div>
        <p class="error-line" id="cpError"></p>`);
    const save = $("#cpSave", body);
    save.addEventListener("click", () => submitForm(save, $("#cpError", body), async () => {
        await apiSend("POST", "/auth/change-password", { current_password: $("#cpOld", body).value, new_password: $("#cpNew", body).value });
        Modal.close();
        toast("رمز عبور تغییر کرد");
    }));
});

// ---------------------------------------------------------------------------
// تنظیمات کنترل
// ---------------------------------------------------------------------------
const CONTROL_LABELS = {
    risk_score: ["امتیازدهی ریسک پرداخت", "محاسبهٔ امتیاز ۰ تا ۱۰۰ برای هر درخواست"],
    bank_change_alert: ["هشدار تغییر حساب بانکی", "تغییر تأییدنشدهٔ حساب تأمین‌کننده ریسک می‌دهد"],
    duplicate_detection: ["تشخیص پرداخت تکراری", "همان مبلغ و تأمین‌کننده در ۷ روز"],
    three_way_match: ["تطبیق سفارش / رسید / فاکتور", "مقایسهٔ مقدار رسیدشده با فاکتورشده"],
    task_escalation: ["هشدار وظایف بحرانی عقب‌افتاده", "نمایش در هشدارهای داشبورد"],
};

let loadedSettings = null;
const isAdmin = atLeast("admin");

function renderSettings(cfg) {
    $("#controlToggles").innerHTML = Object.entries(CONTROL_LABELS).map(([key, [title, hint]]) => `
        <label class="toggle-row">
            <span><b>${title}</b><small>${hint}</small></span>
            <input type="checkbox" data-control="${key}" ${cfg.controls[key] ? "checked" : ""} ${isAdmin ? "" : "disabled"}>
        </label>`).join("");

    const tiers = cfg.approval_tiers;
    $("#tiers").innerHTML = tiers.map((t, i) => {
        const prev = i === 0 ? null : tiers[i - 1].upto;
        const label = t.upto === null
            ? `<span class="tier-label">بیش از <b>${fmt(prev)}</b></span>`
            : `<span class="tier-label">${i === 0 ? "تا" : `${fmt(prev)} تا`}</span>
               <input class="input tier-upto" data-i="${i}" inputmode="numeric" value="${fmt(t.upto)}" ${isAdmin ? "" : "disabled"}>`;
        return `<div class="tier-row">${label}
            <select class="select tier-role" data-i="${i}" ${isAdmin ? "" : "disabled"}>
                <option value="manager" ${t.role === "manager" ? "selected" : ""}>مدیر</option>
                <option value="admin" ${t.role === "admin" ? "selected" : ""}>مدیر سیستم</option>
            </select></div>`;
    }).join("");

    $("#setHigh").value = fmt(cfg.high_risk_threshold);
    $("#setTolerance").value = fmt(cfg.match_tolerance_pct);
    $("#setBuyerLimit").value = fmt(cfg.buyer_debt_limit);
    $$("#view-settings .input").forEach(i => { if (!isAdmin) i.disabled = true; });
    $("#saveSettings").hidden = !isAdmin;
}

async function loadSettings() {
    try {
        loadedSettings = await apiJson("/settings/");
        Cfg.high = loadedSettings.high_risk_threshold;
        renderSettings(loadedSettings);
    } catch (err) {
        toast(err.message, true);
    }
}

$("#saveSettings").addEventListener("click", () => {
    const btn = $("#saveSettings");
    submitForm(btn, $("#settingsError"), async () => {
        const controls = {};
        $$("[data-control]").forEach(el => { controls[el.dataset.control] = el.checked; });

        const tiers = loadedSettings.approval_tiers.map((t, i) => {
            const upto = $(`.tier-upto[data-i="${i}"]`);
            const role = $(`.tier-role[data-i="${i}"]`).value;
            if (!upto) return { upto: null, role };
            const n = parseNum(upto.value);
            if (!(n > 0)) throw new Error("سقف‌های تأیید باید عدد مثبت باشند");
            return { upto: n, role };
        });
        const high = parseNum($("#setHigh").value), tol = parseNum($("#setTolerance").value);
        if (!(high >= 1 && high <= 100)) throw new Error("آستانهٔ ریسک بالا باید بین ۱ تا ۱۰۰ باشد");
        if (!(tol >= 0 && tol <= 50)) throw new Error("اختلاف مجاز باید بین ۰ تا ۵۰ درصد باشد");
        const buyerLimit = parseNum($("#setBuyerLimit").value);
        if (!(buyerLimit >= 0)) throw new Error("سقف بدهی خریدار باید عدد (۰ یا بیشتر) باشد");

        loadedSettings = await apiSend("PUT", "/settings/", {
            controls, approval_tiers: tiers, match_tolerance_pct: tol, high_risk_threshold: high,
            buyer_debt_limit: buyerLimit,
        });
        Cfg.high = loadedSettings.high_risk_threshold;
        renderSettings(loadedSettings);
        invalidate("overview", "payments", "purchase");
        toast("تنظیمات ذخیره شد (روی درخواست‌های جدید اعمال می‌شود)");
    });
});

registerView("reports", loadReports);
registerView("users", () => { userList.reload(); loadDepartments(); });
registerView("settings", loadSettings);
