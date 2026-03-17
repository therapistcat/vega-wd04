# Potential Merge Conflicts Report - AI Clustering Integration

This document outlines all files modified during the AI Duplicate Issue Clustering integration and identifies specific areas where conflicts may arise if integrated with other features or branches.

## 1. Backend Conflicts

### backend/app/api/v1/citizen.py
- **Area:** `submit_complaint` endpoint.
- **Change:** Integrated synchronous clustering logic using `cluster_process_issue` before returning the response. Moved clustering from background to foreground.
- **Risk:** High. Any changes to the complaint submission flow or response schema will likely conflict here.

### backend/app/main.py
- **Area:** Router registration.
- **Change:** Added `app.include_router(clusters.router, prefix=settings.api_v1_prefix)`.
- **Risk:** Low. Standard conflict if multiple branches add routers at the same line.

### backend/app/models/complaint_model.py
- **Area:** `build_complaint_document` and `serialize_complaint`.
- **Change:** Added `cluster_id` and `is_duplicate` fields.
- **Risk:** Medium. Any other schema updates to complaints will touch these same functions.

### backend/app/api/v1/vapi.py
- **Area:** Vapi webhook processing.
- **Change:** Integrated clustering logic for call-based complaints.

---

## 2. Frontend Conflicts

### frontend/src/pages/citizen/Dashboard.jsx
- **Area:** `handleSubmit` function and the bottom of the component (Toast rendering).
- **Change:** Added logic to handle `is_duplicate` API response and display a toast linked to the cluster page.
- **Risk:** High. This is a primary UI file; any other dashboard features will likely touch similar state or JSX blocks.

### frontend/src/App.jsx
- **Area:** Route definitions.
- **Change:** Added `/citizen/cluster/:clusterId` route.
- **Risk:** Low. Standard conflict if multiple routes are added simultaneously.

### frontend/src/pages/admin/AllComplaints.jsx
- **Area:** Complaints table (thead and tbody).
- **Change:** Added "Cluster" column and link to cluster details.
- **Risk:** Medium. Any other admin table enhancements will conflict in the JSX mapping.

## 3. Environment & Dependencies

### backend/requirements.txt
- **Update Required:** `scikit-learn` has been added to ensure the background task and TF-IDF logic function.

---
**Recommendation:** Perform a rebase or a careful manual merge of the above files, prioritizing the new clustering fields in responses to avoid breaking the Frontend Duplicate Alert UI.
