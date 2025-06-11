import pytest
from dwa_client.oslc.urn import URN
from dwa_client.guid import DWAResourceType


@pytest.mark.parametrize(
    "urn_str,expected_dbid,expected_type,expected_key,expected_object_no,expected_module_key",
    [
        (
            "urn:rational::1-48beda447cfb0c27-M-00003c20",
            "48beda447cfb0c27",
            DWAResourceType.MODULE,
            "00003c20",
            None,
            None,
        ),
        (
            "urn:rational::1-48beda447cfb0c27-P-0000500d",
            "48beda447cfb0c27",
            DWAResourceType.PROJECT,
            "0000500d",
            None,
            None,
        ),
        (
            "urn:rational::1-48beda447cfb0c27-O-2-00003c20",
            "48beda447cfb0c27",
            DWAResourceType.OBJECT,
            "00003c20",
            2,
            "00003c20",
        ),
        (
            "urn:rational::1-48beda447cfb0c27-F-00000003",
            "48beda447cfb0c27",
            DWAResourceType.FOLDER,
            "00000003",
            None,
            None,
        ),
    ],
)
def test_urn_fields(
    urn_str: str,
    expected_dbid: str,
    expected_type: DWAResourceType,
    expected_key: str,
    expected_object_no: int | None,
    expected_module_key: str | None,
) -> None:
    urn = URN.from_string(urn_str)
    assert urn.get_dbid() == expected_dbid
    assert urn.get_resource_type() == expected_type
    assert urn.get_key() == expected_key
    assert urn.get_object_no() == expected_object_no
    assert urn.get_module_key() == expected_module_key


@pytest.mark.parametrize(
    "urn_str",
    [
        "urn:rational::1-48beda447cfb0c27-M-00003c20",
        "urn:rational::1-48beda447cfb0c27-P-0000500d",
        "urn:rational::1-48beda447cfb0c27-O-2-00003c20",
        "urn:rational::1-48beda447cfb0c27-F-00000003",
    ],
)
def test_urn_str_roundtrip(urn_str: str) -> None:
    urn = URN.from_string(urn_str)
    assert str(urn) == urn_str


import pytest
from dwa_client.oslc.urn import URN
from dwa_client.guid import DWAResourceType, GUID


@pytest.mark.parametrize(
    "guid_str,expected_urn",
    [
        (
            "AB:48beda447cfb0c27:21:2100003c20:28ffffffff:{null,0}",
            "urn:rational::1-48beda447cfb0c27-M-00003c20",
        ),
        (
            "AB:48beda447cfb0c27:1f:1f0000500d:28ffffffff",
            "urn:rational::1-48beda447cfb0c27-P-0000500d",
        ),
        (
            "AB:48beda447cfb0c27:23:2100003c20:2800000002:{1000014,1709026242}",
            "urn:rational::1-48beda447cfb0c27-O-2-00003c20",
        ),
        (
            "AB:48beda447cfb0c27:1f:1f00000003:28ffffffff",
            "urn:rational::1-48beda447cfb0c27-F-00000003",
        ),
    ],
)
def test_urn_from_guid(guid_str: str, expected_urn: str) -> None:
    guid = GUID.from_string(guid_str)
    urn = URN.from_guid(guid)
    assert str(urn) == expected_urn
