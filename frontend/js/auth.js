// آدرس API از config.js خوانده می‌شود (خالی = هم‌منشأ با Backend)
const API_URL = (window.ENV && window.ENV.API_URL) || "";

if (window.Scenes) Scenes.background(document.getElementById("bgCanvas"));

// هر نقش پنل خودش را دارد: مدیریت/کارمند → داشبورد مدیریتی؛ خریدار و کارگران بخش → پنل کاربری
const INTERNAL_ROLES = ["admin", "manager", "staff"];
const homeFor = role => (INTERNAL_ROLES.includes(role) ? "dashboard.html" : "portal.html");

// کاربری که قبلاً وارد شده است مستقیم به پنل خودش می‌رود
try {
    const saved = JSON.parse(localStorage.getItem("user") || "null");
    if (localStorage.getItem("access_token") && saved) window.location.replace(homeFor(saved.role));
} catch (e) { /* اطلاعات خراب ذخیره‌شده نادیده گرفته می‌شود */ }

document.getElementById("loginForm").addEventListener("submit", async function (e) {
    e.preventDefault();

    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;
    const errorMessage = document.getElementById("errorMessage");
    const button = document.getElementById("loginBtn");

    errorMessage.textContent = "";
    button.disabled = true;
    button.textContent = "در حال ورود...";

    try {
        const response = await fetch(`${API_URL}/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password }),
        });

        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            errorMessage.textContent = typeof data.detail === "string" ? data.detail : "ورود ناموفق بود";
            return;
        }

        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("user", JSON.stringify(data.user));
        window.location.href = homeFor(data.user.role);
    } catch (error) {
        errorMessage.textContent = "خطا در اتصال به سرور. مطمئن شوید Backend روشن است.";
        console.error(error);
    } finally {
        button.disabled = false;
        button.textContent = "ورود";
    }
});
