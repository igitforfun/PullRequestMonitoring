import sqlite3
from logging_config import logger

class sql_command:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()

    def create_table(self, table_command):
        """
        Create a table in the database.

        Args:
            table_command (str): SQL command to create the table.
        """
        self.cursor.execute(table_command)
    
    def create_dictionary_from_table(self, table_name):
        """
        Create a dictionary from the specified table.

        Args:
            table_name (str): Name of the table to create a dictionary from.

        Returns:
            dict: Dictionary with column names as keys and data as values.
        """
        self.cursor.execute(f"PRAGMA table_info({table_name})")
        columns = self.cursor.fetchall()
        dict = {col[1]: 'None' for col in columns}
        return dict

    def insert_dictionary_to_table(self, dict, table_name):
        """
        Insert a new record into the specified table.

        Args:
            dict (dict): Dictionary containing column names as keys and data as values.
            table_name (str): Name of the table to insert data into.
        """
        try:
            columns = ', '.join(dict.keys())
            values = tuple(dict.values())
            sql = f"INSERT INTO {table_name} ({columns}) VALUES {values}"
            self.cursor.execute(sql)
            self.conn.commit()
        except Exception as e:
            logger.error(f"{e}: when execute {sql}")

    def execute_update_command(self, dict, table_name, primary_key):
        """
        Update an existing record in the specified table.

        Args:
            dict (dict): Dictionary containing column names as keys and data as values.
            table_name (str): Name of the table to update data in.
        """
        try:
            set_clause = ', '.join([f"{key} = ?" for key in dict.keys() if key != primary_key])
            values = tuple([value for key, value in dict.items() if key != primary_key])
            values += (dict[primary_key],)
            sql = f'''UPDATE {table_name} SET {set_clause} WHERE {primary_key} = ?'''
            self.cursor.execute(sql, values)
            self.conn.commit()
        except Exception as e:
            logger.error(f"{e}: when execute")

    def execute_query(self, query):
        """
        Execute a query on the database.

        Args:
            query (str): SQL query to execute
        """
        self.cursor.execute(query)
        self.conn.commit()


    def add_new_column(self, table_name, column_name, column_type):
        """
        Add a new column to the specified table.

        Args:
            table_name (str): Name of the table to add the column to.
            column_name (str): Name of the column to add.
            column_type (str): Data type of the column.
        """
        self.cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
        self.conn.commit()

    def execute_query_fetchall(self, query):
        """
        Execute a query on the database and fetch all the results.

        Args:
            query (str): SQL query to execute.

        Returns:
            list: List of tuples containing the results.
        """
        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        return rows
    
    def execute_query_fetchone(self, query):
        """
        Execute a query on the database and fetch one result.

        Args:
            query (str): SQL query to execute
        """
        self.cursor.execute(query)
        rows = self.cursor.fetchone()
        return rows
    
    def verify_database(self, table_name):
        """
        Verify the data in the specified table by fetching and printing the rows.

        Args:
            table_name (str): Name of the table to verify.
        """
        self.cursor.execute(f"SELECT * FROM {table_name}")
        rows = self.cursor.fetchall()
        for row in rows:
            print(row)

    def get_max_build_number(self, table_name, column_name, column_variant, variant):
        """
        Get the maximum build number for a specific variant from the specified table.

        Args:
            table_name (str): Name of the table to query.
            column_name (str): Name of the column to get the maximum value from.
            column_variant (str): Name of the column to filter by variant.
            variant (str): The variant value to filter the results.

        Returns:
            int: Maximum build number for the specified variant, or None if no rows are found.
        """
        self.cursor.execute(f"SELECT {column_name} FROM {table_name} WHERE {column_variant} = ? ORDER BY {column_name} DESC", [variant])
        rows = self.cursor.fetchone()
        if rows is None:
            return None
        return rows[0]
    
    def get_number_of_entries(self, table_name):
        self.cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        row = self.cursor.fetchone()
        return row[0]
    
    def close_database(self):
        """
        Close the SQLite database connection.
        """
        self.conn.close()
