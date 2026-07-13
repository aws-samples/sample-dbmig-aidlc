# Equivalence Test Report — HUMANRESOURCES

Mode: `silent`  |  Cases: 10  Passed: 10  Failed: 0  Skipped: 0

| Object | Type | Case | Status | Detail |
|---|---|---|---|---|
| HumanResources.uspUpdateEmployeeLogin | procedure | c1 | pass | {'employee1_loginid': {'source_delta': "(True, 'test-login')", 'target_delta': "(True, 'test-login')", 'match': True}} |
| HumanResources.uspUpdateEmployeePersonalInfo | procedure | c1 | pass | {'employee1_nationalid': {'source_delta': "(True, '999999999')", 'target_delta': "(True, '999999999')", 'match': True}} |
| HumanResources.vEmployee | function | c1 | pass | {'source': '290', 'target': '290'} |
| HumanResources.vEmployee | function | c2 | pass | {'source': 'Chief Executive Officer', 'target': 'Chief Executive Officer'} |
| HumanResources.vEmployeeDepartment | function | c1 | pass | {'source': '290', 'target': '290'} |
| HumanResources.vEmployeeDepartment | function | c2 | pass | {'source': 'Executive', 'target': 'Executive'} |
| HumanResources.vEmployeeDepartmentHistory | function | c1 | pass | {'source': '296', 'target': '296'} |
| HumanResources.vJobCandidate | function | c1 | pass | {'source': '13', 'target': '13'} |
| HumanResources.vJobCandidateEducation | function | c1 | pass | {'source': '16', 'target': '16'} |
| HumanResources.vJobCandidateEmployment | function | c1 | pass | {'source': '30', 'target': '30'} |
