// تنظیمات برنامه، دفتر فعالیت و ابزارهای زمان (منطقهٔ زمانی تهران برای «امروز»)
import { eq } from "drizzle-orm";

import { db } from "../db/index.js";
import { activityLog, appSettings, departments } from "../db/schema.js";
import { fail } from "./http.js";
import { DEPARTMENT_ROLES } from "./auth.js";

export const ROLE_RANK: Record<string, number> = { staff: 0, manager: 1, admin: 2 };

export interface Tier { upto: number | null; role: "manager" | "admin" }
export interface AppConfig {
  controls: Record<"risk_score" | "bank_change_alert" | "duplicate_detection" | "three_way_match" | "task_escalation", boolean>;
  approval_tiers: Tier[];
  match_tolerance_pct: number;
  high_risk_threshold: number;
  buyer_debt_limit: number;
}

export const DEFAULTS: AppConfig = {
  // کلیدهای کنترل (قواعد هشدار)
  controls: {
    risk_score: true,
    bank_change_alert: true,
    duplicate_detection: true,
    three_way_match: true,
    task_escalation: true,
  },
  // سقف تأیید: تا مبلغ upto (تومان) حداقل نقش تأییدکننده role است؛ upto=null یعنی بالاتر از همه
  approval_tiers: [
    { upto: 100_000_000, role: "manager" },
    { upto: 500_000_000, role: "manager" },
    { upto: 2_000_000_000, role: "admin" },
    { upto: null, role: "admin" },
  ],
  match_tolerance_pct: 2,
  high_risk_threshold: 70,
  buyer_debt_limit: 20_000_000,
};

export async function getSettings(): Promise<AppConfig> {
  const result: any = structuredClone(DEFAULTS);
  for (const row of await db.select().from(appSettings)) {
    let stored: unknown;
    try {
      stored = JSON.parse(row.value);
    } catch {
      continue;
    }
    const current = result[row.key];
    if (current && typeof current === "object" && !Array.isArray(current) && stored && typeof stored === "object" && !Array.isArray(stored)) {
      Object.assign(current, stored);
    } else {
      result[row.key] = stored;
    }
  }
  return result;
}

export async function saveSettings(values: Record<string, unknown>): Promise<void> {
  for (const [key, value] of Object.entries(values)) {
    const payload = JSON.stringify(value);
    await db.insert(appSettings).values({ key, value: payload }).onConflictDoUpdate({ target: appSettings.key, set: { value: payload } });
  }
}

/** حداقل نقش لازم برای تأیید یک پرداخت (بر اساس مبلغ و امتیاز ریسک) */
export function requiredRole(amount: number | string, cfg: AppConfig, riskScore = 0): string {
  let role = "admin";
  for (const tier of cfg.approval_tiers) {
    if (tier.upto === null || Number(amount) <= Number(tier.upto)) {
      role = tier.role;
      break;
    }
  }
  if (riskScore >= cfg.high_risk_threshold) role = "admin";
  return role;
}

export const roleAllows = (userRole: string, needed: string) => (ROLE_RANK[userRole] ?? -1) >= (ROLE_RANK[needed] ?? 99);

export async function logActivity(actor: string, action: string, entity: string | null = null, detail: string | null = null) {
  await db.insert(activityLog).values({ actor, action, entity, detail });
}

/** رییس و کارکن بخش حتماً باید عضو یکی از بخش‌های ثبت‌شده باشند؛ بقیهٔ نقش‌ها بخش ندارند */
export async function normalizeDepartment(role: string, department: string | null | undefined): Promise<string | null> {
  if (!(DEPARTMENT_ROLES as readonly string[]).includes(role)) return null;
  const name = (department ?? "").trim();
  if (!name) fail(400, "برای رییس بخش و کارکن بخش، انتخاب بخش الزامی است");
  const [exists] = await db.select({ id: departments.id }).from(departments).where(eq(departments.name, name));
  if (!exists) fail(400, "بخش انتخاب‌شده معتبر نیست؛ ابتدا بخش را بسازید");
  return name;
}

// ---------------------------------------------------------------------------
// زمان محلی
// ---------------------------------------------------------------------------
export const TZ = "Asia/Tehran";

/** تاریخ محلی (YYYY-MM-DD) برای یک لحظه */
export function localDate(d: Date = new Date()): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit" }).format(d);
}

function offsetMinutes(at: Date): number {
  const name = new Intl.DateTimeFormat("en-US", { timeZone: TZ, timeZoneName: "longOffset" })
    .formatToParts(at).find(p => p.type === "timeZoneName")?.value ?? "GMT";
  const m = name.match(/GMT([+-])(\d{2}):?(\d{2})?/);
  if (!m) return 0;
  return (m[1] === "-" ? -1 : 1) * (Number(m[2]) * 60 + Number(m[3] ?? 0));
}

/** شروع روز محلی (۰۰:۰۰) به UTC */
export function localDayStart(day: string): Date {
  const utcMidnight = new Date(`${day}T00:00:00Z`);
  return new Date(utcMidnight.getTime() - offsetMinutes(utcMidnight) * 60_000);
}

export function addDays(day: string, n: number): string {
  const d = new Date(`${day}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}
