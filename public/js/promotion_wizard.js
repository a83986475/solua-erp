/**
 * Promotion Wizard for solua_home
 *
 * 功能：基于模板快速创建促销规则（特价/折扣/买赠/量大从优/会员专享）
 * 入口：Ctrl+Shift+D 或右下角浮动按钮
 */
frappe.provide("solua_home.promotion_wizard");

(function () {
    "use strict";

    let dialog_open = false;
    let $dialog = null;

    // ─── 快捷键 ───────────────────────────────────────────────────

    $(document).on("keydown", function (e) {
        if (e.ctrlKey && e.shiftKey && e.key === "D") {
            e.preventDefault();
            e.stopPropagation();
            dialog_open ? close_dialog() : open_dialog();
            return false;
        }
    });

    // ─── 对话框 ───────────────────────────────────────────────────

    function open_dialog() {
        if (dialog_open) return;
        dialog_open = true;
        if (!$dialog) create_dialog();
        $dialog.show();
        _load_promotions();
    }

    function close_dialog() {
        if (!dialog_open) return;
        dialog_open = false;
        if ($dialog) $dialog.hide();
    }

    function create_dialog() {
        $dialog = $(`
        <div id="promotion-dialog" style="
            position:fixed;top:0;left:0;width:100%;height:100%;
            background:rgba(0,0,0,0.5);z-index:9999;
            display:flex;align-items:center;justify-content:center;
        ">
        <div style="
            background:#fff;border-radius:12px;width:95vw;max-width:900px;
            max-height:90vh;display:flex;flex-direction:column;
            box-shadow:0 8px 32px rgba(0,0,0,0.3);overflow:hidden;
        ">
            <!-- 标题栏 -->
            <div style="padding:14px 20px;background:#e67e22;color:#fff;display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <h3 style="margin:0;font-size:18px;">🎯 促销管理</h3>
                    <div style="font-size:11px;opacity:0.8;margin-top:2px;">Ctrl+Shift+D 打开/关闭 · 创建/管理促销规则</div>
                </div>
                <button id="pm-close-btn" style="background:none;border:none;color:#fff;font-size:24px;cursor:pointer;">✕</button>
            </div>

            <!-- Tab 栏 -->
            <div style="display:flex;border-bottom:2px solid #e9ecef;background:#f8f9fa;">
                <button class="pm-tab active" data-tab="list" style="padding:10px 20px;border:none;background:transparent;cursor:pointer;font-size:14px;font-weight:500;color:#e67e22;border-bottom:2px solid #e67e22;margin-bottom:-2px;">📋 促销列表</button>
                <button class="pm-tab" data-tab="create" style="padding:10px 20px;border:none;background:transparent;cursor:pointer;font-size:14px;font-weight:500;color:#666;border-bottom:2px solid transparent;margin-bottom:-2px;">➕ 创建促销</button>
            </div>

            <!-- 列表 Tab -->
            <div id="pm-tab-list" style="flex:1;overflow-y:auto;padding:16px 20px;">
                <div id="pm-list-loading" style="text-align:center;color:#999;padding:40px;">加载中...</div>
                <div id="pm-list"></div>
            </div>

            <!-- 创建 Tab -->
            <div id="pm-tab-create" style="flex:1;overflow-y:auto;padding:16px 20px;display:none;">
                <div style="margin-bottom:16px;">
                    <h4 style="margin:0 0 8px;">选择促销类型</h4>
                    <div id="pm-templates" style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;"></div>
                </div>
                <div id="pm-form" style="display:none;">
                    <h4 id="pm-form-title" style="margin:0 0 12px;"></h4>
                    <div id="pm-form-fields"></div>
                    <div style="margin-top:16px;text-align:right;">
                        <button id="pm-cancel-form" style="padding:8px 16px;background:#6c757d;color:#fff;border:none;border-radius:6px;cursor:pointer;margin-right:8px;">取消</button>
                        <button id="pm-submit-form" style="padding:8px 24px;background:#28a745;color:#fff;border:none;border-radius:6px;cursor:pointer;font-weight:600;">✅ 创建</button>
                    </div>
                </div>
            </div>
        </div>
        </div>
        `);

        $("body").append($dialog);

        // 事件
        $dialog.find("#pm-close-btn").on("click", close_dialog);
        $dialog.on("click", function (e) { if (e.target === $dialog[0]) close_dialog(); });
        $dialog.find(".pm-tab").on("click", function () {
            var tab = $(this).data("tab");
            $dialog.find(".pm-tab").each(function () {
                var is_active = $(this).data("tab") === tab;
                $(this).css({
                    color: is_active ? "#e67e22" : "#666",
                    "border-bottom-color": is_active ? "#e67e22" : "transparent",
                    "font-weight": is_active ? "600" : "500",
                });
            });
            $dialog.find("#pm-tab-list").toggle(tab === "list");
            $dialog.find("#pm-tab-create").toggle(tab === "create");
        });
    }

    // ─── 促销列表 ─────────────────────────────────────────────────

    function _load_promotions() {
        var $loading = $dialog.find("#pm-list-loading");
        var $list = $dialog.find("#pm-list");
        $loading.show();
        $list.empty();

        frappe.call({
            method: "solua_home.api.promotion.list_promotions",
            args: { show_disabled: 1, limit: 50 },
            callback: function (r) {
                $loading.hide();
                var records = r.message || [];
                if (records.length === 0) {
                    $list.html('<div style="text-align:center;color:#999;padding:40px;">暂无促销规则<br><button class="pm-goto-create" style="margin-top:12px;padding:6px 16px;background:#e67e22;color:#fff;border:none;border-radius:6px;cursor:pointer;">➕ 创建第一个促销</button></div>');
                    $list.find(".pm-goto-create").on("click", function () {
                        $dialog.find(".pm-tab[data-tab='create']").click();
                    });
                    return;
                }

                var html = "";
                records.forEach(function (r) {
                    var status_badge = r.is_active
                        ? '<span style="background:#d4edda;color:#155724;padding:2px 8px;border-radius:10px;font-size:11px;">生效中</span>'
                        : r.disable
                            ? '<span style="background:#f8d7da;color:#721c24;padding:2px 8px;border-radius:10px;font-size:11px;">已停用</span>'
                            : '<span style="background:#fff3cd;color:#856404;padding:2px 8px;border-radius:10px;font-size:11px;">未到期</span>';

                    var date_info = "";
                    if (r.valid_from || r.valid_upto) {
                        date_info = (r.valid_from || "—") + " ~ " + (r.valid_upto || "∞");
                    }

                    html += `
                    <div style="padding:12px;border:1px solid #e9ecef;border-radius:8px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center;">
                        <div style="flex:1;">
                            <div style="display:flex;align-items:center;gap:8px;">
                                <span style="font-weight:600;font-size:14px;">${r.title}</span>
                                ${status_badge}
                            </div>
                            <div style="font-size:12px;color:#666;margin-top:4px;">
                                ${r.description || ''} · ${r.apply_on || ''}
                                ${r.scope ? ' · ' + r.scope : ''}
                            </div>
                            <div style="font-size:11px;color:#999;margin-top:2px;">
                                ${date_info}
                                ${r.min_qty ? ' · 最少' + r.min_qty + '件' : ''}
                            </div>
                        </div>
                        <div style="display:flex;gap:6px;">
                            ${r.is_active
                                ? '<button class="pm-toggle-btn" data-action="disable" data-name="' + r.name + '" style="padding:4px 10px;background:#f8d7da;color:#721c24;border:1px solid #f5c6cb;border-radius:4px;cursor:pointer;font-size:11px;">停用</button>'
                                : '<button class="pm-toggle-btn" data-action="enable" data-name="' + r.name + '" style="padding:4px 10px;background:#d4edda;color:#155724;border:1px solid #c3e6cb;border-radius:4px;cursor:pointer;font-size:11px;">启用</button>'
                            }
                        </div>
                    </div>`;
                });

                $list.html(html);

                // 绑定启用/停用
                $list.find(".pm-toggle-btn").on("click", function () {
                    var action = $(this).data("action");
                    var name = $(this).data("name");
                    var method = action === "disable" ? "disable_promotion" : "enable_promotion";
                    frappe.call({
                        method: "solua_home.api.promotion." + method,
                        args: { pricing_rule_name: name },
                        callback: function () {
                            frappe.show_alert({ message: action === "disable" ? "已停用" : "已启用", indicator: "green" });
                            _load_promotions();
                        },
                    });
                });
            },
        });
    }

    // ─── 创建促销 ─────────────────────────────────────────────────

    function _load_templates() {
        frappe.call({
            method: "solua_home.api.promotion.get_promotion_templates",
            callback: function (r) {
                var templates = r.message || [];
                var $tpls = $dialog.find("#pm-templates");
                var icons = {
                    "item_discount": "🏷️",
                    "category_discount": "📂",
                    "fixed_price": "💰",
                    "buy_get_free": "🎁",
                    "qty_discount": "📊",
                    "member_discount": "👑",
                };
                var colors = {
                    "item_discount": "#e74c3c",
                    "category_discount": "#3498db",
                    "fixed_price": "#27ae60",
                    "buy_get_free": "#e67e22",
                    "qty_discount": "#9b59b6",
                    "member_discount": "#f1c40f",
                };

                var html = "";
                templates.forEach(function (t) {
                    html += `
                    <div class="pm-tpl-card" data-key="${t.key}" style="
                        padding:14px;border:2px solid #e9ecef;border-radius:10px;
                        cursor:pointer;text-align:center;transition:all 0.15s;
                    ">
                        <div style="font-size:28px;margin-bottom:6px;">${icons[t.key] || '🎯'}</div>
                        <div style="font-weight:600;font-size:13px;">${t.name}</div>
                        <div style="font-size:11px;color:#888;margin-top:4px;">${t.description}</div>
                    </div>`;
                });
                $tpls.html(html);

                // 绑定点击
                $tpls.find(".pm-tpl-card").on("mouseenter", function () {
                    $(this).css({ "border-color": "#e67e22", "background": "#fff8f0" });
                }).on("mouseleave", function () {
                    $(this).css({ "border-color": "#e9ecef", "background": "" });
                }).on("click", function () {
                    _show_form($(this).data("key"));
                });
            },
        });
    }

    function _show_form(key) {
        var $form = $dialog.find("#pm-form");
        var $fields = $dialog.find("#pm-form-fields");

        var titles = {
            "item_discount": "🏷️ 单品特价",
            "category_discount": "📂 分类折扣",
            "fixed_price": "💰 固定售价",
            "buy_get_free": "🎁 买赠",
            "qty_discount": "📊 量大从优",
            "member_discount": "👑 会员专享价",
        };

        $dialog.find("#pm-form-title").text(titles[key] || "创建促销");
        $form.show();
        $dialog.find("#pm-templates").hide();

        var html = `
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
            <div>
                <label style="font-size:13px;font-weight:500;">促销名称 *</label>
                <input id="pm-f-title" type="text" placeholder="如：CR-001 限时特价" style="width:100%;padding:8px;border:1px solid #dee2e6;border-radius:6px;margin-top:4px;" />
            </div>
            <div>
                <label style="font-size:13px;font-weight:500;">有效期</label>
                <div style="display:flex;gap:6px;margin-top:4px;">
                    <input id="pm-f-from" type="date" style="flex:1;padding:8px;border:1px solid #dee2e6;border-radius:6px;" />
                    <span style="padding:8px 0;">至</span>
                    <input id="pm-f-to" type="date" style="flex:1;padding:8px;border:1px solid #dee2e6;border-radius:6px;" />
                </div>
            </div>
        </div>`;

        // 根据模板类型显示不同字段
        if (key === "item_discount" || key === "fixed_price") {
            html += `
            <div style="margin-top:12px;">
                <label style="font-size:13px;font-weight:500;">物料编码（多个用逗号分隔）*</label>
                <input id="pm-f-items" type="text" placeholder="如：CR-001-BR,CR-001-AZ" style="width:100%;padding:8px;border:1px solid #dee2e6;border-radius:6px;margin-top:4px;" />
            </div>`;
        }

        if (key === "category_discount") {
            html += `
            <div style="margin-top:12px;">
                <label style="font-size:13px;font-weight:500;">商品分类*</label>
                <input id="pm-f-item-groups" type="text" placeholder="如：窗帘" style="width:100%;padding:8px;border:1px solid #dee2e6;border-radius:6px;margin-top:4px;" />
            </div>`;
        }

        if (key === "item_discount" || key === "category_discount" || key === "qty_discount" || key === "member_discount") {
            html += `
            <div style="margin-top:12px;">
                <label style="font-size:13px;font-weight:500;">折扣百分比 * </label>
                <input id="pm-f-discount" type="number" min="1" max="99" value="10" style="width:120px;padding:8px;border:1px solid #dee2e6;border-radius:6px;margin-top:4px;" />
                <span style="font-size:12px;color:#666;">%</span>
            </div>`;
        }

        if (key === "fixed_price") {
            html += `
            <div style="margin-top:12px;">
                <label style="font-size:13px;font-weight:500;">固定价格 *</label>
                <input id="pm-f-rate" type="number" min="0" step="0.01" style="width:150px;padding:8px;border:1px solid #dee2e6;border-radius:6px;margin-top:4px;" />
            </div>`;
        }

        if (key === "qty_discount") {
            html += `
            <div style="margin-top:12px;">
                <label style="font-size:13px;font-weight:500;">最少购买数量 *</label>
                <input id="pm-f-min-qty" type="number" min="1" value="5" style="width:100px;padding:8px;border:1px solid #dee2e6;border-radius:6px;margin-top:4px;" />
            </div>`;
        }

        if (key === "buy_get_free") {
            html += `
            <div style="margin-top:12px;">
                <label style="font-size:13px;font-weight:500;">购买数量 *</label>
                <input id="pm-f-min-qty" type="number" min="1" value="3" style="width:100px;padding:8px;border:1px solid #dee2e6;border-radius:6px;margin-top:4px;" />
            </div>
            <div style="margin-top:8px;">
                <label style="font-size:13px;font-weight:500;">赠送数量</label>
                <input id="pm-f-free-qty" type="number" min="1" value="1" style="width:100px;padding:8px;border:1px solid #dee2e6;border-radius:6px;margin-top:4px;" />
            </div>`;
        }

        $fields.html(html);

        // 设置默认日期
        var today = new Date().toISOString().split("T")[0];
        $dialog.find("#pm-f-from").val(today);
    }

    function _submit_form() {
        var key = $dialog.find(".pm-tpl-card:hover").data("key") || _get_selected_template_key();
        if (!key) {
            frappe.show_alert({ message: "请先选择促销类型", indicator: "orange" });
            return;
        }

        var config = {
            title: $dialog.find("#pm-f-title").val() || "",
            valid_from: $dialog.find("#pm-f-from").val() || "",
            valid_upto: $dialog.find("#pm-f-to").val() || "",
        };

        if (!config.title) {
            frappe.show_alert({ message: "请输入促销名称", indicator: "orange" });
            return;
        }

        // 物料列表
        var itemsStr = $dialog.find("#pm-f-items").val();
        if (itemsStr) {
            config.items = itemsStr.split(",").map(function (s) { return s.trim(); }).filter(Boolean);
        }

        // 分类列表
        var groupsStr = $dialog.find("#pm-f-item-groups").val();
        if (groupsStr) {
            config.item_groups = groupsStr.split(",").map(function (s) { return s.trim(); }).filter(Boolean);
        }

        // 折扣
        var discount = $dialog.find("#pm-f-discount").val();
        if (discount) config.discount_percentage = parseFloat(discount);

        // 固定价
        var rate = $dialog.find("#pm-f-rate").val();
        if (rate) config.rate = parseFloat(rate);

        // 数量
        var minQty = $dialog.find("#pm-f-min-qty").val();
        if (minQty) config.min_qty = parseInt(minQty);

        var freeQty = $dialog.find("#pm-f-free-qty").val();
        if (freeQty) config.free_qty = parseInt(freeQty);

        frappe.call({
            method: "solua_home.api.promotion.create_promotion",
            args: { template_key: key, config: JSON.stringify(config) },
            callback: function (r) {
                var msg = r.message || {};
                frappe.show_alert({ message: msg.message || "创建成功", indicator: "green" });
                // 回到列表
                $dialog.find(".pm-tab[data-tab='list']").click();
                _load_promotions();
                // 重置表单
                $dialog.find("#pm-form").hide();
                $dialog.find("#pm-templates").show();
            },
            error: function (r) {
                frappe.show_alert({ message: "创建失败：" + (r._message || "未知错误"), indicator: "red" });
            },
        });
    }

    function _get_selected_template_key() {
        var $hovered = $dialog.find(".pm-tpl-card:hover");
        if ($hovered.length) return $hovered.data("key");
        // fallback: 看哪个被高亮
        var $selected = $dialog.find(".pm-tpl-card[style*='e67e22']");
        if ($selected.length) return $selected.data("key");
        return null;
    }

    // ─── 浮动按钮 ─────────────────────────────────────────────────

    function inject_floating_button() {
        if (window.location.pathname.includes("/point-of-sale")) return;

        var $btn = $('<div id="pm-float-btn" title="促销管理 (Ctrl+Shift+D)" style="' +
            'position:fixed;bottom:140px;right:24px;z-index:9990;' +
            'width:48px;height:48px;border-radius:50%;' +
            'background:#e67e22;color:#fff;cursor:pointer;' +
            'display:flex;align-items:center;justify-content:center;' +
            'font-size:20px;box-shadow:0 4px 12px rgba(230,126,34,0.4);' +
            'transition:transform 0.2s,box-shadow 0.2s;">🎯</div>');

        $btn.on("mouseenter", function () {
            $(this).css({ transform: "scale(1.1)", "box-shadow": "0 6px 20px rgba(230,126,34,0.5)" });
        });
        $btn.on("mouseleave", function () {
            $(this).css({ transform: "scale(1)", "box-shadow": "0 4px 12px rgba(230,126,34,0.4)" });
        });
        $btn.on("click", open_dialog);
        $("body").append($btn);
    }

    // ─── 导出接口 ─────────────────────────────────────────────────
    solua_home.promotion_wizard.open = open_dialog;
    solua_home.promotion_wizard.close = close_dialog;

    $(document).ready(function () {
        inject_floating_button();
        // 绑定表单提交（延迟绑定，等 DOM 就绪）
        $(document).on("click", "#pm-submit-form", _submit_form);
        $(document).on("click", "#pm-cancel-form", function () {
            $dialog.find("#pm-form").hide();
            $dialog.find("#pm-templates").show();
        });
        $(document).on("click", ".pm-goto-create", function () {
            $dialog.find(".pm-tab[data-tab='create']").click();
            _load_templates();
        });
        // Tab 切换时加载模板
        $(document).on("click", ".pm-tab[data-tab='create']", function () {
            _load_templates();
        });
    });
})();
