// Keep Query Report columns added from the UI across refreshes and page reloads.
(function () {
    "use strict";

    const storage_prefix = "solua_query_report_custom_columns_v1:";

    function storage_key(report_name) {
        return storage_prefix + (report_name || "");
    }

    function read_columns(report_name) {
        if (!report_name) return [];
        try {
            return JSON.parse(window.localStorage.getItem(storage_key(report_name)) || "[]");
        } catch (error) {
            return [];
        }
    }

    function write_columns(report_name, columns) {
        if (!report_name) return;
        try {
            window.localStorage.setItem(storage_key(report_name), JSON.stringify(columns));
        } catch (error) {
            // Storage can be unavailable in private browsing; the current page still works.
        }
    }

    function serialize_column(column) {
        if (!column) return null;
        const source_field = column.__solua_source_field || column.source_field;
        const link_fieldname = column.__solua_link_fieldname || column.link_fieldname || column.link_field?.fieldname;
        if (!column || !column.doctype || !source_field || !link_fieldname) return null;
        return {
            fieldname: column.fieldname,
            fieldtype: column.fieldtype,
            label: column.label,
            insert_after_index: Number(column.insert_after_index),
            doctype: column.doctype,
            options: column.options,
            width: column.width,
            source_field,
            link_fieldname,
        };
    }

    function merge_columns(...groups) {
        const columns = [];
        const seen = new Set();
        groups.flat().forEach((column) => {
            const serialized = serialize_column(column) || column;
            if (!serialized?.fieldname || seen.has(serialized.fieldname)) return;
            seen.add(serialized.fieldname);
            columns.push(serialized);
        });
        return columns;
    }

    function install() {
        const QueryReport = frappe.views?.QueryReport;
        const prototype = QueryReport?.prototype;
        if (!prototype || prototype.__solua_custom_columns_patch) return !!prototype;

        const original_prepare_report_data = prototype.prepare_report_data;
        const original_add_custom_column = prototype.add_custom_column;

        prototype.add_custom_column = function (custom_column, custom_data, new_column_data, insert_after_index) {
            custom_column.forEach((column) => {
                column.__solua_source_field = new_column_data.field;
                column.__solua_link_fieldname = new_column_data.fieldname;
                column.insert_after_index = insert_after_index;
            });
            const result = original_add_custom_column.call(
                this, custom_column, custom_data, new_column_data, insert_after_index
            );
            write_columns(this.report_name, merge_columns(this.custom_columns));
            return result;
        };

        prototype.prepare_report_data = function (data) {
            const previous_columns = (this.custom_columns || []).map(serialize_column).filter(Boolean);
            const stored_columns = read_columns(this.report_name);
            const result = original_prepare_report_data.call(this, data);
            const columns = merge_columns(stored_columns, previous_columns);
            this.custom_columns = columns;
            if (!columns.length) return result;

            const restore_id = (this.__solua_custom_columns_restore_id || 0) + 1;
            this.__solua_custom_columns_restore_id = restore_id;
            const restore_next = (index) => {
                if (restore_id !== this.__solua_custom_columns_restore_id || index >= columns.length) return;
                const definition = columns[index];
                const names = [...new Set(this.data.map((row) => row[definition.link_fieldname]).filter(Boolean))];
                const add_column = (response) => {
                    if (restore_id !== this.__solua_custom_columns_restore_id) return;
                    const column = {
                        ...definition,
                        insert_after_index: definition.insert_after_index,
                        link_field: {fieldname: definition.link_fieldname, names: new Set(names)},
                    };
                    this.add_custom_column(
                        [column],
                        response?.message || {},
                        {field: definition.source_field, doctype: definition.doctype, fieldname: definition.link_fieldname},
                        definition.insert_after_index,
                    );
                    restore_next(index + 1);
                };
                if (!names.length) {
                    add_column({message: {}});
                    return;
                }
                frappe.call({
                    method: "frappe.desk.query_report.get_data_for_custom_field",
                    args: {field: definition.source_field, doctype: definition.doctype, names},
                    callback: add_column,
                    error: () => restore_next(index + 1),
                });
            };
            restore_next(0);
            return result;
        };

        prototype.__solua_custom_columns_patch = true;
        return true;
    }

    if (!install()) {
        let attempts = 0;
        const retry = () => {
            if (install() || attempts++ >= 20) return;
            setTimeout(retry, 100);
        };
        retry();
    }
})();
