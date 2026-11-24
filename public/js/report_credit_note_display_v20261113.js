// Keep self-posted return credits out of the report's Paid Amount column.
(function () {
    "use strict";

    const REPORTS = new Set(["Accounts Receivable", "应收账款", "Solua Accounts Receivable"]);

    function number(value) {
        const result = Number(value);
        return Number.isFinite(result) ? result : 0;
    }

    function move_credit(row, amount) {
        row.paid = number(row.paid) - amount;
        row.credit_note = number(row.credit_note) + amount;
        if (row.paid_in_account_currency != null) {
            row.paid_in_account_currency = number(row.paid_in_account_currency) - amount;
            row.credit_note_in_account_currency = number(row.credit_note_in_account_currency) + amount;
        }
    }

    function normalize(report_name, rows) {
        if (!REPORTS.has(report_name) || !Array.isArray(rows)) return;

        const moved_by_party = new Map();
        let moved_total = 0;
        rows.forEach((row) => {
            if (row.voucher_type !== "Sales Invoice"
                || number(row.invoice_grand_total) !== 0 || number(row.paid) <= 0
                || number(row.outstanding) >= 0) return;

            const amount = number(row.paid);
            move_credit(row, amount);
            moved_total += amount;
            moved_by_party.set(row.party, (moved_by_party.get(row.party) || 0) + amount);
        });

        rows.forEach((row) => {
            if (row.voucher_no || row.paid == null || row.credit_note == null) return;
            const amount = row.party === "Total"
                ? moved_total
                : (moved_by_party.get(row.party) || (!row.party ? moved_total : 0));
            if (amount) move_credit(row, amount);
        });
    }

    function install() {
        const prototype = frappe.views?.QueryReport?.prototype;
        if (!prototype) return false;
        if (prototype.__solua_credit_note_display_patch) return true;

        const original_prepare_report_data = prototype.prepare_report_data;
        prototype.prepare_report_data = function (data) {
            const result = original_prepare_report_data.call(this, data);
            normalize(this.report_name, this.data);
            return result;
        };
        prototype.__solua_credit_note_display_patch = true;
        return true;
    }

    if (!install()) {
        let attempts = 0;
        const retry = () => {
            if (install() || attempts++ >= 20) return;
            setTimeout(retry, 100);
        };
        retry();
    }
})();
