# Change Record: Product / Category / Pricing Schema Review

Change ID: 2026-09-07-015
Module: catalog / category-pricing
Branch: docs/product-category-schema-review

## Changes

- 瀹屾垚鐪熷疄鍟嗗搧澶ц〃 31 瀛楁鐨?Product Schema Matrix銆?- 瀹屾垚涓夌骇 Category Dimension銆丳roduct 鈫?Category FK 涓庣被鐩墸鐐瑰揩鐓ц瘎瀹″缓璁€?- 姣旇緝涓€鏈?Pricing 鎵胯浇鏂瑰紡锛屽缓璁綋鍓嶈緭鍏ヤ笌娲剧敓鍊肩洿鎺ユ斁鍏?`scm_product`銆?- 缁欏嚭閲戦 `DECIMAL(18,4)`銆佹瘮鐜?`DECIMAL(9,4)` 鐨勫缓璁紱鏅€?Decimal 鑸嶅叆宸插喕缁撲负 `ROUND_HALF_UP` / 4 浣嶏紝`deduction_review` 缁х画涓?`ROUND_DOWN` / 4 浣嶃€?- 鏄庣‘ `scm_category.deduction_rate` 鏄被鐩樊寮傜殑鍞竴姝ｅ紡杩愯鏃舵潵婧愶紝Product 淇濆瓨瀹為檯浣跨敤鐨勬墸鐐瑰揩鐓с€?- 鏄庣‘ Excel 鈥滀緵搴斿晢鈥濆垪涓?IMPORT_ONLY锛屼笉鍒涘缓 Product-Supplier FK 鎴?Supplier Product Quote銆?
## Database / Code

鏃?Migration銆丱RM銆丄PI銆乁I 鎴?Pricing Service 鍙樻洿銆?
## Next Step

瀹屾垚 Schema Review锛屽喕缁撶粨鏋勪笌閫氱敤 Decimal 鑸嶅叆绛栫暐鍚庯紝鎵嶈繘鍏?Pricing Service銆丆ategory/Product Migration 鍜?Backend 瀹炴柦銆?
