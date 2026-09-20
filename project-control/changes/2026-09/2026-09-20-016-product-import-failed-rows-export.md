# Change Record: Product Import Failed Rows Export

Change ID: 2026-09-20-016
Module: catalog / product-import
Date: 2026-09-20
Branch: feat/product-import-failed-rows-export

## Problem

商品大表预览会明确列出不通过行，但运营只能回到原始大表逐行定位和修改。真实大表可能包含四千余行及数百 MB 图片，少量错误行的修正成本过高。

## Delivered

- 新增 `GET /api/v1/products/imports/{task_id}/failed-rows`，仅任务上传者且具有 `product:import` 权限可下载。
- 导出文件直接复用商品主数据下载接口所用的正式 `.xlsx` 模板，保留表头、字体、颜色、列宽、行高和第 2 行单元格格式，只填入全部未处理失败行的原始值；公式按导出后的紧凑行号平移。
- 第二工作表记录导出行、原 Excel 行和错误原因，不影响首个工作表重新上传。
- 含 WPS `DISPIMG` 时，从临时源工作簿仅复制失败行引用的图片元数据和媒体，避免把整本大表无关图片复制到修正文件。
- 商品导入预览底部在存在失败行时显示带数量的导出按钮。

## Boundaries

- 不修改 Staging 或正式 Product，不自动修复数据，不导出已导入行。
- 复用 `product:import` 权限，不新增权限或数据库 Schema。
- 若临时源文件已不可用，43 列原值与错误说明仍可导出；内嵌图片只能在源文件保留期内随文件复制。

## Verification

- Backend Ruff、mypy 通过。
- `tests/catalog/test_product_import_api.py` 覆盖正式模板样式、内嵌图片失败行导出并重新预览。
- Frontend Catalog API Vitest：8 passed；TypeScript typecheck 和生产构建通过。
