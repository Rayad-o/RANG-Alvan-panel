// خواندن فایل‌های اکسل/CSV آپلودشده و پاک‌سازی مقادیر (معادل backend/app/core/excel.py)
import * as XLSX from "xlsx";

import { fail } from "./http.js";

const ALLOWED_SUFFIXES = [".xlsx", ".xls", ".xlsm", ".csv"];

export type Row = Record<string, unknown>;
export interface Table { columns: string[]; rows: Row[] }

/** حروف عربی → فارسی و یکسان‌سازی فاصله‌ها برای مقایسهٔ نام ستون‌ها */
export const normalizePersian = (text: string) =>
  text.replace(/ي/g, "ی").replace(/ك/g, "ک").replace(/‌/g, " ").replace(/ /g, " ").trim();

const toLatinDigits = (s: string) =>
  s.replace(/[۰-۹]/g, d => String("۰۱۲۳۴۵۶۷۸۹".indexOf(d))).replace(/[٠-٩]/g, d => String("٠١٢٣٤٥٦٧٨٩".indexOf(d)));

const isNa = (v: unknown) => v === null || v === undefined || (typeof v === "number" && Number.isNaN(v));

/** متن تمیزشده یا null اگر خالی باشد */
export function cleanText(v: unknown): string | null {
  if (isNa(v)) return null;
  const text = String(v).trim();
  if (!text || text.toLowerCase() === "nan") return null;
  return text;
}

/**
 * تبدیل مقدار خام اکسل به عدد: ارقام فارسی/عربی، جداکنندهٔ هزارگان، اعشار فارسی و
 * اعداد منفی حسابداری مثل (1,234) و 1234- . مقدار نامعتبر صفر می‌شود.
 */
export function cleanAmount(v: unknown): number {
  if (typeof v === "boolean" || isNa(v)) return 0;
  if (typeof v === "number") return Number.isFinite(v) ? v : 0;

  let text = String(v).trim();
  if (!text) return 0;
  text = toLatinDigits(text).replace(/[,٬،\s ‌]/g, "").replace(/٫/g, ".");

  let negative = false;
  if (text.startsWith("(") && text.endsWith(")")) {
    negative = true;
    text = text.slice(1, -1);
  }
  if (text.endsWith("-")) {
    negative = true;
    text = text.slice(0, -1);
  }
  if (text.startsWith("-")) {
    negative = true;
    text = text.slice(1);
  }
  if (text.startsWith("+")) text = text.slice(1);

  text = text.replace(/[^\d.]/g, "");
  if (!text || text === "." || !/^\d*\.?\d*$/.test(text)) return 0;
  const n = Number(text);
  if (!Number.isFinite(n)) return 0;
  return negative ? -n : n;
}

/** تاریخ شمسی به قالب ثابت YYYY/MM/DD (ورودی‌هایی مثل 1405/7/2، 1405-07-02، 14050702) یا null */
export function cleanJalaliDate(v: unknown): string | null {
  if (typeof v === "boolean" || isNa(v)) return null;

  let digits: string;
  if (typeof v === "number") {
    if (!Number.isInteger(v)) return null;
    digits = String(v).padStart(8, "0");
  } else {
    const text = toLatinDigits(String(v)).trim();
    const parts = text.split(/\D+/).filter(Boolean);
    if (parts.length >= 3 && parts[0].length === 4) {
      digits = `${parts[0]}${parts[1].padStart(2, "0")}${parts[2].slice(0, 2).padStart(2, "0")}`;
    } else {
      digits = parts.join("");
    }
  }
  if (digits.length < 8) return null;

  const [y, m, d] = [digits.slice(0, 4), digits.slice(4, 6), digits.slice(6, 8)];
  if (![y, m, d].every(p => /^\d+$/.test(p))) return null;
  const year = Number(y), month = Number(m), day = Number(d);
  // سال شمسی حدود ۱۴۰۰ است؛ اعداد بزرگ‌تر یعنی تاریخ میلادی که ذخیره نمی‌شود
  if (!(year >= 1200 && year <= 1600)) return null;
  if (!(month >= 1 && month <= 12 && day >= 1 && day <= 31)) return null;
  return `${y}/${m}/${d}`;
}

function toTable(matrix: unknown[][]): Table {
  // سطر هدر: اولین سطری که بیش از یک سلول پر دارد (عنوان‌های بالای جدول رد می‌شوند)
  const filled = (r: unknown[]) => r.filter(v => !isNa(v) && v !== "").length;
  let headerIdx = matrix.findIndex(r => filled(r) > 1);
  if (headerIdx < 0) headerIdx = 0;
  const headerRow = matrix[headerIdx] ?? [];
  const width = Math.max(headerRow.length, ...matrix.slice(headerIdx + 1).map(r => r.length), 0);

  const columns: string[] = [];
  for (let i = 0; i < width; i++) {
    const v = headerRow[i];
    columns.push(isNa(v) || v === "" ? `ستون${i + 1}` : normalizePersian(String(v)));
  }
  const rows = matrix.slice(headerIdx + 1).map(r => {
    const row: Row = {};
    columns.forEach((c, i) => { if (!(c in row) || isNa(row[c])) row[c] = r[i] ?? null; });
    return row;
  });
  return { columns, rows };
}

/** فایل اکسل/CSV را از فرم آپلود (فیلد file) می‌خواند */
export async function readTabularFile(req: Request): Promise<Table> {
  let form: FormData;
  try {
    form = await req.formData();
  } catch {
    return fail(400, "فایل ارسال نشده است");
  }
  const file = form.get("file");
  if (!file || typeof file === "string" || !file.name) return fail(400, "فایل ارسال نشده است");

  const filename = file.name.toLowerCase();
  if (!ALLOWED_SUFFIXES.some(s => filename.endsWith(s))) fail(400, "فقط فایل Excel یا CSV مجاز است");

  const content = Buffer.from(await file.arrayBuffer());
  if (!content.length) fail(400, "فایل خالی است");

  let matrix: unknown[][];
  try {
    const isCsv = filename.endsWith(".csv");
    // raw برای CSV: متن‌ها (مثل تاریخ شمسی) خودکار به تاریخ میلادی تبدیل نشوند
    const wb = isCsv
      ? XLSX.read(content.toString("utf8").replace(/^﻿/, ""), { type: "string", raw: true })
      : XLSX.read(content, { type: "buffer" });
    const sheet = wb.Sheets[wb.SheetNames[0]];
    if (!sheet) throw new Error("جدولی در فایل پیدا نشد");
    matrix = XLSX.utils.sheet_to_json<unknown[]>(sheet, { header: 1, defval: null, raw: true, blankrows: false });
  } catch (err) {
    return fail(400, `خواندن فایل ناموفق بود: ${(err as Error).message}`);
  }
  if (!matrix.length) fail(400, "خواندن فایل ناموفق بود: جدولی در فایل پیدا نشد");
  return toTable(matrix);
}

/** تغییر نام ستون‌ها طبق نگاشت داده‌شده (ستون‌های ناشناخته دست‌نخورده می‌مانند) */
export function mapColumns(table: Table, map: Record<string, string>): Table {
  const rename = (c: string) => map[c] ?? c;
  return {
    columns: table.columns.map(rename),
    rows: table.rows.map(r => {
      const out: Row = {};
      for (const [k, v] of Object.entries(r)) {
        const key = rename(k);
        if (!(key in out) || isNa(out[key])) out[key] = v;
      }
      return out;
    }),
  };
}

export function requireColumns(table: Table, required: string[]) {
  const missing = required.filter(c => !table.columns.includes(c));
  if (missing.length) {
    fail(400, `ستون‌های ضروری یافت نشد: ${JSON.stringify(missing)}. ستون‌های فایل: ${JSON.stringify(table.columns)}`);
  }
}

/** درج دسته‌ای ردیف‌ها (برای فایل‌های بزرگ در چند بخش) */
export async function insertChunks<T>(rows: T[], insert: (chunk: T[]) => Promise<unknown>, size = 500) {
  for (let i = 0; i < rows.length; i += size) await insert(rows.slice(i, i + size));
}
