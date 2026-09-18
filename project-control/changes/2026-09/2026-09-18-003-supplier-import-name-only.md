# 2026-09-18-003 Supplier Import Name-Only Required Field

## Scope

Supplier Master Excel import now treats only `供应商名称` as mandatory. `主营品牌`、`主要优势`、`联系人` and `联系电话` remain present in the approved five-column template but are optional for imported rows.

## Implementation

- Preview validation rejects only an empty supplier name (apart from existing duplicate and formula-cell checks).
- Confirm writes blank `主营品牌` and `主要优势` as empty strings because the existing formal Supplier columns are non-null; contacts remain absent when both contact cells are blank.
- Deleted-record recovery applies the same import mapping.
- Manual Supplier create and update requests remain unchanged: `supplier_name`、`main_brands` and `advantage` are still required there.

## Verification

- Supplier Excel integration coverage now previews and confirms a row that contains only a supplier name, then verifies its stored optional fields are empty strings.

## Schema / API

- Alembic Revision: none.
- API route and approved template headers: unchanged.
