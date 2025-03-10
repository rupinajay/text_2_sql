import pandas as pd
import duckdb
import os
import uuid
import time
from typing import Dict, List, Tuple
import re

class CSVProcessor:
    def __init__(self, db_path: str = "data/user_data.duckdb"):
        """Initialize the CSV processor with a DuckDB database path."""
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Generate a unique path for this session to avoid lock conflicts
        unique_id = str(uuid.uuid4())[:8]
        base_dir = os.path.dirname(db_path)
        base_name = os.path.basename(db_path)
        self.db_path = os.path.join(base_dir, f"{os.path.splitext(base_name)[0]}_{unique_id}.duckdb")
        
        # Try to connect with retries
        max_retries = 3
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                self.conn = duckdb.connect(self.db_path)
                break
            except duckdb.IOException as e:
                if attempt < max_retries - 1:
                    print(f"Database connection attempt {attempt+1} failed: {e}. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    raise Exception(f"Failed to connect to database after {max_retries} attempts: {e}")
        
        self.tables = {}  # Store table metadata
        
        # Load existing tables from database
        self._load_existing_tables()
        
    def _load_existing_tables(self):
        """Load metadata for existing tables in the database."""
        try:
            # Get list of tables
            tables_df = self.conn.execute("SHOW TABLES").fetchdf()
            
            if not tables_df.empty:
                for table_name in tables_df['name']:
                    # Get column information
                    columns_df = self.conn.execute(f"PRAGMA table_info('{table_name}')").fetchdf()
                    
                    # Get row count
                    row_count = self.conn.execute(f"SELECT COUNT(*) FROM '{table_name}'").fetchone()[0]
                    
                    # Get sample data
                    sample_data = self.conn.execute(f"SELECT * FROM '{table_name}' LIMIT 5").fetchdf().to_dict(orient="records")
                    
                    # Store metadata
                    columns = [{"name": row['name'], "type": row['type']} for _, row in columns_df.iterrows()]
                    
                    self.tables[table_name] = {
                        "name": table_name,
                        "columns": columns,
                        "row_count": row_count,
                        "sample_data": sample_data
                    }
        except Exception as e:
            print(f"Error loading existing tables: {e}")
        
    def clean_column_name(self, name: str) -> str:
        """Clean column names to be SQL-friendly."""
        # Replace spaces and special characters with underscores
        clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        # Ensure name starts with a letter
        if not clean_name[0].isalpha():
            clean_name = 'col_' + clean_name
        return clean_name.lower()
    
    def infer_column_types(self, df: pd.DataFrame) -> Dict[str, str]:
        """Infer SQL data types from pandas DataFrame."""
        type_map = {}
        for col in df.columns:
            if pd.api.types.is_integer_dtype(df[col]):
                type_map[col] = 'INTEGER'
            elif pd.api.types.is_float_dtype(df[col]):
                type_map[col] = 'DOUBLE'
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                type_map[col] = 'TIMESTAMP'
            elif pd.api.types.is_bool_dtype(df[col]):
                type_map[col] = 'BOOLEAN'
            else:
                type_map[col] = 'VARCHAR'
        return type_map
    
    def process_csv(self, file_path: str, table_name: str = None) -> Tuple[str, Dict]:
        """
        Process a CSV file, infer schema, create table, and return metadata.
        
        Args:
            file_path: Path to the CSV file
            table_name: Optional custom table name (defaults to filename)
            
        Returns:
            tuple: (table_name, table_metadata)
        """
        # Read CSV file
        df = pd.read_csv(file_path)
        
        # Clean column names
        original_columns = df.columns.tolist()
        cleaned_columns = [self.clean_column_name(col) for col in original_columns]
        df.columns = cleaned_columns
        
        # Infer data types
        column_types = self.infer_column_types(df)
        
        # Generate table name if not provided
        if table_name is None:
            base_name = os.path.basename(file_path)
            table_name = self.clean_column_name(os.path.splitext(base_name)[0])
        else:
            table_name = self.clean_column_name(table_name)
        
        # Check if table already exists and append number if needed
        base_table_name = table_name
        counter = 1
        while table_name in self.tables:
            table_name = f"{base_table_name}_{counter}"
            counter += 1
        
        # Create table in DuckDB
        columns_sql = ", ".join([f'"{col}" {dtype}' for col, dtype in column_types.items()])
        create_table_sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" ({columns_sql})'
        self.conn.execute(create_table_sql)
        
        # Insert data
        self.conn.execute(f'INSERT INTO "{table_name}" SELECT * FROM df')
        
        # Store metadata
        table_metadata = {
            "name": table_name,
            "columns": [{"name": col, "type": dtype} for col, dtype in column_types.items()],
            "original_columns": dict(zip(cleaned_columns, original_columns)),
            "row_count": len(df),
            "sample_data": df.head(5).to_dict(orient="records")
        }
        
        self.tables[table_name] = table_metadata
        
        return table_name, table_metadata
    
    def get_table_schema_for_llm(self, table_name: str = None) -> str:
        """
        Generate a schema description suitable for the LLM context.
        
        Args:
            table_name: If provided, return schema for specific table, 
                       otherwise return all tables
        
        Returns:
            str: Schema description in text format
        """
        if table_name and table_name in self.tables:
            tables = {table_name: self.tables[table_name]}
        else:
            tables = self.tables
            
        schema_text = []
        
        for name, metadata in tables.items():
            columns_desc = "\n".join([
                f"- {col['name']} ({col['type']})" 
                for col in metadata["columns"]
            ])
            
            schema_text.append(f"Table: {name}\nColumns:\n{columns_desc}\n")
            
            # Add sample data
            sample_rows = metadata.get("sample_data", [])
            if sample_rows:
                sample_text = "Sample data (first few rows):\n"
                for i, row in enumerate(sample_rows[:3]):
                    sample_text += f"Row {i+1}: " + ", ".join([f"{k}={v}" for k, v in row.items()]) + "\n"
                schema_text.append(sample_text)
                
        return "\n".join(schema_text)
    
    def execute_query(self, sql_query: str) -> Tuple[pd.DataFrame, str]:
        """
        Execute SQL query against the database.
        
        Returns:
            tuple: (result_dataframe, error_message)
        """
        try:
            result = self.conn.execute(sql_query).fetchdf()
            return result, None
        except Exception as e:
            return None, str(e)