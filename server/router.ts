// مسیریاب سادهٔ API: هر مسیر نقش‌های مجاز و کد وضعیت خودش را دارد
import { checkRole, currentUser, type User } from "./auth.js";
import { HttpError, json } from "./http.js";

export interface Ctx {
  req: Request;
  url: URL;
  params: Record<string, string>;
  user: User; // برای مسیرهای public مقدار ندارد
}

type Handler = (ctx: Ctx) => Promise<unknown>;

interface Route {
  method: string;
  parts: string[];
  handler: Handler;
  roles?: readonly string[];
  isPublic: boolean;
  status: number;
}

export interface RouteOpts {
  roles?: readonly string[];
  public?: boolean;
  status?: number;
}

const split = (path: string) => path.split("/").filter(Boolean);

export class Router {
  private routes: Route[] = [];

  /** prefixRoles: نقش‌هایی که برای همهٔ مسیرهای این بخش لازم است (مثل داشبورد مدیریتی) */
  constructor(private prefixRoles?: readonly string[]) {}

  add(method: string, path: string, handler: Handler, opts: RouteOpts = {}) {
    this.routes.push({ method, parts: split(path), handler, roles: opts.roles, isPublic: !!opts.public, status: opts.status ?? 200 });
    return this;
  }

  get = (path: string, h: Handler, o?: RouteOpts) => this.add("GET", path, h, o);
  post = (path: string, h: Handler, o?: RouteOpts) => this.add("POST", path, h, o);
  put = (path: string, h: Handler, o?: RouteOpts) => this.add("PUT", path, h, o);
  patch = (path: string, h: Handler, o?: RouteOpts) => this.add("PATCH", path, h, o);

  match(method: string, pathname: string): { route: Route; params: Record<string, string> } | "method" | null {
    const parts = split(pathname);
    let methodMismatch = false;
    for (const route of this.routes) {
      if (route.parts.length !== parts.length) continue;
      const params: Record<string, string> = {};
      const ok = route.parts.every((p, i) => {
        if (p.startsWith(":")) {
          params[p.slice(1)] = decodeURIComponent(parts[i]);
          return true;
        }
        return p === parts[i];
      });
      if (!ok) continue;
      if (route.method !== method) {
        methodMismatch = true;
        continue;
      }
      return { route, params };
    }
    return methodMismatch ? "method" : null;
  }

  async run(req: Request, url: URL, found: { route: Route; params: Record<string, string> }) {
    const { route, params } = found;
    // پارامتر عددی مسیر (مثل /payments/12/approve)
    for (const [k, v] of Object.entries(params)) {
      if (k.endsWith("id") && !/^\d+$/.test(v)) throw new HttpError(422, `شناسهٔ «${k}» نامعتبر است`);
    }
    let user = undefined as unknown as User;
    if (!route.isPublic) {
      user = await currentUser(req);
      if (this.prefixRoles) checkRole(user, this.prefixRoles);
      if (route.roles) checkRole(user, route.roles);
    }
    const result = await route.handler({ req, url, params, user });
    return result instanceof Response ? result : json(result ?? null, route.status);
  }
}

export async function dispatch(req: Request, routers: Router[]): Promise<Response> {
  const url = new URL(req.url);
  try {
    let methodMismatch = false;
    for (const router of routers) {
      const found = router.match(req.method, url.pathname);
      if (found === "method") methodMismatch = true;
      else if (found) return await router.run(req, url, found);
    }
    return methodMismatch ? json({ detail: "Method Not Allowed" }, 405) : json({ detail: "Not Found" }, 404);
  } catch (err) {
    if (err instanceof HttpError) {
      const headers: Record<string, string> = err.status === 401 ? { "WWW-Authenticate": "Bearer" } : {};
      const res = json({ detail: err.detail }, err.status);
      Object.entries(headers).forEach(([k, v]) => res.headers.set(k, v));
      return res;
    }
    console.error(err);
    return json({ detail: "خطای داخلی سرور" }, 500);
  }
}
