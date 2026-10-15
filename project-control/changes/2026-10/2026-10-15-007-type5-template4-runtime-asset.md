# Change 2026-10-15-007：类型 5 模板 4 v5 运行资产随仓库分发

日期：2026-10-15

## 背景

模板 4 `UNION_QUOTE_WHITE` v5 的代码、Manifest 和注册信息已经进入仓库，但 CLEAN 运行资产此前被精确 Git 规则忽略，只存在于开发机配置的本地资产目录。其他部署或 CI 环境无法仅通过拉取仓库获得该模板文件。

## 变更

- 删除 `.gitignore` 中对 `/assets/ppt-templates/UNION_QUOTE_WHITE_OFFICIAL_CLEAN_v5.pptx` 的单文件忽略规则。
- 将审核后的 CLEAN 运行资产加入 `assets/ppt-templates`，使部署环境能够按既有资产解析规则直接加载模板 4 v5。
- 客户原始 `模板4.pptx` 和配套 TXT 不进入仓库；本次只提交经过既有构建、清理和结构校验的运行资产。
- 不修改模板 1、模板 2、模板 3、模板 5，也不修改渲染逻辑、推荐规则、价格规则或商品数据。

## 资产证据

- 路径：`assets/ppt-templates/UNION_QUOTE_WHITE_OFFICIAL_CLEAN_v5.pptx`
- 大小：373,111 bytes
- SHA-256：`701F5FA13A7F533B26E56207CD49ED5995A8528CE1C3637D23017BBE757C8BEF`

## 影响

- Alembic Revision：无。
- API / UI / Permission：无变化。
- 部署：模板 4 v5 不再依赖开发机私有资产目录，可随应用代码一并取得。

## 验证

- 项目控制门禁：重新执行 `python scripts/check_project_control.py <base> <head>`。
- 模板内容和渲染实现未在本次提交中改变；沿用模板 4 v5 已完成的专项、联合回归及 WPS 验收结果。
