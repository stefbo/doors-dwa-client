import pytest
from typing import Optional
from dwa_client.guid import GUID, DWAResourceType
from dwa_client.oslc.urn import URN


@pytest.mark.parametrize(
    "guid_str,expected_type",
    [
        (
            "AB:48beda447cfb0c27:21:2100003c20:28ffffffff:{null,0}",
            DWAResourceType.MODULE,
        ),
        ("AB:48beda447cfb0c27:1f:1f0000500d:28ffffffff", DWAResourceType.PROJECT),
        (
            "AB:48beda447cfb0c27:23:2100003c20:2800000002:{1000014,1709026242}",
            DWAResourceType.OBJECT,
        ),
        ("AB:48beda447cfb0c27:1f:1f00000003:28ffffffff", DWAResourceType.FOLDER),
    ],
)
def test_guid_resource_type(guid_str: str, expected_type: DWAResourceType) -> None:
    # Remove flags for GUID constructor, as it does not accept them
    parts = guid_str.split(":")
    if len(parts) > 5:
        guid_str_no_flags = ":".join(parts[:5])
    else:
        guid_str_no_flags = guid_str
    guid = GUID.from_string(guid_str_no_flags)
    assert guid.get_resource_type() == expected_type


@pytest.mark.parametrize(
    "guid_str,dbid,typecode,parent_key,object_key,baseline_key_str",
    [
        (
            "AB:48beda447cfb0c27:21:2100003c20:28ffffffff:{null,0}",
            "48beda447cfb0c27",
            "21",
            "2100003c20",
            "28ffffffff",
            "{null,0}",
        ),
        (
            "AB:48beda447cfb0c27:1f:1f0000500d:28ffffffff",
            "48beda447cfb0c27",
            "1f",
            "1f0000500d",
            "28ffffffff",
            None,
        ),
        (
            "AB:48beda447cfb0c27:23:2100003c20:2800000002:{1000014,1709026242}",
            "48beda447cfb0c27",
            "23",
            "2100003c20",
            "2800000002",
            "{1000014,1709026242}",
        ),
        (
            "AB:48beda447cfb0c27:1f:1f00000003:28ffffffff",
            "48beda447cfb0c27",
            "1f",
            "1f00000003",
            "28ffffffff",
            None,
        ),
    ],
)
def test_guid_fields_full(
    guid_str: str,
    dbid: str,
    typecode: str,
    parent_key: str,
    object_key: str,
    baseline_key_str: Optional[str],
) -> None:
    guid = GUID.from_string(guid_str)
    assert guid.get_dbid() == dbid
    assert guid.get_typecode() == typecode
    assert guid.get_parent_key() == parent_key
    assert guid.get_object_key() == object_key
    if baseline_key_str is None:
        assert guid.baseline_key is None
    else:
        assert str(guid.baseline_key) == baseline_key_str


@pytest.mark.parametrize(
    "guid_str",
    [
        "AB:48beda447cfb0c27:21:2100003c20:28ffffffff:{null,0}",
        "AB:48beda447cfb0c27:1f:1f0000500d:28ffffffff",
        "AB:48beda447cfb0c27:23:2100003c20:2800000002:{1000014,1709026242}",
        "AB:48beda447cfb0c27:1f:1f00000003:28ffffffff",
    ],
)
def test_guid_str_roundtrip_full(guid_str: str) -> None:
    guid = GUID.from_string(guid_str)
    assert str(guid) == guid_str


@pytest.mark.parametrize(
    "guid_str,expected_object_id",
    [
        ("AB:48beda447cfb0c27:23:2100003e20:2800000ba6:{100001d,1742565471}", 2982),
        ("AB:48beda447cfb0c27:23:2100003c20:2800000002:{1000014,1709026242}", 2),
        ("AB:48beda447cfb0c27:21:2100003c20:28ffffffff:{null,0}", 4294967295),
        ("AB:48beda447cfb0c27:1f:1f0000500d:28ffffffff", 4294967295),
    ],
)
def test_guid_object_id(guid_str: str, expected_object_id: int) -> None:
    guid = GUID.from_string(guid_str)
    assert guid.get_object_id() == expected_object_id


@pytest.mark.parametrize(
    "guid_str,expected_baseline,expected_id,expected_epoch,expected_is_legacy",
    [
        (
            "AB:48beda447cfb0c27:23:2100003e20:2800000ba6:{100001d,1742565471}",
            "{100001d,1742565471}",
            "100001d",
            1742565471,
            False,
        ),
        (
            "AB:48beda447cfb0c27:23:2100003c20:2800000002:{1000014,1709026242}",
            "{1000014,1709026242}",
            "1000014",
            1709026242,
            False,
        ),
        (
            "AB:48beda447cfb0c27:21:2100003c20:28ffffffff:{null,0}",
            "{null,0}",
            "null",
            0,
            False,
        ),
        ("AB:48beda447cfb0c27:1f:1f0000500d:28ffffffff", None, None, None, None),
        (
            "AB:48beda447cfb0c27:23:2100003c20:2800000002:ff0000000a",
            "ff0000000a",
            "0000000a",
            None,
            True,
        ),
    ],
)
def test_guid_baseline_key_elements(
    guid_str: str,
    expected_baseline: Optional[str],
    expected_id: Optional[str],
    expected_epoch: Optional[int],
    expected_is_legacy: Optional[bool],
) -> None:
    guid = GUID.from_string(guid_str)
    baseline = guid.get_baseline_key()
    if expected_baseline is None:
        assert baseline is None
    else:
        assert str(baseline) == expected_baseline
        assert baseline.baseline_id == expected_id
        assert baseline.epoch == expected_epoch
        assert baseline.is_legacy == expected_is_legacy


@pytest.mark.parametrize(
    "urn_str,expected_guid_str",
    [
        (
            "urn:rational::1-48beda447cfb0c27-M-00003c20",
            "AB:48beda447cfb0c27:21:2100003c20:28ffffffff",
        ),
        (
            "urn:rational::1-48beda447cfb0c27-P-0000500d",
            "AB:48beda447cfb0c27:1f:1f0000500d:28ffffffff",
        ),
        (
            "urn:rational::1-48beda447cfb0c27-O-2-00003c20",
            "AB:48beda447cfb0c27:23:2100003c20:2800000002",
        ),
        (
            "urn:rational::1-48beda447cfb0c27-F-00000003",
            "AB:48beda447cfb0c27:1f:1f00000003:28ffffffff",
        ),
    ],
)
def test_guid_from_urn(urn_str: str, expected_guid_str: str) -> None:
    urn = URN.from_string(urn_str)
    guid = GUID.from_urn(urn)
    assert str(guid) == expected_guid_str


def test_guid_hash_equality() -> None:
    # Identical GUIDs should have the same hash and be equal
    guid1 = GUID.from_string("AB:48beda447cfb0c27:21:2100003c20:28ffffffff:{null,0}")
    guid2 = GUID.from_string("AB:48beda447cfb0c27:21:2100003c20:28ffffffff:{null,0}")
    assert guid1 == guid2
    assert hash(guid1) == hash(guid2)


def test_guid_hash_inequality() -> None:
    # Different GUIDs should have different hashes (very likely)
    guid1 = GUID.from_string("AB:48beda447cfb0c27:21:2100003c20:28ffffffff:{null,0}")
    guid2 = GUID.from_string("AB:48beda447cfb0c27:1f:1f0000500d:28ffffffff")
    assert guid1 != guid2
    assert hash(guid1) != hash(guid2)


def test_guid_hash_in_collections() -> None:
    # GUIDs should be usable as dict keys and set members
    guid1 = GUID.from_string("AB:48beda447cfb0c27:21:2100003c20:28ffffffff:{null,0}")
    guid2 = GUID.from_string("AB:48beda447cfb0c27:21:2100003c20:28ffffffff:{null,0}")
    guid3 = GUID.from_string("AB:48beda447cfb0c27:1f:1f00000003:28ffffffff")
    guid_set = {guid1, guid3}
    assert guid2 in guid_set
    guid_dict = {guid1: "module", guid3: "folder"}
    assert guid_dict[guid2] == "module"
