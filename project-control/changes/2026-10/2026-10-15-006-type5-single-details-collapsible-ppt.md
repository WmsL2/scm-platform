# Change 2026-10-15-006：类型 5 单品详情、折叠候选区与确认后 PPT 生成

日期：2026-10-15

## 范围

- 仅调整类型 5 单品推品工作台和其既有 PPT 生成状态门槛。
- 不修改商品主数据、候选冻结数据、DeepSeek、PPT 模板资产、API 路径、权限或数据库 Schema；仅调整既有模板卡的展示名称与顺序。

## 变更

- 单品候选表每行新增“查看详情”。弹窗复用组合推品详情展示，仅读取当前 Run 的 `product_snapshot`、`price_snapshot` 和图片引用，显示 SKU、品牌、型号、三级类目、商品名称、规格、卖点、成本价、毛利率、协议价、京东价、折扣率和好评率；不查询或写入 `scm_product`。
- 单品候选表移入默认展开的“匹配商品”折叠区。收起时仍显示候选总数和已确认数量，避免长商品表挤占 PPT 配置和生成记录区域。
- `SELECTING` 项目中，只要当前 Run 为 `CONFIRMED` 且至少存在一件已确认候选，即可创建 PPT 生成任务；不再要求先执行“完成选品”。任务创建与成功生成均不把项目从 `SELECTING` 提前转为结束状态，因此用户仍可确认或撤销其他商品。`READY` / `EXPORTED` 历史路径保持兼容。
- 模板卡以既有内部模板编码继续渲染和生成，但展示名称统一为“模板1”至“模板5”，固定顺序为：`JD_DETAIL_RED`、`JD_FESTIVE_RED`、`CATALOG_MINIMAL`、`UNION_QUOTE_WHITE`、`SYSTEM_DEFAULT`。其中本地 v5 预览替换版本沿用相同名称；预览图、版本、资产解析和历史任务读取不变。

## 验证

- 后端：`apps/api-server/.venv/Scripts/python.exe -m pytest tests/recommendation/test_recommendation_core_service.py -q` → `5 passed`，覆盖 `SELECTING + CONFIRMED + 已确认候选` 可创建 PPT 任务且项目状态保持 `SELECTING`。
- 后端：`apps/api-server/.venv/Scripts/python.exe -m ruff check app/modules/recommendation/application/ppt_service.py tests/recommendation/test_recommendation_core_service.py` → 通过。
- 前端：`npm run test -- --run src/views/bid/PptSolutionWorkspaceView.spec.ts` → `2 passed`。
- 前端：`npm run test` → `43 files / 186 tests passed`。
- 前端：`npm run typecheck` → 通过。
- 前端：`npm run build` → 通过；保留既有的大包体积告警。
- 后端：模板目录回归覆盖卡片顺序及“模板1”至“模板5”名称。

Alembic Revision：无。

API / UI / Permission：API 路径与权限不变；单品候选 UI 增加详情入口与折叠区，PPT 生成可在已确认商品的待选品状态使用，模板卡以模板1--5顺序展示。

## 待验收

- 浏览器使用真实单品 Run 点击“查看详情”、展开/收起候选区、确认至少一件商品后不点“完成选品”直接生成 PPT，并确认生成后仍可继续选品。
