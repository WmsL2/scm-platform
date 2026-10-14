# Change Record：Type-5 公共模板资产迁移

日期：2026-10-14  
模块：recommendation  
状态：IMPLEMENTED / 模板 2 客户最终视觉验收仍待完成

## 审计范围与结论

本次未启动服务、未创建真实任务、未访问或修改商品数据库。用户已明确批准两份审核后的 v5 CLEAN 运行模板进入现有 GitHub 公开仓库；原始客户 PPT、真实商品资料、诊断输出及其他私有文件仍未迁移。

- 当前分支：`codex/type5-official-template1-v5`。
- 工作区在审计开始前已有 Type-5 渲染、前端、配置和项目控制文档的未提交修改；这些修改未由本次审计覆盖或还原。
- 公共目录现有四个 v3 CLEAN 资产和两份已批准的 v5 CLEAN 资产。
- 当前本机实际 `PPT_TEMPLATE_ASSET_DIR` 指向 Git 忽略的 `.codex-assets/local-v5-runtime/ppt-templates`。模板 1 的实际运行文件为该目录中 SHA-256 `D2E3CFFE8D22601A5017B64E0C3A878842EE241718A3EFE8FCD3EAE732F92C2D` 的 `JD_DETAIL_RED_OFFICIAL_CLEAN_v5.pptx`。
- 两份候选 v5 运行文件均包含“京东”品牌文字和嵌入媒体。ZIP 审计确认没有备注页或外部关系，但这不能证明 Logo、品牌和嵌入素材已经获准公开分发。
- ADR-0052 只确认既有 CLEAN v3 是可公开分发资产，并要求未确认授权的品牌标识、装饰图片及其他媒体不得提交。当前 v5 的最近记录仍把它们称作私有运行资产，未提供针对 v5 的公开分发授权记录。

经用户明确授权，以下两份文件已从当前实际运行目录逐字节复制到 `assets/ppt-templates/`：模板 1 的 SHA-256 为 `D2E3CFFE8D22601A5017B64E0C3A878842EE241718A3EFE8FCD3EAE732F92C2D`，模板 2 的 SHA-256 为 `F0814AF47B80B281E3407C4373CA88F03E3CDFF7409DC30473E71DA7070D12B7`。源文件与私有目录均未修改，未删除任一资产。

## 模板资产清单

| 路径 / 文件 | 模板代码 / 版本 | SHA-256 | Git 跟踪 | 当前引用 / 历史依赖 | 公开分发判断 | 建议 |
|---|---|---|---|---|---|---|
| `assets/ppt-templates/JD_DETAIL_RED_CLEAN_v3.pptx` | `JD_DETAIL_RED` v3 | `9F544B771376404C82E6B56EBFBA6D5A9FD7FC7DE8AAE38AE9EB76FA56F32DA2` | 是 | v3 manifest、默认模板、历史任务及回归测试 | ADR-0052 已确认 | 保留 |
| `assets/ppt-templates/JD_FESTIVE_RED_CLEAN_v3.pptx` | `JD_FESTIVE_RED` v3 | `0CC5D1939EE9F2336AB178130AE463CC82F1FAA9EF971887CFFD6395F9710C26` | 是 | v3 manifest、默认模板、历史任务及回归测试 | ADR-0052 已确认 | 保留 |
| `assets/ppt-templates/CATALOG_MINIMAL_CLEAN_v3.pptx` | `CATALOG_MINIMAL` v3 | `D3E09119C75A897CDCB69FEB9AD6B7A45273C5A4FD487765D8DB4FF75427BCF5` | 是 | v3 manifest、默认模板、历史任务及回归测试 | ADR-0052 已确认 | 保留 |
| `assets/ppt-templates/UNION_QUOTE_WHITE_CLEAN_v3.pptx` | `UNION_QUOTE_WHITE` v3 | `2B39F5078E723839B0B9D8DDCEB05ED2740FF28263C59F9FA86EC71888E9E398` | 是 | v3 manifest、默认模板、历史任务及回归测试 | ADR-0052 已确认 | 保留 |
| `assets/ppt-templates/JD_DETAIL_RED_OFFICIAL_CLEAN_v5.pptx` | `JD_DETAIL_RED` v5 | `D2E3CFFE8D22601A5017B64E0C3A878842EE241718A3EFE8FCD3EAE732F92C2D` | 新增待提交 | v5 manifest、专用 renderer、v5 测试 | 本次用户批准 | 保留 |
| `.codex-assets/local-v5-runtime/ppt-templates/JD_DETAIL_RED_OFFICIAL_CLEAN_v5.pptx` | `JD_DETAIL_RED` v5 源文件 | 同上 | 否 | 当前运行源；未修改 | 私有源副本 | 保留，不删除 |
| `.codex-assets/local-v5-runtime/ppt-templates/JD_DETAIL_RED_OFFICIAL_CLEAN_v5.backup-20261014-D2E3CFFE8D22.pptx` | `JD_DETAIL_RED` v5 备份 | 同上 | 否 | 无运行引用；与实际运行文件字节一致 | 私有备份 | 不迁移、不删除 |
| `assets/ppt-templates/JD_FESTIVE_RED_OFFICIAL_CLEAN_v5.pptx` | `JD_FESTIVE_RED` v5 | `F0814AF47B80B281E3407C4373CA88F03E3CDFF7409DC30473E71DA7070D12B7` | 新增待提交 | v5 manifest、专用 renderer、v5 测试 | 本次用户批准 | 保留；当前仍待客户最终视觉验收 |
| `.codex-assets/local-v5-runtime/ppt-templates/JD_FESTIVE_RED_OFFICIAL_CLEAN_v5.pptx` | `JD_FESTIVE_RED` v5 源文件 | 同上 | 否 | 当前运行源；未修改 | 私有源副本 | 保留，不删除 |
| `.codex-assets/local-v5-runtime/ppt-templates/JD_DETAIL_RED_CLEAN_v4-text-fix.pptx` | `JD_DETAIL_RED` v4 | `A787010C314BFA481C8ABAF670480777CEA82B716611EA46EA78BE550D1D5C56` | 否 | 版本化 manifest、历史 v4 renderer 与回归测试 | 私有历史兼容版本 | 保留，不迁移、不删除 |
| `.codex-assets/local-v5-runtime/ppt-templates/JD_FESTIVE_RED_CLEAN_v4.pptx` | `JD_FESTIVE_RED` v4 | `EF0BF403E0A6CA471A7C01C92C12938E310855E941A29B6727A785EAAFD78BA3` | 否 | 版本化 manifest、历史 v4 renderer 与回归测试 | 私有历史兼容版本 | 保留，不迁移、不删除 |
| `.codex-assets/local-v5-runtime/ppt-templates/CATALOG_MINIMAL_CLEAN_v4.pptx` | `CATALOG_MINIMAL` v4 | `A59C710755DE3827F691F588C8F6046292D1EBAFA9BC791E2D1011036633BEA5` | 否 | 版本化 manifest、v4 回归测试 | 私有历史兼容版本 | 保留，不迁移、不删除 |
| `.codex-assets/local-v5-runtime/ppt-templates/UNION_QUOTE_WHITE_CLEAN_v4.pptx` | `UNION_QUOTE_WHITE` v4 | `DF95632C170E97BA3E7C1C3158CC4EF895448C6B17C8BEF65A4A0A6887B846A4` | 否 | 版本化 manifest、v4 回归测试 | 私有历史兼容版本 | 保留，不迁移、不删除 |
| `.codex-assets/local-v5-runtime/ppt-templates/*_CLEAN_v3.pptx`（4 个） | 四个 v3 | 与公共同 SHA | 否 | 仅显式私有目录覆盖时可被加载 | 重复副本；但显式目录和历史环境可能依赖 | 不迁移、不删除 |
| `.codex-assets/official-ppt/runtime/JD_DETAIL_RED_OFFICIAL_CLEAN_v5.pptx` | `JD_DETAIL_RED` v5 | `6FE174FC4B45EAD2DFAF005018CD1C906A14D89A393B7F59E3D30A001986808B` | 否 | 未被当前 `PPT_TEMPLATE_ASSET_DIR` 使用；与当前运行文件不一致 | 私有旧运行副本 | 保留，不能用它替换已验收文件 |
| `.codex-assets/official-ppt/runtime/JD_FESTIVE_RED_OFFICIAL_CLEAN_v5.pptx` | `JD_FESTIVE_RED` v5 | `912BA704432B54D211890E96994E32A70A9026E5AE727B3964CE44284CDB4488` | 否 | 未被当前 `PPT_TEMPLATE_ASSET_DIR` 使用；与当前运行文件不一致 | 私有旧运行副本 | 保留，不能用它替换当前开发文件 |

`.codex-assets/official-ppt/originals/` 中的 5 份客户原件、`.codex-assets/official-ppt/samples/` 中的虚构样例、`.codex-assets/ppt-v4-review/` 等验证目录，以及 `local-data/ppt-template-verification/` 中的生成结果均不属于可发布运行资产。本次未修改它们。

## 代码与配置影响

- `ppt_template_registry.py` 现使所有已批准版本（含 v5）在未显式配置时从 `PROJECT_ROOT / "assets" / "ppt-templates"` 读取；显式目录仍严格解析且不跨版本回退。
- `ppt_template_manifest.py` 的 v5 `clean_filename` 已与拟迁移文件名一致，不需要改名。
- `config.py` 已将相对 `PPT_TEMPLATE_ASSET_DIR` 以 `PROJECT_ROOT` 解析，满足可移植路径规则。
- `apps/api-server/.env` 已仅替换 PPT 模板目录为 `assets/ppt-templates`，保留数据库、JWT 与 AI 配置，并维持 `PPT_V5_LAYOUT_PREVIEW=0`。
- `apps/api-server/.env.example` 和根 `.env.example` 已使用可移植公共目录、无个人绝对路径或真实凭据；注释说明版本化资产和严格解析规则。

## 验证与后续

- 定向公共 v5 默认解析与真实渲染测试：4 passed。两套模板均从公共目录生成两页输出；模板 1 正式输出不含排版诊断页。
- `Settings(ppt_template_asset_dir="assets/ppt-templates")` 解析为项目根目录下的公共目录。
- `ruff check .` 与 `mypy app` 通过；`git diff --check` 通过。
- Recommendation 全量仍有 5 个既有失败，均来自启用本地 v5 默认版本后旧测试仍假定 v3/组合/旧价格文案。未删除或掩盖这些测试。
- 模板 2 的卖点容量已有独立 Change `2026-10-14-008`；该模板仍不可标记为客户最终视觉验收完成。

Alembic Revision：无。API、UI、Permission、数据库：无变化。服务启动：未执行。未 commit、push 或创建 PR。
