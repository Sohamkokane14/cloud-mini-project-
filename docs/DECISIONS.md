# Decision log

| Date | Decision | Rationale | Status |
| --- | --- | --- | --- |
| 2026-10-28 | Use `main` for releases and `dev` for integration. | Matches the supplied project plan and protects the release path. | Accepted |
| 2026-10-28 | Build and verify mock mode before Azure integration. | Enables development without exposing secrets or incurring cloud cost. | Accepted |
| 2026-10-28 | Preserve the user-supplied plan as the canonical implementation source. | It defines functional scope, architecture, and human Azure checkpoints. | Accepted |
| 2026-10-28 | Integrate `feat/shared` into `dev`. | Mock-mode repository, matching tests, compilation, and secret scan completed successfully. | Approved |
| 2026-10-28 | Integrate `feat/student` into `dev`. | Student Portal smoke tests passed against the integrated mock data layer. | Approved |
| 2026-10-28 | Integrate `feat/admin` into `dev`. | Admin login, dashboard, and item-status smoke tests passed in mock mode. | Approved |
| 2026-10-28 | Integrate `feat/deploy` into `dev`. | Dependency resolution and Linux-shell validation completed; LF is enforced for VM artifacts. | Approved |
| 2026-10-28 | Integrate `feat/docs` into `dev`. | Report content, presentation outline, and a secret-safe screenshot checklist are ready. | Approved |
