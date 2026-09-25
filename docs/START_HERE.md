# Start Here

If you have five minutes, follow this path.

## 1. Read the front door

Start with the repository `README.md`.

It explains the problem HYDRA is solving and the engineering principles that shape the system.

## 2. See the architecture

Read [ARCHITECTURE.md](ARCHITECTURE.md).

Focus on the governed path:

`source -> ingestion -> canonicalization -> context -> contracts -> lineage -> validation -> consumer`

The important behavior is at the seams. HYDRA is designed to reject invalid or unauthorized handoffs instead of silently manufacturing missing fields.

## 3. Inspect technical proof

Read [TECHNICAL_PROOF.md](TECHNICAL_PROOF.md).

Look for:
- source-accounted ingestion;
- canonical row counts;
- deterministic reruns;
- contract/schema validation;
- provenance and lineage;
- fail-closed authority behavior;
- repair -> rerun -> freeze evidence.

## 4. Use the repository map

Read [REPOSITORY_MAP.md](REPOSITORY_MAP.md).

The GH-01 audit generates a repo-specific map so representative code and proof can be surfaced before internal support material.

## 5. Check claim boundaries

Read [PUBLIC_CLAIM_BOUNDARIES.md](PUBLIC_CLAIM_BOUNDARIES.md).

HYDRA distinguishes:
- real observed data;
- derived data;
- synthetic or shadow fixtures;
- validated research outputs;
- planned or incomplete integrations.

That distinction is part of the system, not a footnote.

## 6. See the public showcase

Project website:

https://hydradataai.github.io/Hydra-Website/

Website repository:

https://github.com/HYDRADATAAI/Hydra-Website
