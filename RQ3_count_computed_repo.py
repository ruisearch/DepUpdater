"""读取rq3_module_api_count.csv文件，统计目前计算出来的repo数量"""
import pandas as pd
import os

df = pd.read_csv(os.path.join("data", "rq3_module_api_count.csv"))
# df = pd.read_csv(os.path.join("data", "rq3_processed.csv"))

part_df = df.iloc[:, :1]

count = part_df.drop_duplicates().shape[0]

print("repo count:", count)
