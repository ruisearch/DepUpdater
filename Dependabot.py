"""evaluate the performance of Dependabot
this script should be executed after Dataset.py
"""
import pandas as pd
import subprocess
import os
import logging
from tqdm import tqdm
from constants import DATA_DIR, TREE_DIR, RET_DIR

def main():
    """main function"""
    log_path = os.path.join(DATA_DIR, 'dependabot_log.txt')
    # clear log
    if os.path.exists(log_path):
        os.remove(log_path)
    # set log
    logging.basicConfig(filename=log_path,level=logging.INFO,format='%(asctime)s - %(message)s')

    csv_path = os.path.join(DATA_DIR, 'dependabot_dataset.csv')
    # 