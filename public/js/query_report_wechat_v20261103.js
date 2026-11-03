// Send selected standard query reports to the configured WeCom group bot.
frappe.provide("solua_home.query_report_wechat");

(function () {
    "use strict";

    const REPORTS = new Set([
        "Stock Balance",
        "Stock Ledger",
        "Sales Order Analysis",
        "Sales Register",
        "Item-wise Sales Register",
        "Accounts Receivable",
        "Accounts Receivable Summary",
        "General Ledger",
    ]);

    const addButton = (report) => {
        if (!report || !REPORTS.has(report.report_name) || !report.page?.add_inner_button) return;
        if (report.__solua_wechat_button_report === report.report_name) return;

        report.page.add_inner_button(__("发送表格到微信"), () => {
            const filters = report.get_filter_values(true);
            frappe.confirm(
                __("将当前筛选结果表格发送到企业微信群，继续吗？"),
                () => frappe.call({
                    method: "solua_home.api.wecom.send_query_report_xlsx_to_wechat",
                    args: {report_name: report.report_name, filters},
                }).then((response) => {
                    frappe.show_alert({message: __("表格已发送到企业微信群"), indicator: "green"});
                    return response;
                }),
            );
        });
        report.__solua_wechat_button_report = report.report_name;
    };

    const install = () => {
        const QueryReport = frappe.views?.QueryReport;
        if (!QueryReport || QueryReport.prototype.__solua_wechat_patch) return Boolean(QueryReport);

        const refreshReport = QueryReport.prototype.refresh_report;
        if (typeof refreshReport !== "function") return false;
        QueryReport.prototype.refresh_report = function () {
            const result = refreshReport.apply(this, arguments);
            return Promise.resolve(result).then(() => {
                addButton(this);
                return result;
            });
        };
        QueryReport.prototype.__solua_wechat_patch = true;
        return true;
    };

    let attempts = 0;
    const waitForQueryReport = () => {
        if (install() || ++attempts >= 30) return;
        setTimeout(waitForQueryReport, 500);
    };
    waitForQueryReport();
})();
