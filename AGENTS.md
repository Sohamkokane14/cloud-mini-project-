# Project working agreement

## Scope and ownership

| Lane | Owned paths | Branch |
| --- | --- | --- |
| Shared/data | `shared/`, `database/`, `tests/` | `feat/shared` |
| Student portal | `student_portal/`, `wsgi_student.py` | `feat/student` |
| Admin panel | `admin_panel/`, `wsgi_admin.py` | `feat/admin` |
| Deployment | `deploy/`, `requirements.txt`, `docs/DEPLOYMENT.md` | `feat/deploy` |
| Documentation | `docs/report/`, `docs/SCREENSHOTS.md` | `feat/docs` |

The integration branch is `dev`; release promotion to `main` requires explicit approval after verification.

## Non-negotiable rules

1. Read `PLAN.md` and `docs/CONTRACTS.md` before implementing application code.
2. Work only in the owned paths for the active lane. Propose cross-lane changes before editing them.
3. Never add a password, private key, connection string, access token, or actual `.env` file to Git.
4. Every feature must work in `APP_MODE=mock` before it is tested against Azure.
5. Use parameterized SQL only, keep database access in `shared/db.py`, and close connections per request.
6. Finish a lane by updating `docs/STATUS.md` and providing a `READY_FOR_GIT` handoff with tests actually run.

## Git handoff

```text
READY_FOR_GIT
Task ID:
Feature:
Branch:
Files modified:
Tests executed:
Known limitations:
Documentation changes:
Integration dependencies:
```

Do not merge or deploy merely because code has been written. Review the diff, run the relevant tests, scan staged changes for secrets, and record the result first.
