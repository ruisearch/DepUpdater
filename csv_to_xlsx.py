"""
    This script converts total_dataset.csv to total_dataset.xlsx
    execute this script after running inner_join_two_csv.py
"""
import pandas as pd
import os

csv_path = os.path.join('data', 'total_dataset.csv')
xlsx_path = os.path.join('data', 'total_dataset.xlsx')
df = pd.read_csv(csv_path)
df.to_excel(xlsx_path, index=False, header=True)