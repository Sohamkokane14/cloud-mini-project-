# Smart Campus Lost & Found System — Report Content

## Abstract

Smart Campus Lost & Found is a cloud-based web application that helps students report lost and found belongings and helps staff verify possible matches. The solution uses Azure App Service for the student portal, an Ubuntu virtual machine for the staff portal, Azure SQL Database for structured records, Azure Blob Storage for photos, Azure Key Vault with managed identities for secrets, Microsoft sign-in for access control, and Azure AI Vision for optional image tags. The design demonstrates IaaS, PaaS, DBaaS, Storage as a Service, and Security as a Service in one practical campus workflow.

## Introduction and problem statement

Paper notices and informal social-media messages make it difficult to connect a lost item with a found item. Reports are incomplete, photos are dispersed, staff cannot easily see unresolved cases, and passwords or cloud keys can be exposed when an application is assembled quickly. The proposed system centralizes reports, stores photos safely, suggests matches using tags/category/location, and gives staff a controlled dashboard for confirmation and return.

## Objectives

1. Let students submit lost and found reports from a responsive browser interface.
2. Store item data in Azure SQL and photos in Azure Blob Storage.
3. Generate optional image tags and captions using Azure AI Vision.
4. Suggest likely lost/found pairs with an explainable score.
5. Give staff a protected admin dashboard to confirm matches and mark items returned.
6. Demonstrate multiple cloud service models with secure secret handling.

## System architecture

The Student Portal runs on Azure App Service. Microsoft Easy Auth authenticates students before requests reach Flask. App Service uses a managed identity to read its Azure SQL, Blob Storage, Vision, and admin-hash configuration from Key Vault. The portal writes item rows to Azure SQL, uploads photos to the `item-images` Blob container, and displays AI tags.

The Admin Panel runs behind Nginx and Gunicorn on an Ubuntu VM. The VM has its own managed identity and reads the same required secrets from Key Vault. An NSG permits HTTP access and restricts SSH to the administrator's public IP. Both applications share the same repository layer and matching logic.

## Cloud service models used

| Model | Azure service | Project use |
| --- | --- | --- |
| IaaS | Ubuntu VM | Nginx/Gunicorn Admin Panel with configurable OS and NSG |
| PaaS | Azure App Service | Student Portal deployment without server management |
| DBaaS | Azure SQL Database | Items, matches, status, and audit-friendly structured data |
| STaaS | Azure Blob Storage | Item-photo object storage |
| SECaaS | Key Vault, managed identities, Microsoft sign-in, NSG | Secret protection, password-free service access, user authentication, network control |
| AI as a Service | Azure AI Vision | Image tags and optional captions |

## Implementation details

The Flask apps support three configuration modes: `mock` for SQLite/local uploads/deterministic tags, `local` for Azure services configured through an ignored `.env`, and `cloud` for managed-identity access to Key Vault. Mock mode allowed functional development before cloud resources were created.

The `Items` table stores type, title, category, location, item date, photo URL, tags, caption, reporter data, status, and creation time. The `Matches` table links lost and found item IDs, score, status, and creation time. SQL access is parameterized and connections are short-lived so the serverless database can pause when unused.

The match score is `0.6 × Jaccard tag similarity + 0.3 × category match + 0.1 × location match`. Suggestions scoring at least 0.4 are stored for staff review. This simple formula is transparent enough to explain in a viva and can later be replaced by a learned model.

## Security design

Secrets never enter Git. Local values are kept only in ignored `.env`; deployed services use Key Vault. App Service and the VM use managed identities instead of stored service credentials. Student authentication is delegated to Microsoft Easy Auth. Admin passwords are stored as a Werkzeug hash, and the VM NSG limits SSH to the administrator's address. The application accepts only JPG/PNG uploads up to 5 MB.

## Testing and results

Mock-mode repository and matching tests passed. Student Portal smoke tests covered health, lost/found report submission, browsing, and My Items. Admin Panel smoke tests covered login, dashboard loading, and marking an item returned. The deployment script passed Bash syntax validation, and its pinned dependencies resolved in a dry run. Add the screenshots from `docs/SCREENSHOTS.md` as evidence of live Azure deployment and end-to-end testing.

## Advantages

- Centralized, searchable campus reports.
- Explainable automated suggestions instead of opaque matching.
- Separation of student and staff interfaces.
- Cloud services make storage, database, authentication, and secret management visible for assessment.
- Mock mode enables demonstrations even when an Azure resource is unavailable.

## Limitations and future scope

The first version relies on text/tags and manual staff confirmation. Future work can add email notifications, QR-code labels, push notifications, mobile apps, stronger duplicate detection, and Azure OpenAI-assisted semantic matching. Azure AI Vision Image Analysis 4.0 should be reviewed before its announced 2028 retirement/migration horizon. Accessibility testing, audit logs, rate limiting, and automated backups are also appropriate production enhancements.

## Conclusion

The project demonstrates that a focused campus problem can use multiple cloud delivery models without mixing secrets into source code. Students get a simple reporting experience, staff get a controlled workflow, and the architecture clearly maps each Azure service to an academic cloud-computing concept.

## References

1. Microsoft Azure documentation: App Service, Azure SQL Database, Blob Storage, Key Vault, Virtual Machines, and Microsoft Entra ID.
2. Microsoft Azure AI Vision documentation.
3. Flask and Werkzeug documentation.
4. GitHub Actions documentation.
