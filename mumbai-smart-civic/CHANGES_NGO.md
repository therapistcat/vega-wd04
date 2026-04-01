# NGO Integration — Full Changes Document

> **Purpose**: This document is for team handoff and PR review.
> It lists every file changed, what changed inside it, which areas are likely merge conflict zones,
> and how the NGO feature integrates with the rest of the system.

---

## Summary of Feature

A new **NGO Partner role** was added to the platform, enabling NGOs to:
1. Log in with a real JWT (provisioned via `/auth/mock-ngo-login`)
2. Browse open civic complaints
3. Send "Request to Assist" on any complaint
4. Track their own requests and their approval status

Admins/Authorities can:
- View all incoming NGO assistance requests
- Approve or Reject them
- See live NGO request counts and assist status on every complaint in the All Complaints view

---

## Files Changed

### BACKEND — New Files

| File | Purpose |
|---|---|
| `backend/app/models/ngo_request_model.py` | MongoDB document builder and serializer for NGO requests |
| `backend/app/schemas/ngo_request_schema.py` | Pydantic schemas: `NGORequestCreate`, `NGORequestUpdate`, `NGORequestResponse` |
| `backend/app/api/v1/ngo_requests.py` | FastAPI router with all 5 NGO-related endpoints |

---

### BACKEND — Modified Files

#### `backend/app/schemas/user_schema.py`
**What changed:**
- Added `ngo` to `UserRole` enum
- Added `ngo` to `LoginAs` enum

**⚠️ Merge Conflict Risk — HIGH**
Any teammate who added a new role, updated `LoginAs`, or expanded `UserRole` will conflict here.
```diff
  class UserRole(str, Enum):
      citizen = "citizen"
      authority = "authority"
      admin = "admin"
+     ngo = "ngo"

  class LoginAs(str, Enum):
      citizen = "citizen"
      authority = "authority"
+     ngo = "ngo"
```

---

#### `backend/app/api/v1/auth.py`
**What changed:**
- Added handling for `LoginAs.ngo` in the `login_user` endpoint
- Added a new `POST /auth/mock-ngo-login` endpoint that auto-provisions a demo NGO user and returns a real JWT

**⚠️ Merge Conflict Risk — MEDIUM**
Conflicts possible if a teammate added a new login flow or touched the `login_user` function body.

```diff
  # In login_user():
+     if payload.login_as == LoginAs.ngo:
+         if role != "ngo":
+             raise HTTPException(status_code=403, detail="This account is not an NGO account")

+ @router.post("/mock-ngo-login", response_model=TokenResponse)
+ async def mock_ngo_login(db: AsyncIOMotorDatabase = Depends(get_database)) -> TokenResponse:
+     ...
```

---

#### `backend/app/core/security.py`
**What changed:**
- Added `require_ngo()` dependency function (similar to `require_authority`)

**⚠️ Merge Conflict Risk — LOW**
Only added new function at end of file. Will conflict only if teammate added code at the same location.

```diff
+ def require_ngo():
+     async def ngo_dependency(current_user = Depends(get_current_user)):
+         if current_user.get("role") != "ngo":
+             raise HTTPException(status_code=403, detail="NGO access required")
+         return current_user
+     return ngo_dependency
```

---

#### `backend/app/core/database.py`
**What changed:**
- Added indexes on `ngo_requests` collection (`issue_id`, `ngo_id`) inside `init_indexes()`

**⚠️ Merge Conflict Risk — LOW**
Will conflict only if a teammate also added new index creation calls in `init_indexes()`.

---

#### `backend/app/schemas/complaint_schema.py`
**What changed:**
- Added 3 new optional fields to `ComplaintResponse`:

```diff
+ ngo_request_count: int = 0
+ ngo_assisting: bool = False
+ assistant_name: str | None = None
```

**⚠️ Merge Conflict Risk — MEDIUM**
Any teammate who added fields to `ComplaintResponse` will conflict at the field definition block.

---

#### `backend/app/api/v1/admin.py`
**What changed:**
- `list_all_complaints` endpoint now also queries `ngo_requests` collection and:
  - Counts NGO requests per complaint → `ngo_request_count`
  - Marks if an NGO is approved to assist → `ngo_assisting`
  - Stores the assisting NGO's name → `assistant_name`
- Imports added: `NGO_REQUESTS_COLLECTION` from `ngo_request_model`

**⚠️ Merge Conflict Risk — HIGH**
This is the most risky file. Changes are inside `list_all_complaints`, which is a central endpoint.
If a teammate modified the complaint list query, sort logic, or serialization, this will conflict.

**Integration Note**: The changes here are **additive** — the original sort logic and serialization are preserved. NGO metadata is injected after the existing `serialize_complaint()` call. As long as teammates didn't change the loop at lines ~113–120, merging should be clean.

---

#### `backend/app/main.py`
**What changed:**
- Imported `ngo_requests` router from `app.api.v1`
- Registered router: `app.include_router(ngo_requests.router, prefix=settings.api_v1_prefix)`

**⚠️ Merge Conflict Risk — MEDIUM**
Imports and `include_router` calls are often touched simultaneously. Conflict possible if multiple router additions happen in the same PR.

---

### FRONTEND — New Files

| File | Purpose |
|---|---|
| `frontend/src/pages/ngo/Dashboard.jsx` | NGO stats dashboard |
| `frontend/src/pages/ngo/AvailableIssues.jsx` | Browse open complaints + "Request to Assist" |
| `frontend/src/pages/ngo/MyAssistanceRequests.jsx` | NGO's own submitted requests and their status |
| `frontend/src/pages/admin/NGORequests.jsx` | Admin panel for approving/rejecting NGO requests |

---

### FRONTEND — Modified Files

#### `frontend/src/context/NGOContext.jsx`
**What changed (full rewrite from mock to real API):**
- Added `import api from '../utils/api'` ← **this was missing and was the root cause of login logouts**
- `fetchRequests()` now calls real backend (`/ngo-requests/me` or `/ngo-requests` based on role)
- `addRequest()` now calls `POST /ngo-requests`
- `updateRequestStatus()` now calls `PATCH /ngo-requests/{id}`
- Role guard: won't call API if role is not `ngo`, `authority`, or `admin` (prevents 401s for citizens)
- Errors in `fetchRequests` are caught silently to prevent page-level logouts

**⚠️ Merge Conflict Risk — HIGH**
This file was previously fully mock-data driven. Any teammate who also refactored the context or added state will conflict.

---

#### `frontend/src/pages/Login.jsx`
**What changed:**
- "NGO" Quick Fill button now calls `handleNGOQuickLogin()` instead of filling form fields
- `handleNGOQuickLogin()` directly calls `POST /auth/mock-ngo-login` → gets real JWT → navigates to `/ngo/dashboard`
- `handleSubmit()` also handles `loginAs === 'ngo'` branch using the real backend
- Removed mock token generation (`'mock_ngo_token_' + Date.now()`)

**⚠️ Merge Conflict Risk — MEDIUM**
Any teammate who touched `handleSubmit`, the quick fill buttons, or the role-select options will conflict.

---

#### `frontend/src/utils/api.js`
**What changed:**
- Global 401 interceptor now guards against logout loops:
  - Only clears token + redirects if a token actually exists
  - Prevents spurious logouts from background fetches on the login page

**⚠️ Merge Conflict Risk — LOW**
The interceptor block is small and isolated. Conflict only if teammate also modified the 401 handler.

---

#### `frontend/src/App.jsx`
**What changed:**
- Added imports for `NGODashboard`, `AvailableIssues`, `MyRequests`
- Added `/ngo/*` route block with `ProtectedRoute allowedRole="ngo"`
- Added sub-routes: `dashboard`, `available-issues`, `my-requests`

**⚠️ Merge Conflict Risk — HIGH**
`App.jsx` is one of the most frequently touched files in any frontend. Any teammate adding new routes, imports, or modifying `ProtectedRoute` will conflict.

---

#### `frontend/src/components/Sidebar.jsx`
**What changed:**
- Added `ngoLinks` array with sidebar nav items for `Dashboard`, `Available Issues`, `My Requests`
- Added NGO detection: `const isNGO = role === 'ngo'`
- Added `else if (isNGO)` branch for sidebar link selection

**⚠️ Merge Conflict Risk — MEDIUM**
If a teammate added sidebar links for another role or changed the sidebar rendering logic, there may be conflicts.

---

## Integration Points with Other Features

### 1. Complaint Feed (Citizen)
- **Not changed** — citizen complaint feed is completely untouched.
- NGO requests are stored separately in `ngo_requests` collection.
- Citizen's `ComplaintResponse` uses the same schema which now has optional `ngo_request_count` and `ngo_assisting` fields (default 0/false), so existing citizen API responses are **backward compatible**.

### 2. Admin Complaint List (`/a/complaints`)
- **Modified** — now enriches each complaint with NGO metadata.
- The enrichment is done as a second DB query **after** all existing sorting/filtering logic.
- If a teammate extended the admin complaint list (e.g., added filters or new sorting), the integration point is around lines 96–121 in `admin.py` — specifically the `ngo_map` building and serialization loop.

### 3. Authentication System
- **Extended, not modified** — existing login flow for `citizen` and `authority` is unchanged.
- NGO login goes through a dedicated endpoint (`/auth/mock-ngo-login`) to avoid touching existing auth flows.
- JWT token format is the same — just `role: "ngo"` is set in the payload.
- `get_current_user` in `security.py` is unchanged.

### 4. Role-Based Access Control (RBAC)
- `require_ngo()` was added as a new dependency, parallel to `require_authority()`.
- If a teammate is implementing a new role, they should follow the same pattern.
- `require_roles(["ngo"])` is used in the NGO router (same utility pattern as all other roles).

### 5. Upvotes / Duplicate Detection / Spatial Analytics
- **Not touched** — no changes to these systems.
- However, `AvailableIssues` returns real complaint objects which include `priority_score`, `upvotes_count`, and `location` — these are passed through cleanly.

### 6. Blockchain Ledger
- **Not touched** — entirely separate system.

### 7. Emergency Assistant / AI Agent
- **Not touched** — entirely separate system.

---

## Potential Merge Conflict Cheat Sheet

| File | Risk | Key area of conflict |
|---|---|---|
| `user_schema.py` | 🔴 HIGH | `UserRole` and `LoginAs` enum values |
| `admin.py` | 🔴 HIGH | `list_all_complaints` function body |
| `App.jsx` | 🔴 HIGH | Route imports + route tree structure |
| `NGOContext.jsx` | 🔴 HIGH | Entire file (was fully mocked, now real) |
| `auth.py` | 🟠 MEDIUM | `login_user` function + new endpoint at end |
| `complaint_schema.py` | 🟠 MEDIUM | `ComplaintResponse` fields |
| `main.py` | 🟠 MEDIUM | Router import + `include_router` call |
| `Login.jsx` | 🟠 MEDIUM | `handleSubmit` and quick fill buttons |
| `Sidebar.jsx` | 🟠 MEDIUM | `ngoLinks` and role detection |
| `security.py` | 🟡 LOW | New function at end of file |
| `database.py` | 🟡 LOW | `init_indexes` additions |
| `api.js` | 🟡 LOW | 401 interceptor body |

---

## How to Merge Safely

1. **Merge `user_schema.py` first** — it's a dependency of everything else. Ensure both `UserRole.ngo` and `LoginAs.ngo` are present.
2. **Merge `complaint_schema.py` next** — add the 3 NGO fields to `ComplaintResponse` if not already there. They all have defaults so they won't break existing responses.
3. **Merge `security.py`** — just append `require_ngo()` if not already there.
4. **Merge `admin.py`** — the NGO enrichment block (lines 96–121) can be inserted after the existing `complaints.sort(...)` call and before `return response_list`.
5. **Merge `auth.py`** — add `LoginAs.ngo` handling in `login_user`, then add the `mock-ngo-login` endpoint.
6. **Merge `main.py`** — add `ngo_requests` to the import and `include_router` calls.
7. **Merge frontend last** — `App.jsx`, `Sidebar.jsx`, `Login.jsx`, `NGOContext.jsx` in that order.

---

## New Collections in MongoDB

| Collection | Indexes |
|---|---|
| `ngo_requests` | `{ issue_id: 1 }`, `{ ngo_id: 1 }` |

No changes to existing collections or their schemas.

---

## Demo Login

| Role | How to login |
|---|---|
| **NGO** | Click "NGO" in Quick Fill on login page — auto-logs-in as "NGO Sahayata" |
| **Authority** | Quick Fill → Authority (uses `MUM-COM-4404` code) |
| **Citizen** | Quick Fill → Citizen |
