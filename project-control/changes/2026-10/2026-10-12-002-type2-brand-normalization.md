# Change Record：类型 2 受控品牌归一化

日期：2026-10-12  
分支：`feat/type2-brand-normalization`  
模块：matching / bid

## 问题

类型 2 原先对品牌归一化后仍要求完整字符串相等，客户品牌“联想”无法命中正式商品品牌“联想Lenovo”；品牌字段带“中国”“电脑”等修饰词时同样漏匹配。型号分隔符差异已受支持，无需引入模糊型号匹配。

## 本次变更

- 从本次任务的可用正式商品品牌构建并复用受控别名目录，连接中英文组合品牌的中文和英文别名。
- 支持安全后缀及唯一目录品牌识别；“中国”等可能属于正式品牌的前缀不盲目删除，原始输入和商品主数据不被改写。
- 多品牌歧义输入直接保持未匹配，未知品牌不猜测。
- 型号继续采用归一化后完整相等，明确拒绝 `TN328` 与 `TN328C` 等近似型号。
- 品牌别名匹配写入 `CANONICAL_ALIAS` 审计信号和中文优先标准品牌名，规则版本升级为 `v2`；原商品品牌展示值不被覆盖。

## 数据库、API 与权限

- Alembic Revision：无。
- API、UI、权限：无合同变化。

## 验证

- `pytest tests/bid tests/matching tests/recommendation -q`：134 passed（pytest 退出清理 Windows 临时目录时出现环境权限警告，不影响退出码 0）。
- `pytest tests/bid tests/matching -q`：37 passed（退出清理临时目录时出现 Windows `PermissionError` 警告，不影响测试通过和退出码）。
- `ruff check app/modules/bid app/modules/matching tests/bid tests/matching`：通过。
- `mypy app/modules/bid app/modules/matching`：通过。
