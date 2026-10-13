// احراز هویت: توکن JWT (HS256)، هش رمز با bcrypt و کنترل نقش‌ها
import { createHmac, randomBytes, timingSafeEqual } from "node:crypto";
import bcrypt from "bcryptjs";
import { eq } from "drizzle-orm";

import { db } from "../db/index.js";
import { appSecrets, users } from "../db/schema.js";
import { fail, HttpError } from "./http.js";

export type User = typeof users.$inferSelect;

export const INTERNAL_ROLES = ["admin", "manager", "staff"] as const;
export const DEPARTMENT_ROLES = ["dept_head", "dept_staff"] as const;
export const ALL_ROLES = ["admin", "manager", "staff", "buyer", "accountant", "dept_head", "dept_staff"] as const;

const TOKEN_TTL_SECONDS = 60 * 60 * 24; // ۲۴ ساعت

// ---------------------------------------------------------------------------
// رمز عبور (bcrypt فقط ۷۲ بایت اول را در نظر می‌گیرد؛ هش‌های $2b$ پایتونی هم معتبرند)
// ---------------------------------------------------------------------------
const prepare = (password: string) => Buffer.from(password, "utf8").subarray(0, 72).toString("utf8");

export const hashPassword = (password: string) => bcrypt.hash(prepare(password), 12);

export async function verifyPassword(plain: string, hashed: string | null | undefined): Promise<boolean> {
  if (!hashed) return false;
  try {
    return await bcrypt.compare(prepare(plain), hashed);
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------------------
// کلید امضای توکن: از متغیر محیطی SECRET_KEY، وگرنه یک کلید تصادفی که یک بار در دیتابیس ذخیره می‌شود
// ---------------------------------------------------------------------------
let secretCache: string | undefined;

async function secretKey(): Promise<string> {
  if (secretCache) return secretCache;
  const fromEnv = Netlify.env.get("SECRET_KEY");
  if (fromEnv) return (secretCache = fromEnv);

  await db.insert(appSecrets).values({ key: "jwt_secret", value: randomBytes(48).toString("base64url") }).onConflictDoNothing();
  const [row] = await db.select().from(appSecrets).where(eq(appSecrets.key, "jwt_secret"));
  return (secretCache = row.value);
}

const b64 = (data: string | Buffer) => Buffer.from(data).toString("base64url");

export async function createAccessToken(payload: Record<string, unknown>): Promise<string> {
  const now = Math.floor(Date.now() / 1000);
  const header = b64(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const body = b64(JSON.stringify({ ...payload, iat: now, exp: now + TOKEN_TTL_SECONDS }));
  const sig = createHmac("sha256", await secretKey()).update(`${header}.${body}`).digest("base64url");
  return `${header}.${body}.${sig}`;
}

async function decodeToken(token: string): Promise<Record<string, unknown> | null> {
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  const [header, body, sig] = parts;
  const expected = createHmac("sha256", await secretKey()).update(`${header}.${body}`).digest();
  const given = Buffer.from(sig, "base64url");
  if (given.length !== expected.length || !timingSafeEqual(given, expected)) return null;
  try {
    const head = JSON.parse(Buffer.from(header, "base64url").toString());
    if (head.alg !== "HS256") return null;
    const payload = JSON.parse(Buffer.from(body, "base64url").toString());
    if (typeof payload.exp !== "number" || payload.exp < Date.now() / 1000) return null;
    return payload;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// کاربر جاری
// ---------------------------------------------------------------------------
export async function optionalUser(req: Request): Promise<User | null> {
  const header = req.headers.get("authorization");
  if (!header) return null;
  return currentUser(req);
}

export async function currentUser(req: Request): Promise<User> {
  const header = req.headers.get("authorization") ?? "";
  const [scheme, token] = header.split(" ");
  if (!token || scheme.toLowerCase() !== "bearer") throw new HttpError(401, "هدر Authorization ارسال نشده است");

  const payload = await decodeToken(token);
  const email = payload?.sub;
  if (typeof email !== "string" || !email) throw new HttpError(401, "توکن نامعتبر است");

  const [user] = await db.select().from(users).where(eq(users.email, email));
  if (!user) throw new HttpError(401, "کاربر یافت نشد");
  // کاربر غیرفعال نباید بتواند از توکن معتبرش استفاده کند
  if (!user.isActive) throw new HttpError(403, "حساب کاربری غیرفعال است");
  return user;
}

export function checkRole(user: User, roles: readonly string[]): User {
  if (!roles.includes(user.role)) fail(403, "دسترسی مجاز نیست");
  return user;
}

export const userOut = (u: User) => ({
  id: u.id, email: u.email, full_name: u.fullName, role: u.role, is_active: u.isActive, department: u.department,
});
