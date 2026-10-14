// فروش، مطالبات و بستانکاری، انبار و آپلود اکسل
const salesList = createList({
    endpoint: "/sales/", body: "#salesBody", search: "#salesSearch", more: "#salesMore", pageSize: 50, columns: 6,
    row: s => `
        <tr>
            <td>${toFaDigits(esc(s.sale_date))}</td>
            <td>${toFaDigits(esc(s.invoice_number)) || "—"}</td>
            <td>${esc(s.customer_name) || "—"}</td>
            <td>${fmt(s.amount)}</td>
            <td>${Number(s.remaining_amount) > 0 ? fmt(s.remaining_amount) : "—"}</td>
            <td>${Number(s.remaining_amount) > 0 ? badge(["", "orange"], "تسویه‌نشده") : badge(["", "green"], "تسویه‌شده")}</td>
        </tr>`,
});

const financeType = segmented("#financeType", () => financeList.reload());
const financeList = createList({
    endpoint: "/finance/", body: "#financeBody", search: "#financeSearch", more: "#financeMore", pageSize: 50, columns: 4,
    extraParams: () => ({ type: financeType() }),
    row: f => `
        <tr>
            <td>${esc(f.party_name) || "—"}</td>
            <td>${f.type === "receivable" ? badge(["", "blue"], "مطالبات") : badge(["", "pink"], "بستانکاری")}</td>
            <td>${fmt(f.amount)}</td>
            <td>${toFaDigits(esc(f.description)) || "—"}</td>
        </tr>`,
});

const inventoryList = createList({
    endpoint: "/inventory/", body: "#inventoryBody", search: "#inventorySearch", pageSize: 500, columns: 5,
    row: i => `
        <tr>
            <td>${toFaDigits(esc(i.code))}</td>
            <td>${esc(i.title)}</td>
            <td>${fmt(i.quantity)}</td>
            <td>${i.stock_value == null ? "—" : fmt(i.stock_value)}</td>
            <td>${i.avg_price == null ? "—" : fmt(i.avg_price)}</td>
        </tr>`,
});

// ---------------------------------------------------------------------------
// خزانه‌داری: بانک‌ها، چک‌ها، دریافت‌ها، دفتر پرداخت و دفتر حساب‌ها
// ---------------------------------------------------------------------------
const banksList = createList({
    endpoint: "/banks/", body: "#banksBody", search: "#banksSearch", more: "#banksMore", pageSize: 100, columns: 6,
    row: b => `
        <tr>
            <td>${toFaDigits(esc(b.code))}</td>
            <td>${esc(b.title)}</td>
            <td>${fmt(b.opening_balance)}</td>
            <td>${fmt(b.receipts)}</td>
            <td>${fmt(b.payments)}</td>
            <td><b>${fmt(b.balance)}</b></td>
        </tr>`,
});

const CHECK_STATUS = {
    pending: ["در انتظار", "orange"],
    deposited: ["واگذار به بانک", "blue"],
    spent: ["خرج شده", "green"],
    cleared: ["پاس شده", "gray"],
    received: ["دریافتی", "gray"],
};

const checkDir = segmented("#checkDir", () => checksList.reload());
const checkStatus = segmented("#checkStatus", () => checksList.reload());
const checksList = createList({
    endpoint: "/checks/", body: "#checksBody", search: "#checksSearch", more: "#checksMore",
    pageSize: 100, columns: 7,
    extraParams: () => ({ direction: checkDir(), status: checkStatus() }),
    row: c => `
        <tr>
            <td>${c.direction === "received" ? badge(["", "blue"], "دریافتی") : badge(["", "pink"], "پرداختنی")}</td>
            <td>${esc(c.counterparty)}${c.owner ? `<br><small class="sub">${esc(c.owner)}</small>` : ""}</td>
            <td>${fmt(c.amount)}</td>
            <td>${toFaDigits(esc(c.due_date)) || "—"}</td>
            <td>${toFaDigits(esc(c.check_no || c.announce_no)) || "—"}</td>
            <td>${esc(c.bank) || "—"}</td>
            <td>${CHECK_STATUS[c.status] ? badge(CHECK_STATUS[c.status]) : badge(["", "gray"], c.status)}</td>
        </tr>`,
});

const receiptKind = segmented("#receiptKind", () => receiptsList.reload());
const receiptsList = createList({
    endpoint: "/receipts/", body: "#receiptsBody", search: "#receiptsSearch", more: "#receiptsMore",
    pageSize: 100, columns: 6,
    extraParams: () => ({ kind: receiptKind() }),
    row: r => `
        <tr>
            <td>${r.kind ? badge(["", "blue"], r.kind) : "—"}</td>
            <td>${esc(r.counterparty)}</td>
            <td>${toFaDigits(esc(r.ref_no)) || "—"}</td>
            <td>${toFaDigits(esc(r.date)) || "—"}</td>
            <td>${fmt(r.amount)}</td>
            <td>${esc(r.description) || "—"}</td>
        </tr>`,
});

const paylogList = createList({
    endpoint: "/payment-log/", body: "#paylogBody", search: "#paylogSearch", more: "#paylogMore",
    pageSize: 100, columns: 7,
    extraParams: () => ({ kind: $("#paylogKind").value }),
    row: p => `
        <tr>
            <td>${p.kind ? badge(["", "pink"], p.kind) : "—"}</td>
            <td>${esc(p.counterparty)}</td>
            <td>${toFaDigits(esc(p.ref_no)) || "—"}</td>
            <td>${toFaDigits(esc(p.date)) || "—"}</td>
            <td>${esc(p.item) || "—"}</td>
            <td>${fmt(p.amount)}</td>
            <td>${esc(p.description) || "—"}</td>
        </tr>`,
});
$("#paylogKind").addEventListener("change", () => paylogList.reload());

const ledgerList = createList({
    endpoint: "/expenses/", body: "#ledgerBody", search: "#ledgerSearch", more: "#ledgerMore",
    pageSize: 100, columns: 6,
    row: e => `
        <tr>
            <td>${toFaDigits(esc(e.code))}</td>
            <td>${esc(e.title)}</td>
            <td>${Number(e.debit_turnover) ? fmt(e.debit_turnover) : "—"}</td>
            <td>${Number(e.credit_turnover) ? fmt(e.credit_turnover) : "—"}</td>
            <td>${Number(e.debit_balance) ? fmt(e.debit_balance) : "—"}</td>
            <td>${Number(e.credit_balance) ? fmt(e.credit_balance) : "—"}</td>
        </tr>`,
});

registerView("sales", () => salesList.reload());
registerView("finance", () => financeList.reload());
registerView("inventory", () => inventoryList.reload());
registerView("upload", () => {});
registerView("banks", () => banksList.reload());
registerView("checks", () => checksList.reload());
registerView("receipts", () => receiptsList.reload());
registerView("paylog", () => paylogList.reload());
registerView("ledger", () => ledgerList.reload());

// ---------------------------------------------------------------------------
// آپلود اکسل
// ---------------------------------------------------------------------------
const UPLOADS = [
    { id: "sales", title: "فاکتور فروش", path: "/upload/sales-excel", cols: "تاریخ، نام مشتری، خالص (+ باقی مانده فاکتور، نوع تسویه، شماره فاکتور)", affects: ["overview", "sales"] },
    { id: "receivables", title: "حساب‌های دریافتنی", path: "/upload/receivables-excel", cols: "عنوان، مانده (+ کد)", affects: ["overview", "finance"] },
    { id: "payables", title: "مانده بستانکاری", path: "/upload/payables-excel", cols: "عنوان، مانده بستانکار (+ کد)", affects: ["overview", "finance"] },
    { id: "expense", title: "گزارش هزینه / دفتر حساب‌ها", path: "/upload/expense-report", cols: "کد، عنوان (+ گردش و مانده بدهکار/بستانکار)", affects: ["ledger"] },
    { id: "inventory", title: "موجودی انبار (تعدادی)", path: "/inventory/upload", cols: "کد کالا، عنوان کالا، موجودی", affects: ["overview", "inventory"] },
    { id: "inventoryValue", title: "موجودی انبار (مبلغی و فی متوسط)", path: "/inventory/upload", cols: "کد کالا، عنوان کالا، موجودی، موجودی-مبلغ، موجودی-فی متوسط", affects: ["overview", "inventory"] },
    { id: "banks", title: "بانک‌ها (دریافت و پرداخت)", path: "/upload/banks-excel", cols: "کد تفصیلی، عنوان، اول دوره، دریافت ها، پرداخت ها، مانده", affects: ["overview", "banks"] },
    { id: "checksReceived", title: "چک‌های دریافتی", path: "/upload/checks-excel?direction=received", cols: "تفصیلی، طرف مقابل، نوع، شماره، مبلغ، تاریخ سررسید، تاریخ رسید، بانک، وضعیت، صاحب چک", affects: ["overview", "checks"] },
    { id: "checksPayable", title: "چک‌های پرداختنی (در انتظار)", path: "/upload/checks-excel?direction=payable&status=pending", cols: "تفصیلی، طرف مقابل، تاریخ سررسید، شماره اعلامیه، تاریخ اعلامیه، حساب بانکی، نوع", affects: ["overview", "checks"] },
    { id: "checksCleared", title: "چک‌های پرداختنی پاس‌شده", path: "/upload/checks-excel?direction=payable&status=cleared", cols: "تفصیلی، طرف مقابل، مبلغ، تاریخ سررسید، شماره اعلامیه، تاریخ وصول، حساب بانکی", affects: ["overview", "checks"] },
    { id: "receipts", title: "دریافت‌ها (تفکیک نوع و تاریخ)", path: "/upload/receipts-excel", cols: "نوع دریافت، طرف مقابل، شماره، تاریخ، مبلغ دریافت، شرح", affects: ["overview", "receipts"] },
    { id: "paylog", title: "دفتر پرداخت (تفکیک نوع و روز)", path: "/upload/payments-excel", cols: "نوع پرداخت، طرف مقابل، شماره، تاریخ، اقلام، مبلغ پرداخت، شرح", affects: ["overview", "paylog"] },
];

$("#uploadGrid").innerHTML = UPLOADS.map(u => `
    <div class="panel upload-card" id="up-${u.id}">
        <h2>${u.title}</h2>
        <p class="cols">ستون‌ها: ${u.cols}</p>
        <label class="drop"><b>انتخاب یا رها کردن فایل</b><span>xlsx، xls، csv</span>
            <input type="file" accept=".xlsx,.xls,.xlsm,.csv" hidden>
        </label>
        <div class="result" aria-live="polite"></div>
    </div>`).join("");

UPLOADS.forEach(u => {
    const card = $(`#up-${u.id}`);
    const input = $("input", card);
    const drop = $(".drop", card);
    const result = $(".result", card);

    async function send(file) {
        if (!file) return;
        const form = new FormData();
        form.append("file", file);
        result.className = "result";
        result.textContent = `در حال ارسال «${file.name}»...`;
        try {
            const response = await apiFetch(u.path, { method: "POST", body: form });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(errorText(data, "آپلود ناموفق بود"));
            result.className = "result ok";
            const errs = (data.errors || []).map(e => `<li>${esc(e)}</li>`).join("");
            result.innerHTML = `✓ ${fmt(data.created)} ردیف ثبت شد` +
                (data.updated ? `، ${fmt(data.updated)} ردیف به‌روزرسانی شد` : "") +
                `، ${fmt(data.skipped)} ردیف رد شد` +
                (errs ? `<ul>${errs}</ul>` : "");
            invalidate(...u.affects);
            toast(`${u.title}: آپلود انجام شد`);
        } catch (err) {
            result.className = "result err";
            result.textContent = err.message;
        } finally {
            input.value = "";
        }
    }

    input.addEventListener("change", () => send(input.files[0]));
    ["dragenter", "dragover"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add("over"); }));
    ["dragleave", "drop"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.remove("over"); }));
    drop.addEventListener("drop", e => send(e.dataTransfer.files[0]));
});
