"""
Test script to reproduce and demonstrate the Pydantic v2 recursion error
and provide a solution for circular references.
"""

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid


# Example of problematic models that could cause recursion error
class User(BaseModel):
    id: uuid.UUID
    name: str
    # This creates a circular reference if Order has a user field
    orders: List['Order'] = []


class Order(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    user: Optional['User'] = None  # Circular reference
    amount: float


# Correct way to handle circular references in Pydantic v2
from typing import ForwardRef

# Define forward references
UserRef = ForwardRef('User')

class UserCorrect(BaseModel):
    id: uuid.UUID = uuid.uuid4()
    name: str
    email: str
    # Using string annotations to avoid circular imports
    orders: List['OrderCorrect'] = []


class OrderCorrect(BaseModel):
    id: uuid.UUID = uuid.uuid4()
    user_id: uuid.UUID
    # Use string annotation instead of actual reference
    user: Optional['UserCorrect'] = None
    amount: float
    created_at: datetime = datetime.now()


# Another example demonstrating the recursion issue with complex nested models
class Category(BaseModel):
    id: int
    name: str
    # Self-referencing for hierarchical categories
    parent: Optional['Category'] = None
    children: List['Category'] = []


# Demonstrate how to properly define models with circular references in Pydantic v2
def test_basic_models():
    """Test basic model creation without circular references"""
    print("Testing basic model creation...")

    # Create a user without orders to avoid circular reference initially
    user = UserCorrect(name="John Doe", email="john@example.com")
    print(f"Created user: {user}")

    # Create an order without user reference
    order = OrderCorrect(user_id=user.id, amount=100.0)
    print(f"Created order: {order}")

    # Now assign the user to the order
    order.user = user
    print(f"Assigned user to order: {order}")


def test_circular_reference():
    """Test circular reference handling"""
    print("\nTesting circular reference handling...")

    # Create instances
    user = UserCorrect(id=uuid.uuid4(), name="Jane Doe", email="jane@example.com")
    order = OrderCorrect(id=uuid.uuid4(), user_id=user.id, amount=250.0)

    # Establish bidirectional relationship
    user.orders = [order]
    order.user = user

    print(f"User with order: {user}")
    print(f"Order with user: {order}")


def test_category_hierarchy():
    """Test hierarchical category model"""
    print("\nTesting hierarchical category model...")

    # Create categories
    electronics = Category(id=1, name="Electronics")
    phones = Category(id=2, name="Phones", parent=electronics)
    smartphones = Category(id=3, name="Smartphones", parent=phones)

    # Add children to parents (in reverse order to avoid issues)
    phones.children = [smartphones]
    electronics.children = [phones]

    print(f"Electronics category: {electronics}")


def demonstrate_fixes():
    """Demonstrate various fixes for Pydantic v2 recursion issues"""
    print("\nDemonstrating fixes for Pydantic recursion issues:")

    # 1. Use string annotations for forward references
    print("1. Using string annotations for forward references")

    # 2. Proper initialization to avoid recursion during repr
    class SafeUser(BaseModel):
        id: uuid.UUID
        name: str
        email: str

        def __repr__(self):
            # Override repr to avoid recursion
            return f"SafeUser(id={self.id}, name='{self.name}', email='{self.email}')"

    class SafeOrder(BaseModel):
        id: uuid.UUID
        user_id: uuid.UUID
        user: Optional['SafeUser'] = None
        amount: float

        def __repr__(self):
            # Override repr to avoid recursion
            user_repr = f"SafeUser(id={self.user.id})" if self.user else "None"
            return f"SafeOrder(id={self.id}, user_id={self.user_id}, user={user_repr}, amount={self.amount})"

    # Test safe models
    safe_user = SafeUser(id=uuid.uuid4(), name="Safe User", email="safe@example.com")
    safe_order = SafeOrder(id=uuid.uuid4(), user_id=safe_user.id, amount=100.0)
    safe_order.user = safe_user

    print(f"Safe user: {safe_user}")
    print(f"Safe order: {safe_order}")


if __name__ == "__main__":
    print("Testing Pydantic v2 recursion issue reproduction and fixes\n")

    test_basic_models()
    test_circular_reference()
    test_category_hierarchy()
    demonstrate_fixes()

    print("\nAll tests completed successfully!")