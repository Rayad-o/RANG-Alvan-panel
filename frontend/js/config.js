// تنظیمات اتصال به Backend
// - فرانت‌اند از خود Backend (پورت 8000) یا از Netlify/nginx سرو شود: آدرس خالی = هم‌منشأ
//   (روی Netlify درخواست‌ها با netlify.toml به بک‌اند پراکسی می‌شوند).
// - Live Server یا http.server روی localhost (مثلاً 5500): به Backend روی 8000 وصل می‌شویم.
const isLocalDev = ["localhost", "127.0.0.1"].includes(window.location.hostname) && window.location.port !== "8000";
window.ENV = {
    API_URL: isLocalDev ? "http://127.0.0.1:8000" : "",
};
