# solua_home - ERPNext 中文定制

ERPNext v16 中文定制功能扩展包。提供常用模块的中文翻译和自定义字段。

## 功能

- 中文翻译（覆盖销售、采购、库存、财务、制造等模块）
- 自定义字段（客户合同管理、供应商审批等）
- 事件钩子（Sales Invoice 验证等）

## WhatsApp 收件箱（MVP）

- 页面：`/whatsapp`
- 角色：`WhatsApp Support`、`WhatsApp Supervisor`
- Meta 验证：`/api/method/solua_home.api.whatsapp.verify_webhook`
- Meta Webhook：`/api/method/solua_home.api.whatsapp.webhook`
- 站点配置只放在 `site_config.json`，不要提交到 Git：

```json
{
  "whatsapp_cloud_api_token": "",
  "whatsapp_cloud_api_phone_number_id": "",
  "whatsapp_cloud_api_version": "",
  "whatsapp_cloud_api_verify_token": "",
  "whatsapp_cloud_api_app_secret": ""
}
```

第一版只发送 24 小时客服窗口内的文字消息；窗口外的模板消息尚未启用。
