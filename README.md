# British Auction RFQ

An RFQ (Request For Quotation) system where suppliers compete in a **British (reverse) auction**:
bids only go down, and late activity extends the auction up to a hard **forced close**.

- Buyers create RFQs with an auction window and extension rules (trigger window X, extension Y, trigger type).
- Suppliers place bids (freight + origin + destination charges); the lowest total is L1.
- A bid in the last X minutes that matches the trigger pushes the close out by Y minutes, never past the forced close.

**Stack:** FastAPI · PostgreSQL · SQLAlchemy · Alembic · Celery + Redis · React (Vite, TanStack Query, React Router, Tailwind CSS)

## Design documents

- **[High-Level Design](docs/HLD.md)**: architecture diagram, components, auction lifecycle, bid flow, scaling notes
- **[Database Schema](docs/SCHEMA.md)**: ER diagram, tables, constraints, indexes, design decisions

## Run it

**Needs:** Docker (with Compose), [uv](https://docs.astral.sh/uv/), Node.js 20+, make (optional).

```bash
cp .env.example .env   # change ports here if 5432 / 6379 / 8000 are taken
make infra             # postgres + redis in docker
make install           # backend dependencies (uv installs Python 3.12 too)
make migrate           # create the tables
make seed              # demo data: 1 buyer, 3 suppliers, 4 auctions (one per status)
make web-install       # frontend dependencies

make api               # terminal 1: API at http://localhost:8000 (Swagger at /docs)
make worker            # terminal 2: Celery worker
make beat              # terminal 3: Celery beat, closes expired auctions every 5 s
make web               # terminal 4: UI at http://localhost:5173
```

Open http://localhost:5173 and pick a user in the top-right corner ("Acting as"). Buyers
create RFQs; suppliers place bids. There is no login: the UI sends the chosen user as an
`X-User-Id` header. Every `make` target is a plain command; see the `Makefile`.

## Project structure

```
backend/    FastAPI app (api/ routers, services/, engine.py auction rules, models/, worker/ Celery)
frontend/   React + Vite + Tailwind (pages/: listing, create RFQ, details; components/)
docs/       HLD.md (architecture), SCHEMA.md (database design)
```

## Testing

```bash
make test     # 48 backend tests: auction rules, API, Celery sweep, 20 parallel bids
```

With the API running, every endpoint can also be tried at http://localhost:8000/docs (Swagger UI).

## Assumptions

The assignment leaves some rules open. These are the decisions made:

| # | Question | Decision |
|---|---|---|
| A1 | What is ranked? | `total_price = freight + origin + destination`. Lowest = L1. |
| A2 | Can a supplier bid many times? | Yes, but each new bid must be strictly lower than their own latest bid. |
| A3 | Must a bid beat L1? | No. Otherwise L2/L3 could never move and rank-change triggers would be meaningless. |
| A4 | Tie-break | Equal totals: the earlier bid ranks higher. |
| A5 | Trigger window | `[current_close − X, current_close)`, start inclusive. It moves when the close extends. |
| A6 | Bid exactly at close time | Rejected. Bids are valid only while `now < current_close`. |
| A7 | Extension rule | `new_close = min(current_close + Y, forced_close)`: Y is added to the close, not to the bid time. |
| A8 | "Rank change" | Any existing supplier's position differs before vs after. A new supplier entering last doesn't count; entering ahead of others does. |
| A9 | "L1 change" | The L1 supplier differs before vs after. The very first bid counts. |
| A10 | Closed vs Force Closed | Final close == forced close → FORCE_CLOSED, else CLOSED. |
| A11 | Already at forced cap | A triggering bid is accepted, but no extension is logged. |
| A12 | Auth | None: an `X-User-Id` header plus a user switcher in the UI. JWT is future work. |
| A13 | Time | Everything is UTC `timestamptz`; the server is the only clock; the UI shows IST. |
| A14 | Money | `NUMERIC(14,2)` / Python `Decimal`. Never float. |
| A15 | British Auction option | Always on: every RFQ is a British auction (the spec only asks for RFQs with it enabled). |
| A16 | "All supplier bids" vs "ranking" | Details shows both: a ranking of each supplier's latest bid (L1, L2, ...) and every bid ever placed, sorted by price. |
