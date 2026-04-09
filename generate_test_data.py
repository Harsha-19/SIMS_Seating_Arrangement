import pandas as pd

# Creating a messy but valid dataset for testing the parser and seating engine
data = {
    'USN': [
        '101', '102', '103', '104', # BCA
        '201', '202', '203', '204', # BBA
        '301', '302', '303', '304', # BCOM
        'T-01', 'D-01' # Dirty rows (TEST/DUMMY)
    ],
    'Name': [
        'BCA_STU_1', 'BCA_STU_2', 'BCA_STU_3', 'BCA_STU_4',
        'BBA_STU_1', 'BBA_STU_2', 'BBA_STU_3', 'BBA_STU_4',
        'BCOM_STU_1', 'BCOM_STU_2', 'BCOM_STU_3', 'BCOM_STU_4',
        'TEST_USER', 'DUMMY_DATA'
    ],
    'Department': [
        'BCA', 'BCA', 'BCA', 'BCA',
        'BBA', 'BBA', 'BBA', 'BBA',
        'B COM', 'B COM', 'B COM', 'B COM', # Messy B COM
        'BCA', 'BBA'
    ],
    'Semester': [
        'I SEM', 'I SEM', 'I SEM', 'I SEM',
        'I SEM', 'I SEM', 'I SEM', 'I SEM',
        'SEM 1', 'SEM 1', 'SEM 1', 'SEM 1',
        'I SEM', 'I SEM'
    ]
}

df = pd.DataFrame(data)
df.to_excel('test_students.xlsx', index=False)
print("Test dataset 'test_students.xlsx' created successfully.")
