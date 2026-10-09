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
    endpoint: "/inventory/", body: "#inventoryBody", search: "#inventorySearch", pageSize: 500, columns: 3,
    row: i => `
        <tr>
            <td>${toFaDigits(esc(i.code))}</td>
            <td>${esc(i.title)}</td>
            <td>${fmt(i.quantity)}</td>
        </tr>`,
});

registerView("sales", () => salesList.reload());
registerView("finance", () => financeList.reload());
registerView("inventory", () => inventoryList.reload());
registerView("upload", () => {});

// ---------------------------------------------------------------------------
// آپلود اکسل
// ---------------------------------------------------------------------------
const UPLOADS = [
    { id: "sales", title: "فاکتور فروش", path: "/upload/sales-excel", cols: "تاریخ، نام مشتری، خالص (+ باقی مانده فاکتور، نوع تسویه، شماره فاکتور)", affects: ["overview", "sales"] },
    { id: "receivables", title: "حساب‌های دریافتنی", path: "/upload/receivables-excel", cols: "عنوان، مانده (+ کد)", affects: ["overview", "finance"] },
    { id: "payables", title: "مانده بستانکاری", path: "/upload/payables-excel", cols: "عنوان، مانده بستانکار (+ کد)", affects: ["overview", "finance"] },
    { id: "expense", title: "گزارش هزینه", path: "/upload/expense-report", cols: "کد، عنوان (+ گردش و مانده بدهکار/بستانکار)", affects: [] },
    { id: "inventory", title: "موجودی انبار", path: "/inventory/upload", cols: "کد کالا، عنوان کالا، موجودی", affects: ["overview", "inventory"] },
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
            result.innerHTML = `✓ ${fmt(data.created)} ردیف ثبت شد، ${fmt(data.skipped)} ردیف رد شد` +
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
