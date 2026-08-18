/**
 * Label Printing for solua_home
 *
 * 功能：扫码/搜索物料 → 选模板 → 设数量 → 批量打印标签
 *
 * 快捷键：
 *   Ctrl+L    打开/关闭标签打印界面
 *   F2        聚焦搜索框（新增模式）
 *   Enter     搜索（搜索框内）/ 确认（数量输入内）
 *   Ctrl+P    打印选中物料
 *   Escape    关闭界面 / 清空搜索
 *   ↑↓        导航搜索结果
 *   Space     切换选中/取消选中
 *   +/-       增减选中项数量
 *   Ctrl+A    全选/取消全选搜索结果
 *   Ctrl+Shift+P  切换打印模式（批量/单个）
 */
frappe.provide("solua_home.label_print");

(function () {
    "use strict";

    // ─── 全局快捷键监听 ───────────────────────────────────────────
    let dialog_open = false;
    let $dialog = null;

    $(document).on("keydown", function (e) {
        // Ctrl+L → 打开/关闭
        if (e.ctrlKey && e.key === "l") {
            e.preventDefault();
            e.stopPropagation();
            if (dialog_open) {
                close_dialog();
            } else {
                open_dialog();
            }
            return false;
        }

        // 如果对话框未打开，不处理其他快捷键
        if (!dialog_open) return;

        // Escape → 关闭
        if (e.key === "Escape") {
            e.preventDefault();
            close_dialog();
            return false;
        }

        // F2 → 聚焦搜索框
        if (e.key === "F2") {
            e.preventDefault();
            focus_search();
            return false;
        }

        // Ctrl+P → 打印
        if (e.ctrlKey && e.key === "p") {
            e.preventDefault();
            do_print();
            return false;
        }

        // Ctrl+A → 全选
        if (e.ctrlKey && e.key === "a" && !_is_input_focused()) {
            e.preventDefault();
            toggle_select_all();
            return false;
        }

        // ↑↓ → 导航结果
        if ((e.key === "ArrowUp" || e.key === "ArrowDown") && !_is_input_focused()) {
            e.preventDefault();
            navigate_results(e.key === "ArrowDown" ? 1 : -1);
            return false;
        }

        // Space → 切换选中
        if (e.key === " " && !_is_input_focused()) {
            e.preventDefault();
            toggle_current_item();
            return false;
        }

        // + / - → 增减数量
        if ((e.key === "+" || e.key === "=" || e.key === "-") && !_is_input_focused()) {
            e.preventDefault();
            adjust_quantity(e.key === "-" ? -1 : 1);
            return false;
        }
    });

    function _is_input_focused() {
        var el = document.activeElement;
        return el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT");
    }

    // ─── 对话框 UI ─────────────────────────────────────────────────

    function open_dialog() {
        if (dialog_open) return;
        dialog_open = true;

        // 如果还没创建，创建 DOM
        if (!$dialog) {
            create_dialog();
        }

        $dialog.show();
        focus_search();
        _load_print_formats();
    }

    function close_dialog() {
        if (!dialog_open) return;
        dialog_open = false;
        if ($dialog) {
            $dialog.hide();
        }
    }

    function focus_search() {
        setTimeout(function () {
            var $search = $dialog.find("#lp-search-input");
            if ($search.length) {
                $search[0].focus();
                $search[0].select();
            }
        }, 100);
    }

    function create_dialog() {
        $dialog = $(`
        <div id="label-print-dialog" style="
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.5); z-index: 9999;
            display: flex; align-items: center; justify-content: center;
        ">
        <div style="
            background: #fff; border-radius: 12px; width: 95vw; max-width: 1100px;
            max-height: 90vh; display: flex; flex-direction: column;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3); overflow: hidden;
        ">
            <!-- 标题栏 -->
            <div style="
                padding: 16px 20px; background: #007bff; color: #fff;
                display: flex; justify-content: space-between; align-items: center;
            ">
                <div>
                    <h3 style="margin: 0; font-size: 18px;">
                        <i class="fa fa-tag"></i> 标签打印
                    </h3>
                    <div style="font-size: 12px; opacity: 0.8; margin-top: 2px;">
                        Ctrl+L 打开/关闭 · F2 聚焦搜索 · Ctrl+P 打印 · Esc 关闭
                    </div>
                </div>
                <button id="lp-close-btn" style="
                    background: none; border: none; color: #fff; font-size: 24px;
                    cursor: pointer; padding: 4px 8px;
                " title="关闭 (Esc)">✕</button>
            </div>

            <!-- 搜索栏 -->
            <div style="padding: 16px 20px; border-bottom: 1px solid #e9ecef;">
                <div style="display: flex; gap: 12px; align-items: center;">
                    <div style="flex: 1; position: relative;">
                        <input id="lp-search-input" type="text" placeholder="扫码或输入物料编码/名称..."
                            style="
                                width: 100%; padding: 10px 14px; font-size: 16px;
                                border: 2px solid #dee2e6; border-radius: 8px;
                                outline: none; transition: border-color 0.2s;
                            "
                            autocomplete="off" />
                    </div>
                    <button id="lp-search-btn" style="
                        padding: 10px 20px; background: #28a745; color: #fff;
                        border: none; border-radius: 8px; cursor: pointer;
                        font-size: 14px; white-space: nowrap;
                    ">🔍 搜索</button>
                </div>
            </div>

            <!-- 中间内容区 -->
            <div style="flex: 1; overflow-y: auto; padding: 16px 20px; min-height: 200px;">
                <!-- 提示区 -->
                <div id="lp-hint" style="
                    text-align: center; color: #999; padding: 40px 20px;
                    font-size: 14px;
                ">
                    <div style="font-size: 48px; margin-bottom: 12px;">🏷️</div>
                    <div>扫描条码或输入关键词搜索物料</div>
                    <div style="margin-top: 8px; font-size: 12px; color: #bbb;">
                        支持：条码、物料编码、名称、中文名、简称
                    </div>
                </div>

                <!-- 搜索结果列表 -->
                <div id="lp-results" style="display: none;">
                    <div id="lp-results-count" style="
                        font-size: 13px; color: #666; margin-bottom: 10px;
                    "></div>
                    <div id="lp-items"></div>
                </div>

                <!-- 已选中项汇总 -->
                <div id="lp-selected-summary" style="
                    display: none; margin-top: 16px; padding: 12px;
                    background: #e8f5e9; border-radius: 8px; border: 1px solid #c8e6c9;
                ">
                    <div style="font-weight: 600; margin-bottom: 6px;">
                        📋 已选 <span id="lp-selected-count">0</span> 种物料，
                        共 <span id="lp-total-qty">0</span> 张标签
                    </div>
                    <div id="lp-selected-list" style="font-size: 13px; color: #555;"></div>
                </div>
            </div>

            <!-- 底部操作栏 -->
            <div style="
                padding: 16px 20px; border-top: 1px solid #e9ecef;
                display: flex; justify-content: space-between; align-items: center;
                background: #f8f9fa;
            ">
                <div style="display: flex; gap: 10px; align-items: center;">
                    <label style="font-size: 13px; font-weight: 500;">打印格式：</label>
                    <select id="lp-format" style="
                        padding: 6px 10px; border: 1px solid #dee2e6; border-radius: 6px;
                        font-size: 13px; min-width: 160px;
                    "></select>

                    <label style="font-size: 13px; font-weight: 500; margin-left: 12px;">每件数量：</label>
                    <input id="lp-qty" type="number" value="1" min="1" max="999" style="
                        width: 60px; padding: 6px 8px; border: 1px solid #dee2e6;
                        border-radius: 6px; font-size: 13px; text-align: center;
                    " />
                </div>
                <div style="display: flex; gap: 10px;">
                    <button id="lp-select-all-btn" style="
                        padding: 8px 16px; background: #6c757d; color: #fff;
                        border: none; border-radius: 6px; cursor: pointer; font-size: 13px;
                    ">全选</button>
                    <button id="lp-clear-btn" style="
                        padding: 8px 16px; background: #ffc107; color: #333;
                        border: none; border-radius: 6px; cursor: pointer; font-size: 13px;
                    ">清空</button>
                    <button id="lp-print-btn" style="
                        padding: 8px 24px; background: #007bff; color: #fff;
                        border: none; border-radius: 6px; cursor: pointer;
                        font-size: 15px; font-weight: 600;
                    ">🖨️ 打印 <kbd style="font-size:11px;opacity:0.7">Ctrl+P</kbd></button>
                </div>
            </div>
        </div>
        </div>
        `);

        $("body").append($dialog);

        // ─── 事件绑定 ─────────────────────────────────────────────
        // 关闭按钮
        $dialog.find("#lp-close-btn").on("click", close_dialog);
        // 点击遮罩关闭
        $dialog.on("click", function (e) {
            if (e.target === $dialog[0]) close_dialog();
        });

        // 搜索：输入框回车 + 按钮点击
        $dialog.find("#lp-search-input").on("keydown", function (e) {
            if (e.key === "Enter") {
                e.preventDefault();
                do_search();
            }
        });
        $dialog.find("#lp-search-btn").on("click", do_search);

        // 数量变更 → 更新汇总
        $dialog.find("#lp-qty").on("change", update_selected_summary);

        // 操作按钮
        $dialog.find("#lp-print-btn").on("click", do_print);
        $dialog.find("#lp-clear-btn").on("click", clear_search);
        $dialog.find("#lp-select-all-btn").on("click", toggle_select_all);
    }

    // ─── 搜索 ─────────────────────────────────────────────────────

    let _search_timer = null;
    let _current_results = [];
    let _cursor_index = -1;

    function do_search() {
        var query = ($dialog.find("#lp-search-input").val() || "").trim();
        if (!query) return;

        frappe.call({
            method: "solua_home.api.label_print.search_items_for_label",
            args: { query: query, limit: 20 },
            callback: function (r) {
                _current_results = r.message || [];
                _render_results();
            },
            error: function (r) {
                frappe.msgprint("搜索失败：" + (r._message || "未知错误"));
            },
        });
    }

    function _render_results() {
        var $hint = $dialog.find("#lp-hint");
        var $results = $dialog.find("#lp-results");
        var $items = $dialog.find("#lp-items");

        if (_current_results.length === 0) {
            $hint.html('<div style="font-size:48px;margin-bottom:12px;">🔍</div><div>未找到匹配物料</div>').show();
            $results.hide();
            return;
        }

        $hint.hide();
        $results.show();
        $dialog.find("#lp-results-count").text(
            `找到 ${_current_results.length} 个物料`
        );

        var html = "";
        _current_results.forEach(function (item, idx) {
            var img_html = item.image
                ? `<img src="${item.image}" style="width:44px;height:44px;object-fit:cover;border-radius:6px;" />`
                : `<div style="width:44px;height:44px;background:#e9ecef;border-radius:6px;display:flex;align-items:center;justify-content:center;color:#999;font-size:20px;">📦</div>`;

            var bc_text = "";
            if (item.barcodes && item.barcodes.length > 0) {
                bc_text = item.barcodes.map(function (b) {
                    return `<span style="background:#e3f2fd;padding:1px 6px;border-radius:3px;font-size:11px;">${b.barcode}</span>`;
                }).join(" ");
            }

            var variant_tag = "";
            if (item.is_template) {
                variant_tag = '<span style="background:#fff3cd;color:#856404;padding:1px 6px;border-radius:3px;font-size:11px;margin-left:4px;">模板</span>';
            } else if (item.is_variant) {
                variant_tag = '<span style="background:#d4edda;color:#155724;padding:1px 6px;border-radius:3px;font-size:11px;margin-left:4px;">变体</span>';
            }

            html += `
            <div class="lp-item" data-index="${idx}" style="
                display: flex; align-items: center; gap: 12px;
                padding: 10px 12px; border: 1px solid #e9ecef; border-radius: 8px;
                margin-bottom: 6px; cursor: pointer; transition: all 0.15s;
            ">
                <input type="checkbox" class="lp-check" data-index="${idx}"
                    style="width:18px;height:18px;cursor:pointer;" />
                ${img_html}
                <div style="flex: 1; min-width: 0;">
                    <div style="display:flex;align-items:center;">
                        <span style="font-weight:600;font-size:14px;">
                            ${item.custom_chinese_name || item.custom_pos_short_name || item.item_name}
                        </span>
                        ${variant_tag}
                    </div>
                    <div style="font-size:12px;color:#666;margin-top:2px;">
                        ${item.item_code} · ${item.item_group || ''}
                        ${item.custom_spec_summary ? ' · ' + item.custom_spec_summary : ''}
                    </div>
                    <div style="margin-top:3px;">${bc_text}</div>
                </div>
                <div style="text-align:right;white-space:nowrap;">
                    <div style="font-weight:600;color:#007bff;font-size:15px;">
                        ${item.standard_rate ? frappe.utils.flt(item.standard_rate).toLocaleString() : '—'}
                    </div>
                    <div style="font-size:11px;color:#999;">${item.stock_uom || ''}</div>
                </div>
            </div>`;
        });

        $items.html(html);

        // 绑定点击/勾选事件
        $items.find(".lp-item").on("click", function (e) {
            // 点击行 = 切换勾选（除非点击的是 checkbox 本身）
            if (!$(e.target).hasClass("lp-check")) {
                var $cb = $(this).find(".lp-check");
                $cb.prop("checked", !$cb.prop("checked"));
                _highlight_item($(this).index());
            }
            update_selected_summary();
        });

        $items.find(".lp-check").on("change", function () {
            update_selected_summary();
        });

        _cursor_index = -1;
    }

    function _highlight_item(index) {
        var $items = $dialog.find(".lp-items .lp-item");
        $items.removeClass("lp-active");
        if (index >= 0 && index < $items.length) {
            $items.eq(index).addClass("lp-active").css("background", "#e3f2fd");
            setTimeout(function () {
                $items.eq(index).css("background", "");
            }, 300);
        }
    }

    // ─── 选中汇总 ─────────────────────────────────────────────────

    function get_selected_items() {
        var selected = [];
        var qty = parseInt($dialog.find("#lp-qty").val()) || 1;
        $dialog.find(".lp-check:checked").each(function () {
            var idx = parseInt($(this).data("index"));
            if (idx >= 0 && idx < _current_results.length) {
                selected.push({
                    item: _current_results[idx],
                    qty: qty,
                });
            }
        });
        return selected;
    }

    function update_selected_summary() {
        var selected = get_selected_items();
        var $summary = $dialog.find("#lp-selected-summary");

        if (selected.length === 0) {
            $summary.hide();
            return;
        }

        $summary.show();
        var total_qty = 0;
        var list_html = "";
        selected.forEach(function (s) {
            total_qty += s.qty;
            var name = s.item.custom_chinese_name || s.item.item_name || s.item.item_code;
            list_html += `<span style="display:inline-block;margin:2px 4px;background:#fff;padding:2px 8px;border-radius:4px;border:1px solid #c8e6c9;">
                ${name} ×${s.qty}
            </span>`;
        });

        $dialog.find("#lp-selected-count").text(selected.length);
        $dialog.find("#lp-total-qty").text(total_qty);
        $dialog.find("#lp-selected-list").html(list_html);
    }

    // ─── 打印 ─────────────────────────────────────────────────────

    function do_print() {
        var selected = get_selected_items();
        if (selected.length === 0) {
            frappe.show_alert({ message: "请先勾选要打印的物料", indicator: "orange" });
            return;
        }

        var format_name = $dialog.find("#lp-format").val();
        if (!format_name) {
            frappe.show_alert({ message: "请先选择打印格式", indicator: "orange" });
            return;
        }

        var item_codes = selected.map(function (s) { return s.item.item_code; });
        var quantities = {};
        selected.forEach(function (s) { quantities[s.item.item_code] = s.qty; });

        frappe.show_alert({ message: `正在生成 ${selected.length} 种物料的标签...`, indicator: "blue" });

        frappe.call({
            method: "solua_home.api.label_print.generate_label_html",
            args: {
                item_codes: JSON.stringify(item_codes),
                format_name: format_name,
                quantities: JSON.stringify(quantities),
            },
            callback: function (r) {
                if (r.message && r.message.html) {
                    _open_print_window(r.message.html, r.message.label_count);
                } else {
                    frappe.show_alert({ message: "标签生成失败", indicator: "red" });
                }
            },
            error: function (r) {
                frappe.show_alert({
                    message: "生成失败：" + (r._message || "未知错误"),
                    indicator: "red",
                });
            },
        });
    }

    function _open_print_window(html, count) {
        var print_win = window.open("", "_blank", "width=800,height=600");
        if (!print_win) {
            frappe.show_alert({
                message: "弹出窗口被浏览器拦截，请允许弹窗后重试",
                indicator: "orange",
            });
            return;
        }

        print_win.document.write(html);
        print_win.document.close();

        // 延迟后自动打印
        print_win.onload = function () {
            setTimeout(function () {
                print_win.print();
            }, 500);
        };

        frappe.show_alert({
            message: `已生成 ${count} 张标签，打印窗口已弹出`,
            indicator: "green",
        });
    }

    // ─── 辅助操作 ─────────────────────────────────────────────────

    function clear_search() {
        $dialog.find("#lp-search-input").val("").focus();
        $dialog.find("#lp-hint").show();
        $dialog.find("#lp-results").hide();
        $dialog.find("#lp-selected-summary").hide();
        _current_results = [];
        _cursor_index = -1;
    }

    function toggle_select_all() {
        var $checks = $dialog.find(".lp-check");
        var all_checked = $checks.length === $checks.filter(":checked").length;
        $checks.prop("checked", !all_checked);
        update_selected_summary();
    }

    function navigate_results(dir) {
        if (_current_results.length === 0) return;
        _cursor_index = Math.max(-1, Math.min(_cursor_index + dir, _current_results.length - 1));
        _highlight_item(_cursor_index);
    }

    function toggle_current_item() {
        if (_cursor_index < 0 || _cursor_index >= _current_results.length) return;
        var $cb = $dialog.find(".lp-check").eq(_cursor_index);
        $cb.prop("checked", !$cb.prop("checked"));
        update_selected_summary();
    }

    function adjust_quantity(delta) {
        var $qty = $dialog.find("#lp-qty");
        var val = parseInt($qty.val()) || 1;
        val = Math.max(1, Math.min(999, val + delta));
        $qty.val(val);
        update_selected_summary();
    }

    // ─── 加载打印格式 ─────────────────────────────────────────────

    function _load_print_formats() {
        frappe.call({
            method: "solua_home.api.label_print.get_label_print_formats",
            callback: function (r) {
                var formats = r.message || [];
                var $sel = $dialog.find("#lp-format");
                $sel.empty();
                if (formats.length === 0) {
                    $sel.append('<option value="">无可用格式</option>');
                } else {
                    formats.forEach(function (f) {
                        $sel.append(`<option value="${f.name}">${f.name}</option>`);
                    });
                }
            },
        });
    }

    // ─── 初始化：向 POS 等页面注入浮动按钮 ────────────────────────

    function inject_floating_button() {
        // 仅在 desk 页面注入（不在 POS 页面注入，POS 有自己的入口）
        if (window.location.pathname.includes("/point-of-sale")) return;

        var $btn = $(`
            <div id="lp-float-btn" title="标签打印 (Ctrl+L)" style="
                position: fixed; bottom: 80px; right: 24px; z-index: 9990;
                width: 48px; height: 48px; border-radius: 50%;
                background: #007bff; color: #fff; cursor: pointer;
                display: flex; align-items: center; justify-content: center;
                font-size: 20px; box-shadow: 0 4px 12px rgba(0,123,255,0.4);
                transition: transform 0.2s, box-shadow 0.2s;
            ">
                🏷️
            </div>
        `);

        $btn.on("mouseenter", function () {
            $(this).css({ transform: "scale(1.1)", "box-shadow": "0 6px 20px rgba(0,123,255,0.5)" });
        });
        $btn.on("mouseleave", function () {
            $(this).css({ transform: "scale(1)", "box-shadow": "0 4px 12px rgba(0,123,255,0.4)" });
        });
        $btn.on("click", open_dialog);

        $("body").append($btn);
    }

    // ─── 导出接口 ─────────────────────────────────────────────────
    solua_home.label_print.open = open_dialog;
    solua_home.label_print.close = close_dialog;

    // 页面加载后注入
    $(document).ready(function () {
        inject_floating_button();
    });
})();
