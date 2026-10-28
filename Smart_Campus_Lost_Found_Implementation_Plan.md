# Smart Campus Lost & Found System — Implementation & Deployment Playbook

**Cloud Computing Mini Project · Experiment 10**
*Design and deploy a web application on a public cloud platform by integrating IaaS, PaaS, DBaaS, Storage as a Service and Security as a Service.*

---

## 0. Read This First

### What we are building

A **responsive website** (it works on phones and laptops in any browser) with two parts:

| Part | Users | Hosted on | Cloud model shown |
|---|---|---|---|
| Student Portal | Students report lost/found items, see AI-suggested matches | Azure App Service | **PaaS** |
| Admin Panel | Staff manage items, confirm matches, view stats | Azure Linux VM + Nginx | **IaaS** |
| Database | Items and matches | Azure SQL Database (free offer) | **DBaaS** |
| Photo storage | Item images | Azure Blob Storage | **Storage as a Service** |
| Security | Secrets, login, firewall | Key Vault + Managed Identity + Microsoft login + NSG | **Security as a Service** |
| AI (bonus) | Auto-tags item photos | Azure AI Vision | AI as a Service |

**Services count for the sheet: 7** (VM, App Service, Azure SQL, Blob Storage, Key Vault, Entra ID / Microsoft login, AI Vision).

### How to use this file

1. Put this file in your project folder as `PLAN.md`.
2. Open the folder in **Claude Code** (recommended, because it supports real sub-agents) or Cursor.
3. Do the **🛑 HUMAN** steps yourself when the agents stop and ask. Each one is explained click by click in Section 7.
4. Everything else is done by the agents.

### Estimated time

| Stage | Who | Time |
|---|---|---|
| Install tools, GitHub, Azure account | You | 1 – 1.5 h |
| Create Azure resources (guided clicks) | You | 1.5 – 2 h |
| Build all code (agents working in parallel) | Agents | 3 – 5 h (your review: ~1 h) |
| Local testing | You + agents | 1 h |
| Deploy to App Service + VM | You + agents | 2 – 3 h (first time, including fixing errors) |
| Final testing + screenshots | You | 1 h |
| Report + PPT | Docs agent + you | 2 – 3 h |
| **Total** | | **≈ 12 – 16 hours** |

That works out to **2 focused full days**, or **3–4 evenings**. Running agents in parallel saves about 40% of the build time compared with one agent doing everything in sequence.

> ⚠️ Your portal showed the report was due 24 Oct and the PPT due 25 Oct. Confirm the late-submission window with your faculty **today**, then use the **Fast-Track** schedule in Section 12.

---

## 1. Architecture

```
                         ┌──────────────────────── Azure Subscription (Azure for Students) ────────────────────────┐
                         │                                                                                          │
  Student (browser) ──►  │  App Service (PaaS)            Linux VM B1s (IaaS)  ◄── Admin (browser, port 80)          │
   Microsoft login ───►  │  Student Portal (Flask)        Nginx → Gunicorn → Admin Panel (Flask)                     │
   (Entra ID, SECaaS)    │        │  Managed Identity            │  Managed Identity        NSG firewall (SECaaS)     │
                         │        └──────────┬───────────────────┘                          22: your IP only          │
                         │                   ▼                                              80: open                  │
                         │          Key Vault (SECaaS) ── secrets: SQL conn, Storage conn, Vision key, admin hash     │
                         │                   │                                                                      │
                         │     ┌─────────────┼───────────────────────┐                                              │
                         │     ▼             ▼                       ▼                                              │
                         │  Azure SQL     Blob Storage          AI Vision                                           │
                         │  (DBaaS)       (STaaS)               (tags + caption)                                    │
                         │  Items,        container:                                                                │
                         │  Matches       item-images                                                               │
                         └──────────────────────────────────────────────────────────────────────────────────────────┘
        Source code: GitHub repo ──(GitHub Actions via Deployment Center)──► App Service
                                 └─(git clone + setup script)──────────────► VM
```

### Request flow ("Report Found Item")

1. The student logs in with a Microsoft account. App Service handles the login, so no login code is needed.
2. The student fills the form and uploads a photo.
3. The app reads its secrets from Key Vault using Managed Identity, so no passwords are stored in the code.
4. The photo is uploaded to Blob Storage, and its URL is saved.
5. The photo is sent to AI Vision, which returns tags (for example `bottle`, `blue`, `plastic`) and a caption.
6. The item row is inserted into Azure SQL.
7. The matching engine compares the item with open "lost" items and stores any match with score ≥ 0.4.
8. The student sees the AI tags and suggested matches. The admin sees everything on the VM dashboard.

---

## 2. Tech Stack

- Python 3.11, Flask, Jinja2 templates, Bootstrap 5 (CDN), Chart.js (CDN)
- `pyodbc` + Microsoft ODBC Driver 18 (Azure SQL)
- `azure-identity`, `azure-keyvault-secrets`, `azure-storage-blob`, `azure-ai-vision-imageanalysis`
- `python-dotenv`, `gunicorn`, `werkzeug` (password hashing)
- Git + GitHub + GitHub CLI (`gh`)
- Azure Portal (and optionally Azure CLI)

> Note: Azure AI Vision **Image Analysis 4.0** is deprecated and retires on **25 Sept 2028**. It works fine for this project; mention this in the report's "Future Scope" section as a migration point. Image **captions** in 4.0 work only in some regions, which is why we use **East US**. Tags work everywhere.

---

## 3. Repository Structure

Folder names use underscores so they work as Python packages. Root-level `wsgi_*.py` files let both apps share the `shared` package on App Service and on the VM.

```
smart-campus-lost-found/
├── CLAUDE.md                     # Rules every agent follows (Section 4.4)
├── PLAN.md                       # This file
├── requirements.txt              # One file for both apps (App Service builds from root)
├── wsgi_student.py               # from student_portal.app import app
├── wsgi_admin.py                 # from admin_panel.app import app
├── .env.example                  # Variable names only — never real values
├── .gitignore                    # .env, venv/, __pycache__/, local_uploads/, *.pem, *.db
├── shared/
│   ├── __init__.py
│   ├── config.py                 # Key Vault (cloud) or .env (local) or mock
│   ├── db.py                     # All SQL lives here (repository functions)
│   ├── storage.py                # Blob upload/delete (or local folder in mock mode)
│   ├── vision.py                 # AI tags + caption (or fake tags in mock mode)
│   └── matching.py               # Jaccard tag score + category + location
├── student_portal/
│   ├── __init__.py
│   ├── app.py
│   ├── templates/  (base, home, report, browse, my_items, item_detail)
│   └── static/     (css, img)
├── admin_panel/
│   ├── __init__.py
│   ├── app.py
│   ├── templates/  (base, login, dashboard, items, matches)
│   └── static/
├── database/
│   ├── schema.sql                # T-SQL for Azure SQL
│   └── sample_data.sql
├── deploy/
│   ├── vm-setup.sh               # One-shot VM install script
│   ├── gunicorn-admin.service    # systemd unit
│   ├── nginx-admin.conf
│   └── appservice-startup.txt    # gunicorn --bind=0.0.0.0 --timeout 600 wsgi_student:app
├── docs/
│   ├── CONTRACTS.md              # Function signatures all agents code against
│   ├── STATUS.md                 # Each agent updates its lane here
│   ├── DECISIONS.md              # Master agent's decisions log
│   ├── HUMAN_TASKS.md            # Pending/done human checkpoints
│   ├── DEPLOYMENT.md             # Final deployment guide (Section 8, refined)
│   ├── SCREENSHOTS.md            # Checklist for the report
│   └── report/                   # Report + PPT content drafts
└── tests/
    └── test_matching.py
```

---

## 4. The Agent Team

### 4.1 Roles

| Agent | Name | Owns | Works in parallel with |
|---|---|---|---|
| 🧠 **Master** | `master` (the main session) | Plan, contracts, task assignment, **code review**, approve/reject, final decisions | Supervises all |
| 🗄️ Agent A | `shared-db-agent` | `shared/`, `database/`, `tests/` | B, C, D, F |
| 🎓 Agent B | `student-portal-agent` | `student_portal/`, `wsgi_student.py` | A, C, D, F |
| 🛠️ Agent C | `admin-panel-agent` | `admin_panel/`, `wsgi_admin.py` | A, B, D, F |
| ☁️ Agent D | `devops-agent` | `deploy/`, `docs/DEPLOYMENT.md`, `requirements.txt` | A, B, C, F |
| 🐙 Agent E | `github-agent` | Repo, branches, commits, PRs, merges, `.gitignore`, secret scan, Actions workflow | Runs after each lane finishes |
| 📝 Agent F | `docs-agent` | `docs/report/`, `docs/SCREENSHOTS.md`, report + PPT text | A, B, C, D |

### 4.2 Why parallel work is safe here

- **Contracts first.** Before anyone codes, the Master writes `docs/CONTRACTS.md` with the exact function signatures of `shared/` (for example `db.create_item(...) -> int`). Agents B and C code against these signatures while Agent A implements them.
- **Mock mode.** With `APP_MODE=mock`, the apps use SQLite, a local `local_uploads/` folder and fake AI tags. All agents can run and test **without Azure** and without spending credit. With `APP_MODE=cloud`, they use real Azure.
- **Separate folders, separate branches.** Each agent edits only its own folder, on its own branch, in its own **git worktree**, so there are no merge conflicts.

### 4.3 Branch & review flow

```
main  ← protected, only Master-approved merges from dev
 └── dev  ← integration branch
      ├── feat/shared      (Agent A)
      ├── feat/student     (Agent B)
      ├── feat/admin       (Agent C)
      ├── feat/deploy      (Agent D)
      └── feat/docs        (Agent F)

1. Agent finishes a task → updates docs/STATUS.md → tells Master "READY FOR REVIEW: <branch>"
2. Master reviews using the checklist (4.6) → writes verdict in docs/DECISIONS.md
      APPROVED            → GitHub agent opens PR feat/* → dev, merges, deletes branch
      CHANGES REQUESTED   → the same agent fixes, then repeats step 1
3. After integration test on dev passes → GitHub agent merges dev → main
4. main triggers GitHub Actions → deploys Student Portal to App Service
```

### 4.4 `CLAUDE.md` (create this at the repo root, so all agents read it)

```markdown
# Project Rules — Smart Campus Lost & Found

## Golden rules
1. Read PLAN.md and docs/CONTRACTS.md before writing code.
2. Edit ONLY the folders your role owns. Need a change elsewhere? Ask the Master.
3. NEVER write, print, commit or log a real secret, password, key or connection string.
   Real values live only in .env (local) and Azure Key Vault (cloud).
4. Keep code simple and commented — a student must explain it in a viva.
5. Every feature must work in APP_MODE=mock before cloud testing.
6. When you finish, update docs/STATUS.md and say "READY FOR REVIEW: <branch>".

## Human checkpoint protocol
When a step needs the human (Azure portal, GitHub login, secrets, SSH, payment-free account setup):
1. STOP. Do not guess or fake it.
2. Add/mark the item in docs/HUMAN_TASKS.md.
3. Print exactly:
   🛑 WAITING FOR HUMAN-XX: <title>
   Why: <one line>
   Steps: see PLAN.md Section 7 → HUMAN-XX
   When done, reply: "HUMAN-XX done" (+ any non-secret values requested)
4. Continue only after the human replies.
Never ask the human to paste secrets into chat. Ask them to put secrets in .env or Key Vault themselves.

## Code style
- Python 3.11, Flask, type hints on shared functions, docstrings on every function.
- SQL only inside shared/db.py, always parameterised (?), never string-formatted.
- Open a DB connection per request and close it (keeps the free SQL DB able to auto-pause).
```

### 4.5 Sub-agent definition files (Claude Code)

Create the folder `.claude/agents/` and add one file per agent. The GitHub agent can create these in Phase 0.

**`.claude/agents/shared-db-agent.md`**
```markdown
---
name: shared-db-agent
description: Builds the shared Python package (config, db, storage, vision, matching), the T-SQL schema and unit tests for the Lost & Found project. Use for anything in shared/, database/ or tests/.
tools: Read, Write, Edit, Bash, Glob, Grep
---
You are Agent A. Follow CLAUDE.md. Work only in shared/, database/, tests/ on branch feat/shared.
Implement EXACTLY the signatures in docs/CONTRACTS.md.
- config.py: APP_MODE = mock | local | cloud.
  cloud: KEY_VAULT_URL + DefaultAzureCredential + SecretClient, secrets:
  SqlConnectionString, StorageConnectionString, VisionEndpoint, VisionKey, AdminPasswordHash.
  local: same names from .env. mock: no secrets needed.
- db.py: pyodbc for local/cloud (set pyodbc.pooling = False, open/close per call, retry 3x with 10s wait
  because the serverless DB may be waking up), sqlite3 for mock. Keep SQL portable or branch per dialect.
- storage.py: Blob container "item-images", uuid filenames, return public-read URL or SAS URL; mock saves to local_uploads/.
- vision.py: Image Analysis 4.0 TAGS (+ CAPTION if VISION_CAPTION=on), keep tags with confidence >= 0.7;
  mock returns tags guessed from the filename/category.
- matching.py: score = 0.6*jaccard(tags) + 0.3*(same category) + 0.1*(same location); store if >= 0.4.
- database/schema.sql + sample_data.sql (T-SQL). tests/test_matching.py with pytest.
Finish with STATUS.md update and "READY FOR REVIEW: feat/shared".
```

**`.claude/agents/student-portal-agent.md`**
```markdown
---
name: student-portal-agent
description: Builds the Flask Student Portal (PaaS app on App Service) for the Lost & Found project. Use for anything in student_portal/ or wsgi_student.py.
tools: Read, Write, Edit, Bash, Glob, Grep
---
You are Agent B. Follow CLAUDE.md. Work only in student_portal/ and wsgi_student.py on branch feat/student.
Use ONLY functions from docs/CONTRACTS.md (import from shared). If shared isn't ready, write against the contract.
Pages: Home (counts + recent items), Report Lost, Report Found (title, description, category dropdown:
Electronics, ID Card, Books, Bottle, Bag, Keys, Clothing, Other; location; date; photo ≤ 5 MB, jpg/png),
Browse (filters: type, category, keyword), My Items (with suggested matches + score %), Item detail.
Current user: read X-MS-CLIENT-PRINCIPAL-NAME header (App Service auth); in mock/local use "demo@student.local".
Show AI tags as Bootstrap badges. Footer: "Hosted on Azure App Service (PaaS)". Mobile-friendly.
Add /health route returning {"status":"ok"}. Friendly error page if DB is waking up.
Finish with STATUS.md update and "READY FOR REVIEW: feat/student".
```

**`.claude/agents/admin-panel-agent.md`**
```markdown
---
name: admin-panel-agent
description: Builds the Flask Admin Panel that runs on the Azure VM (IaaS) for the Lost & Found project. Use for anything in admin_panel/ or wsgi_admin.py.
tools: Read, Write, Edit, Bash, Glob, Grep
---
You are Agent C. Follow CLAUDE.md. Work only in admin_panel/ and wsgi_admin.py on branch feat/admin.
Use ONLY functions from docs/CONTRACTS.md.
Features: login (username "admin", password checked with werkzeug check_password_hash against
secret AdminPasswordHash; Flask session; SECRET_KEY from env), Dashboard (totals + Chart.js items per category
+ recent activity), Items table (mark returned, delete → also delete blob), Matches page (confirm/reject).
Footer: "Hosted on Azure Virtual Machine (IaaS) — host: <socket.gethostname()>".
Add a small script admin_panel/make_hash.py that asks for a password and prints its hash (for HUMAN-07).
Finish with STATUS.md update and "READY FOR REVIEW: feat/admin".
```

**`.claude/agents/devops-agent.md`**
```markdown
---
name: devops-agent
description: Writes deployment files and the Azure deployment guide for the Lost & Found project (App Service, VM, Nginx, systemd, requirements). Use for deploy/, docs/DEPLOYMENT.md, requirements.txt.
tools: Read, Write, Edit, Bash, Glob, Grep
---
You are Agent D. Follow CLAUDE.md. Work only in deploy/, docs/DEPLOYMENT.md, requirements.txt on branch feat/deploy.
- requirements.txt (pinned, at repo root, used by both apps).
- deploy/appservice-startup.txt: gunicorn --bind=0.0.0.0 --timeout 600 wsgi_student:app
- deploy/vm-setup.sh for Ubuntu 24.04: apt update; install python3-venv, git, nginx, curl;
  install Microsoft ODBC Driver 18 (msodbcsql18) from packages.microsoft.com; clone repo to /opt/lostfound;
  venv + pip install; write /etc/lostfound.env with APP_MODE=cloud, KEY_VAULT_URL, FLASK_SECRET_KEY (generated);
  install systemd unit + nginx site; enable + start; print the URL. Script must be idempotent and well commented.
- deploy/gunicorn-admin.service and deploy/nginx-admin.conf (proxy :80 → 127.0.0.1:8000).
- docs/DEPLOYMENT.md: expand PLAN.md Section 8 with exact commands. Never include real secrets.
Finish with STATUS.md update and "READY FOR REVIEW: feat/deploy".
```

**`.claude/agents/github-agent.md`**
```markdown
---
name: github-agent
description: Handles all Git and GitHub work for the Lost & Found project — repo setup, worktrees, branches, commits, PRs, merges, secret scanning and the App Service GitHub Actions workflow. Use whenever anything touches git or GitHub.
tools: Read, Write, Edit, Bash, Glob, Grep
---
You are Agent E. Follow CLAUDE.md. You own git/GitHub operations, .gitignore, .github/.
Setup: git init, create .gitignore, initial commit, create GitHub repo with gh (public — it holds no secrets),
create dev branch, create worktrees ../wt-shared, ../wt-student, ../wt-admin, ../wt-deploy, ../wt-docs
on their feat/* branches.
Before EVERY push: scan staged files for secrets (patterns: AccountKey=, Password=, Pwd=, sig=, -----BEGIN,
.pem, .env, long base64 keys). If found: STOP, unstage, report to Master.
Merge rules: only merge feat/* → dev when docs/DECISIONS.md shows "APPROVED" for that branch from Master.
Only merge dev → main when Master says "RELEASE". Use conventional commits (feat:, fix:, docs:, chore:).
If gh is not logged in → trigger HUMAN-02. After Deployment Center creates the Actions workflow, verify it
builds from repo root and uses the startup command; fix only the workflow file if needed.
```

**`.claude/agents/docs-agent.md`**
```markdown
---
name: docs-agent
description: Writes the mini project report and PPT content, plus the screenshot checklist, for the Lost & Found project. Use for docs/report/ and docs/SCREENSHOTS.md.
tools: Read, Write, Edit, Glob, Grep
---
You are Agent F. Follow CLAUDE.md. Work only in docs/report/ and docs/SCREENSHOTS.md on branch feat/docs.
Write: abstract, introduction, problem statement, objectives, literature/existing systems, cloud service models
explained with how THIS project uses each (IaaS/PaaS/DBaaS/STaaS/SECaaS), architecture explanation,
services-used table, implementation steps, database design, security design, results (placeholders for
screenshots), cost analysis (free tiers), advantages, limitations, future scope (incl. Image Analysis 4.0
retirement in 2028, mobile app, email alerts, Azure OpenAI matching), conclusion, references.
When the college report/PPT templates are provided (docs/report/templates/), follow their exact headings.
Write PPT content as slide-by-slide outline (title + 3–5 bullets + speaker note).
```

### 4.6 Master agent — kickoff prompt

Paste this into the **main** Claude Code session once the repo is set up:

```
You are the MASTER agent for this project. Read PLAN.md and CLAUDE.md fully.

Your job:
1. Write docs/CONTRACTS.md (exact shared/ function signatures + return types + mock behaviour),
   docs/STATUS.md (one section per agent lane), docs/DECISIONS.md, docs/HUMAN_TASKS.md (copy HUMAN-01..12
   from PLAN.md Section 7, all "pending").
2. Run the phases in PLAN.md Section 6. Launch sub-agents IN PARALLEL wherever the plan marks ⇉ parallel.
   Give each sub-agent: its task, its branch/worktree path, and "follow CLAUDE.md".
3. Review every "READY FOR REVIEW" using this checklist and record the verdict in docs/DECISIONS.md:
   [ ] Matches docs/CONTRACTS.md exactly
   [ ] Runs in APP_MODE=mock (you actually run it / run pytest)
   [ ] No secrets anywhere (grep it)
   [ ] Only touched its own folders
   [ ] Simple enough to explain in a viva; functions have docstrings
   [ ] The cloud service model it represents is clearly visible (footer, comments, README)
   Verdict: APPROVED or CHANGES REQUESTED (with a numbered list of fixes).
4. You make the final call on any design disagreement; log the decision and the reason in DECISIONS.md.
5. When a phase needs a human step, follow the Human checkpoint protocol in CLAUDE.md and wait.
6. After each phase, give me a 5-line status: done, in progress, blocked, next human step, time estimate left.

Start with Phase 0.
```

### 4.7 Not using Claude Code?

**Cursor or Windsurf:** open the repo **5 times**, once per worktree folder (`wt-shared`, `wt-student` and so on). In each window, start a chat and paste that agent's `.md` body as the first message. Keep one extra window on `dev` as the Master and paste the Master prompt there. You become the messenger: copy each "READY FOR REVIEW" to the Master window.

---

## 5. `docs/CONTRACTS.md` (starter for the Master)

```python
# shared/config.py
APP_MODE: str                      # "mock" | "local" | "cloud"
def get_secret(name: str) -> str   # Key Vault in cloud, .env in local, "" in mock

# shared/db.py
def init_db() -> None                                  # mock: create SQLite tables
def create_item(data: dict) -> int                     # returns ItemId
def get_item(item_id: int) -> dict | None
def list_items(type: str | None = None, category: str | None = None,
               keyword: str | None = None, status: str | None = None,
               reporter_email: str | None = None, limit: int = 50) -> list[dict]
def update_item_status(item_id: int, status: str) -> None   # open | matched | returned
def delete_item(item_id: int) -> str | None            # returns ImageUrl to delete
def create_match(lost_id: int, found_id: int, score: float) -> int
def list_matches(item_id: int | None = None, status: str | None = None) -> list[dict]
def update_match_status(match_id: int, status: str) -> None # suggested | confirmed | rejected
def get_stats() -> dict   # {"lost": n, "found": n, "returned": n, "by_category": {...}}

# shared/storage.py
def upload_image(file_storage) -> str                  # returns URL
def delete_image(url: str) -> None

# shared/vision.py
def analyze_image(image_bytes: bytes, category_hint: str = "") -> dict  # {"tags": [...], "caption": "..."}

# shared/matching.py
def score(item_a: dict, item_b: dict) -> float
def find_and_store_matches(new_item_id: int) -> list[dict]
```

### Database schema (T-SQL)

```sql
CREATE TABLE Items (
  ItemId        INT IDENTITY(1,1) PRIMARY KEY,
  Type          NVARCHAR(10)  NOT NULL CHECK (Type IN ('lost','found')),
  Title         NVARCHAR(100) NOT NULL,
  Description   NVARCHAR(500),
  Category      NVARCHAR(50)  NOT NULL,
  Location      NVARCHAR(100),
  ItemDate      DATE,
  ImageUrl      NVARCHAR(500),
  Tags          NVARCHAR(500),
  Caption       NVARCHAR(300),
  ReporterName  NVARCHAR(100),
  ReporterEmail NVARCHAR(150),
  Status        NVARCHAR(20)  NOT NULL DEFAULT 'open',
  CreatedAt     DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME()
);
CREATE TABLE Matches (
  MatchId     INT IDENTITY(1,1) PRIMARY KEY,
  LostItemId  INT NOT NULL REFERENCES Items(ItemId),
  FoundItemId INT NOT NULL REFERENCES Items(ItemId),
  Score       FLOAT NOT NULL,
  Status      NVARCHAR(20) NOT NULL DEFAULT 'suggested',
  CreatedAt   DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);
CREATE INDEX IX_Items_Type_Status ON Items(Type, Status);
```

---

## 6. Phase Plan (who does what, and in what order)

Legend: ⇉ = agents run in parallel · 🛑 = you must do something · ✅ = Master review gate

### Phase 0 — Setup (≈ 1–1.5 h)
| # | Task | Who |
|---|---|---|
| 0.1 | 🛑 **HUMAN-01** Install tools | You |
| 0.2 | 🛑 **HUMAN-02** GitHub account + `gh auth login` | You |
| 0.3 | Create repo, `.gitignore`, `dev` branch, worktrees, `.claude/agents/*`, `CLAUDE.md` | GitHub agent |
| 0.4 | Write CONTRACTS, STATUS, DECISIONS, HUMAN_TASKS | Master |
| 0.5 | 🛑 **HUMAN-03** Activate Azure for Students | You (can do this while 0.3–0.4 run) |

### Phase 1 — Build in mock mode (≈ 3–5 h agent time) ⇉
| Lane | Agent | Output |
|---|---|---|
| A | shared-db-agent | `shared/*`, `schema.sql`, tests |
| B | student-portal-agent | Student Portal (against contract) |
| C | admin-panel-agent | Admin Panel (against contract) |
| D | devops-agent | `deploy/*`, `requirements.txt`, `DEPLOYMENT.md` |
| F | docs-agent | Report + PPT draft, screenshot checklist |

All five lanes run at the same time. ✅ The Master reviews each lane as it finishes, and the GitHub agent merges approved lanes into `dev`.

**Meanwhile, you do Phase 2 in the Azure portal.** It doesn't depend on the code.

### Phase 2 — Create Azure resources (≈ 1.5–2 h) 🛑 (in parallel with Phase 1)
| # | Step |
|---|---|
| 2.1 | 🛑 **HUMAN-04** Resource group + choose region |
| 2.2 | 🛑 **HUMAN-05** Azure SQL Database (free offer) + run schema |
| 2.3 | 🛑 **HUMAN-06** Storage account + container |
| 2.4 | 🛑 **HUMAN-07** AI Vision resource |
| 2.5 | 🛑 **HUMAN-08** Key Vault + add all secrets |

### Phase 3 — Integration test (≈ 1 h)
| # | Task | Who |
|---|---|---|
| 3.1 | Run both apps on `dev` in `APP_MODE=mock`, then fix issues | Master + owning agents |
| 3.2 | Run both apps in `APP_MODE=local` (real Azure SQL / Blob / Vision via `.env`) | You run, agents fix |
| 3.3 | ✅ Master says **RELEASE**, and the GitHub agent merges `dev` → `main` | Master + GitHub agent |

### Phase 4 — Deploy (≈ 2–3 h)
| # | Step | Who |
|---|---|---|
| 4.1 | 🛑 **HUMAN-09** App Service + Managed Identity + Key Vault access + GitHub deployment | You, then GitHub agent checks the workflow |
| 4.2 | 🛑 **HUMAN-10** Microsoft login (Easy Auth) on App Service | You |
| 4.3 | 🛑 **HUMAN-11** Linux VM + NSG + Managed Identity + run `vm-setup.sh` | You, with devops-agent guiding |
| 4.4 | End-to-end test on the live URLs | You + Master |

### Phase 5 — Submission (≈ 2–3 h)
| # | Task | Who |
|---|---|---|
| 5.1 | 🛑 **HUMAN-12** Take screenshots (list in Section 10) | You |
| 5.2 | Put screenshots + college templates into `docs/report/` | You |
| 5.3 | Fill report + PPT in the college format | docs-agent (or ask Claude chat to build the .docx/.pptx) |
| 5.4 | Export PDFs and upload to the portal | You |

---

## 7. 🛑 Human Checkpoints — Step by Step

> **Golden rule:** never paste passwords, keys or connection strings into any AI chat. You type secrets only into `.env` on your laptop or into Azure Key Vault.

### HUMAN-01 — Install tools (30 min)
1. **Python 3.11 or 3.12** from python.org. On Windows, tick **"Add Python to PATH"** during install.
2. **Git** from git-scm.com, keeping the default options.
3. **VS Code** (and the Claude Code extension) or Cursor.
4. **Claude Code CLI**, following Anthropic's install guide, or use the VS Code extension.
5. **GitHub CLI** from cli.github.com.
6. **Microsoft ODBC Driver 18 for SQL Server**: search "Download ODBC Driver 18 for SQL Server", then install the version for your OS.
7. *(Optional)* **Azure CLI**: search "Install Azure CLI".
8. Check that everything works. Open a terminal and run:
   ```
   python --version
   git --version
   gh --version
   ```
   Each should print a version number. Reply **"HUMAN-01 done"**.

### HUMAN-02 — GitHub login (5 min)
1. Create an account at github.com if you don't have one.
2. In the terminal, run `gh auth login` and choose **GitHub.com → HTTPS → Login with a web browser**.
3. Copy the 8-character code shown, paste it in the browser page that opens, and click **Authorize**.
4. Run `git config --global user.name "Your Name"` and `git config --global user.email "you@example.com"`.
5. Reply **"HUMAN-02 done, username: <your GitHub username>"**.

### HUMAN-03 — Activate Azure for Students (10–15 min)
1. Go to **azure.microsoft.com/free/students** and click **Start free**.
2. Sign in, then verify with your **college email** (a code is sent to it). No credit card is needed.
3. You get **$100 credit for 12 months**, plus free services.
4. Open **portal.azure.com**, search **Subscriptions**, and check you see **"Azure for Students"**.
5. Reply **"HUMAN-03 done"**.

### HUMAN-04 — Resource group (3 min)
A resource group is a folder that holds every Azure resource for this project. Deleting it later removes everything in one go.
1. In the portal search bar, type **Resource groups** → **+ Create**.
2. Subscription: **Azure for Students**. Name: `rg-lostfound`. Region: **East US**.
3. Click **Review + create** → **Create**.

> If you get a "region not allowed" error anywhere: student subscriptions sometimes restrict regions. Try **Central India** or **South India** and use the **same region for everything**. If East US isn't allowed, set `VISION_CAPTION=off` later; tags will still work.

Reply **"HUMAN-04 done, region: <region>"**.

### HUMAN-05 — Azure SQL Database, free offer (20 min)
1. Search **SQL databases** → **+ Create**.
2. If you see the banner **"Want to try Azure SQL Database for free?"**, click **Apply offer**.
3. **Basics** tab:
   - Resource group: `rg-lostfound`
   - Database name: `lostfounddb`
   - Server: **Create new**
     - Server name: `lostfound-sql-<yourname>` (must be unique worldwide; lowercase only)
     - Location: your region
     - Authentication: **Use SQL authentication**
     - Admin login: `sqladmin`
     - Password: a strong password. **Write it down privately.**
   - When the free amount is used up: keep **"Auto-pause the database until next month"**. This guarantees you are never charged.
4. **Networking** tab:
   - Connectivity method: **Public endpoint**
   - **Allow Azure services and resources to access this server: Yes** (this lets App Service and the VM connect)
   - **Add current client IP address: Yes** (this lets your laptop connect)
5. Click **Review + create** → **Create**, then wait 3–5 minutes.
6. **Create the tables:** open the database → **Query editor (preview)** → log in with `sqladmin` and your password → paste the contents of `database/schema.sql` → **Run**. Then do the same with `sample_data.sql`.
7. **Get the connection string:** go to the database → **Connection strings** → **ODBC** tab → copy it. Replace `{your_password_here}` with your password, then:
   - Paste it into `.env` on your laptop as `SQL_CONNECTION_STRING=...` (local testing)
   - Keep it ready for Key Vault in HUMAN-08

> 💡 The free database **sleeps after about 1 hour of no use**, and the first request after that takes up to 1 minute. Before your demo, open the website once so the database wakes up.

Reply **"HUMAN-05 done"**. Don't paste the string in chat.

### HUMAN-06 — Storage account + container (10 min)
1. Search **Storage accounts** → **+ Create**.
2. Resource group: `rg-lostfound`. Name: `lostfoundstore<yourname>` (lowercase letters and numbers only, globally unique). Region: same as before. Performance: **Standard**. Redundancy: **LRS** (cheapest).
3. **Advanced** tab: tick **Allow enabling anonymous access on individual containers** (so item photos can be shown on the website).
4. **Review + create** → **Create**.
5. Open the storage account → **Containers** → **+ Container**. Name: `item-images`. Anonymous access level: **Blob (anonymous read access for blobs only)** → **Create**.
6. Go to **Access keys** → **Show** → copy **Connection string** (key1). Put it in `.env` as `STORAGE_CONNECTION_STRING=...` and keep it for Key Vault.

Reply **"HUMAN-06 done"**.

### HUMAN-07 — AI Vision + admin password hash (10 min)
1. Search **Computer vision** (it may also appear as "Azure AI Vision") → **+ Create**.
2. Resource group: `rg-lostfound`. Region: **East US** (needed for captions). Name: `lostfound-vision-<yourname>`. Pricing tier: **Free F0** (if F0 isn't offered because you already used it once, choose **S1**; this project costs only a few rupees).
3. Tick the Responsible AI notice → **Review + create** → **Create**.
4. Open it → **Keys and Endpoint** → copy **KEY 1** and **Endpoint**. Put them in `.env` as `VISION_KEY=...` and `VISION_ENDPOINT=...`.
5. **Admin password hash:** in the project folder run `python admin_panel/make_hash.py`, type an admin password, and copy the long hash it prints. Put it in `.env` as `ADMIN_PASSWORD_HASH=...`.

Reply **"HUMAN-07 done"**.

### HUMAN-08 — Key Vault + secrets (15 min)
1. Search **Key vaults** → **+ Create**.
2. Resource group: `rg-lostfound`. Name: `lostfound-kv-<yourname>`. Region: same. Pricing: **Standard**.
3. **Access configuration** tab: Permission model: **Azure role-based access control (recommended)**.
4. **Review + create** → **Create**.
5. **Give yourself permission** (this step is the most commonly missed one):
   Key Vault → **Access control (IAM)** → **+ Add** → **Add role assignment** → choose **Key Vault Secrets Officer** → Next → **+ Select members** → pick your own account → **Review + assign**. Wait about 1 minute.
6. Key Vault → **Secrets** → **+ Generate/Import**. Create these 5 secrets, using the exact names below and pasting values from your `.env`:

   | Secret name | Value from |
   |---|---|
   | `SqlConnectionString` | HUMAN-05 |
   | `StorageConnectionString` | HUMAN-06 |
   | `VisionEndpoint` | HUMAN-07 |
   | `VisionKey` | HUMAN-07 |
   | `AdminPasswordHash` | HUMAN-07 |

7. Copy the **Vault URI** from Overview (for example `https://lostfound-kv-xyz.vault.azure.net/`). This one is **not** secret, so you can share it with the agents.

Reply **"HUMAN-08 done, vault URI: <uri>"**.

### HUMAN-09 — App Service (PaaS) + deploy from GitHub (25 min)
1. Search **App Services** → **+ Create** → **Web App**.
2. **Basics:**
   - Resource group: `rg-lostfound`. Name: `lostfound-<yourname>`. This becomes your URL: `https://lostfound-<yourname>.azurewebsites.net`.
   - Publish: **Code**. Runtime stack: **Python 3.11**. OS: **Linux**. Region: same.
   - Pricing plan: **Create new** → choose **Free F1** (or **Basic B1** if F1 isn't available; B1 is covered by your credit).
3. **Deployment** tab: Continuous deployment **Enable** → connect your **GitHub** account → choose repo `smart-campus-lost-found`, branch `main`.
4. **Review + create** → **Create**. GitHub Actions starts deploying automatically.
5. **Turn on Managed Identity:** Web App → **Identity** → **System assigned** → **On** → **Save** → **Yes**.
6. **Allow it to read Key Vault:** Key Vault → **Access control (IAM)** → **+ Add role assignment** → **Key Vault Secrets User** → Members: **Managed identity** → select **App Service** → `lostfound-<yourname>` → **Review + assign**.
7. **App settings:** Web App → **Settings → Environment variables** → **+ Add** each of these:
   - `APP_MODE` = `cloud`
   - `KEY_VAULT_URL` = your Vault URI
   - `VISION_CAPTION` = `on` (or `off` if your region isn't East US)
   - `FLASK_SECRET_KEY` = any long random text
   - `SCM_DO_BUILD_DURING_DEPLOYMENT` = `true`
   Click **Apply**.
8. **Startup command:** **Settings → Configuration → General settings** → Startup Command:
   `gunicorn --bind=0.0.0.0 --timeout 600 wsgi_student:app` → **Save**.
9. Wait for the GitHub Actions run to go green (repo → **Actions** tab), then open your URL.

Reply **"HUMAN-09 done, URL: <url>"**. The GitHub agent then checks the workflow file.

### HUMAN-10 — Microsoft login on the Student Portal (10 min)
1. Web App → **Settings → Authentication** → **Add identity provider**.
2. Identity provider: **Microsoft**. App registration: **Create new**. Supported account types: **Any Microsoft Entra directory and personal Microsoft accounts**.
3. Restrict access: **Require authentication**. Unauthenticated requests: **HTTP 302 redirect**.
4. Click **Add**. Open your URL in a private window, and you should see the Microsoft sign-in page.

> If you get "insufficient privileges to create app registration", your college directory blocks it. Tell the Master. The fallback is to sign in to Azure with a personal Microsoft account, or for the agents to add a simple email-based login and explain it in the report.

Reply **"HUMAN-10 done"**.

### HUMAN-11 — Linux VM for the Admin Panel (IaaS) (40 min)
1. Search **Virtual machines** → **+ Create** → **Azure virtual machine**.
2. **Basics:**
   - Resource group: `rg-lostfound`. Name: `lostfound-admin-vm`. Region: same.
   - Image: **Ubuntu Server 24.04 LTS**. Size: **Standard_B1s** (free-eligible for students).
   - Authentication: **SSH public key**. Username: `azureuser`. Key pair name: `lostfound-key`.
   - Inbound ports: allow **SSH (22)** and **HTTP (80)**.
3. **Management** tab: tick **Enable system assigned managed identity**.
4. **Review + create** → **Create** → **Download private key**. Save `lostfound-key.pem` somewhere safe, **outside** the project folder.
5. **Lock down SSH (Security):** VM → **Networking** → click the **SSH (22)** rule → Source: **My IP address** → **Save**. Now only your laptop can SSH in, while port 80 stays open for the website.
6. **Key Vault access for the VM:** Key Vault → **Access control (IAM)** → **+ Add role assignment** → **Key Vault Secrets User** → Members: **Managed identity** → **Virtual machine** → `lostfound-admin-vm` → **Review + assign**.
7. **Connect.** Copy the VM's **Public IP** from Overview, then in the terminal:
   ```
   # Windows: run in PowerShell from the folder with the key
   ssh -i lostfound-key.pem azureuser@<PUBLIC_IP>
   ```
   (On Mac/Linux, first run `chmod 400 lostfound-key.pem`.) Type `yes` when asked.
8. **Run the setup script** inside the VM:
   ```
   git clone https://github.com/<your-username>/smart-campus-lost-found.git
   cd smart-campus-lost-found
   sudo bash deploy/vm-setup.sh
   ```
   When asked, paste your **Vault URI**. The script installs everything and starts the Admin Panel.
9. Open `http://<PUBLIC_IP>` in the browser, then log in as `admin` with the password you chose in HUMAN-07.

Reply **"HUMAN-11 done, admin URL: http://<ip>"**. If any command fails, copy the error output (it has no secrets) and give it to the devops-agent.

### HUMAN-12 — Screenshots (30 min)
Follow the list in Section 10, and save them as `01_resource_group.png`, `02_sql.png`, and so on in `docs/report/screenshots/`.

---

## 8. Deployment Summary (order of operations)

```
Local mock OK ─► Local with real Azure (.env) OK ─► Key Vault filled ─► merge to main
      │
      ├─► App Service: identity → KV role → env vars → startup cmd → GitHub Actions deploy → Easy Auth
      └─► VM: create → NSG lock → identity → KV role → SSH → vm-setup.sh → test http://IP
                                        │
                              End-to-end test (Section 9)
```

**Redeploying after code changes:**
- Student Portal: merge to `main`, and GitHub Actions redeploys automatically.
- Admin Panel: SSH into the VM, then run `cd /opt/lostfound && sudo git pull && sudo systemctl restart lostfound-admin`.

---

## 9. Test Checklist & Demo Script

**Functional tests**
- [ ] Student logs in with a Microsoft account
- [ ] Report a **lost** "blue water bottle" with a photo → AI tags appear
- [ ] Report a **found** bottle with a similar photo → a match appears with score %
- [ ] Photo is visible in **Blob Storage → item-images** in the portal
- [ ] Rows are visible in SQL **Query editor**: `SELECT * FROM Items`
- [ ] Admin logs in on the VM URL → dashboard chart shows counts
- [ ] Admin confirms the match and marks it returned → the student portal shows the updated status
- [ ] No secrets appear in GitHub (search the repo for "AccountKey" and "Password")

**5-minute viva demo flow**
1. Show the architecture slide and name the 5 service models.
2. Live: log in (SECaaS) → report a found item → upload a photo (STaaS) → show the AI tags.
3. Show the match on the lost item → open the Admin Panel on the VM (IaaS) → confirm the match.
4. Azure portal: show the SQL query result (DBaaS), the Key Vault secrets list (values hidden), and the NSG rules.
5. Close with cost (≈ ₹0 on free tiers) and future scope.

---

## 10. Screenshot Checklist (for the report)

| # | Screenshot | Shows |
|---|---|---|
| 01 | Resource group with all resources listed | Overall setup |
| 02 | SQL Database overview (free offer banner, vCore remaining) | DBaaS |
| 03 | Query editor showing `SELECT * FROM Items` results | DBaaS |
| 04 | Storage account → `item-images` container with uploaded photos | STaaS |
| 05 | AI Vision resource overview | AI service |
| 06 | Key Vault → Secrets list (names only) | SECaaS |
| 07 | Key Vault → IAM role assignments (App Service + VM identities) | SECaaS |
| 08 | App Service overview (URL, runtime, plan) | PaaS |
| 09 | App Service → Authentication (Microsoft provider) | SECaaS |
| 10 | GitHub Actions successful run | CI/CD |
| 11 | VM overview (size B1s, Ubuntu, public IP) | IaaS |
| 12 | VM → Networking (NSG rules: 22 = My IP, 80 = Any) | SECaaS |
| 13 | SSH terminal showing `systemctl status lostfound-admin` active | IaaS |
| 14 | Student Portal: Home page | App |
| 15 | Report form + AI tags result | App + AI |
| 16 | Suggested match screen | App |
| 17 | Admin dashboard with chart (footer showing VM hostname) | App on IaaS |
| 18 | Microsoft sign-in page for the portal | SECaaS |
| 19 | Cost Management → cost analysis | Cost |

---

## 11. Cost Safety & Cleanup

- Azure for Students has **no credit card**, so you can't be charged beyond the $100 credit. Services simply stop.
- SQL free offer: keep **auto-pause** selected. Close the Query editor when you're done, because open connections keep the database awake.
- **Stop the VM** when you're not working (VM → **Stop**). A stopped and deallocated VM doesn't use compute hours.
- Check usage in **Cost Management → Cost analysis** once a day.
- **After your marks are final:** delete `rg-lostfound` and everything inside it is removed. Take all your screenshots first.

---

## 12. Fast-Track Schedule (since the deadline has passed)

| When | Do |
|---|---|
| **Day 1 morning** | HUMAN-01, 02, 03 · GitHub agent setup · Master writes contracts |
| **Day 1 afternoon** | Phase 1: all 5 agents in parallel ⇉ · **you** do HUMAN-04 → 08 at the same time |
| **Day 1 evening** | Phase 3: local tests · merge to `main` |
| **Day 2 morning** | HUMAN-09, 10, 11: deploy both apps · end-to-end test |
| **Day 2 afternoon** | HUMAN-12 screenshots · docs-agent fills the report + PPT in the college template · export PDF · upload |

---

## 13. Troubleshooting Quick Reference

| Problem | Likely cause | Fix |
|---|---|---|
| `Can't open lib 'ODBC Driver 18 for SQL Server'` | Driver missing | Laptop: install the driver (HUMAN-01 step 6). VM: re-run `vm-setup.sh`. App Service: check the runtime is Python 3.11 Linux |
| `Login timeout expired` / first load very slow | Free SQL DB was paused | Wait ~1 min and refresh. The app's retry logic should handle this |
| `Cannot open server ... client IP not allowed` | Firewall | SQL server → Networking → add your current IP |
| Key Vault `Forbidden` / `403` | Role missing or not propagated yet | Re-check the IAM role (Secrets User for apps, Secrets Officer for you), then wait 5 min |
| App Service shows "Application Error" | Startup failure | Web App → **Log stream**. Usually a wrong startup command or missing env var |
| Photos don't display | Container is private | Set container access level to **Blob** (HUMAN-06 step 5) |
| VM site not loading | NSG or Nginx | Check port 80 rule; on VM: `sudo systemctl status nginx lostfound-admin` |
| SSH `Permission denied (publickey)` | Wrong key/user | Use `azureuser` and the right `.pem`; on Mac/Linux run `chmod 400` |
| Vision `401` | Wrong key/endpoint | Re-copy from Keys and Endpoint, then update the Key Vault secret |
| "Region not allowed" | Student policy | Use Central India or South India for everything; set `VISION_CAPTION=off` |

---

*Prepared for: CompsA · Cloud Computing Mini Project · Experiment 10*
