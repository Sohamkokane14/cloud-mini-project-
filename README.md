# Smart Campus Lost & Found System

A cloud-computing mini project where students report lost or found belongings and staff manage matching and returns.

The planned architecture demonstrates Azure App Service (PaaS), a Linux VM (IaaS), Azure SQL (DBaaS), Blob Storage (STaaS), Key Vault and Microsoft sign-in (SECaaS), with optional Azure AI Vision tagging.

## Project status

Foundation setup is complete. Application code has not yet been added.

## Planning and safety

- The detailed implementation and deployment playbook is in [Smart_Campus_Lost_Found_Implementation_Plan.md](Smart_Campus_Lost_Found_Implementation_Plan.md).
- Shared interfaces are defined in [docs/CONTRACTS.md](docs/CONTRACTS.md) before implementation begins.
- Copy `.env.example` to `.env` only for local Azure testing. Never commit real secrets, connection strings, or private keys.

## Intended local workflow

1. Create and activate a Python 3.11+ virtual environment.
2. Install dependencies from `requirements.txt` once the deployment lane supplies it.
3. Set `APP_MODE=mock` in `.env` (or leave the default) to run without Azure resources.
4. Run the student and admin applications after their feature branches are integrated into `dev`.

## Branch policy

`main` is the release branch. Feature work is isolated on `feat/*` branches and reviewed into `dev`; `dev` is promoted to `main` only after mock-mode and deployment checks pass.
