# HYDRA Architecture

## System view

```mermaid
flowchart TB
    subgraph S[Source layer]
      S1[Market / historical inputs]
      S2[Options-derived inputs]
      S3[Macro / regime context]
      S4[Research / planner inputs]
    end

    subgraph I[Ingestion]
      I1[Source registry]
      I2[Manifests]
      I3[Raw record checks]
    end

    subgraph C[Canonical data]
      C1[Normalization]
      C2[Canonical schemas]
      C3[Identity / naming controls]
    end

    subgraph X[Context assembly]
      X1[Structural levels]
      X2[Value / profile context]
      X3[Session / gap / volatility context]
      X4[Gamma / regime context]
    end

    subgraph G[Governance]
      G1[Schema contracts]
      G2[Producer authority]
      G3[Lineage / provenance]
      G4[Contradiction / constraint checks]
    end

    subgraph V[Validation and release]
      V1[Cross-stage validation]
      V2[Repair -> rerun -> freeze]
      V3[Fail-closed release gate]
    end

    subgraph D[Downstream]
      D1[Research / replay]
      D2[Label / dataset construction]
      D3[Model-development interfaces]
      D4[Public proof artifacts]
    end

    S --> I --> C --> X --> G --> V --> D
    G2 -->|missing authority| V3
```

## Core design ideas

### Source-accounted ingestion

A downstream record should not become "trusted" merely because a parser produced it. HYDRA keeps source identity and source scope visible through the pipeline.

### Canonicalization

Source-specific representations are normalized into stable, inspectable structures. Canonicalization is where names, fields, types, and semantic expectations become explicit.

### Contract-bound handoffs

Pipeline stages do not get permission to invent fields required by the next stage.

A downstream requirement must map to:
1. an authoritative producer;
2. an authorized derivation contract; or
3. an explicit missing-authority blocker.

### Lineage and provenance

The system treats "where did this value come from?" as a first-class question.

Observed, derived, synthetic, and assumed values must not collapse into one indistinguishable state.

### Validation and release gates

A green result is meaningful only when the test itself is honest.

HYDRA uses fail-closed behavior when the required evidence or authority is absent.

## Public boundary

This architecture document describes the public engineering model and validated design direction. It should not be used to imply that every displayed lane is live, integrated, or production deployed.

See [PUBLIC_CLAIM_BOUNDARIES.md](PUBLIC_CLAIM_BOUNDARIES.md).
