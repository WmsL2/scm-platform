# 修复任务列表查询的 SQLAlchemy 跨版本类型兼容

日期：2026-10-14
分支：`feat/mysql-task-queue-stability`

## 原因

- GitHub 后端 CI 的 Mypy 在 `task_service.py:106/129` 报出查询泛型赋值及响应转换错误，后续 Migration/pytest 未执行。
- 项目允许 `sqlalchemy[asyncio]>=2.0,<3`；本机安装 2.0.52，而新解析可安装 2.1.4。
- 固定 `Select[tuple[AsyncTask]]` 标注与 2.1 的 `Select[AsyncTask]` 泛型不同，使标量结果被误判为元组。此前本机 2.0 的通过不能替代新依赖环境验证。

## 修复

- `app/modules/system/task_service.py` 删除手写的 Select 泛型标注及未使用的导入，由 `select(AsyncTask)` 推断当前版本的查询类型。
- 不使用 `Any`、`cast`、`type: ignore` 或关闭 Mypy 规则绕过检查，不更改运行期 SQL 与业务逻辑。
- 不修改用户 `.env.example`、本机 `.env`、依赖范围或业务数据库。
- 同步 CURRENT_STATUS 与 System 模块状态。

## 验证

- 本机 SQLAlchemy 2.0.52 / Mypy 1.20.2：`ruff check .` 与 `mypy --no-incremental app` 通过，152 个应用源文件无错误。
- 使用临时依赖覆盖目录安装 SQLAlchemy 2.1.4，不升级正在使用的 `.venv`；旧泛型标注的最小例重现标量结果元组类型错误。修复后 `mypy --no-incremental app` 在 2.1.4 / Mypy 1.20.2 下通过，152 个应用源文件无错误。
- 在独立临时 MySQL 8.4 实例和 SQLAlchemy 2.1.4 下执行 `alembic upgrade head`、`pytest -q --tb=short`：538 passed，75 条已有 API 的弃用警告，无失败（52.34 秒）。
- 本机启动验证：全量测试包括两个 API Worker 的就绪检查和独立 HEAVY/MAPPING 子进程；全部连接隔离测试实例。测试实例、临时依赖和测试数据已清理，用户业务库及常驻进程未改动。
- 本机 Python 为 3.13，检查目标仍为项目配置的 Python 3.12；不据此宣称远程 Ubuntu/Python 3.12 流水线已通过。前端未改动，本次未重跑前端测试。

## 影响与边界

- Alembic Revision：无；API / UI / Permission：无变化。
- 不重启用户当前业务进程；本次为查询类型兼容修复。
- GitHub 新一次 CI 的最终结果以推送后流水线为准。
