# Decision log

| Date | Decision | Rationale | Status |
| --- | --- | --- | --- |
| 2026-10-28 | Use `main` for releases and `dev` for integration. | Matches the supplied project plan and protects the release path. | Accepted |
| 2026-10-28 | Build and verify mock mode before Azure integration. | Enables development without exposing secrets or incurring cloud cost. | Accepted |
| 2026-10-28 | Preserve the user-supplied plan as the canonical implementation source. | It defines functional scope, architecture, and human Azure checkpoints. | Accepted |
