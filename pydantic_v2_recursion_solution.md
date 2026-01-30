# Pydantic v2 Recursion Error Solution

## Issue Description

The error occurs in Pydantic v2's internal representation system:

```
File "/usr/local/lib/python3.10/site-packages/pydantic/_internal/_repr.py", line 82, in __repr__
    return f'{self.__repr_name__()}({self.__repr_str__(", ")})'

File "/usr/local/lib/python3.10/site-packages/pydantic/_internal/_repr.py", line 55, in __repr_str__
    return join_str.join(repr(v) if a is None else f'{a}={v!r}' for a, v in self.__repr_args__())

File "/usr/local/lib/python3.10/site-packages/pydantic/_internal/_repr.py", line 55, in <genexpr>
    return join_str.join(repr(v) if a is None else f'{a}={v!r}' for a, v in self.__repr_args__())

File "/usr/local/lib/python3.10/site-packages/pydantic/fields.py", line 556, in __repr_args__
    yield 'annotation', _repr.PlainRepr(_repr.display_as_type(self.annotation))

File "/usr/local/lib/python3.10/site-packages/pydantic/_internal/_repr.py", line 95, in display_as_type
    return repr(obj)
```

This creates an infinite recursion when Pydantic tries to represent field annotations that have circular references.

## Root Cause Analysis

The recursion happens when:

1. A Pydantic model has fields with forward references (using string annotations)
2. Those references create circular dependencies between models
3. The `__repr__` method tries to represent the field annotations
4. This triggers `display_as_type()` which tries to represent the annotation
5. Leading to infinite recursion between the models during representation

## Current State of the Codebase

The current codebase is relatively safe because:

- It uses SQLModel which properly handles circular references with `TYPE_CHECKING`
- Models like User/Role use the correct forward reference pattern
- Authentication models (Token, TokenData) are simple and don't have circular references
- Most models follow proper Pydantic v2 patterns

## Recommended Solutions

### 1. Upgrade Dependencies to Latest Pydantic v2 Compatible Versions

Update `requirements.txt`:
```txt
pydantic==2.12.5
pydantic-settings==2.7.0
fastapi==0.115.0
sqlmodel==0.0.22
```

Update `pyproject.toml`:
```toml
pydantic = "2.12.5"
pydantic-settings = "2.7.0"
fastapi = "0.115.0"
sqlmodel = "0.0.22"
```

### 2. Best Practices for Handling Circular References

When creating Pydantic models with circular references:

```python
from typing import TYPE_CHECKING, List, Optional
from pydantic import BaseModel

if TYPE_CHECKING:
    from .other_module import OtherModel

class MyModel(BaseModel):
    id: int
    name: str
    related: Optional['OtherModel'] = None
    others: List['OtherModel'] = []

class OtherModel(BaseModel):
    id: int
    my_model: Optional['MyModel'] = None
```

### 3. Custom __repr__ Methods to Prevent Recursion

For models that might cause recursion:

```python
class SafeModel(BaseModel):
    id: int
    name: str
    related: Optional['SafeModel'] = None

    def __repr__(self):
        return f'SafeModel(id={self.id}, name="{self.name}", related_id={self.related.id if self.related else None})'
```

### 4. Pydantic Model Configuration

Use proper configuration to handle complex models:

```python
from pydantic import ConfigDict, BaseModel

class MyModel(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        # Other configurations as needed
    )

    # model fields here
```

## Testing the Solution

Create a test to verify the fix works:

```python
# test_pydantic_fix.py
from pydantic import BaseModel
from typing import List, Optional

class User(BaseModel):
    id: int
    name: str
    orders: List['Order'] = []

class Order(BaseModel):
    id: int
    user_id: int
    user: Optional['User'] = None
    amount: float

# Test that circular references work without recursion
user = User(id=1, name="John")
order = Order(id=1, user_id=1, amount=100.0)
user.orders = [order]
order.user = user

# This should work without recursion error
print(f"User: {user}")
print(f"Order: {order}")
```

## Implementation Steps

1. Update dependencies to latest Pydantic v2 compatible versions
2. Review any custom Pydantic models for potential circular references
3. Add proper `TYPE_CHECKING` imports where needed
4. Consider custom `__repr__` methods for complex models
5. Test thoroughly to ensure no recursion errors occur

## Prevention Strategies

- Always use `TYPE_CHECKING` for circular imports
- Avoid deep nesting of models with bidirectional references
- Test model representations during development
- Use Pydantic's validation and serialization features appropriately
- Monitor for recursion errors during testing

## Conclusion

The current codebase is largely protected from this issue due to proper use of SQLModel patterns. The main fix is to upgrade to the latest Pydantic v2 compatible versions which have improved handling of circular references and representation issues.