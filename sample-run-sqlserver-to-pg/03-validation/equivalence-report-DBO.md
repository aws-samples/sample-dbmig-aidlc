# Equivalence Test Report — DBO

Mode: `silent`  |  Cases: 69  Passed: 69  Failed: 0  Skipped: 0

**LOW_COVERAGE** — every table these objects read was empty in the source, so the tests exercised only the empty / default path. A pass here is honest but shallow; re-test with representative data before cutover:

- `DBO.uspLogError`

| Object | Type | Case | Status | Coverage | Detail |
|---|---|---|---|---|---|
| DBO.ufnCalculateCustomerLifetimeValue | function | c1 | pass | OK | {'source': '103.49', 'target': '103.49'} |
| DBO.ufnCalculateCustomerLifetimeValue | function | c2 | pass | OK | {'source': '88.7', 'target': '88.70'} |
| DBO.ufnCalculateCustomerLifetimeValue | function | c3 | pass | OK | {'source': '2053.32', 'target': '2053.32'} |
| DBO.ufnCalculateCustomerLifetimeValue | function | c4 | pass | OK | {'source': None, 'target': None} |
| DBO.ufnGetAccountingEndDate | function | c1 | pass | n/a | {'source': '2004-06-30 23:59:59.997000', 'target': '2004-06-30 23:59:59.997000'} |
| DBO.ufnGetAccountingStartDate | function | c1 | pass | n/a | {'source': '2003-07-01 00:00:00', 'target': '2003-07-01 00:00:00'} |
| DBO.ufnGetDocumentStatusText | function | c1 | pass | n/a | {'source': 'Pending approval', 'target': 'Pending approval'} |
| DBO.ufnGetDocumentStatusText | function | c2 | pass | n/a | {'source': 'Obsolete', 'target': 'Obsolete'} |
| DBO.ufnGetDocumentStatusText | function | c3 | pass | n/a | {'source': '** Invalid **', 'target': '** Invalid **'} |
| DBO.ufnGetPurchaseOrderStatusText | function | c1 | pass | n/a | {'source': 'Approved', 'target': 'Approved'} |
| DBO.ufnGetPurchaseOrderStatusText | function | c2 | pass | n/a | {'source': 'Complete', 'target': 'Complete'} |
| DBO.ufnGetPurchaseOrderStatusText | function | c3 | pass | n/a | {'source': '** Invalid **', 'target': '** Invalid **'} |
| DBO.ufnGetSalesOrderStatusText | function | c1 | pass | n/a | {'source': 'In process', 'target': 'In process'} |
| DBO.ufnGetSalesOrderStatusText | function | c2 | pass | n/a | {'source': 'Shipped', 'target': 'Shipped'} |
| DBO.ufnGetSalesOrderStatusText | function | c3 | pass | n/a | {'source': 'Cancelled', 'target': 'Cancelled'} |
| DBO.ufnGetSalesOrderStatusText | function | c4 | pass | n/a | {'source': '** Invalid **', 'target': '** Invalid **'} |
| DBO.ufnLeadingZeros | function | c1 | pass | n/a | {'source': '00000123', 'target': '00000123'} |
| DBO.ufnLeadingZeros | function | c2 | pass | n/a | {'source': '00000000', 'target': '00000000'} |
| DBO.ufnLeadingZeros | function | c3 | pass | n/a | {'source': '12345678', 'target': '12345678'} |
| DBO.ufnLeadingZeros | function | c4 | pass | n/a | {'source': '0000000*', 'target': '0000000*'} |
| DBO.VwCustomerShopping | function | v1 | pass | OK | {'source': '95', 'target': '95'} |
| DBO.VwCustomerShopping | function | v2 | pass | OK | {'source': '8942.75', 'target': '8942.75'} |
| DBO.VwCustomerShopping | function | v3 | pass | OK | {'source': 'Hi, Bob! Your order #2 for $75.50 will be shipped shortly. Thank you!', 'target': 'Hi, Bob! Your order #2 for $75.50 will be shipped shortly. Thank … |
| DBO.VwCustomerShopping | function | v4 | pass | OK | {'source': 'Bob Marley', 'target': 'Bob Marley'} |
| DBO.VwOpenCoupons | function | v1 | pass | OK | {'source': '0', 'target': '0'} |
| DBO.VwOpenCoupons | function | v2 | pass | OK | {'source': '26924', 'target': '26924'} |
| DBO.VwRegionalSales | function | v1 | pass | OK | {'source': '10', 'target': '10'} |
| DBO.VwRegionalSales | function | v2 | pass | OK | {'source': '42194.34', 'target': '42194.34'} |
| DBO.VwRegionalSales | function | v3 | pass | OK | {'source': '3648', 'target': '3648.00'} |
| DBO.VwTopMembers | function | v1 | pass | OK | {'source': '10', 'target': '10'} |
| DBO.VwTopMembers | function | v2 | pass | OK | {'source': '4987.75', 'target': '4987.75'} |
| DBO.uspDeleteAuthor | procedure | p1 | pass | OK | {'authors': {'source_delta': '-1.0', 'target_delta': '-1.0', 'match': True}, 'author5': {'source_delta': '-1.0', 'target_delta': '-1.0', 'match': True}} |
| DBO.uspDeleteOldCoupons | procedure | p1 | pass | OK | {'coupons': {'source_delta': '-26.0', 'target_delta': '-26.0', 'match': True}, 'closed': {'source_delta': '-26.0', 'target_delta': '-26.0', 'match': True}} |
| DBO.uspDeleteOldCoupons | procedure | p2 | pass | OK | {'coupons': {'source_delta': '0.0', 'target_delta': '0.0', 'match': True}} |
| DBO.uspGetAuthorManagers | function | r1 | pass | OK | {'source': '0', 'target': '0'} |
| DBO.uspGetAuthorManagers | function | r2 | pass | OK | {'source': '0', 'target': '0'} |
| DBO.uspGetAuthorManagers | function | r3 | pass | OK | {'source': '0', 'target': '0'} |
| DBO.uspGetAuthorManagers | function | r4 | pass | OK | {'source': '0', 'target': '0'} |
| DBO.uspGetBillOfMaterials | function | r1 | pass | OK | {'source': '0', 'target': '0'} |
| DBO.uspGetBillOfMaterials | function | r1q | pass | OK | {'source': '0', 'target': '0'} |
| DBO.uspGetBillOfMaterials | function | r2 | pass | OK | {'source': '0', 'target': '0'} |
| DBO.uspGetBillOfMaterials | function | r2q | pass | OK | {'source': '0', 'target': '0'} |
| DBO.uspGetBillOfMaterials | function | r3 | pass | OK | {'source': '2', 'target': '2'} |
| DBO.uspGetBillOfMaterials | function | r3q | pass | OK | {'source': '3', 'target': '3.00'} |
| DBO.uspGetBillOfMaterials | function | r4 | pass | OK | {'source_rows': 3, 'target_rows': 3, 'source_first': "(497, 939, 'ML Road Pedal', Decimal('1'), Decimal('27.568'), Decimal('62.09'), 1, 2)", 'target_first': "(4… |
| DBO.uspGetManagerAuthors | function | r1 | pass | OK | {'source': '0', 'target': '0'} |
| DBO.uspGetManagerAuthors | function | r2 | pass | OK | {'source': '0', 'target': '0'} |
| DBO.uspGetManagerAuthors | function | r3 | pass | OK | {'source': '0', 'target': '0'} |
| DBO.uspGetManagerAuthors | function | r4 | pass | OK | {'source': '0', 'target': '0'} |
| DBO.uspGetProductData | function | r1 | pass | OK | {'source': '50669716', 'target': '50669716'} |
| DBO.uspGetTopRegion | function | r1 | pass | OK | {'source': '0', 'target': '0'} |
| DBO.uspGetTopRegion | function | r2 | pass | OK | {'source': '0', 'target': '0'} |
| DBO.uspGetTopRegion | function | r3 | pass | OK | {'source': '3', 'target': '3'} |
| DBO.uspGetWhereUsedProductID | function | r1 | pass | OK | {'source': '0', 'target': '0'} |
| DBO.uspGetWhereUsedProductID | function | r1q | pass | OK | {'source': '0', 'target': '0'} |
| DBO.uspGetWhereUsedProductID | function | r2 | pass | OK | {'source': '2', 'target': '2'} |
| DBO.uspGetWhereUsedProductID | function | r2q | pass | OK | {'source': '4', 'target': '4.00'} |
| DBO.uspGetWhereUsedProductID | function | r3 | pass | OK | {'source': '37', 'target': '37'} |
| DBO.uspGetWhereUsedProductID | function | r3q | pass | OK | {'source': '43', 'target': '43.00'} |
| DBO.uspLogError | procedure | l1 | pass | LOW_COVERAGE | {'errorlog': {'source_delta': '0.0', 'target_delta': '0.0', 'match': True}} |
| DBO.uspLogError | procedure | l2 | pass | LOW_COVERAGE | {'errorlog': {'source_delta': '1.0', 'target_delta': '1.0', 'match': True}, 'errnum': {'source_delta': '8134.0', 'target_delta': '8134.0', 'match': True}} |
| DBO.uspPrintError | procedure | p1 | pass | n/a | {'errorlog': {'source_delta': '0.0', 'target_delta': '0.0', 'match': True}} |
| DBO.uspProcessRefunds | procedure | p1 | pass | OK | {'coupons': {'source_delta': '3.0', 'target_delta': '3.0', 'match': True}, 'refunded': {'source_delta': '3.0', 'target_delta': '3.0', 'match': True}, 'max_ticke… |
| DBO.uspShoppingLevelAmount | function | r1 | pass | OK | {'source': '36', 'target': '36'} |
| DBO.uspShoppingLevelAmount | function | r2 | pass | OK | {'source': '95', 'target': '95'} |
| DBO.uspShoppingLevelAmount | function | r3 | pass | OK | {'source': '0', 'target': '0'} |
| DBO.uspUpdateAuthorLogin | procedure | u1 | pass | OK | {'login2': {'source_delta': "(True, 'adventure-works\\\\terri9')", 'target_delta': "(True, 'adventure-works\\\\terri9')", 'match': True}, 'flag2': {'source_delt… |
| DBO.uspUpdateAuthorLogin | procedure | u2 | pass | OK | {'login2': {'source_delta': "(False, 'adventure-works\\\\terri0')", 'target_delta': "(False, 'adventure-works\\\\terri0')", 'match': True}, 'errorlog': {'source… |
| DBO.uspUpdateAuthorPersonalInfo | procedure | u1 | pass | OK | {'marital3': {'source_delta': "(True, 'S')", 'target_delta': "(True, 'S')", 'match': True}} |
