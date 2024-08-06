"""all constants of database"""
import os

CURRENT_FILE_PATH = os.path.abspath(__file__)
CURRENT_DIR_PATH = os.path.dirname(CURRENT_FILE_PATH)
ROOT_DIR = os.path.join(CURRENT_DIR_PATH, os.pardir)
# path to sqlite file(it locates in the root dir of this project)
SQLITE_PATH = os.path.join(ROOT_DIR, 'reusable_data.sqlite')