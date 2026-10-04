# SOLUA Home 独立 App 迁移暂存区

此目录只用于从当前 ERPNext fork 中拆分 SOLUA 自定义代码。

## 重要说明

- 当前目录 **不是生产 App**。
- 当前目录 **不会被 bench 自动安装**。
- 当前目录只存在于 `architecture/solua-home-extraction` 分支。
- 生产环境继续使用现有 `solua-erp` 结构，直到每个模块完成验证。
- 最终目标是把这里的内容迁移到独立仓库 `a83986475/solua-home`。

## 目标结构

```text
solua-home/
├── pyproject.toml
├── README.md
└── solua_home/
    ├── __init__.py
    ├── hooks.py
    ├── modules.txt
    ├── api/
    ├── overrides/
    ├── wholesale/
    ├── whatsapp/
    ├── retail/
    ├── printing/
    ├── integrations/
    ├── public/
    └── patches/
```

## 迁移规则

1. 不一次性移动生产代码。
2. 每次只迁一个功能域。
3. 保留原有 Python import / API 路径，直到对应模块切换完成。
4. 每个模块必须先在开发环境验证，再进入生产。
5. 未完成验证前，不从旧位置删除代码。
6. ERPNext core 修改必须单独列出并逐项消除或保留为明确 patch。
