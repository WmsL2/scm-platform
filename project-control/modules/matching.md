# 智能匹配

状态：FOUNDATION_IMPLEMENTED / PERSISTENCE_BLOCKED
Owner：feat/bid-matching-selection
Last Updated：2026-09-15

## Database
- [ ] 等待 1 号任务合入 `scm_bid_project`、`scm_bid_project_item`、`scm_match_task`、`scm_match_candidate` 与 `scm_bid_item_selection`；本任务不新增 Alembic Migration。

## Backend
- [x] 确定性匹配领域规则：NFKC、大小写、空白、分隔符与括号归一化；采购方编码精确召回、品牌+型号精确召回、名称/规格/类目降级召回。
- [x] 候选资格过滤：仅 `ACTIVE` Product 与 `ARCHIVED + NORMAL + not deleted` Source Supplier 可参与。
- [x] 评分、稳定排序、Top 20、匹配依据 JSON 和 `NO_MATCH` / `UNIQUE_MATCH` / `MULTIPLE_MATCH` 决策已在纯领域层实现。
- [x] 人工选品与无法报价的请求 DTO：只能选择已持久化候选，金额使用 Decimal，`OTHER` 无法报价原因必须说明。
- [ ] 等待共享表后实现候选持久化、追加式 Selection 快照、无法报价写入、任务队列和四个真实 API。

## Frontend
- [ ] 由 3 号任务负责；等待真实 API。

## Permissions
- [ ] 权限编码与种子数据由 1 号任务迁移统一落地；尚未接入 Router。

## Tests
- [x] 领域测试覆盖编码精确匹配、标准化品牌+型号、冲突排除、候选稳定排序、状态过滤、降级候选与输入不足。
- [x] DTO 测试覆盖候选选择绑定与无法报价原因校验。

## Known Issues
- 共享投标表、Migration、项目/Excel 基础设施尚未进入当前 `main`，不能安全提供真实数据库写入或 HTTP 接口。

## Next Step
1 号任务合入共享 Schema 后，按 `project-control/handoffs/2026-09-15-bid-matching-schema-dependency.md` 接入 Repository、Application Service、追加式快照与权限 API；随后由 3 号任务接真实页面。
