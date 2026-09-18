# ADR-0029：商品导入内嵌图片逐张流式保存

状态：ACCEPTED
日期：2026-09-18

## Context

真实商品大表包含四千余个 WPS/Excel `DISPIMG` 内嵌图片，媒体总量超过 500MB。旧实现把图片累计读入内存，并在达到 50MB 后停止提取，导致 Confirm 成功但后续商品静默缺图；部分媒体还是 TIFF/EMF，浏览器不能直接稳定显示。

## Decision

- 预览只读取 `cellimages.xml`、关系文件和 ZIP 条目元数据；存在 `DISPIMG` 公式但找不到对应媒体、类型不支持或单图超限时，该行不通过。
- Confirm 仅打开一次工作簿 ZIP，按唯一图片引用逐张提取到受控临时目录、解码校验并通过 `ObjectStorage.save_file` 保存；每次仅持有一张图片，不设全工作簿图片累计上限。
- PNG、JPEG、GIF、WebP 保持原格式；TIFF、EMF、BMP、WMF 转换为 PNG 后保存，正式 Product 只引用浏览器可显示的媒体。
- 单张内嵌图片上限由 `PRODUCT_IMPORT_MAX_IMAGE_MB` 配置，默认 64MB；坏图或解码失败使本次 Confirm 原子失败，已暂存的新图片按精确 key 清理。
- 图片列真正为空时仍允许导入。此变更不回填历史商品，也不改写既有图片引用；用户重新上传并 Confirm 后应用新逻辑。

## Consequences

- 大表图片总量不再造成静默截断；内存峰值主要由单张图片解码决定，而不是整批图片总量。
- 预览不能保证媒体内容一定可解码，最终解码仍在 Confirm 执行；失败会明确返回错误并保持数据库事务原子性。
- Pillow 成为后端运行时依赖；无数据库 Schema 变化，无 Alembic Revision。

## Related

- ADR-0011 商品导入图片使用项目相对本地存储（缺图仅警告条款被本 ADR 替代）
- ADR-0017 商品导入图片仅在确认时落盘
- ADR-0022 商品大表分块上传与磁盘只读解析
- ADR-0027 商品导入数值安全、分页与并发确认
