# Retrieval module

Scope: exact lookup, search projections, PostgreSQL FTS, ranking, and query audit.

- Start with exact `act_id`/`address_key`/`edition_id` lookup and a Russian PostgreSQL FTS baseline.
- Apply verified time, jurisdiction, approval, corpus-scope, and ACL filters before ranking.
- `SearchProjection` is rebuildable retrieval data, never citation authority.
- Return evidence by `edition_id + provision_id + evidence_span`; never cite a `chunk_id`.
- Do not overlap projections across provisions or editions. Split only inside one overlong provision while preserving offsets.
- Add dense retrieval, RRF, or reranking only after an ablation on the same frozen evaluation set shows a measured benefit.

