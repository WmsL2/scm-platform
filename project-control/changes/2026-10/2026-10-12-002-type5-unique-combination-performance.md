# Change Record：类型 5 组合全局去重、短缺保留与受控加速

日期：2026-10-12
分支：`codex/feat/type5-unique-combination-performance`
模块：recommendation

## 问题

组合生成按价格档独立选择，组内虽然不重复，但同一商品可出现在多张组合卡中。请求数量大于可构成的无重复合规组合数时，旧逻辑会使整次 Run 失败，页面不会显示已经可用的组合。

## 变更

- 类型 5 `COMBINATION` 在后端维护 Run 级已占用商品集合；组合内、同档和跨价格档均禁止重复 `product_id`。
- 全池继续以压缩字段做 AI 场景/性价比粗评；组合候选由后端在价格、2--4 件、类目多样性和去重约束下受限生成，AI 再对详细组合短名单作最终精评。
- 组合首轮评估不再人为压到两路，使用配置值但最多四路并发；候选组保留更多但仍有上限的备选，以提高高数量目标的无重复覆盖率。
- 若只能生成部分组合，保留并持久化全部可行组合，Run 正常进入人工确认。工作台显示“AI 已生成 N / 目标 M 组”及不足提示；只有零组合才报生成失败。
- 类型 1--4、类型 5 单品模式、PPT 渲染、套餐创建、权限和现有 API 路径不变。

## 数据库 / 接口

- Alembic Revision：无。
- API：无新增或破坏性合同；组合计划列表继续返回已生成的可行组。
- UI：组合工作台新增目标数量与实际生成数量、短缺说明。

## 验证

- `apps/api-server/.venv/Scripts/python.exe -m pytest tests/recommendation/test_ppt_plan_runner.py tests/recommendation/test_ppt_solution_plans.py -q`：18 passed。
- `apps/api-server/.venv/Scripts/python.exe -m ruff check app/modules/recommendation/application/ppt_plan_runner.py app/modules/recommendation/application/ppt_service.py tests/recommendation/test_ppt_plan_runner.py`：通过。
- `npm run test -- --run src/views/bid/PptSolutionWorkspaceView.spec.ts`：2 passed。
- `npm run typecheck`：通过。

## 待验收

- 使用真实 DeepSeek 在高数量组合（例如目标 50 组）验证吞吐、全局无重复、短缺提示和人工确认后 PPT 生成。
