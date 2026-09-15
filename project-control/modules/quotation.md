# 客户报价

状态：IN_PROGRESS
Owner：投标项目 1 号任务
Last Updated：2026-09-15

## Database
- [x] 报价导出文件版本与实际投标文件引用已具备基础表结构。

## Backend
- [x] ORIGINAL 副本生成报价文件、版本递增和文件下载已实现。

## Frontend
- [ ] 投标文件版本页面由 3 号任务实现。

## Permissions
- [x] `bid:export`、`bid:file:download`、`bid:submit` 已创建。

## Tests
- [ ] 等待真实模板与 2 号选品结果后补充端到端导出测试。

## Known Issues
报价列必须由真实模板配置；当前不猜测客户 Excel 的报价列。

## Next Step
收到样表后配置模板，完成选品后联调报价导出。
