# Mumbai Smart Civic Portal

FastAPI + MongoDB + React (Vite) civic complaint platform with:
- role-based JWT auth (citizen/authority/admin)
- geospatial complaints and heatmaps
- upvotes and report discovery
- authority workflow with resolution proof images
- agentic AI (OpenAI-compatible tool-calling)
- Vapi webhook integration
- tamper-evident blockchain ledger (SHA-256 + proof-of-work)
- mobile responsive frontend

This README reflects the current implemented code in:
- `backend/app`
- `backend/scripts`
- `frontend/src`

Mumbai-specific positioning:
- This implementation is intentionally Mumbai-first. Mumbai is one of the largest municipal governance environments, so if this workflow is robust at Mumbai scale, it can be adapted to other cities with minimal structural changes.
- The design uses Mumbai-oriented ward/landmark behavior, local complaint patterns, and city-focused heatmap/reporting flows.

## Live Link (Current Local Tunnel)
Frontend (local devtunnel session):
- `https://lx8nhk32-5173.inc1.devtunnels.ms/`

Note:
- this is a local tunnel URL and may expire when tunnel/session stops.

## What Is Implemented

### 1) Authentication and RBAC
- JWT auth with `python-jose`
- Password hashing with `passlib + bcrypt`
- Roles:
  - `citizen`
  - `authority`
  - `admin`
- Authority login/registration requires rank-specific authority code
- Dependency-based guards:
  - `require_roles(...)`
  - `require_authority(min_level=...)`

Auth routes:
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/register/authority`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`

### 2) Complaint Lifecycle
- Citizen complaint creation supports:
  - mandatory image
  - required `landmark`
  - optional `lat/lng`
  - auto fallback to landmark/city-center when coords missing
- ML department prediction before insert
- duplicate detection:
  - `$near`
  - radius default `50m`
  - window default `48h`
- background tasks:
  - ST-DBSCAN clustering
  - intensity score updates
- upvote toggle per user
- feed ranking with time decay:
  - new complaints boosted temporarily
  - old upvoted issues decay and move down
- voting-based prioritization:
  - both citizens and municipal authorities (authority/admin roles) can upvote
  - this creates community + operations-driven prioritization for urgent issues

Citizen routes:
- `GET /api/v1/c/departments`
- `GET /api/v1/c/announcements`
- `GET /api/v1/c/notifications`
- `POST /api/v1/c/complaints`
- `GET /api/v1/c/complaints/me`
- `GET /api/v1/c/my-complaints` (alias)
- `GET /api/v1/c/complaints/feed`
- `POST /api/v1/c/complaints/{complaint_id}/upvote`
- `GET /api/v1/c/spatial-analytics`
- `GET /api/v1/c/heatmap` (alias)
- `GET /api/v1/c/reports/by-area`
- `GET /api/v1/c/reports/{complaint_id}`
- `GET /api/v1/c/status/{complaint_id}`
- `GET /api/v1/c/progress/overview`

### 3) Authority Workflow
- List all complaints
- Update complaint status
- Mark resolved with proof image upload
- Spatial analytics endpoint

Authority routes:
- `GET /api/v1/a/complaints`
- `PATCH /api/v1/a/complaints/{complaint_id}/status`
- `POST /api/v1/a/complaints/{complaint_id}/status-with-proof`
- `GET /api/v1/a/spatial-analytics`

### 4) Heatmaps and Spatial Analytics
- GeoJSON `Point` storage for complaint location
- 2dsphere index on `complaints.location`
- Aggregated heatmap output only (`lat`, `lng`, `intensity`)
- Frontend Leaflet + `leaflet.heat` integration
- Live refresh cycle on heatmap screen

### 5) Agentic AI (Tool Calling)
- Endpoint: `POST /api/v1/ai/query`
- Model config via env:
  - `OPENAI_API_KEY`
  - `OPENAI_API_BASE`
  - `AI_AGENT_MODEL`
- Tools implemented:
  - `create_complaint(description, landmark, user_name, lat?, lng?)`
  - `get_my_complaints(user_id)`
  - `get_complaint_status(complaint_id)`
  - `get_heatmap_summary(...)`
- Multilingual prompt support (English/Hindi/Marathi)
- Complaint creation flow is landmark-first and lat/lng optional

### 6) Vapi Integration
- Protected by static bearer token dependency (`verify_vapi_token`)
- Routes:
  - `GET /api/v1/vapi/ping`
  - `POST /api/v1/vapi/webhook`
- Webhook events stored in Mongo collection `vapi_events`

### 7) Hotline in Frontend
- Citizen dashboard shows hotline section with click-to-call
- Current number in UI:
  - `+16018043496`
- Designed for call intake path together with Vapi webhook/event flow

### 8) Blockchain Ledger
- No Solidity, no MetaMask, no external blockchain SDK
- SHA-256 chain in Mongo (`blockchain_ledger`)
- Genesis block + previous-hash chain linking + mini PoW
- Complaint anchoring and tamper verification routes:
  - `GET /api/v1/blockchain/chain`
  - `POST /api/v1/blockchain/anchor/{complaint_id}`
  - `GET /api/v1/blockchain/verify/{complaint_id}`
  - `POST /api/v1/blockchain/anchor-all`

### 9) Frontend Integration and Responsiveness
- Frontend and backend integrated via Vite proxy:
  - `/api` -> `http://localhost:8000`
  - `/static` -> `http://localhost:8000`
- Mobile responsiveness improvements are implemented across:
  - dashboard
  - heatmap
  - my complaints
  - sidebar/navbar behavior
  - blockchain ledger page

## Sample Images Note
- The project uses sample images in seeded data (public URLs) for demo records.
- User-uploaded complaint and resolution images are saved under:
  - `backend/app/static/uploads`
- Served by backend static route:
  - `/static/uploads/<filename>`

## Tech Stack
- Backend:
  - FastAPI
  - Motor + PyMongo
  - python-jose
  - passlib/bcrypt
  - httpx
- Frontend:
  - React 18
  - Vite
  - react-router-dom
  - axios
  - react-leaflet + leaflet.heat

## Environment Variables
Create/update `backend/.env`.

Core:
```env
MONGODB_URL=mongodb+srv://<user>:<password>@<cluster>/?appName=<app>
MONGODB_DB_NAME=vega_hackathon
JWT_SECRET_KEY=<strong-secret>
```

Authority codes and seed users:
```env
AUTHORITY_CODE_INSPECTOR=MUM-INS-1101
AUTHORITY_CODE_WARD_OFFICER=MUM-WARD-2202
AUTHORITY_CODE_DEPUTY_COMMISSIONER=MUM-DEP-3303
AUTHORITY_CODE_COMMISSIONER=MUM-COM-4404

SEED_AUTHORITY_NAME=Vega Authority
SEED_AUTHORITY_EMAIL=authority@example.com
SEED_AUTHORITY_PASSWORD=Authority@12345
SEED_AUTHORITY_RANK=commissioner

SEED_CITIZEN_NAME=Vega Citizen
SEED_CITIZEN_EMAIL=citizen@example.com
SEED_CITIZEN_PASSWORD=Citizen@12345
```

AI + Vapi:
```env
OPENAI_API_KEY=<your-openai-key>
OPENAI_API_BASE=https://api.openai.com/v1
AI_AGENT_MODEL=gpt-4o-mini

VAPI_SERVICE_TOKEN=<shared-static-token>
```

Optional tuning:
```env
ML_SERVICE_URL=http://localhost:9000
ML_SERVICE_TIMEOUT_SECONDS=2.5
DUPLICATE_RADIUS_METERS=50
DUPLICATE_WINDOW_HOURS=48
CLUSTER_SPATIAL_EPS_METERS=120
CLUSTER_TEMPORAL_EPS_HOURS=36
CLUSTER_MIN_SAMPLES=2
```

## How To Run (Local)

### 1) Backend
```powershell
cd mumbai-smart-civic/backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Health check:
```powershell
curl http://127.0.0.1:8000/health
```

### 2) Frontend
```powershell
cd mumbai-smart-civic/frontend
npm install
npm run dev
```

Open:
- `http://localhost:5173`

Notes:
- Vite config already proxies `/api` and `/static` to backend port 8000.
- For external frontend deployment without proxy, set `VITE_API_BASE` accordingly.

Integration note (frontend + backend):
- Frontend and backend are fully connected through live API calls and MongoDB persistence for core workflows.
- Complaint feed, reports, heatmaps, progress, blockchain, AI, and webhook flows are data-driven (not static hardcoded UI data).
- Seed data is included only to bootstrap/demo the system quickly.

## Tunnel Scripts

Backend with devtunnel:
```powershell
cd mumbai-smart-civic/backend
powershell -ExecutionPolicy Bypass -File .\scripts\run_backend_with_devtunnel.ps1
```

Backend with ngrok:
```powershell
cd mumbai-smart-civic/backend
powershell -ExecutionPolicy Bypass -File .\scripts\run_backend_with_ngrok.ps1
```

## Seed Data

Run:
```powershell
cd mumbai-smart-civic/backend
python scripts/seed_data.py
```

What it seeds/upserts:
- authority user
- citizen user
- 23 complaints (`seed_tag=vega-sample-v2`)
- 3 announcements (`seed_tag=vega-sample-v2`)
- sample image URLs for evidence/proof data

## Mongo Collections and Indexes

Collections used:
- `users`
- `complaints`
- `announcements`
- `vapi_events`
- `blockchain_ledger`

Key indexes:
- `users.email` unique
- `complaints.location` 2dsphere
- `complaints.created_at`
- `complaints.user_id + created_at`
- `complaints.department`
- `complaints.status`
- `complaints.upvotes_count + created_at`
- `announcements.created_at`
- `blockchain_ledger.complaint_id` unique sparse
- `blockchain_ledger.index`

## Quick Verification Checklist

### Backend and DB
1. Run backend.
2. Check `/health` => `database_connected: true`.
3. Create a complaint from UI.
4. Confirm Mongo `complaints` receives new document.

### Heatmap
1. Open Heatmap page.
2. Confirm points are loaded from `/api/v1/c/spatial-analytics`.
3. Confirm map updates over refresh cycle.

### Agentic AI
1. Ensure `OPENAI_API_KEY` is set.
2. Call `POST /api/v1/ai/query`.
3. Confirm tool usage appears in response (`used_tools`).

### Vapi
1. Set `VAPI_SERVICE_TOKEN`.
2. Call `GET /api/v1/vapi/ping` with bearer token.
3. Call `POST /api/v1/vapi/webhook`, confirm `vapi_events` insert.

### Blockchain
1. Open Chain Ledger page.
2. Click `Anchor My Complaints`.
3. Confirm records appear in `blockchain_ledger`.
4. Modify a complaint manually in DB.
5. Verify endpoint shows invalid/tampered state.

## Useful Commands

Compile check:
```powershell
cd mumbai-smart-civic/backend
python -m compileall app scripts
```

Frontend build check:
```powershell
cd mumbai-smart-civic/frontend
npm run build
```

## Troubleshooting

`bad auth : authentication failed`:
- validate Mongo username/password in `MONGODB_URL`
- URL-encode password if it contains special chars
- ensure Atlas user has access and IP allowlist is correct

`Database is not connected`:
- confirm `.env` is present at `backend/.env`
- confirm app starts from `backend` directory
- check `/health`

Images not loading:
- ensure backend is running and static route is active
- verify stored path starts with `/static/uploads/`

AI route returns config error:
- set `OPENAI_API_KEY` in backend `.env`

Vapi unauthorized:
- send `Authorization: Bearer <VAPI_SERVICE_TOKEN>`

## Security Notes
- Do not commit real API keys, DB passwords, or service tokens.
- Rotate any keys that were shared in chat/logs.
- Use separate credentials for production and local development.
