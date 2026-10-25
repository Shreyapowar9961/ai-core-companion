import uuid
from typing import Dict, Any, List, Optional, Type
from datetime import datetime
from unittest.mock import MagicMock
from sqlalchemy.sql.selectable import Select

class MockResult:
    def __init__(self, items: list):
        self._items = items

    def scalars(self):
        class ScalarResult:
            def __init__(self, data):
                self._data = data
            def first(self):
                return self._data[0] if self._data else None
            def all(self):
                return list(self._data)
        return ScalarResult(self._items)

    def scalar_one_or_none(self):
        return self._items[0] if self._items else None

    def all(self):
        return list(self._items)


class MockPostgresSession:
    """
    In-memory Mock SQLAlchemy Session representing a PostgreSQL database.
    ZERO SQLite or aiosqlite dependencies.
    Provides storage and query execution for all Care Companion models.
    """
    def __init__(self):
        self.storage: Dict[Type, Dict[str, Any]] = {}
        self.added_objects: List[Any] = []
        self._custom_return = None

    def add(self, obj: Any):
        if not hasattr(obj, "id") or not obj.id:
            try:
                obj.id = str(uuid.uuid4())
            except Exception:
                pass
        obj_type = type(obj)
        if obj_type not in self.storage:
            self.storage[obj_type] = {}
        self.storage[obj_type][obj.id] = obj
        self.added_objects.append(obj)

    def add_all(self, objs: List[Any]):
        for obj in objs:
            self.add(obj)

    def flush(self):
        for obj in self.added_objects:
            if not hasattr(obj, "id") or not obj.id:
                obj.id = str(uuid.uuid4())
            obj_type = type(obj)
            if obj_type not in self.storage:
                self.storage[obj_type] = {}
            self.storage[obj_type][obj.id] = obj

    def commit(self):
        self.flush()

    def refresh(self, obj: Any):
        pass

    def get(self, model: Type, ident: Any):
        return self.storage.get(model, {}).get(str(ident))

    def delete(self, obj: Any):
        obj_type = type(obj)
        if obj_type in self.storage and hasattr(obj, "id") and obj.id in self.storage[obj_type]:
            del self.storage[obj_type][obj.id]

    def execute(self, stmt: Any):
        if self._custom_return is not None:
            ret = self._custom_return
            if isinstance(ret, list):
                return MockResult(ret)
            return MockResult([ret])

        # If it's a select statement
        if hasattr(stmt, "column_descriptions") and stmt.column_descriptions:
            target_entity = stmt.column_descriptions[0].get("entity")
            if target_entity and target_entity in self.storage:
                items = list(self.storage[target_entity].values())
                return MockResult(items)

        if isinstance(stmt, Select):
            for entity in self.storage:
                if str(entity.__name__) in str(stmt):
                    return MockResult(list(self.storage[entity].values()))

        # Default fallback
        return MockResult([])

    def close(self):
        pass
