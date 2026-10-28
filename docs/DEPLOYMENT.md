# Deployment guide

This guide uses Azure resources created through the human checkpoints in `PLAN.md`. Do not commit connection strings, passwords, access keys, private keys, or `.env` files.

## Local verification

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:APP_MODE = 'mock'
python -m pytest -q
python wsgi_student.py
```

Use a second terminal for `python wsgi_admin.py`. For local Azure testing, set `APP_MODE=local` and add secret values only to your ignored `.env` file.

## App Service — Student Portal

Complete HUMAN-09 first. Configure the Linux Python 3.11 App Service with these non-secret settings:

| Name | Value |
| --- | --- |
| `APP_MODE` | `cloud` |
| `KEY_VAULT_URL` | Your vault URI |
| `VISION_CAPTION` | `on` in a supported region, otherwise `off` |
| `FLASK_SECRET_KEY` | A long, random value entered in App Service only |
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | `true` |

Set the startup command to the exact contents of `deploy/appservice-startup.txt`:

```text
gunicorn --bind=0.0.0.0 --timeout 600 wsgi_student:app
```

Enable the system-assigned identity and assign it the **Key Vault Secrets User** role on the Key Vault. Configure GitHub Deployment Center to deploy the `main` branch only after the project has passed local and `dev` verification. It creates the GitHub Actions workflow; inspect that workflow before relying on it.

## Linux VM — Admin Panel

Complete HUMAN-11 first: create an Ubuntu 24.04 VM, permit HTTP (80), restrict SSH (22) to your IP, enable its managed identity, and grant that identity **Key Vault Secrets User** on the vault.

From a checkout that has the correct `origin` remote, run:

```bash
sudo bash deploy/vm-setup.sh
```

Enter only the vault URI when prompted. The script installs Nginx, ODBC Driver 18, Python dependencies, the systemd service, and the `/etc/lostfound.env` file with restrictive permissions. It clones the configured remote into `/opt/lostfound` and starts `lostfound-admin`.

Useful VM checks:

```bash
sudo systemctl status lostfound-admin nginx
sudo journalctl -u lostfound-admin -n 100 --no-pager
sudo nginx -t
```

For a post-deployment update, SSH to the VM and run `sudo git -C /opt/lostfound pull --ff-only && sudo systemctl restart lostfound-admin`.

## Release and validation

1. Run both applications in mock mode on `dev`.
2. Complete HUMAN-04 through HUMAN-08 and verify local Azure mode using the ignored `.env`.
3. Record test evidence, open/review a pull request from `dev` to `main`, and merge only after explicit release approval.
4. Validate the App Service health route, portal workflows, VM admin login, SQL/Blob persistence, Key Vault access, and Microsoft Easy Auth.
