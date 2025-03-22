import os
import pandas as pd
from typing import Tuple, Callable, Any
from dotenv import load_dotenv
from langchain_groq import ChatGroq

# Load environment variables
load_dotenv()

class TextToSQLProcessor:
    def __init__(self, model_name="llama3-70b-8192"):
        """
        Initialize the Text-to-SQL processor with a Groq LLM.
        """
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set")
        
        self.llm = ChatGroq(
            model_name=model_name,
            api_key=api_key
        )
        
        self.sql_prompt_template = """
        You are an expert SQL query generator.
        Given the following database schema information and user question,
        generate a valid SQL query that answers the user's question.
        
        Database Schema Information:
        {context}
        
        User Question: {question}
        
        The SQL query should:
        1. Be compatible with DuckDB syntax
        2. Use double quotes for table and column names
        3. Be optimized and efficient
        4. Directly answer the user's question
        
        IMPORTANT: Return only the raw SQL query without any explanation, markdown formatting, or code block delimiters (like ```).
        """
        
        self.correction_prompt_template = """
        The following SQL query:
        
        {query}
        
        Generated this error:
        
        {error}
        
        Please fix the SQL query to resolve this error. The query should be compatible with DuckDB.
        
        IMPORTANT: Return only the corrected SQL query without any explanation, markdown formatting, or code block delimiters (like ```).
        """

    def generate_sql(self, question: str, context: str) -> str:
        prompt = self.sql_prompt_template.format(context=context, question=question)
        response = self.llm.invoke(prompt)
        return self._clean_sql_response(response.content.strip())

    def correct_sql(self, query: str, error: str) -> str:
        prompt = self.correction_prompt_template.format(query=query, error=error)
        response = self.llm.invoke(prompt)
        return self._clean_sql_response(response.content.strip())

    def _clean_sql_response(self, sql: str) -> str:
        if sql.startswith("```sql"):
            sql = sql[6:]
        elif sql.startswith("```"):
            sql = sql[3:]
        
        if sql.endswith("```"):
            sql = sql[:-3]
            
        return sql.strip()

    def execute_with_correction(self, 
                                sql_query: str, 
                                execute_func: Callable[[str], Tuple[Any, str]], 
                                max_attempts: int = 3) -> Tuple[str, Any, str]:
        current_query = self._clean_sql_response(sql_query)
        
        for attempt in range(max_attempts):
            result, error = execute_func(current_query)
            
            if error is None:
                return current_query, result, None
            
            if attempt < max_attempts - 1:
                current_query = self.correct_sql(current_query, error)
            
        return current_query, None, error

    def generate_insights(self, query_results: pd.DataFrame, original_question: str) -> str:
        """
        Generate insights focusing strictly on the query results.
        """
        try:
            CHUNK_SIZE = 10  # Number of rows per chunk
            total_rows = len(query_results)
            all_insights = []

            for start_idx in range(0, total_rows, CHUNK_SIZE):
                end_idx = min(start_idx + CHUNK_SIZE, total_rows)
                chunk_df = query_results.iloc[start_idx:end_idx]
                
                chunk_str = chunk_df.to_string()
                
                chunk_prompt = f"""
                Analyze these LinkedIn profile results and provide insights.
                
                Original Question: {original_question}
                
                Results (Rows {start_idx + 1} to {end_idx} of {total_rows}):
                {chunk_str}
                
                Please analyze ONLY the data shown above and provide:
                1. Specific details about the profiles shown and Key information relevant to the original question
                
                IMPORTANT: 
                - Only mention information present in these results
                - Be specific about the details shown
                - Focus on answering the original question
                """
                
                response = self.llm.invoke(chunk_prompt)
                all_insights.append(response.content.strip())

            if len(all_insights) > 1:
                final_prompt = f"""
                Combine these insights into a cohesive summary.
                
                Original Question: {original_question}
                Total Profiles Found: {total_rows}
                
                Individual Analyses:
                {'\n\n'.join(all_insights)}
                
                Please provide:
                1. A complete answer to the original question
                2. Key findings across all results
                3. Specific details about the profiles found
                
                IMPORTANT: Present a clear, organized summary focusing only on the actual data found.
                """
                
                final_response = self.llm.invoke(final_prompt)
                return final_response.content.strip()
            else:
                return all_insights[0]

        except Exception as e:
            return f"Error analyzing results: {str(e)}"
