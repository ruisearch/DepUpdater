import pandas as pd
import os

csv_path = os.path.join('data', 'total_dataset.csv')
xlsx_path = os.path.join('data', 'total_dataset.xlsx')
df = pd.read_csv(csv_path)
df.to_excel(xlsx_path, index=False, header=True)