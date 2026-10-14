# 投标项目核心

## 业务边界

一个买家 Excel 对应一个投标项目，Excel 的每一行对应一条项目需求。项目以正式商品和供应商主数据为后续匹配来源，不创建独立供应商报价历史。

## 文件规则

- ORIGINAL 是用户上传的源文件，永久保存且不可覆盖。
- 报价文件从 ORIGINAL 副本生成，按 V1、V2 等版本保存。
- 标记已投标时必须指定当前项目的一份报价导出文件。

## 模板规则

模板保存工作表、表头行、数据起始行、字段映射、报价列映射和指纹。没有识别到模板时，系统保存源文件并将导入状态标记为待映射，不猜测字段。

类型 1/2 新项目每次都由对应类型 Agent 从本次上传工作簿识别输入列与结果列。创建阶段只保存当前项目的原文件和建议，不立即生成需求行；工作台先由人工确认 Sheet、表头行、数据起始行及“客户 Excel 列 → 类型专属需求字段”，确认后服务端才重新读取 ORIGINAL 并解析需求。AI 失败时仍为当前项目建立空白人工映射入口，不复用其他项目模板。

输入映射只标记结构化主参考字段，不是允许参与匹配的列白名单。未映射的其他非空原表列仍完整保存在需求行 `source_data`，并作为类型专属 Agent 的次要上下文用于发现补充要求和明确冲突；主匹配入口、确定性召回及价格等硬规则仍只由对应类型的正式规则控制。

结果列另存为项目级 `output_mapping` 并单独确认。回填映射只控制 ORIGINAL 副本的结果写入位置，不参与需求解析或商品匹配，也不回写其他项目模板。历史项目没有项目级快照时，其冻结映射也必须重新解析为当前 ORIGINAL 中真实存在的表头，不存在的旧列名直接丢弃。

## 状态规则

`IMPORTED → MATCHING → SELECTING → READY → EXPORTED → SUBMITTED → WON / LOST`

在 `IMPORTED`、`MATCHING`、`SELECTING`、`READY` 或 `EXPORTED` 阶段可以业务作废为 `VOIDED`。`VOIDED` 是终态；不物理删除项目、需求行、选品快照、文件或事件，以保留投标审计历史。已提交、已中标和未中标项目不可作废。

## 项目时间

`start_at` 是用户填写的项目业务开始时间，`deadline_at` 是用户填写的投标截止时间；两者均不等同于数据库自动生成、只读的审计时间 `created_at`。开始时间不得晚于截止时间。

重新选品后，已导出项目回到 `READY`，旧报价文件保留，新结果必须重新导出。中标和未中标是终态。

## 接口

- `POST /api/v1/bid-projects`：新建项目并上传 Excel。
- `PATCH /api/v1/bid-projects/{id}`：在允许状态下更新名称、需求商、业务时间和备注（`bid:update`）。
- `POST /api/v1/bid-projects/{id}/commands/void`：记录必填作废原因并转为 `VOIDED`（`bid:void`）。
- `GET /api/v1/bid-projects`：项目分页列表。
- `GET /api/v1/bid-projects/{id}`：项目详情和事件历史。
- `GET /api/v1/bid-projects/{id}/items`：需求行服务端分页。
- `GET /api/v1/bid-projects/{id}/input-mapping`：读取类型 1/2 当前项目的 Sheet、真实表头、类型专属需求字段及 AI 建议；可通过查询参数切换 Sheet 和表头行。
- `PUT /api/v1/bid-projects/{id}/input-mapping`：人工确认输入映射并从当前项目 ORIGINAL 解析需求行；解析完成前禁止开始匹配。
- `GET /api/v1/bid-projects/{id}/output-mapping`：读取类型 1/2 当前客户原表的回填字段预识别结果。
- `PUT /api/v1/bid-projects/{id}/output-mapping`：人工确认项目级回填字段；只允许选择当前原表中真实存在的列。
- `GET /api/v1/bid-projects/{id}/files`：文件版本列表。
- `GET /api/v1/bid-projects/{id}/files/{file_id}/download`：下载文件。
- `POST /api/v1/bid-projects/{id}/exports`：生成新的报价版本。
- `POST /api/v1/bid-projects/{id}/commands/submit`：标记已投标。
- `POST /api/v1/bid-projects/{id}/commands/win`：标记中标。
- `POST /api/v1/bid-projects/{id}/commands/lose`：标记未中标。

报价导出的附件记录、项目状态和审计事件必须在 POST 响应发送前完成事务提交。前端收到文件 ID 后可以立即调用下载接口，不应因另一数据库会话尚不可见而偶发返回“投标文件不存在”。

## 商品匹配与人工选品

- `POST /api/v1/bid-projects/{id}/commands/start-matching`：针对已解析项目创建一次匹配任务，在本机 `inline` TaskQueue 中完成候选生成；写入任务、Top 20 候选和行级匹配状态。
- `GET /api/v1/bid-projects/{id}/items/{item_id}/candidates`：读取该项目最新一次完成匹配任务的候选及评分依据。
- `POST /api/v1/bid-projects/{id}/items/{item_id}/selections`：只能提交已持久化候选 ID 和 Decimal 单价。服务会重新校验商品、供应商、需求限价，并追加不可变快照。
- `POST /api/v1/bid-projects/{id}/items/{item_id}/no-quote`：将该行标记为无法报价，保存原因；`OTHER` 必须填写说明。

## Web 工作台

Web Admin 已提供项目列表、创建、详情、事件与文件版本，以及按需求行服务端分页的匹配工作台。类型 1/2 创建后先纵向复核输入映射，解析成功后再独立复核结果回填映射，最后由用户主动开始匹配。候选仅在用户打开对应行时加载；已选品行展示持久化的不可变快照。页面不会猜测或伪造不存在的字段。

匹配接口分别需要 `bid:match`、`bid:detail`、`bid:select` 权限。候选只来自 `ACTIVE` Product 和 `ARCHIVED + NORMAL + not deleted` 的来源供应商；价格不参与商品身份评分。
