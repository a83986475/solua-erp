frappe.pages["a4-print-designer"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("A4 打印设计器"), single_column: true });
	const types = ["Sales Order", "Sales Invoice", "Delivery Note", "Pick List"];
	const labels = {
		image: "FOTO", name: "Artigo / 商品", spu: "SPU", sku: "SKU / 货号", color_code: "Cor",
		barcode: "EAN / 条码", description: "Descrição / 描述", ordered: "Qt. pedido / 已订购",
		remaining: "Qt. restante / 剩余", qty: "Qt/数量", picked: "Qt separado / 已拣", uom: "Un.", rate: "Prc",
		amount: "Valor / 金额", additional_notes: "补充说明", trace: "Rastreabilidade / 追溯", warehouse: "Armazém / 仓库", order: "S.O. / 订单",
	};
	const featureLabels = { payment_schedule: "付款计划", color_qr: "色卡二维码", footer: "页脚页码" };
	const base = ["image", "name", "spu", "sku", "color_code", "barcode", "description"];
	const columns = {
		"Sales Order": ["additional_notes", "qty", "uom", "rate", "amount"],
		"Sales Invoice": ["qty", "uom", "rate", "amount"],
		"Delivery Note": ["ordered", "remaining", "qty", "uom", "rate", "amount", "trace"],
		"Pick List": ["qty", "picked", "uom", "warehouse", "order"],
	};
	const defaults = {
		"Sales Order": { image: 7, name: 12, spu: 8, sku: 12, color_code: 8, barcode: 11, description: 16, additional_notes: 10, qty: 5, uom: 5, rate: 4, amount: 5 },
		"Sales Invoice": { image: 7, name: 12, spu: 8, sku: 12, color_code: 8, barcode: 11, description: 16, qty: 5, uom: 5, rate: 4, amount: 5 },
		"Delivery Note": { image: 6, name: 10, spu: 8, sku: 10, color_code: 6, barcode: 8, description: 11, ordered: 9, remaining: 9, qty: 8, uom: 5, rate: 5, amount: 6, trace: 5 },
		"Pick List": { image: 8, name: 14, spu: 8, sku: 12, color_code: 7, barcode: 11, description: 16, qty: 7, picked: 7, uom: 5, warehouse: 8, order: 5 },
	};
	const defaultFeatures = { payment_schedule: false, color_qr: false, additional_notes: false, footer: true, legacy_warning: false, legacy_controls: false };
	const defaultControlDefaults = { custom_print_color_images: true, custom_print_item_name: true, custom_print_sku: true, custom_print_color_code: true, custom_print_cor: true, custom_print_description: true, custom_print_additional_notes: true };
	const defaultSettings = { fontSize: 9, titleSize: 18, headSize: 9, lineHeight: 1.35, cellPadding: 1.5, pageMargin: 12, logoWidth: 32, logoHeight: 20, titleColor: "#99732c", headBg: "#f5f1e9", itemBorders: true };
	const config = {
		doctype: types[0],
		visible: Object.fromEntries(types.map(type => [type, Object.fromEntries([...base, ...columns[type]].map(key => [key, key !== "image" && key !== "additional_notes"]))])),
		widths: Object.fromEntries(types.map(type => [type, JSON.parse(JSON.stringify(defaults[type]))])),
		settings: { ...defaultSettings, itemBordersByDoctype: Object.fromEntries(types.map(type => [type, true])) },
		features: { ...defaultFeatures },
		control_defaults: { ...defaultControlDefaults },
	};
	const currentSettings = () => {
		const map = config.settings.itemBordersByDoctype || (config.settings.itemBordersByDoctype = Object.fromEntries(types.map(type => [type, !!config.settings.itemBorders])));
		config.settings.itemBorders = map[config.doctype] !== undefined ? !!map[config.doctype] : true;
		return config.settings;
	};
	config.visible["Delivery Note"].qty = false;
	let preview = null;
	let legacyHtml = "";
	let canSave = false;
	let canPublish = false;
	let editingMode = "designer";
	let formatMeta = {};

	page.main.html(`<style>
 .a4d{display:grid;grid-template-columns:330px 1fr;min-height:calc(100vh - 120px);color:#25313a}.a4d-panel{padding:18px;background:white;border-right:1px solid #ccd3d8;overflow:auto}.a4d-panel h2{font-size:15px;margin:12px 0}.a4d-field{display:grid;grid-template-columns:1fr 115px;align-items:center;gap:8px;margin:8px 0}.a4d-field input,.a4d-field select{width:100%}.a4d-checks,.a4d-features{display:grid;grid-template-columns:1fr 1fr;gap:6px}.a4d-widths{display:grid;grid-template-columns:1fr 75px;gap:6px 10px;align-items:center}.a4d-widths input{width:75px}.a4d-group{border-top:1px solid #d7dde1;padding:10px 0}.a4d-actions{display:grid;gap:8px}.a4d-stage{background:#eef1f3;padding:20px;overflow:auto}.a4d-paper{width:210mm;min-height:297mm;margin:auto;padding:12mm;background:#fff;box-shadow:0 2px 18px #0002;box-sizing:border-box;color:#25313a;font-size:9pt;overflow-wrap:anywhere}.a4d-paper h1{font-size:18pt;color:#99732c;text-align:center}.a4d-paper table{width:100%;border-collapse:collapse;table-layout:fixed}.a4d-paper .a4d-items{font-size:9pt;line-height:1.35}.a4d-paper th,.a4d-paper td{padding:1.5mm;border:1px solid #aeb8be;vertical-align:top;overflow-wrap:anywhere}.a4d-paper th{background:#f5f1e9;font-weight:700}.a4d-paper thead{display:table-header-group}.a4d-paper tbody tr,.a4d-paper tbody tr td{break-inside:avoid;page-break-inside:avoid}.a4d-paper .a4d-brand{margin-bottom:4mm}.a4d-paper .a4d-brand td{border:0;padding:0;vertical-align:middle}.a4d-photo{width:min(12mm,100%);aspect-ratio:1;object-fit:cover;display:block}.a4d-mock{width:min(12mm,100%);aspect-ratio:1;background:linear-gradient(135deg,#e8ecef,#aeb7bd);border:1px solid #c5ccd0;box-shadow:0 1mm 2mm #25313a40}.a4d-totals{page-break-inside:avoid;margin-top:3mm;border:1px solid #d8c49b;background:#f5f1e9;padding:2mm}.a4d-total{text-align:right;margin:0;font-size:11pt;font-weight:700}.a4d-cash-summary{border-top:1px solid #d8c49b;margin-top:2mm;padding-top:2mm;text-align:right}.a4d-cash-summary div{margin-top:1mm}.a4d-status{padding:8px;background:#f6f7f8;white-space:pre-wrap}.a4d-meta{margin:10px 0}.a4d-meta td{width:50%}.a4d-tools{display:grid;grid-template-columns:1fr 1fr;gap:8px}.a4d-tools button{width:100%}.a4d-legacy-frame{width:100%;min-height:calc(100vh - 180px);border:0;background:white}@media(max-width:1000px){.a4d{grid-template-columns:1fr}.a4d-stage{padding:12px}.a4d-paper{margin:0}}
	</style><div class="a4d"><aside class="a4d-panel"><p>使用真实 ERPNext 单据预览；旧版 Jinja 只能原格式预览，导入后只会另存为新格式。</p><div class="a4d-group"><h2>真实单据</h2><label class="a4d-field">单据类型<select data-role="doctype">${types.map(x => `<option>${x}</option>`).join("")}</select></label><label class="a4d-field">单据<select data-role="document"><option value="">先选择单据类型</option></select></label><button class="btn btn-default" data-action="load-preview">加载真实预览</button></div><div class="a4d-group"><h2>版式</h2>${[["fontSize", "字号", 7, 13, 1], ["titleSize", "标题字号", 12, 26, 1], ["headSize", "表头字号", 6, 14, 1], ["lineHeight", "正文行高", 1, 2, .05], ["cellPadding", "单元格内边距", .5, 3, .5], ["pageMargin", "页面内边距", 5, 20, 1], ["logoWidth", "Logo 宽度（mm）", 10, 80, 1], ["logoHeight", "Logo 高度（mm）", 6, 50, 1]].map(([key, label, min, max, step]) => `<label class="a4d-field">${label}<input data-setting="${key}" type="number" min="${min}" max="${max}" step="${step}" value="${config.settings[key]}"></label>`).join("")}<label class="a4d-field">标题颜色<input data-setting="titleColor" type="color" value="#99732c"></label><label class="a4d-field">表头底色<input data-setting="headBg" type="color" value="#f5f1e9"></label></div><div class="a4d-group"><h2>标题列（每列独立开关）</h2><div class="a4d-checks" data-role="checks"></div></div><div class="a4d-group"><h2>扩展功能</h2><div class="a4d-features" data-role="features"></div></div><div class="a4d-group"><h2>列宽（合计 100%）</h2><div class="a4d-widths" data-role="widths"></div><button class="btn btn-default" data-action="equal">均分可见列</button></div><div class="a4d-group"><h2>打开/导入旧格式</h2><label class="a4d-field">格式<select data-role="format"><option value="">选择格式</option></select></label><div class="a4d-actions"><button class="btn btn-default" data-action="legacy-preview">原格式预览</button><button class="btn btn-default" data-action="import-format">导入为可视化格式</button><button class="btn btn-default" data-action="open-format">加载设计设置</button></div></div><div class="a4d-group"><h2>另存为打印格式</h2><label class="a4d-field">新格式名称<input data-role="format-name" maxlength="140" placeholder="例如：销售单 A4 测试"></label><button class="btn btn-primary" data-action="save">保存为新打印格式</button></div><div class="a4d-status" data-role="status" role="status" aria-live="polite">正在读取权限…</div></aside><main class="a4d-stage"><article class="a4d-paper" data-role="paper"><h1>Solua Home · A4</h1><p>选择单据并加载真实预览。</p></article></main></div>`);
	const root = page.main;
	root.find('[data-action="load-preview"]').after('<button class="btn btn-default" data-action="export-pdf">导出当前单据 PDF</button>');
	root.find('[data-action="open-format"]').after('<button class="btn btn-default" data-action="toggle-disabled">停用/启用选中格式</button><button class="btn btn-danger" data-action="delete-format">删除选中格式</button>');
	root.find('[data-action="save"]').after('<button class="btn btn-success" data-action="publish">发布新版本并设为当前格式</button>');
	root.find('[data-setting="headBg"]').closest("label").after('<label class="a4d-field">商品信息边框（当前单据类型）<input data-setting="itemBorders" type="checkbox" checked></label>');
	const call = (method, args = {}) => frappe.call({ method: `solua_home.api.a4_designer.${method}`, args }).then(r => r.message);
	const status = text => root.find('[data-role="status"]').text(text);
	const esc = value => frappe.utils.escape_html(String(value == null ? "" : value));
	const rowValue = (row, key) => ({ name: row.item_name, sku: row.order_code || row.item_code, color_code: row.color_code, additional_notes: row.additional_notes || row.pos_additional_notes }[key] ?? row[key]);
	const partyText = party => [party?.nuit, party?.store, party?.address, party?.contact, party?.phone].filter(Boolean).map(value => esc(String(value).replace(/<br\s*\/?>(\r?\n)?/gi, " "))).join("<br>");
	const allowed = () => [...base, ...columns[config.doctype]];
	const visibleCols = () => {
		const keys = allowed().filter(key => config.visible[config.doctype][key]);
		if (config.doctype === "Delivery Note" && !keys.includes("ordered") && !keys.includes("remaining") && !keys.includes("qty")) keys.push("qty");
		return keys;
	};
	function renderControls() {
		const keys = allowed();
		root.find('[data-role="checks"]').html(keys.map(key => `<label><input type="checkbox" data-column="${key}" ${config.visible[config.doctype][key] ? "checked" : ""}> ${labels[key]}</label>`).join(""));
		root.find('[data-role="features"]').html(Object.keys(featureLabels).map(key => `<label><input type="checkbox" data-feature="${key}" ${config.features[key] ? "checked" : ""}> ${featureLabels[key]}</label>`).join(""));
		const cols = visibleCols(), values = config.widths[config.doctype], sum = cols.reduce((n, key) => n + (values[key] || 1), 0) || 1;
		cols.forEach(key => values[key] = (values[key] || 1) * 100 / sum);
		root.find('[data-role="widths"]').html(cols.map(key => `<label>${labels[key]}</label><input data-width="${key}" type="number" min="2" max="90" step=".1" value="${values[key].toFixed(1)}">`).join(""));
	}
	function render() {
		renderControls();
		const paper = root.find('[data-role="paper"]');
		if (legacyHtml) {
			paper.empty();
			const frame = document.createElement("iframe");
			frame.className = "a4d-legacy-frame";
			frame.title = "旧版 Jinja Print Format 预览";
			frame.setAttribute("sandbox", "");
			paper[0].appendChild(frame);
			frame.srcdoc = `<!doctype html><html><head><meta charset="utf-8"><base href="${window.location.origin}/"></head><body>${legacyHtml}</body></html>`;
			return;
		}
		if (!preview) { paper.html(`<h1>Solua Home · A4</h1><p>请选择真实 ERPNext 单据并加载预览。</p>`); return; }
		const cols = visibleCols(), rows = preview.items || [], widths = config.widths[config.doctype], s = currentSettings();
		paper.css({ padding: `${s.pageMargin}mm`, fontSize: `${s.fontSize}pt` });
		const head = cols.map(key => `<th style="font-size:${s.headSize}pt;font-weight:700">${labels[key]}</th>`).join("");
		const body = rows.map(row => `<tr>${cols.map(key => `<td>${key === "image" ? (row.image ? `<img class="a4d-photo" src="${esc(row.image)}" alt="">` : '<span class="a4d-mock" aria-label="无商品图片"></span>') : esc(rowValue(row, key) || "—")}</td>`).join("")}</tr>`).join("");
		const colgroup = cols.map(key => `<col style="width:${(widths[key] || 1).toFixed(3)}%">`).join("");
		const currency = preview.currency ? ` ${esc(preview.currency)}` : "";
		const cash = preview.cash_discount && preview.cash_discount.enabled ? `<div class="a4d-cash-summary"><div>现金付款折扣 / Desconto pronto pagamento (${esc(preview.cash_discount.rate)}%): -${Number(preview.cash_discount.amount || 0).toLocaleString("en-US")} ${esc(preview.currency || "")}</div><div><b>现金实收 / Valor recebido em numerário: ${Number(preview.cash_discount.cash_paid || 0).toLocaleString("en-US")} ${esc(preview.currency || "")}</b></div></div>` : "";
		const totals = config.doctype === "Sales Invoice" ? `<div class="a4d-totals"><div class="a4d-total">发票总额 / Invoice total: ${esc(preview.total)}${currency}</div>${cash}</div>` : (config.doctype === "Sales Order" ? `<div class="a4d-total">Total / 含税合计: ${esc(preview.total)}${currency}</div>` : "");
		const warning = preview.docstatus === 0 ? '<div style="color:#a35c00;margin:3mm 0">RASCUNHO / 草稿 — Documento não oficial / 非正式凭证</div>' : (preview.docstatus === 2 ? '<div style="color:#a35c00;margin:3mm 0">CANCELADO / 已取消 — Documento não oficial / 非正式凭证</div>' : "");
		const payment = `<div style="page-break-inside:avoid;margin-top:12px;border:1px solid #d5dce0;padding:2mm">Plano de pagamento / 付款安排: ${esc(preview.payment_method || "未维护")} · Depósito / 定金: ${esc(preview.deposit || 0)} · Vencimento do saldo / 尾款到期: ${esc(preview.balance_due_date || "—")}<br>Plano de faturação / 开票安排: ${esc(preview.invoice_plan || "未维护")}</div>`;
		const schedule = config.features.payment_schedule && (preview.payment_schedule || []).length ? `<table><thead><tr><th>Condições de pagamento / 付款条件</th><th>Data de vencimento / 到期日</th><th>Valor / 金额</th></tr></thead><tbody>${preview.payment_schedule.map(row => `<tr><td>${esc(row.payment_term)}</td><td>${esc(row.due_date)}</td><td>${esc(row.payment_amount)}</td></tr>`).join("")}</tbody></table>` : "";
		const qr = config.features.color_qr ? (preview.qr_items || []).map(row => `<div style="display:inline-block;margin-right:6mm"><img class="a4d-photo" src="${esc(row.image)}" alt="QR"><br>${esc(row.template_code)}</div>`).join("") : "";
		const footer = config.features.footer ? `<div style="text-align:center;margin-top:8mm;color:#52606a">${esc(preview.name)} · Página 1 / 1</div>` : "";
		const title = { "Sales Order": "Confirmação de Encomenda / 订单确认单", "Sales Invoice": "Factura / 销售单", "Delivery Note": "Guia de Remessa / 送货单", "Pick List": "Lista de Separação / 拣货单" }[config.doctype];
		const deliveryMeta = `<tr><td>N.º / 编号: ${esc(preview.name)}<br>Encomenda / 订单: ${esc((preview.order || {}).name || "—")}</td><td>Data / 日期: ${esc(preview.date)}<br>Saída / 出发: ${esc((preview.transport || {}).departure_time || "—")}<br>Armazém / 仓库: ${esc((preview.transport || {}).source_address || "—")}</td></tr>`;
		const pickMeta = `<tr><td>N.º / 编号: ${esc(preview.name)}<br>Finalidade / 用途: ${esc(preview.purpose || "—")}</td><td>Origem / 来源: ${esc(preview.source || "—")}<br>Cliente / 客户: ${esc((preview.receiver || {}).name || "—")}</td></tr>`;
		const orderMeta = `<tr><td>N.º / 编号: ${esc(preview.name)}<br>N.º encomenda cliente / 客户订单号: ${esc(preview.customer_order_no || "—")}</td><td>Data / 日期: ${esc(preview.date)}<br>Prazo de entrega / 交期: ${esc(preview.delivery_date || "—")}</td></tr>`;
		const meta = config.doctype === "Delivery Note" ? deliveryMeta : (config.doctype === "Pick List" ? pickMeta : orderMeta);
		const tableTitle = config.doctype === "Delivery Note" ? "本次送货 / Entrega" : (config.doctype === "Pick List" ? "拣货 / Separação" : "订购 / Encomenda");
		const closing = config.doctype === "Delivery Note" ? `<div style="page-break-inside:avoid;margin-top:12px;border:1px solid #d5dce0;padding:2mm">Transporte / 运输: ${esc((preview.transport || {}).driver_name || "—")} · ${esc((preview.transport || {}).driver_phone || "—")}<br>Plano de faturação / 开票安排: ${esc(preview.invoice_plan || "未维护")}</div><div style="page-break-inside:avoid;margin-top:12px;border:1px solid #d5dce0;padding:4mm">Diferenças / 退货备注: ______________________________________<br>Cliente recebeu / 客户签收: ____________________<br>Motorista / 司机签字: ____________________</div>` : (config.doctype === "Pick List" ? `<div style="page-break-inside:avoid;margin-top:12px;border:1px solid #d5dce0;padding:2mm">Armazém / 仓库: ${esc(preview.source || "—")}<br>已拣数量 / Total separado: ${esc(preview.total_picked || 0)}</div>` : `${payment}${schedule}`);
		const logo = (preview.sender || {}).logo ? `<img class="a4d-brand-logo" src="${esc(preview.sender.logo)}" alt="Company Logo">` : "";
		paper.html(`<table class="a4d-brand"><tr><td class="a4d-brand-logo-cell">${logo}</td><td><h2 style="font-size:${s.titleSize}pt;color:${s.titleColor};text-align:left;margin:0;font-weight:700">${esc(title)}</h2></td></tr></table>${warning}<table class="a4d-meta"><tr><td><b>${esc((preview.sender || {}).name || "")}</b><br>${partyText(preview.sender || {})}</td><td><b>Cliente / 客户: ${esc((preview.receiver || {}).name || "")}</b><br>${partyText(preview.receiver || {})}</td></tr>${meta}</table><table class="a4d-items" style="line-height:${s.lineHeight};font-size:${s.fontSize}pt"><colgroup>${colgroup}</colgroup><thead><tr><th colspan="${cols.length}" style="font-size:${s.headSize}pt;font-weight:700">${esc(preview.name)} · ${tableTitle}</th></tr><tr>${head}</tr></thead><tbody>${body}</tbody></table><div style="width:100%;text-align:right;font-weight:700;margin:3mm 0">Total Qty / 总数量: ${esc(preview.total_qty || 0)}</div>${totals}${closing}${qr}${footer}`);
		paper.find("th,td").css("padding", `${s.cellPadding}mm`);
		paper.find("th").css("background", s.headBg);
		paper.find("th,td").css("border", s.itemBorders ? "1px solid #aeb8be" : "0");
		paper.css("position", "relative");
		paper.find(".a4d-brand-logo").css({ display: "block", width: `${s.logoWidth}mm`, height: `${s.logoHeight}mm`, objectFit: "contain", objectPosition: "left center" });
		paper.find(".a4d-brand-logo-cell").css({ width: "42mm", padding: 0, border: 0, verticalAlign: "middle" });
	}
	function loadDocuments() {
		const select = root.find('[data-role="document"]');
		select.html("<option value=\"\">读取单据列表…</option>");
		call("get_documents", { doctype: config.doctype }).then(rows => select.html('<option value="">选择单据</option>' + rows.map(x => `<option value="${esc(x.name)}">${esc(x.name)}</option>`).join(""))).catch(e => { select.html('<option value="">无法读取单据</option>'); status(e.message || "读取单据失败"); });
	}
	function loadFormats() {
		call("list_formats", { doctype: config.doctype }).then(rows => {
			formatMeta = Object.fromEntries(rows.map(row => [row.name, row]));
			const modeLabel = { designer: "A4 可视化", legacy_importable: "旧版 Jinja，可导入", legacy_preview: "仅预览" };
			root.find('[data-role="format"]').html('<option value="">选择格式</option>' + rows.map(row => { const state = row.disabled ? " · 已停用" : (row.active ? " · 当前使用" : ""); return `<option value="${esc(row.name)}">${esc(row.name)} [${modeLabel[row.mode] || "旧版"}]${state}</option>`; }).join(""));
		}).catch(() => {});
	}
	function selectedFormat() { return formatMeta[root.find('[data-role="format"]').val()]; }
	function applyConfig(loaded) {
		const loadedConfig = loaded.config || loaded;
		config.doctype = loadedConfig.doctype;
		config.visible[config.doctype] = loadedConfig.visible;
		config.widths[config.doctype] = loadedConfig.widths;
		const loadedSettings = { ...defaultSettings, ...(loadedConfig.settings || {}) };
		loadedSettings.itemBordersByDoctype = { ...Object.fromEntries(types.map(type => [type, !!loadedSettings.itemBorders])), ...(loadedSettings.itemBordersByDoctype || {}) };
		config.settings = loadedSettings;
		config.features = { ...defaultFeatures, ...(loadedConfig.features || {}) };
		config.control_defaults = { ...defaultControlDefaults, ...(loadedConfig.control_defaults || {}) };
		root.find('[data-role="doctype"]').val(config.doctype);
		currentSettings();
		for (const key of Object.keys(defaultSettings)) {
			const input = root.find(`[data-setting="${key}"]`);
			if (key === "itemBorders") input.prop("checked", !!config.settings[key]);
			else input.val(config.settings[key]);
		}
	}
	root.on("change", "[data-role=doctype]", function () { config.doctype = this.value; currentSettings(); preview = null; legacyHtml = ""; editingMode = "designer"; render(); loadDocuments(); loadFormats(); });
	root.on("change", "[data-role=format]", function () { const meta = selectedFormat(); if (meta) status(meta.mode === "legacy_importable" ? "这是已识别的 Solua Wholesale 旧格式，可原格式预览或导入。" : meta.mode === "legacy_preview" ? "这是旧版 Jinja 格式，可以预览，但尚未转换为可视化格式。" : "这是 A4 可视化格式。"); });
	root.on("change", "[data-column]", function () { config.visible[config.doctype][this.dataset.column] = this.checked; render(); });
	root.on("change", "[data-feature]", function () { config.features[this.dataset.feature] = this.checked; render(); });
	root.on("change", "[data-width]", function () { const key = this.dataset.width, value = Number(this.value), cols = visibleCols(), rest = cols.filter(x => x !== key), room = 100 - Math.max(2, Math.min(90, value)), other = rest.reduce((n, x) => n + config.widths[config.doctype][x], 0) || rest.length; config.widths[config.doctype][key] = 100 - room; rest.forEach(x => config.widths[config.doctype][x] = (config.widths[config.doctype][x] || 1) * room / other); render(); });
	root.on("change", "[data-setting]", function () { const key = this.dataset.setting; if (key === "itemBorders") { config.settings.itemBordersByDoctype[config.doctype] = this.checked; config.settings.itemBorders = this.checked; } else config.settings[key] = key.endsWith("Color") || key === "headBg" ? this.value : Number(this.value); render(); });
	root.on("click", "[data-action]", async function () {
		const action = this.dataset.action;
		try {
			const docName = root.find('[data-role="document"]').val();
			if (action === "export-pdf") {
				if (!preview) throw new Error("请先加载一张真实单据");
				const popup = window.open("", "_blank");
				if (!popup) throw new Error("浏览器阻止了导出窗口，请允许本站打开新窗口");
				const styles = Array.from(document.querySelectorAll("style")).map(node => node.textContent).join("\n");
				popup.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>${esc(preview.name)} PDF</title><style>${styles}\n@page{size:A4;margin:0}html,body{margin:0;padding:0;background:#fff}.a4d-paper{box-shadow:none!important}</style></head><body>${root.find('[data-role="paper"]')[0].outerHTML}</body></html>`);
				popup.document.close();
				popup.focus();
				setTimeout(() => popup.print(), 300);
				status("已打开当前单据打印窗口，请选择“另存为 PDF”。");
			}
			if (action === "load-preview") {
				if (!docName) throw new Error("请选择真实单据");
				preview = await call("get_preview", { doctype: config.doctype, name: docName });
				legacyHtml = ""; editingMode = "designer"; render(); status(`已加载真实单据 ${preview.name}，${preview.items.length} 行。`);
			}
			if (action === "legacy-preview") {
				const meta = selectedFormat();
				if (!meta || meta.mode === "designer") throw new Error("请选择一个旧版 Jinja 格式");
				if (!docName) throw new Error("请选择真实单据");
				const result = await call("get_preview", { doctype: config.doctype, name: docName, print_format: meta.name });
				legacyHtml = result.html || ""; preview = null; editingMode = "legacy_preview"; render(); status("这是旧版 Jinja 格式，可以预览，但尚未转换为可视化格式。");
			}
			if (action === "import-format") {
				const meta = selectedFormat();
				if (!meta || meta.mode !== "legacy_importable") throw new Error("只有已识别的 Solua Wholesale 格式可以导入");
				const loaded = await call("load_config", { name: meta.name });
				applyConfig(loaded); legacyHtml = ""; editingMode = "designer";
				const nameInput = root.find('[data-role="format-name"]'); if (!nameInput.val()) nameInput.val(`${meta.name}-A4可视化版`);
				if (docName) preview = await call("get_preview", { doctype: config.doctype, name: docName });
				render(); status(loaded.warning || `已导入 ${meta.name}，请调整后另存为新格式。`);
			}
			if (action === "open-format") {
				const meta = selectedFormat();
				if (!meta || meta.mode !== "designer") throw new Error("旧版 Jinja 请使用“导入为可视化格式”或“原格式预览”");
				const loaded = await call("load_config", { name: meta.name });
				applyConfig(loaded); preview = null; legacyHtml = ""; editingMode = "designer"; render(); loadDocuments(); loadFormats(); status(`已加载 ${meta.name} 的设计设置；请重新加载真实单据预览。`);
			}
			if (action === "toggle-disabled") {
				const meta = selectedFormat();
				if (!meta) throw new Error("请选择一个打印格式");
				const disabled = meta.disabled ? 0 : 1;
				const result = await call("set_format_status", { name: meta.name, disabled });
				loadFormats(); status(disabled ? `已停用 ${result.name}。` : `已启用 ${result.name}。`);
			}
			if (action === "delete-format") {
				const meta = selectedFormat();
				if (!meta) throw new Error("请选择一个打印格式");
				if (meta.active) throw new Error("当前使用格式不能删除，请先发布其他格式");
				if (!window.confirm(`确定删除打印格式“${meta.name}”？删除前系统会自动保存后台快照。`)) return;
				const result = await call("delete_format", { name: meta.name });
				root.find('[data-role="format"]').val(""); loadFormats(); status(`已删除 ${result.name}；后台快照已保存。`);
			}
			if (action === "equal") { const cols = visibleCols(); cols.forEach(key => config.widths[config.doctype][key] = 100 / cols.length); render(); }
			if (action === "save" || action === "publish") {
				const publishing = action === "publish";
				if (editingMode === "legacy_preview") throw new Error("旧版 Jinja 预览不能直接保存，请先导入为可视化格式");
				if (!canSave) throw new Error("当前账号没有创建打印格式的权限");
				if (publishing && !canPublish) throw new Error("当前账号没有发布打印格式的权限");
				if (!preview) throw new Error("请先加载一张真实单据");
				const name = root.find('[data-role="format-name"]').val().trim(); if (!name) throw new Error("请输入新的格式名称");
				const saved = await call("save_format", { name, config: JSON.stringify({ version: 2, doctype: config.doctype, visible: config.visible[config.doctype], widths: config.widths[config.doctype], settings: config.settings, features: config.features, control_defaults: config.control_defaults }), sample_name: preview.name, publish: publishing ? 1 : 0 });
				status(publishing ? `已发布 ${saved.name}，现在作为 ${config.doctype} 的当前格式。` : `已创建 ${saved.name}。`); loadFormats();
			}
		} catch (e) { status(e.message || "操作失败"); frappe.msgprint({ title: __("A4 打印设计器"), message: e.message || __("操作失败"), indicator: "red" }); }
	});
	call("get_access").then(data => { canSave = !!data.can_save; canPublish = !!data.can_publish; if (!canSave) root.find('[data-action=save]').prop("disabled", true); if (!canPublish) root.find('[data-action=publish]').prop("disabled", true); status(canSave ? "可预览、导入、新建并发布打印格式。" : "可预览与导入；当前账号没有 Print Format 创建权限，保存已禁用。"); }).catch(e => status(e.message || "权限读取失败"));
	loadDocuments(); loadFormats(); render();
};






