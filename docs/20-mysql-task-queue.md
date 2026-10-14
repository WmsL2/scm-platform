# 投标项目 MySQL 任务队列与运维

Revision：`20261014_0057` → `20261014_0058` → `20261014_0059`；ADR-0065。

## 启动

在仓库根目录分别运行（开发库 `.env` 保持原值，不覆盖密钥）：

```powershell
.\scripts\start-backend.ps1 -MultiUser
.\scripts\start-task-worker.ps1
.\scripts\start-mapping-worker.ps1
```

两个 Uvicorn 应用 Worker、一个 HEAVY Worker、一个 MAPPING Worker 是四个业务执行角色；Uvicorn 还包含父进程，Windows/Python 也可能显示启动包装进程，因此操作系统进程总数不一定等于四。开发 API 可不带 `-MultiUser` 使用 reload；业务异步队列仍需两个 Worker。API 成功启动不等于队列已经有人消费。

默认 HEAVY、MAPPING 各并发 1；心跳 15 秒、租约 900 秒。MySQL 8、`pool_pre_ping` 和既有连接池复用；不新增 Redis、ARQ、Celery 或 AI 服务。检查 `/health/live`、`/health/ready`，以及运行中任务的 `heartbeat_at`。

当前 Worker 仅打印启动与异常/租约回收等日志，正常领取和成功没有逐任务日志；终端停留在启动行不表示没有消费。运行中进度目前固定标记为 5%，成功为 100%，不代表实际已处理行数或剩余耗时。以任务状态、最近心跳、已提交缓存和业务结果核验执行情况。

单任务诊断可运行：

```powershell
cd apps/api-server
.\.venv\Scripts\python.exe -m app.jobs.task_worker --queue mapping --once --task-id <任务UUID>
```

该命令只领取指定 ID 和队列中的 PENDING 任务；`--task-id` 必须与 `--once` 一起使用。Worker 数据库轮询发生短时异常时会退避重试；正在执行的失败任务由租约恢复收敛，不静默重复 AI 调用。

## 数据字典

`scm_async_task`（所有 UUID 为 CHAR(36)，审计时间为 UTC DATETIME）：

| 字段 | 类型 / 语义 |
| --- | --- |
| id | UUID 主键 |
| project_id | 项目 UUID，FK `scm_bid_project.id` RESTRICT |
| run_id | 可空领域 UUID；类型 1/2 精确指向 MatchTask，类型 3 指向 Type3Run，类型 4/5 指向 RecommendationRun |
| task_kind | VARCHAR(48)，六类 HEAVY 和 `MAPPING_STRUCTURE_ANALYSIS` |
| status | VARCHAR(16)：PENDING / RUNNING / SUCCEEDED / FAILED / CANCELLED |
| payload_json | JSON，只允许文件/分析定位、PPT 领域任务 ID、受控重试参数等白名单标量 |
| progress_percent / progress_message | INT / VARCHAR(500)，执行阶段进度，非精确耗时百分比 |
| attempt_count / max_attempts | INT，领取次数 / 最大尝试次数，默认 0 / 3 |
| error_code / error_message | VARCHAR(64) / TEXT，安全错误摘要 |
| lease_expires_at / heartbeat_at | 可空 DATETIME，领取者租约及最近心跳 |
| started_at / completed_at | 可空 DATETIME，执行开始与终态时间 |
| created_by | 创建人 UUID |
| created_at / updated_at | DATETIME，创建 / 最后更新时间 |

索引：`(project_id,status)`、`(status,created_at)`、`lease_expires_at`、`run_id`、`(task_kind,status)`。状态和类型有 CHECK 合同。

`scm_mapping_analysis_cache`：

| 字段 | 类型 / 语义 |
| --- | --- |
| id | UUID 主键 |
| project_id | 项目 UUID，FK RESTRICT |
| file_id | 文件 UUID，隔离上传版本 |
| async_task_id | 解析任务 UUID，FK `scm_async_task.id` RESTRICT，有索引 |
| analysis_key | VARCHAR(255)，分析类型、Sheet 和表头行组合 |
| status | PENDING / RUNNING / SUCCEEDED / FAILED |
| result_json / error_message | 可空 JSON / TEXT，已提交结构结果与错误 |
| created_at / updated_at | DATETIME |

唯一索引 `(project_id,file_id,analysis_key)`。缓存查询命中不加写锁；未命中时短事务锁定项目、重新读取当前记录并创建唯一解析任务，避免 REPEATABLE READ 旧快照和并发插入问题。文件 SHA-256 由 Worker 验证。工作簿解析在映射进程的受限执行槽位完成，解析期间不持有数据库 Session 或事务，心跳可继续运行。

## API / UI

- 类型 1/2 匹配、类型 3/4/5 推品、PPT 生成和历史方案补生成都返回 `202` 和统一任务 DTO；同项目活跃 HEAVY 任务冲突为 `409`。
- `GET /api/v1/bid-projects/{project_id}/async-tasks`：分页任务历史，活跃任务优先；`GET /api/v1/bid-projects/async-tasks/{id}`：详情。
- `POST .../async-tasks/{id}/commands/cancel`：仅取消 PENDING；`POST .../commands/retry`：仅失败任务且尝试次数未耗尽。权限按任务种类复用 `bid:match`、`recommendation:run`、`recommendation:export`；映射任务复用 `bid:update` / `recommendation:create`。
- 项目列表批量读取最新/活跃任务，不逐行查询；详情和五类工作台展示任务、心跳、错误、取消与重试。映射页面显示读取缓存、后台解析、成功、失败；等待两分钟后给出可刷新提示。
- 类型 1/2 回填列、类型 3 模板/Sheet 结构、类型 4 推荐模板结构：未解析返回 `202`，缓存命中返回 `200`。保存映射只使用结构缓存验证，不重新读取 Excel。上传文件的初始识别流程仍沿用既有入口，不能把这份验证报告理解为所有上传/导出入口均已后台化。
- 合入主分支输入映射确认后，类型 1/2 回填结构缓存键包含 Sheet 与表头行，任务冻结对应参数；修改输入映射后不会复用旧列结构。匹配任务待领取或执行中时，禁止重新确认输入映射。新增输入映射的结构读取与确认解析仍保留主分支同步实现，不属于 MAPPING Worker 覆盖范围。

## 失败与重试

取消、执行失败和过期恢复在同一事务更新队列及关联业务状态，写入项目事件。类型 3 有候选后同时写 `WAITING_CONFIRMATION` 和项目 `SELECTING`。类型 1/2 回收其精确 MatchTask；PPT 回收精确生成任务。重试会先锁项目并检查其他活跃 HEAVY 任务；新的推荐 Run / PPT 任务隔离旧结果。历史补方案重试使用原冻结候选池，只补缺失方案。队列心跳/完成/失败校验尝试次数，旧执行轮次不能覆盖新轮次状态。

无需手工 UPDATE 项目状态。回归测试通过应用服务触发取消/失败/过期恢复，再使用新数据库会话核验状态；仅测试夹具模拟过期时间，正式产品流程由 Worker 完成回收。

## 验证边界

测试使用真实 MySQL、HTTP、Excel、独立 Worker 子进程与两个 Uvicorn Worker；模型回答使用受控替身。真实 DeepSeek 的限流/可用性、多浏览器操作和 6–8 用户持续大文件负载仍需部署环境验收。

2026-10-14 用户反馈类型 1～4 本机导入到导出完整流程通过；只读数据库核验示例项目 BID00000362 / BID00000364 / BID00000365 / BID00000366 的匹配/推品和结构解析任务成功，缓存结果已提交。这是单用户实际流程补验，不代表类型 5、提供方异常、多用户负载或导出内容逐项校验均已通过。

本机复验环境为 Python 3.13.14 / MySQL 8.4.11；仓库 CI 的 Python 3.12 / MySQL 8.0 本轮未在远端执行。`alembic heads/current` 均为单 Head `20261014_0059`；既有 `env.py` 未提供 autogenerate MetaData，因此 `alembic check` 不可用。本轮另外反射数据库，确认 `scm_async_task` 的 19 列/5 个索引和 `scm_mapping_analysis_cache` 的 10 列/2 个索引均与 ORM 一致。
