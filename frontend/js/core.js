// هستهٔ مشترک داشبورد: احراز هویت، درخواست API، ابزارهای قالب‌بندی، مودال و لیست‌های جدول‌دار
const API_URL = (window.ENV && window.ENV.API_URL) || "";

const token = localStorage.getItem("access_token");
const user = JSON.parse(localStorage.getItem("user") || "null");

function logout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user");
    window.location.replace("index.html");
}

if (!token || !user) {
    logout();
    throw new Error("unauthenticated");  // جلوگیری از اجرای ادامهٔ اسکریپت تا انجام ریدایرکت
}

// هر پنل فقط برای نقش‌های خودش: داشبورد مدیریتی ↔ پنل خریدار/کارگران
const INTERNAL_ROLES = ["admin", "manager", "staff"];
// Netlify نشانی‌ها را بدون پسوند هم سرو می‌کند (/portal) پس پسوند .html را نادیده می‌گیریم
const PAGE = location.pathname.split("/").pop().replace(/\.html$/, "");
if ((PAGE === "dashboard" && !INTERNAL_ROLES.includes(user.role)) ||
    (PAGE === "portal" && user.role === "staff")) {
    location.replace(PAGE === "dashboard" ? "portal.html" : "dashboard.html");
    throw new Error("wrong-panel");
}

// ---------------------------------------------------------------------------
// ابزارهای عمومی
// ---------------------------------------------------------------------------
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

const fa = new Intl.NumberFormat("fa-IR", { maximumFractionDigits: 2 });
const faShort = new Intl.NumberFormat("fa-IR", { maximumFractionDigits: 1 });

const fmt = n => fa.format(Number(n) || 0);
const toFaDigits = s => String(s ?? "").replace(/\d/g, d => "۰۱۲۳۴۵۶۷۸۹"[d]);

function fmtShort(n) {
    const v = Number(n) || 0;
    const a = Math.abs(v);
    if (a >= 1e12) return faShort.format(v / 1e12) + " تریلیون";
    if (a >= 1e9) return faShort.format(v / 1e9) + " میلیارد";
    if (a >= 1e6) return faShort.format(v / 1e6) + " میلیون";
    if (a >= 1e3) return faShort.format(v / 1e3) + " هزار";
    return fmt(v);
}

// ورودی عددی کاربر (ارقام فارسی/عربی، جداکننده هزارگان) → عدد
function parseNum(text) {
    const latin = String(text ?? "")
        .replace(/[۰-۹]/g, d => "۰۱۲۳۴۵۶۷۸۹".indexOf(d))
        .replace(/[٠-٩]/g, d => "٠١٢٣٤٥٦٧٨٩".indexOf(d))
        .replace(/[,٬،\s]/g, "")
        .replace("٫", ".");
    const n = Number(latin);
    return latin !== "" && Number.isFinite(n) ? n : NaN;
}

// متن‌های دیتابیس (مثلاً نام مشتری از اکسل) را قبل از قرار دادن در HTML امن می‌کنیم
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const MONTHS = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"];
const monthName = ym => MONTHS[(parseInt(String(ym).slice(5, 7), 10) || 1) - 1];

function todayJalali() {
    const parts = new Intl.DateTimeFormat("en-US-u-ca-persian-nu-latn", {
        year: "numeric", month: "2-digit", day: "2-digit",
    }).formatToParts(new Date());
    const get = type => parts.find(p => p.type === type).value;
    return `${get("year")}/${get("month")}/${get("day")}`;
}

// تاریخ/زمان ISO سرور (UTC) → متن شمسی
function fmtDate(iso, withTime = false) {
    if (!iso) return "—";
    const d = new Date(iso);
    if (isNaN(d)) return "—";
    const opts = { year: "numeric", month: "2-digit", day: "2-digit" };
    if (withTime) Object.assign(opts, { hour: "2-digit", minute: "2-digit" });
    return new Intl.DateTimeFormat("fa-IR-u-ca-persian", opts).format(d);
}

// زمان نسبی کوتاه: «۲ روز تأخیر» / «۴ ساعت دیگر»
function relDue(iso) {
    const diff = new Date(iso) - Date.now();
    const abs = Math.abs(diff);
    const h = Math.round(abs / 36e5);
    const text = h < 1 ? "کمتر از ۱ ساعت" : h < 48 ? `${fmt(h)} ساعت` : `${fmt(Math.round(h / 24))} روز`;
    return diff < 0 ? `${text} تأخیر` : `${text} دیگر`;
}

const ROLES = {
    admin: "مدیر سیستم", manager: "مدیر", staff: "کارمند اداری",
    buyer: "خریدار", accountant: "حسابدار", dept_head: "رییس بخش", dept_staff: "کارکن بخش",
};
const ROLE_RANK = { staff: 0, manager: 1, admin: 2 };
const atLeast = role => (ROLE_RANK[user.role] ?? -1) >= (ROLE_RANK[role] ?? 99);

let toastTimer;
function toast(message, isError = false) {
    const el = $("#toast");
    el.textContent = message;
    el.classList.toggle("err", isError);
    el.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove("show"), 3500);
}

function debounce(fn, ms = 300) {
    let t;
    return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------
// درخواست احراز هویت‌شده. برای FormData هدر Content-Type را مرورگر خودش (با boundary) می‌گذارد.
async function apiFetch(path, options = {}) {
    const headers = new Headers(options.headers || {});
    headers.set("Authorization", `Bearer ${token}`);
    if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
        headers.set("Content-Type", "application/json");
    }

    const response = await fetch(`${API_URL}${path}`, { ...options, headers });

    if (response.status === 401) {
        logout();
        throw new Error("نشست منقضی شده است");
    }
    return response;
}

function errorText(data, fallback) {
    if (!data || !data.detail) return fallback;
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail)) return data.detail.map(d => d.msg).join("؛ ") || fallback;
    return fallback;
}

async function apiJson(path) {
    const response = await apiFetch(path);
    const data = await response.json().catch(() => null);
    if (!response.ok) throw new Error(errorText(data, "خطا در دریافت اطلاعات"));
    return data;
}

async function apiSend(method, path, body) {
    const response = await apiFetch(path, { method, body: body === undefined ? undefined : JSON.stringify(body) });
    const data = await response.json().catch(() => null);
    if (!response.ok) throw new Error(errorText(data, "انجام عملیات ناموفق بود"));
    return data;
}

// ---------------------------------------------------------------------------
// مودال
// ---------------------------------------------------------------------------
const Modal = {
    open(title, html) {
        const back = $("#modalBack");
        $("#modalTitle").textContent = title;
        const body = $("#modalBody");
        body.innerHTML = html;
        back.classList.add("show");
        const first = $("input, select, textarea", body);
        if (first) first.focus();
        return body;
    },
    close() { $("#modalBack").classList.remove("show"); },
};
$("#modalBack").addEventListener("click", e => { if (e.target.id === "modalBack") Modal.close(); });
$("#modalClose").addEventListener("click", Modal.close);
document.addEventListener("keydown", e => { if (e.key === "Escape") Modal.close(); });

// فرم کوچک: برچسب + ورودی
const field = (label, input, full = false) =>
    `<label class="fld${full ? " full" : ""}"><span>${label}</span>${input}</label>`;

// دکمهٔ «ارسال» در مودال: وضعیت در حال انجام را مدیریت و خطا را نمایش می‌دهد
async function submitForm(button, errorBox, action) {
    button.disabled = true;
    errorBox.textContent = "";
    try {
        await action();
    } catch (err) {
        errorBox.textContent = err.message;
    } finally {
        button.disabled = false;
    }
}

// ---------------------------------------------------------------------------
// نماها و ناوبری
// ---------------------------------------------------------------------------
const views = {};            // name → تابع بارگذاری
const stale = new Set();     // نماهایی که باید دوباره لود شوند
const visited = new Set();

function registerView(name, load) { views[name] = load; }
function invalidate(...names) { names.forEach(n => stale.add(n)); }

// ---------------------------------------------------------------------------
// لیست‌های جدول‌دار (جستجو + صفحه‌بندی + اقدام روی ردیف)
// ---------------------------------------------------------------------------
function createList({ endpoint, body, search, more, pageSize, extraParams, row, columns, onAction }) {
    const tbody = $(body);
    const moreBtn = more ? $(more) : null;
    const items = new Map();
    let offset = 0;
    let ticket = 0;

    async function load(append) {
        const mine = ++ticket;
        if (!append) {
            offset = 0;
            items.clear();
            tbody.innerHTML = `<tr><td colspan="${columns}" class="empty">در حال بارگذاری...</td></tr>`;
        }
        const params = new URLSearchParams({ limit: pageSize, offset });
        const q = search ? $(search).value.trim() : "";
        if (q) params.set("q", q);
        Object.entries(extraParams ? extraParams() : {}).forEach(([k, v]) => v && params.set(k, v));

        try {
            const list = await apiJson(`${endpoint}?${params}`);
            if (mine !== ticket) return;  // نتیجهٔ جستجوی قدیمی‌تر را دور بریز

            list.forEach(it => items.set(String(it.id), it));
            const html = list.map(row).join("");
            if (append) tbody.insertAdjacentHTML("beforeend", html);
            else tbody.innerHTML = html || `<tr><td colspan="${columns}" class="empty">موردی یافت نشد</td></tr>`;

            offset += list.length;
            if (moreBtn) moreBtn.hidden = list.length < pageSize;
        } catch (err) {
            if (mine !== ticket) return;
            tbody.innerHTML = `<tr><td colspan="${columns}" class="empty">${esc(err.message)}</td></tr>`;
        }
    }

    if (search) $(search).addEventListener("input", debounce(() => load(false)));
    if (moreBtn) moreBtn.addEventListener("click", () => load(true));
    if (onAction) {
        tbody.addEventListener("click", e => {
            const btn = e.target.closest("[data-act]");
            if (!btn) return;
            const item = items.get(btn.dataset.id);
            if (item) onAction(btn.dataset.act, item, btn);
        });
    }
    return { reload: () => load(false), items };
}

// کنترل‌های segmented (فیلتر وضعیت)؛ مقدار انتخابی را برمی‌گرداند و روی تغییر callback می‌زند
function segmented(selector, onChange) {
    const box = $(selector);
    let value = ($("button.on", box) || {}).dataset?.value ?? "";
    box.addEventListener("click", e => {
        const btn = e.target.closest("button");
        if (!btn) return;
        value = btn.dataset.value;
        $$("button", box).forEach(b => b.classList.toggle("on", b === btn));
        onChange(value);
    });
    return () => value;
}

// دانلود CSV (با BOM تا اکسل فارسی را درست باز کند)
function downloadCSV(filename, columns, rows) {
    const cell = v => `"${String(v ?? "").replace(/"/g, '""')}"`;
    const csv = [columns.map(c => cell(c.title)).join(",")]
        .concat(rows.map(r => columns.map(c => cell(c.value(r))).join(",")))
        .join("\r\n");
    const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}

// ---------------------------------------------------------------------------
// ریسک و برچسب‌ها (مشترک بین نماها)
// ---------------------------------------------------------------------------
const Cfg = { high: 70 };  // آستانهٔ ریسک بالا؛ بعد از ورود از /settings به‌روز می‌شود
const riskClass = s => (s >= Cfg.high ? "red" : s >= 40 ? "orange" : "green");
const RISK_VAR = { red: "var(--danger)", orange: "var(--warn)", green: "var(--accent)" };

const PAY_STATUS = { pending: ["نیازمند بررسی", "orange"], approved: ["تأییدشده", "green"], stopped: ["متوقف", "red"] };
const INV_STATUS = { matched: ["تأییدشده", "green"], review: ["بررسی", "orange"], mismatch: ["مغایرت", "red"], resolved: ["رفع‌شده", "blue"] };
const TASK_STATUS = { open: ["در حال انجام", "blue"], overdue: ["عقب‌افتاده", "orange"], done: ["تکمیل", "green"] };
const PRIORITY = { critical: ["بحرانی", "red"], high: ["بالا", "orange"], medium: ["متوسط", "blue"], low: ["پایین", "gray"] };

const badge = (pair, text) => `<span class="badge ${pair[1]}">${esc(text ?? pair[0])}</span>`;
