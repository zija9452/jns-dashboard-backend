"""
Test script to reproduce the specific Pydantic v2 recursion error mentioned in the issue.
This creates a more complex scenario that might trigger the infinite recursion.
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid


# Create a more complex scenario that might trigger the recursion error
class ComplexField(BaseModel):
    """A complex field that might cause issues during repr"""
    name: str
    type_annotation: Any  # This could be any complex type
    default_value: Any = None
    constraints: List[str] = []

    def __repr_args__(self):
        # Custom repr_args that might cause issues
        yield 'name', self.name
        yield 'type_annotation', self.type_annotation  # This could be recursive
        yield 'default_value', self.default_value
        yield 'constraints', self.constraints


class ComplexModelDefinition(BaseModel):
    """Model that represents a definition of another model - potential for recursion"""
    name: str
    fields: Dict[str, ComplexField]
    base_classes: List[Any] = []  # Could reference other model definitions

    def __repr_args__(self):
        yield 'name', self.name
        yield 'fields', self.fields  # This could cause recursion
        yield 'base_classes', self.base_classes


# Try to create a scenario that might trigger the specific error
def test_complex_scenario():
    """Test complex scenario that might trigger the recursion error"""
    print("Testing complex scenario...")

    # Create a complex field with a reference to its parent model
    complex_field = ComplexField(
        name="test_field",
        type_annotation=str,  # Use a simple type first
        constraints=["required", "unique"]
    )

    # Create a model definition containing the field
    model_def = ComplexModelDefinition(
        name="TestModel",
        fields={"test_field": complex_field}
    )

    # Update the complex field to reference the parent model
    complex_field.type_annotation = model_def  # This creates a circular reference

    print(f"Model definition: {model_def}")
    print(f"Complex field: {complex_field}")


# Create a scenario similar to what might exist in the current codebase
class Product(BaseModel):
    id: uuid.UUID
    name: str
    category_id: uuid.UUID
    category: Optional['Category'] = None  # Forward reference
    variants: List['ProductVariant'] = []


class ProductVariant(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    product: Optional['Product'] = None  # Circular reference
    sku: str
    price: float
    attributes: Dict[str, str] = {}


class Category(BaseModel):
    id: uuid.UUID
    name: str
    parent_id: Optional[uuid.UUID] = None
    parent: Optional['Category'] = None  # Self-reference
    children: List['Category'] = []
    products: List['Product'] = []


def test_realistic_scenario():
    """Test a realistic scenario similar to the existing codebase"""
    print("\nTesting realistic scenario...")

    # Create instances
    parent_cat = Category(id=uuid.uuid4(), name="Electronics")
    child_cat = Category(id=uuid.uuid4(), name="Phones", parent_id=parent_cat.id)
    product = Product(id=uuid.uuid4(), name="iPhone", category_id=child_cat.id)
    variant = ProductVariant(id=uuid.uuid4(), product_id=product.id, sku="IPHONE-X", price=999.99)

    # Establish relationships
    parent_cat.children = [child_cat]
    child_cat.parent = parent_cat
    child_cat.products = [product]
    product.category = child_cat
    product.variants = [variant]
    variant.product = product

    # Try to print representations - this might trigger the recursion
    print(f"Parent category: {parent_cat}")
    print(f"Child category: {child_cat}")
    print(f"Product: {product}")
    print(f"Variant: {variant}")


def test_field_annotations():
    """Test field annotations that might cause the recursion error"""
    print("\nTesting field annotations...")

    from pydantic.fields import FieldInfo

    # Create a field with complex annotation that might cause recursion
    field_info = FieldInfo(annotation=str, default="test")

    # Create a model that references its own field information
    class RecursiveFieldModel(BaseModel):
        name: str
        field_info_ref: Optional[FieldInfo] = None

        def __repr_args__(self):
            yield 'name', self.name
            if self.field_info_ref:
                yield 'field_info_ref', self.field_info_ref

    # This might cause the recursion when trying to represent the field_info_ref
    model_instance = RecursiveFieldModel(name="test")
    field_info_from_model = FieldInfo(annotation=RecursiveFieldModel, default=model_instance)
    model_instance.field_info_ref = field_info_from_model

    print(f"Model instance: {model_instance}")


if __name__ == "__main__":
    print("Testing complex Pydantic v2 scenarios that might cause recursion\n")

    try:
        test_complex_scenario()
    except RecursionError as e:
        print(f"Recursion error occurred in complex scenario: {e}")
    except Exception as e:
        print(f"Other error in complex scenario: {e}")

    try:
        test_realistic_scenario()
    except RecursionError as e:
        print(f"Recursion error occurred in realistic scenario: {e}")
    except Exception as e:
        print(f"Other error in realistic scenario: {e}")

    try:
        test_field_annotations()
    except RecursionError as e:
        print(f"Recursion error occurred in field annotations: {e}")
    except Exception as e:
        print(f"Other error in field annotations: {e}")

    print("\nTest completed.")