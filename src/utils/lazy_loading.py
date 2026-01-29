"""
Lazy loading utilities for the Regal POS Backend
Implements lazy loading patterns for large datasets to optimize performance
"""
import asyncio
from typing import TypeVar, Generic, List, Optional, AsyncGenerator, Iterator, Callable, Any
from sqlmodel import Session, select
from sqlalchemy import func
from contextlib import asynccontextmanager
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import math


T = TypeVar('T')


class LoadStrategy(Enum):
    EAGER = "eager"
    LAZY = "lazy"
    PAGINATED = "paginated"
    STREAMING = "streaming"


@dataclass
class PaginationInfo:
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool


class DataLoader(ABC, Generic[T]):
    """
    Abstract base class for data loaders with different loading strategies
    """

    @abstractmethod
    async def load_item(self, item_id: Any) -> Optional[T]:
        """
        Load a single item by ID
        """
        pass

    @abstractmethod
    async def load_batch(self, item_ids: List[Any]) -> List[T]:
        """
        Load a batch of items by their IDs
        """
        pass

    @abstractmethod
    async def load_all(self) -> List[T]:
        """
        Load all items (should be used carefully for large datasets)
        """
        pass

    @abstractmethod
    async def load_paginated(self, page: int = 1, page_size: int = 50) -> tuple[List[T], PaginationInfo]:
        """
        Load items with pagination
        """
        pass


class LazyLoader(Generic[T]):
    """
    Lazy loader that defers loading until actually accessed
    """

    def __init__(self, loader_func: Callable[[], T]):
        self.loader_func = loader_func
        self._loaded = False
        self._value = None
        self.logger = logging.getLogger(__name__)

    def __await__(self):
        return self.load().__await__()

    async def load(self) -> T:
        """
        Load the value if not already loaded
        """
        if not self._loaded:
            self.logger.debug("Loading lazy value...")
            if asyncio.iscoroutinefunction(self.loader_func):
                self._value = await self.loader_func()
            else:
                self._value = self.loader_func()
            self._loaded = True
        return self._value

    def is_loaded(self) -> bool:
        """
        Check if the value has been loaded
        """
        return self._loaded

    def reset(self):
        """
        Reset the loader to unloaded state
        """
        self._loaded = False
        self._value = None


class StreamingLoader(Generic[T]):
    """
    Streaming loader for large datasets that yields items one by one
    """

    def __init__(self, query_func: Callable[[int, int], List[T]], batch_size: int = 100):
        self.query_func = query_func
        self.batch_size = batch_size
        self.logger = logging.getLogger(__name__)

    async def stream_all(self) -> AsyncGenerator[T, None]:
        """
        Stream all items from the database in batches
        """
        offset = 0
        while True:
            batch = self.query_func(offset, self.batch_size)

            if not batch:
                break

            for item in batch:
                yield item

            offset += self.batch_size

    async def stream_with_progress(self, total_count: int = None) -> AsyncGenerator[tuple[T, int], None]:
        """
        Stream items with progress information
        """
        count = 0
        async for item in self.stream_all():
            count += 1
            yield item, count
            if total_count and count >= total_count:
                break


class PaginatedLoader(DataLoader[T]):
    """
    Loader that implements pagination for large datasets
    """

    def __init__(self, model_class, db_session: Session, default_page_size: int = 50):
        self.model_class = model_class
        self.db_session = db_session
        self.default_page_size = default_page_size
        self.logger = logging.getLogger(__name__)

    async def load_item(self, item_id: Any) -> Optional[T]:
        """
        Load a single item by ID
        """
        stmt = select(self.model_class).where(self.model_class.id == item_id)
        result = self.db_session.exec(stmt)
        return result.first()

    async def load_batch(self, item_ids: List[Any]) -> List[T]:
        """
        Load a batch of items by their IDs
        """
        if not item_ids:
            return []

        stmt = select(self.model_class).where(self.model_class.id.in_(item_ids))
        result = self.db_session.exec(stmt)
        return result.all()

    async def load_all(self) -> List[T]:
        """
        Load all items (use with caution for large datasets)
        """
        self.logger.warning(f"Loading ALL {self.model_class.__name__} records. This may be inefficient for large datasets.")
        stmt = select(self.model_class)
        result = self.db_session.exec(stmt)
        return result.all()

    async def load_paginated(self, page: int = 1, page_size: int = None) -> tuple[List[T], PaginationInfo]:
        """
        Load items with pagination
        """
        page_size = page_size or self.default_page_size
        offset = (page - 1) * page_size

        # Get total count
        count_stmt = select(func.count(self.model_class.id))
        total_items = self.db_session.exec(count_stmt).one()

        # Get paginated results
        stmt = select(self.model_class).offset(offset).limit(page_size)
        results = self.db_session.exec(stmt).all()

        total_pages = math.ceil(total_items / page_size)
        has_next = page < total_pages
        has_prev = page > 1

        pagination_info = PaginationInfo(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev
        )

        return results, pagination_info


class RelationshipLazyLoader(Generic[T]):
    """
    Specialized loader for lazy loading relationships
    """

    def __init__(self, parent_item: T, relationship_loader: Callable[[T], Any]):
        self.parent_item = parent_item
        self.relationship_loader = relationship_loader
        self._relationship_loaded = False
        self._relationship_data = None
        self.logger = logging.getLogger(__name__)

    async def load_relationship(self):
        """
        Load the relationship data
        """
        if not self._relationship_loaded:
            self.logger.debug(f"Loading relationship for {self.parent_item}")
            self._relationship_data = self.relationship_loader(self.parent_item)
            self._relationship_loaded = True
        return self._relationship_data

    def __await__(self):
        return self.load_relationship().__await__()


class LazyAttribute:
    """
    Descriptor for lazy-loading attributes
    """

    def __init__(self, loader_func: Callable):
        self.loader_func = loader_func
        self.attribute_name = None
        self.logger = logging.getLogger(__name__)

    def __set_name__(self, owner, name):
        self.attribute_name = f"_lazy_{name}"

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self

        if not hasattr(obj, self.attribute_name):
            # Load the attribute
            self.logger.debug(f"Lazy loading attribute: {self.attribute_name}")
            value = self.loader_func(obj)
            setattr(obj, self.attribute_name, value)

        return getattr(obj, self.attribute_name)

    def __set__(self, obj, value):
        setattr(obj, self.attribute_name, value)


def lazy_property(loader_func: Callable):
    """
    Decorator to create a lazy-loaded property
    """
    return LazyAttribute(loader_func)


class LazyCollection(Generic[T]):
    """
    Lazy-loaded collection that loads items on-demand
    """

    def __init__(self, loader_func: Callable[[], List[T]]):
        self.loader_func = loader_func
        self._loaded = False
        self._items = None
        self.logger = logging.getLogger(__name__)

    async def load(self) -> List[T]:
        """
        Load the collection if not already loaded
        """
        if not self._loaded:
            self.logger.debug("Loading lazy collection...")
            if asyncio.iscoroutinefunction(self.loader_func):
                self._items = await self.loader_func()
            else:
                self._items = self.loader_func()
            self._loaded = True
        return self._items

    def __len__(self):
        if not self._loaded:
            raise RuntimeError("Collection must be loaded before getting length")
        return len(self._items)

    def __getitem__(self, index):
        if not self._loaded:
            raise RuntimeError("Collection must be loaded before accessing items")
        return self._items[index]

    def __iter__(self):
        if not self._loaded:
            raise RuntimeError("Collection must be loaded before iteration")
        return iter(self._items)

    def __await__(self):
        return self.load().__await__()


# Example usage and implementation for specific models
class LazyUserLoader:
    """
    Example implementation of lazy loading for User model
    """

    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)

    def get_lazy_profile(self, user_id: int):
        """
        Get a lazy loader for user profile
        """
        async def load_profile():
            from ..models.user import User
            stmt = select(User).where(User.id == user_id)
            user = self.db_session.exec(stmt).first()
            return user.profile if user and hasattr(user, 'profile') else None

        return LazyLoader(load_profile)

    def get_lazy_permissions(self, user_id: int):
        """
        Get a lazy loader for user permissions
        """
        async def load_permissions():
            from ..models.user import User
            stmt = select(User).where(User.id == user_id)
            user = self.db_session.exec(stmt).first()
            return user.permissions if user and hasattr(user, 'permissions') else []

        return LazyLoader(load_permissions)

    def get_streaming_users(self, batch_size: int = 100):
        """
        Get a streaming loader for all users
        """
        from ..models.user import User

        def query_batch(offset: int, limit: int):
            stmt = select(User).offset(offset).limit(limit)
            return self.db_session.exec(stmt).all()

        return StreamingLoader(query_batch, batch_size)


class LazyProductLoader:
    """
    Example implementation of lazy loading for Product model
    """

    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)

    def get_lazy_stock_levels(self, product_ids: List[int]):
        """
        Get lazy loader for stock levels of multiple products
        """
        async def load_stock_levels():
            from ..models.stock_entry import StockEntry
            from sqlmodel import func
            # Query stock levels for the given products
            stmt = select(
                StockEntry.product_id,
                func.sum(StockEntry.quantity).label('total_stock')
            ).where(StockEntry.product_id.in_(product_ids)).group_by(StockEntry.product_id)

            results = self.db_session.exec(stmt).all()
            return {result.product_id: result.total_stock for result in results}

        return LazyLoader(load_stock_levels)

    def get_paginated_products(self, page: int = 1, page_size: int = 50):
        """
        Get paginated loader for products
        """
        from ..models.product import Product
        return PaginatedLoader(Product, self.db_session, page_size)


# Utility functions for implementing lazy loading
def apply_lazy_loading(model_instance, attr_name: str, loader_func: Callable):
    """
    Apply lazy loading to a specific attribute of a model instance
    """
    lazy_attr = LazyAttribute(loader_func)
    lazy_attr.__set_name__(type(model_instance), attr_name)

    # Set the lazy attribute on the instance
    setattr(model_instance, attr_name, lazy_attr.__get__(model_instance))


def create_lazy_relationship(parent_obj, relationship_name: str, loader_func: Callable):
    """
    Create a lazy-loaded relationship on a parent object
    """
    lazy_loader = RelationshipLazyLoader(parent_obj, loader_func)
    setattr(parent_obj, f"_{relationship_name}_loader", lazy_loader)

    # Create a property that uses the lazy loader
    def lazy_getter(self):
        return self._relationship_name_loader

    prop = property(lazy_getter)
    setattr(type(parent_obj), relationship_name, prop)


# Performance monitoring for lazy loading
class LazyLoadingMonitor:
    """
    Monitor performance of lazy loading operations
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.stats = {
            'total_lazy_loads': 0,
            'total_time_spent': 0.0,
            'average_load_time': 0.0
        }

    def record_load(self, load_time: float):
        """
        Record a lazy loading operation
        """
        self.stats['total_lazy_loads'] += 1
        self.stats['total_time_spent'] += load_time
        self.stats['average_load_time'] = self.stats['total_time_spent'] / self.stats['total_lazy_loads']

        if load_time > 1.0:  # Log slow loads (over 1 second)
            self.logger.warning(f"Slow lazy load detected: {load_time:.2f}s")

    def get_stats(self):
        """
        Get current statistics
        """
        return self.stats.copy()


# Global monitor instance
lazy_monitor = LazyLoadingMonitor()


def monitor_lazy_load(func: Callable) -> Callable:
    """
    Decorator to monitor lazy loading performance
    """
    import time
    from functools import wraps

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()

        load_time = end_time - start_time
        lazy_monitor.record_load(load_time)

        return result

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()

        load_time = end_time - start_time
        lazy_monitor.record_load(load_time)

        return result

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


# Example usage patterns
class LazyLoadingExamples:
    """
    Examples of how to implement lazy loading
    """

    @staticmethod
    def example_lazy_user_with_profile(db_session, user_id: int):
        """
        Example: Lazy loading user with profile
        """
        from ..models.user import User

        # Method 1: Using LazyLoader
        async def load_user():
            stmt = select(User).where(User.id == user_id)
            return db_session.exec(stmt).first()

        lazy_user = LazyLoader(load_user)
        return lazy_user

    @staticmethod
    def example_lazy_collection_of_orders(db_session, customer_id: int):
        """
        Example: Lazy loading collection of orders for a customer
        """
        from ..models.invoice import Invoice

        async def load_orders():
            stmt = select(Invoice).where(Invoice.customer_id == customer_id)
            return db_session.exec(stmt).all()

        lazy_orders = LazyCollection(load_orders)
        return lazy_orders

    @staticmethod
    def example_paginated_product_catalog(db_session, page: int = 1, page_size: int = 20):
        """
        Example: Paginated loading of product catalog
        """
        return PaginatedLoader("Product", db_session, page_size).load_paginated(page, page_size)


if __name__ == "__main__":
    # Example usage
    print("Lazy loading utilities loaded")
    print(f"Default page size: 50 items")
    print(f"Batch size for streaming: 100 items")