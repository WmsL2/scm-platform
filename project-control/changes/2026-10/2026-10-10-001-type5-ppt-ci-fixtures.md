# Change Record：类型 5 PPT 私有资产 CI 测试夹具

日期：2026-10-10  
分支：`codex/feat/type5-ppt-clean-v3`  
模块：recommendation

## 变更

- 业务 PPT 渲染测试在 pytest `tmp_path` 中生成四套完全虚构的最小 PPTX 夹具；夹具提供语义文本槽、商品图片槽、必要封面和静态形状。
- 节庆夹具保留一张虚构静态背景图，用于验证克隆后静态媒体保留以及动态商品图片替换。
- 测试直接 patch `ppt_renderer.resolve_ppt_template_asset`，覆盖渲染器已直接导入的实际调用点，不再依赖 Git 忽略的 `.codex-assets/`。
- 保留并扩展真实渲染断言：价格槽去重、缺图提示、图片替换、PPTX 可重新打开、商品内容不串页、静态背景保留；另覆盖真实资产缺失与版本不匹配的显式拒绝。

## 范围与影响

- 未提交客户或 CLEAN 私有 PPTX，未将私有素材写入 CI artifact 或日志。
- 未修改生产资产缺失机制、四套模板注册版本、API、权限、前端、数据库或 Alembic。

## Alembic

- 无。

## 验证

- `python -m pytest tests/recommendation/test_ppt_renderer.py -q`：10 passed。
- `python -m pytest tests/recommendation -q`：90 passed（本机 MySQL 已升级至 `20261009_0052`）。
- `python -m ruff check .`：通过；`python -m mypy app`：通过；`git diff --check`：通过。
- `python -m pytest -x -q`：本次渲染测试之后在既有 Catalog 用例
  `test_product_selection_ids_reuses_active_supplier_visibility` 停止（`/selection-ids` 返回 422），与 PPT
  资产无关；完整运行随后在该失败后停滞，已终止，未将其列为本次修复通过结果。
