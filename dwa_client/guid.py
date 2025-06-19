from __future__ import annotations
from enum import Enum
import re
from typing import Optional, Union


class DWAResourceType(Enum):
    """Canonical resource types as used by DOORS / DWA."""

    MODULE = "M"  #: GUID type‑code 0x21
    OBJECT = "O"  #: GUID type‑code 0x23
    FOLDER = "F"  #: GUID type‑code 0x1f but ID <  0x1000
    PROJECT = "P"  #: GUID type‑code 0x1f but ID >= 0x1000

    def __str__(self) -> str:  # pragma: no cover – convenience
        return self.value


def _folder_or_project(hex_id: str) -> str:
    """Return ``"P"`` for root‑project GUIDs, else ``"F"`` for normal folders.

    Empirically DOORS uses IDs >= ``0x1000`` for projects while sub‑folders
    start at ``0x00000001``.  Adjust the threshold if you encounter edge cases.
    """
    return "P" if int(hex_id, 16) >= 0x1000 else "F"


class BaselineKey:
    """Legacy or modern baseline key representation.
    Represents a baseline key in DOORS Classic GUIDs.

    There are two formats:
    - Legacy: `ffXXXXXXXX`, where `XXXXXXXX` is the baseline number in hexadecimal.
    - Modern:
      *`{id,epoch}`, where `id` is the baseline ID and `epoch` is a UNIX timestamp.
      * `{null,0}` indicates the live working copy (no baseline).
    """

    __slots__ = ("is_legacy", "baseline_id", "epoch")

    def __init__(
        self, is_legacy: bool, baseline_id: str, epoch: Optional[int] = None
    ) -> None:
        """Initialize a baseline key.

        Args:
            is_legacy (bool): Indicates if the baseline key is in legacy format.
            baseline_id (str): The baseline identifier (legacy: hex number, modern: ID or "null").
            epoch (Optional[int], optional): The epoch timestamp (modern format only). Defaults to None.
        """
        self.is_legacy = is_legacy
        self.baseline_id = baseline_id
        self.epoch = epoch

    @staticmethod
    def from_string(value: str) -> "BaselineKey":
        if value.startswith("ff"):
            return BaselineKey(is_legacy=True, baseline_id=value[2:], epoch=None)
        elif value.startswith("{"):
            baseline_id, epoch = value.strip("{}").split(",")
            return BaselineKey(
                is_legacy=False, baseline_id=baseline_id, epoch=int(epoch)
            )
        else:
            raise ValueError(f"Invalid baseline key format: {value}")

    def __str__(self) -> str:
        if self.is_legacy:
            return f"ff{self.baseline_id}"
        else:
            return f"{{{self.baseline_id},{self.epoch}}}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BaselineKey):
            return NotImplemented
        return (
            self.is_legacy == other.is_legacy
            and self.baseline_id == other.baseline_id
            and self.epoch == other.epoch
        )

    def __hash__(self) -> int:
        return hash((self.is_legacy, self.baseline_id, self.epoch))


class GUID:
    """Immutable, hashable wrapper for a DOORS Classic GUID."""

    __slots__ = ("dbid", "typecode", "parent_key", "object_key", "baseline_key")

    def __init__(
        self,
        dbid: str,
        typecode: str,
        parent_key: str,
        object_key: str,
        baseline_key: Optional[BaselineKey] = None,
    ) -> "GUID":
        """Return a :class:`Guid` parsed from its components."""
        if not re.match(r"^[0-9A-Fa-f]{16}$", dbid):
            raise ValueError(f"Invalid database ID: {dbid}")
        if not re.match(r"^[0-9A-Fa-f]{2}$", typecode):
            raise ValueError(f"Invalid type code: {typecode}")
        if not re.match(r"^[0-9A-Fa-f]{10}$", parent_key):
            raise ValueError(f"Invalid module segment: {parent_key}")
        # parent key always starts with "28"
        if not re.match(r"^28[0-9A-Fa-f]{8}$", object_key):
            raise ValueError(f"Invalid object segment: {object_key}")

        self.dbid = dbid.lower()
        self.typecode = typecode.lower()
        self.parent_key = parent_key.lower()
        self.object_key = object_key.lower()
        self.baseline_key = baseline_key

    @classmethod
    def from_urn(cls, urn: "URN") -> "GUID":
        """Create a GUID from a URN instance (no baseline)."""
        # Import URN here to avoid circular import at module level
        from dwa_client.oslc.urn import URN as _URN

        if not isinstance(urn, _URN):
            raise TypeError("from_urn expects a URN instance")
        dbid = urn.get_dbid()
        resource_type = urn.get_resource_type()
        if resource_type == DWAResourceType.OBJECT:
            module_key = urn.get_module_key()
            object_no = urn.get_object_no()
            parent_key = f"21{module_key}"
            object_key = f"28{object_no:08x}"
            typecode = "23"
        elif resource_type == DWAResourceType.MODULE:
            parent_key = f"21{urn.get_key()}"
            object_key = "28ffffffff"
            typecode = "21"
        elif resource_type == DWAResourceType.PROJECT:
            parent_key = f"1f{urn.get_key()}"
            object_key = "28ffffffff"
            typecode = "1f"
        elif resource_type == DWAResourceType.FOLDER:
            parent_key = f"1f{urn.get_key()}"
            object_key = "28ffffffff"
            typecode = "1f"
        else:
            raise ValueError(f"Unsupported resource type: {resource_type}")
        return cls(dbid, typecode, parent_key, object_key)

    @classmethod
    def from_string(cls, value: str) -> "GUID":
        """Create a GUID from a string representation."""
        # check "AB:"
        if not value.startswith("AB:"):
            raise ValueError(f"Invalid GUID format: {value}")

        # split by ":"
        parts = value.split(":")
        if len(parts) < 5 or len(parts) > 6:
            raise ValueError(f"Invalid GUID format: {value}")

        baseline_key = None
        if len(parts) == 6:
            baseline_key = BaselineKey.from_string(parts[5])

        return cls(
            parts[1],  # dbid
            parts[2],  # typecode
            parts[3],  # parent_key
            parts[4],  # object_key
            baseline_key,  # baseline_key
        )

    def get_dbid(self) -> str:
        """16‑digit, lower‑case database ID."""
        return self.dbid

    def get_typecode(self) -> str:
        """Returns the 2‑digit, lower‑case type code.

        If you need the semantic resource type, use :meth:`get_resource_type` instead.
        """
        return self.typecode

    def get_parent_key(self) -> str:
        return self.parent_key

    def get_object_key(self) -> str:
        """The 10‑digit hexadecimal object key starting with "28".

        If you need the object ID, use :meth:`get_object_id` instead.
        """
        return self.object_key

    def get_object_id(self) -> int:
        """Return the object ID as an integer."""
        return int(self.object_key[2:], 16)  # Skip the "28" prefix

    def get_resource_type(self) -> DWAResourceType:
        """Return semantic resource type inferred from the GUID."""
        tc = self.typecode
        if tc == "21":
            return DWAResourceType.MODULE
        if tc == "23":
            return DWAResourceType.OBJECT
        if tc == "1f":
            return (
                DWAResourceType.PROJECT
                if _folder_or_project(self.parent_key[-8:]) == "P"
                else DWAResourceType.FOLDER
            )
        raise ValueError(f"Unknown GUID type‑code {tc}")

    def get_baseline_key(self) -> Optional[BaselineKey]:
        return self.baseline_key

    def __str__(self) -> str:
        """Return the string representation of the GUID."""
        result = f"AB:{self.dbid}:{self.typecode}:{self.parent_key}:{self.object_key}"
        if self.baseline_key:
            result += f":{self.baseline_key}"
        return result

    def __repr__(self) -> str:
        """Return a string representation for debugging."""
        return (
            f"GUID(dbid={self.dbid!r}, typecode={self.typecode!r}, "
            f"parent_key={self.parent_key!r}, object_key={self.object_key!r}, baseline_key={self.baseline_key!r})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GUID):
            return NotImplemented
        return (
            self.dbid == other.dbid
            and self.typecode == other.typecode
            and self.parent_key == other.parent_key
            and self.object_key == other.object_key
            and self.baseline_key == other.baseline_key
        )

    def __hash__(self) -> int:
        return hash(
            (
                self.dbid,
                self.typecode,
                self.parent_key,
                self.object_key,
                self.baseline_key,
            )
        )
