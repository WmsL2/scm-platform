# Change Record：模板 1 v5 终审缺陷修复

日期：2026-10-13
模块：recommendation
状态：IMPLEMENTED / PRIVATE DESKTOP RENDER EVIDENCE PENDING

## P0：卖点容量

卖点容量改为按运行模板 `SCM_FIELD_SELLING_POINTS` 实际几何计算：扣除文本框内边距后的可用宽高、12pt 字号、单倍行距的保守 1.2 行高，以及每条带编号文本自动换行后的总行数。仅当标题和全部卖点行都能安全放入时才生成。

正式私有运行模板已验证如下复现输入会返回 `PPT_TEMPLATE_TEXT_CAPACITY_EXCEEDED`，不会生成溢出页面：

```python
"\n".join(["宽" * 40] * 6)
```

未自行增加续页或改变客户版式。

## P1：模板合同与私有构建

- 标准化前校验正式原件的 3 页、每页形状类型/数量和 SHA-256 结构指纹；合同不符返回 `PPT_TEMPLATE_ASSET_STRUCTURE_INVALID`。
- 运行时校验 2 页运行资产、商品页 15 个对象、全部必需且唯一的文本/图片槽及槽类型；缺槽/重复槽不再导致未处理的 `KeyError`。
- 构建脚本在运行资产同目录创建临时 PPTX，完成标准化、样例媒体哈希清理和运行结构验证后才原子替换目标；失败会删除候选并保留原已审核运行资产。

## P2：类型检查与测试

- 移除 `ppt_official_template_v5.py` 的全模块 `# mypy: ignore-errors`；关键渲染、结构验证、克隆和图片替换函数采用显式类型，第三方 `python-pptx` 未类型化构造器只保留局部忽略。
- 新增长标题、长 SKU、长规格、六条自动换行卖点、缺失图片、结构合同、槽缺失和原子构建失败回归测试。

## 影响

无 Alembic Revision、API、UI、权限、数据库、选品或报价规则变化。客户原件、运行模板和虚构样例仍位于 Git 忽略私有目录；v3/v4、模板 2--5 未修改。
