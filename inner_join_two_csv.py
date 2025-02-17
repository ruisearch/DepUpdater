"""
    inner join dataset.csv which is the result of our tool and dependabot_dataset.csv which is the result of dependabot
    and save the result into total_dataset.csv
    execute this script after running Dataset.py and dependabot_dataset.py
"""

from constants import DATA_DIR
import pandas as pd
import os

# read two csv
tool_df = pd.read_csv(os.path.join(DATA_DIR, 'dataset.csv'), dtype={
    'repo':'object',
    'module':'object',
    'dependabot_compile_success':'object',
    'dependabot_test_pass':'object',
    'original_tech_lag':'object',
    'dependabot_current_tech_lag':'object',
    'dependabot_reduced_tech_lag':'object',
    'original_dep_count':'object',
    'dependabot_current_dep_count':'object',
    'dependabot_reduced_dep_count':'object'
})
dependabot_df = pd.read_csv(os.path.join(DATA_DIR, 'dependabot_dataset.csv'), dtype={
    'repo':'object',
    'module':'object',
    'dependabot_compile_success':'object',
    'dependabot_test_pass':'object',
    'original_tech_lag':'object',
    'dependabot_current_tech_lag':'object',
    'dependabot_reduced_tech_lag':'object',
    'original_dep_count':'object',
    'dependabot_current_dep_count':'object',
    'dependabot_reduced_dep_count':'object'
})

# inner join two csv
total_df = pd.merge(tool_df, dependabot_df, on=['repo','module','original_tech_lag','original_dep_count']\
    ,how='inner')
# change the order of columns
total_df = total_df[['repo','module','original_tech_lag','original_dep_count',\
    'current_tech_lag','dependabot_current_tech_lag','current_dep_count','dependabot_current_dep_count',\
        'compile_success','dependabot_compile_success','test_pass','dependabot_test_pass',\
            'reduced_dep_count','dependabot_reduced_dep_count','reduced_tech_lag','dependabot_reduced_tech_lag']]
total_csv_path = os.path.join(DATA_DIR, 'total_dataset.csv')
total_df.to_csv(total_csv_path, index=False, header=True, mode='w')