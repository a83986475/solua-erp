// Keep explicit Sales Order item edits when delayed item-detail calls sync a stale row.
(() => {
	if (frappe.call.__solua_sales_order_item_guard) return;

	const nativeCall = frappe.call;
	const nativeSync = frappe.model?.sync;
	const nativeSetValue = frappe.model?.set_value;
	const states = new Set();
	const itemDetailMethods = new Set([
		"process_item_selection",
		"erpnext.stock.get_item_details.get_item_details",
	]);

	function isMobile() {
		try {
			const mobileFlag = frappe.utils?.is_mobile;
			return Boolean(
				frappe.is_mobile ||
				frappe.flags?.is_mobile ||
				(typeof mobileFlag === "function" ? mobileFlag.call(frappe.utils) : mobileFlag)
			);
		} catch (error) {
			return false;
		}
	}

	function getWrapper(frm) {
		const field = frm.fields_dict?.items;
		return field?.wrapper || field?.$wrapper?.[0] || null;
	}

	function isDesktopDraft(frm) {
		return Boolean(
			frm?.doctype === "Sales Order" &&
			frm.doc?.docstatus === 0 &&
			!isMobile() &&
			frm.fields_dict?.items?.grid &&
			getWrapper(frm)
		);
	}

	function methodName(options) {
		return typeof options === "string" ? options : options?.method;
	}

	function isItemDetailRequest(options) {
		const method = methodName(options);
		return (
			itemDetailMethods.has(method) ||
			method === "solua_home.api.sales.get_sales_order_item_display" ||
			method === "erpnext.stock.utils.get_incoming_rate" ||
			(typeof method === "string" && (
				method.startsWith("erpnext.stock.get_item_details.") ||
				method.startsWith("erpnext.accounts.doctype.pricing_rule.pricing_rule.")
			))
		);
	}

	function currentForm(options) {
		const frm = typeof cur_frm !== "undefined" ? cur_frm : window.cur_frm;
		if (!isDesktopDraft(frm)) return null;
		const requestDoc = typeof options === "object" ? options?.doc : null;
		if (
			requestDoc &&
			requestDoc !== frm.doc &&
			requestDoc.name &&
			frm.doc.name &&
			requestDoc.name !== frm.doc.name
		) {
			return null;
		}
		return frm;
	}

	function findRow(frm, rowName) {
		return (frm.doc.items || []).find((row) => String(row.name) === String(rowName));
	}

	function stateFor(frm) {
		if (!isDesktopDraft(frm)) return null;
		if (frm.__solua_sales_order_item_guard) return frm.__solua_sales_order_item_guard;

		const state = {
			frm,
			pending: 0,
			requests: new Set(),
			edited: new Map(),
			userAction: null,
			statusNode: null,
			waiters: [],
		};
		frm.__solua_sales_order_item_guard = state;
		states.add(state);
		attachEditorListener(state);
		wrapSave(state);
		return state;
	}

	function markEdited(state, rowName, fieldname, value) {
		if (!rowName || !fieldname) return;
		if (fieldname === "item_code") state.edited.delete(String(rowName));
		let fields = state.edited.get(String(rowName));
		if (!fields) {
			fields = new Map();
			state.edited.set(String(rowName), fields);
		}
		fields.set(fieldname, value);
	}

	function rowNameFromTarget(target) {
		const row = target?.closest?.(".grid-row");
		return row?.getAttribute?.("data-name") || row?.dataset?.name;
	}

	function fieldNameFromTarget(target) {
		const field = target?.closest?.("[data-fieldname]");
		return (
			target?.getAttribute?.("data-fieldname") ||
			target?.dataset?.fieldname ||
			field?.getAttribute?.("data-fieldname") ||
			field?.dataset?.fieldname
		);
	}

	function noteUserEdit(state, event) {
		const fieldname = fieldNameFromTarget(event.target);
		if (!fieldname || (fieldname === "item_code" && event.type === "input")) return;
		const rowName = rowNameFromTarget(event.target);
		const row = findRow(state.frm, rowName);
		if (!rowName || !row) return;

		if (fieldname === "item_code") state.edited.delete(String(rowName));
		state.userAction = { rowName: String(rowName) };
		if (Object.prototype.hasOwnProperty.call(row, fieldname)) {
			markEdited(state, rowName, fieldname, row[fieldname]);
		} else {
			markEdited(state, rowName, fieldname, event.target.value);
		}
		Promise.resolve().then(() => {
			const latest = findRow(state.frm, rowName);
			if (latest && Object.prototype.hasOwnProperty.call(latest, fieldname)) {
				markEdited(state, rowName, fieldname, latest[fieldname]);
			}
		});
		setTimeout(() => {
			if (state.userAction?.rowName === String(rowName)) state.userAction = null;
		}, 0);
	}

	function attachEditorListener(state) {
		const wrapper = getWrapper(state.frm);
		if (!wrapper?.addEventListener) return;
		wrapper.addEventListener("input", (event) => noteUserEdit(state, event), true);
		wrapper.addEventListener("change", (event) => noteUserEdit(state, event), true);
	}

	function setPendingUi(state, pending) {
		const wrapper = getWrapper(state.frm);
		if (!wrapper) return;
		if (pending) {
			wrapper.setAttribute("aria-busy", "true");
			if (!state.statusNode) {
				state.statusNode = document.createElement("div");
				state.statusNode.className = "solua-item-request-status text-muted small";
				state.statusNode.setAttribute("role", "status");
				state.statusNode.textContent = __("商品信息加载中，请稍候…");
				wrapper.parentNode?.insertBefore(state.statusNode, wrapper);
			}
			state.frm.disable_save?.();
			return;
		}
		wrapper.removeAttribute("aria-busy");
		state.statusNode?.remove?.();
		state.statusNode = null;
		state.frm.enable_save?.();
	}

	function finishPending(state, token) {
		if (!state.requests.delete(token)) return;
		state.pending = state.requests.size;
		if (state.pending) return;
		setPendingUi(state, false);
		const waiters = state.waiters.splice(0);
		waiters.forEach((resolve) => resolve());
	}

	function waitForIdle(state) {
		if (!state.pending) return Promise.resolve();
		return new Promise((resolve) => state.waiters.push(resolve));
	}

	function wrapSave(state) {
		if (typeof state.frm.save !== "function" || state.frm.__solua_save_guarded) return;
		const nativeSave = state.frm.save.bind(state.frm);
		state.frm.save = (...args) => {
			if (!state.pending) return nativeSave(...args);
			frappe.msgprint?.(__("商品信息仍在加载，请稍候再保存。"));
			return waitForIdle(state).then(() => nativeSave(...args));
		};
		state.frm.__solua_save_guarded = true;
	}

	function restoreEditedValues(state) {
		let changed = false;
		for (const [rowName, fields] of state.edited) {
			const row = findRow(state.frm, rowName);
			if (!row) continue;
			for (const [fieldname, value] of fields) {
				if (row[fieldname] !== value) {
					row[fieldname] = value;
					changed = true;
				}
			}
		}
		if (changed) state.frm.refresh_field?.("items");
	}

	function wrapModelSync() {
		if (!nativeSync || frappe.model.__solua_sales_order_item_sync_guard) return;
		frappe.model.sync = function (...args) {
			const result = nativeSync.apply(this, args);
			states.forEach(restoreEditedValues);
			return result;
		};
		frappe.model.__solua_sales_order_item_sync_guard = true;
	}

	function wrapModelSetValue() {
		if (!nativeSetValue || frappe.model.__solua_sales_order_item_set_value_guard) return;
		frappe.model.set_value = function (cdt, cdn, fieldname, value) {
			const statesForRow = [...states].filter((state) => findRow(state.frm, cdn));
			const userState = statesForRow.find((candidate) => candidate.userAction?.rowName === String(cdn));
			const rowState = statesForRow.find((candidate) => candidate.edited.has(String(cdn)));
			const protectedFields = rowState?.edited.get(String(cdn));
			if (protectedFields && !userState && typeof fieldname === "string" && protectedFields.has(fieldname)) {
				return Promise.resolve(findRow(rowState.frm, cdn)?.[fieldname]);
			}

			let fields = typeof fieldname === "object" ? Object.keys(fieldname) : [fieldname];
			if (protectedFields && !userState && typeof fieldname === "object") {
				fields = fields.filter((key) => !protectedFields.has(key));
				if (!fields.length) return Promise.resolve();
				const filtered = Object.fromEntries(fields.map((key) => [key, fieldname[key]]));
				return nativeSetValue.call(this, cdt, cdn, filtered, value);
			}

			const result = nativeSetValue.call(this, cdt, cdn, fieldname, value);
			if (userState) {
				const row = findRow(userState.frm, cdn);
				fields.forEach((key) => markEdited(userState, cdn, key, row?.[key]));
			}
			return result;
		};
		frappe.model.__solua_sales_order_item_set_value_guard = true;
	}

	function installForm(frm) {
		if (!isDesktopDraft(frm)) return;
		stateFor(frm);
	}

	wrapModelSync();
	wrapModelSetValue();
	frappe.ui.form.on("Sales Order", {
		setup: installForm,
		refresh: installForm,
	});

	frappe.call = function (...args) {
		const options = args[0];
		const frm = isItemDetailRequest(options) ? currentForm(options) : null;
		if (!frm) return nativeCall.apply(this, args);

		const state = stateFor(frm);
		const token = {};
		state.requests.add(token);
		state.pending = state.requests.size;
		if (state.pending === 1) setPendingUi(state, true);
		try {
			return Promise.resolve(nativeCall.apply(this, args)).finally(() => finishPending(state, token));
		} catch (error) {
			finishPending(state, token);
			throw error;
		}
	};
	frappe.call.__solua_sales_order_item_guard = true;
	if (typeof window !== "undefined") {
		window.solua_home_sales_order_async_item_guard = { installForm, stateFor };
	}
})();
