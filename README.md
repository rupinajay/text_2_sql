# CSV to SQL Query with Natural Language

A Streamlit application that transforms CSV data exploration through natural language processing. This project enables users to interact with their CSV files using plain English queries, which are automatically converted into SQL queries.

## 🌟 Project Overview

This codebase consists of three main components that work together to provide a seamless data querying experience:

### 1. Main Application (app.py)
The core interface built with Streamlit that provides:
- CSV file upload functionality
- Natural language query interface
- Interactive schema browser
- Real-time query results display
- Data insights generation

### 2. CSV Processor (csv_processor.py)
Handles all data management operations:
- CSV file processing and validation
- Automatic schema detection and type inference
- DuckDB database management
- Table metadata management
- SQL query execution

### 3. Text to SQL Processor (text_to_sql.py)
Manages the natural language processing capabilities:
- Converts English questions to SQL queries using Groq LLM
- Provides automatic SQL query error correction
- Generates insights from query results
- Handles multi-table query context

## 🛠️ Technical Implementation

The project leverages:
- **DuckDB**: For efficient in-process SQL analytics
- **Groq LLM**: For natural language understanding and SQL generation
- **Pandas**: For data manipulation and processing
- **Streamlit**: For the web interface

## 🔑 Key Features

- Natural language to SQL conversion
- Automatic schema inference
- Multi-table query support
- Query error correction
- Intelligent data insights
- Interactive data preview
- Schema visualization
- Example query suggestions

## 📊 Data Processing Flow

1. CSV files are uploaded and processed
2. Schema and metadata are automatically extracted
3. Data is stored in DuckDB for querying
4. Natural language queries are converted to SQL
5. Queries are executed and results are displayed
6. AI-powered insights are generated from results

This project simplifies data exploration by removing the need for SQL knowledge, making data analysis accessible to non-technical users while maintaining the power and flexibility of SQL queries.
