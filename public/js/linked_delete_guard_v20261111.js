(() => {
	if (frappe.__solua_linked_delete_guard_installed) return;
	frappe.__solua_linked_delete_guard_installed = true;

	const nativeDeleteDoc = frappe.model.delete_doc;
	const nativeCall = frappe.call;

	function linkedDeletePasswordDialog(doctype, names, request) {
		return new Promise((resolve) => {
			const dialog = new frappe.ui.Dialog({
				title: __("管理员验证"),
				fields: [
					{
						fieldname: "password",
						fieldtype: "Password",
						label: __("当前用户密码"),
						reqd: 1,
					},
				],
				primary_action_label: __("验证并删除"),
				primary_action(values) {
					const password = (values.password || "").trim();
					if (!password) return;
					const args = { ...(request.args || {}), password };
					nativeCall({ ...request, args }).then((result) => {
						if (result && result.exc) return;
						dialog.hide();
						resolve(result);
					});
				},
			});
			dialog.show();
			dialog.get_field("password").$input.focus();
		});
	}

	frappe.call = function (method, args, callback) {
		const request = typeof method === "object" ? method : null;
		if (!request || request.method !== "frappe.desk.reportview.delete_items") {
			return nativeCall.apply(this, arguments);
		}

		const names = Array.isArray(request.args?.items)
			? request.args.items
			: JSON.parse(request.args?.items || "[]");
		const doctype = request.args?.doctype;
		return nativeCall({
			method: "solua_home.api.delete_guard.get_bulk_delete_policy",
			args: { doctype, names: JSON.stringify(names) },
		}).then((policy) => {
			if (!policy?.message?.requires_admin_password) return nativeCall(request);
			if (!policy.message.can_delete) {
				frappe.msgprint(__("只有管理员（System Manager）可以删除带账务关联的单据"));
				return { message: names };
			}
			return linkedDeletePasswordDialog(doctype, names, request);
		});
	};

	frappe.model.delete_doc = function (doctype, docname, callback) {
		frappe.call({
			method: "solua_home.api.delete_guard.get_delete_policy",
			args: { doctype, name: docname },
			callback: (r) => {
				if (r.exc || !r.message) return;
				if (!r.message.has_linked_ledger_entries) {
					return nativeDeleteDoc(doctype, docname, callback);
				}
				if (!r.message.can_delete) {
					frappe.msgprint(__("只有管理员（System Manager）可以删除带账务关联的单据"));
					return;
				}

				frappe.confirm(__("该单据已关联总账或库存账，仍要永久删除吗？"), () => {
					const dialog = new frappe.ui.Dialog({
						title: __("管理员验证"),
						fields: [
							{
								fieldname: "password",
								fieldtype: "Password",
								label: __("当前用户密码"),
								reqd: 1,
							},
						],
						primary_action_label: __("验证并删除"),
						primary_action(values) {
							const password = (values.password || "").trim();
							if (!password) return;
							frappe.call({
								method: "frappe.client.delete",
								args: { doctype, name: docname, password },
								freeze: true,
								freeze_message: __("正在删除 {0}...", [docname]),
								callback: (result, rt) => {
									if (result.exc) return;
									dialog.hide();
									frappe.utils.play_sound("delete");
									frappe.model.delete_from_locals(doctype, docname);
									if (callback) callback(result, rt);
								},
							});
						},
					});
					dialog.show();
					dialog.get_field("password").$input.focus();
				});
			},
		});
	};
})();
