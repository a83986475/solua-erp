/**
 * Print Designer 导入/导出功能
 *
 * 在 Print Designer 页面顶栏注入「📥 导出」和「📤 导入」按钮
 * 导出：将当前打印格式的 JSON 设计导出为 .json 文件下载
 * 导入：选择 .json 文件导入到新的打印格式
 */
frappe.provide("solua_home.print_format_ie");

(function () {
    "use strict";

    let injected = false;

    function inject_buttons() {
        if (injected) return;
        if (!window.location.pathname.includes("/print-designer")) {
            return;
        }
        injected = true;

        // 等待 Print Designer 页面加载
        setTimeout(() => {
            const $toolbar = $(".print-designer-toolbar, .pd-toolbar, [class*='toolbar']").first();
            if (!$toolbar.length) {
                // 重试
                setTimeout(inject_buttons, 1000);
                return;
            }

            // 导出按钮
            const $export_btn = $(`
                <button class="btn btn-xs btn-default" style="margin-left:8px;" title="导出当前打印格式为 JSON 文件">
                    📥 导出格式
                </button>
            `);
            $export_btn.on("click", export_current_format);

            // 导入按钮
            const $import_btn = $(`
                <button class="btn btn-xs btn-default" style="margin-left:4px;" title="从 JSON 文件导入打印格式">
                    📤 导入格式
                </button>
            `);
            $import_btn.on("click", import_format);

            $toolbar.append($export_btn).append($import_btn);
        }, 2000);
    }

    function export_current_format() {
        // 从 Print Designer 的 URL 获取 print_format name
        const url_params = new URLSearchParams(window.location.search);
        const print_format = url_params.get("print_format") || url_params.get("name");

        if (!print_format) {
            frappe.show_alert({ message: "请先打开一个打印格式", indicator: "orange" });
            return;
        }

        frappe.call({
            method: "frappe.client.get_value",
            args: {
                doctype: "Print Format",
                filters: { name: print_format },
                fieldname: ["name", "print_format_body", "doc_type", "module"],
            },
            callback: function (r) {
                const data = r.message;
                if (!data || !data.print_format_body) {
                    frappe.show_alert({ message: "该格式没有设计数据", indicator: "orange" });
                    return;
                }

                // 构建导出 JSON
                const export_data = {
                    print_format_name: data.name,
                    doc_type: data.doc_type,
                    module: data.module,
                    print_format_body: data.print_format_body,
                    exported_at: new Date().toISOString(),
                    exported_by: frappe.session.user,
                };

                // 下载
                const blob = new Blob([JSON.stringify(export_data, null, 2)], { type: "application/json" });
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `print_format_${print_format}_${frappe.datetime.nowdate()}.json`;
                a.click();
                URL.revokeObjectURL(url);

                frappe.show_alert({ message: `已导出：${print_format}`, indicator: "green" });
            },
        });
    }

    function import_format() {
        const input = document.createElement("input");
        input.type = "file";
        input.accept = ".json";
        input.onchange = function (e) {
            const file = e.target.files[0];
            if (!file) return;

            const reader = new FileReader();
            reader.onload = function (ev) {
                try {
                    const data = JSON.parse(ev.target.result);
                    if (!data.print_format_body) {
                        frappe.show_alert({ message: "无效的打印格式文件", indicator: "red" });
                        return;
                    }
                    show_import_dialog(data);
                } catch (err) {
                    frappe.show_alert({ message: "文件解析失败：" + err.message, indicator: "red" });
                }
            };
            reader.readAsText(file);
        };
        input.click();
    }

    function show_import_dialog(data) {
        const d = new frappe.ui.Dialog({
            title: "导入打印格式",
            fields: [
                {
                    fieldtype: "HTML",
                    fieldname: "info",
                    options: `
                        <div style="margin-bottom:12px;">
                            <p><b>来源格式：</b>${data.print_format_name || "未知"}</p>
                            <p><b>目标 DocType：</b>${data.doc_type || "未知"}</p>
                            <p><b>导出时间：</b>${data.exported_at || "未知"}</p>
                        </div>
                    `,
                },
                {
                    fieldtype: "Data",
                    fieldname: "new_format_name",
                    label: "新格式名称",
                    reqd: 1,
                    default: (data.print_format_name || "") + " (导入)",
                },
            ],
            primary_action_label: "导入",
            primary_action: function (values) {
                frappe.call({
                    method: "frappe.client.insert",
                    args: {
                        doc: {
                            doctype: "Print Format",
                            name: values.new_format_name,
                            doc_type: data.doc_type,
                            print_format_body: data.print_format_body,
                            module: data.module || "Custom",
                            custom: 1,
                        },
                    },
                    callback: function (r) {
                        frappe.show_alert({ message: "导入成功！", indicator: "green" });
                        d.hide();
                        // 跳转到新格式
                        frappe.set_route("print-designer", { print_format: values.new_format_name });
                    },
                    error: function (r) {
                        frappe.show_alert({ message: "导入失败：" + (r._message || ""), indicator: "red" });
                    },
                });
            },
        });
        d.show();
    }

    $(document).ready(function () {
        inject_buttons();
    });

    // 路由变化时重新检测
    $(window).on("hashchange", function () {
        injected = false;
        setTimeout(inject_buttons, 1000);
    });
})();
