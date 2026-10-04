/**
 * 零售参数设置面板 (Retail Settings Panel)
 *
 * 参考智百威零售参数设置，集中管理 POS 所有零售参数
 * 入口：/app/retail-settings 或 solua_home.retail_settings.open()
 */
frappe.provide("solua_home.retail_settings");

(function () {
    "use strict";

    var dialog_open = false;
    var $dialog = null;

    function open_dialog() {
        if (dialog_open) return;
        dialog_open = true;
        if (!$dialog) create_dialog();
        $dialog.show();
        load_settings();
    }

    function close_dialog() {
        if (!dialog_open) return;
        dialog_open = false;
        if ($dialog) $dialog.hide();
    }

    function create_dialog() {
        $dialog = $(`
        <div id="retail-settings-dialog" style="
            position:fixed;top:0;left:0;width:100%;height:100%;
            background:rgba(0,0,0,0.5);z-index:9999;
            display:flex;align-items:center;justify-content:center;
        ">
        <div style="
            background:#fff;border-radius:12px;width:92vw;max-width:800px;
            max-height:88vh;display:flex;flex-direction:column;
            box-shadow:0 8px 32px rgba(0,0,0,0.3);overflow:hidden;
        ">
            <div style="padding:14px 20px;background:#6c757d;color:#fff;display:flex;justify-content:space-between;align-items:center;flex-shrink:0;">
                <div>
                    <h3 style="margin:0;font-size:18px;">零售参数设置</h3>
                    <div style="font-size:11px;opacity:0.8;margin-top:2px;">仅管理员可修改 · 访问地址 /app/retail-settings</div>
                </div>
                <button id="rs-close-btn" style="background:none;border:none;color:#fff;font-size:24px;cursor:pointer;padding:4px 8px;">&times;</button>
            </div>

            <div style="flex:1;overflow-y:auto;padding:20px;">
                <div id="rs-loading" style="text-align:center;color:#999;padding:40px;">加载中...</div>
                <div id="rs-content" style="display:none;">

                    <!-- 小票设置 -->
                    <h4 style="margin:0 0 12px;color:#333;border-bottom:2px solid #007bff;padding-bottom:6px;">小票设置</h4>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:8px;">
                        <div><label style="font-size:12px;font-weight:500;color:#666;">标题1（公司名）</label>
                        <input id="rs-title1" type="text" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:6px;" /></div>
                        <div><label style="font-size:12px;font-weight:500;color:#666;">标题2（副标题）</label>
                        <input id="rs-title2" type="text" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:6px;" /></div>
                    </div>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px;">
                        <div><label style="font-size:12px;font-weight:500;color:#666;">页脚1</label>
                        <input id="rs-footer1" type="text" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:6px;" /></div>
                        <div><label style="font-size:12px;font-weight:500;color:#666;">页脚2</label>
                        <input id="rs-footer2" type="text" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:6px;" /></div>
                        <div><label style="font-size:12px;font-weight:500;color:#666;">页脚3</label>
                        <input id="rs-footer3" type="text" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:6px;" /></div>
                        <div><label style="font-size:12px;font-weight:500;color:#666;">页脚4</label>
                        <input id="rs-footer4" type="text" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:6px;" /></div>
                    </div>

                    <!-- 打印设置 -->
                    <h4 style="margin:16px 0 12px;color:#333;border-bottom:2px solid #28a745;padding-bottom:6px;">打印设置</h4>
                    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:8px;">
                        <div><label style="font-size:12px;font-weight:500;color:#666;">纸宽</label>
                        <select id="rs-paper-width" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:6px;">
                            <option value="80mm">80mm</option><option value="58mm">58mm</option>
                        </select></div>
                        <div><label style="font-size:12px;font-weight:500;color:#666;">打印份数</label>
                        <input id="rs-copies" type="number" min="1" max="5" value="1" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:6px;" /></div>
                        <div><label style="font-size:12px;font-weight:500;color:#666;">抹零方式</label>
                        <select id="rs-rounding" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:6px;">
                            <option value="None">不处理</option><option value="Round to 0.1">四舍五入到角</option>
                            <option value="Round to 1">四舍五入到元</option><option value="Truncate cent">舍去分</option>
                            <option value="Truncate dec">舍去角</option>
                        </select></div>
                    </div>
                    <div style="display:flex;gap:20px;flex-wrap:wrap;margin-bottom:12px;">
                        <label style="font-size:13px;display:flex;align-items:center;gap:6px;"><input id="rs-print-company" type="checkbox" /> 打印公司名称</label>
                        <label style="font-size:13px;display:flex;align-items:center;gap:6px;"><input id="rs-print-datetime" type="checkbox" /> 打印日期时间</label>
                        <label style="font-size:13px;display:flex;align-items:center;gap:6px;"><input id="rs-print-change" type="checkbox" /> 打印找零金额</label>
                    </div>

                    <!-- 小票显示元素 -->
                    <h4 style="margin:16px 0 12px;color:#333;border-bottom:2px solid #ffc107;padding-bottom:6px;">小票显示元素</h4>
                    <div style="display:flex;gap:20px;flex-wrap:wrap;margin-bottom:12px;">
                        <label style="font-size:13px;display:flex;align-items:center;gap:6px;"><input id="rs-show-barcode" type="checkbox" /> 条码</label>
                        <label style="font-size:13px;display:flex;align-items:center;gap:6px;"><input id="rs-show-name" type="checkbox" /> 商品名称</label>
                        <label style="font-size:13px;display:flex;align-items:center;gap:6px;"><input id="rs-show-origprice" type="checkbox" /> 原价</label>
                        <label style="font-size:13px;display:flex;align-items:center;gap:6px;"><input id="rs-show-discount" type="checkbox" /> 折扣/特价</label>
                        <label style="font-size:13px;display:flex;align-items:center;gap:6px;"><input id="rs-show-qty" type="checkbox" /> 数量</label>
                        <label style="font-size:13px;display:flex;align-items:center;gap:6px;"><input id="rs-show-unit" type="checkbox" /> 单位</label>
                        <label style="font-size:13px;display:flex;align-items:center;gap:6px;"><input id="rs-show-subtotal" type="checkbox" /> 小计</label>
                        <label style="font-size:13px;display:flex;align-items:center;gap:6px;"><input id="rs-show-regno" type="checkbox" /> 机号</label>
                    </div>

                    <!-- 价格控制 -->
                    <h4 style="margin:16px 0 12px;color:#333;border-bottom:2px solid #dc3545;padding-bottom:6px;">价格控制</h4>
                    <div style="display:flex;gap:20px;flex-wrap:wrap;margin-bottom:12px;">
                        <label style="font-size:13px;display:flex;align-items:center;gap:6px;"><input id="rs-allow-override" type="checkbox" /> 允许前台改价</label>
                        <label style="font-size:13px;display:flex;align-items:center;gap:6px;"><input id="rs-override-approval" type="checkbox" /> 改价需要审批密码</label>
                    </div>

                    <!-- 其它设置 -->
                    <h4 style="margin:16px 0 12px;color:#333;border-bottom:2px solid #17a2b8;padding-bottom:6px;">其它设置</h4>
                    <div style="display:flex;gap:20px;flex-wrap:wrap;margin-bottom:12px;">
                        <label style="font-size:13px;display:flex;align-items:center;gap:6px;"><input id="rs-front-inventory" type="checkbox" /> 允许前台盘点</label>
                        <label style="font-size:13px;display:flex;align-items:center;gap:6px;"><input id="rs-auto-add" type="checkbox" /> 扫码自动加购（无需点击）</label>
                    </div>

                    <!-- 保存 -->
                    <div style="text-align:right;padding-top:12px;border-top:1px solid #eee;">
                        <button id="rs-save-btn" style="padding:10px 30px;background:#007bff;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:14px;font-weight:600;">保存设置</button>
                    </div>
                </div>
            </div>
        </div>
        </div>
        `);

        $("body").append($dialog);
        $dialog.find("#rs-close-btn").on("click", close_dialog);
        $dialog.on("click", function (e) { if (e.target === $dialog[0]) close_dialog(); });
        $dialog.find("#rs-save-btn").on("click", save_settings);
    }

    function load_settings() {
        frappe.call({
            method: "solua_home.api.retail_settings.get_retail_settings",
            callback: function (r) {
                var s = r.message || {};
                $dialog.find("#rs-loading").hide();
                $dialog.find("#rs-content").show();

                $dialog.find("#rs-title1").val(s.receipt_title_1 || "Solua Home");
                $dialog.find("#rs-title2").val(s.receipt_title_2 || "Lda");
                $dialog.find("#rs-footer1").val(s.receipt_footer_1 || "");
                $dialog.find("#rs-footer2").val(s.receipt_footer_2 || "");
                $dialog.find("#rs-footer3").val(s.receipt_footer_3 || "");
                $dialog.find("#rs-footer4").val(s.receipt_footer_4 || "");
                $dialog.find("#rs-paper-width").val(s.paper_width || "80mm");
                $dialog.find("#rs-copies").val(s.print_copies || 1);
                $dialog.find("#rs-rounding").val(s.rounding_method || "None");
                $dialog.find("#rs-print-company").prop("checked", s.print_company_name !== 0);
                $dialog.find("#rs-print-datetime").prop("checked", s.print_date_time !== 0);
                $dialog.find("#rs-print-change").prop("checked", s.print_change !== 0);
                $dialog.find("#rs-show-barcode").prop("checked", s.show_barcode_on_receipt !== 0);
                $dialog.find("#rs-show-name").prop("checked", s.show_item_name !== 0);
                $dialog.find("#rs-show-origprice").prop("checked", s.show_original_price === 1);
                $dialog.find("#rs-show-discount").prop("checked", s.show_discount !== 0);
                $dialog.find("#rs-show-qty").prop("checked", s.show_qty !== 0);
                $dialog.find("#rs-show-unit").prop("checked", s.show_unit !== 0);
                $dialog.find("#rs-show-subtotal").prop("checked", s.show_subtotal !== 0);
                $dialog.find("#rs-show-regno").prop("checked", s.show_register_no === 1);
                $dialog.find("#rs-allow-override").prop("checked", s.allow_price_override === 1);
                $dialog.find("#rs-override-approval").prop("checked", s.price_override_requires_approval !== 0);
                $dialog.find("#rs-front-inventory").prop("checked", s.allow_front_inventory === 1);
                $dialog.find("#rs-auto-add").prop("checked", s.auto_add_item === 1);
            }
        });
    }

    function save_settings() {
        var data = {
            receipt_title_1: $dialog.find("#rs-title1").val(),
            receipt_title_2: $dialog.find("#rs-title2").val(),
            receipt_footer_1: $dialog.find("#rs-footer1").val(),
            receipt_footer_2: $dialog.find("#rs-footer2").val(),
            receipt_footer_3: $dialog.find("#rs-footer3").val(),
            receipt_footer_4: $dialog.find("#rs-footer4").val(),
            paper_width: $dialog.find("#rs-paper-width").val(),
            print_copies: parseInt($dialog.find("#rs-copies").val()) || 1,
            rounding_method: $dialog.find("#rs-rounding").val(),
            print_company_name: $dialog.find("#rs-print-company").is(":checked") ? 1 : 0,
            print_date_time: $dialog.find("#rs-print-datetime").is(":checked") ? 1 : 0,
            print_change: $dialog.find("#rs-print-change").is(":checked") ? 1 : 0,
            show_barcode_on_receipt: $dialog.find("#rs-show-barcode").is(":checked") ? 1 : 0,
            show_item_name: $dialog.find("#rs-show-name").is(":checked") ? 1 : 0,
            show_original_price: $dialog.find("#rs-show-origprice").is(":checked") ? 1 : 0,
            show_discount: $dialog.find("#rs-show-discount").is(":checked") ? 1 : 0,
            show_qty: $dialog.find("#rs-show-qty").is(":checked") ? 1 : 0,
            show_unit: $dialog.find("#rs-show-unit").is(":checked") ? 1 : 0,
            show_subtotal: $dialog.find("#rs-show-subtotal").is(":checked") ? 1 : 0,
            show_register_no: $dialog.find("#rs-show-regno").is(":checked") ? 1 : 0,
            allow_price_override: $dialog.find("#rs-allow-override").is(":checked") ? 1 : 0,
            price_override_requires_approval: $dialog.find("#rs-override-approval").is(":checked") ? 1 : 0,
            allow_front_inventory: $dialog.find("#rs-front-inventory").is(":checked") ? 1 : 0,
            auto_add_item: $dialog.find("#rs-auto-add").is(":checked") ? 1 : 0,
        };

        frappe.call({
            method: "solua_home.api.retail_settings.save_retail_settings",
            args: data,
            callback: function () {
                frappe.show_alert({ message: "零售参数已保存", indicator: "green" });
                close_dialog();
            },
            error: function (r) {
                frappe.show_alert({ message: "保存失败：" + (r._message || "权限不足"), indicator: "red" });
            }
        });
    }

    solua_home.retail_settings.open = open_dialog;
    solua_home.retail_settings.close = close_dialog;
})();
