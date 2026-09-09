# Supplier Field Dictionary / 供应商字段门禁

状态：FROZEN — `FIELD_FREEZE_READY_FOR_SCHEMA_DESIGN`  
范围：Supplier Master 字段语义与导入默认值；本文件不定义 Migration、ORM 或 API 实现。

## 来源字段与正式字段的边界

已取得的真实供应商信息表包含以下来源字段：供应商编码、供应商名称、主营品牌、主要优势、联系人、联系电话、供应商状态。

来源中的“供应商编码”（例如 `GYS001`、`GYS002`）不是系统正式 `supplier_code`，不得直接占用或覆盖系统编码。是否在将来作为可选的 legacy/reference 字段保留，留待单独设计确认。

| 来源字段 | 正式字段概念 | 冻结处理 |
|---|---|---|
| 供应商编码 | 不映射为 `supplier_code` | 仅历史来源参考；尚未决定是否正式保存 |
| 供应商名称 | `supplier_name` | 来源存在；当前样例无重复，但不建立 UNIQUE 约束 |
| 主营品牌 | `main_brands` | 原样保留为可含多个品牌的业务文本；不自动拆分品牌关系表 |
| 主要优势 | `advantage` | 普通业务文本 |
| 联系人 | `contact_name` | nullable；前端不设 required 校验 |
| 联系电话 | `contact_phone` | nullable；前端不设 required 校验；来源允许为空 |
| 供应商状态 | `archive_status`、`cooperation_status` | 不直接把来源状态文本当作正式状态值；按下列系统枚举处理 |

## 已冻结系统规则

- `supplier_code` 由后端系统自动生成，示例格式 `SUP00000001`；全局唯一、创建后不可修改、永久不回收，前端不得填写或修改。
- 归档状态 `archive_status`：`DRAFT`、`PENDING`、`ARCHIVED`。
- 合作状态 `cooperation_status`：`NORMAL`、`STOPPED`、`BLACKLIST`。
- 现有供应商首次导入时固定为 `archive_status = ARCHIVED`、`cooperation_status = NORMAL`：它们是公司已实际使用的正式供应商，而非新建草稿。
- Supplier Master 与 Product Master 是独立领域；正式关联使用系统 `supplier_id`，不用供应商名称作业务外键。一期不建设 Supplier Product Quote 领域。

## Supplier Gate

### 已确认字段

`supplier_name`、`main_brands`、`advantage`、`contact_name`、`contact_phone`，以及来源供应商编码和来源供应商状态的存在与语义边界。

### 已冻结规则

系统生成且唯一不可变的 `supplier_code`，双状态维度、联系人/电话可空，以及已有供应商首次导入的 `ARCHIVED + NORMAL` 默认值。

### 仍待后续确认

来源旧编码是否需要持久化为历史参考字段；以及未出现在已确认资料中的企业、税务、地址、银行、资质或合作等级字段。不得虚构这些字段，也不得据此创建正式 Schema。
