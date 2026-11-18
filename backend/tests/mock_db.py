import uuid
from typing import Dict, Any, List, Optional, Type
from datetime import datetime
from unittest.mock import MagicMock
from sqlalchemy.sql.selectable import Select

from contextlib import contextmanager

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

    def scalar(self):
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

    def _get_ident(self, obj: Any) -> str:
        if hasattr(obj, "token_sig") and obj.token_sig:
            return str(obj.token_sig)
        if hasattr(obj, "id") and obj.id:
            return str(obj.id)
        # Assign generated ID if neither present
        try:
            obj.id = str(uuid.uuid4())
            return str(obj.id)
        except Exception:
            return str(uuid.uuid4())

    def add(self, obj: Any):
        ident = self._get_ident(obj)
        obj_type = type(obj)
        if obj_type not in self.storage:
            self.storage[obj_type] = {}
        self.storage[obj_type][ident] = obj
        self.added_objects.append(obj)

    def add_all(self, objs: List[Any]):
        for obj in objs:
            self.add(obj)

    def flush(self):
        for obj in self.added_objects:
            ident = self._get_ident(obj)
            obj_type = type(obj)
            if obj_type not in self.storage:
                self.storage[obj_type] = {}
            self.storage[obj_type][ident] = obj

    def commit(self):
        self.flush()

    def refresh(self, obj: Any):
        pass

    @contextmanager
    def begin_nested(self):
        yield self

    def get(self, model: Type, ident: Any):
        return self.storage.get(model, {}).get(str(ident))

    def delete(self, obj: Any):
        obj_type = type(obj)
        ident = self._get_ident(obj)
        if obj_type in self.storage and ident in self.storage[obj_type]:
            del self.storage[obj_type][ident]

    def execute(self, stmt: Any):
        if self._custom_return is not None:
            ret = self._custom_return
            if isinstance(ret, list):
                return MockResult(ret)
            return MockResult([ret])

        # If it's a select statement
        target_entity = None
        if hasattr(stmt, "column_descriptions") and stmt.column_descriptions:
            target_entity = stmt.column_descriptions[0].get("entity")

        if not target_entity and isinstance(stmt, Select):
            for entity in self.storage:
                if str(entity.__name__) in str(stmt):
                    target_entity = entity
                    break

        if target_entity and target_entity in self.storage:
            items = list(self.storage[target_entity].values())

            # Specific in-memory filtering for CommunicationLog (Feature A read/unread and patient isolation)
            if target_entity.__name__ == "CommunicationLog":
                if hasattr(stmt, "_where_criteria") and stmt._where_criteria:
                    filtered = []
                    for item in items:
                        match = True
                        for criterion in stmt._where_criteria:
                            try:
                                col_name = getattr(criterion.left, "key", None) or getattr(criterion.left, "name", None)
                                op = getattr(criterion, "operator", None)
                                if col_name == "patient_id":
                                    pid = getattr(criterion.right, "value", None)
                                    if pid and item.patient_id != pid:
                                        match = False
                                        break
                                elif col_name == "viewed_at":
                                    if "is" in str(op) and item.viewed_at is not None:
                                        match = False
                                        break
                            except Exception:
                                pass
                        if match:
                            filtered.append(item)
                    items = filtered

            # Specific in-memory filtering for PushDeviceRegistration (FCM device management)
            elif target_entity.__name__ == "PushDeviceRegistration":
                if hasattr(stmt, "_where_criteria") and stmt._where_criteria:
                    filtered = []
                    for item in items:
                        match = True
                        for criterion in stmt._where_criteria:
                            try:
                                col_name = getattr(criterion.left, "key", None) or getattr(criterion.left, "name", None)
                                right_val = getattr(criterion.right, "value", None)
                                op_str = str(getattr(criterion, "operator", ""))
                                if col_name == "patient_id":
                                    if "!=" in op_str or "ne" in op_str:
                                        if right_val and item.patient_id == right_val:
                                            match = False
                                            break
                                    else:
                                        if right_val and item.patient_id != right_val:
                                            match = False
                                            break
                                elif col_name == "fcm_token":
                                    if right_val and item.fcm_token != right_val:
                                        match = False
                                        break
                                elif col_name == "is_active":
                                    expected = bool(right_val) if right_val is not None else True
                                    if bool(item.is_active) != expected:
                                        match = False
                                        break
                                elif col_name == "push_enabled":
                                    expected = bool(right_val) if right_val is not None else True
                                    if bool(item.push_enabled) != expected:
                                        match = False
                                        break
                            except Exception:
                                pass
                        if match:
                            filtered.append(item)
                    items = filtered

            # Check if it was a count query
            if "count(" in str(stmt).lower():
                return MockResult([len(items)])

            return MockResult(items)

        # Default fallback
        return MockResult([])

    def close(self):
        pass
