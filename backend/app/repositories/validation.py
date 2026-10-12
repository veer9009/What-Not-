from pydantic import TypeAdapter

from app.schemas.common import DatabaseId

_identifier = TypeAdapter(DatabaseId)


def database_id(value) -> int:
    """Validate scalar IDs before emitting SQL, including bool/string rejection."""
    return _identifier.validate_python(value)
