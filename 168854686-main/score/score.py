import pandas as pd

# Load the Excel file
file_path = 'CCA_organized.xlsx'

# Specify the decimal separator to handle commas
df = pd.read_excel(file_path, sheet_name='Sheet1', decimal=',')

# Display the first few rows to understand the structure of the DataFrame
print(df.head())

# Sort the DataFrame by the 'Score' column in descending order
df_sorted = df.sort_values(by='Score', ascending=False)

# Add a new column for the rank
df_sorted['Rank'] = df_sorted['Score'].rank(ascending=False, method='min')

# Find the rank of the person with a score of 15.46
target_score = 15.46
target_rank = df_sorted[df_sorted['Score'] == target_score]['Rank'].iloc[0]

print(f'The rank of the person with a score of {target_score} is {target_rank}.')
