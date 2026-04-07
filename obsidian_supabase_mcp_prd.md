# Product Requirements Document (PRD)
## MCP + Backend Knowledge Operations Platform for Obsidian and Supabase

## 1. Executive Summary

Build a self-hosted knowledge operations platform that allows AI assistants and coding agents to write structured and unstructured project memory into two systems at the same time:

1. **Obsidian Vault** on the user's Contabo VPS for rich, narrative, markdown-first knowledge capture.
2. **Supabase / Postgres** for structured, queryable timelines, commitments, meeting notes, decisions, dependencies, and project activity.

The platform should expose controlled tools through an **MCP server** and optionally a supporting **backend API service** so that assistants like Codex / Claude Code / other agentic tooling can:

- log progress after coding sessions,
- create structured project records,
- update timelines,
- capture decisions and tradeoffs,
- generate reports,
- retrieve project history,
- surface next steps and open dependencies,
- maintain reusable knowledge like `Skills.md`, patterns, lessons, and implementation notes.

The goal is to make the user continuously up to date across projects, employers, and active workstreams, while keeping both a human-friendly second brain and a machine-friendly operational memory.

---

## 2. Problem Statement

The user works across multiple projects, technologies, and employers. Important project memory is currently fragmented across:

- code sessions,
- chats with AI assistants,
- meetings,
- local notes,
- ad hoc documents,
- memory of technical decisions,
- scattered task updates.

This creates several problems:

### 2.1 Loss of operational context
After a coding session or meeting, valuable context is often lost unless manually written down.

### 2.2 Weak continuity across sessions
When resuming a project later, the user must reconstruct:
- what changed,
- why it changed,
- what tradeoffs were made,
- what the next steps are,
- who is responsible for what.

### 2.3 Poor reporting readiness
The user wants assistants to be able to quickly produce status reports, summaries, and project updates. That requires historical records in both narrative and structured form.

### 2.4 Lack of unified personal/project memory
Some information is best stored as markdown and reflection. Some is best stored as structured rows and timelines. Today these are not unified.

### 2.5 Difficulty reusing learning and patterns
Useful lessons, methodology decisions, and implementation patterns are often not normalized into reusable knowledge artifacts.

---

## 3. Product Vision

Create a **Knowledge Logging and Retrieval Layer** that sits between AI assistants and the user’s working systems.

This layer should allow an assistant to do the following reliably:

- understand what project or employer a session belongs to,
- log structured updates into Postgres,
- create or update markdown entries in Obsidian,
- preserve decisions, tradeoffs, and rationale,
- maintain a timeline of work,
- generate reports on demand,
- make retrieval easy by project, employer, date, topic, or task.

The platform should feel like a persistent operational memory system for technical work.

---

## 4. Primary Objectives

### 4.1 Build persistent project memory
Every meaningful session should leave behind a usable record.

### 4.2 Separate narrative and structured memory correctly
- **Obsidian** should store long-form context, notes, thought process, methodology, learnings, and evolving documents.
- **Supabase/Postgres** should store normalized, queryable events and entities.

### 4.3 Enable AI-driven reporting
The assistant should be able to pull relevant data and generate:
- daily updates,
- weekly reports,
- meeting follow-ups,
- status summaries,
- decision summaries,
- employer/project utilization timelines.

### 4.4 Improve continuity between sessions
After any coding or project session, the assistant should know how to write a memory trail that is easy to resume later.

### 4.5 Reduce manual note discipline burden
The system should make high-quality logging lightweight and structured enough that the user actually uses it.

---

## 5. Core User Idea (Expanded)

The user has already identified two strong foundational use cases.

### 5.1 Use Case A: Post-coding session logging
After each coding session, especially one involving Codex or another assistant, the system should log:

- project name,
- employer/client,
- date and time,
- session objective,
- work completed,
- files/modules changed,
- approach chosen,
- alternatives considered,
- thought process,
- tradeoffs,
- advantages and disadvantages,
- blockers,
- risks,
- next steps,
- learnings,
- documentation changes,
- `Skills.md` additions,
- prompts / agentic workflow notes,
- outstanding questions.

This should produce:
- a **structured record** in Postgres,
- a **markdown session note** in Obsidian.

### 5.2 Use Case B: Project/employer operational timeline
For each project and employer, the user wants a timeline of events such as:

- meetings,
- commitments,
- dependencies,
- updates,
- responsibilities,
- mentions by stakeholders,
- changes in priorities,
- deliverables,
- timelines,
- follow-ups.

This timeline should support retrieval like:
- “What did Sneha say last week about Project Alpha?”
- “What commitments were made for Benori this month?”
- “What changed in this project after the 10:00 AM meeting?”
- “What dependencies are still open?”

---

## 6. Expanded Use Cases That Should Be Included

Below are additional use cases that are highly relevant and should be part of the product scope.

### 6.1 Daily worklog generation
At the end of the day, the system should be able to summarize all project activity into a daily worklog.

### 6.2 Weekly status report generation
The system should create employer/project-specific weekly reports from both Obsidian entries and database records.

### 6.3 Meeting intelligence logging
After a meeting, the assistant should extract and store:
- participants,
- summary,
- decisions,
- next steps,
- commitments,
- deadlines,
- blockers,
- dependencies,
- unresolved items.

### 6.4 Decision register
Maintain a formal decision log:
- decision title,
- context,
- chosen option,
- rejected options,
- rationale,
- pros/cons,
- impact.

### 6.5 Architecture / methodology memory
Track why a certain service, framework, architecture, or methodology was chosen.

### 6.6 Task continuity memory
At the end of a session, maintain a handoff note:
- where work stopped,
- what to do next,
- what files matter,
- what assumptions are currently in play.

### 6.7 Skills and capability growth tracking
Capture newly learned tools, patterns, workflows, prompt strategies, or architecture concepts into `Skills.md` or similar vault areas.

### 6.8 Employer/project utilization history
Track where time and attention were spent across employers/projects over time.

### 6.9 Dependency and blocker tracking
Maintain structured records of blockers, owners, due dates, escalation needs, and status changes.

### 6.10 Prompt / agent workflow memory
Capture prompt patterns, agent orchestration strategies, and useful coding workflows discovered during work.

### 6.11 Resume / portfolio evidence capture
Extract implementation evidence and achievements that can later be reused for resumes, portfolios, or interview examples.

### 6.12 Report-on-demand use case
Assistant should answer prompts like:
- “Generate a status report for Benori Project Alpha for the last 7 days.”
- “Summarize all technical decisions taken in this workstream.”
- “What did we learn while implementing the MCP backend?”
- “Show me unresolved dependencies across all employers.”

### 6.13 Personal second-brain enrichment
Convert raw work logs into higher-value notes:
- patterns,
- reusable playbooks,
- architecture notes,
- lessons learned,
- anti-patterns.

### 6.14 Session-to-session continuity with agents
At the start of a new coding session, the assistant should fetch prior notes, next steps, unresolved items, and relevant session history automatically.

---

## 7. Users

### 7.1 Primary user
The user themselves: a multi-project technical professional using AI assistants heavily for coding, architecture, planning, and documentation.

### 7.2 Secondary user
AI assistants and coding agents acting on behalf of the user via MCP and/or backend API tools.

### 7.3 Tertiary user
Future reporting or dashboard interfaces that may query structured project history.

---

## 8. Product Scope

## 8.1 In scope

### Knowledge capture
- session logging,
- meeting logging,
- decision logging,
- project update logging,
- blocker/dependency logging,
- skills capture,
- structured timeline storage,
- markdown documentation generation.

### Knowledge retrieval
- retrieve by employer,
- retrieve by project,
- retrieve by date range,
- retrieve by person,
- retrieve by category,
- retrieve by open item status.

### Knowledge synthesis
- generate summaries,
- generate reports,
- generate handoffs,
- generate weekly updates,
- generate decision summaries,
- generate learning summaries.

### Systems integration
- Obsidian Vault,
- Supabase/Postgres,
- MCP server,
- backend API server.

## 8.2 Out of scope for Phase 1
- advanced analytics dashboards,
- embeddings/vector search,
- automatic calendar/email ingestion,
- enterprise workflow automation,
- mobile-native app,
- multi-user collaboration,
- complex RBAC,
- real-time event streaming.

These can be future phases.

---

## 9. Recommended Product Architecture

## 9.1 High-level architecture

```text
AI Assistant / Codex / Claude Code
            │
            ▼
        MCP Server
            │
            ├── Obsidian Service Layer
            │       ├── create/update markdown notes
            │       ├── append session logs
            │       ├── update Skills.md
            │       └── retrieve notes by project/topic/date
            │
            └── Backend API Layer
                    ├── validation
                    ├── normalization
                    ├── business rules
                    ├── structured event creation
                    └── Supabase/Postgres writes & reads
```

## 9.2 Why both MCP and backend API may be needed

### MCP server role
MCP is the tool interface used by assistants to call capabilities safely and consistently.

### Backend API role
A backend API service is useful because it can centralize:
- validation,
- authentication,
- transformation,
- business rules,
- idempotency,
- database access,
- file path controls,
- audit logging.

### Recommendation
Use:
- **MCP server** as the assistant-facing tool layer.
- **Backend API** as the system-facing application layer.

This keeps the MCP server thin and the business logic centralized.

---

## 10. Obsidian Role in the System

Obsidian should be the home for narrative and human-readable memory.

## 10.1 What belongs in Obsidian
- session notes,
- project journals,
- worklogs,
- architecture notes,
- technical reflections,
- meeting summaries,
- decisions in narrative form,
- methodology notes,
- learning notes,
- `Skills.md` updates,
- project summary pages,
- reusable patterns.

## 10.2 Recommended vault structure

```text
Projects/
  Employer A/
    Project Alpha/
      Sessions/
      Meetings/
      Decisions/
      Reports/
      Architecture/
  Employer B/
    Project Beta/

Daily Notes/
Skills/
  Skills.md
Learnings/
Templates/
Reports/
Inbox/
```

## 10.3 Example markdown artifacts
- Session note: `Projects/Benori/Project Alpha/Sessions/2026-04-07-session.md`
- Meeting note: `Projects/Benori/Project Alpha/Meetings/2026-04-07-sneha-sync.md`
- Decision note: `Projects/Benori/Project Alpha/Decisions/decision-use-fastapi.md`
- Weekly report: `Reports/Benori/2026-W14.md`

---

## 11. Supabase / Postgres Role in the System

Supabase should be the structured memory and reporting layer.

## 11.1 What belongs in Postgres
- employers,
- projects,
- people/stakeholders,
- sessions,
- meetings,
- decisions,
- tasks,
- next steps,
- blockers,
- dependencies,
- commitments,
- events,
- artifacts,
- learnings,
- tags,
- activity logs.

## 11.2 Why structured storage matters
It enables:
- filtering,
- timelines,
- joins,
- query-driven reporting,
- dashboards,
- unresolved item tracking,
- person/project/date-based retrieval.

---

## 12. Proposed Phase 1 Data Model

Below is a practical Phase 1 relational model.

### 12.1 `employers`
- id
- name
- description
- active
- created_at

### 12.2 `projects`
- id
- employer_id
- name
- code_name
- description
- status
- start_date
- end_date
- created_at

### 12.3 `people`
- id
- employer_id
- name
- role
- email
- notes
- created_at

### 12.4 `sessions`
- id
- project_id
- employer_id
- started_at
- ended_at
- source (`codex`, `manual`, `meeting-followup`, etc.)
- title
- objective
- summary
- thought_process
- methodology
- major_changes
- advantages
- disadvantages
- learnings
- next_steps
- blockers
- skills_updates
- obsidian_note_path
- created_at

### 12.5 `meetings`
- id
- project_id
- employer_id
- meeting_datetime
- title
- summary
- attendees_json
- decisions_json
- next_steps_json
- dependencies_json
- commitments_json
- obsidian_note_path
- created_at

### 12.6 `decisions`
- id
- project_id
- employer_id
- title
- context
- chosen_option
- rejected_options_json
- rationale
- pros
- cons
- impact
- status
- obsidian_note_path
- created_at

### 12.7 `tasks`
- id
- project_id
- employer_id
- title
- description
- owner_person_id
- status
- due_date
- source_type
- source_id
- created_at

### 12.8 `dependencies`
- id
- project_id
- employer_id
- title
- description
- dependency_type
- owner_person_id
- status
- due_date
- related_meeting_id
- created_at

### 12.9 `artifacts`
- id
- project_id
- employer_id
- artifact_type
- title
- obsidian_path
- linked_record_type
- linked_record_id
- created_at

### 12.10 `activity_log`
- id
- action_type
- source_system
- target_system
- project_id
- employer_id
- payload_json
- status
- created_at

---

## 13. Core Tooling / MCP Capabilities

The MCP server should expose a clean, deliberate set of tools.

## 13.1 Logging tools
- `log_coding_session`
- `log_meeting`
- `log_decision`
- `log_project_update`
- `log_learning`
- `update_skills`

## 13.2 Retrieval tools
- `get_project_summary`
- `get_project_timeline`
- `get_recent_sessions`
- `get_open_dependencies`
- `get_decisions_by_project`
- `get_meetings_by_person`
- `get_obsidian_note`

## 13.3 Reporting tools
- `generate_daily_report`
- `generate_weekly_status_report`
- `generate_meeting_followup`
- `generate_decision_report`
- `generate_resume_evidence`

## 13.4 Maintenance tools
- `create_project`
- `create_employer`
- `create_person`
- `link_obsidian_note`
- `repair_record_links`

---

## 14. Example User Flows

## 14.1 Post-coding session flow
1. Coding session ends.
2. User or assistant calls `log_coding_session`.
3. Backend validates project/employer.
4. System writes structured session row to Supabase.
5. System generates or updates markdown session note in Obsidian.
6. Relevant learnings update `Skills.md` if approved.
7. Assistant can later generate a report from these records.

## 14.2 Meeting capture flow
1. User provides meeting notes/transcript summary.
2. Assistant calls `log_meeting`.
3. Backend extracts attendees, decisions, next steps, dependencies.
4. Data is written to structured tables.
5. Markdown meeting note is created in Obsidian.
6. Open commitments become queryable later.

## 14.3 Project report flow
1. User asks: “Summarize Project Alpha from last 7 days.”
2. Assistant calls retrieval/report tools.
3. Backend fetches sessions, meetings, tasks, decisions.
4. Optional Obsidian notes are pulled for richer context.
5. Assistant returns a generated report.

## 14.4 Skills update flow
1. User learns a new tool/pattern.
2. Assistant calls `update_skills`.
3. Backend appends structured learning record.
4. Obsidian `Skills.md` and/or learning note is updated.

---

## 15. Functional Requirements

## 15.1 Logging requirements
The system must:
- support logging by employer and project,
- support both structured and markdown storage,
- support manual and assistant-driven logging,
- allow logging with partial data and progressive enrichment,
- attach timestamps automatically,
- preserve original input where useful.

## 15.2 Obsidian requirements
The system must:
- create markdown files in controlled paths,
- use templates for note generation,
- support append and overwrite modes carefully,
- maintain stable note paths,
- optionally link notes to database records.

## 15.3 Database requirements
The system must:
- validate project/employer references,
- maintain referential integrity,
- support querying by time range,
- support open/closed status filtering,
- support person/project/employer scoping.

## 15.4 Reporting requirements
The system must:
- generate summaries from structured records,
- optionally enrich summaries from Obsidian notes,
- provide project-specific and employer-specific reports,
- provide both concise and detailed report formats.

## 15.5 MCP requirements
The system must:
- expose a small, well-defined tool surface,
- validate parameters,
- return predictable structured responses,
- avoid unrestricted filesystem access,
- avoid unrestricted SQL access.

## 15.6 Backend requirements
The backend API must:
- authenticate requests,
- validate payloads,
- enforce path and schema constraints,
- log operations,
- support idempotent writes where appropriate,
- handle failures gracefully.

---

## 16. Non-Functional Requirements

### Security
- restrict vault access to approved paths,
- avoid arbitrary file writes,
- use server-side credentials for Supabase,
- protect secrets,
- maintain Cloudflare Access / VPS security posture.

### Reliability
- logging should not silently fail,
- retries should be controlled,
- write operations should return confirmation.

### Auditability
- every write should be traceable,
- system should log source assistant/tool and timestamp.

### Maintainability
- modular codebase,
- schema migration support,
- templates separated from business logic.

### Scalability
- should support multiple employers/projects,
- should support growing history volume without redesign.

---

## 17. Risks and Design Considerations

### 17.1 Duplicate logging
Same session or meeting may be logged multiple times.

**Mitigation:** idempotency keys, source IDs, dedupe logic.

### 17.2 Poor data quality
If assistants log vague records, structured data becomes unreliable.

**Mitigation:** validation, required fields, templates.

### 17.3 Over-automation of note changes
AI may overwrite useful human notes.

**Mitigation:** controlled append-only strategy for some note types.

### 17.4 Excessive complexity too early
Trying to build analytics, embeddings, ingestion, and dashboards all at once will slow delivery.

**Mitigation:** keep Phase 1 narrow and reliable.

### 17.5 Mixed source of truth confusion
If both Obsidian and Postgres hold overlapping information, ownership can become unclear.

**Mitigation:** define ownership:
- Obsidian = narrative source,
- Postgres = structured operational source.

---

## 18. Recommended Phase Breakdown

## Phase 1 — Core logging foundation
Deliver:
- backend API service,
- Postgres schema,
- MCP server,
- core logging tools,
- controlled Obsidian note creation,
- project/employer/person registry,
- basic reporting tools.

### Success criteria
- can log sessions,
- can log meetings,
- can log decisions,
- can retrieve project timeline,
- can generate basic report.

## Phase 2 — Better retrieval and templates
Deliver:
- richer templates,
- report variations,
- cross-linking between notes and records,
- better next-step extraction,
- improved dependency tracking.

## Phase 3 — Intelligence layer
Deliver:
- semantic retrieval,
- recommendation layer,
- proactive next-step reminders,
- relationship extraction,
- stronger search.

## Phase 4 — Observability and dashboards
Deliver:
- utilization dashboard,
- project health dashboard,
- open blockers dashboard,
- employer/project reporting UI.

---

## 19. MVP Definition

The MVP should allow the following end-to-end use cases:

1. Create employer and project.
2. Log a coding session.
3. Log a meeting.
4. Log a decision.
5. Write markdown notes into Obsidian with consistent templates.
6. Store structured rows in Supabase.
7. Retrieve project timeline.
8. Generate a weekly report.
9. Update `Skills.md` safely.

If these are working reliably, the MVP is successful.

---

## 20. Suggested API / MCP Contract Style

Each tool should accept explicit structured input.

### Example: `log_coding_session`
Input:
- employer_name
- project_name
- session_title
- started_at
- ended_at
- objective
- summary
- thought_process
- methodology
- major_changes
- advantages
- disadvantages
- blockers
- next_steps
- learnings
- skills_updates
- tags

Output:
- session_id
- obsidian_note_path
- project_id
- created_at
- status

### Example: `log_meeting`
Input:
- employer_name
- project_name
- meeting_title
- meeting_datetime
- attendees
- summary
- decisions
- dependencies
- commitments
- next_steps
- tags

Output:
- meeting_id
- obsidian_note_path
- extracted_task_count
- extracted_dependency_count
- status

---

## 21. Recommended Implementation Stack

### Backend API
- FastAPI
- Pydantic
- SQLAlchemy or direct Supabase/PostgREST pattern
- Alembic for migrations

### MCP server
- Python MCP server wrapping backend operations
- tools mapped to internal service methods

### Storage
- Supabase Postgres
- Obsidian vault on VPS filesystem

### Deployment
- VPS-hosted API service
- MCP service on VPS
- Cloudflare-protected app surfaces if needed

---

## 22. Design Principles

1. **Write once, store twice appropriately.**
2. **Narrative memory and structured memory serve different purposes.**
3. **Do not expose raw filesystem or raw SQL to assistants.**
4. **Prefer narrow, explicit tools over generic tools.**
5. **Use templates to normalize note quality.**
6. **Make end-of-session logging frictionless.**
7. **Keep Phase 1 practical and dependable.**

---

## 23. Success Metrics

### Adoption metrics
- % of coding sessions logged
- % of meetings logged
- number of project notes created per week

### Retrieval metrics
- time to generate report
- time to resume a paused project
- number of answered project-history questions

### Quality metrics
- completeness of logs
- reduction in forgotten next steps
- decision traceability
- dependency traceability

### User value metrics
- improved continuity across sessions
- improved reporting readiness
- improved recall of technical rationale
- improved reuse of learnings and skills additions

---

## 24. Final Recommendation

The right approach is **not just an MCP server alone**.

The best architecture for this product is:

- **MCP server** as the assistant-facing tool layer,
- **Backend API server** as the business logic and validation layer,
- **Supabase/Postgres** as structured memory,
- **Obsidian** as narrative/project knowledge,
- optional future reporting/dashboard layer later.

This will give the user a reliable, extensible knowledge operations system that supports multiple employers, multiple projects, AI-assisted coding, project continuity, and high-quality reporting.

---

## 25. Recommended Immediate Next Deliverables

The next step after this PRD should be:

1. Finalize Phase 1 data model.
2. Define exact MCP tools and payload schemas.
3. Design folder conventions for Obsidian.
4. Design backend API endpoints.
5. Implement write path for:
   - coding session logging,
   - meeting logging,
   - decision logging,
   - skills updates.
6. Add retrieval/reporting endpoints.
7. Add authentication and audit logging.

---

## 26. Summary in One Line

Build a self-hosted assistant-operable knowledge platform where every important work session, meeting, decision, and learning is captured in both **Obsidian for human memory** and **Supabase for structured operational intelligence**.

