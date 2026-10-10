# Change Record：类型 5 公开审核 PPT 模板资产

日期：2026-10-10
分支：`codex/public-ppt-template-assets`
模块：recommendation

## 决策与变更

- 已取得将四套 CLEAN v3 模板及 `local-data/ppt-template-verification/` 验证模板公开分发的明确授权。
- 新增版本化 `assets/ppt-templates/*_CLEAN_v3.pptx`；文件由可复现脚本
  `apps/api-server/scripts/generate_public_ppt_template_assets.py` 生成，仅含虚构槽位、静态形状及节庆虚构背景媒体。
- 未配置 `PPT_TEMPLATE_ASSET_DIR` 时使用上述公共资产；显式配置时仍严格读取指定目录，缺失资产仍返回 `PPT_TEMPLATE_ASSET_UNAVAILABLE`。
- `.gitignore` 允许 `local-data/ppt-template-verification/` 被 Git 跟踪；其他 `local-data` 运行时文件仍被忽略。

## 安全边界

- 未授权的客户 PPTX、客户文字、品牌标识、商品图片、超链接、备注及其他媒体仍不得提交。
- 未更改模板代码或版本、API、权限、数据库或 Alembic。

## 验证

- 公共资产默认解析与真实渲染回归已覆盖；Ruff、Mypy 和 Recommendation pytest 结果随本次分支验证记录更新。
