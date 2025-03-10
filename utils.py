import os
import re
import pandas as pd

def ensure_directories_exist():
    """Ensure that all required directories exist."""
    os.makedirs("data", exist_ok=True)
    os.makedirs("uploads", exist_ok=True)

def clean_filename(filename):
    """Clean a filename to be safe for use."""
    # Replace spaces and special characters with underscores
    clean_name = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', filename)
    return clean_name

def get_file_extension(filename):
    """Get the file extension from a filename."""
    return os.path.splitext(filename)[1].lower()

def format_sql_for_display(sql):
    """Format SQL query for better display."""
    # Replace keywords with uppercase
    keywords = [
        "SELECT", "FROM", "WHERE", "GROUP BY", "ORDER BY", "HAVING",
        "JOIN", "LEFT JOIN", "RIGHT JOIN", "INNER JOIN", "OUTER JOIN",
        "ON", "AND", "OR", "AS", "IN", "LIKE", "NOT", "NULL",
        "COUNT", "SUM", "AVG", "MIN", "MAX", "DISTINCT"
    ]
    
    formatted_sql = sql
    for keyword in keywords:
        pattern = r'\b' + keyword + r'\b'
        formatted_sql = re.sub(pattern, keyword, formatted_sql, flags=re.IGNORECASE)
    
    return formatted_sql

def simple_sql_validator(query):
    """
    Simple SQL validator to catch basic syntax errors.
    Returns (is_valid, error_message)
    """
    # Check for basic SQL injection patterns
    dangerous_patterns = [
        r';\s*DROP\s+TABLE',
        r';\s*DELETE\s+FROM',
        r';\s*TRUNCATE\s+TABLE',
        r';\s*ALTER\s+TABLE',
        r';\s*UPDATE\s+.*SET',
        r'EXEC\s+xp_cmdshell',
        r'--\s*$'
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            return False, "Query contains potentially harmful operations"
    
    # Check for basic SQL syntax elements
    required_elements = {
        'SELECT': r'\bSELECT\b',
        'FROM': r'\bFROM\b'
    }
    
    for element, pattern in required_elements.items():
        if not re.search(pattern, query, re.IGNORECASE):
            return False, f"Query missing required {element} statement"
    
    return True, None