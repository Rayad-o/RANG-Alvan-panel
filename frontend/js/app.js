// راه‌اندازی: اطلاعات کاربر، دسترسی منو، مسیریابی و افکت کارت‌ها

$("#welcomeText").textContent = `خوش آمدید، ${user.full_name} — ` +
    new Intl.DateTimeFormat("fa-IR-u-ca-persian", { weekday: "long", year: "numeric", month: "long", day: "numeric" }).format(new Date());
$("#userName").textContent = user.full_name;
$("#userRole").textContent = ROLES[user.role] || user.role;
$("#userAvatar").textContent = (user.full_name || "?").trim().charAt(0);
$("#logoutBtn").addEventListener("click", logout);

// منوهایی که فقط برای نقش بالاتر هستند (دسترسی واقعی را بک‌اند کنترل می‌کند)
$$("[data-min]").forEach(el => { el.hidden = !atLeast(el.dataset.min); });

function route() {
    const name = (location.hash.match(/^#\/(\w+)/) || [])[1];
    let view = views[name] ? name : "overview";
    const link = $(`.nav-link[data-view="${view}"]`);
    if (link && link.hidden) view = "overview";

    $$(".view").forEach(v => v.classList.toggle("active", v.id === `view-${view}`));
    $$(".nav-link").forEach(a => a.classList.toggle("active", a.dataset.view === view));
    window.scrollTo({ top: 0 });

    // نمای کلی همیشه تازه می‌شود؛ بقیه فقط بار اول یا بعد از تغییر داده‌ها
    if (view === "overview" || !visited.has(view) || stale.has(view)) {
        visited.add(view);
        stale.delete(view);
        views[view]();
    }
}
window.addEventListener("hashchange", route);

// تیلت سه‌بعدی ملایم روی کارت‌های آمار (فقط با موس، نه لمسی)
if (!matchMedia("(prefers-reduced-motion: reduce)").matches && matchMedia("(hover: hover)").matches) {
    $$("[data-tilt]").forEach(card => {
        card.addEventListener("pointermove", e => {
            const r = card.getBoundingClientRect();
            const x = (e.clientX - r.left) / r.width - 0.5;
            const y = (e.clientY - r.top) / r.height - 0.5;
            card.style.transform = `perspective(700px) rotateY(${x * 8}deg) rotateX(${-y * 8}deg) translateY(-3px)`;
        });
        card.addEventListener("pointerleave", () => { card.style.transform = ""; });
    });
}

// آستانهٔ ریسک از تنظیمات (برای رنگ‌بندی امتیازها)؛ شکست آن مانع کار نمی‌شود
apiJson("/settings/").then(s => { Cfg.high = s.high_risk_threshold; }).catch(() => {}).finally(route);
refreshBadges();
