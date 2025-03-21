from langchain_groq import ChatGroq
import os
from typing import Tuple, Callable, Any, Dict, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class TextToSQLProcessor:
    def __init__(self, model_name="llama3-8b-8192"):
        """
        Initialize the Text-to-SQL processor with a Groq LLM.
        
        Args:
            model_name: The name of the open-source model to use via Groq
                       (llama3-8b-8192 or mixtral-8x7b-32768)
        """
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set")
            
        self.llm = ChatGroq(
            model_name=model_name,
            api_key=api_key,
            max_tokens=1024
        )
        
        # SQL generation prompt template
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
        
        Return only the SQL query without any explanation.
        """
        
        # SQL correction prompt template
        self.correction_prompt_template = """
        The following SQL query:
        
        {query}
        
        Generated this error:
        
        {error}
        
        Please fix the SQL query to resolve this error. The query should be compatible with DuckDB.
        Return only the corrected SQL query without any explanation.
        """
    
    def generate_sql(self, question: str, context: str) -> str:
        """
        Generate a SQL query from a natural language question and schema context.
        
        Args:
            question: User's natural language question
            context: Database schema information
            
        Returns:
            str: Generated SQL query
        """
        prompt = self.sql_prompt_template.format(context=context, question=question)
        response = self.llm.invoke(prompt)
        sql_query = response.content.strip()
        
        # Remove triple quotes if present
        if sql_query.startswith("'''") and sql_query.endswith("'''"):
            sql_query = sql_query[3:-3].strip()
        elif sql_query.startswith('```') and sql_query.endswith('```'):
            sql_query = sql_query[3:-3].strip()
            
            # Remove SQL language tag if present
            if sql_query.startswith('sql'):
                sql_query = sql_query[3:].strip()
                
        return sql_query
    
    def correct_sql(self, query: str, error: str) -> str:
        """
        Correct a SQL query based on the error message.
        
        Args:
            query: The SQL query that caused an error
            error: The error message
            
        Returns:
            str: Corrected SQL query
        """
        prompt = self.correction_prompt_template.format(query=query, error=error)
        response = self.llm.invoke(prompt)
        corrected_query = response.content.strip()
        
        # Remove triple quotes if present
        if corrected_query.startswith("'''") and corrected_query.endswith("'''"):
            corrected_query = corrected_query[3:-3].strip()
        elif corrected_query.startswith('```') and corrected_query.endswith('```'):
            corrected_query = corrected_query[3:-3].strip()
            
            # Remove SQL language tag if present
            if corrected_query.startswith('sql'):
                corrected_query = corrected_query[3:].strip()
                
        return corrected_query
    
    def execute_with_correction(self, 
                               sql_query: str, 
                               execute_func: Callable[[str], Tuple[Any, str]], 
                               max_attempts: int = 3) -> Tuple[str, Any, str]:
        """
        Execute a SQL query with automatic error correction.
        
        Args:
            sql_query: Initial SQL query to execute
            execute_func: Function that executes the query and returns (result, error)
            max_attempts: Maximum number of correction attempts
            
        Returns:
            tuple: (final_query, result, error)
        """
        current_query = sql_query
        
        for attempt in range(max_attempts):
            # Execute the query
            result, error = execute_func(current_query)
            
            # If successful, return the result
            if error is None:
                return current_query, result, None
            
            # If failed, try to correct the query
            if attempt < max_attempts - 1:
                current_query = self.correct_sql(current_query, error)
            
        # Return the last query and error if all attempts failed
        return current_query, None, error