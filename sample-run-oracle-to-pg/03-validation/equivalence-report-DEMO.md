# Equivalence Test Report — DEMO

Mode: `silent`  |  Cases: 53  Passed: 53  Failed: 0  Skipped: 0

**LOW_COVERAGE** — every table these objects read was empty in the source, so the tests exercised only the empty / default path. A pass here is honest but shallow; re-test with representative data before cutover:

- `DEMO.GET_CUSTOMER_LIFETIME_VALUE`
- `DEMO.ARCHIVE_OLD_ORDERS`
- `DEMO.CLEAR_SHOPPING_CART`
- `DEMO.GENERATE_SALES_REPORT`

| Object | Type | Case | Status | Coverage | Detail |
|---|---|---|---|---|---|
| DEMO.CALCULATE_DISCOUNT_PCT | function | c1 | pass | n/a | {'source': '22.37', 'target': '22.37'} |
| DEMO.CALCULATE_DISCOUNT_PCT | function | c2 | pass | n/a | {'source': '0', 'target': '0'} |
| DEMO.CALCULATE_DISCOUNT_PCT | function | c3 | pass | n/a | {'source': '-7.69', 'target': '-7.69'} |
| DEMO.CALCULATE_DISCOUNT_PCT | function | c4 | pass | n/a | {'source': '66.67', 'target': '66.67'} |
| DEMO.GET_CONDITION_NAME | function | c1 | pass | OK | {'source': 'New', 'target': 'New'} |
| DEMO.GET_CONDITION_NAME | function | c2 | pass | OK | {'source': 'Good', 'target': 'Good'} |
| DEMO.GET_CONDITION_NAME | function | c3 | pass | OK | {'source': 'Unknown', 'target': 'Unknown'} |
| DEMO.GET_CUSTOMER_FULL_NAME | function | c1 | pass | OK | {'source': 'Admin User', 'target': 'Admin User'} |
| DEMO.GET_CUSTOMER_FULL_NAME | function | c2 | pass | OK | {'source': 'John Doe', 'target': 'John Doe'} |
| DEMO.GET_CUSTOMER_FULL_NAME | function | c3 | pass | OK | {'source': 'Unknown Customer', 'target': 'Unknown Customer'} |
| DEMO.GET_CUSTOMER_LIFETIME_VALUE | function | c1 | pass | LOW_COVERAGE | {'source': '0', 'target': '0'} |
| DEMO.GET_CUSTOMER_LIFETIME_VALUE | function | c2 | pass | LOW_COVERAGE | {'source': '0', 'target': '0'} |
| DEMO.GET_GENRE_NAME | function | c1 | pass | OK | {'source': 'Biographies', 'target': 'Biographies'} |
| DEMO.GET_GENRE_NAME | function | c2 | pass | OK | {'source': 'History', 'target': 'History'} |
| DEMO.GET_GENRE_NAME | function | c3 | pass | OK | {'source': 'Unknown', 'target': 'Unknown'} |
| DEMO.BOOK_PKG | function | b1 | pass | OK | {'source': '0', 'target': '0'} |
| DEMO.BOOK_PKG | function | b2 | pass | OK | {'source': '0', 'target': '0.00'} |
| DEMO.BOOK_PKG | function | b3 | pass | OK | {'source': '0', 'target': '0'} |
| DEMO.BOOK_PKG | function | b4 | pass | OK | {'source': '0', 'target': '0'} |
| DEMO.BOOK_PKG | function | b5 | pass | OK | {'source': '0', 'target': '0.00'} |
| DEMO.BOOK_PKG | function | b6 | pass | OK | {'source': '0', 'target': '0'} |
| DEMO.BOOK_PKG | procedure | b7 | pass | OK | {'books_count': {'source_delta': '0.0', 'target_delta': '0.0', 'match': True}} |
| DEMO.INVENTORY_PKG | function | i1 | pass | OK | {'source': '1', 'target': '1'} |
| DEMO.INVENTORY_PKG | function | i2 | pass | OK | {'source': '0', 'target': '0'} |
| DEMO.INVENTORY_PKG | function | i3 | pass | OK | {'source': None, 'target': None} |
| DEMO.INVENTORY_PKG | function | i4 | pass | OK | {'source': '0', 'target': '0'} |
| DEMO.INVENTORY_PKG | function | i5 | pass | OK | {'source': '0', 'target': '0'} |
| DEMO.INVENTORY_PKG | procedure | i6 | pass | OK | {'qty_listing_1': {'source_delta': '-3.0', 'target_delta': '-3.0', 'match': True}, 'updated_set': {'source_delta': '1.0', 'target_delta': '1.0', 'match': True},… |
| DEMO.ORDER_PKG | function | o1 | pass | PARTIAL | {'source': '0', 'target': '0'} |
| DEMO.ORDER_PKG | function | o2 | pass | PARTIAL | {'source': '0', 'target': '0'} |
| DEMO.ORDER_PKG | procedure | o3 | pass | PARTIAL | {'pending_cust1': {'source_delta': '1.0', 'target_delta': '1.0', 'match': True}} |
| DEMO.ORDER_PKG | procedure | o4 | pass | PARTIAL | {'items': {'source_delta': '1.0', 'target_delta': '1.0', 'match': True}, 'total_cust2': {'source_delta': '21.9', 'target_delta': '21.9', 'match': True}, 'item_p… |
| DEMO.ORDER_PKG | procedure | o5 | pass | PARTIAL | {'shipped': {'source_delta': '1.0', 'target_delta': '1.0', 'match': True}} |
| DEMO.REPORTING_PKG | function | r1 | pass | PARTIAL | {'source': '0', 'target': '0'} |
| DEMO.REPORTING_PKG | function | r2 | pass | PARTIAL | {'source': '0', 'target': '0'} |
| DEMO.REPORTING_PKG | procedure | r3 | pass | PARTIAL | {'top_rows': {'source_delta': '2.0', 'target_delta': '2.0', 'match': True}, 'top_sold': {'source_delta': '3.0', 'target_delta': '3.0', 'match': True}, 'top_reve… |
| DEMO.REPORTING_PKG | procedure | r4 | pass | PARTIAL | {'orders_count': {'source_delta': '0.0', 'target_delta': '0.0', 'match': True}} |
| DEMO.VALIDATION_PKG | function | v1 | pass | n/a | {'source': '1', 'target': '1'} |
| DEMO.VALIDATION_PKG | function | v2 | pass | n/a | {'source': '0', 'target': '0'} |
| DEMO.VALIDATION_PKG | function | v3 | pass | n/a | {'source': '1', 'target': '1'} |
| DEMO.VALIDATION_PKG | function | v4 | pass | n/a | {'source': '1', 'target': '1'} |
| DEMO.VALIDATION_PKG | function | v5 | pass | n/a | {'source': '0', 'target': '0'} |
| DEMO.VALIDATION_PKG | function | v6 | pass | n/a | {'source': '0', 'target': '0'} |
| DEMO.VALIDATION_PKG | function | v7 | pass | n/a | {'source': '1', 'target': '1'} |
| DEMO.VALIDATION_PKG | function | v8 | pass | n/a | {'source': '0', 'target': '0'} |
| DEMO.VALIDATION_PKG | function | v9 | pass | n/a | {'source': '0', 'target': '0'} |
| DEMO.VALIDATION_PKG | function | v10 | pass | n/a | {'source': '3', 'target': '3'} |
| DEMO.VALIDATION_PKG | function | v11 | pass | n/a | {'source': '56', 'target': '56'} |
| DEMO.ARCHIVE_OLD_ORDERS | procedure | a1 | pass | LOW_COVERAGE | {'orders_count': {'source_delta': '0.0', 'target_delta': '0.0', 'match': True}} |
| DEMO.CLEAR_SHOPPING_CART | procedure | s1 | pass | LOW_COVERAGE | {'cart_count': {'source_delta': '0.0', 'target_delta': '0.0', 'match': True}} |
| DEMO.GENERATE_SALES_REPORT | procedure | g1 | pass | LOW_COVERAGE | {'orders_count': {'source_delta': '0.0', 'target_delta': '0.0', 'match': True}} |
| DEMO.PROCESS_CUSTOMER_OFFER | procedure | p1 | pass | OK | {'store_listings': {'source_delta': '0.0', 'target_delta': '0.0', 'match': True}} |
| DEMO.SET_BOOK_FEATURED | procedure | f1 | pass | OK | {'featured': {'source_delta': '0.0', 'target_delta': '0.0', 'match': True}} |
