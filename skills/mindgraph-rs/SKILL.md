---
name: mindgraph
version: 5.0.5
description: "Structured knowledge graph with 18 cognitive tools for agent memory and reasoning (server v0.8.0)"
author: shuruheel
---

# MindGraph Skill

MindGraph is a **structured knowledge graph index** for sub-agents, cross-file constraint lookups, and semantic search. Files (MEMORY.md, daily notes) are canonical — MindGraph provides structured relationships and search on top of them.

---

## Setup: Cloud vs Local

MindGraph can run as a **cloud API** or a **local self-hosted server**. Set two env vars to choose:

### Cloud API (recommended — no server, no binary, embeddings included)
```bash
export MINDGRAPH_URL=https://api.mindgraph.cloud
export MINDGRAPH_TOKEN=your-api-key   # from mindgraph.cloud/signup
```
- No binary to install or start
- Embeddings handled server-side — no `OPENAI_API_KEY` needed
- `start.sh` is a no-op when `MINDGRAPH_URL` starts with `https://`

### Local Server (self-hosted)
```bash
bash install.sh       # downloads pre-built binary from GitHub Releases
bash start.sh         # starts server on port 18790
export OPENAI_API_KEY=sk-...   # required for semantic/hybrid search
```
- Runs at `http://127.0.0.1:18790` by default
- Token auto-generated and saved to `data/mindgraph.json` on first start
- `MINDGRAPH_TOKEN` is read from `data/mindgraph.json` automatically

### Environment Variables
| Variable | Required | Description |
|---|---|---|
| `MINDGRAPH_TOKEN` | Always | Bearer token / API key |
| `MINDGRAPH_URL` | Cloud only | Set to `https://api.mindgraph.cloud` |
| `OPENAI_API_KEY` | Local only | Required for semantic/hybrid search |

---

## Design Conventions

1.  **Agent Identity:** Always pass `agent_id: 'jaadu'` (or `claude` if in that context) to ensure accurate `changed_by` provenance.
2.  **Atomic Bundling:** Use bundle endpoints (`/epistemic/argument`, `/action/procedure`, `/agent/plan`) to create related nodes and edges in a single transaction.
3.  **Narration:** Narrate before writing to `/memory/config` or `/agent/governance` as these modify behavioral rules.
4.  **Session Framing:** Call `POST /memory/session (action: open)` at the start of each conversation and use the `session_uid` for trace entries and distillation.
5.  **`props` deep-merge (v0.8.0):** All cognitive endpoints accept an optional `props` field. The server deep-merges user-provided props over its handler-constructed defaults — callers can override any node property. The `summary` field is auto-derived from props when omitted.
6.  **Entity `entity_type` in `props` (v0.8.0):** For `/reality/entity` `create` action, pass `entity_type` inside the `props` object (not as a top-level field). `mg.manageEntity({ action: 'create', label, entityType })` handles this automatically.

---

## Cognitive Layer Endpoints (The 18 Tools)

### Reality Layer (Raw Input)
- **POST /reality/ingest:** Capture `source` (web/paper/book), `snippet` (auto-links to source), or `observation`. Accepts optional `props` to deep-merge with handler defaults.
- **POST /reality/entity:** `create` (dedup-safe via `find_or_create_entity` — checks alias + case-insensitive match before creating, returns `{node, created: bool}`; pass `entity_type` inside `props`), `alias`, `resolve`, `fuzzy_resolve`, `merge`, or `relate` (creates an edge between `source_uid` and `target_uid` with `edge_type`). All actions accept `props`.

### Epistemic Layer (Reasoning)
- **POST /epistemic/argument:** Atomic Toulmin bundle. Creates `Claim` + `Evidence` + `Warrant` + `Argument` nodes and wires `Supports`, `HasWarrant`, `HasPremise`, and `HasConclusion` edges.
- **POST /epistemic/inquiry:** Record `hypothesis`, `anomaly`, `assumption`, `question`, or `open_question`. Handles `AnomalousTo`, `Tests`, and `Addresses` edges.
- **POST /epistemic/structure:** Crystallize `concept`, `pattern`, `mechanism`, `model`, `analogy`, `theorem`, or `equation`. Handles `AnalogousTo` and `TransfersTo` edges.

### Intent Layer (Commitments)
- **POST /intent/commitment:** Declare `goal`, `project`, or `milestone`. Propose before creating Goals/Projects.
- **POST /intent/deliberation:** Manage `open_decision`, `add_option`, `add_constraint`, or `resolve` (creates `DecidedOn` edge).

### Action Layer (Workflows)
- **POST /action/procedure:** Design `create_flow`, `add_step`, `add_affordance`, or `add_control` (wires `ComposedOf`, `StepUses`, `Controls`).
- **POST /action/risk:** `assess` a node (severity/likelihood) or `get_assessments`.

### Memory Layer (Persistence)
- **POST /memory/session:** `open`, `trace` (real-time recording), `close` (sets `ended_at`), or `journal` (creates a `Journal` node, auto-linked to `session_uid` via `CapturedIn` and to `relevant_node_uids` via `RelevantTo`). All actions accept `summary`, `confidence`, `salience`, and `props`.
- **POST /memory/distill:** synthesis of a session into a durable `Summary` node. Accepts `props`.
- **POST /memory/config:** `set_preference`, `set_policy`, `get_preferences`, or `get_policies`. Accepts `props`.

### Agent Layer (Control)
- **POST /agent/plan:** `create_task`, `create_plan`, `add_step`, or `update_status`.
- **POST /agent/governance:** `create_policy`, `set_budget`, `request_approval`, or `resolve_approval`.
- **POST /agent/execution:** `start`, `complete`, `fail`, or `register_agent`.

### Memory Layer — Journal (v0.8.0)
- **Journal nodes** via `POST /memory/session` with `action: "journal"`. Props (in `props` field): `content`, `journal_type` (note/investigation/debug/reasoning), `tags`. Pass `session_uid` to auto-link the journal to the session.
- Use `Follows` edges between Journal nodes for temporal sequencing (debugging arcs, reasoning chains).
- Use `mg.addJournal(label, content, opts)` — wrapper now correctly targets `/memory/session`.

### Connective Tissue
- **POST /retrieve:** Unified search modes: `text`, `semantic`, `hybrid` (RRF fusion of FTS + vector, k=60 — falls back to FTS-only if no embeddings), `active_goals`, `open_questions`, `weak_claims`, `pending_approvals`, `layer`, `recent`.
- **POST /traverse:** Navigation modes: `chain`, `neighborhood`, `path`, `subgraph`.
- **POST /evolve:** Mutation: `update` (propsPatch now validated — returns 422 with `unknown_props_fields` for invalid fields), `tombstone` (with cascade), `restore`, `decay`, `history`, `snapshot`.

### Full-Content FTS (Phase 0.5.2)
FTS indexes **all user-authored text** across 35+ string fields and 43+ Vec<String> fields — not just label and summary. Auto-indexed on insert/update. Run `node reindex-search.js` after upgrading to reindex existing nodes.

---

## Client API (mindgraph-client.js)

The client library wraps these cognitive endpoints. See `mindgraph-client.js` for full method signatures.

```javascript
const mg = require('./mindgraph-client.js');
// Example: Atomic Toulmin Bundle
await mg.addArgument({
  claim: { label: "Succession crisis likely", content: "Khamenei's death creates a power vacuum" },
  evidence: [{ label: "IRGC mobilization", description: "Reports of IRGC units entering Tehran" }],
  warrant: { label: "Historical precedent", explanation: "Regime transitions in Iran are often IRGC-led" }
});

// Phase 0.5 / v0.8.0 additions:
await mg.addJournal("Debug: propsPatch issue", "Full investigation notes...", { journalType: 'investigation', tags: ['bug'], sessionUid });
await mg.hybridSearch("propsPatch validation", { limit: 5 });  // Server-side RRF
await mg.findOrCreateEntity("Aaron Goh", "Person");  // Dedup-safe (entity_type passed via props internally)
await mg.addFollowsEdge(journalUid1, journalUid2);   // Temporal chain
// New: relate two entities with an edge
await mg.manageEntity({ action: 'relate', sourceUid: uid1, targetUid: uid2, edgeType: 'WorksAt' });
// New: props deep-merge override
await mg.ingest("AI paper", "Full text...", 'snippet', { sourceUid, props: { relevance_score: 0.9 } });
```
