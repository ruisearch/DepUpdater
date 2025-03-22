"""all operations on the sqlite db which stores the reusable data"""
import sqlite3

from database.constants import SQLITE_PATH


class Sqlite:
    def __init__(self, sqlite_path):
        """set path to sqlite file"""
        self.sqlite_path = sqlite_path
        self.conn = None
        self.cursor = None

    def connect(self):
        """connect the sqlite db"""
        self.conn = sqlite3.connect(self.sqlite_path)
        self.cursor = self.conn.cursor()

    def close(self):
        """close the connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

    def create_table(self, table_name, columns):
        """create a table"""
        try:
            # column definition
            columns_str = ', '.join([f"{col_name} {col_type}" for col_name, col_type in columns.items()])
            create_table_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_str})"
            self.cursor.execute(create_table_sql)
            self.conn.commit()
        except sqlite3.Error as e:
            print(e)

    def insert_data(self, table_name, data):
        """insert one line if not exists"""
        try:
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data]) # ？is placeholder of SQL
            # if the line already exists, then ignore
            insert_sql = f"INSERT OR IGNORE INTO {table_name} ({columns}) VALUES ({placeholders})"
            self.cursor.execute(insert_sql, list(data.values()))
            self.conn.commit()
        except sqlite3.Error as e:
            print(e)

    def query_data(self, table_name, columns='*', conditions=None):
        """a query returns columns of the lines comply with conditions
        
        Args:
            table_name : name of the table
            conditions : filter the line in need
            columns : the columns to be displayed
        """
        try:
            query_sql = f"SELECT {columns} FROM {table_name}"
            if conditions:
                condition_strs = []
                condition_values = []
                for condition in conditions:
                    if isinstance(condition, str):
                        condition_strs.append(condition)
                    else:
                        col, op, val = condition
                        condition_strs.append(f"{col} {op} ?")# ？is placeholder in SQL
                        condition_values.append(val)
                query_sql += f" WHERE {' '.join(condition_strs)}"
                self.cursor.execute(query_sql, condition_values)
            else:
                self.cursor.execute(query_sql)
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(e)
            return []

    def update_data(self, table_name:str, updates:dict, conditions):
        """change/update lines comply with conditions
        Args:
            table_name : name of the table
            updates (dict): the columns to be updated
            {
                'col1': val1,
                ...
            }
            conditions : filter the line in need
        """
        try:
            updates_str = ', '.join([f"{col}=?" for col in updates.keys()])
            condition_strs = []
            condition_values = []
            for condition in conditions:
                if isinstance(condition, str):
                    # an AND or OR concatenation between conditions
                    condition_strs.append(condition)
                else:
                    # a tuple representing a condition
                    col, op, val = condition
                    condition_strs.append(f"{col} {op} ?")
                    condition_values.append(val)
            conditions_str = ' '.join(condition_strs)
            update_sql = f"UPDATE {table_name} SET {updates_str} WHERE {conditions_str}"
            self.cursor.execute(update_sql, list(updates.values()) + condition_values)
            self.conn.commit()
        except sqlite3.Error as e:
            print(e)

    def delete_data(self, table_name, conditions):
        """delete some lines comply with the conditions"""
        try:
            condition_strs = []
            condition_values = []
            for condition in conditions:
                if isinstance(condition, str):
                    condition_strs.append(condition)
                else:
                    col, op, val = condition
                    condition_strs.append(f"{col} {op} ?")
                    condition_values.append(val)
            conditions_str = ' '.join(condition_strs)
            delete_sql = f"DELETE FROM {table_name} WHERE {conditions_str}"
            self.cursor.execute(delete_sql, condition_values)
            self.conn.commit()
        except sqlite3.Error as e:
            print(e)

    def drop_table(self, table_name:str):
        """drop a table"""
        drop_table_sql = f'DROP TABLE IF EXISTS {table_name}'
        try:
            self.cursor.execute(drop_table_sql)
            self.conn.commit()
            print(f'table {table_name} has been deleted')
        except sqlite3.Error as e:
            print(f"An error occurred: {e}")

    def create_index(self, table_name:str, index_name:list, columns):
        """
        create index for table
        
        Args:
            table_name : name of the table
            index_name : name of the created index
            columns : columns in the index
        """
        # if columns is a str, convert it into a list
        if isinstance(columns, str):
            columns = [columns]

        # represents the columns
        columns_str = ', '.join(columns)

        # sql
        create_index_sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({columns_str})"

        try:
            self.cursor.execute(create_index_sql)
            self.conn.commit()
            print(f"Index '{index_name}' created successfully on table '{table_name}' for columns: {columns_str}")
        except sqlite3.Error as e:
            print(f"An error occurred: {e}")
