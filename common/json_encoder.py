import datetime
import json
from uuid import UUID
try:
    from pydantic import BaseModel
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False

# Type registry (can be extended as needed)
_TYPE_REGISTRY = {
    datetime.datetime: {
        'serialize': lambda obj: obj.isoformat(),
        'deserialize': lambda data: datetime.datetime.fromisoformat(data),
        'type_id': '__datetime__'
    },
    datetime.date: {
        'serialize': lambda obj: obj.isoformat(),
        'deserialize': lambda data: datetime.date.fromisoformat(data),
        'type_id': '__date__'
    },
    UUID: {
        'serialize': lambda obj: str(obj),
        'deserialize': lambda data: UUID(data),
        'type_id': '__uuid__'
    }
}


def register_type(
        cls: type,
        serialize_fn: callable,
        deserialize_fn: callable,
        type_id: str
):
    """Register serialization/deserialization methods for custom types"""
    _TYPE_REGISTRY[cls] = {
        'serialize': serialize_fn,
        'deserialize': deserialize_fn,
        'type_id': type_id
    }


class UniversalEncoder(json.JSONEncoder):
    """JSON encoder that supports multiple data types"""

    def default(self, obj):
        # Check registered types
        for cls, info in _TYPE_REGISTRY.items():
            if isinstance(obj, cls):
                return {info['type_id']: info['serialize'](obj)}

        # Support for Pydantic BaseModel
        if HAS_PYDANTIC and isinstance(obj, BaseModel):
            # Use model_dump() for Pydantic v2 or dict() for v1
            if hasattr(obj, 'model_dump'):
                return obj.model_dump()
            else:
                return obj.dict()

        # Handle custom classes (via __dict__)
        if hasattr(obj, '__dict__'):
            return vars(obj)

        # Handle other iterable objects
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)  # Fallback: convert to string


def universal_decoder(obj_dict):
    """Universal decoder"""
    for info in _TYPE_REGISTRY.values():
        if info['type_id'] in obj_dict:
            return info['deserialize'](obj_dict[info['type_id']])

    # Handle custom class reconstruction (requires class definition in scope)
    if '__class__' in obj_dict:
        cls = globals().get(obj_dict['__class__'])
        if cls:
            return cls(**obj_dict['__data__'])

    return obj_dict


# Example usage =============================================

if __name__ == '__main__':
    # Example custom class
    class User:
        def __init__(self, name, created_at):
            self.name = name
            self.created_at = created_at

    # Register custom type
    register_type(
        cls=User,
        serialize_fn=lambda u: {'name': u.name, 'created_at': u.created_at},
        deserialize_fn=lambda data: User(**data),
        type_id='__user__'
    )

    # Test data
    data = {
        "timestamp": datetime.datetime.now(),
        "user": User("Alice", datetime.datetime.now()),
        "uuid": UUID('12345678123456781234567812345678')
    }

    # Serialization
    json_str = json.dumps(data, cls=UniversalEncoder, indent=2)
    print("Serialized JSON:")
    print(json_str)

    # Deserialization
    restored_data = json.loads(json_str, object_hook=universal_decoder)
    print("\nDeserialized Data:")
    print(f"Type of timestamp: {type(restored_data['timestamp'])}")
    print(f"Type of user: {type(restored_data['user'])}")
    print(f"User name: {restored_data['user'].name}")

    # Example with Pydantic if available
    if HAS_PYDANTIC:
        from pydantic import BaseModel
        
        class UserModel(BaseModel):
            name: str
            age: int
        
        # Test Pydantic model serialization
        user_model = UserModel(name="Bob", age=30)
        json_str = json.dumps({"pydantic_user": user_model}, cls=UniversalEncoder)
        print("\nPydantic Model Serialized:")
        print(json_str)
