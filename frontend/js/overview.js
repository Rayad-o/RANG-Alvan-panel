// داشبورد: دو نما — «فروش و مالی» و «کنترل و ریسک»
const ACTIVITY_LABELS = {
    payment_created: "ثبت درخواست پرداخت",
    payment_approved: "تأیید پرداخت",
    payment_stopped: "توقف پرداخت",
    invoice_created: "ثبت فاکتور خرید",
    invoice_resolved: "رفع مغایرت فاکتور",
    supplier_created: "ثبت تأمین‌کننده",
    bank_changed: "تغییر حساب بانکی تأمین‌کننده",
    bank_verified: "تأیید حساب بانکی",
    task_created: "ایجاد وظیفه",
    task_completed: "تکمیل وظیفه",
    user_updated: "ویرایش کاربر",
    settings_updated: "تغییر تنظیمات کنترل",
    debt_created: "ثبت بدهی خریدار",
    debt_paid: "ثبت پرداخت بدهی",
    debt_voided: "ابطال بدهی",
    request_created: "ثبت درخواست خرید",
    request_forwarded: "ارجاع درخواست خرید",
    request_assigned: "واگذاری درخواست خرید",
    request_completed: "تکمیل درخواست خرید",
    request_rejected: "رد درخواست خرید",
    department_created: "ساخت بخش",
};

let overviewTab = (() => {
    try { return localStorage.getItem("overviewTab") === "control" ? "control" : "business"; } catch (e) { return "business"; }
})();

function showOverviewTab() {
    $("#ov-business").hidden = overviewTab !== "business";
    $("#ov-control").hidden = overviewTab !== "control";
    $$("#overviewTab button").forEach(b => b.classList.toggle("on", b.dataset.value === overviewTab));
}

$("#overviewTab").addEventListener("click", e => {
    const btn = e.target.closest("button");
    if (!btn || btn.dataset.value === overviewTab) return;
    overviewTab = btn.dataset.value;
    try { localStorage.setItem("overviewTab", overviewTab); } catch (e2) { /* بدون ذخیره هم کار می‌کند */ }
    showOverviewTab();
    loadOverview();
});

// نشانگر تعداد کنار منو (پرداخت در انتظار، کار عقب‌افتاده)
async function refreshBadges() {
    try {
        const c = await apiJson("/dashboard/control");
        const set = (sel, n) => { const el = $(sel); el.hidden = !n; el.textContent = fmt(n); };
        set("#navPending", c.pending_count);
        set("#navOverdue", c.overdue_tasks);
        return c;
    } catch (err) {
        return null;
    }
}

async function loadOverview() {
    showOverviewTab();
    if (overviewTab === "control") await loadControlOverview();
    else await loadBusinessOverview();
}

// ---------------------------------------------------------------------------
// فروش و مالی
// ---------------------------------------------------------------------------
async function loadBusinessOverview() {
    let s;
    try {
        s = await apiJson(`/dashboard/summary?today=${encodeURIComponent(todayJalali())}`);
    } catch (err) {
        toast(err.message, true);
        $$("#kpis .value").forEach(el => el.classList.remove("skeleton"));
        return;
    }

    $$("#ov-business [data-k]").forEach(el => {
        const key = el.dataset.k;
        el.classList.remove("skeleton");
        const isCard = el.classList.contains("value");
        el.textContent = isCard ? fmtShort(s[key]) : fmt(s[key]);
        el.title = fmt(s[key]);
    });
    $("#hintToday").textContent = "بر اساس تاریخ شمسی امروز";
    $("#hintSales").textContent = `${fmt(s.sales_count)} فاکتور`;

    const monthly = s.monthly_sales.map(m => ({
        label: monthName(m.month),
        tip: `${monthName(m.month)} ${toFaDigits(String(m.month).slice(0, 4))}`,
        value: m.total,
    }));
    Scenes.barChart(
        $("#chart"), monthly, fmtShort, fmt,
        "هنوز فاکتور فروشی ثبت نشده است.<br>از بخش «آپلود اکسل» فایل فروش را بارگذاری کنید."
    );

    const top = s.top_customers;
    const topMax = Math.max(...top.map(c => c.total), 1);
    $("#topCustomers").innerHTML = top.length
        ? top.map(c => `
            <li>
                <div class="row"><span>${esc(c.name)}</span><b>${fmtShort(c.total)}</b></div>
                <div class="bar"><i style="width:0" data-w="${(c.total / topMax) * 100}"></i></div>
            </li>`).join("")
        : '<li class="empty">داده‌ای وجود ندارد</li>';
    requestAnimationFrame(() => requestAnimationFrame(() =>
        $$("#topCustomers i").forEach(i => { i.style.width = i.dataset.w + "%"; })));

    $("#recentBody").innerHTML = s.recent_sales.length
        ? s.recent_sales.map(r => `
            <tr>
                <td>${toFaDigits(esc(r.sale_date))}</td>
                <td>${esc(r.customer_name) || "—"}</td>
                <td>${fmt(r.amount)}</td>
                <td>${r.remaining_amount > 0 ? fmt(r.remaining_amount) : "—"}</td>
            </tr>`).join("")
        : '<tr><td colspan="4" class="empty">فاکتوری ثبت نشده است</td></tr>';
}

// ---------------------------------------------------------------------------
// کنترل و ریسک
// ---------------------------------------------------------------------------
async function loadControlOverview() {
    const c = await refreshBadges();
    if (!c) { toast("خطا در دریافت اطلاعات کنترل", true); return; }

    const val = (sel, text, title) => { const el = $(sel); el.classList.remove("skeleton"); el.textContent = text; if (title) el.title = title; };
    val("#c-today", fmtShort(c.payments_today), fmt(c.payments_today));
    $("#c-today-hint").innerHTML = c.payments_change_pct === null
        ? "بدون مقایسه با دیروز"
        : `<span class="${c.payments_change_pct >= 0 ? "up" : "down"}">${c.payments_change_pct >= 0 ? "▲" : "▼"} ${fmt(Math.abs(c.payments_change_pct))}٪</span> نسبت به دیروز`;
    val("#c-stopped", fmtShort(c.stopped_amount), fmt(c.stopped_amount));
    $("#c-stopped-hint").textContent = `${fmt(c.stopped_count)} مورد نیازمند تصمیم`;
    val("#c-overdue", fmt(c.overdue_tasks));
    $("#c-overdue-hint").textContent = `${fmt(c.critical_overdue)} مورد بحرانی`;
    val("#c-health", fmt(c.health_score));
    $("#c-health-hint").textContent = c.health_score >= 80 ? "وضعیت مطلوب" : c.health_score >= 50 ? "نیازمند توجه" : "وضعیت بحرانی";

    $("#alertsMeta").textContent = c.alerts_total > c.alerts.length ? `${fmt(c.alerts_total)} هشدار (نمایش ${fmt(c.alerts.length)} مورد)` : "";
    $("#alerts").innerHTML = c.alerts.length
        ? c.alerts.map(a => `
            <button class="alert-item" data-link="${esc(a.link)}">
                <span class="alert-icon ${a.level}">${a.icon}</span>
                <span class="alert-main"><b>${esc(a.title)}</b><small>${toFaDigits(esc(a.detail))}</small></span>
                <span class="badge ${a.level}">${esc(a.badge)}</span>
            </button>`).join("")
        : '<div class="empty">هشدار فعالی وجود ندارد 🎉</div>';

    $("#topRisks").innerHTML = c.top_risks.length
        ? c.top_risks.map(r => {
            const lvl = riskClass(r.risk_score);
            return `
            <div class="risk-box">
                <div class="risk-line"><b>${esc(r.party_name)} <small>${esc(r.ref)}</small></b><span class="badge ${lvl}">${fmt(r.risk_score)}/۱۰۰</span></div>
                <div class="progress"><i style="width:${r.risk_score}%;background:${RISK_VAR[lvl]}"></i></div>
                <div class="risk-reason">${r.reasons.length ? toFaDigits(esc(r.reasons.join(" + "))) : "بدون نشانهٔ ریسک"}</div>
            </div>`;
        }).join("")
        : '<div class="empty">پرداخت در انتظار تأییدی وجود ندارد</div>';

    const days = c.payments_7d.map(d => ({ label: d.label, tip: fmtDate(d.date), value: d.total }));
    Scenes.barChart($("#chart7d"), days, fmtShort, fmt, "در ۷ روز گذشته درخواست پرداختی ثبت نشده است.");

    const perf = c.task_performance;
    $("#ring").style.background = `conic-gradient(var(--accent) 0 ${perf.on_time_pct}%, #e8edf2 ${perf.on_time_pct}%)`;
    $("#ringText").textContent = fmt(perf.on_time_pct) + "٪";
    $("#p-done").textContent = fmt(perf.done);
    $("#p-overdue").textContent = fmt(perf.overdue);
    $("#f-high").textContent = fmt(c.focus.high_risk_payments);
    $("#f-inv").textContent = fmt(c.focus.invoice_mismatches);
    $("#f-sens").textContent = fmt(c.focus.sensitive_changes);

    $("#activity").innerHTML = c.recent_activity.length
        ? c.recent_activity.map(a => `
            <li><span class="dot"></span>
                <span><b>${esc(ACTIVITY_LABELS[a.action] || a.action)}</b>${a.detail ? " — " + toFaDigits(esc(a.detail)) : ""}
                <small>${esc(a.actor)} • ${toFaDigits(fmtDate(a.at, true))}</small></span></li>`).join("")
        : '<li class="empty">فعالیتی ثبت نشده است</li>';
}

// هشدارها و دکمه‌های لینک‌دار: رفتن به صفحهٔ مربوط
document.addEventListener("click", e => {
    const el = e.target.closest("[data-link]");
    if (el) location.hash = `#/${el.dataset.link}`;
});

registerView("overview", loadOverview);
