# MySQL 多用户任务队列基础

日期：2026-10-14
状态：IMPLEMENTED

## 变更

- 新增 `scm_async_task` 与 Revision `20261014_0057`，保存任务类型、项目/Run、受控 payload、进度、尝试、租约、心跳、错误和审计时间。
- Revision `20261014_0058` 将默认最大尝试次数调整为 3，允许显式重试失败任务；`20261014_0059` 新增按项目、文件和分析键缓存结果的 `scm_mapping_analysis_cache`。
- 新增 MySQL Worker：短事务 `SKIP LOCKED` 领取、15 秒心跳、900 秒租约、失败终态和过期任务扫描；HEAVY 与 MAPPING 队列由独立进程运行。
- 类型 1--5 的匹配、推品和 PPT 生成创建统一任务并立即返回 `202`，不再在 HTTP 请求或 `BackgroundTasks` 中等待重任务。
- 类型 3 模板预览 / Sheet 输出列、类型 1/2 客户原表回填列、推荐模板结构由 MAPPING Worker 解析；缓存未命中返回 `202`，页面轮询后读取已提交缓存；保存映射不重读 Excel。
- 五类工作台与详情共用任务状态、心跳、失败重试和待领取取消面板；列表批量获取活跃/最新任务。后台方案补生成也改为 202 派发。
- Worker 在领域 Runner 返回后核验 MatchTask / Run / PPT Generation 终态；异常或租约过期会同时收敛统一任务和相应领域任务。

## 配置与启动

`.env.example` 增加 `TASK_MODE=database`、Worker 并发、心跳、租约和映射并发配置；`start-backend.ps1 -MultiUser` 启动两个 Uvicorn API Worker，`start-task-worker.ps1` 与 `start-mapping-worker.ps1` 分别启动两个队列 Worker。

## 验证

- `alembic upgrade head`：本机开发库升级至单 Head `20261014_0059`。
- 复审新增 23 项真实 MySQL / 子进程测试，覆盖五类型并发 409、SKIP LOCKED、取消、六类租约回收、重试上限、旧轮次和迟到失败回调隔离、类型 3 可确认、类型 4 跨 Session 落库、同结构 8 并发缓存复用及跨模块权限拒绝。
- 后端全量 `pytest -q`：434 passed；Ruff 全目录与 Mypy 通过。前端 Vitest：186 passed；typecheck/build 通过。
- 前端 `npm run typecheck`、`npm run build` 通过；仅保留既有 bundle 大小警告。
- 用户随后反馈类型 1～4 已完成本机导入到导出完整流程；只读数据库核验对应匹配/推品及 MAPPING 任务成功、结构缓存已提交。示例项目 BID00000362 / BID00000364 / BID00000365 / BID00000366；这不替代类型 5、多用户负载或导出内容逐项验收。

## 运行边界

已实际启动两个 Uvicorn Worker 并发访问健康接口，并通过两个独立队列子进程执行指定测试任务；测试进程均已退出。真实提供方和多浏览器持续负载验收仍待部署环境执行。上传初始识别仍沿用既有同步入口，不能将本报告视为所有上传/导出均已后台化。

后续用户本机已启动 API 与两个常驻队列 Worker 并验证类型 1～4 单用户流程。正常领取/成功没有逐任务日志，不能以终端无新增输出判定未消费；应核验任务终态、缓存和心跳。运行中 5% 为固定阶段标记，不代表已处理数据比例。
