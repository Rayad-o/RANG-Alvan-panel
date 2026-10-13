// اسکیمای دیتابیس (معادل مدل‌های SQLAlchemy در backend/app/models)
import { boolean, date, index, integer, numeric, pgTable, serial, text, timestamp, varchar } from "drizzle-orm/pg-core";

const ts = (name: string) => timestamp(name, { withTimezone: true, mode: "date" });

export const users = pgTable("users", {
  id: serial().primaryKey(),
  email: varchar({ length: 255 }).notNull().unique(),
  fullName: varchar("full_name", { length: 255 }).notNull(),
  hashedPassword: text("hashed_password").notNull(),
  isActive: boolean("is_active").notNull().default(true),
  role: varchar({ length: 30 }).notNull().default("staff"),
  department: varchar({ length: 100 }),
});

export const financeTransactions = pgTable("finance_transactions", {
  id: serial().primaryKey(),
  type: varchar({ length: 50 }).notNull(),
  amount: numeric({ precision: 18, scale: 2 }).notNull(),
  transactionDate: date("transaction_date"),
  partyName: varchar("party_name", { length: 255 }),
  description: text(),
  needsFollowup: boolean("needs_followup").notNull().default(false),
  createdAt: ts("created_at").notNull().defaultNow(),
});

export const salesInvoices = pgTable("sales_invoices", {
  id: serial().primaryKey(),
  invoiceNumber: varchar("invoice_number", { length: 100 }),
  customerName: varchar("customer_name", { length: 255 }),
  amount: numeric({ precision: 18, scale: 2 }).notNull(),
  remainingAmount: numeric("remaining_amount", { precision: 18, scale: 2 }),
  saleDate: varchar("sale_date", { length: 20 }).notNull(), // تاریخ شمسی مثل 1405/07/02
  status: varchar({ length: 50 }).notNull().default("completed"),
  description: text(),
  createdAt: ts("created_at").notNull().defaultNow(),
}, t => [index("sales_invoices_sale_date_idx").on(t.saleDate)]);

export const accountingExpenses = pgTable("accounting_expenses", {
  id: serial().primaryKey(),
  code: varchar({ length: 100 }).notNull(),
  title: varchar({ length: 255 }).notNull(),
  debitTurnover: numeric("debit_turnover", { precision: 18, scale: 2 }).notNull().default("0"),
  creditTurnover: numeric("credit_turnover", { precision: 18, scale: 2 }).notNull().default("0"),
  debitBalance: numeric("debit_balance", { precision: 18, scale: 2 }).notNull().default("0"),
  creditBalance: numeric("credit_balance", { precision: 18, scale: 2 }).notNull().default("0"),
  periodLabel: varchar("period_label", { length: 100 }),
  createdAt: ts("created_at").notNull().defaultNow(),
});

export const inventoryItems = pgTable("inventory_items", {
  id: serial().primaryKey(),
  code: varchar({ length: 100 }).notNull(),
  title: varchar({ length: 255 }).notNull(),
  quantity: numeric({ precision: 18, scale: 4 }).notNull().default("0"),
  createdAt: ts("created_at").notNull().defaultNow(),
});

export const suppliers = pgTable("suppliers", {
  id: serial().primaryKey(),
  code: varchar({ length: 30 }).notNull().unique(),
  name: varchar({ length: 255 }).notNull(),
  category: varchar({ length: 100 }),
  bankAccount: varchar("bank_account", { length: 60 }),
  bankChangedAt: ts("bank_changed_at"),
  bankChangedBy: varchar("bank_changed_by", { length: 100 }),
  bankVerified: boolean("bank_verified").notNull().default(true),
  isHighRisk: boolean("is_high_risk").notNull().default(false),
  createdAt: ts("created_at").notNull().defaultNow(),
});

export const paymentRequests = pgTable("payment_requests", {
  id: serial().primaryKey(),
  ref: varchar({ length: 20 }),
  supplierId: integer("supplier_id").references(() => suppliers.id),
  partyName: varchar("party_name", { length: 255 }).notNull(),
  description: varchar({ length: 500 }),
  poRef: varchar("po_ref", { length: 50 }),
  amount: numeric({ precision: 18, scale: 2 }).notNull(),
  riskScore: integer("risk_score").notNull().default(0),
  riskReasons: text("risk_reasons").notNull().default("[]"), // JSON
  status: varchar({ length: 20 }).notNull().default("pending"), // pending/approved/stopped
  createdBy: varchar("created_by", { length: 100 }),
  decidedBy: varchar("decided_by", { length: 100 }),
  decidedAt: ts("decided_at"),
  decisionNote: text("decision_note"),
  createdAt: ts("created_at").notNull().defaultNow(),
}, t => [index("payment_requests_status_idx").on(t.status), index("payment_requests_created_at_idx").on(t.createdAt)]);

export const purchaseInvoices = pgTable("purchase_invoices", {
  id: serial().primaryKey(),
  number: varchar({ length: 50 }).notNull(),
  supplierId: integer("supplier_id").references(() => suppliers.id),
  supplierName: varchar("supplier_name", { length: 255 }).notNull(),
  poNumber: varchar("po_number", { length: 50 }),
  orderedQty: numeric("ordered_qty", { precision: 18, scale: 3 }),
  receivedQty: numeric("received_qty", { precision: 18, scale: 3 }).notNull().default("0"),
  invoicedQty: numeric("invoiced_qty", { precision: 18, scale: 3 }).notNull().default("0"),
  unit: varchar({ length: 20 }).notNull().default("kg"),
  amount: numeric({ precision: 18, scale: 2 }).notNull(),
  status: varchar({ length: 20 }).notNull().default("matched"), // matched/review/mismatch/resolved
  note: text(),
  createdAt: ts("created_at").notNull().defaultNow(),
}, t => [index("purchase_invoices_po_number_idx").on(t.poNumber)]);

export const tasks = pgTable("tasks", {
  id: serial().primaryKey(),
  unit: varchar({ length: 100 }).notNull(),
  title: varchar({ length: 500 }).notNull(),
  owner: varchar({ length: 100 }).notNull(),
  priority: varchar({ length: 20 }).notNull().default("medium"), // critical/high/medium/low
  dueAt: ts("due_at").notNull(),
  status: varchar({ length: 20 }).notNull().default("open"), // open/done
  completedAt: ts("completed_at"),
  createdAt: ts("created_at").notNull().defaultNow(),
});

export const appSettings = pgTable("app_settings", {
  key: varchar({ length: 50 }).primaryKey(),
  value: text().notNull(), // JSON
});

// کلیدهای داخلی (مثلاً کلید امضای توکن) — جدا از app_settings که به کاربران نمایش داده می‌شود
export const appSecrets = pgTable("app_secrets", {
  key: varchar({ length: 50 }).primaryKey(),
  value: text().notNull(),
});

export const activityLog = pgTable("activity_log", {
  id: serial().primaryKey(),
  createdAt: ts("created_at").notNull().defaultNow(),
  actor: varchar({ length: 100 }).notNull(),
  action: varchar({ length: 50 }).notNull(),
  entity: varchar({ length: 50 }),
  detail: text(),
}, t => [index("activity_log_created_at_idx").on(t.createdAt)]);

export const departments = pgTable("departments", {
  id: serial().primaryKey(),
  name: varchar({ length: 100 }).notNull().unique(),
  createdAt: ts("created_at").notNull().defaultNow(),
});

export const buyerDebts = pgTable("buyer_debts", {
  id: serial().primaryKey(),
  buyerId: integer("buyer_id").notNull().references(() => users.id),
  amount: numeric({ precision: 18, scale: 2 }).notNull(),
  paidAmount: numeric("paid_amount", { precision: 18, scale: 2 }).notNull().default("0"),
  description: varchar({ length: 500 }),
  dueDate: date("due_date"),
  status: varchar({ length: 20 }).notNull().default("open"), // open / paid / voided
  createdBy: varchar("created_by", { length: 100 }),
  voidNote: text("void_note"),
  createdAt: ts("created_at").notNull().defaultNow(),
}, t => [index("buyer_debts_buyer_id_idx").on(t.buyerId)]);

export const debtPayments = pgTable("debt_payments", {
  id: serial().primaryKey(),
  debtId: integer("debt_id").notNull().references(() => buyerDebts.id),
  amount: numeric({ precision: 18, scale: 2 }).notNull(),
  note: varchar({ length: 500 }),
  recordedBy: varchar("recorded_by", { length: 100 }),
  paidAt: ts("paid_at").notNull().defaultNow(),
});

export const purchaseRequests = pgTable("purchase_requests", {
  id: serial().primaryKey(),
  ref: varchar({ length: 20 }),
  buyerId: integer("buyer_id").notNull().references(() => users.id),
  note: varchar({ length: 1000 }),
  // submitted / forwarded / assigned / in_progress / done / rejected / cancelled
  status: varchar({ length: 20 }).notNull().default("submitted"),
  department: varchar({ length: 100 }),
  assignedToId: integer("assigned_to_id").references(() => users.id),
  decisionNote: text("decision_note"),
  createdAt: ts("created_at").notNull().defaultNow(),
  updatedAt: ts("updated_at").notNull().defaultNow(),
}, t => [index("purchase_requests_buyer_id_idx").on(t.buyerId), index("purchase_requests_status_idx").on(t.status)]);

export const purchaseRequestItems = pgTable("purchase_request_items", {
  id: serial().primaryKey(),
  requestId: integer("request_id").notNull().references(() => purchaseRequests.id),
  productId: integer("product_id").references(() => inventoryItems.id),
  productCode: varchar("product_code", { length: 100 }).notNull(),
  productTitle: varchar("product_title", { length: 255 }).notNull(),
  quantity: numeric({ precision: 18, scale: 3 }).notNull(),
}, t => [index("purchase_request_items_request_id_idx").on(t.requestId)]);

export const requestEvents = pgTable("request_events", {
  id: serial().primaryKey(),
  requestId: integer("request_id").notNull().references(() => purchaseRequests.id),
  at: ts("at").notNull().defaultNow(),
  actor: varchar({ length: 100 }).notNull(),
  action: varchar({ length: 30 }).notNull(),
  note: text(),
}, t => [index("request_events_request_id_idx").on(t.requestId)]);
