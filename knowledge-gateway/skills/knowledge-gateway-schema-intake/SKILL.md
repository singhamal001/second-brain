# Skill: knowledge-gateway-schema-intake

## Version
2026-04-19

## Purpose
Handle prompts like "create a database/table" using safe dynamic-table workflows in the existing KG Postgres.

## Canonical Mapping
- "create database" means `create_dynamic_table`.
- Never provision external database infrastructure from this intent.

## Clarification Batch (ask once if missing)
1. Scope: global / employer / project / cross-employer
2. Table purpose (business intent)
3. Required columns and types

## Scope Model
- `global`
- `employer_all_projects`
- `single_project`
- `multi_employer_or_multi_project`

## Table Naming Policy (auto_prefix_by_scope)
- global: `global_<name>`
- employer: `<employer_slug>_<name>`
- project: `<employer_slug>_<project_slug>_<name>`

## Column Safety
- Use gateway-supported types only: text/string/int/float/bool/datetime/json.
- Avoid reserved metadata columns (`id`, `created_at`, `updated_at`, `archived`).

## Checksum Discipline
- Treat this as strict policy text.
- Update through `update_gateway_skill` with reason.
