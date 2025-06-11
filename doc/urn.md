# DOORS Web Access (DWA) URNs

A DWA URN is an _opaque_ but highly structured identifier that tells the server **which database** you are talking to and **which kind of resource** you want (project, folder, module, object, …).

```
urn:rational::1-<db-id>-<kind>-<id>[ -<extra> ]
│              │ │         │        │
│              │ │         │        └─ optional (object’s parent key, etc.)
│              │ │         └────────── resource type letter
│              │ └──────────────────── 16-hex-digit database id
│              └────────────────────── scheme & vendor
└────────────────────────────────────── fixed “1” → URN version
```

---

## 1. Two roots: **`ers`** URNs vs. “**`1-…`**” URNs

| Syntax                      | What it identifies                     | Typical use                                                                                                  |
| --------------------------- | -------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| `urn:rational:ers-<db-id>:` | **Just the database**                  | Written into _festival.xml_ and other config files so DWA knows which database it will serve. ([ibm.com][1]) |
| `urn:rational::1-<db-id>-…` | **A concrete resource inside that DB** | Appears in every DWA-generated link, OSLC response, or Copy-URL action.                                      |

The two forms share the same 16-hex database id that you get from the DXL call
`print getDatabaseIdentifier()`.

---

## 2. Resource-type letters

| Letter | Meaning                                | Example snippet                                                               |
| ------ | -------------------------------------- | ----------------------------------------------------------------------------- |
| `P`    | Project root (top-level container)     | `…-P-0000500d` ([ibm.com][2])                                                 |
| `F`    | Folder (sub-container below a project) | `…-F-0001bb60` (copied from “Copy URL” on a folder) ([jazz.net][3])           |
| `M`    | Formal **M**odule                      | `…-M-0001cc43` (also used for `/linkTypes`, `/types`, … paths) ([ibm.com][4]) |
| `O`    | Requirement **O**bject (row)           | `…-O-102-000001c3` (object #102 in module `000001c3`) ([jazz.net][5])         |

> **Why no letter for “view”?**
> A view is _not_ a standalone resource. DWA keeps the module URN and adds `&view=<viewKey>` in the query string.

---

## 3. Field semantics

### `<db-id>`

16-hex digits – globally unique per DOORS database.

### `<kind>`

Single capital letter from the table above.

### `<id>`

- Always eight hex digits for `P`, `F`, and `M`.
  They map 1-to-1 to the internal “key” you see in DXL (`key (current Module)`).
- For objects (`O`) the field is split:
  `-O-<absNo>-<moduleKey>` → absolute number + owning module key.

### `<extra>`

Only present when the resource needs two keys (object’s module, attribute-definition’s module, …).
It is the owning module’s 8-hex key.

---

## 4. Examples in full URLs

| What you copy in the client | What the browser ends up with                                                        |
| --------------------------- | ------------------------------------------------------------------------------------ |
| Project URL                 | `http://server:8080/dwa/redirector/?urn=urn:rational::1-48beda447cfb0c27-P-0000500d` |
| Folder URL                  | `http://server:8080/dwa/redirector/?urn=urn:rational::1-48beda447cfb0c27-F-00000003` |
| Module URL                  | `http://server:8080/dwa/rm/urn:rational::1-48beda447cfb0c27-M-00003c20`              |
| Object URL                  | `http://server:8080/dwa/rm/urn:rational::1-48beda447cfb0c27-O-2-00003c20`            |

All those URLs funnel through _doorsRedirector_; after a short 302 redirect you land in `/dwa/rm/...` or `/dwa/iq/…` depending on the call.

---

## 5. Pseudo-parser (Python)

```python
import re

URN_RE = re.compile(
    r"^urn:(?:rational|telelogic)::1-(?P<db>[0-9a-f]{16})-"
    r"(?P<kind>[A-Z])-(?P<rest>.+)$"
)

def parse_dwa_urn(urn: str):
    m = URN_RE.match(urn)
    if not m:
        raise ValueError("Not a DWA URN")
    dbid = m.group('db')
    kind = m.group('kind')
    parts = m.group('rest').split('-')
    if kind == 'O':
        abs_no, mod_key = parts[0], parts[1]
        return dict(dbid=dbid, kind='object',
                    object_no=int(abs_no), module_key=int(mod_key, 16))
    else:
        key = parts[0]
        return dict(dbid=dbid, kind=kind, key=int(key, 16))
```

Feed the string, get a dictionary ready for your OSLC library or redirector builder.

---

## 6. Relationship to GUIDs

- **Database & container mapping**
  `db-id` (URN) ↔ the same 16-hex field in the GUID.
  Module key & folder key values are identical across both encodings.
- **Views** live in GUIDs (`type = 1F`) but are only query-parameters in URNs.
- **Baselines** are _never_ encoded in the URN itself – instead DWA adds
  `&baseline=<id>` (>= 9.6) or `&version=<nr>` (<= 9.5) to the URL.

---

## 7. Quick reference

| Piece                 | Regex            | Notes                 |                                       |
| --------------------- | ---------------- | --------------------- | ------------------------------------- |
| Entire URN            | \`^urn:(rational | telelogic)::1-…$\`    | Two vendor spellings accepted by DWA. |
| Database id           | `[0-9a-f]{16}`   | Always lowercase hex. |                                       |
| Key (module/folder/…) | `[0-9a-f]{8}`    | Leading zeros matter. |                                       |
| Object number         | `\d+`            | Decimal, no padding.  |                                       |

---

## 8. See also

- IBM Doc **“Identifying the database URN”** – shows the `ers-…` form. ([ibm.com][1])
- IBM Support **“Opening DOORS URL fails”** – sample `-P-` URL. ([ibm.com][2])
- Jazz-forum **“DOORS URL in Word”** – sample `-F-` folder link. ([jazz.net][3])
- IBM Docs **“DOORS as an OSLC service provider”** – module URN with `-M-` and nested paths. ([ibm.com][4])
- Jazz-forum **“DOORS URL redirection loop”** – object URN with `-O-`. ([jazz.net][5])

---

### Drop-in summary

- `urn:rational::1-<db>-P-…` → Project
- `urn:rational::1-<db>-F-…` → Folder
- `urn:rational::1-<db>-M-…` → Formal module
- `urn:rational::1-<db>-O-<absNo>-<modKey>` → Single requirement object
- Use `&view=<key>` for views and `&baseline=<id>` for baselines.

Happy linking!

[1]: https://www.ibm.com/docs/SSYQBZ_9.7.2/com.ibm.rational.dwa.install.doc/topics/t_identifyurn.html "Identifying the URN in IBM Engineering Requirements Management DOORS - Web Access"
[2]: https://www.ibm.com/support/pages/node/284729/stub "Opening DOORS URL in web browser fails with page cannot be found error"
[3]: https://jazz.net/doors-general/html/1344%20-%20DOORS%20URL%20in%20Word.html "DOORS URL in Word"
[4]: https://www.ibm.com/docs/SSYQBZ_9.7.1/com.ibm.doors.install.doc/topics/r_doors_provider.html "DOORS as an OSLC service provider"
[5]: https://jazz.net/doors-admin/html/61%20-%20DOORS%20URL%20Redirection%20Loop.html "DOORS URL Redirection Loop"
