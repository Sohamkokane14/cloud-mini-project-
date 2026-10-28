# Presentation outline — Smart Campus Lost & Found

## Slide 1 — Title

- Smart Campus Lost & Found System
- Cloud Computing Mini Project — Experiment 10
- Team members, class, and faculty name

## Slide 2 — Problem

- Lost/found notices are fragmented and slow
- Students cannot easily discover a similar report
- Staff need a simple verification workflow

## Slide 3 — Objectives

- Report, store, match, and return campus items
- Demonstrate five cloud service models securely
- Keep the workflow simple enough for a live demo

## Slide 4 — Architecture

- Student Portal on App Service
- Admin Panel on Ubuntu VM
- SQL, Blob, Key Vault, Microsoft sign-in, and AI Vision
- Insert architecture diagram/screenshot

## Slide 5 — Cloud service models

- IaaS: VM and Nginx/Gunicorn
- PaaS: App Service
- DBaaS/STaaS: Azure SQL and Blob Storage
- SECaaS: Key Vault, managed identities, Easy Auth, NSG

## Slide 6 — Student workflow

- Sign in with Microsoft account
- Submit lost/found report and optional photo
- Store image, tags, and report
- Show suggested matches

## Slide 7 — Matching logic

- 60% tag similarity
- 30% same category
- 10% same location
- Score ≥ 0.4 becomes a staff-review suggestion

## Slide 8 — Admin workflow

- Secure staff login
- Dashboard/chart and item list
- Confirm/reject match and mark returned

## Slide 9 — Security

- Secrets only in Key Vault
- Managed identity for both hosts
- Easy Auth and hashed admin password
- NSG: SSH restricted, HTTP open

## Slide 10 — Deployment and CI/CD

- GitHub source control and `dev` integration
- App Service deployment workflow
- VM setup: ODBC, Gunicorn, systemd, Nginx

## Slide 11 — Results

- Add portal, match, storage, SQL, and dashboard screenshots
- Mention mock-mode tests and live end-to-end test result

## Slide 12 — Cost and future scope

- Azure for Students/free tiers and VM stop policy
- Notifications, mobile app, semantic matching

## Slide 13 — Conclusion

- Problem solved through practical cloud integration
- Questions
