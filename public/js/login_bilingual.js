/* Solua Home login page: browser-language labels with an explicit toggle. */
(() => {
	const copy = {
		zh: {
			toggle: "Português",
			account: "员工账号 / 自助注册",
			loginTitle: "登录",
			loginSubtitle: "欢迎！请登录继续。",
			identifier: "邮箱、手机号或用户名",
			password: "密码",
			forgot: "忘记密码？",
			login: "继续",
			emailLink: "通过邮箱链接登录",
			emailTitle: "登录",
			emailSubtitle: "输入邮箱，我们会发送登录链接。",
			email: "邮箱",
			sendLink: "发送登录链接",
			passwordLogin: "使用密码登录",
			forgotTitle: "忘了密码？",
			forgotSubtitle: "请输入邮箱，我们会发送密码重置链接。",
			forgotSend: "发送链接",
			backToLogin: "返回登录",
			signupTitle: "注册",
			signupSubtitle: "设置您的账号。",
			signupDisabled: "注册已禁用",
			signupMessage: "此网站已禁用注册功能",
			home: "主页",
		},
		pt: {
			toggle: "中文",
			account: "Conta de colaborador / Registo",
			loginTitle: "Iniciar sessão",
			loginSubtitle: "Bem-vindo! Inicie sessão para continuar.",
			identifier: "E-mail, telefone ou nome de utilizador",
			password: "Palavra-passe",
			forgot: "Esqueceu-se da palavra-passe?",
			login: "Entrar",
			emailLink: "Entrar com link enviado por e-mail",
			emailTitle: "Iniciar sessão",
			emailSubtitle: "Introduza o seu e-mail para receber um link de acesso.",
			email: "E-mail",
			sendLink: "Enviar link de acesso",
			passwordLogin: "Entrar com palavra-passe",
			forgotTitle: "Esqueceu-se da palavra-passe?",
			forgotSubtitle: "Introduza o seu e-mail para receber o link de reposição.",
			forgotSend: "Enviar link",
			backToLogin: "Voltar ao início de sessão",
			signupTitle: "Criar conta",
			signupSubtitle: "Vamos configurar a sua conta.",
			signupDisabled: "Registo desativado",
			signupMessage: "O registo está desativado neste site.",
			home: "Página inicial",
		},
	};

	const readSavedLanguage = () => {
		try {
			const saved = window.localStorage.getItem("solua-login-language");
			if (copy[saved]) return saved;
		} catch (_) {}
		const languages = navigator.languages?.length ? navigator.languages : [navigator.language || ""];
		return languages.some((language) => /^zh(?:-|$)/i.test(language)) ? "zh" : "pt";
	};

	let language = readSavedLanguage();
	const setText = (selector, key) => document.querySelectorAll(selector).forEach((element) => { element.textContent = copy[language][key]; });

	const applyLanguage = () => {
		const t = copy[language];
		document.documentElement.lang = language === "zh" ? "zh-CN" : "pt-PT";
		setText("section.for-login .page-card-head-text h4", "loginTitle");
		setText("section.for-login .page-card-subtitle", "loginSubtitle");
		setText("section.for-login label[for='login_email']", "identifier");
		setText("section.for-login label[for='login_password']", "password");
		setText("section.for-login .forgot-password-message a", "forgot");
		setText("section.for-login .btn-login", "login");
		setText("section.for-login .btn-login-with-email-link", "emailLink");

		setText("section.for-login-with-email-link .page-card-head-text h4", "emailTitle");
		setText("section.for-login-with-email-link .page-card-subtitle", "emailSubtitle");
		setText("section.for-login-with-email-link label[for='login_with_email_link_email']", "email");
		setText("section.for-login-with-email-link .form-login-with-email-link .btn-login-with-email-link", "sendLink");
		setText("section.for-login-with-email-link .btn-login-option", "passwordLogin");

		setText("section.for-forgot .page-card-head-text h4", "forgotTitle");
		setText("section.for-forgot .page-card-subtitle", "forgotSubtitle");
		setText("section.for-forgot label[for='forgot_email']", "email");
		setText("section.for-forgot .btn-forgot", "forgotSend");
		setText("section.for-forgot .sign-up-message a", "backToLogin");

		setText("section.for-signup .page-card-head-text h4", "signupTitle");
		setText("section.for-signup .page-card-subtitle", "signupSubtitle");
		setText("section.for-signup .signup-disabled-message .indicator", "signupDisabled");
		setText("section.for-signup .sign-up-message", "signupMessage");
		setText("section.for-signup .signup-disabled-message a", "home");
		document.querySelectorAll(".solua-login-language").forEach((button) => {
			button.textContent = t.toggle;
			button.setAttribute("aria-label", t.toggle);
		});
		const accountLink = document.querySelector(".solua-login-account-link");
		if (accountLink) accountLink.textContent = t.account;
	};

	const addAccountLink = () => {
		const actions = document.querySelector("section.for-login .page-card-actions");
		if (!actions || actions.querySelector(".solua-login-account-link")) return;
		const link = document.createElement("a");
		link.className = "solua-login-account-link";
		link.href = "/account";
		actions.appendChild(link);
	};

	const addLanguageToggle = (section) => {
		const card = section.querySelector(".login-content.page-card");
		if (!card || card.querySelector(".solua-login-language")) return;
		const button = document.createElement("button");
		button.className = "solua-login-language";
		button.type = "button";
		button.addEventListener("click", () => {
			language = language === "zh" ? "pt" : "zh";
			try { window.localStorage.setItem("solua-login-language", language); } catch (_) {}
			applyLanguage();
		});
		card.appendChild(button);
	};

	const init = () => {
		if (!document.querySelector("section.for-login")) return;
		document.querySelectorAll("section.for-login, section.for-signup, section.for-forgot, section.for-login-with-email-link").forEach(addLanguageToggle);
		addAccountLink();
		applyLanguage();
		window.addEventListener("hashchange", applyLanguage);
	};

	if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, {once: true});
	else init();
})();
