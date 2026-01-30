"""
Test script to specifically reproduce the Pydantic v2 __repr__ recursion error
mentioned in the original issue.
"""

from pydantic import BaseModel
from pydantic._internal._repr import PlainRepr, display_as_type
from pydantic.fields import FieldInfo
from typing import List, Optional, get_origin, get_args
import sys
import traceback


def test_field_info_repr_issue():
    """Test the specific scenario that causes the __repr__ recursion error"""
    print("Testing FieldInfo __repr__ recursion issue...")

    # Create a field with complex annotation that could cause recursion
    # This mimics what might happen when Pydantic tries to represent field annotations

    class ProblematicModel(BaseModel):
        # A field with a complex annotation that references itself
        self_ref_field: 'ProblematicModel' = None

        def __repr_args__(self):
            # This is similar to what Pydantic does internally
            for field_name, field_info in self.model_fields.items():
                yield field_name, field_info  # This could cause recursion

    try:
        # Create an instance
        instance = ProblematicModel()

        # Try to access the field info which might trigger the recursion
        field_info = instance.model_fields['self_ref_field']
        print(f"Field info: {field_info}")

        # This is where the recursion might happen - when trying to represent the annotation
        print(f"Annotation: {field_info.annotation}")

        # Try to trigger repr which might cause the recursion
        repr_result = repr(instance)
        print(f"Instance repr: {repr_result[:200]}...")  # Truncate for safety

    except RecursionError as e:
        print(f"RecursionError caught: {str(e)[:100]}...")
        print("This confirms the recursion issue!")
        return True
    except Exception as e:
        print(f"Other error: {e}")
        return False

    return False


def test_complex_field_info():
    """Test with more complex field info that might trigger the issue"""
    print("\nTesting complex field info...")

    # Create a complex field info that might cause the recursion
    try:
        # Create a field info with a complex annotation
        complex_annotation = List['ComplexModel']

        field_info = FieldInfo(annotation=complex_annotation, default=None)

        # Try to get the representation of the annotation
        # This might trigger the recursion in display_as_type
        annotation_repr = display_as_type(field_info.annotation)
        print(f"Annotation repr: {annotation_repr}")

        # Create a model with this field
        class ComplexModel(BaseModel):
            items: List['ComplexModel'] = []

        # Try to instantiate and repr
        instance = ComplexModel()
        repr_result = repr(instance)
        print(f"ComplexModel repr: {repr_result}")

    except RecursionError as e:
        print(f"RecursionError in complex field: {str(e)[:100]}...")
        return True
    except Exception as e:
        print(f"Other error in complex field: {e}")
        # Still might be related to the issue
        import pydantic
        print(f"Pydantic version: {pydantic.VERSION}")
        return False

    return False


def test_direct_repr_issue():
    """Test the exact scenario from the error traceback"""
    print("\nTesting direct repr issue...")

    try:
        # Following the error stack trace pattern:
        # The issue happens in __repr_args__ -> __repr_str__ -> display_as_type

        from pydantic.fields import FieldInfo
        from pydantic._internal._repr import PlainRepr, display_as_type

        # Create a FieldInfo with a self-referencing annotation
        class SelfReferencingModel(BaseModel):
            self_field: 'SelfReferencingModel'

        # Access the field info which should have the problematic annotation
        field_info = SelfReferencingModel.model_fields['self_field']

        print(f"Field annotation: {field_info.annotation}")

        # This should trigger the display_as_type function which causes recursion
        type_display = display_as_type(field_info.annotation)
        print(f"Type display: {type_display}")

        # Try the repr of the field info itself
        field_repr = repr(field_info)
        print(f"Field info repr: {field_repr}")

        # Finally, try the full model repr
        model = SelfReferencingModel(self_field=None)
        full_repr = repr(model)
        print(f"Full model repr: {full_repr}")

    except RecursionError as e:
        print(f"RecursionError confirmed: {str(e)[:100]}...")
        tb = traceback.format_exc()
        print(f"Full traceback:\n{tb}")
        return True
    except Exception as e:
        print(f"Different error: {e}")
        import pydantic
        print(f"Pydantic version: {pydantic.VERSION}")
        return False

    return False


def test_sqlmodel_like_scenario():
    """Test scenario similar to what might happen with SQLModel relationships"""
    print("\nTesting SQLModel-like scenario...")

    # Since the original codebase uses SQLModel, the issue might be related to
    # how SQLModel extends Pydantic and creates complex relationships
    try:
        # Simulate the kind of complex relationships that might exist
        class Node(BaseModel):
            id: int
            parent: Optional['Node'] = None
            children: List['Node'] = []
            # Additional complex field that might cause issues
            metadata: dict = {}

        # Create a complex nested structure
        root = Node(id=1)
        child1 = Node(id=2, parent=root)
        child2 = Node(id=3, parent=root)
        grandchild = Node(id=4, parent=child1)

        root.children = [child1, child2]
        child1.children = [grandchild]

        # This deep nesting with circular references might trigger the issue
        print(f"Root node: {root}")

        # Try various repr operations
        print(f"Child1: {child1}")
        print(f"Grandchild: {grandchild}")

    except RecursionError as e:
        print(f"RecursionError in SQLModel-like scenario: {str(e)[:100]}...")
        return True
    except Exception as e:
        print(f"Other error in SQLModel-like scenario: {e}")
        return False

    return False


if __name__ == "__main__":
    print("Testing specific Pydantic v2 recursion scenarios\n")

    issues_found = []

    if test_field_info_repr_issue():
        issues_found.append("field_info_repr_issue")

    if test_complex_field_info():
        issues_found.append("complex_field_info")

    if test_direct_repr_issue():
        issues_found.append("direct_repr_issue")

    if test_sqlmodel_like_scenario():
        issues_found.append("sqlmodel_like_scenario")

    print(f"\nIssues found: {issues_found}")

    if issues_found:
        print("\nThe recursion error occurs when Pydantic tries to represent")
        print("field annotations that have circular references, especially")
        print("when using string annotations for forward references.")
    else:
        print("\nCould not reproduce the exact recursion error.")
        print("The issue might be version-specific or require a more specific scenario.")