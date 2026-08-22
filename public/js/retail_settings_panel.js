/**
 * 零售参数设置面板 (Retail Settings Panel)
 *
 * 功能：集中管理 POS 零售参数
 *   - 小票标题/页脚
 *   - 打印份数
 *   - 抹零方式
 *   - 前台允许改价
 *   - 默认仓库
 *
 * 快捷键：Ctrl+Shift+R 打开/关闭
 * 入口：右下角 ⚙️ 浮动按钮
 */
frappe.provide("solua_home.retail_settings");

(function () {
    "use strict";

    let dialog_open = false;
    let $dialog = null;

    // 全局快捷键
    $(document).on("keydown", function (e) {
        if (e.ctrlKey && e.shiftKey && e.key === "R") {
            e.preventDefault();
            e.stopPropagation();
            dialog_open ? close_dialog() : open_dialog();
            return false;
        }
    });

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
            background:#fff;border-radius:12px;width:90vw;max-width:700px;
            max-height:85vh;display:flex;flex-direction:column;
            box-shadow:0 8px 32px rgba(0,0,0,0.3);overflow:hidden;
        ">
            <!-- 标题栏 -->
            <div style="padding:14px 20px;background:#6c757d;color:#fff;display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <h3 style="margin:0;font-size:18px;">⚙️ 零售参数设置</h3>
                    <div style="font-size:11px;opacity:0.8;margin-top:2px;">Ctrl+Shift+R 开关 · 仅管理员可修改</div>
                </div>
                <button id="rs-close-btn" style="background:none;border:none;color:#fff;font-size:24px;cursor:pointer;padding:4px 8px;">✕</button>
            </div>

            <!-- 内容区 -->
            <div style="flex:1;overflow-y:auto;padding:20px;">
                <div id="rs-loading" style="text-align:center;color:#999;padding:40px;">加载中...</div>
                <div id="rs-content" style="display:none;">
                    <!-- 小票设置 -->
                    <h4 style="margin:0 0 12px;color:#333;border-bottom:2px solid #007bff;padding-bottom:6px;">🧾 小票设置</h4>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:20px;">
                        <div>
                            <label style="font-size:12px;font-weight:500;color:#666;">标题1（公司名）</label>
                            <input id="rs-title1" type="text" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:6px;" />
                        </div>
                        <div>
                            <label style="font-size:12px;font-weight:500;color:#666;">标题2（副标题）</label>
                            <input id="rs-title2" type="text" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:6px;" />
                        </div>
                        <div>
                            <label style="font-size:12px;font-weight:500;color:#666;">页脚1</label>
                            <input id="rs-footer1" type="text" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:6px;" />
                        </div>
                        <div>
                            <label style="font-size:12px;font-weight:500;color:#666;">页脚2</label>
                            <input id="rs-footer2" type="text" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:6px;" />
                        </div>
                        <div>
                            <label style="font-size:12px;font-weight:500;color:#666;">页脚3</label>
                            <input id="rs-footer3" type="text" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:6px;" />
                        </div>
                        <div>
                            <label style="font-size:12px;font-weight:500;color:#666;">页脚4</label>
                            <input id="rs-footer4" type="text" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:6px;" />
                        </div>
                    </div>

                    <!-- 打印设置 -->
                    <h4 style="margin:0 0 12px;color:#333;border-bottom:2px solid #28a745;padding-bottom:6px;">🖨️ 打印设置</h4>
                    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:20px;">
                        <div>
                            <label style="font-size:12px;font-weight:500;color:#666;">打印份数</label>
                            <input id="rs-copies" type="number" min="1" max="5" value="1" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:6px;" />
                        </div>
                        <div>
                            <label style="font-size:12px;font-weight:500;color:#666;">抹零方式</label>
                            <select id="rs-rounding" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:6px;">
                                <option value="不处理">不处理</option>
                                <option value="四舍五入到角">四舍五入到角</option>
                                <option value="四舍五入到元">四舍五入到元</option>
                                <option value="舍去分">舍去分</option>
                                <option value="舍去角">舍去角</option>
                            </select>
                        </div>
                        <div>
                            <label style="font-size:12px;font-weight:500;color:#666;">纸宽</label>
                            <select id="rs-paper-width" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:6px;">
                                <option value="80mm">80mm</option>
                                <option value="58mm">58mm</option>
                            </select>
                        </div>
                    </div>

                    <!-- 价格控制 -->
                    <h4 style="margin:0 0 12px;color:#333;border-bottom:2px solid #ffc107;padding-bottom:6px;">💰 价格控制</h4>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:20px;">
                        <div style="display:flex;align-items:center;gap:8px;">
                            <input id="rs-allow-override" type="checkbox" style="width:18px;height:18px;" />
                            <label for="rs-allow-override" style="font-size:13px;">允许前台改价</label>
                        </div>
                        <div style="display:flex;align-items:center;gap:8px;">
                            <input id="rs-override-approval" type="checkbox" style="width:18px;height:18px;" />
                            <label for="rs-override-approval" style="font-size:13px;">改价需要审批密码</label>
                        </div>
                    </div>

                    <!-- 保存按钮 -->
                    <div style="text-align:right;padding-top:12px;border-top:1px solid #eee;">
                        <button id="rs-save-btn" style="padding:10px 30px;background:#007bff;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:14px;font-weight:600;">💾 保存设置</button>
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
                $dialog.find("#rs-footer1").val(s.receipt_footer_1 || "Obrigado pela preferência!");
                $dialog.find("#rs-footer2").val(s.receipt_footer_2 || "");
                $dialog.find("#rs-footer3").val(s.receipt_footer_3 || "www.solua.one");
                $dialog.find("#rs-footer4").val(s.receipt_footer_4 || "");
                $dialog.find("#rs-copies").val(s.print_copies || 1);
                $dialog.find("#rs-rounding").val(s.rounding_method || "不处理");
                $dialog.find("#rs-paper-width").val(s.paper_width || "80mm");
                $dialog.find("#rs-allow-override").prop("checked", !!s.allow_price_override);
                $dialog.find("#rs-override-approval").prop("checked", s.price_override_requires_approval !== 0);
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
            print_copies: parseInt($dialog.find("#rs-copies").val()) || 1,
            rounding_method: $dialog.find("#rs-rounding").val(),
            paper_width: $dialog.find("#rs-paper-width").val(),
            allow_price_override: $dialog.find("#rs-allow-override").is(":checked") ? 1 : 0,
            price_override_requires_approval: $dialog.find("#rs-override-approval").is(":checked") ? 1 : 0,
        };

        frappe.call({
            method: "solua_home.api.retail_settings.save_retail_settings",
            args: data,
            callback: function (r) {
                frappe.show_alert({ message: "零售参数已保存", indicator: "green" });
                close_dialog();
            },
            error: function (r) {
                frappe.show_alert({ message: "保存失败：" + (r._message || "权限不足"), indicator: "red" });
            }
        });
    }

    // 浮动按钮
    function inject_floating_button() {
        if (window.location.pathname.includes("/point-of-sale")) return;
        if ($("#rs-float-btn").length) return;

        var $btn = $('<div id="rs-float-btn" title="零售参数 (Ctrl+Shift+R)" style="' +
            'position:fixed;bottom:140px;right:24px;z-index:9990;' +
            'width:48px;height:48px;border-radius:50%;' +
            'background:#6c757d;color:#fff;cursor:pointer;' +
            'display:flex;align-items:center;justify-content:center;' +
            'font-size:20px;box-shadow:0 4px 12px rgba(108,117,125,0.4);' +
            'transition:transform 0.2s;">⚙️</div>');

        $btn.on("mouseenter", function () { $(this).css("transform", "scale(1.1)"); });
        $btn.on("mouseleave", function () { $(this).css("transform", "scale(1)"); });
        $btn.on("click", open_dialog);
        $("body").append($btn);
    }

    solua_home.retail_settings.open = open_dialog;
    solua_home.retail_settings.close = close_dialog;

    $(document).ready(function () {
        inject_floating_button();
    });
})();
