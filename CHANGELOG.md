# Changelog

All notable changes to this project are documented in this file.

Changes are organized into the following categories:

- **Added:** New features or functionality introduced to the project.
- **Changed:** Modifications to existing functionality that do not add new features.
- **Fixed:** Bug fixes that resolve issues or correct unintended behavior.
- **Removed:** Features or components that have been removed from the project.

## [Unreleased]

### Added

- Community standards added to the repository.

### Changed

- Supabase keys are now sent on the `apikey` header only. The current secret keys
  (`sb_secret_...`) are not JWTs, so the `Authorization: Bearer` header the app also
  sent is wrong for them.
- `SUPABASE_SERVICE_ROLE_KEY` renamed to `SUPABASE_SECRET_KEY`, matching Supabase's
  publishable/secret key model. The old variable name is still accepted, so existing
  `.env` files and deployments keep working.
- pgvector is installed into the `extensions` schema, as Supabase recommends.
- Free-tier and dashboard guidance updated throughout: Supabase pauses free projects
  on a 7-day low-activity window with a 90-day restore limit, keys live under
  **Settings → API Keys**, and the project URL sits behind **Connect**.
- `speaker/` moved to `docs/` and reframed as reusable examples rather than notes for
  one specific delivery.

<!-- e.g., -->
<!-- Unreleased -->
<!-- v2.0.0 -->
<!-- v1.1.0 -->
<!-- v1.0.0 -->
<!-- v0.0.1 -->

[Unreleased]: https://github.com/dileepadev/deploying-agentic-ai-apps-workshop/branches
