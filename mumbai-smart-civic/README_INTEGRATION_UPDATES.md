# Mumbai Smart Civic Portal Integration Updates

This document summarizes the implementation updates added for:

1. Vapi call ingestion -> complaint creation flow
2. NGO -> Authority assistance request flow

## 1. Vapi Call Integration

### Goal

Make Vapi webhook events fully usable inside the civic complaint system so that:

- Vapi webhook payloads are stored in MongoDB
- End-of-call reports are converted into complaints
- Call-created complaints appear in citizen/admin views
- Call-created complaints are tagged with `source: "call"`
- Duplicate complaint creation is prevented per `callId`
- Clustering remains active for call-created complaints

### Backend Changes

#### File: `backend/app/api/v1/vapi.py`

Added and fixed:

- Stores every webhook payload in MongoDB collection `vapi_events`
- Extracts:
  - `callId`
  - event type
  - summary
  - transcript
- Uses shared Vapi auth via `verify_vapi_token`
- Uses the configured Mongo database instead of a hardcoded DB name
- Only creates a complaint when:
  - `eventType == "end-of-call-report"`
  - `callId` exists
  - complaint for that `callId` does not already exist
- Builds complaint with:
  - `source = "call"`
  - `is_verified = False`
  - `reported_by_name = "Voice Hotline"`
  - `call_metadata` including `call_id`, summary, transcript, phone number, duration, parsed details
- Runs clustering before finalizing complaint metadata:
  - `cluster_id`
  - `is_duplicate`
- Triggers background spatial refresh tasks:
  - `run_st_dbscan_clustering`
  - `update_intensity_scores`

#### File: `backend/app/services/call_service.py`

Improved parsing logic so call data can be converted into structured complaint fields:

- Detects:
  - problem
  - location
  - details
  - category
  - ward
- Builds a cleaner complaint description from parsed summary/transcript
- Falls back safely when fields are missing

#### File: `backend/app/models/complaint_model.py`

Adjusted serialization for call-created complaints:

- Handles complaints with `user_id = None`
- Prevents serialization issues in admin/citizen views for hotline-created records

### Frontend Changes

#### File: `frontend/src/pages/citizen/Dashboard.jsx`

Added:

- `📞 Reported via Call` tag on call-created complaints
- `View Details` action on feed cards
- Call-source label inside area reports and daily priority sections

#### File: `frontend/src/components/ReportDetailsModal.jsx`

Extended call complaint modal details:

- Shows call location when available
- Shows parsed summary
- Shows parsed details
- Shows transcript
- Keeps caller metadata and call ID visible

#### File: `frontend/src/pages/admin/AllComplaints.jsx`

Added:

- `Source` column with `Web` / `Call`
- Safer handling for complaints without a linked user account

### Result

Calls now flow like this:

`Vapi webhook -> vapi_events -> complaint creation -> clustering -> dashboard/admin visibility`

### Manual Verification Steps

1. Make a Vapi call
2. Confirm event exists:

```js
db.vapi_events.find().sort({ receivedAt: -1 })
```

3. Confirm complaint exists:

```js
db.complaints.find({ source: "call" })
```

4. Confirm dashboard/admin UI shows the complaint and tags it as call-based

### Files Updated for Vapi Work

- `backend/app/api/v1/vapi.py`
- `backend/app/services/call_service.py`
- `backend/app/models/complaint_model.py`
- `frontend/src/pages/citizen/Dashboard.jsx`
- `frontend/src/components/ReportDetailsModal.jsx`
- `frontend/src/pages/admin/AllComplaints.jsx`

## 2. NGO -> Authority Assistance Request Flow

### Goal

Make the NGO request flow fully functional so that:

- NGO can click `Request to Assist`
- Request is sent to backend
- Request is stored in MongoDB `ngo_requests`
- Admin/Authority can view requests
- Admin/Authority can approve or reject requests
- UI updates correctly after submission and review

### Backend Changes

#### File: `backend/app/api/v1/ngo_requests.py`

Fixed and aligned the API flow:

- `POST /ngo-requests`
  - restricted to NGO users with `require_ngo()`
  - logs payload and current user for debugging
  - validates `issue_id`
  - verifies complaint exists
  - blocks duplicate requests per NGO + issue
  - stores request in `ngo_requests`
- `GET /ngo-requests/me`
  - returns NGO user’s own requests
- `GET /ngo-requests`
  - returns all requests for authority/admin review
- `GET /ngo-requests/available-issues`
  - returns open complaints for NGO browsing
- `PATCH /ngo-requests/{request_id}`
  - authority/admin can approve or reject
  - updates `status`
  - updates `updated_at`

Debug logs added:

```python
print("NGO request payload:", payload.model_dump())
print("User:", current_user)
```

#### File: `backend/app/schemas/ngo_request_schema.py`

Adjusted request schema:

- `issue_title` is now optional
- Frontend only needs to send `issue_id`

#### File: `backend/app/models/ngo_request_model.py`

Adjusted document builder:

- accepts optional `issue_title`
- safely stores fallback title text from complaint description

### Frontend Changes

#### File: `frontend/src/context/NGOContext.jsx`

Fixed request handling:

- Sends:

```javascript
await api.post("/ngo-requests", {
  issue_id: issueId
});
```

- Explicitly passes JWT header when creating/updating requests
- Adds frontend debug log:

```javascript
console.log("Sending request", issueId);
```

- Keeps local NGO request state in sync after create/update

#### File: `frontend/src/pages/ngo/AvailableIssues.jsx`

Fixed NGO action flow:

- `Request to Assist` now uses the correct issue identifier
- Handles both `id` and `_id`
- Shows `Request Sent` after success
- Disables duplicate request action when already requested
- Shows `Sending...` while request is in progress
- Displays backend error messages when request fails

#### File: `frontend/src/pages/admin/NGORequests.jsx`

Improved admin review flow:

- Approve button updates request status to `approved`
- Reject button updates request status to `rejected`
- Buttons disable while saving
- UI updates in place after review

#### File: `frontend/src/pages/ngo/MyAssistanceRequests.jsx`

Cleaned request listing:

- Uses backend `/ngo-requests/me` data directly
- Avoids redundant client-side filtering by NGO name

### Result

NGO request flow now works like this:

`NGO clicks request -> backend stores ngo_requests record -> admin sees request -> admin approves/rejects -> UI reflects updated status`

### Manual Verification Steps

1. Login as NGO
2. Open `Available Issues`
3. Click `Request to Assist`
4. Confirm Mongo record exists:

```js
db.ngo_requests.find()
```

5. Login as Admin or Authority
6. Open NGO requests page
7. Approve or reject a request
8. Confirm status changed in MongoDB
9. Confirm complaint-related UI reflects approved NGO assistance

### Files Updated for NGO Flow

- `backend/app/api/v1/ngo_requests.py`
- `backend/app/schemas/ngo_request_schema.py`
- `backend/app/models/ngo_request_model.py`
- `frontend/src/context/NGOContext.jsx`
- `frontend/src/pages/ngo/AvailableIssues.jsx`
- `frontend/src/pages/admin/NGORequests.jsx`
- `frontend/src/pages/ngo/MyAssistanceRequests.jsx`

## Verification Performed

The following checks were run after the changes:

### Backend

```powershell
cd backend
python -m compileall app
```

Result:

- Passed

### Frontend

```powershell
cd frontend
npm run build
```

Result:

- Passed

Note:

- The Vapi complaint storage path was verified against the live configured MongoDB during testing of the latest call.
- NGO flow code was verified structurally through backend compile and frontend production build, but still benefits from a full live role-based click-through test with NGO and Admin accounts.

## Summary

### Completed

- Vapi webhook events stored in MongoDB
- End-of-call reports converted into complaints
- Call complaints tagged with `source: "call"`
- Call complaints visible in dashboard/admin UI
- NGO request creation fixed
- Duplicate NGO requests blocked
- Admin/Authority review endpoints fixed
- NGO/Admin UI state updated correctly

### Recommended Live Test Sequence

1. Make a Vapi call and confirm complaint creation
2. Login as NGO and send a request to assist
3. Confirm request in `ngo_requests`
4. Login as Admin and approve the request
5. Verify the approved request is reflected in complaint/admin views
