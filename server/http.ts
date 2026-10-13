// ابزارهای مشترک API: خطا، اعتبارسنجی ورودی و خروجی JSON (معادل رفتار FastAPI/Pydantic قبلی)

export class HttpError extends Error {
  constructor(public status: number, public detail: string) {
    super(detail);
  }
}

export const fail = (status: number, detail: string): never => {
  throw new HttpError(status, detail);
};

export const json = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json; charset=utf-8" } });

export type Body = Record<string, unknown>;

export async function readBody(req: Request, optional = false): Promise<Body> {
  const text = await req.text();
  if (!text.trim()) {
    if (optional) return {};
    return fail(422, "بدنهٔ درخواست خالی است");
  }
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    return fail(422, "بدنهٔ درخواست JSON معتبر نیست");
  }
  if (data === null && optional) return {};
  if (typeof data !== "object" || data === null || Array.isArray(data)) return fail(422, "بدنهٔ درخواست باید یک شیء JSON باشد");
  return data as Body;
}

const has = (b: Body, key: string) => b[key] !== undefined && b[key] !== null;

interface StrOpts { min?: number; max?: number; required?: boolean; label?: string }

/** متن اختیاری/الزامی با کنترل طول؛ مقدار نداده = undefined، null = null */
export function str(b: Body, key: string, o: StrOpts = {}): string | null | undefined {
  const label = o.label ?? key;
  if (!has(b, key)) {
    if (o.required) fail(422, `فیلد «${label}» الزامی است`);
    return b[key] as null | undefined;
  }
  const v = b[key];
  if (typeof v !== "string") return fail(422, `فیلد «${label}» باید متن باشد`);
  if (o.min !== undefined && v.length < o.min) fail(422, `فیلد «${label}» باید حداقل ${o.min} نویسه باشد`);
  if (o.max !== undefined && v.length > o.max) fail(422, `فیلد «${label}» حداکثر ${o.max} نویسه است`);
  return v;
}

export const reqStr = (b: Body, key: string, o: Omit<StrOpts, "required"> = {}) => str(b, key, { ...o, required: true }) as string;

interface NumOpts { gt?: number; ge?: number; le?: number; required?: boolean; int?: boolean; label?: string }

export function num(b: Body, key: string, o: NumOpts = {}): number | null | undefined {
  const label = o.label ?? key;
  if (!has(b, key)) {
    if (o.required) fail(422, `فیلد «${label}» الزامی است`);
    return b[key] as null | undefined;
  }
  const raw = b[key];
  const v = typeof raw === "string" && raw.trim() !== "" ? Number(raw) : raw;
  if (typeof v !== "number" || !Number.isFinite(v)) return fail(422, `فیلد «${label}» باید عدد باشد`);
  if (o.int && !Number.isInteger(v)) fail(422, `فیلد «${label}» باید عدد صحیح باشد`);
  if (o.gt !== undefined && !(v > o.gt)) fail(422, `فیلد «${label}» باید بیشتر از ${o.gt} باشد`);
  if (o.ge !== undefined && !(v >= o.ge)) fail(422, `فیلد «${label}» نباید کمتر از ${o.ge} باشد`);
  if (o.le !== undefined && !(v <= o.le)) fail(422, `فیلد «${label}» نباید بیشتر از ${o.le} باشد`);
  return v;
}

export const reqNum = (b: Body, key: string, o: Omit<NumOpts, "required"> = {}) => num(b, key, { ...o, required: true }) as number;

/** مبلغ با حداکثر ۲ رقم اعشار (معادل Decimal(max_digits=18, decimal_places=2)) به‌صورت متن برای ستون numeric */
export const money = (v: number) => (Math.round(v * 100) / 100).toFixed(2);

export function bool(b: Body, key: string): boolean | undefined {
  if (!has(b, key)) return undefined;
  if (typeof b[key] !== "boolean") return fail(422, `فیلد «${key}» باید true یا false باشد`);
  return b[key] as boolean;
}

export function isoDate(b: Body, key: string): string | null | undefined {
  if (!has(b, key)) return b[key] as null | undefined;
  const v = b[key];
  if (typeof v !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(v) || isNaN(Date.parse(v))) {
    return fail(422, `فیلد «${key}» باید تاریخ به شکل YYYY-MM-DD باشد`);
  }
  return v;
}

export function oneOf<T extends string>(b: Body, key: string, values: readonly T[]): T | undefined {
  if (!has(b, key)) return undefined;
  if (!values.includes(b[key] as T)) return fail(422, `مقدار «${key}» معتبر نیست`);
  return b[key] as T;
}

// پارامترهای کوئری
export function qInt(url: URL, key: string, def: number, min: number, max: number): number {
  const raw = url.searchParams.get(key);
  if (raw === null || raw === "") return def;
  const v = Number(raw);
  if (!Number.isInteger(v) || v < min || v > max) return fail(422, `پارامتر «${key}» باید عددی بین ${min} و ${max} باشد`);
  return v;
}

export function qOptInt(url: URL, key: string): number | undefined {
  const raw = url.searchParams.get(key);
  if (raw === null || raw === "") return undefined;
  const v = Number(raw);
  if (!Number.isInteger(v)) return fail(422, `پارامتر «${key}» باید عدد صحیح باشد`);
  return v;
}

export const qStr = (url: URL, key: string) => {
  const v = url.searchParams.get(key);
  return v === null || v === "" ? undefined : v;
};

/** متن جستجو برای ILIKE (نویسه‌های ویژه escape می‌شوند) */
export const likeOf = (q: string | undefined) =>
  q && q.trim() ? `%${q.trim().replace(/[\\%_]/g, c => "\\" + c)}%` : undefined;

export const toNum = (v: unknown) => Number(v ?? 0) || 0;
