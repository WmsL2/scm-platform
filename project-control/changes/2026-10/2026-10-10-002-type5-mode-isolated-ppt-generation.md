# Change Record：类型 5 模式隔离 PPT 输出与模板资产可用性

日期：2026-10-10  
分支：`codex/fix/type5-single-ppt-mode`  
模块：recommendation

## 背景

类型 5 工作台原先在单品 Run 中仍展示“单品与组合套装”，而 PPT 任务会同时读取手工套装和已确认商品，造成单品/组合输出边界不清。四套私有业务模板在本机未配置受控 PPTX 资产时仍会展示为可点击，随后异步生成任务才失败。

## 变更

- PPT 生成按冻结配置分流：
  - `SINGLE` 只将已确认商品传入单品页，不读取或输出任何套装；
  - `COMBINATION` 只将已确认的 AI 组合方案转换为组合页；仅为历史 Run 保留无 AI 组合时的既有手工套装读取。
- 单品 Run 的后端拒绝创建套装，工作台不再显示手工组套区域；组合模式仍保留“额外人工组套”作为历史补充入口。
- 模板目录根据当前部署的受控资产目录判断可用性。私有 PPTX 缺失时模板卡禁用并标识“当前环境不可用”；生成接口在创建任务前再次拒绝，避免产生必然失败的异步记录。
- `SYSTEM_DEFAULT` 不依赖私有模板资产，仍可在本机直接生成可编辑 PPTX。私有模板要恢复可用，管理员需在 `PPT_TEMPLATE_ASSET_DIR` 放置对应经授权且版本匹配的 CLEAN v3 PPTX 文件。

## 范围与影响

- 不提交、不伪造或替代私有业务 PPTX 资产。
- 无数据库字段、Alembic、权限或类型 1--4 改动。
- 模板接口已有 `is_available` 字段，本次仅改为返回真实可用性；无需客户端合同升级。

## 验证

- `python -m pytest tests/recommendation/test_ppt_template_registry.py tests/recommendation/test_ppt_renderer.py tests/recommendation/test_ppt_solution_plans.py -q`：18 passed。
- `python -m ruff check app/modules/recommendation/application/ppt_service.py app/modules/recommendation/application/ppt_template_registry.py tests/recommendation/test_ppt_template_registry.py tests/recommendation/test_ppt_solution_plans.py`：通过。
- `python -m mypy app/modules/recommendation/application/ppt_service.py app/modules/recommendation/application/ppt_template_registry.py`：通过。
- `npm run test -- --run src/views/bid/PptSolutionWorkspaceView.spec.ts`：2 passed；`npm run typecheck`、`npm run build`：通过。

## 未完成验收

- 浏览器选择“系统默认版”执行一次真实生成并下载 PPTX。
- 如需使用四套业务模板，先在本机或部署环境配置经授权的对应私有 PPTX 资产后复验。
