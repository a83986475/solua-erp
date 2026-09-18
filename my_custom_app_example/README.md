# solua_home - ERPNext 中文定制示例

## 快速开始

```bash
# 1. 进入 bench 目录
cd ~/frappe-bench

# 2. 创建自定义 app
bench new-app solua_home

# 3. 把本目录中的文件覆盖到 apps/solua_home/
# （或者手动创建对应文件）

# 4. 安装到站点
bench --site dev.localhost install-app solua_home
bench --site dev.localhost migrate

# 5. 重启并清理缓存
bench restart
bench --site dev.localhost clear-cache
```

## 文件说明

| 文件 | 用途 |
|------|------|
| `hooks.py` | 注册所有扩展点（事件、重写、定时任务） |
| `api/sales.py` | 销售模块：发票验证、大额审批、客户管理 |
| `api/buying.py` | 采购模块：采购订单验证、供应商管理 |
| `api/stock.py` | 库存模块：物料验证、库存检查 |
| `api/common.py` | 通用：地址验证、对外 API、工具函数 |
| `override/sales_invoice.py` | 类重写示例（更灵活的扩展方式） |
| `setup.py` | 安装/迁移时自动添加翻译和自定义字段 |
| `tasks.py` | 定时任务：逾期检查、低库存提醒、日志清理 |
| `translations/zh.csv` | 中文翻译文件（备用的批量导入方式） |

## 功能列表

### ✅ 自动翻译
安装后自动向系统添加中文翻译，覆盖销售、采购、库存等模块。

### ✅ 自定义字段
自动给 DocType 添加字段：
- Customer: 信用额度、上次交易日期、状态
- Supplier: 状态、供应商等级
- Sales Invoice: 审批人、审批日期、需要同步

### ✅ 业务验证
- 销售发票大额审批（> 100,000）
- 采购订单金额上限
- 库存出库量检查
- 客户信用额度控制

### ✅ 定时任务
- 每日：检查逾期发票、低库存物料
- 每周：生成销售周报
- 凌晨：清理旧日志

## 开发注意事项

1. **hooks.py 修改后**：`bench restart` 即可生效（不需要 migrate）
2. **setup.py 修改后**：需要 `bench migrate` 才会重新执行
3. **新增 Python 文件**：需要 `bench restart` 或重新启动 bench
4. **自定义字段**：字段名建议加 `custom_` 前缀（Frappe 规范）

## 常用命令

```bash
# 应用变更
bench --site dev.localhost migrate

# 构建前端
bench build

# 重启
bench restart

# 清缓存
bench --site dev.localhost clear-cache

# 查看日志
bench --site dev.localhost console
```
