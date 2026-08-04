# The Experience Graph

**A Language-Independent Representation of Emotional, Symbolic, Narrative,
and Cultural Meaning for Non-Literal Cross-Lingual Re-Expression**

Status: Research-grade specification — canonical internal representation of
CASTIA, superseding and formalizing the flat `IMRNode` sketched in
`CASTIA_ARCHITECTURE.md` §5.1.

---

## Abstract

Machine translation systems represent text as sequences of tokens and
optimize for surface-level correspondence between source and target
strings. This representation is structurally incapable of the task CASTIA is
built for: preserving what a piece of language *does* to a reader — its
emotional trajectory, its symbolic weight, its narrative function, its
cultural resonance — independent of the words used to do it. We propose the
**Experience Graph (EG)**, a typed, attributed, multi-relational graph that
represents a lyric, dialogue line, or poem as a structured object of
*experience* rather than of *text*. Every unit of source language is first
compiled into an Experience Graph; every downstream re-expression is
generated from the graph, never from the source string. This document
specifies the EG's formal schema, its node and edge taxonomy, its metadata
and confidence model, and the four representational subsystems — emotional,
symbolic, narrative, and cultural — that give the graph its expressive
power. Every field in the schema is justified against a specific failure
mode it exists to prevent.

---

## 1. Introduction and Motivation

### 1.1 Why a graph, and not a flat record

The earlier architectural sketch of CASTIA's interlingual representation
(`IMRNode`, one flat record per segment) is adequate for describing a single
line in isolation, but it cannot represent the thing that actually carries
most of a work's emotional and aesthetic power: **relationships between
units** — a symbol planted in stanza 1 and paid off in stanza 9, a
character's tone shifting across a scene, an emotional callback between two
lines forty pages apart, a cultural reference whose meaning depends on one
established earlier in the same work. A flat per-segment record has no
native way to express "this line means what it means partly *because* of
that other line." A graph does, natively, as an edge.

This is not a stylistic preference. It is the specific reason the
Experience Graph exists as a *graph*: **meaning in poetry, lyric, and
narrative is frequently relational, not local**, and any representation
that only captures local content will systematically under-represent
exactly the long-range structure (motif, arc, refrain, foreshadowing) that
this system was built to preserve.

### 1.2 Relationship to prior work in representation design

The Experience Graph draws deliberately on four separate traditions, each
solving part of this problem and none solving all of it alone:

- **Abstract Meaning Representation (AMR)** and **frame semantics
  (FrameNet)** — for the idea that propositional content can be represented
  as a language-independent graph of predicates and arguments rather than
  surface syntax. The Experience Graph's `PropositionNode`/`ParticipantEdge`
  layer is a direct descendant of this tradition, but AMR stops at literal
  meaning; it has no notion of affect, symbol, or narrative function.
- **Dimensional affect models (valence-arousal-dominance / VAD)** from
  affective computing — for representing emotion as continuous, composable
  dimensions rather than a single sentiment polarity. The EG's
  `EmotionNode` uses VAD as its dimensional substrate, but VAD alone
  flattens culturally-specific affect concepts (§8), so it is deliberately
  paired with an open categorical vocabulary.
- **Narratology (Propp's morphology of folk tale functions, Genette's
  discourse/story distinction)** — for the idea that narrative units serve
  *functions* in a larger structure (setup, complication, payoff) distinct
  from their propositional content. The EG's `NarrativeFunctionNode` and
  discourse-relation edges formalize this as graph structure instead of
  literary-critical prose.
- **Translation studies (Nida's dynamic/formal equivalence, Vermeer's
  skopos theory)** — for the principle that equivalence should be judged
  against communicative effect and purpose, not lexical correspondence. This
  is the theoretical justification for why the EG represents *effect*
  (emotion, symbol, function, cultural resonance) as first-class content,
  with literal propositional meaning present but explicitly subordinate to
  it in the downstream generation objective.

The Experience Graph's contribution is not any one of these ideas — it is
fusing all four into a single queryable structure that a generation system
can be built against, with an explicit, versioned schema rather than an
implicit prompt convention.

### 1.3 Position in the CASTIA pipeline

Every ingestible unit — a lyric line, a dialogue turn, a stanza — is
compiled into an Experience Graph fragment by the Layer 1 understanding
modules (SED, CRR, NDC in `CASTIA_ARCHITECTURE.md`) and assembled by what was
previously called the IMR builder, now understood as the **Experience Graph
Constructor**. Layer 3 (TCA, PFP, DGM) reads the graph to plan and generate;
Layer 4 (EEE, BCC) evaluates candidates *against* the graph; Layer 5 (LHM)
persists graph fragments — motifs, character arcs, terminology decisions —
across an entire work. No module downstream of construction ever reads
source text again. The graph is the interface.

---

## 2. Design Principles

1. **Language independence is structural, not conventional.** No node or
   edge type may reference a specific natural language's grammar (no
   "subject/verb/object" — that is `PropositionNode` with typed
   participant roles instead; no "adjective" — that is an `EmotionNode`
   attribute instead). If a field can only be filled in by looking at
   surface grammar of one language, it does not belong in the schema.
2. **Every claim is evidenced.** Any node or edge that asserts something
   about meaning (an emotion, a symbol, a cultural function) carries a
   pointer back to the source span that licenses the claim, and a
   confidence score. Nothing is asserted for free.
3. **Ambiguity is preserved, not resolved, at construction time.** Where a
   line genuinely supports two readings, the graph represents both,
   explicitly linked as alternatives, rather than the constructor silently
   picking one. Resolution (if any) happens downstream, where more context
   (cultural target, audience) is available to justify a choice.
4. **Relational structure is first-class.** Long-range relationships
   (motif recurrence, foreshadowing, character arcs) are represented as
   graph edges with their own types and confidence, not left implicit in
   node contents.
5. **Every representational subsystem is independently queryable.** A
   downstream module should be able to ask "what does this unit
   emotionally do" without also having to parse cultural or narrative
   content, and vice versa. The four representational subsystems
   (emotional, symbolic, narrative, cultural) are cross-linked but not
   merged into a single undifferentiated blob.
6. **The schema is versioned, not the model.** As per `CASTIA_ARCHITECTURE.md`
   §3.1 and §10.1, the models that populate the graph are expected to
   improve; the graph schema is the stable contract those models are
   expected to fill in, and it evolves under its own versioning discipline
   (§6.4), decoupled from any specific model upgrade.

---

## 3. Formal Model

The Experience Graph for a work `W` is a typed, attributed, directed
multigraph:

```
EG(W) = (V, E, τ_V, τ_E, φ_V, φ_E)
```

- `V` — the set of nodes.
- `E ⊆ V × V` — the set of directed edges (multigraph: multiple typed
  edges may exist between the same ordered pair of nodes).
- `τ_V : V → NodeTypes` — a total function assigning each node exactly one
  type from the taxonomy in §4.
- `τ_E : E → EdgeTypes` — a total function assigning each edge exactly one
  type from the taxonomy in §5.
- `φ_V : V → Properties` — a property map; `Properties` is a typed
  key-value record whose keys are fixed per node type (schema, not
  free-form).
- `φ_E : E → Properties` — likewise for edges.

Every node and every edge additionally carries two properties present
across **all** types, defined once here rather than repeated in every
table below:

| Field | Type | Rationale |
|---|---|---|
| `id` | UUID | Stable reference target for cross-linking, provenance, and audit trails (`SelectionRecord` in the architecture doc references graph node ids directly). |
| `metadata` | `Metadata` object (§6) | Every claim in the graph must be traceable to what produced it and when — required by design principle 2. |
| `confidence` | `Confidence` object (§7) | Every claim in the graph is a model-derived hypothesis, not a fact; nothing downstream may treat a graph field as ground truth without knowing how much to trust it. |

A single natural-language unit (a line, a turn, a stanza) is represented
not as one node but as a **subgraph anchored at an `ExperienceUnit`
node** — because a unit's meaning is properly represented as a bundle of
claims (an emotion, a proposition, a cultural reference, a narrative role),
each independently evidenced and scored, not as one monolithic record.

---

## 4. Node Taxonomy

Every node type below includes its distinguishing properties (beyond the
universal `id`/`metadata`/`confidence`) and, critically, **why each field
exists** — the failure mode it's designed to prevent, per design principle
2.

### 4.1 `WorkNode`

The single root node per work (song, poem, scene, chapter, novel).

| Field | Type | Why it exists |
|---|---|---|
| `title` | string? | Human-facing identification; optional because not all units (e.g. a single lyric line submitted alone) have one. |
| `source_language` | language tag | Every downstream module needs to know what linguistic assumptions *not* to carry over (e.g. grammatical gender, honorific systems) — without this tag, cultural/formal modules cannot know what source-specific features to look for and neutralize. |
| `form_genre` | enum: `lyric_song \| dialogue \| poem \| prose \| mixed` | Downstream planning (PFP, TCA) branches heavily on genre — a song lyric has performance/melody constraints a poem doesn't; collapsing genre into free text would make this branching unreliable. |
| `global_symbol_index` | list of `SymbolNode` ids | Without a work-level index, detecting that a symbol in unit 40 recurs from unit 2 would require an expensive full-graph scan every time; this field exists purely for retrieval efficiency and is derived, not authored. |

### 4.2 `ExperienceUnit` (EU)

The anchor node for one segment of source text (a line, a turn, a stanza).
This is the node type that replaces the old flat `IMRNode` — but here it is
a hub that other nodes attach to via edges, not a container of all content
itself.

| Field | Type | Why it exists |
|---|---|---|
| `span` | `(start, end)` offsets into source | The graph must always be traceable back to exact source text — required for audit (§2 principle 2) and for BCC's consistency checking against the original. |
| `unit_type` | enum: `line \| turn \| stanza \| utterance` | Different unit types have different formal expectations downstream (a `line` may carry meter; a `turn` carries speaker attribution) — collapsing this loses information PFP and NDC need. |
| `sequence_index` | integer | Graph edges express *relative* order (`PRECEDES`) but a global index is needed for efficient range queries ("everything between unit 10 and unit 40") without traversing the whole precedence chain. |
| `raw_text` | string | Kept for human review (HITL) and for BCC's literal back-derivation check — even though no *generation* module is permitted to read it directly, evaluation and audit legitimately need it. |

### 4.3 `PropositionNode` (PR)

Literal, language-independent semantic content: a predicate with typed
participant roles (agent, patient, instrument, location, etc.), in the AMR
tradition (§1.2).

| Field | Type | Why it exists |
|---|---|---|
| `predicate` | canonical predicate identifier (from a language-independent predicate inventory, not a source-language verb) | Using the source language's verb directly would silently reintroduce a source-language pivot — canonicalizing to a predicate inventory is what makes this node type actually language-independent rather than language-independent in name only. |
| `participants` | list of `(role, referent_node_id)` | Thematic roles (agent/patient/etc.) are cross-linguistically stable in a way surface grammatical roles (subject/object) are not — encoding roles this way is what lets BCC check "who did what to whom" survived adaptation even when sentence structure changes completely. |
| `polarity` | `affirmative \| negated \| hypothetical \| counterfactual` | Adaptation strategies (TCA) can accidentally invert polarity (e.g. turning a rhetorical negation into a flat assertion); this field exists so that inversion is a checkable, explicit property rather than something only detectable by re-reading full text. |

### 4.4 `EmotionNode` (EN)

See §8 for full rationale of the emotional subsystem; schema summarized
here.

| Field | Type | Why it exists |
|---|---|---|
| `valence` | float [-1, 1] | Continuous, composable representation needed so that emotional *trajectories* (§8.2) can be computed numerically (e.g. detecting a shift from negative to positive valence across a stanza) — a categorical label alone can't support this. |
| `arousal` | float [0, 1] | Distinguishes calm sadness from agitated sadness — two states a single valence score cannot tell apart, and which call for very different re-expression choices (a hushed grief vs. a wailing grief). |
| `dominance` | float [-1, 1] | Captures felt agency/power (helplessness vs. control) — a dimension VAD literature treats as separate from valence/arousal and which matters distinctly for narrative voice (a victim's line and a victor's line can share valence and arousal but must not share dominance). |
| `discrete_tags` | open-vocabulary list of strings | Dimensional scores alone flatten culturally-specific affect concepts with no clean VAD equivalent (e.g. *saudade*, *mono no aware*, *schadenfreude*) — kept open-vocabulary specifically so the system is not forced to approximate these onto whatever affect taxonomy happened to be built into training data. |
| `temporal_scope` | `instantaneous \| sustained \| building` | Distinguishes a flash of feeling from a mood that colors an entire passage — collapsing this loses information PFP/DGM need to decide whether an emotional effect should be concentrated in one line or distributed. |
| `is_ironic_or_masked` | boolean | Marks cases (from SED's cross-check, `CASTIA_ARCHITECTURE.md` §4.2) where literal sentiment and detected affect diverge — exists so downstream modules don't have to re-derive this themselves from raw scores, and so the divergence is an explicit, auditable claim rather than implicit in a low confidence score. |

### 4.5 `SymbolNode` (SY)

See §9. One instance per occurrence of a symbol/image/motif in the text
(not one per distinct symbol type — recurrence is represented via edges,
§5.6, so that the *history* of a motif across a work is itself inspectable).

| Field | Type | Why it exists |
|---|---|---|
| `surface_form` | string (source language) | Needed to keep the symbol traceable to its literal instantiation ("a caged bird") even though its meaning is represented abstractly elsewhere in this node. |
| `referent_gloss` | free-text description of what the symbol stands for | Symbolic meaning is often too specific and context-dependent to force into a closed taxonomy (unlike, say, emotion's VAD substrate) — kept as a structured gloss rather than a fixed enum for the same reason `discrete_tags` on `EmotionNode` is open-vocabulary. |
| `symbol_class` | `archetypal \| cultural \| personal_to_work` | Determines re-expression strategy: an archetypal symbol (fire = passion) often survives direct rendering; a culturally-specific one (a particular flower's meaning in one culture) needs TCA's adaptation machinery; a personal-to-work symbol (established earlier in *this* poem) must be rendered consistently with its own prior occurrences via LHM, not re-interpreted fresh. Without this classification, TCA cannot know which strategy family even applies. |
| `motif_id` | UUID, shared across all occurrences of the same recurring symbol | Distinguishes "this happens to be the same word" from "this is a graph-tracked recurring motif" — required so that `RECURS_AS` edges (§5.6) can be queried efficiently and so LHM can retrieve every prior occurrence of a specific motif in the work. |

### 4.6 `CulturalReferenceNode` (CR)

See §10.

| Field | Type | Why it exists |
|---|---|---|
| `reference_type` | `idiom \| allusion \| honorific \| taboo \| humor \| historical \| religious` | Different types demand structurally different adaptation strategies in TCA (an honorific's adaptation logic is unrelated to a historical allusion's) — a single undifferentiated "cultural note" field would force TCA to re-classify from free text every time, reintroducing exactly the ambiguity this node exists to remove. |
| `source_function` | free-text description of what cultural work this reference performs for a source-culture reader | This is the field TCA actually reasons from — not "what does this idiom mean" but "what is it *doing* here" (marking intimacy, signaling class, invoking shared history) — because a correct adaptation needs to reproduce the function, not the content. |
| `salience` | float [0, 1] | Distinguishes a load-bearing central reference from a passing decorative one — without this, TCA/SA cannot decide how much re-expression effort or risk is justified for a given reference. |
| `untranslatable` | boolean | An explicit flag rather than an implicit absence of equivalents — this is what triggers TCA's compensation/explanation strategies instead of a default (and likely wrong) direct-substitution attempt. |

### 4.7 `NarrativeFunctionNode` (NF)

See §11.

| Field | Type | Why it exists |
|---|---|---|
| `function_type` | open vocabulary, seeded from Proppian/Genettean categories (e.g. `setup`, `complication`, `climax`, `resolution`, `foreshadowing`, `callback`, `characterization`) | Encodes *why this unit exists in the larger work*, distinct from what it literally says — needed because a technically-accurate rendering that fails to still set up a later payoff is a narrative failure invisible to purely local (emotional/propositional) evaluation. |
| `payoff_ref` | optional `ExperienceUnit` id | Explicit pointer instead of relying on evaluators to rediscover the connection — required for EEE's narrative-fidelity check (`CASTIA_ARCHITECTURE.md` §7.1) to verify a foreshadowing unit's rendering still plausibly sets up its named payoff. |

### 4.8 `AgentNode` (AG)

Represents a character, speaker, or addressee.

| Field | Type | Why it exists |
|---|---|---|
| `voice_signature` | structured record of lexical/register/syntactic tendencies | Required so DGM can condition generation to keep a character's voice consistent — without a graph-native place to store this, voice consistency would depend entirely on model context length, which does not scale to long works (see `CASTIA_ARCHITECTURE.md` LHM rationale). |
| `emotional_arc_ref` | ordered list of `EmotionNode` ids associated with this agent across the work | Makes a character's emotional trajectory a first-class, queryable object rather than something that has to be reconstructed by walking the entire graph on demand. |

### 4.9 `FormalConstraintNode` (FM)

Prosodic/poetic form attached to a unit (meter, rhyme, repetition,
syllable count) — see `CASTIA_ARCHITECTURE.md` §6.2 (PFP) for the module that
populates this.

| Field | Type | Why it exists |
|---|---|---|
| `constraint_type` | `meter \| rhyme_scheme \| syllable_count \| repetition \| alliteration` | Different constraint types require different target-language feasibility analysis; merging them would force PFP's feasibility logic to branch on free text instead of a typed field. |
| `priority` | `load_bearing \| preferred \| negotiable` | This is the single most consequential field in the node: it tells DGM/SA what to sacrifice first when full fidelity across emotional, cultural, and formal dimensions is jointly infeasible — which, for poetic re-expression, is the normal case, not the exception. |

### 4.10 `AmbiguityNode` (AM)

Marks a genuinely underdetermined reading, per design principle 3.

| Field | Type | Why it exists |
|---|---|---|
| `alternative_refs` | list of node ids, each representing one complete alternative reading (e.g. two different `EmotionNode`/`PropositionNode` pairs) | This is the mechanism that lets ambiguity survive into Layer 3 instead of being silently collapsed at construction time — TCA can then choose the reading that fits the target culture, rather than inheriting a source-culture-biased resolution made too early. |
| `resolution_deferred_to` | enum naming which downstream module is expected to resolve it (e.g. `TCA`, `HITL`) | Prevents ambiguity from being dropped silently — every `AmbiguityNode` must have a designated resolver, or graph validation (§6.4) rejects it. |

---

## 5. Relationship (Edge) Taxonomy

Edges are as important as nodes: the Experience Graph's central claim is
that meaning is substantially relational, so the edge set is where most of
that claim is operationalized.

| Edge type | Source → Target | Cardinality | Semantics | Why it exists |
|---|---|---|---|---|
| `CONTAINS` | `WorkNode`/`SceneNode` → `ExperienceUnit` | 1→N | Hierarchical containment | Lets queries scope to "everything in this scene" without needing a separate indexing structure. |
| `PRECEDES` | `ExperienceUnit` → `ExperienceUnit` | 1→1 (chain) | Direct sequential order | The minimal ordering relation every long-range relation (echo, foreshadowing) is defined relative to. |
| `EXPRESSES` | `ExperienceUnit` → `PropositionNode` | 1→N | Unit's literal content | Separates "what is claimed" from "what unit claims it," so a proposition can in principle be referenced by evaluation logic independent of surface unit boundaries. |
| `HAS_EMOTION` | `ExperienceUnit` → `EmotionNode` | 1→N | Unit's affective content (can be N because a unit can carry layered/conflicting affect, e.g. bittersweet) | N-cardinality specifically exists to represent co-present, non-reducible mixed emotion (grief *and* relief simultaneously) rather than forcing a single blended score that would misrepresent both. |
| `NEXT_EMOTION` | `EmotionNode` → `EmotionNode` | 1→1 (chain, per agent or per work) | Emotional trajectory step | Makes trajectory (§8.2) an explicit chain rather than something inferred post hoc from a list — required for EEE's trajectory-fidelity comparison. |
| `EVOKES` | `ExperienceUnit` → `SymbolNode` | 1→N | Unit invokes a symbol/image | Distinguishes "this unit contains a symbol" from the symbol's own recurrence history, which lives in `RECURS_AS` below — keeps per-occurrence and cross-occurrence information separately queryable (design principle 5). |
| `RECURS_AS` | `SymbolNode` → `SymbolNode` | 1→1 (chain, same `motif_id`) | Links successive occurrences of the same motif | This is the edge that operationalizes design principle 4 (relational structure is first-class) for symbolism specifically — without it, "this callback to the caged-bird image" is not a graph fact, just a coincidence of two nodes sharing a gloss. |
| `GROUNDED_IN` | `ExperienceUnit` → `CulturalReferenceNode` | 1→N | Unit's cultural content | Kept as its own edge (not folded into `EVOKES`) because cultural references and symbols have different adaptation logic downstream (TCA vs. a symbol-preservation heuristic) and must remain distinguishable by type alone. |
| `SERVES` | `ExperienceUnit` → `NarrativeFunctionNode` | 1→N | Unit's role in the larger work | The mechanism by which local content is tied to global narrative purpose — required for EEE's narrative-fidelity axis. |
| `FORESHADOWS` / `PAYS_OFF` | `ExperienceUnit` → `ExperienceUnit` | N→N | Long-range narrative dependency | Explicit long-range edges rather than relying on context-window co-presence — this is precisely the class of relationship a flat per-segment representation cannot express, and the primary motivating example for why EG is a graph (§1.1). |
| `ECHOES` | `ExperienceUnit` → `ExperienceUnit` | N→N | Non-motif-specific repetition/parallelism (refrains, structural parallels) | Distinguished from `RECURS_AS` because a unit can echo another structurally/rhythmically without sharing a tracked symbol — e.g. a refrain with varied imagery each time. |
| `CONTRASTS_WITH` | `ExperienceUnit` → `ExperienceUnit` | N→N | Deliberate juxtaposition/irony across units | Needed because contrast is itself a rhetorical device whose effect (dramatic irony, bathos) is lost if each unit is only evaluated locally. |
| `SPOKEN_BY` / `ADDRESSED_TO` | `ExperienceUnit` → `AgentNode` | N→1 | Speaker/addressee attribution | Required for voice-consistency conditioning in DGM and for per-character emotional arcs in `AgentNode.emotional_arc_ref`. |
| `PARTICIPANT` | `PropositionNode` → `AgentNode`/referent node | N→N, role-typed | Thematic-role binding (agent, patient, instrument, etc.) | This is the actual payload of `PropositionNode.participants` expressed as graph structure — kept as edges (not just properties) so BCC can traverse participant identity across a rendering to check "who did what to whom" survived. |
| `CONSTRAINED_BY` | `ExperienceUnit` → `FormalConstraintNode` | 1→N | Formal/prosodic requirement on the unit | Separated from emotional/cultural content because formal constraints are evaluated by an entirely different feasibility analysis (PFP) working over target-language phonology, not meaning. |
| `AMBIGUOUS_BETWEEN` | `AmbiguityNode` → any node type | 1→N | Points to each competing alternative | The structural realization of design principle 3 — ambiguity as first-class graph content, not an implementation detail hidden in low confidence scores. |
| `EQUIVALENT_CANDIDATE_IN` | `CulturalReferenceNode` → external `CulturalKnowledgeBase` concept id | 1→N | Points to catalogued candidate target-culture equivalents | Deliberately an edge to an *external*, target-culture-scoped store rather than a property on the node — keeps the Experience Graph itself culture-of-origin-only and language-independent (design principle 1); target-culture answers live outside the graph and are attached only at TCA time, per work. |

---

## 6. Metadata and Provenance

### 6.1 The `Metadata` object (attached to every node/edge)

| Field | Type | Why it exists |
|---|---|---|
| `created_by` | `{module, model_id, model_version}` (via MAL, `CASTIA_ARCHITECTURE.md` §3.1) | Enables exactly the kind of audit principle 2 requires: if a claim later turns out wrong, provenance identifies which model/module produced it, which matters both for debugging and for MAL's shadow-evaluation comparisons across model versions. |
| `created_at` | timestamp | Needed for reproducibility and for detecting stale claims after a knowledge base update (e.g. a cultural equivalence that was valid when the graph was built but has since been revised). |
| `source_span` | offset range into `WorkNode`'s raw text (redundant with `ExperienceUnit.span` for unit-anchored nodes, but required independently for nodes like `PropositionNode` whose evidentiary span may be narrower than the whole unit) | Every claim must be traceable to the literal text that licenses it — this is what makes the graph auditable rather than merely plausible. |
| `revision_of` | optional node id | Supports non-destructive correction (e.g. HITL overriding an automated claim) without deleting the original — preserves the audit trail principle established for `SelectionRecord` in the architecture doc. |
| `schema_version` | semver string | The schema is expected to evolve (design principle 6); every node must declare which schema version it was built against so that older graphs remain interpretable by newer modules via explicit migration, not silent assumption. |

### 6.2 Why metadata is per-node/edge and not per-graph

A single graph-level metadata block would be sufficient if every claim in a
work were produced by the same model at the same time — which will not be
true in practice (a graph is built incrementally, segments may be
reprocessed after a model upgrade, HITL may revise individual claims). Per-
node provenance is what allows partial reprocessing and mixed-provenance
graphs to remain fully auditable.

---

## 7. Confidence Model

### 7.1 The `Confidence` object (attached to every node/edge)

| Field | Type | Why it exists |
|---|---|---|
| `value` | float [0, 1] | The base confidence estimate — required so downstream modules (especially SA, `CASTIA_ARCHITECTURE.md` §7.3) can weigh competing claims instead of treating all graph content as equally certain. |
| `method` | `model_inference \| rule_based \| human_annotated \| ensemble_agreement` | Different methods warrant different downstream trust policies (e.g. a policy may treat `human_annotated` as effectively ground truth and `model_inference` as always subject to EEE re-verification) — collapsing method into the scalar value would make that policy impossible to express. |
| `ensemble_variance` | float?, present only when `method = ensemble_agreement` | High variance across independently-queried models (via MAL's ensemble routing) is itself a signal that a claim is genuinely uncertain or that the underlying text is ambiguous — this is a materially different situation from a single confident-but-wrong model, and needs to be visible as its own field, not folded into `value`. |
| `evidence_spans` | list of source offset ranges | A confidence score without pointers to what generated it cannot be audited or contested — this is the field an HITL reviewer actually reads to judge whether to trust the claim. |

### 7.2 Confidence propagation

Confidence does not automatically propagate along edges (e.g. a
`FORESHADOWS` edge's confidence is not derived arithmetically from its
endpoints' confidences) — narrative/relational judgments are estimated
independently by the module that asserts them (NDC), because a relationship
can be highly confident even when one endpoint's local content is
ambiguous, and vice versa. Deriving edge confidence mechanically from node
confidence would misrepresent this independence.

---

## 8. Emotional Representation

### 8.1 Why dual-encode (dimensional + categorical)

A purely dimensional (VAD) encoding is composable and supports numerical
trajectory analysis, but flattens emotion concepts that don't decompose
cleanly along three universal axes — many culturally specific affect
concepts are defined by *situation* and *social relation*, not just felt
quality. A purely categorical encoding (a fixed emotion-label taxonomy)
avoids that flattening but cannot support arithmetic operations needed for
trajectory modeling (e.g. "valence rises across this stanza"), and forces
every observed emotion into a closed, likely Western-centric, label set.
The Experience Graph uses both, on the same `EmotionNode`, precisely
because each compensates for the other's failure mode, and because keeping
`discrete_tags` open-vocabulary (§4.4) means the categorical side is never
artificially constrained to a fixed inventory.

### 8.2 Trajectory as graph structure

`NEXT_EMOTION` edges (§5) chain `EmotionNode`s in two independent orders:
per-unit sequence (the emotional arc of the *text*, unit by unit) and
per-agent sequence (the emotional arc of a *character*, via
`AgentNode.emotional_arc_ref`). These are kept separate because a scene's
overall emotional trajectory and one character's emotional trajectory
within that scene are different, both meaningful, comparisons for EEE to
make (a scene can escalate in tension while an individual character
remains numb throughout — collapsing these into one trajectory would erase
that specific effect).

### 8.3 Irony and masking as a first-class flag

`is_ironic_or_masked` (§4.4) exists because emotion detected from surface
sentiment and emotion actually intended can diverge, and this divergence is
itself meaningful content that a translator (human or CASTIA) must
reproduce — flattening it into "just report the true emotion" would
discard the fact that the text is *performing* a different emotion on the
surface, which is often exactly the poetic effect being achieved.

---

## 9. Symbolic Representation

### 9.1 Occurrence-level nodes, motif-level linking

Representing each occurrence of a symbol as a distinct `SymbolNode` linked
by `RECURS_AS` edges (§5) — rather than one node per abstract symbol
referenced multiple times — exists so that a symbol's *evolution* across a
work is representable: the caged bird in stanza 1 (hope) and the caged
bird in stanza 9 (resignation) are the same motif but not the same
meaning, and only occurrence-level nodes chained by an explicit "same
motif, different instance" edge can capture that a symbol's meaning has
shifted across a work while its identity persists.

### 9.2 The three-way `symbol_class` split

The classification into `archetypal / cultural / personal_to_work` (§4.5)
exists because it directly determines which downstream module family is
responsible for handling the symbol correctly: archetypal symbols are the
safest to render with minimal adaptation (TCA can largely defer to DGM);
culturally-specific symbols require TCA's cultural-knowledge-base
machinery; work-internal symbols require LHM consistency lookups. A
generic "symbol" node without this split would force every downstream
module to re-derive the classification itself, redundantly and
inconsistently.

---

## 10. Cultural Representation

### 10.1 Function over content

`CulturalReferenceNode.source_function` (§4.6) is deliberately a
description of *what the reference does* (signals intimacy, marks class,
invokes shared religious memory) rather than *what it literally refers to*
(which is already captured, if relevant, by a linked `PropositionNode`).
This split exists because TCA's entire job is to find a target-culture
device that does the same *work*, which may require an entirely different
literal reference — the function is the actual invariant that must survive
adaptation; the literal content is not.

### 10.2 Keeping target-culture answers outside the graph

The Experience Graph never stores a specific target-language equivalence
inside `CulturalReferenceNode` itself — only a pointer
(`EQUIVALENT_CANDIDATE_IN`) into an external, target-culture-scoped
knowledge base. This is a direct consequence of design principle 1: if the
graph embedded "in French, this idiom becomes X," the graph would no
longer be language-independent, it would be a source-plus-one-target
structure, and would need to be rebuilt per target language rather than
built once per source unit and reused for every target language CASTIA is
ever asked to render into.

### 10.3 The `untranslatable` flag as compensation trigger

Marking a reference `untranslatable` (§4.6) rather than leaving it
unmatched exists because "no equivalence found" is ambiguous between "this
concept genuinely has no analog" and "the knowledge base is simply
incomplete" — an explicit flag, set deliberately by CRR based on structural
analysis (not absence of a KB hit), routes the reference to TCA's
compensation/explanation strategies rather than either silently omitting
it or defaulting to an ill-fitting literal substitution.

---

## 11. Narrative Representation

### 11.1 Function as distinct from content

`NarrativeFunctionNode` (§4.7) exists as a separate node type from
`PropositionNode` because two units can express nearly identical
propositional content while serving entirely different narrative
functions (a repeated line that was a question in Act 1 and a statement
of resignation in Act 3) — function must be assessable independent of
content for `payoff_ref` tracking and for EEE's narrative-fidelity checks
to mean anything.

### 11.2 Why `payoff_ref` is a pointer, not a description

An explicit pointer to the specific `ExperienceUnit` that pays off a given
setup (rather than a free-text description like "sets something up later")
exists so that if a translation candidate for the payoff unit changes
significantly, the system can automatically re-check whether the setup
unit's rendering still makes sense in light of that change — a structural
consistency check that free text cannot support.

---

## 12. Worked Example

Source (illustrative, English for exposition only — the graph itself
carries no privileged language):

> *"She kept his letters in a locked drawer, the way you keep a wound you
> won't let heal."*

```mermaid
graph LR
    WORK[WorkNode: form_genre=poem]
    EU1[ExperienceUnit #12<br/>span=142-210]
    PR1[PropositionNode<br/>predicate=KEEP<br/>polarity=affirmative]
    PR2[PropositionNode<br/>predicate=REFUSE-HEAL<br/>polarity=negated]
    AG1[AgentNode: she]
    SY1[SymbolNode<br/>surface_form='locked drawer'<br/>referent_gloss='guarded, unresolved attachment'<br/>symbol_class=archetypal]
    SY2[SymbolNode<br/>surface_form='a wound you won't let heal'<br/>referent_gloss='deliberately sustained emotional injury'<br/>symbol_class=archetypal<br/>motif_id=M-07]
    EN1[EmotionNode<br/>valence=-0.6, arousal=0.3, dominance=-0.2<br/>discrete_tags=[grief, attachment, refusal-to-move-on]<br/>temporal_scope=sustained]
    NF1[NarrativeFunctionNode<br/>function_type=characterization]
    FM1[FormalConstraintNode<br/>constraint_type=simile-structure<br/>priority=preferred]

    WORK -->|CONTAINS| EU1
    EU1 -->|EXPRESSES| PR1
    EU1 -->|EXPRESSES| PR2
    PR1 -->|PARTICIPANT: agent| AG1
    EU1 -->|SPOKEN_BY: narrator, ADDRESSED_TO: implied listener| AG1
    EU1 -->|EVOKES| SY1
    EU1 -->|EVOKES| SY2
    EU1 -->|HAS_EMOTION| EN1
    EU1 -->|SERVES| NF1
    EU1 -->|CONSTRAINED_BY| FM1
```

Notes on this instantiation:

- Two `PropositionNode`s exist because the sentence makes two distinct
  literal claims (keeping letters; refusing to let a wound heal) joined by
  simile — kept separate because a candidate rendering could preserve one
  faithfully while distorting the other, and EEE/BCC need to check both
  independently.
- `SY2` carries a `motif_id`; if "wound" recurs later in the work, that
  later occurrence is linked via `RECURS_AS` to this node, letting LHM and
  TCA retrieve this exact gloss and confidence rather than re-deriving it.
- No `CulturalReferenceNode` is attached here because a locked drawer and
  an unhealed wound are treated as archetypal (§9.2), not culturally
  specific — TCA can defer directly to DGM for this unit without cultural
  knowledge base lookup, which is itself a decision this schema makes
  legible rather than implicit.
- `EN1.dominance = -0.2` (rather than a fixed default) is what
  distinguishes this passage from a superficially similar high-arousal,
  negative-valence line about anger — the low dominance signals
  helplessness against one's own attachment, which is the actual emotional
  content DGM needs to preserve, not merely "sad."

---

## 13. Consumption Patterns

How Layer 3–5 modules from `CASTIA_ARCHITECTURE.md` query the graph, briefly,
to ground the schema in actual use:

| Module | Primary query pattern |
|---|---|
| TCA (§6.1) | For each `ExperienceUnit`, traverse `GROUNDED_IN` to `CulturalReferenceNode`s; check `untranslatable`; follow `EQUIVALENT_CANDIDATE_IN` to the external knowledge base; check `LHM` for prior `RECURS_AS`-linked occurrences of the same reference. |
| PFP (§6.2) | Traverse `CONSTRAINED_BY` to `FormalConstraintNode`s; read `priority` to determine what's negotiable. |
| DGM (§6.3) | Traverse `HAS_EMOTION`, `EVOKES`, `SERVES`, `SPOKEN_BY` to assemble the full generation brief for a unit; read `AgentNode.voice_signature` for dialogue. |
| EEE (§7.1) | Re-derive a candidate's `EmotionNode`/`NarrativeFunctionNode` equivalents and diff against the source unit's; follow `payoff_ref`/`FORESHADOWS` edges to verify long-range narrative function survived. |
| BCC (§7.2) | Re-derive `PropositionNode`/`PARTICIPANT` structure from the candidate and diff against the source unit's, tolerant of `GROUNDED_IN`-sanctioned substitutions. |
| LHM (§8, architecture doc) | Persist and retrieve by `motif_id`, `AgentNode.id`, and `CulturalReferenceNode` identity across the whole graph, not just within one run. |

---

## 14. Failure Modes and Limitations

- **Graph fragmentation under parallel construction.** When segments are
  processed in parallel (per `CASTIA_ARCHITECTURE.md` OC fan-out), long-range
  edges (`FORESHADOWS`, `RECURS_AS`, `ECHOES`) require a reconciliation pass
  after fan-in, since a segment processed in isolation cannot know about a
  motif established in a segment it hasn't seen. This is a structural cost
  of the graph model, not a bug — reconciliation is a required, explicit
  pipeline stage, not an optional cleanup step.
- **Schema rigidity vs. expressive need.** A fixed node/edge taxonomy will
  occasionally under-fit a genuinely novel poetic device that doesn't map
  onto any existing type. The schema versioning discipline (§6.1) exists
  specifically to let the taxonomy grow, but there is an inherent lag
  between encountering a new device and having a node type for it — until
  then, it is likely to be mis-typed as the nearest existing category
  (typically `SymbolNode` or `AmbiguityNode`), which is a known, accepted
  degradation rather than a silent one.
- **Confidence miscalibration compounds across a large graph.** Because
  downstream modules make decisions by combining confidence across many
  nodes and edges (e.g. SA weighing several `EquivalenceScore`s derived
  from graph content), systematic miscalibration in one upstream capability
  (e.g. `affective-profiling` consistently overconfident) propagates
  broadly rather than being isolated to one claim — this is why ensemble
  variance (§7.1) is tracked as its own signal rather than trusting a
  single `value`.
- **Cultural bias in classification, not just content.** The
  `symbol_class` and `reference_type` taxonomies (§9.2, §4.6) are
  themselves categorization schemes, and any fixed categorization scheme
  risks encoding the assumptions of whatever tradition (here, substantially
  Western/Euro-American literary theory, per §1.2's related-work grounding)
  produced it. This is flagged as an open problem the schema does not
  claim to solve, only to make visible and revisable.

---

## 15. Future Work

- **Learned edge types.** Currently the edge taxonomy is fixed and
  human-designed; a natural extension is a controlled process for
  proposing new edge types from observed patterns across many works
  (analogous to the schema-versioning process in §6.1), rather than
  requiring hand-authored taxonomy extensions indefinitely.
- **Cross-work graph linking.** Presently each `WorkNode` is independent;
  a shared graph across an author's full body of work (or a genre, or a
  cultural tradition) would let motif/symbol recognition benefit from
  patterns beyond a single work, feeding back into the global
  `CulturalKnowledgeBase` described in `CASTIA_ARCHITECTURE.md` §8.1's future
  improvements.
- **Quantitative validation against human literary judgment.** The
  representational choices here (VAD + open categorical tags; occurrence-
  level symbol nodes; function-over-content cultural framing) are
  theoretically motivated but not yet empirically validated against human
  raters' judgments of translation quality — a natural next research step
  once the graph construction pipeline is implemented and candidate
  outputs exist to evaluate.
- **Formal graph query language.** This document specifies consumption
  patterns informally (§13); a properly typed query language over the
  Experience Graph schema (in the spirit of SPARQL for RDF, but aware of
  this schema's typed multigraph structure and confidence model) would let
  downstream modules express graph queries declaratively rather than via
  ad hoc traversal code, and would make the confidence-propagation
  discipline (§7.2) enforceable at the query layer.

---

## Appendix: Schema Reference (Compact)

**Node types:** `WorkNode`, `ExperienceUnit`, `PropositionNode`,
`EmotionNode`, `SymbolNode`, `CulturalReferenceNode`, `NarrativeFunctionNode`,
`AgentNode`, `FormalConstraintNode`, `AmbiguityNode`.

**Edge types:** `CONTAINS`, `PRECEDES`, `EXPRESSES`, `HAS_EMOTION`,
`NEXT_EMOTION`, `EVOKES`, `RECURS_AS`, `GROUNDED_IN`, `SERVES`,
`FORESHADOWS`/`PAYS_OFF`, `ECHOES`, `CONTRASTS_WITH`, `SPOKEN_BY`/
`ADDRESSED_TO`, `PARTICIPANT`, `CONSTRAINED_BY`, `AMBIGUOUS_BETWEEN`,
`EQUIVALENT_CANDIDATE_IN`.

**Universal fields (every node and edge):** `id`, `metadata` (§6),
`confidence` (§7).

*End of document.*
