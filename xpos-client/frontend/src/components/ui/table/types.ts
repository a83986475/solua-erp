export interface TableRow {
	[key: string]: any;
}

export type ColumnType = "text" | "number" | "date" | "select" | "readonly" | "component" | "link";

export interface SelectOption {
	label: string;
	value: string;
}

export interface LinkColumnConfig {
	doctype: string;
	labelField?: string;
	filters?: Record<string, unknown> | ((row: TableRow, index: number) => Record<string, unknown>);
	onSelect?: (
		selectedValue: string,
		option: { value: string; description?: string },
		row: TableRow,
		index: number,
	) => Partial<TableRow> | void;
}

export interface TableColumn {
	fieldname: string;
	label: string;
	type: ColumnType;
	width?: string;
	align?: "left" | "center" | "right";
	min?: number;
	max?: number;
	precision?: number;
	options?: SelectOption[] | ((row: TableRow, index: number) => SelectOption[]);
	format?: (value: any, row: TableRow, index: number) => string;
	cellClass?: string | ((value: any, row: TableRow, index: number) => string);
	editable?: boolean;
	visible?: boolean;
	required?: boolean;
	frozen?: "left" | "right";
	frozenWidth?: number;
	placeholder?: string;
	alwaysVisible?: boolean;
	link?: LinkColumnConfig;
	showInEditor?: boolean;
}

export interface TableProps {
	rows: TableRow[];
	columns: TableColumn[];
	label?: string;
	minWidth?: string;
	showRowNumbers?: boolean;
	showCheckboxes?: boolean;
	showDeleteButton?: boolean;
	showAddRow?: boolean;
	keyboardNavigation?: boolean;
	allowReorder?: boolean;
	allowDuplicate?: boolean;
	emptyMessage?: string;
	emptyDescription?: string;
	showColumnSettings?: boolean;
	highlightNewRows?: boolean;
	heightClass?: string;
	showEditRow?: boolean;
	tabToAddRow?: boolean;
}
