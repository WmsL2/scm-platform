# 2026-10-16-001：类型 5 价格档唯一控制单品协议价

Change ID：2026-10-16-001  
Module：Recommendation / Type 5 PPT Solution  
Author / Agent：Codex  
Date：2026-10-16  
Branch：`codex/fix/type5-fee-tier-not-single-price`  
Commit：待提交

## Goal

修复类型 5 将需求备注中的福利费用档位/方案预算错误映射为单品协议价硬条件的问题。页面保存的价格档成为单品协议价的唯一硬筛边界；明确京东价、毛利率、折扣率、强制品牌和受控类目保持原有行为。

## Created Files

- `apps/api-server/tests/recommendation/test_ppt_selection_adapter.py`
- `project-control/decisions/ADR-0066-type5-price-band-authority.md`
- `project-control/changes/2026-10/2026-10-16-001-type5-price-band-authority.md`

## Modified Files

- `apps/api-server/app/modules/recommendation/application/ppt_selection_adapter.py`
- `apps/api-server/app/modules/recommendation/application/ppt_selection_runner.py`
- `apps/api-server/app/modules/recommendation/application/ppt_plan_runner.py`
- `apps/api-server/tests/recommendation/test_ppt_selection_runner.py`
- `project-control/modules/recommendation.md`
- `project-control/CURRENT_STATUS.md`

## Deleted Files

无。

## Database / Alembic

Revision：无。

## API Changes

无。

## UI Changes

无；既有类型 5 页面价格档继续作为单品协议价的唯一配置入口。

## Permission Changes

无。

## Business Rule Changes

- 费用档位、慰问标准、方案预算和需求备注内的协议价文本不再参与类型 5 单品协议价硬筛。
- 页面价格档是类型 5 单品协议价的唯一硬筛条件。
- 明确京东价、毛利率、折扣率、强制品牌和受控类目仍参与既有硬筛。

## Tests

Command：

```powershell
cd apps/api-server
.\.venv\Scripts\python.exe -m pytest tests/recommendation/test_ppt_selection_runner.py tests/recommendation/test_ppt_selection_adapter.py
```

Result：3 passed。

```powershell
cd apps/api-server
.\.venv\Scripts\python.exe -m pytest tests/recommendation/test_ppt_selection_runner.py tests/recommendation/test_ppt_selection_adapter.py tests/recommendation/test_ppt_plan_runner.py tests/recommendation/test_ppt_solution_plans.py tests/recommendation/test_recommendation_core_service.py
.\.venv\Scripts\python.exe -m ruff check app/modules/recommendation/application/ppt_selection_adapter.py app/modules/recommendation/application/ppt_selection_runner.py app/modules/recommendation/application/ppt_plan_runner.py tests/recommendation/test_ppt_selection_runner.py tests/recommendation/test_ppt_selection_adapter.py
.\.venv\Scripts\python.exe -m mypy app/modules/recommendation/application/ppt_selection_adapter.py app/modules/recommendation/application/ppt_selection_runner.py app/modules/recommendation/application/ppt_plan_runner.py
```

Result：28 passed；Ruff 全部通过；Mypy 3 个源文件无问题。

项目控制门禁待本分支收尾执行。

## Known Issues

- 不回写历史 Run；已有失败 Run 需以相同项目配置重新生成，才会使用新规则。
- 真实服务器浏览器验收仍需确认 `0--50` 页面价格档可返回 ¥45/¥49 商品，同时备注保留 100/200/300/500 元费用档位。
- `tests/recommendation` 全量收集 306 项时，未修改的 `test_ppt_renderer.py` 出现 4 项失败；首个复现为 `JD_DETAIL_RED v5` 仅支持单品页，却被通用“每个内置模板均生成组合”断言传入组合数据。该渲染合同与本次价格筛选改动无调用关系，未在本分支调整。

## Remaining Work

- 执行项目控制门禁。
- 进行服务器新 Run 的浏览器验收。

## Next Step

在服务器部署本分支后，以会员慰问品需求重建类型 5 Run，确认费用档位不再与页面单品价格档相交。
