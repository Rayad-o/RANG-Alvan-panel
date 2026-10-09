// راه‌اندازی پنل: منو بر اساس نقش، مسیریابی و نشانگر تعداد کارهای منتظر
const NAV_ICONS = {
    home: '<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>',
    wallet: '<rect x="3" y="6" width="18" height="13" rx="2.5"/><path d="M3 10h18M16 14.5h2"/>',
    cart: '<path d="M3 4h2l2.4 11h10.2L20 8H6.2"/><circle cx="9" cy="19.5" r="1.4"/><circle cx="17" cy="19.5" r="1.4"/>',
    inbox: '<path d="M4 13l2-8h12l2 8"/><path d="M4 13v6h16v-6h-5l-1 2h-4l-1-2z"/>',
    users: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6"/><path d="M17 5.5a3.5 3.5 0 010 5M19 14.5c1.6.8 2.5 2.5 2.5 5.5"/>',
    panel: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18M9 9v11"/>',
    task: '<rect x="4" y="4" width="16" height="17" rx="2"/><path d="M9 4V2h6v2"/><path d="M8.5 13l2.5 2.5 4.5-5"/>',
};

const HOME = ["home", "داشبورد", "home"];
const NAV = {
    buyer: [HOME, ["myDebts", "بدهی‌های من", "wallet"], ["myRequests", "درخواست خرید", "cart"]],
    accountant: [HOME, ["requests", "درخواست‌های خرید", "inbox"], ["debts", "ثبت و پیگیری بدهی‌ها", "wallet"], ["buyers", "خریداران", "users"]],
    dept_head: [HOME, ["requests", "درخواست‌های بخش", "inbox"]],
    dept_staff: [HOME, ["requests", "کارهای من", "task"]],
};
NAV.admin = NAV.accountant;
NAV.manager = NAV.accountant;

// مدیر سیستم و مدیر از این‌جا به داشبورد مدیریتی (و مدیر سیستم به مدیریت کاربران) برمی‌گردند
const EXTRA_LINKS = {
    admin: [["dashboard.html#/overview", "داشبورد مدیریتی", "panel"], ["dashboard.html#/users", "کاربران و بخش‌ها", "users"]],
    manager: [["dashboard.html#/overview", "داشبورد مدیریتی", "panel"]],
};

const navItems = NAV[ROLE] || [HOME];
const svg = key => `<svg viewBox="0 0 24 24">${NAV_ICONS[key]}</svg>`;

$("#nav").innerHTML =
    navItems.map(([view, label, icon]) =>
        `<a class="nav-link" href="#/${view}" data-view="${view}">${svg(icon)}${label}${view === "requests" ? '<span class="count" id="navRequests" hidden></span>' : ""}</a>`).join("") +
    ((EXTRA_LINKS[ROLE] || []).length ? '<div class="nav-title">مدیریت</div>' : "") +
    (EXTRA_LINKS[ROLE] || []).map(([href, label, icon]) => `<a class="nav-link" href="${href}">${svg(icon)}${label}</a>`).join("");

$("#brandTitle").textContent = ROLE === "buyer" ? "پنل خریدار" : "پنل همکاران";
$("#brandSub").textContent = "کارخانهٔ رنگ";
$("#userName").textContent = user.full_name;
$("#userAvatar").textContent = (user.full_name || "?").trim().charAt(0);
$("#userRole").textContent = ROLES[ROLE] || ROLE;
if (user.department) $("#userRole").textContent += ` • ${user.department}`;
$("#logoutBtn").addEventListener("click", logout);
document.title = `${ROLE === "buyer" ? "پنل خریدار" : "پنل همکاران"} — ${user.full_name}`;

// نشانگر کنار «درخواست‌ها»: تعداد کارهای منتظر اقدام همین کاربر
async function refreshPortalBadges() {
    if (ROLE === "buyer") return;
    try {
        const s = await apiJson("/requests/summary");
        const el = $("#navRequests");
        if (el) { el.hidden = !s.pending_for_me; el.textContent = fmt(s.pending_for_me); }
    } catch (e) { /* نشانگر اختیاری است */ }
}

let currentView = null;

function route() {
    const name = (location.hash.match(/^#\/(\w+)/) || [])[1];
    const allowed = navItems.map(i => i[0]);
    const view = allowed.includes(name) && views[name] ? name : "home";
    currentView = view;

    $$(".view").forEach(v => v.classList.toggle("active", v.id === `view-${view}`));
    $$(".nav-link[data-view]").forEach(a => a.classList.toggle("active", a.dataset.view === view));
    window.scrollTo({ top: 0 });

    if (view === "home" || !visited.has(view) || stale.has(view)) {
        visited.add(view);
        stale.delete(view);
        views[view]();
    }
}

// بعد از هر تغییر (ارجاع، واگذاری، پرداخت...) نمای فعلی و بقیهٔ نماها تازه می‌شوند
afterRequestChange = () => {
    invalidate(...Object.keys(views));
    stale.delete(currentView);
    views[currentView]();
    refreshPortalBadges();
};

window.addEventListener("hashchange", route);
route();
refreshPortalBadges();
