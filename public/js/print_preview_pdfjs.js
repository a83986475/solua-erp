// Render Print Designer formats with the PDF.js bundle already used by the designer.
(() => {
	const patchPrintView = () => {
		const prototype = frappe.ui.form.PrintView?.prototype;
		if (!prototype || typeof prototype.designer_pdf !== "function" || prototype.__solua_pdfjs) {
			return false;
		}

		prototype.__solua_pdfjs = true;
		prototype.designer_pdf = async function (print_format) {
			const token = (this.__solua_preview_token || 0) + 1;
			this.__solua_preview_token = token;
			const container = document.getElementById("preview-container");
			const settings = JSON.parse(print_format.print_designer_settings);
			const page = settings.page;
			container.style.display = "block";
			container.style.minHeight = `${page.height}px`;
			container.style.width = `${page.width}px`;
			container.innerHTML = frappe.render_template("print_skeleton_loading");

			let loadingTask;
			let timeout;
			try {
				await frappe.require("print_designer.bundle.js");
				const pdfjsLib = window.pdfjsLib;
				if (!pdfjsLib) throw new Error("PDF.js did not load");

				const params = new URLSearchParams({
					doctype: this.frm.doc.doctype,
					name: this.frm.doc.name,
					format: this.selected_format(),
					_lang: this.lang_code,
				});
				loadingTask = pdfjsLib.getDocument(
					`${window.location.origin}/api/method/frappe.utils.print_format.download_pdf?${params}`
				);
				const pdfPromise = (async () => {
					const pdf = await loadingTask.promise;
					container.replaceChildren();
					for (let number = 1; number <= pdf.numPages; number++) {
						if (token !== this.__solua_preview_token) return;
						const pdfPage = await pdf.getPage(number);
						const viewport = pdfPage.getViewport({ scale: 1 });
						const scale = (page.width / viewport.width) * window.devicePixelRatio;
						const scaled = pdfPage.getViewport({ scale });
						const canvas = document.createElement("canvas");
						canvas.width = scaled.width;
						canvas.height = scaled.height;
						canvas.style.cssText = `display:block;width:${page.width}px;height:${page.height}px;margin:20px auto 0`;
						container.appendChild(canvas);
						await pdfPage.render({
							canvasContext: canvas.getContext("2d"),
							viewport: scaled,
							intent: "print",
						}).promise;
					}
				})();
				await Promise.race([
					pdfPromise,
					new Promise((_, reject) => {
						timeout = setTimeout(() => reject(new Error("PDF preview timed out")), 30000);
					}),
				]);
			} catch (error) {
				if (token !== this.__solua_preview_token) return;
				console.warn("Print Designer PDF preview failed; falling back to HTML.", error);
				loadingTask?.destroy();
				this.print_wrapper.find(".print-designer-wrapper").hide();
				this.inner_msg.show();
				this.full_page_btn.show();
				this.pdf_btn.show();
				this.letterhead_selector.show();
				this.sidebar_dynamic_section.show();
				this.print_btn.show();
				this.sidebar.show();
				this.toolbar_print_format_selector.$wrapper.hide();
				this.toolbar_language_selector.$wrapper.hide();
				Object.getPrototypeOf(Object.getPrototypeOf(this)).preview.call(this);
				frappe.show_alert({
					message: __("PDF preview failed; showing HTML preview instead."),
					indicator: "orange",
				});
			} finally {
				clearTimeout(timeout);
			}
		};
		return true;
	};

	const install = () => {
		let attempts = 0;
		const timer = setInterval(() => {
			if (patchPrintView() || ++attempts >= 120) clearInterval(timer);
		}, 50);
	};

	install();
	frappe.router?.on("change", install);
})();
