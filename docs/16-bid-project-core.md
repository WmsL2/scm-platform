# 投标项目核心

## 业务边界

一个买家 Excel 对应一个投标项目，Excel 的每一行对应一条项目需求。项目以正式商品和供应商主数据为后续匹配来源，不创建独立供应商报价历史。

## 文件规则

- ORIGINAL 是用户上传的源文件，永久保存且不可覆盖。
- 报价文件从 ORIGINAL 副本生成，按 V1、V2 等版本保存。
- 标记已投标时必须指定当前项目的一份报价导出文件。

## 模板规则

模板保存工作表、表头行、数据起始行、字段映射、报价列映射和指纹。没有识别到模板时，系统保存源文件并将导入状态标记为待映射，不猜测字段。

## 状态规则

`IMPORTED → MATCHING → SELECTING → READY → EXPORTED → SUBMITTED → WON / LOST`

重新选品后，已导出项目回到 `READY`，旧报价文件保留，新结果必须重新导出。中标和未中标是终态。

## 接口

- `POST /api/v1/bid-projects`：新建项目并上传 Excel。
- `GET /api/v1/bid-projects`：项目分页列表。
- `GET /api/v1/bid-projects/{id}`：项目详情和事件历史。
- `GET /api/v1/bid-projects/{id}/items`：需求行服务端分页。
- `GET /api/v1/bid-projects/{id}/files`：文件版本列表。
- `GET /api/v1/bid-projects/{id}/files/{file_id}/download`：下载文件。
- `POST /api/v1/bid-projects/{id}/exports`：生成新的报价版本。
- `POST /api/v1/bid-projects/{id}/commands/submit`：标记已投标。
- `POST /api/v1/bid-projects/{id}/commands/win`：标记中标。
- `POST /api/v1/bid-projects/{id}/commands/lose`：标记未中标。
