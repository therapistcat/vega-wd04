# Mumbai Smart Civic Portal

End-to-end civic issue reporting and resolution platform for Mumbai, built with FastAPI, MongoDB, React, and an integrated ML detection pipeline.

This repository contains:
- Citizen-facing complaint workflows (reporting, upvotes, progress, heatmaps, notifications, nearby issue discovery)
- Authority workflows (priority queue, impact-based recommendations, status actions, resolution with image proof)
- NGO workflows (requesting issues, assignment sync, progress updates, resolution tracking)
- AI-assisted complaint interactions (tool-calling agent)
- Tamper-evident blockchain complaint anchoring + transparency audit ledger
- YOLO-based garbage and pothole detection/training pipeline

## Why this project

Mumbai-scale civic operations require:
- Fast reporting from citizens
- Clear routing to responsible departments
- A single source of truth for issue status across citizen, NGO, and authority views
- Prioritization based on urgency and public signal (upvotes)
- Transparent decision support for authorities based on impact and public reach
- Traceable closure evidence from authorities
- Spatial intelligence for hotspot planning

This implementation is Mumbai-first (wards, landmarks, heatmap behavior, complaint flow), but designed to be adapted to other cities.

## Core Features

### Citizen
- Register/login with JWT authentication
- Submit complaint with mandatory image evidence
- Landmark-first complaint flow (coordinates optional)
- Live geolocation capture from browser
- AI image verification via `/detect`
- Department routing and priority score assignment
- Community feed with upvote ranking and time decay
- Area/ward report search + detailed modal view
- Progress dashboard with trend, badges, and recent reports
- Daily "Most Important Fix Today" card from DB
- Heatmap from MongoDB-backed spatial analytics
- Interactive map clicks that fetch nearby issues within a chosen radius
- Marker clustering, colored issue pins, and nearby-issues navigation dashboard
- Notifications/announcements with backend fallback behavior
- Blockchain ledger view and complaint verification

### Authority/Admin
- Role-protected authority login with rank code validation
- Ranked complaint queue based on urgency + upvotes + freshness
- Explainable impact engine with impact score, affected people, priority level, and recommendation text
- Top recommended actions panel for high-impact fixes
- Quick status actions from dashboard (Open/In Progress/Resolved)
- Resolve workflow with mandatory fixed-work image when status = Resolved
- Spatial analytics dashboard with heatmap
- Full complaint listing and filtering
- Blockchain transparency ledger page with chain verification and issue filtering

### NGO
- NGO-specific login and workspace
- Request-to-assist flow for open complaints
- Approved assignment sync directly into `complaints`
- Assigned issue dashboard backed by `complaints` as the single source of truth
- Progress timeline updates that reflect globally in citizen and admin views
- NGO-driven issue resolution with synced complaint state and audit logging

### Backend intelligence
- Duplicate detection window by distance + time
- ST-DBSCAN style clustering for duplicate groups
- Intensity scoring for heatmap points
- Nearby-issues geospatial query endpoint for map exploration
- Impact engine that combines duplicates, population, severity, and engagement
- Rule-based + optional external ML triage for department prediction
- AI tool-calling endpoint for complaint creation/status/summary tasks
- Vapi webhook ingestion with token protection
- Blockchain anchoring and tamper verification
- Append-only transparency audit ledger for complaint lifecycle events

## Architecture

```text
Frontend (React + Vite)
  -> /api/*, /static/* proxied by Vite
Backend (FastAPI)
  -> MongoDB (users, complaints, announcements, ngo_requests, vapi_events, blockchain_ledger)
  -> Detection Service (YOLO model loaded from app/ml_models/best.pt)
  -> Blockchain Transparency Layer (SHA-256 audit chain + verification)
  -> Impact Engine (duplicate count + ward population + severity + engagement)
  -> AI Agent (OpenAI-compatible chat/completions + tool calls)
```

## Repository Structure

```text
mumbai-smart-civic/
  backend/
    app/
      api/v1/              # auth, citizen, admin, detection, blockchain, vapi
      blockchain/          # transparency audit chain internals
      ai/                  # agent route + callable tools
      core/                # settings, DB, security
      models/              # complaint/user model helpers
      schemas/             # request/response schemas
      services/            # detection, spatial, duplicate, blockchain, etc.
      static/uploads/      # user-uploaded complaint/fix images
    ml_engine/             # triage + utility ML modules
    scripts/               # seed data, model training, tunnel helpers
    data/, ml_data/, runs/ # datasets, training outputs, model artifacts
    requirements.txt
  frontend/
    src/
      pages/
        citizen/           # dashboard, progress, heatmap, notifications, ledger
        admin/             # authority dashboard, resolve, analytics, blockchain ledger
        ngo/               # NGO dashboard, requests, assigned work
        shared/            # cross-role pages such as nearby issue explorer
      components/          # layout, map, heat layer, UI components
      utils/api.js         # axios client with JWT interceptors
    package.json
  README.md
```

## Tech Stack

### Backend
- FastAPI
- Uvicorn
- Motor + PyMongo
- python-jose + passlib/bcrypt
- httpx
- ultralytics (YOLOv8)
- opencv-python-headless
- albumentations

### Frontend
- React 18
- Vite 5
- React Router 6
- Axios
- Leaflet + react-leaflet + leaflet.heat + leaflet.markercluster
- react-icons

## Local Setup

## 1) Prerequisites
- Python 3.10+ (recommended 3.11+)
- Node.js 18+
- npm 9+
- MongoDB Atlas or local MongoDB instance

## 2) Backend setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create `backend/.env` (template below), then run:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Health check:

```powershell
curl http://127.0.0.1:8000/health
```

## 3) Frontend setup

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

Vite proxy is already configured:
- `/api` -> `http://localhost:8000`
- `/static` -> `http://localhost:8000`

## Environment Variables (`backend/.env`)

Use placeholders, not real secrets:

```env
# Core
MONGODB_URL=mongodb+srv://<user>:<password>@<cluster>/?appName=<app>
MONGODB_DB_NAME=mumbai_smart_civic
JWT_SECRET_KEY=<strong-secret>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Detection
MODEL_PATH=app/ml_models/best.pt
DETECTION_CONF_THRESHOLD=0.35
DETECTION_CONF_THRESHOLD_GARBAGE=0.35
DETECTION_CONF_THRESHOLD_POTHOLE=0.35
DETECTION_IOU_THRESHOLD=0.45
DETECTION_MAX_DET=50
DETECTION_AUTOTAG_THRESHOLD=0.60
DETECTION_AUTOTAG_THRESHOLD_GARBAGE=0.60
DETECTION_AUTOTAG_THRESHOLD_POTHOLE=0.60
DETECTION_STRICT_MODE=false

# Optional external ML triage service
ML_SERVICE_URL=http://localhost:9000
ML_SERVICE_TIMEOUT_SECONDS=2.5

# Duplicate + clustering
DUPLICATE_RADIUS_METERS=50
DUPLICATE_WINDOW_HOURS=48
CLUSTER_SPATIAL_EPS_METERS=120
CLUSTER_TEMPORAL_EPS_HOURS=36
CLUSTER_MIN_SAMPLES=2

# AI agent
OPENAI_API_KEY=<openai-key>
OPENAI_API_BASE=https://api.openai.com/v1
AI_AGENT_MODEL=gpt-4o-mini
AI_AGENT_TEMPERATURE=0.2
AI_AGENT_TIMEOUT_SECONDS=30
AI_AGENT_MAX_TOOL_ROUNDS=3

# Vapi webhook token
VAPI_SERVICE_TOKEN=<shared-static-token>

# Authority codes
AUTHORITY_CODE_INSPECTOR=MUM-INS-1101
AUTHORITY_CODE_WARD_OFFICER=MUM-WARD-2202
AUTHORITY_CODE_DEPUTY_COMMISSIONER=MUM-DEP-3303
AUTHORITY_CODE_COMMISSIONER=MUM-COM-4404

# Authority ACL levels
AUTHORITY_MIN_LEVEL_LIST=1
AUTHORITY_MIN_LEVEL_STATUS_UPDATE=2
AUTHORITY_MIN_LEVEL_SPATIAL_ANALYTICS=3

# Optional seed defaults
SEED_AUTHORITY_NAME=Vega Authority
SEED_AUTHORITY_EMAIL=authority@example.com
SEED_AUTHORITY_PASSWORD=Authority@12345
SEED_AUTHORITY_RANK=commissioner
SEED_CITIZEN_NAME=Vega Citizen
SEED_CITIZEN_EMAIL=citizen@example.com
SEED_CITIZEN_PASSWORD=Citizen@12345
```

## Seed Demo Data

```powershell
cd backend
python scripts/seed_data.py
```

Seed includes:
- authority user
- citizen user
- NGO user
- sample complaints
- sample announcements

## Frontend Routes

### Public
- `/` Login
- `/register` Register

### Citizen
- `/citizen/dashboard`
- `/citizen/progress-dashboard`
- `/citizen/my-complaints`
- `/citizen/heatmap`
- `/citizen/notifications`
- `/citizen/blockchain-ledger`

### Shared Authenticated
- `/issues/nearby`

### NGO
- `/ngo/dashboard`
- `/ngo/available-issues`
- `/ngo/my-requests`
- `/ngo/assigned-issues`

### Authority/Admin
- `/admin/dashboard`
- `/admin/all-complaints`
- `/admin/blockchain-ledger`
- `/admin/resolve`
- `/admin/analytics`
- `/admin/ngo-requests`

## API Overview

Base prefix: `/api/v1`

### Auth
- `POST /auth/register`
- `POST /auth/register/authority`
- `POST /auth/login`
- `GET /auth/me`

### Citizen
- `GET /c/departments`
- `GET /c/announcements`
- `GET /c/notifications`
- `POST /c/complaints`
- `GET /c/complaints/me`
- `GET /c/my-complaints`
- `GET /c/complaints/feed`
- `POST /c/complaints/{complaint_id}/upvote`
- `GET /c/spatial-analytics`
- `GET /c/heatmap`
- `GET /c/reports/by-area`
- `GET /c/reports/priority-today`
- `GET /c/reports/{complaint_id}`
- `GET /c/status/{complaint_id}`
- `GET /c/progress/overview`

### Nearby Issues
- `GET /issues/nearby`

### NGO
- `POST /ngo-requests`
- `GET /ngo-requests`
- `GET /ngo-requests/me`
- `GET /ngo-requests/available-issues`
- `PATCH /ngo-requests/{request_id}`
- `GET /ngo/assigned-issues`
- `PATCH /ngo/issues/{issue_id}/progress`
- `GET /ngo/issues/{issue_id}/updates`

### Authority
- `GET /a/complaints`
- `PATCH /a/complaints/{complaint_id}/status`
- `POST /a/complaints/{complaint_id}/status-with-proof`
- `GET /a/spatial-analytics`

### Detection
- `POST /detect`

### AI Agent
- `POST /ai/query`

### Blockchain
- `GET /blockchain/chain`
- `GET /blockchain/ledger`
- `GET /blockchain/verify`
- `GET /blockchain/issue/{id}`
- `POST /blockchain/anchor/{complaint_id}`
- `GET /blockchain/verify/{complaint_id}`
- `POST /blockchain/anchor-all`

### Vapi
- `GET /vapi/ping`
- `POST /vapi/webhook`

## Data Model Notes

### Complaint lifecycle
- Initial status: `Open`
- Valid statuses: `Open`, `In Progress`, `Resolved`
- Complaint state is the single source of truth for status, NGO assignment, progress, and resolution
- `ngo_requests` stores request workflow metadata only (pending/approved/rejected + NGO/issue relation)
- NGO assignment is denormalized into complaint fields (`assigned_ngo_id`, `assigned_ngo_name`) for faster reads
- NGO progress is stored in `complaints.progress_status` and `complaints.progress_updates`
- Resolution proof image is mandatory when resolved through `status-with-proof`
- Upvotes are user-specific toggles with `upvoted_by` tracking
- Authority responses also include impact-engine fields such as `impact_score`, `affected_people`, and `recommendation_text`

### Storage and indexing
Collections:
- `users`
- `complaints`
- `announcements`
- `ngo_requests`
- `vapi_events`
- `blockchain_ledger`

Indexes include:
- unique `users.email`
- 2dsphere `complaints.location`
- complaint indexes on time/user/department/status/upvotes/assigned NGO
- unique sparse `blockchain_ledger.complaint_id`
- audit-ledger indexes on `chain_type + index`, `chain_type + timestamp`, and `chain_type + data.issue_id`

## Real-time and Ranking Behavior

Several pages refresh every 15s:
- Citizen dashboard
- Progress dashboard
- Heatmap
- Notifications
- Authority dashboard

Ranking behavior (implemented in backend/frontend):
- Fresh complaints get temporary boost
- Older vote influence decays over time
- Status-based weighting adjusts urgency
- Daily top-priority report is selected from today non-resolved complaints
- Admin decisioning uses an explainable impact score built from duplicate count, ward population, severity, and engagement

If no daily priority exists for the day, API/UI message is:
- `No reports detected today.`

## ML and Detection Pipeline

## Runtime detection
- Model loads once at startup from `MODEL_PATH`
- Class-specific confidence thresholds are supported
- Auto-tag thresholds can be global or per-class
- Strict mode can reject complaints when model confidence is insufficient

Detection endpoint constraints:
- image only
- max file size 8 MB

## Training command

```powershell
cd backend
python scripts/train_detection_model.py `
  --garbage-yolo-dir ml_data/garbage_detection `
  --epochs 80 `
  --imgsz 896 `
  --batch 8 `
  --cache
```

What training script does:
- merges supported datasets (YOLO/COCO/VOC sources)
- normalizes labels into two classes (`garbage`, `pothole`)
- deduplicates exact duplicates
- split generation (train/val/test)
- augmentation (rain/quality/minority balancing)
- YOLOv8 training + val/test evaluation
- best weight copy to `app/ml_models/best.pt`
- optional auto-tag threshold calibration output

## Data recommendations to improve garbage recognition
- 300 to 500 Mumbai garbage-positive images across wards
- 300 to 500 hard negatives (clean roads, puddles, leaves, shadows, debris)
- include low-light, rain, blur, compression, off-angle mobile captures
- balanced object scales (small/medium/large garbage clusters)
- consistent YOLO bounding boxes

## AI Agent Details

`POST /ai/query` supports tool-calling for:
- creating complaint from natural language
- fetching user complaints
- checking complaint status
- summarizing heatmap hotspots

Context includes user role and optional coordinates.

## NGO Workflow Details

- NGOs can browse open complaints and submit assistance requests
- Authorities approve or reject NGO requests
- On approval, the assigned NGO is written directly into the complaint document
- NGO progress updates and NGO resolutions update the complaint itself, so citizen dashboards, admin dashboards, analytics, and feeds stay in sync
- Assigned NGO work is read from `complaints`, not reconstructed from `ngo_requests`

## Nearby Issue Exploration

- Clicking the citizen heatmap fetches nearby issues through MongoDB geospatial search
- Nearby complaints are shown as color-coded markers with Leaflet clustering
- Marker popups show status, NGO assignment, and a link to the nearby-issues dashboard
- `/issues/nearby` lists nearby complaints with distance and priority-based sorting

## Authority Decision AI Assistant

- Lightweight scoring-based decision engine, no heavy model training
- Computes:
  - impact score
  - estimated affected people
  - priority label (`LOW`, `MEDIUM`, `HIGH`)
  - recommendation text
- Inputs used:
  - duplicate count from clustering signals
  - ward population mapping
  - category severity weight
  - upvotes / engagement
- Output is shown directly in the admin dashboard and used to sort recommended actions

## Blockchain Ledger Details

- Internal SHA-256 blockchain ledger in MongoDB (no Solidity/MetaMask)
- Genesis block + chain linking + proof-of-work fields
- Can anchor single complaint or all current user complaints
- Verification API checks anchored snapshot integrity vs current state

## Blockchain Transparency Layer

Purpose:
- Prevent tampering of important civic actions
- Preserve accountability across citizen, NGO, and authority workflows
- Give admins a transparent audit trail for issue lifecycle decisions

How it works:
- Important events are written as append-only audit blocks into MongoDB collection `blockchain_ledger`
- Each audit block stores structured event data, the previous block hash, and a SHA-256 hash of its own contents
- A dedicated verification endpoint walks the audit chain and detects broken hash links or modified records

Events tracked:
- Complaint creation
- NGO assignment approval
- Issue progress updates
- Issue resolution

API endpoints:
- `GET /blockchain/ledger`
- `GET /blockchain/verify`
- `GET /blockchain/issue/{id}`

Tech used:
- SHA-256 hashing
- MongoDB append-only ledger storage
- FastAPI route integration

Demo explanation:
- If any stored block data or previous hash is modified manually in MongoDB, the verification step fails
- The admin blockchain ledger page highlights this state with an invalid/tampering warning so the break is visible immediately

## Vapi Integration

- Token-protected endpoints using `VAPI_SERVICE_TOKEN`
- Incoming payloads are stored in `vapi_events`
- Useful for hotline/call workflow telemetry

## Tunnel Scripts

Run backend with public tunnel:

```powershell
cd backend
powershell -ExecutionPolicy Bypass -File .\scripts\run_backend_with_devtunnel.ps1
```

Or ngrok:

```powershell
cd backend
powershell -ExecutionPolicy Bypass -File .\scripts\run_backend_with_ngrok.ps1
```

## Build/Check Commands

Backend import/compile check:

```powershell
cd backend
python -m compileall app scripts
```

Frontend production build:

```powershell
cd frontend
npm run build
```

## Troubleshooting

### `Database is not connected`
- Verify `backend/.env` exists
- Confirm `MONGODB_URL` and `MONGODB_DB_NAME`
- Check backend startup logs and `/health`

### Mongo auth failed
- Re-check Mongo username/password
- URL-encode special password characters
- Ensure IP allowlist and DB user permissions

### Images not visible
- Ensure backend is running (`/static` mount active)
- Confirm stored path begins with `/static/uploads/`

### AI agent unavailable
- Set valid `OPENAI_API_KEY`
- Ensure `OPENAI_API_BASE` reachable

### Vapi unauthorized
- Send header: `Authorization: Bearer <VAPI_SERVICE_TOKEN>`

### Detection not classifying well
- Verify model exists at `MODEL_PATH`
- Recalibrate `DETECTION_CONF_*` and `DETECTION_AUTOTAG_*`
- Add hard negatives and Mumbai-context images, then retrain

## Security and Repo Hygiene

- Never commit real secrets from `.env`
- Rotate credentials if leaked
- Keep generated artifacts out of git where possible (`node_modules`, local caches, large temp outputs)
- Uploaded evidence images may contain sensitive content; secure storage and access controls are recommended for production

## Known Notes

- `docker-compose.yml` currently exists but is empty
- Root repository currently includes many generated artifacts and local caches; production hardening should clean these paths and add strict ignore rules

## License

No explicit license file is currently present in the repository.
Add a `LICENSE` file before public/commercial distribution.
