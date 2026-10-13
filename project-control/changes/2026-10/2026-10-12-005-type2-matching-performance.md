# Change：类型 2 大表匹配性能优化

日期：2026-10-12  
状态：IMPLEMENTED / REAL_DEEPSEEK_RETRY_PENDING

## 问题

- 288 条需求对 7,246 条正式商品构建候选时，每个“需求行 × 商品”组合都会重复拼接文本、拆分搜索词和归一化型号，本地候选阶段约耗时 80 秒。
- 每行最多携带 20 条候选，10 行一批时单次 DeepSeek 输入约 2.8 万至 3.9 万 Token。
- `asyncio.gather` 中一个批次失败后，其他已发出的请求仍继续运行，接口返回失败后仍消耗时间和 Token。

## 修改

- 商品搜索文本、搜索词、归一化型号及品牌目录改为每个匹配任务只构建一次。
- 每个需求行只向 AI 提交确定性排序后的前 8 条候选；原品仍排在替代品之前，最终资格、限价、折扣和最低价规则不变。
- 并发批次任一失败时，显式取消同轮尚未结束的请求并等待取消收敛。
- 新增性能回归测试，验证商品搜索文档构建次数只随商品数量增长，且候选池不超过 8 条。

## 验证

- 真实开发库只读基准：288 行需求、7,246 条商品，候选构建 9.614 秒；优化前约 80 秒。
- `python -m ruff check app/modules/matching tests/matching`：通过。
- `python -m mypy app/modules/matching`：通过。
- `python -m pytest tests/bid tests/matching -q`：45 passed。
- pytest 结束后的 Windows 临时目录清理出现 `pytest-current` 权限警告，不影响测试结果和业务数据。

## 兼容性

- 无数据库 Schema 变化，无 Alembic Revision。
- 无 API、UI 或权限变化。
- 类型 1、3、4、5 不变。
