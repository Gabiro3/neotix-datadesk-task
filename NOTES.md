# Engineering Notes

## 1. Design

### Architecture

The system is a React/Vite single-page application backed by a modular FastAPI API and PostgreSQL. The backend is divided into routers, domain services, SQLAlchemy models, and migration-managed persistence. PostgreSQL is the source of truth; the frontend only keeps the current session and transient interface state.

The main relational entities are:

- `users`: unique email, bcrypt password hash, role, active state, organisation, and `must_change_password`.
- `episodes`: canonical unique `episode_id`, robot/task metadata, recording time, duration, operator, and quality.
- `requests`: client ownership, requested task/count, deadline, notes, and current workflow status.
- `assignments`: joins an episode to a request. A database unique constraint on `episode_id` guarantees that one episode cannot be assigned to two requests.
- `request_events`: append-only audit records for every status transition, including actor and timestamp.

The current status is stored on `requests` for efficient listing and filtering, while `request_events` provides the immutable history. Both are updated in one transaction by the transition service.

JWTs identify the user, but they are not treated as the final authorization source. Every authenticated request reloads the user from PostgreSQL, verifies that the account is active, checks the current role, and blocks users whose temporary password has not been replaced.

### Important decisions

1. **Temporary passwords for administrator-created users.** An administrator needs a practical way to provision an account without knowing the user's permanent password. New accounts therefore receive a temporary password and `must_change_password=true`. After login, the API rejects all normal protected endpoints until the user verifies the temporary password and chooses a different password of at least eight characters. This is enforced server-side, including the SSE endpoint, rather than relying on a frontend redirect. Seed users are explicitly exempt because they are documented test accounts.

2. **Database-enforced assignment and workflow rules.** Readable service-level validation produces useful `409` responses, but correctness does not depend on application timing. The assignment table's unique constraint remains the final protection against concurrent double assignment. Delivery also checks the assigned count in the database before allowing the status transition.

3. **Normalize safe CSV differences, reject ambiguous data.** Whitespace, casing, supported date formats, and fractional duration are normalized. Missing identifiers, unknown robots, invalid quality values, invalid dates, and unrealistic durations are skipped with row-level reasons. Re-importing unchanged data is a no-op; a valid changed row with the same canonical ID updates the existing episode.

4. **Dynamic analytics filters for informed decisions.** Operators can filter analytics by date range, operator, robot, task, and quality. These filters are applied in SQL rather than to an incomplete browser payload. The endpoint also returns distinct filter options for the selected period. Request-status and fulfilment metrics remain request-level measures, while episode filters affect recording throughput and task-quality analysis.

5. **Charts in addition to tabular numbers.** Daily grouped robot bars, status distributions, robot totals, and top-task bars make operational patterns easier to understand than raw values alone. The visualizations are deliberately lightweight React/CSS components rather than a large charting dependency. They retain accessible labels and hover details while keeping the bundle small.

6. **Role picker on login without trusting the browser.** The role picker selects an appropriate seeded demonstration profile and makes evaluation faster. It is not authorization: the submitted email/password is authenticated normally and the returned server-side role determines access.

7. **SSE as the selected stretch item.** Operators receive request creation and status changes without refreshing. The browser uses `fetch` with a `ReadableStream`, which allows a Bearer header unlike native `EventSource`. The current in-process event bus is intentionally simple for one API replica.

## 2. Deliberate simplifications and next steps

Deliberately left out:

- Cursor pagination. The episode endpoint is capped at 500 rows.
- Password reset/email delivery, refresh-token rotation, MFA, and SSO.
- Organisation-level tenancy beyond clients only seeing their own requests.
- Assignment audit events; status events are audited, assignments currently are not.
- Background export jobs and public deployment, since SSE was the chosen stretch item.
- A production semantic/vector search service. Request search currently performs useful intent/synonym matching over loaded requests.

With two more days I would add cursor pagination, assignment audit records, password-reset delivery, and a suggested-episode query ordered by exact task match and quality. I would also generate the larger dataset, capture `EXPLAIN (ANALYZE, BUFFERS)` output for every analytics query, and add a PostgreSQL integration-test job so dialect-specific analytics are tested in CI.

## 3. What went wrong and diagnosis

The first PostgreSQL startup failed because the initial migration explicitly created enum types and SQLAlchemy's generic `Enum` table metadata attempted to create the same types again. The partial failed run left `user_role` behind, so retries failed with `DuplicateObject`. I diagnosed it from the failing SQL in the container logs, replaced migration enum columns with PostgreSQL types that do not auto-create, and made type creation idempotent. The initial migration now safely handles a retry after a partially failed first run.

There was also a local port conflict: Oracle XE already owned IPv4 port 8080, while Docker appeared reachable through another address. Comparing `curl` responses and server headers exposed that requests were reaching Oracle rather than nginx. The frontend was moved to port 3000.

A third issue was SSE authentication. Native `EventSource` cannot set an `Authorization` header. The frontend now consumes the stream with authenticated `fetch` and `ReadableStream`. Temporary-password enforcement was also added to the SSE authentication path so it cannot bypass the first-login gate.

## 4. Security

- Passwords are bcrypt hashes and are never logged or returned.
- Administrator-created passwords are temporary and must be replaced on first login.
- JWTs expire after 12 hours and use a secret supplied through the environment.
- Deactivation and temporary-password state are checked against the live user record on every protected request.
- Pydantic validates API input; CSV rows receive separate domain validation.
- Authorization is server-side. Clients only query their own requests, operators cannot manage users, and only administrators can provision/deactivate accounts or change roles.
- Access to another client's request returns `404`, avoiding an existence leak.

The two main production concerns are:

1. **Token theft/XSS.** Tokens currently live in `localStorage`. I would move to short-lived access tokens in secure, httpOnly, same-site cookies with refresh rotation and CSRF protection.
2. **Privileged internal-account compromise.** Operators can view all episodes and assignments by design. I would add MFA/SSO, assignment audit logs, anomaly alerts, and optional approval for final delivery.

The development JWT fallback must never be used in production, and the query-token compatibility path for SSE should be removed before public deployment.

## 5. Scale

At 10x users, stateless API replicas and PostgreSQL connection pooling are sufficient. The in-process SSE bus is the first multi-replica limitation; Redis pub/sub or PostgreSQL `LISTEN/NOTIFY` would provide shared fan-out.

At 100x episodes, the first pressure points are available-episode filtering and date-range analytics. The current indexes support the initial workload, but tens of millions of episodes would justify date partitioning, covering indexes for common robot/operator/date filters, pre-aggregated daily metrics, and a read replica for analytics. Import should move from ORM row handling to PostgreSQL staging tables plus `COPY`, validation SQL, and `INSERT ... ON CONFLICT` batches.

Concurrent assignment remains safe because PostgreSQL owns the uniqueness guarantee. More contention would require retrying unique-constraint conflicts and possibly reserving episodes with `SELECT ... FOR UPDATE SKIP LOCKED`.

## 6. AI tooling

I used OpenCode as a pair-programming assistant to inspect the task, scaffold and refine the FastAPI/React implementation, diagnose Docker/PostgreSQL/nginx issues, add tests, and improve documentation. I selected the architecture, PostgreSQL, SSE stretch item, domain behavior, import policy, security flow, analytics filters, and interface direction. I reviewed and adjusted the generated implementation, and verified it with the automated tests, production frontend builds, migrations, health checks, and filtered analytics calls.

## CSV import policy

| Input case | Decision |
|---|---|
| Missing or malformed `episode_id` | Skip |
| Duplicate ID in the same file | Keep first valid row; skip later rows |
| Unknown or missing robot | Skip |
| Missing/invalid date | Skip |
| Implausibly future date | Skip |
| Non-positive, missing, `N/A`, or extreme duration | Skip |
| Quality outside `good`, `usable`, `bad` | Skip |
| Mixed case or surrounding whitespace | Normalize |
| Supported ISO, space-separated, `Z`, or day-first date | Parse as UTC |
| Fractional duration such as `45.5` | Round to nearest second |
| Quoted task containing a comma | Accept |
| Identical re-import | Skip as unchanged |
| Same ID with changed valid metadata | Update |

Known robots are `arm-01`, `arm-02`, `arm-03`, `mobile-01`, and `humanoid-01`.
