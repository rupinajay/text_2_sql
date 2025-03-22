# app.py

import streamlit as st
import pandas as pd
import os
import tempfile
from csv_processor import CSVProcessor
from text_to_sql import TextToSQLProcessor

# Initialize session state
if 'csv_processor' not in st.session_state:
    st.session_state.csv_processor = CSVProcessor()

if 'text_to_sql' not in st.session_state:
    st.session_state.text_to_sql = TextToSQLProcessor()

st.set_page_config(page_title="CSV to SQL Query", layout="wide")

st.title("📊 CSV to SQL with Natural Language")
st.markdown("Upload CSV files and query them using plain English")

# Create tabs for different operations
tab1, tab2, tab3 = st.tabs(["Upload Data", "Query Data", "Schema Browser"])

# Tab 1: Data Upload
with tab1:
    st.header("Upload Your CSV Files")
    
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
    custom_table_name = st.text_input("Custom table name (optional)")
    
    if st.button("Upload and Process"):
        if uploaded_file is not None:
            # Save the uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_filepath = tmp_file.name
            
            # Process the CSV file
            with st.spinner("Processing CSV file..."):
                table_name, metadata = st.session_state.csv_processor.process_csv(
                    tmp_filepath, 
                    custom_table_name if custom_table_name else None
                )
                
                # Remove temporary file
                os.unlink(tmp_filepath)
                
                # Display success message
                st.success(f"Successfully uploaded and created table '{table_name}'")
                
                # Show preview of the data
                st.subheader("Data Preview")
                st.dataframe(pd.DataFrame(metadata["sample_data"]))
                
                # Show schema
                st.subheader("Table Schema")
                schema_text = "\n".join([f"- {col['name']} ({col['type']})" for col in metadata["columns"]])
                st.text(schema_text)
        else:
            st.error("Please upload a CSV file")

# Tab 2: Query Interface
with tab2:
    st.header("Ask Questions About Your Data")
    
    if not st.session_state.csv_processor.tables:
        st.warning("Please upload at least one CSV file in the 'Upload Data' tab first")
    else:
        table_options = list(st.session_state.csv_processor.tables.keys())
        selected_tables = st.multiselect(
            "Select tables to query (leave empty to query all)", 
            options=table_options
        )
        
        user_query = st.text_area("Enter your question in plain English:", height=100)
        
        if st.button("Generate SQL & Execute Query"):
            if user_query:
                with st.spinner("Processing your question..."):
                    if selected_tables:
                        schema_context = "\n".join([
                            st.session_state.csv_processor.get_table_schema_for_llm(table) 
                            for table in selected_tables
                        ])
                    else:
                        schema_context = st.session_state.csv_processor.get_table_schema_for_llm()
                    
                    sql_query = st.session_state.text_to_sql.generate_sql(user_query, schema_context)
                    
                    final_query, result, error = st.session_state.text_to_sql.execute_with_correction(
                        sql_query, 
                        st.session_state.csv_processor.execute_query
                    )
                    
                    st.subheader("Generated SQL")
                    st.code(final_query, language="sql")
                    
                    if error:
                        st.error(f"Error executing query: {error}")
                    else:
                        st.subheader("Query Results")
                        st.dataframe(result)
                        
                        # Generate and display insights with progress
                        with st.spinner("Generating insights from all data..."):
                            # Add a progress bar
                            progress_text = st.empty()
                            progress_bar = st.progress(0)
                            
                            total_batches = (len(result) + 9) // 10  # Calculate total number of batches
                            
                            progress_text.text(f"Processing data in {total_batches} batches...")
                            
                            insights = st.session_state.text_to_sql.generate_insights(result, user_query)
                            
                            progress_bar.empty()
                            progress_text.empty()
                            
                            st.subheader("Response")
                            st.write(insights)
            else:
                st.warning("Please enter a question")

# Tab 3: Schema Browser
with tab3:
    st.header("Database Schema Browser")
    
    if not st.session_state.csv_processor.tables:
        st.warning("No tables available. Please upload data first.")
    else:
        st.subheader("Available Tables")
        
        for table_name, metadata in st.session_state.csv_processor.tables.items():
            with st.expander(f"Table: {table_name} ({metadata['row_count']} rows)"):
                cols_df = pd.DataFrame(metadata["columns"])
                st.dataframe(cols_df)
                
                st.subheader("Sample Data")
                sample_df = pd.DataFrame(metadata["sample_data"])
                st.dataframe(sample_df)

# Sidebar with example questions
with st.sidebar:
    st.header("Example Questions")
    
    if st.session_state.csv_processor.tables:
        examples = []
        
        first_table = list(st.session_state.csv_processor.tables.keys())[0]
        table_data = st.session_state.csv_processor.tables[first_table]
        
        numeric_cols = [col["name"] for col in table_data["columns"] 
                       if col["type"] in ("INTEGER", "DOUBLE")]
        
        if numeric_cols:
            examples.append(f"What is the average {numeric_cols[0]} in {first_table}?")
            if len(numeric_cols) > 1:
                examples.append(f"Show the relationship between {numeric_cols[0]} and {numeric_cols[1]} in {first_table}")
        
        examples.append(f"Show me all columns from {first_table} sorted by {table_data['columns'][0]['name']}")
        examples.append(f"What are the top 5 rows in {first_table}?")
        
        for example in examples:
            if st.button(example):
                st.session_state.user_query = example
                st.experimental_rerun()
    else:
        st.info("Upload data to see example questions")
