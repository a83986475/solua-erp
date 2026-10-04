# SOLUA 自定义代码迁移清单

> 分支：`architecture/solua-home-extraction`  
> 状态：迁移准备  
> 原则：先盘点、后迁移；不直接影响生产。

## A. 当前已确认的自定义区域

| 当前路径 | 目标位置 | 风险 | 优先级 | 状态 |
|---|---|---:|---:|---|
| `public/` | `solua_home/public/` | 低 | P1 | 待迁移 |
| `printing/` | `solua_home/printing/` | 低~中 | P1 | 待迁移 |
| `print_format/` | fixtures / `solua_home/printing/` | 中 | P1 | 待分类 |
| `api/` | `solua_home/api/` | 中 | P2 | 待迁移 |
| `whatsapp_inbox/` | `solua_home/whatsapp/` 或保留模块名 | 中 | P2 | 待迁移 |
| `solua_wholesale/` | `solua_home/wholesale/` | 中 | P2 | 待迁移 |
| `retail_settings/` | `solua_home/retail/` | 中 | P2 | 待迁移 |
| `product_bundle_definition/` | `solua_home/retail/` 或独立模块 | 中 | P2 | 待迁移 |
| `override/` | `solua_home/overrides/` | 中~高 | P3 | 待迁移 |
| `boot.py` | `solua_home/boot.py` | 中 | P3 | 待迁移 |
| `item_metrics.py` | `solua_home/services/item_metrics.py` | 中 | P3 | 待迁移 |
| `tasks.py` | `solua_home/tasks.py` | 中 | P3 | 待迁移 |
| `install.py` | `solua_home/install.py` / patches | 高 | P4 | 待拆分 |
| `hooks.py` | `solua_home/hooks.py` | 高 | P4 | 最后切换 |

## B. 已确认的高风险依赖

当前 hooks 中大量路径已经使用 `solua_home.*`：

- `solua_home.api.*`
- `solua_home.printing.*`
- `solua_home.override.*`
- `solua_home.item_metrics.*`
- `solua_home.tasks.*`
- `solua_home.install.*`

这说明逻辑命名已经基本正确，但当前仓库依赖“仓库根目录本身就是 solua_home package”的特殊布局。

迁移到标准 Frappe App 后，目标是：

```text
repo root
└── solua_home/
    ├── api/
    ├── printing/
    ├── overrides/
    └── ...
```

因此迁移时最重要的是 **保持 import path 不变**，而不是重命名 Python namespace。

## C. 第一批迁移建议

第一批只处理低风险、不涉及数据库 schema 的内容：

1. `public/css`
2. `public/js`
3. `public/images`
4. `printing/label_helpers.py`
5. `printing/color_card.py`

暂不迁：

- `hooks.py`
- `install.py`
- `override/`
- `api/sales.py`
- `api/stock.py`
- 自定义 DocType

## D. 每批迁移验收

每批迁移必须完成：

- Python import 成功
- bench build 成功
- bench migrate 成功
- 页面资源加载正常
- 对应业务功能回归通过
- 旧实现与新实现不能同时注册
- 生产切换前有回滚点

## E. 生产切换原则

迁移期间生产继续使用当前 `solua-erp`。

只有当独立 App 在开发环境验证通过后，才进入：

1. 安装 `solua_home`
2. 启用对应新模块
3. 验证
4. 删除 fork 中旧实现
5. 再进入下一模块

禁止一次性全部切换。
