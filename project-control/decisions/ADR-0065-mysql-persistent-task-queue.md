# ADR-0065：投标项目使用 MySQL 持久化任务队列

状态：ACCEPTED
日期：2026-10-14

## 决策

类型 1--5 的匹配、AI 推品与 PPT 生成统一创建 `scm_async_task`，由独立本机 Worker 从 MySQL 领取；不再由 HTTP 请求、`BackgroundTasks` 或进程内锁运行重任务。

- HEAVY 队列处理类型 1--5；映射结构分析使用独立 MAPPING Worker 和 `scm_mapping_analysis_cache`。类型 3 的模板/Sheet 结构、类型 1/2 的回填列结构只在该 Worker 中读取工作簿。
- 领取使用短事务 `SELECT ... FOR UPDATE SKIP LOCKED`；任务保存租约、心跳、尝试次数、脱敏错误和终态。
- 创建 HEAVY 任务时锁定项目并检查该项目已有的 `PENDING/RUNNING` HEAVY 任务，因此多个 Uvicorn Worker 下第二次创建返回 `409`。
- 既有 `scm_match_task`、Recommendation Run 和 `scm_ppt_generation_task` 继续保存领域历史；`scm_async_task` 只负责跨进程投递与运维状态。
- 失败/取消/租约过期与关联业务状态回收在同一短事务完成；失败重试重新检查项目活跃 HEAVY，并使用新 Run / PPT 记录隔离历史结果（历史补方案使用原冻结 Run）。尝试次数隔离旧领取者的心跳及完成写入。
- 推荐模板结构也使用 MAPPING cache；读取成功结果不持有写锁，缓存未命中先锁项目再做当前读复查，保证多个请求复用一个解析任务。初始上传识别的现有同步入口仍需单独治理，不将其计作已完成的后台路径。

## 后果

API 创建任务返回 `202 Accepted` 和任务 DTO；前端通过 Run / 任务查询读取状态，不等待 AI、Excel 或 PPT 处理完成。

多人启动使用 `scripts/start-backend.ps1 -MultiUser` 的两个 API Worker，加上 `scripts/start-task-worker.ps1` 与 `scripts/start-mapping-worker.ps1` 两个队列 Worker。不引入 Redis、ARQ、Celery、Docker 或独立 AI 服务。
