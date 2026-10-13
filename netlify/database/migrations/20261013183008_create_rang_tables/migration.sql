CREATE TABLE "accounting_expenses" (
	"id" serial PRIMARY KEY,
	"code" varchar(100) NOT NULL,
	"title" varchar(255) NOT NULL,
	"debit_turnover" numeric(18,2) DEFAULT '0' NOT NULL,
	"credit_turnover" numeric(18,2) DEFAULT '0' NOT NULL,
	"debit_balance" numeric(18,2) DEFAULT '0' NOT NULL,
	"credit_balance" numeric(18,2) DEFAULT '0' NOT NULL,
	"period_label" varchar(100),
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "activity_log" (
	"id" serial PRIMARY KEY,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"actor" varchar(100) NOT NULL,
	"action" varchar(50) NOT NULL,
	"entity" varchar(50),
	"detail" text
);
--> statement-breakpoint
CREATE TABLE "app_secrets" (
	"key" varchar(50) PRIMARY KEY,
	"value" text NOT NULL
);
--> statement-breakpoint
CREATE TABLE "app_settings" (
	"key" varchar(50) PRIMARY KEY,
	"value" text NOT NULL
);
--> statement-breakpoint
CREATE TABLE "buyer_debts" (
	"id" serial PRIMARY KEY,
	"buyer_id" integer NOT NULL,
	"amount" numeric(18,2) NOT NULL,
	"paid_amount" numeric(18,2) DEFAULT '0' NOT NULL,
	"description" varchar(500),
	"due_date" date,
	"status" varchar(20) DEFAULT 'open' NOT NULL,
	"created_by" varchar(100),
	"void_note" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "debt_payments" (
	"id" serial PRIMARY KEY,
	"debt_id" integer NOT NULL,
	"amount" numeric(18,2) NOT NULL,
	"note" varchar(500),
	"recorded_by" varchar(100),
	"paid_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "departments" (
	"id" serial PRIMARY KEY,
	"name" varchar(100) NOT NULL UNIQUE,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "finance_transactions" (
	"id" serial PRIMARY KEY,
	"type" varchar(50) NOT NULL,
	"amount" numeric(18,2) NOT NULL,
	"transaction_date" date,
	"party_name" varchar(255),
	"description" text,
	"needs_followup" boolean DEFAULT false NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "inventory_items" (
	"id" serial PRIMARY KEY,
	"code" varchar(100) NOT NULL,
	"title" varchar(255) NOT NULL,
	"quantity" numeric(18,4) DEFAULT '0' NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "payment_requests" (
	"id" serial PRIMARY KEY,
	"ref" varchar(20),
	"supplier_id" integer,
	"party_name" varchar(255) NOT NULL,
	"description" varchar(500),
	"po_ref" varchar(50),
	"amount" numeric(18,2) NOT NULL,
	"risk_score" integer DEFAULT 0 NOT NULL,
	"risk_reasons" text DEFAULT '[]' NOT NULL,
	"status" varchar(20) DEFAULT 'pending' NOT NULL,
	"created_by" varchar(100),
	"decided_by" varchar(100),
	"decided_at" timestamp with time zone,
	"decision_note" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "purchase_invoices" (
	"id" serial PRIMARY KEY,
	"number" varchar(50) NOT NULL,
	"supplier_id" integer,
	"supplier_name" varchar(255) NOT NULL,
	"po_number" varchar(50),
	"ordered_qty" numeric(18,3),
	"received_qty" numeric(18,3) DEFAULT '0' NOT NULL,
	"invoiced_qty" numeric(18,3) DEFAULT '0' NOT NULL,
	"unit" varchar(20) DEFAULT 'kg' NOT NULL,
	"amount" numeric(18,2) NOT NULL,
	"status" varchar(20) DEFAULT 'matched' NOT NULL,
	"note" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "purchase_request_items" (
	"id" serial PRIMARY KEY,
	"request_id" integer NOT NULL,
	"product_id" integer,
	"product_code" varchar(100) NOT NULL,
	"product_title" varchar(255) NOT NULL,
	"quantity" numeric(18,3) NOT NULL
);
--> statement-breakpoint
CREATE TABLE "purchase_requests" (
	"id" serial PRIMARY KEY,
	"ref" varchar(20),
	"buyer_id" integer NOT NULL,
	"note" varchar(1000),
	"status" varchar(20) DEFAULT 'submitted' NOT NULL,
	"department" varchar(100),
	"assigned_to_id" integer,
	"decision_note" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "request_events" (
	"id" serial PRIMARY KEY,
	"request_id" integer NOT NULL,
	"at" timestamp with time zone DEFAULT now() NOT NULL,
	"actor" varchar(100) NOT NULL,
	"action" varchar(30) NOT NULL,
	"note" text
);
--> statement-breakpoint
CREATE TABLE "sales_invoices" (
	"id" serial PRIMARY KEY,
	"invoice_number" varchar(100),
	"customer_name" varchar(255),
	"amount" numeric(18,2) NOT NULL,
	"remaining_amount" numeric(18,2),
	"sale_date" varchar(20) NOT NULL,
	"status" varchar(50) DEFAULT 'completed' NOT NULL,
	"description" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "suppliers" (
	"id" serial PRIMARY KEY,
	"code" varchar(30) NOT NULL UNIQUE,
	"name" varchar(255) NOT NULL,
	"category" varchar(100),
	"bank_account" varchar(60),
	"bank_changed_at" timestamp with time zone,
	"bank_changed_by" varchar(100),
	"bank_verified" boolean DEFAULT true NOT NULL,
	"is_high_risk" boolean DEFAULT false NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "tasks" (
	"id" serial PRIMARY KEY,
	"unit" varchar(100) NOT NULL,
	"title" varchar(500) NOT NULL,
	"owner" varchar(100) NOT NULL,
	"priority" varchar(20) DEFAULT 'medium' NOT NULL,
	"due_at" timestamp with time zone NOT NULL,
	"status" varchar(20) DEFAULT 'open' NOT NULL,
	"completed_at" timestamp with time zone,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "users" (
	"id" serial PRIMARY KEY,
	"email" varchar(255) NOT NULL UNIQUE,
	"full_name" varchar(255) NOT NULL,
	"hashed_password" text NOT NULL,
	"is_active" boolean DEFAULT true NOT NULL,
	"role" varchar(30) DEFAULT 'staff' NOT NULL,
	"department" varchar(100)
);
--> statement-breakpoint
CREATE INDEX "activity_log_created_at_idx" ON "activity_log" ("created_at");--> statement-breakpoint
CREATE INDEX "buyer_debts_buyer_id_idx" ON "buyer_debts" ("buyer_id");--> statement-breakpoint
CREATE INDEX "payment_requests_status_idx" ON "payment_requests" ("status");--> statement-breakpoint
CREATE INDEX "payment_requests_created_at_idx" ON "payment_requests" ("created_at");--> statement-breakpoint
CREATE INDEX "purchase_invoices_po_number_idx" ON "purchase_invoices" ("po_number");--> statement-breakpoint
CREATE INDEX "purchase_request_items_request_id_idx" ON "purchase_request_items" ("request_id");--> statement-breakpoint
CREATE INDEX "purchase_requests_buyer_id_idx" ON "purchase_requests" ("buyer_id");--> statement-breakpoint
CREATE INDEX "purchase_requests_status_idx" ON "purchase_requests" ("status");--> statement-breakpoint
CREATE INDEX "request_events_request_id_idx" ON "request_events" ("request_id");--> statement-breakpoint
CREATE INDEX "sales_invoices_sale_date_idx" ON "sales_invoices" ("sale_date");--> statement-breakpoint
ALTER TABLE "buyer_debts" ADD CONSTRAINT "buyer_debts_buyer_id_users_id_fkey" FOREIGN KEY ("buyer_id") REFERENCES "users"("id");--> statement-breakpoint
ALTER TABLE "debt_payments" ADD CONSTRAINT "debt_payments_debt_id_buyer_debts_id_fkey" FOREIGN KEY ("debt_id") REFERENCES "buyer_debts"("id");--> statement-breakpoint
ALTER TABLE "payment_requests" ADD CONSTRAINT "payment_requests_supplier_id_suppliers_id_fkey" FOREIGN KEY ("supplier_id") REFERENCES "suppliers"("id");--> statement-breakpoint
ALTER TABLE "purchase_invoices" ADD CONSTRAINT "purchase_invoices_supplier_id_suppliers_id_fkey" FOREIGN KEY ("supplier_id") REFERENCES "suppliers"("id");--> statement-breakpoint
ALTER TABLE "purchase_request_items" ADD CONSTRAINT "purchase_request_items_request_id_purchase_requests_id_fkey" FOREIGN KEY ("request_id") REFERENCES "purchase_requests"("id");--> statement-breakpoint
ALTER TABLE "purchase_request_items" ADD CONSTRAINT "purchase_request_items_product_id_inventory_items_id_fkey" FOREIGN KEY ("product_id") REFERENCES "inventory_items"("id");--> statement-breakpoint
ALTER TABLE "purchase_requests" ADD CONSTRAINT "purchase_requests_buyer_id_users_id_fkey" FOREIGN KEY ("buyer_id") REFERENCES "users"("id");--> statement-breakpoint
ALTER TABLE "purchase_requests" ADD CONSTRAINT "purchase_requests_assigned_to_id_users_id_fkey" FOREIGN KEY ("assigned_to_id") REFERENCES "users"("id");--> statement-breakpoint
ALTER TABLE "request_events" ADD CONSTRAINT "request_events_request_id_purchase_requests_id_fkey" FOREIGN KEY ("request_id") REFERENCES "purchase_requests"("id");