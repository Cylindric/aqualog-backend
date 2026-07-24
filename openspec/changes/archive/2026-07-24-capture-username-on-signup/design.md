## Context

`User` rows are created in `UserRepository.create_for_identity` (via `resolve_or_create`), called from `user_service.resolve_or_create_authenticated_user` on first-ever authenticated request for an OAuth identity. Today only `oauth_issuer` and `oauth_subject` are stored; `display_name`/`bio` are user-editable via `PATCH` on the profile endpoint (`src/profile.py`) and are `null` until the user sets them. The OIDC token claims dict already flows into `resolve_or_create_authenticated_user` but is discarded after extracting `iss`/`sub`.

## Goals / Non-Goals

**Goals:**
- Capture the OAuth provider's `preferred_username` claim into a new `username` column at the moment a local `User` row is first created.
- Surface `username` as a read-only field in the profile response.
- Add the Alembic migration for the new column.

**Non-Goals:**
- Backfilling `username` for existing users (out of scope; no historical claims data available).
- Making `username` editable through the profile update endpoint — it is provider-sourced, not user-owned.
- Re-syncing `username` on every login if it changes at the IdP (only captured at creation, consistent with how `oauth_issuer`/`oauth_subject` are handled).

## Decisions

- **Column is nullable**: not every IdP/token guarantees `preferred_username`. Storing `null` and letting signup proceed avoids adding a hard dependency on IdP claim configuration. Alternative considered: reject login if missing — rejected, since it would turn a cosmetic field into an auth outage risk.
- **Captured only at creation, not on every login**: matches existing precedent (`oauth_issuer`/`oauth_subject` are also fixed at creation) and avoids surprise mutations to a field the user didn't choose. Alternative considered: sync on every login — rejected for this change to keep scope small; can be a follow-up if needed.
- **Read-only in profile API**: `username` represents the IdP identity, distinct from `display_name` which is already the user-editable "name" field. Allowing `PATCH` to overwrite it would conflate the two.
- **No new capability/spec**: this extends the existing `api-user-persistence` (creation behavior) and `api-user-profile` (read exposure) capabilities rather than introducing a new one.

## Risks / Trade-offs

- [Risk] IdP token doesn't include `preferred_username` for some users → column stays `null` for those users indefinitely. → Mitigation: documented as expected/non-goal; a future change can add on-login sync or backfill if this becomes a real problem.
- [Risk] Migration adds a column to a live `users` table. → Mitigation: nullable column with no default backfill required; safe additive migration, no lock-heavy rewrite.

## Migration Plan

1. Add `username` column (nullable `String`) to `User` model.
2. Generate Alembic migration (`alembic revision --autogenerate`), verify it only adds the nullable column.
3. Update `UserRepository.create_for_identity` to accept and persist `username`.
4. Update `user_service.resolve_or_create_authenticated_user` to extract `preferred_username` from claims and pass it through.
5. Update `src/profile.py` response payload to include `username` (read-only).
6. Run `alembic upgrade head` as part of normal deploy; no rollback complexity beyond standard `alembic downgrade`.

## Open Questions

- None blocking; on-login sync of `username` for existing users can be revisited later if requested.
