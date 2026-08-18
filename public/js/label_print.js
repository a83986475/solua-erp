/**
 * Label Printing for solua_home (Enhanced v2)
 *
 * 功能：扫码/搜索物料 → 选模板 → 设数量 → 批量打印标签
 * 新增：物料图片预览、库存数量显示、打印历史记录
 *
 * 快捷键：
 *   Ctrl+L    打开/关闭标签打印界面
 *   F2        聚焦搜索框
 *   Enter     搜索（搜索框内）
 *   Ctrl+P    打印选中物料
 *   Escape    关闭界面 / 清空搜索
 *   ↑↓        导航搜索结果
 *   Space     切换选中/取消选中
 *   +/-       增减选中项数量
 *   Ctrl+A    全选/取消全选
 *   Ctrl+H    切换到打印历史 Tab
 */
frappe.provide("solua_home.label_print");

(function () {
    "use strict";

    let dialog_open = false;
    let $dialog = null;
    let _current_tab = "search"; // "search" | "history"

    // ─── 全局快捷键 ───────────────────────────────────────────────

    $(document).on("keydown", function (e) {
        if (e.ctrlKey && e.key === "l") {
            e.preventDefault();
            e.stopPropagation();
            dialog_open ? close_dialog() : open_dialog();
            return false;
        }
        if (!dialog_open) return;

        if (e.key === "Escape") { e.preventDefault(); close_dialog(); return false; }
        if (e.key === "F2") { e.preventDefault(); focus_search(); return false; }
        if (e.ctrlKey && e.key === "p") { e.preventDefault(); do_print(); return false; }

        // Ctrl+H → 切换到历史 Tab
        if (e.ctrlKey && e.key === "h" && !_is_input_focused()) {
            e.preventDefault();
            _switch_tab("history");
            return false;
        }

        if (e.ctrlKey && e.key === "a" && !_is_input_focused()) {
            e.preventDefault(); toggle_select_all(); return false;
        }
        if ((e.key === "ArrowUp" || e.key === "ArrowDown") && !_is_input_focused()) {
            e.preventDefault();
            navigate_results(e.key === "ArrowDown" ? 1 : -1);
            return false;
        }
        if (e.key === " " && !_is_input_focused()) {
            e.preventDefault(); toggle_current_item(); return false;
        }
        if ((e.key === "+" || e.key === "=" || e.key === "-") && !_is_input_focused()) {
            e.preventDefault(); adjust_quantity(e.key === "-" ? -1 : 1); return false;
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
        if (!$dialog) create_dialog();
        $dialog.show();
        _switch_tab("search");
        focus_search();
        _load_print_formats();
    }

    function close_dialog() {
        if (!dialog_open) return;
        dialog_open = false;
        if ($dialog) $dialog.hide();
        // 关闭图片预览
        _close_image_preview();
    }

    function focus_search() {
        setTimeout(function () {
            var $s = $dialog.find("#lp-search-input");
            if ($s.length) { $s[0].focus(); $s[0].select(); }
        }, 100);
    }

    function create_dialog() {
        $dialog = $(`
        <div id="label-print-dialog" style="
            position:fixed;top:0;left:0;width:100%;height:100%;
            background:rgba(0,0,0,0.5);z-index:9999;
            display:flex;align-items:center;justify-content:center;
        ">
        <div style="
            background:#fff;border-radius:12px;width:95vw;max-width:1100px;
            max-height:90vh;display:flex;flex-direction:column;
            box-shadow:0 8px 32px rgba(0,0,0,0.3);overflow:hidden;
        ">
            <!-- 标题栏 -->
            <div style="padding:14px 20px;background:#007bff;color:#fff;display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <h3 style="margin:0;font-size:18px;">🏷️ 标签打印</h3>
                    <div style="font-size:11px;opacity:0.8;margin-top:2px;">
                        Ctrl+L 开关 · F2 搜索 · Ctrl+P 打印 · Ctrl+H 历史 · Esc 关闭
                    </div>
                </div>
                <button id="lp-close-btn" style="background:none;border:none;color:#fff;font-size:24px;cursor:pointer;padding:4px 8px;">✕</button>
            </div>

            <!-- Tab 栏 -->
            <div style="display:flex;border-bottom:2px solid #e9ecef;background:#f8f9fa;">
                <button class="lp-tab active" data-tab="search" style="
                    padding:10px 20px;border:none;background:transparent;cursor:pointer;
                    font-size:14px;font-weight:500;color:#007bff;border-bottom:2px solid #007bff;
                    margin-bottom:-2px;
                ">🔍 搜索物料</button>
                <button class="lp-tab" data-tab="history" style="
                    padding:10px 20px;border:none;background:transparent;cursor:pointer;
                    font-size:14px;font-weight:500;color:#666;border-bottom:2px solid transparent;
                    margin-bottom:-2px;
                ">📋 打印历史 <kbd style="font-size:10px;opacity:0.6">Ctrl+H</kbd></button>
            </div>

            <!-- 搜索 Tab -->
            <div id="lp-tab-search" style="flex:1;display:flex;flex-direction:column;overflow:hidden;">
                <!-- 搜索栏 -->
                <div style="padding:12px 20px;border-bottom:1px solid #e9ecef;">
                    <div style="display:flex;gap:10px;align-items:center;">
                        <input id="lp-search-input" type="text" placeholder="扫码或输入物料编码/名称..."
                            style="flex:1;padding:10px 14px;font-size:16px;border:2px solid #dee2e6;border-radius:8px;outline:none;"
                            autocomplete="off" />
                        <button id="lp-search-btn" style="padding:10px 20px;background:#28a745;color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:14px;">🔍 搜索</button>
                    </div>
                </div>
                <!-- 结果区 -->
                <div style="flex:1;overflow-y:auto;padding:12px 20px;min-height:150px;">
                    <div id="lp-hint" style="text-align:center;color:#999;padding:40px 20px;">
                        <div style="font-size:48px;margin-bottom:12px;">🏷️</div>
                        <div>扫描条码或输入关键词搜索物料</div>
                        <div style="margin-top:8px;font-size:12px;color:#bbb;">支持：条码、编码、名称、中文名、简称</div>
                    </div>
                    <div id="lp-results" style="display:none;">
                        <div id="lp-results-count" style="font-size:13px;color:#666;margin-bottom:8px;"></div>
                        <div id="lp-items"></div>
                    </div>
                    <div id="lp-selected-summary" style="display:none;margin-top:12px;padding:10px;background:#e8f5e9;border-radius:8px;border:1px solid #c8e6c9;">
                        <div style="font-weight:600;margin-bottom:4px;">📋 已选 <span id="lp-selected-count">0</span> 种，共 <span id="lp-total-qty">0</span> 张</div>
                        <div id="lp-selected-list" style="font-size:12px;color:#555;"></div>
                    </div>
                </div>
            </div>

            <!-- 历史 Tab -->
            <div id="lp-tab-history" style="flex:1;display:none;flex-direction:column;overflow:hidden;">
                <div style="flex:1;overflow-y:auto;padding:12px 20px;">
                    <div id="lp-history-loading" style="text-align:center;color:#999;padding:40px;">加载中...</div>
                    <div id="lp-history-list"></div>
                </div>
                <div style="padding:10px 20px;border-top:1px solid #e9ecef;text-align:center;">
                    <button id="lp-history-refresh" style="padding:6px 16px;background:#6c757d;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:13px;">🔄 刷新</button>
                </div>
            </div>

            <!-- 底部操作栏（仅搜索 Tab 显示） -->
            <div id="lp-footer" style="
                padding:12px 20px;border-top:1px solid #e9ecef;
                display:flex;justify-content:space-between;align-items:center;background:#f8f9fa;
            ">
                <div style="display:flex;gap:10px;align-items:center;">
                    <label style="font-size:13px;font-weight:500;">格式：</label>
                    <select id="lp-format" style="padding:5px 8px;border:1px solid #dee2e6;border-radius:6px;font-size:13px;min-width:140px;"></select>
                    <label style="font-size:13px;font-weight:500;margin-left:8px;">数量：</label>
                    <input id="lp-qty" type="number" value="1" min="1" max="999" style="width:55px;padding:5px;border:1px solid #dee2e6;border-radius:6px;font-size:13px;text-align:center;" />
                </div>
                <div style="display:flex;gap:8px;">
                    <button id="lp-select-all-btn" style="padding:7px 14px;background:#6c757d;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:13px;">全选</button>
                    <button id="lp-clear-btn" style="padding:7px 14px;background:#ffc107;color:#333;border:none;border-radius:6px;cursor:pointer;font-size:13px;">清空</button>
                    <button id="lp-print-btn" style="padding:7px 20px;background:#007bff;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:14px;font-weight:600;">🖨️ 打印 <kbd style="font-size:10px;opacity:0.7">Ctrl+P</kbd></button>
                </div>
            </div>
        </div>
        </div>
        `);

        $("body").append($dialog);

        // ─── 事件绑定 ─────────────────────────────────────────────
        $dialog.find("#lp-close-btn").on("click", close_dialog);
        $dialog.on("click", function (e) { if (e.target === $dialog[0]) close_dialog(); });

        // Tab 切换
        $dialog.find(".lp-tab").on("click", function () {
            _switch_tab($(this).data("tab"));
        });

        // 搜索
        $dialog.find("#lp-search-input").on("keydown", function (e) {
            if (e.key === "Enter") { e.preventDefault(); do_search(); }
        });
        $dialog.find("#lp-search-btn").on("click", do_search);

        // 数量
        $dialog.find("#lp-qty").on("change", update_selected_summary);

        // 操作按钮
        $dialog.find("#lp-print-btn").on("click", do_print);
        $dialog.find("#lp-clear-btn").on("click", clear_search);
        $dialog.find("#lp-select-all-btn").on("click", toggle_select_all);

        // 历史刷新
        $dialog.find("#lp-history-refresh").on("click", _load_history);
    }

    // ─── Tab 切换 ─────────────────────────────────────────────────

    function _switch_tab(tab) {
        _current_tab = tab;
        $dialog.find(".lp-tab").each(function () {
            var is_active = $(this).data("tab") === tab;
            $(this).css({
                color: is_active ? "#007bff" : "#666",
                "border-bottom-color": is_active ? "#007bff" : "transparent",
                "font-weight": is_active ? "600" : "500",
            });
        });

        if (tab === "search") {
            $dialog.find("#lp-tab-search").css("display", "flex");
            $dialog.find("#lp-tab-history").css("display", "none");
            $dialog.find("#lp-footer").show();
            focus_search();
        } else {
            $dialog.find("#lp-tab-search").css("display", "none");
            $dialog.find("#lp-tab-history").css("display", "flex");
            $dialog.find("#lp-footer").hide();
            _load_history();
        }
    }

    // ─── 搜索 ─────────────────────────────────────────────────────

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
        $dialog.find("#lp-results-count").text("找到 " + _current_results.length + " 个物料");

        var html = "";
        _current_results.forEach(function (item, idx) {
            // 图片：大图 + 点击预览
            var img_html;
            if (item.image) {
                img_html = `<div class="lp-img-wrap" data-src="${item.image}" style="
                    width:52px;height:52px;border-radius:8px;overflow:hidden;
                    cursor:pointer;flex-shrink:0;position:relative;
                    border:1px solid #e0e0e0;
                ">
                    <img src="${item.image}" style="width:100%;height:100%;object-fit:cover;" />
                    <div style="position:absolute;bottom:0;right:0;background:rgba(0,0,0,0.5);color:#fff;font-size:9px;padding:1px 3px;border-radius:3px 0 0 0;">🔍</div>
                </div>`;
            } else {
                img_html = `<div style="width:52px;height:52px;background:#f0f0f0;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#bbb;font-size:22px;flex-shrink:0;border:1px solid #e0e0e0;">📦</div>`;
            }

            // 条码标签
            var bc_text = "";
            if (item.barcodes && item.barcodes.length > 0) {
                bc_text = item.barcodes.slice(0, 3).map(function (b) {
                    return '<span style="background:#e3f2fd;padding:1px 5px;border-radius:3px;font-size:10px;">' + b.barcode + '</span>';
                }).join(" ");
                if (item.barcodes.length > 3) bc_text += '<span style="font-size:10px;color:#999;">+' + (item.barcodes.length - 3) + '</span>';
            }

            // 类型标签
            var variant_tag = "";
            if (item.is_template) {
                variant_tag = '<span style="background:#fff3cd;color:#856404;padding:1px 5px;border-radius:3px;font-size:10px;margin-left:4px;">模板</span>';
            } else if (item.is_variant) {
                variant_tag = '<span style="background:#d4edda;color:#155724;padding:1px 5px;border-radius:3px;font-size:10px;margin-left:4px;">变体</span>';
            }

            // 库存指示器
            var stock = item.stock_qty || 0;
            var stock_html;
            if (stock > 0) {
                stock_html = '<span style="color:#28a745;font-weight:600;font-size:13px;">📦 ' + stock + '</span>';
            } else {
                stock_html = '<span style="color:#dc3545;font-size:12px;">⚠️ 无库存</span>';
            }

            html += `
            <div class="lp-item" data-index="${idx}" style="
                display:flex;align-items:center;gap:10px;
                padding:8px 10px;border:1px solid #e9ecef;border-radius:8px;
                margin-bottom:5px;cursor:pointer;transition:all 0.15s;
            ">
                <input type="checkbox" class="lp-check" data-index="${idx}" style="width:16px;height:16px;cursor:pointer;" />
                ${img_html}
                <div style="flex:1;min-width:0;">
                    <div style="display:flex;align-items:center;">
                        <span style="font-weight:600;font-size:13px;">
                            ${item.custom_chinese_name || item.custom_pos_short_name || item.item_name}
                        </span>
                        ${variant_tag}
                    </div>
                    <div style="font-size:11px;color:#888;margin-top:1px;">
                        ${item.item_code} · ${item.item_group || ''}
                    </div>
                    <div style="margin-top:2px;display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
                        ${bc_text}
                    </div>
                </div>
                <div style="text-align:right;white-space:nowrap;min-width:80px;">
                    <div style="font-weight:600;color:#007bff;font-size:14px;">
                        ${item.standard_rate ? frappe.utils.flt(item.standard_rate).toLocaleString() : '—'}
                    </div>
                    <div style="margin-top:2px;">${stock_html}</div>
                </div>
            </div>`;
        });

        $items.html(html);

        // 绑定事件
        $items.find(".lp-item").on("click", function (e) {
            if (!$(e.target).hasClass("lp-check") && !$(e.target).closest(".lp-img-wrap").length) {
                $(this).find(".lp-check").prop("checked", !$(this).find(".lp-check").prop("checked"));
            }
            update_selected_summary();
        });

        $items.find(".lp-check").on("change", update_selected_summary);

        // 图片点击预览
        $items.find(".lp-img-wrap").on("click", function (e) {
            e.stopPropagation();
            _open_image_preview($(this).data("src"));
        });

        _cursor_index = -1;
    }

    // ─── 图片预览浮层 ─────────────────────────────────────────────

    function _open_image_preview(src) {
        _close_image_preview();
        var $overlay = $(`
            <div id="lp-img-preview" style="
                position:fixed;top:0;left:0;width:100%;height:100%;
                background:rgba(0,0,0,0.7);z-index:10000;
                display:flex;align-items:center;justify-content:center;cursor:pointer;
            ">
                <div style="background:#fff;border-radius:12px;padding:8px;max-width:80vw;max-height:80vh;box-shadow:0 8px 32px rgba(0,0,0,0.4);">
                    <img src="${src}" style="max-width:75vw;max-height:75vh;object-fit:contain;border-radius:8px;" />
                </div>
                <div style="position:absolute;top:16px;right:20px;color:#fff;font-size:28px;cursor:pointer;">✕</div>
            </div>
        `);
        $overlay.on("click", function (e) {
            if (e.target === $overlay[0] || $(e.target).closest("#lp-img-preview > div").length === 0 || $(e.target).is(".fa")) {
                _close_image_preview();
            }
        });
        $("body").append($overlay);
    }

    function _close_image_preview() {
        $("#lp-img-preview").remove();
    }

    // ─── 打印历史 ─────────────────────────────────────────────────

    function _load_history() {
        var $loading = $dialog.find("#lp-history-loading");
        var $list = $dialog.find("#lp-history-list");
        $loading.show();
        $list.empty();

        frappe.call({
            method: "solua_home.api.label_print.get_print_history",
            args: { limit: 20 },
            callback: function (r) {
                $loading.hide();
                var records = r.message || [];
                if (records.length === 0) {
                    $list.html('<div style="text-align:center;color:#999;padding:40px;">暂无打印记录</div>');
                    return;
                }

                var html = "";
                records.forEach(function (rec) {
                    var time = rec.creation ? frappe.datetime.str_to_user(rec.creation) : "";
                    html += `
                    <div style="padding:10px 12px;border:1px solid #e9ecef;border-radius:8px;margin-bottom:6px;display:flex;justify-content:space-between;align-items:center;">
                        <div style="flex:1;min-width:0;">
                            <div style="font-size:13px;font-weight:500;color:#333;">${rec.summary || rec.content || '(无内容)'}</div>
                            <div style="font-size:11px;color:#999;margin-top:2px;">
                                ${time} · ${rec.user || ''}
                            </div>
                        </div>
                        <button class="lp-reprint-btn" data-item="${rec.item_code || ''}" style="
                            padding:4px 10px;background:#e3f2fd;color:#007bff;border:1px solid #bbdefb;
                            border-radius:4px;cursor:pointer;font-size:11px;white-space:nowrap;margin-left:8px;
                        ">🔄 重打</button>
                    </div>`;
                });
                $list.html(html);

                // 绑定重打按钮
                $list.find(".lp-reprint-btn").on("click", function () {
                    var itemCode = $(this).data("item");
                    if (itemCode) {
                        _switch_tab("search");
                        $dialog.find("#lp-search-input").val(itemCode);
                        do_search();
                    }
                });
            },
            error: function () {
                $loading.hide();
                $list.html('<div style="text-align:center;color:#dc3545;padding:40px;">加载失败</div>');
            },
        });
    }

    // ─── 选中汇总 ─────────────────────────────────────────────────

    function get_selected_items() {
        var selected = [];
        var qty = parseInt($dialog.find("#lp-qty").val()) || 1;
        $dialog.find(".lp-check:checked").each(function () {
            var idx = parseInt($(this).data("index"));
            if (idx >= 0 && idx < _current_results.length) {
                selected.push({ item: _current_results[idx], qty: qty });
            }
        });
        return selected;
    }

    function update_selected_summary() {
        var selected = get_selected_items();
        var $summary = $dialog.find("#lp-selected-summary");
        if (selected.length === 0) { $summary.hide(); return; }

        $summary.show();
        var total_qty = 0;
        var list_html = "";
        selected.forEach(function (s) {
            total_qty += s.qty;
            var name = s.item.custom_chinese_name || s.item.item_name || s.item.item_code;
            list_html += '<span style="display:inline-block;margin:2px 3px;background:#fff;padding:2px 6px;border-radius:4px;border:1px solid #c8e6c9;font-size:12px;">' + name + ' ×' + s.qty + '</span>';
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
        var total_labels = 0;
        selected.forEach(function (s) { total_labels += s.qty; });

        frappe.show_alert({ message: "正在生成 " + selected.length + " 种物料的标签...", indicator: "blue" });

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
                    // 记录打印历史
                    _record_history(item_codes, format_name, quantities, total_labels);
                } else {
                    frappe.show_alert({ message: "标签生成失败", indicator: "red" });
                }
            },
            error: function (r) {
                frappe.show_alert({ message: "生成失败：" + (r._message || "未知错误"), indicator: "red" });
            },
        });
    }

    function _record_history(item_codes, format_name, quantities, total) {
        frappe.call({
            method: "solua_home.api.label_print.record_print_history",
            args: {
                item_codes: JSON.stringify(item_codes),
                format_name: format_name,
                quantities: JSON.stringify(quantities),
                total_labels: total,
            },
            error: function () { /* 静默失败 */ },
        });
    }

    function _open_print_window(html, count) {
        var print_win = window.open("", "_blank", "width=800,height=600");
        if (!print_win) {
            frappe.show_alert({ message: "弹出窗口被浏览器拦截，请允许弹窗后重试", indicator: "orange" });
            return;
        }
        print_win.document.write(html);
        print_win.document.close();
        print_win.onload = function () {
            setTimeout(function () { print_win.print(); }, 500);
        };
        frappe.show_alert({ message: "已生成 " + count + " 张标签，打印窗口已弹出", indicator: "green" });
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
        var $items = $dialog.find(".lp-item");
        $items.css("background", "");
        if (_cursor_index >= 0 && _cursor_index < $items.length) {
            $items.eq(_cursor_index).css("background", "#e3f2fd");
        }
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
                        $sel.append('<option value="' + f.name + '">' + f.name + '</option>');
                    });
                }
            },
        });
    }

    // ─── 浮动按钮 ─────────────────────────────────────────────────

    function inject_floating_button() {
        if (window.location.pathname.includes("/point-of-sale")) return;

        var $btn = $('<div id="lp-float-btn" title="标签打印 (Ctrl+L)" style="' +
            'position:fixed;bottom:80px;right:24px;z-index:9990;' +
            'width:48px;height:48px;border-radius:50%;' +
            'background:#007bff;color:#fff;cursor:pointer;' +
            'display:flex;align-items:center;justify-content:center;' +
            'font-size:20px;box-shadow:0 4px 12px rgba(0,123,255,0.4);' +
            'transition:transform 0.2s,box-shadow 0.2s;">🏷️</div>');

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

    $(document).ready(function () {
        inject_floating_button();
    });
})();
