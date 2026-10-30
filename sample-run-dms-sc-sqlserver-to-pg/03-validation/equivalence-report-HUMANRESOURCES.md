# Equivalence Test Report — HUMANRESOURCES

Mode: `silent`  |  Cases: 16  Passed: 16  Failed: 0  Skipped: 4

| Object | Type | Case | Status | Coverage | Detail |
|---|---|---|---|---|---|
| HUMANRESOURCES.vEmployee | function | c1 | pass | OK | {'source': '290', 'target': '290'} |
| HUMANRESOURCES.vEmployee | function | c2 | pass | OK | {'source_rows': 290, 'target_rows': 290, 'source_first': "(259, None, 'Ben', 'T', 'Miller', None, 'Buyer', '151-555-0113', 'Work', 'ben0@adventure-works.com', 0… |
| HUMANRESOURCES.vEmployee | function | c3 | pass | OK | {'source': 'United States', 'target': 'United States'} |
| HUMANRESOURCES.vEmployeeDepartment | function | c1 | pass | OK | {'source': '290', 'target': '290'} |
| HUMANRESOURCES.vEmployeeDepartment | function | c2 | pass | OK | {'source_rows': 290, 'target_rows': 290, 'source_first': "(1, None, 'Ken', 'J', 'Sánchez', None, 'Chief Executive Officer', 'Executive', 'Executive General and … |
| HUMANRESOURCES.vEmployeeDepartmentHistory | function | c1 | pass | OK | {'source': '296', 'target': '296'} |
| HUMANRESOURCES.vEmployeeDepartmentHistory | function | c2 | pass | OK | {'source_rows': 296, 'target_rows': 296, 'source_first': "(263, None, 'Jean', 'E', 'Trenary', None, 'Day', 'Information Services', 'Executive General and Admini… |
| HUMANRESOURCES.uspUpdateEmployeeLogin | procedure | c1 | pass | OK | {'jobtitle': {'source_delta': "(True, 'Lead Tool Designer')", 'target_delta': "(True, 'Lead Tool Designer')", 'match': True}, 'node': {'source_delta': "(True, '… |
| HUMANRESOURCES.uspUpdateEmployeeLogin | procedure | c2 | pass | OK | {'node': {'source_delta': "(True, '/1/9/')", 'target_delta': "(True, '/1/9/')", 'match': True}, 'level': {'source_delta': '-1.0', 'target_delta': '-1.0', 'match… |
| HUMANRESOURCES.uspUpdateEmployeeLogin | procedure | c3 | pass | OK | {'login': {'source_delta': "(False, 'adventure-works\\\\rob0')", 'target_delta': "(False, 'adventure-works\\\\rob0')", 'match': True}, 'errorlog_rows': {'source… |
| HUMANRESOURCES.uspUpdateEmployeePersonalInfo | procedure | c1 | pass | OK | {'gender': {'source_delta': "(True, 'f')", 'target_delta': "(True, 'f')", 'match': True}, 'maritalstatus': {'source_delta': "(True, 'm')", 'target_delta': "(Tru… |
| HUMANRESOURCES.uspUpdateEmployeePersonalInfo | procedure | c2 | pass | OK | {'gender': {'source_delta': "(False, 'M')", 'target_delta': "(False, 'M')", 'match': True}, 'errorlog_rows': {'source_delta': '1.0', 'target_delta': '1.0', 'mat… |
| HUMANRESOURCES.uspUpdateEmployeePersonalInfo | procedure | c3 | pass | OK | {'maritalstatus': {'source_delta': "(False, 'S')", 'target_delta': "(False, 'S')", 'match': True}, 'errorlog_rows': {'source_delta': '1.0', 'target_delta': '1.0… |
| HUMANRESOURCES.Employee | function | c1 | pass | OK | {'source_rows': 290, 'target_rows': 290, 'source_first': '(1, None, None)', 'target_first': '(1, None, None)'} |
| HUMANRESOURCES.Employee | function | c2 | pass | OK | {'source_rows': 5, 'target_rows': 5, 'source_first': '(None, 1)', 'target_first': '(None, 1)'} |
| HUMANRESOURCES.Department | procedure | c1 | pass | OK | {'defaulted_rows': {'source_delta': '1.0', 'target_delta': '1.0', 'match': True}} |
