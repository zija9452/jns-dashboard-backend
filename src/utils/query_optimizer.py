"""
Database query optimization utilities for the Regal POS Backend
Provides tools for query profiling, N+1 prevention, and performance optimization
"""
import asyncio
import time
import logging
from typing import List, Dict, Any, Optional, Callable, Awaitable
from functools import wraps
from contextlib import contextmanager
from sqlmodel import select, Session
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from ..database.database import engine
import os


class QueryProfiler:
    """
    Query profiler to identify slow queries and performance bottlenecks
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.queries = []  # Store query history for analysis
        self.slow_query_threshold = float(os.getenv("SLOW_QUERY_THRESHOLD", "0.5"))  # 500ms default
        self.enabled = os.getenv("QUERY_PROFILING_ENABLED", "false").lower() == "true"

    def log_query(self, query_text: str, execution_time: float, params: Dict[str, Any] = None):
        """
        Log query execution details
        """
        query_info = {
            "query": query_text,
            "execution_time": execution_time,
            "params": params,
            "timestamp": time.time(),
            "is_slow": execution_time > self.slow_query_threshold
        }

        self.queries.append(query_info)

        if execution_time > self.slow_query_threshold:
            self.logger.warning(
                f"SLOW QUERY DETECTED ({execution_time:.3f}s): {query_text[:100]}... "
                f"Params: {str(params)[:100]}"
            )
        elif self.enabled:
            self.logger.debug(f"Query executed in {execution_time:.3f}s: {query_text[:100]}...")

    def get_slow_queries(self, threshold: float = None) -> List[Dict[str, Any]]:
        """
        Get queries that exceed the slow query threshold
        """
        threshold = threshold or self.slow_query_threshold
        return [q for q in self.queries if q["execution_time"] > threshold]

    def get_query_stats(self) -> Dict[str, Any]:
        """
        Get statistics about query performance
        """
        if not self.queries:
            return {"total_queries": 0}

        execution_times = [q["execution_time"] for q in self.queries]
        slow_queries = [q for q in self.queries if q["is_slow"]]

        return {
            "total_queries": len(self.queries),
            "avg_execution_time": sum(execution_times) / len(execution_times),
            "max_execution_time": max(execution_times),
            "slow_query_count": len(slow_queries),
            "slow_query_percentage": (len(slow_queries) / len(self.queries)) * 100
        }


class NPlusOneDetector:
    """
    N+1 query detector to identify inefficient data access patterns
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.query_counts = {}  # Track query counts per endpoint/context
        self.n_plus_one_patterns = []  # Store detected N+1 patterns

    def detect_n_plus_one(self, query_count: int, expected_count: int = 1) -> bool:
        """
        Detect potential N+1 query pattern
        """
        if query_count > expected_count * 2:  # Allow some tolerance
            return True
        return False

    def analyze_query_pattern(self, context: str, queries: List[str]):
        """
        Analyze a series of queries for N+1 patterns
        """
        if len(queries) > 10:  # Threshold for potential N+1
            # Check for repetitive patterns
            query_templates = [self._normalize_query(q) for q in queries]
            unique_templates = set(query_templates)

            # If we have many queries but few unique templates, it might be N+1
            if len(queries) / len(unique_templates) > 5:  # Heuristic: more than 5x more queries than templates
                self.n_plus_one_patterns.append({
                    "context": context,
                    "total_queries": len(queries),
                    "unique_templates": len(unique_templates),
                    "pattern": "Potential N+1: Many similar queries"
                })
                self.logger.warning(f"N+1 pattern detected in {context}: {len(queries)} queries, {len(unique_templates)} unique patterns")

    def _normalize_query(self, query: str) -> str:
        """
        Normalize query for comparison (remove values, standardize)
        """
        # Remove numeric values and string literals for pattern matching
        import re
        normalized = re.sub(r'\d+', '?', query)  # Replace numbers with ?
        normalized = re.sub(r"'[^']*'", '?', normalized)  # Replace string literals with ?
        return normalized.strip()


class QueryOptimizer:
    """
    Query optimization utilities
    """

    def __init__(self):
        self.profiler = QueryProfiler()
        self.n_plus_one_detector = NPlusOneDetector()
        self.logger = logging.getLogger(__name__)

    def optimize_with_joins(self, base_model, relationships: List[str]):
        """
        Apply join optimization to prevent N+1 queries
        """
        query = select(base_model)

        for rel in relationships:
            query = query.options(joinedload(getattr(base_model, rel)))

        return query

    def optimize_with_selectin(self, base_model, relationships: List[str]):
        """
        Apply selectin optimization for collections to prevent N+1
        """
        query = select(base_model)

        for rel in relationships:
            query = query.options(selectinload(getattr(base_model, rel)))

        return query

    def add_query_profiling(self, func: Callable) -> Callable:
        """
        Decorator to add query profiling to database functions
        """
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not self.profiler.enabled:
                return await func(*args, **kwargs)

            start_time = time.time()
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time

            # Log the function call as a "query" for profiling purposes
            self.profiler.log_query(
                f"Function: {func.__name__}",
                execution_time,
                {"args": str(args)[:100], "kwargs": str(kwargs)[:100]}
            )

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not self.profiler.enabled:
                return func(*args, **kwargs)

            start_time = time.time()
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time

            # Log the function call as a "query" for profiling purposes
            self.profiler.log_query(
                f"Function: {func.__name__}",
                execution_time,
                {"args": str(args)[:100], "kwargs": str(kwargs)[:100]}
            )

            return result

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    async def analyze_database_performance(self, db: Session) -> Dict[str, Any]:
        """
        Analyze database performance and identify optimization opportunities
        """
        analysis_results = {
            "indexes": [],
            "slow_queries": self.profiler.get_slow_queries(),
            "n_plus_one_issues": self.n_plus_one_detector.n_plus_one_patterns,
            "recommendations": []
        }

        # Check for missing indexes (basic check)
        try:
            # This is a simplified check - in real applications you'd want more sophisticated analysis
            result = db.exec(text("""
                SELECT schemaname, tablename, indexname, indexdef
                FROM pg_indexes
                WHERE schemaname = 'public'
            """)).all()

            analysis_results["indexes"] = [dict(row) for row in result]
        except Exception as e:
            self.logger.warning(f"Could not analyze database indexes: {e}")

        # Add recommendations based on analysis
        if analysis_results["slow_queries"]:
            analysis_results["recommendations"].append("Review slow queries and consider adding indexes or optimizing queries")

        if analysis_results["n_plus_one_issues"]:
            analysis_results["recommendations"].append("Address N+1 query issues by using joinedload or selectinload")

        if len(analysis_results["indexes"]) < 5:  # Arbitrary threshold
            analysis_results["recommendations"].append("Consider adding more database indexes for frequently queried columns")

        return analysis_results

    def suggest_optimizations(self, table_name: str, columns: List[str]) -> List[str]:
        """
        Suggest optimizations for a specific table
        """
        suggestions = []

        # Suggest indexes for commonly filtered columns
        common_filter_columns = ['user_id', 'created_at', 'updated_at', 'status', 'type', 'category']
        filtered_cols = [col for col in columns if col in common_filter_columns]

        for col in filtered_cols:
            suggestions.append(f"CREATE INDEX idx_{table_name}_{col} ON {table_name}({col});")

        # Suggest composite indexes for common combinations
        if 'user_id' in columns and 'created_at' in columns:
            suggestions.append(f"CREATE INDEX idx_{table_name}_user_created ON {table_name}(user_id, created_at);")

        if 'status' in columns and 'created_at' in columns:
            suggestions.append(f"CREATE INDEX idx_{table_name}_status_created ON {table_name}(status, created_at);")

        return suggestions


# Global optimizer instance
query_optimizer = QueryOptimizer()


def with_optimized_joins(*relationships):
    """
    Decorator to apply join optimization to prevent N+1 queries
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Apply join optimization - this is a conceptual decorator
            # In practice, you'd modify the query inside the function
            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Apply join optimization
            return func(*args, **kwargs)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def profile_query(func: Callable) -> Callable:
    """
    Decorator to profile individual query functions
    """
    return query_optimizer.add_query_profiling(func)


def batch_fetch(items: List[Any], batch_size: int = 100) -> List[List[Any]]:
    """
    Helper function to batch fetch items to prevent memory issues
    """
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]


def optimize_pagination(skip: int, limit: int, max_limit: int = 1000) -> tuple:
    """
    Optimize pagination parameters to prevent performance issues
    """
    # Limit the maximum number of items that can be fetched at once
    if limit > max_limit:
        limit = max_limit

    # Ensure skip and limit are reasonable
    if skip < 0:
        skip = 0
    if limit <= 0:
        limit = 20  # default

    return skip, limit


# Example usage and best practices
class QueryOptimizationExamples:
    """
    Examples of query optimization patterns
    """

    @staticmethod
    @profile_query
    async def get_users_with_roles_optimized(db: AsyncSession):
        """
        Example: Optimized query to get users with roles (prevents N+1)
        """
        from ..models.user import User
        from sqlalchemy.future import select

        # Use joinedload to fetch users and roles in a single query
        query = select(User).options(joinedload(User.role))
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    @profile_query
    async def get_products_with_categories_optimized(db: AsyncSession):
        """
        Example: Optimized query to get products with categories (prevents N+1)
        """
        from ..models.product import Product
        from sqlalchemy.future import select

        # Use joinedload for single relationships, selectinload for collections
        query = select(Product).options(
            joinedload(Product.category),
            joinedload(Product.brand),
            selectinload(Product.stock_entries)
        )
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def paginated_query_example(db: Session, page: int = 1, page_size: int = 50):
        """
        Example: Properly optimized paginated query
        """
        from ..models.product import Product

        # Optimize pagination parameters
        skip, limit = optimize_pagination((page - 1) * page_size, page_size)

        # Use offset and limit for pagination
        query = select(Product).offset(skip).limit(limit)

        with query_optimizer.profiler:
            start_time = time.time()
            result = db.exec(query).all()
            execution_time = time.time() - start_time

            query_optimizer.profiler.log_query(
                "SELECT products with pagination",
                execution_time,
                {"skip": skip, "limit": limit}
            )

        return result


# Initialize the query optimizer
def init_query_optimizer():
    """
    Initialize query optimization utilities
    """
    if query_optimizer.profiler.enabled:
        logging.getLogger(__name__).info("Query profiling enabled")

    # Set up any necessary database configurations for optimization
    pass


# Initialize when module is imported
init_query_optimizer()


if __name__ == "__main__":
    # Example usage
    print("Query optimization utilities ready")
    print(f"Slow query threshold: {query_optimizer.profiler.slow_query_threshold}s")
    print(f"Profiling enabled: {query_optimizer.profiler.enabled}")