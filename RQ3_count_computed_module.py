"""读取rq3_module_api_count.csv文件，统计目前计算出来的module数量"""
import pandas as pd
import os

df = pd.read_csv(os.path.join("data", "rq3_module_api_count.csv"))

part_df = df.iloc[:, :2]

count = part_df.drop_duplicates().shape[0]

print("module count:", count)
