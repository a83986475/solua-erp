"""Self-service account actions for Solua stock-viewing employees."""

import hmac
import secrets

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, get_datetime, now_datetime, validate_email_address
from frappe.utils.synchronization import filelock


STOCK_VIEWER_ROLE = "Solua Stock Viewer"
SIGNUP_CODE_CONFIG = {
    "code": "solua_employee_signup_code",
    "expires_at": "solua_employee_signup_code_expires_at",
    "single_use": "solua_employee_signup_code_single_use",
    "used_at": "solua_employee_signup_code_used_at",
    "generated_at": "solua_employee_signup_code_generated_at",
    "generated_by": "solua_employee_signup_code_generated_by",
    "revoked_at": "solua_employee_signup_code_revoked_at",
}


def _require_employee():
    if frappe.session.user == "Guest" or STOCK_VIEWER_ROLE not in frappe.get_roles():
        frappe.throw(_("没有员工账号管理权限"), frappe.PermissionError)


def _require_signup_admin():
    if frappe.session.user != "Administrator" and "System Manager" not in frappe.get_roles():
        frappe.throw(_("只有 Administrator 或 System Manager 可以管理员工注册授权码"), frappe.PermissionError)


def _read_signup_code_config():
    config = frappe.get_site_config()
    return {name: str(config.get(key) or "") for name, key in SIGNUP_CODE_CONFIG.items()}


def _signup_code_expired(expires_at):
    if not expires_at:
        return False
    try:
        return get_datetime(expires_at) <= now_datetime()
    except Exception:
        return True


def _signup_code_state(config):
    code = config["code"]
    expired = _signup_code_expired(config["expires_at"])
    single_use = bool(cint(config["single_use"]))
    used = bool(config["used_at"])
    revoked = bool(config["revoked_at"])
    if not code:
        status = "disabled"
    elif revoked:
        status = "revoked"
    elif expired:
        status = "expired"
    elif single_use and used:
        status = "used"
    else:
        status = "active"
    return {
        "code": code,
        "expires_at": config["expires_at"],
        "single_use": single_use,
        "used_at": config["used_at"],
        "generated_at": config["generated_at"],
        "generated_by": config["generated_by"],
        "revoked_at": config["revoked_at"],
        "status": status,
        "enabled": status == "active",
    }


def _new_signup_code():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(16))


@frappe.whitelist(methods=["GET"])
def get_employee_signup_code_settings():
    _require_signup_admin()
    with filelock("solua_employee_signup_code", timeout=10):
        return _signup_code_state(_read_signup_code_config())


@frappe.whitelist(methods=["POST"])
def generate_employee_signup_code(expires_at=None, single_use=1):
    _require_signup_admin()
    expiry = str(expires_at or "").strip()
    if expiry:
        try:
            expiry = get_datetime(expiry)
        except Exception:
            frappe.throw(_("有效期格式不正确"))
        if expiry <= now_datetime():
            frappe.throw(_("有效期必须晚于当前时间"))
        expiry = expiry.isoformat(sep=" ")
    code = _new_signup_code()
    from frappe.installer import update_site_config

    with filelock("solua_employee_signup_code", timeout=10):
        update_site_config(SIGNUP_CODE_CONFIG["code"], code)
        update_site_config(SIGNUP_CODE_CONFIG["expires_at"], expiry)
        update_site_config(SIGNUP_CODE_CONFIG["single_use"], "1" if cint(single_use) else "0")
        update_site_config(SIGNUP_CODE_CONFIG["used_at"], "")
        update_site_config(SIGNUP_CODE_CONFIG["generated_at"], now_datetime().isoformat(sep=" "))
        update_site_config(SIGNUP_CODE_CONFIG["generated_by"], frappe.session.user)
        update_site_config(SIGNUP_CODE_CONFIG["revoked_at"], "")
        return _signup_code_state(_read_signup_code_config())


@frappe.whitelist(methods=["POST"])
def revoke_employee_signup_code():
    _require_signup_admin()
    from frappe.installer import update_site_config

    with filelock("solua_employee_signup_code", timeout=10):
        if not _read_signup_code_config()["code"]:
            frappe.throw(_("当前没有可撤销的授权码"))
        update_site_config(SIGNUP_CODE_CONFIG["revoked_at"], now_datetime().isoformat(sep=" "))
        return _signup_code_state(_read_signup_code_config())


@frappe.whitelist(methods=["POST"])
def change_employee_password(current_password, new_password, confirm_password):
    _require_employee()
    current_password = str(current_password or "")
    new_password = str(new_password or "")
    confirm_password = str(confirm_password or "")
    if not current_password:
        frappe.throw(_("请输入当前密码"))
    if not new_password or new_password != confirm_password:
        frappe.throw(_("两次输入的新密码不一致"))
    from frappe.core.doctype.user.user import update_password

    update_password(new_password=new_password, old_password=current_password, logout_all_sessions=1)
    return {"ok": 1}


@frappe.whitelist(methods=["POST"])
def bind_employee_email(email, current_password):
    _require_employee()
    email = str(email or "").strip().lower()
    current_password = str(current_password or "")
    if not email:
        frappe.throw(_("请输入邮箱"))
    validate_email_address(email, throw=True)
    if not current_password:
        frappe.throw(_("请输入当前密码"))
    frappe.local.login_manager.check_password(frappe.session.user, current_password)
    if frappe.get_all("User", filters={"email": email, "name": ["!=", frappe.session.user]}, pluck="name", limit_page_length=1):
        frappe.throw(_("该邮箱已绑定其他账号"))
    user = frappe.get_doc("User", frappe.session.user)
    user.email = email
    user.save(ignore_permissions=True)
    frappe.db.commit()
    return {"ok": 1, "email": email}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=50, seconds=60 * 60)
def register_employee(full_name, email, password, confirm_password, authorization_code):
    if frappe.session.user != "Guest":
        frappe.throw(_("请退出当前账号后再注册"))
    full_name = str(full_name or "").strip()
    email = str(email or "").strip().lower()
    password = str(password or "")
    confirm_password = str(confirm_password or "")
    supplied_code = str(authorization_code or "").strip().upper()
    from frappe.installer import update_site_config

    with filelock("solua_employee_signup_code", timeout=10):
        config = _read_signup_code_config()
        state = _signup_code_state(config)
        if not state["enabled"] or not hmac.compare_digest(supplied_code, state["code"].upper()):
            frappe.throw(_("授权码无效、已过期、已使用或已被撤销"), frappe.PermissionError)
        if not full_name:
            frappe.throw(_("请输入姓名"))
        validate_email_address(email, throw=True)
        if password != confirm_password or not password:
            frappe.throw(_("两次输入的密码不一致"))
        if frappe.db.exists("User", email) or frappe.get_all("User", filters={"email": email}, pluck="name", limit_page_length=1):
            frappe.throw(_("该邮箱已经注册"))
        user = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": full_name,
            "full_name": full_name,
            "user_type": "Website User",
            "enabled": 1,
            "send_welcome_email": 0,
            "new_password": password,
        })
        user.flags.ignore_permissions = True
        user.flags.ignore_password_policy = True
        user.insert()
        user.add_roles(STOCK_VIEWER_ROLE)
        if state["single_use"]:
            update_site_config(SIGNUP_CODE_CONFIG["used_at"], now_datetime().isoformat(sep=" "))
        frappe.db.commit()
        return {"ok": 1}
