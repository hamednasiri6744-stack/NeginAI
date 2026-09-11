# Package content verification

## STATUS: PASS

- Verifier version: `1.1.0`
- Declared scan state: `PARTIAL — CAPABILITY GAP`
- Canonical ledger rows: `92079`
- Case-fold collisions: `0`
- Finding records reconciled: `321`
- Dependency records reconciled: `8748`
- Symbol records reconciled: `9430`
- Internal SQLite quick-check: `PASS`
- Snapshot-union paths independently reconciled: `92079`
- Privacy-shape files checked: `20`

The verifier proved unique ledger identity, exact union-denominator reconciliation, CSV/JSONL path equality, related-record referential integrity, policy-required hash withholding, explicit fast-profile metadata-only invariants, full-byte/hash invariants for stable text/binary/archive rows, and absence of forbidden raw-content fields.

This PASS verifies package structure and internal accounting. It does not upgrade the scan's declared `PARTIAL` state or prove runtime behavior, formal security assurance, an atomic SMB snapshot, or human semantic review.
