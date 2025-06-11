# DOORS Web Access (DWA) GUIDs Documentation

This document explains the structure and usage of GUIDs (Globally Unique Identifiers) in IBM DOORS Web Access (DWA). It’s aimed at developers building libraries or tools that interact with DWA or parse GUIDs.

---

## GUID Structure

A typical DWA GUID is a colon-separated string with several encoded fields:

```
AB:<db-id>:<type>:<parentKey>:<objectKey>[:<baselineKey>]
```

### Field Breakdown

| Field           | Format / Example                       | Description                                                                                          |
| --------------- | -------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| Header          | `AB`                                   | Constant prefix for all DOORS GUIDs.                                                                 |
| `<db-id>`       | `48beda447cfb0c27`                     | 16-hex digit Database ID (see `dbid=` in URLs).                                                      |
| `<type>`        | `21`                                   | 1-byte hex type code (see [Type Codes](#type-codes)).                                                |
| `<parentKey>`   | `21xxxxxxx` (e.g. `2100003c20`)        | 5 bytes: 1-byte type + 4-byte parent key (often the module or view).                                 |
| `<objectKey>`   | `28xxxxxxxx` (e.g. `28ffffffff`)       | 5 bytes: Always starts with `28`. `28ffffffff` = whole container; otherwise, absolute object number. |
| `<baselineKey>` | Optional: `{id,epoch}` or `ffXXXXXXXX` | Baseline identifier (optional; see [Baselines](#baselines)).                                         |

---

## Type Codes

| Hex  | Meaning             |
| ---- | ------------------- |
| `18` | Project root        |
| `19` | Folder              |
| `1D` | Baseline-set/stream |
| `1F` | View                |
| `21` | Formal module       |
| `23` | Requirement/Object  |

---

## Field Semantics

### `<db-id>`

- Uniquely identifies the DOORS database.

### `<type>`

- Indicates the kind of entity (module, object, view, etc.)

### `<parentKey>`

- Encodes the parent container (e.g., module key for an object).
- Format: `<type><4-byte key>`.

### `<objectKey>`

- Always starts with `28`.
- `28ffffffff` refers to the whole container (e.g., the entire module).
- `28xxxxxxx` gives the absolute object number (requirement row).

### `<baselineKey>`

- _Optional_.
- Two formats:

  - `ffXXXXXXXX`: Legacy, where `XXXXXXXX` is the baseline number (hex).
  - `{id,epoch}`: Modern (since DWA 9.6+), where `id` is the baseline ID and `epoch` is a UNIX timestamp.
  - `{null,0}` indicates the live working copy (no baseline).

---

## Examples

| GUID Example                                                        | Meaning                                                                      |
| ------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| `AB:48beda447cfb0c27:21:2100003c20:28ffffffff:{null,0}`             | Formal Module `0x3C20` in database, live (current) version.                  |
| `AB:48beda447cfb0c27:1f:1f0000500d:28ffffffff`                      | View `0x500D` in database.                                                   |
| `AB:48beda447cfb0c27:23:2100003c20:2800000002:{1000014,1709026242}` | Object (requirement) `2` inside module `0x3C20`, from baseline ID `1000014`. |
| `AB:48beda447cfb0c27:1f:1f00000003:28ffffffff`                      | View `0x0003` (often “Standard View”).                                       |

---

## Translating GUIDs to URNs and URLs

- **URN format:**

  ```
  urn:telelogic::1-<db-id>[-M-<moduleKey>][-O-<absno>-<moduleKey>]
  ```

  - For a module: `urn:telelogic::1-<db-id>-M-<moduleKey>`
  - For an object: `urn:telelogic::1-<db-id>-O-<objectNumber>-<moduleKey>`
  - For a view: Use the module’s URN and add `&view=<viewKey>` as a query parameter.

- **DWA Redirector Example:**

  ```
  http://<server>/dwa/redirector/?version=2&urn=urn:telelogic::1-48beda447cfb0c27-O-2-00003c20
  ```

- **Baselines:**
  Append `&version=<baseline>` (legacy) or `&baseline=<id>` (modern) as appropriate.

---

## Parsing Example (Python Pseudocode)

```python
def parse_doors_guid(guid):
    seg = guid.split(':')
    dbid = seg[1]
    t = int(seg[2], 16)
    parent_key = int(seg[3][2:], 16)
    obj_seg = seg[4]
    obj_no = None
    if obj_seg.startswith('28') and obj_seg[2:] != 'ffffffff':
        obj_no = int(obj_seg[2:], 16)
    baseline = None
    if len(seg) > 5:
        if seg[5].startswith('ff'):
            baseline = int(seg[5][2:], 16)
        elif seg[5].startswith('{'):
            baseline = int(seg[5].strip('{}').split(',')[0])
    return dict(dbid=dbid, kind=t, parent=parent_key, object=obj_no, baseline=baseline)
```

---

## Quick Reference Table

| Field           | Meaning                                            |
| --------------- | -------------------------------------------------- |
| `AB`            | DOORS GUID prefix                                  |
| `<db-id>`       | Database ID (16 hex digits)                        |
| `<type>`        | Entity type (see [Type Codes](#type-codes))        |
| `<parentKey>`   | Parent container key (type + 4-byte key)           |
| `<objectKey>`   | Object key (`28ffffffff` or `28` + abs object no.) |
| `<baselineKey>` | Optional baseline info                             |

---

## Notes

- These GUIDs are not random UUIDs; their fields encode entity metadata.
- You can use these fields to map to DOORS URLs, URNs, and for OSLC queries.
- Baseline format varies by DWA version; always check your environment.

---

## See Also

- [IBM DOORS Web Access Documentation](https://www.ibm.com/docs/en/engineering-lifecycle-management-suite/lifecycle-management/7.0.2?topic=projects-doors-web-access)
- [OSLC Specification for DOORS](https://open-services.net/specifications/)

---

**For questions or suggestions, feel free to contribute or contact the library maintainers!**
