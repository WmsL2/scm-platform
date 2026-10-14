# 类型 1/2 需求字段映射人工确认

日期：2026-10-14  
模块：bid / matching / web-admin  
状态：IMPLEMENTED / REAL_BROWSER_ACCEPTANCE_PENDING

## 背景

类型 1、2 原流程在项目创建时直接使用 AI 建议解析客户 Excel。客户表结构持续变化时，错误的 Sheet、表头或输入字段建议会直接影响需求行及后续匹配，用户没有在匹配前复核输入语义的机会。结果回填映射已经独立存在，但不能替代需求输入映射确认。

## 变更

- 类型 1、2 创建时仍调用各自独立 Agent 生成项目级建议，但只保存原文件和映射快照，`import_status` 保持 `MAPPING_REQUIRED`，不生成需求行。
- 新增 `GET /api/v1/bid-projects/{id}/input-mapping`，返回当前项目工作表、表头、类型专属字段及 AI 建议；可按 Sheet 和表头行重新读取真实列。
- 新增 `PUT /api/v1/bid-projects/{id}/input-mapping`，人工确认 Sheet、表头行、数据起始行与字段映射后，服务端校验真实列和类型主匹配条件，再从当前项目原文件解析需求行。
- 类型 1 要求至少具备类目、商品名称、规格参数或技术要求之一；类型 2 要求客户编码、品牌+型号，或可提取身份信息的商品名称/规格之一。两个类型继续使用各自合同和后续匹配流程。
- AI 建议失败时建立当前文件的空白人工映射入口；不使用其他项目或固定客户模板兜底。
- 历史项目若仍引用共享模板，确认前先复制为当前项目专属快照，避免重新解析时修改其他项目的输入映射。
- 工作台采用纵向“客户 Excel 列 → 类型专属需求字段”布局；输入映射与结果回填映射分为两个独立页签，确认输入并解析成功后自动进入结果回填页签，避免两张大表上下堆叠。
- 人工映射只确认结构化主参考字段。未映射的其他非空原表列继续保存在需求行 `source_data`，并通过 Agent `source_row` 作为次要上下文参与复核；它们不会取代主匹配条件、扩大确定性召回或绕过价格等代码硬规则。
- 开始匹配先检查输入映射与需求解析状态，再检查回填映射；未确认时返回明确提示。

## 数据与权限

- 无 Alembic Revision；复用项目 `import_status`、项目专属 `BidTemplate.import_mapping` 与事件审计。
- 读取复用 `bid:detail`，确认复用 `bid:update`；无新增权限。

## 验证

- `python -m ruff check app/modules/bid app/modules/matching tests/bid tests/matching`：通过。
- `python -m mypy app/modules/bid app/modules/matching`：通过。
- `python -m pytest tests/bid tests/matching -q`：69 passed。
- `python -m pytest -q`：413 passed。
- `npm run typecheck`：通过。
- `npm test -- --run`：43 files / 184 tests passed。
- `npm run build`：通过（仅保留既有大 Chunk 警告）。

## 待验收

- 使用真实 DeepSeek 和类型 1、2 客户文件完成浏览器上传、输入映射调整、确认解析、回填映射确认、主动匹配、结果查看、导出与下载全流程。
