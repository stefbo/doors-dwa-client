from __future__ import annotations
import re
from typing import Optional
from dwa_client.guid import DWAResourceType, GUID

_DWA_URN_RE = re.compile(
    r"^urn:(?:rational|telelogic)::1-"
    r"(?P<dbid>[0-9a-fA-F]{16})-"
    r"(?P<kind>[PFMO])-"
    r"(?P<rest>.+)$"
)


class URN:
    """Immutable, hashable wrapper for a DWA OSLC URN (concrete resources only)."""

    __slots__ = ("dbid", "resource_type", "key", "object_no", "module_key")

    def __init__(
        self,
        dbid: str,
        resource_type: DWAResourceType,
        key: str,
        object_no: Optional[int] = None,
        module_key: Optional[str] = None,
    ) -> None:
        if not re.match(r"^[0-9a-fA-F]{16}$", dbid):
            raise ValueError(f"Invalid database ID: {dbid}")
        if resource_type not in (
            DWAResourceType.PROJECT,
            DWAResourceType.FOLDER,
            DWAResourceType.MODULE,
            DWAResourceType.OBJECT,
        ):
            raise ValueError(f"Invalid resource type: {resource_type}")
        if resource_type == DWAResourceType.OBJECT:
            if object_no is None or module_key is None:
                raise ValueError("Object URN requires object_no and module_key")
            if not isinstance(object_no, int) or object_no < 0:
                raise ValueError("Invalid object number")
            if not re.match(r"^[0-9a-fA-F]{8}$", module_key):
                raise ValueError("Invalid module key for object URN")
        else:
            if not re.match(r"^[0-9a-fA-F]{8}$", key):
                raise ValueError(f"Invalid key for {resource_type}: {key}")

        self.dbid = dbid.lower()
        self.resource_type = resource_type
        self.key = key.lower()
        self.object_no = object_no
        self.module_key = module_key.lower() if module_key else None

    @classmethod
    def from_string(cls, value: str) -> "URN":
        m = _DWA_URN_RE.match(value)
        if not m:
            raise ValueError(f"Invalid DWA URN: {value}")
        dbid = m.group("dbid").lower()
        kind = m.group("kind")
        rest = m.group("rest")
        if kind == "O":
            parts = rest.split("-")
            if len(parts) != 2:
                raise ValueError(f"Invalid object URN: {value}")
            object_no = int(parts[0])
            module_key = parts[1].lower()
            return cls(
                dbid,
                DWAResourceType.OBJECT,
                module_key,
                object_no=object_no,
                module_key=module_key,
            )
        else:
            if not re.match(r"^[0-9a-fA-F]{8}$", rest):
                raise ValueError(f"Invalid key for {kind}: {rest}")
            rt = DWAResourceType(kind)
            return cls(dbid, rt, rest)

    @classmethod
    def from_guid(cls, guid: GUID) -> "URN":
        """Create a URN from a GUID instance."""
        dbid = guid.get_dbid()
        resource_type = guid.get_resource_type()
        if resource_type == DWAResourceType.OBJECT:
            object_no = guid.get_object_id()
            module_key = guid.get_parent_key()[-8:]
            return cls(
                dbid=dbid,
                resource_type=resource_type,
                key=module_key,
                object_no=object_no,
                module_key=module_key,
            )
        else:
            key = guid.get_parent_key()[-8:]
            return cls(
                dbid=dbid,
                resource_type=resource_type,
                key=key,
            )

    def get_dbid(self) -> str:
        return self.dbid

    def get_resource_type(self) -> DWAResourceType:
        return self.resource_type

    def get_key(self) -> str:
        """Returns the 8-hex-digit key for project/folder/module, or module key for object."""
        return self.key

    def get_object_no(self) -> Optional[int]:
        """Returns the object number for object URNs, else None."""
        return self.object_no

    def get_module_key(self) -> Optional[str]:
        """Returns the module key for object URNs, else None."""
        return self.module_key

    def __str__(self) -> str:
        base = f"urn:rational::1-{self.dbid}-{self.resource_type.value}-"
        if self.resource_type == DWAResourceType.OBJECT:
            return f"{base}{self.object_no}-{self.module_key}"
        else:
            return f"{base}{self.key}"

    def __repr__(self) -> str:
        return (
            f"URN(dbid={self.dbid!r}, resource_type={self.resource_type!r}, "
            f"key={self.key!r}, object_no={self.object_no!r}, module_key={self.module_key!r})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, URN):
            return NotImplemented
        return (
            self.dbid == other.dbid
            and self.resource_type == other.resource_type
            and self.key == other.key
            and self.object_no == other.object_no
            and self.module_key == other.module_key
        )

    def __hash__(self) -> int:
        return hash(
            (self.dbid, self.resource_type, self.key, self.object_no, self.module_key)
        )
