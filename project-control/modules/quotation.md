# 客户报价

状态：IN_PROGRESS
Owner：投标项目 1 号任务
Last Updated：2026-09-16

## Database
- [x] 报价导出文件版本与实际投标文件引用已具备基础表结构。
- [x] 投标项目已增加可空业务开始时间 `start_at`；`created_at` 继续只用于审计（Revision `20260916_0025`）。

## Backend
- [x] ORIGINAL 副本生成报价文件、版本递增和文件下载已实现。
- [x] 未提交项目可通过 `bid:void` 作废；原始 Excel、报价 Excel 和全部审计事件均保留，已提交后的业务结果不可用作废覆盖。

## Frontend
- [x] 文件版本、下载、导出、标记投标及结果操作界面已实现；状态：IMPLEMENTED / TEMPLATE_DATA_GATE_BLOCKED。
- [x] 投标项目 Excel 上传建项、报价文件导出及已有文件下载显示本次浏览器请求耗时；上传建项的导入遮罩同步显示已耗时。

## Permissions
- [x] `bid:export`、`bid:file:download`、`bid:submit` 已创建。

## Tests
- [ ] 等待真实模板与 2 号选品结果后补充端到端导出测试。

## Known Issues
报价列必须由真实模板配置；当前不猜测客户 Excel 的报价列。

## Next Step
收到样表后配置模板，完成选品后联调报价导出。
