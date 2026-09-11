# NeginAI file-by-file coverage summary

## STATUS: PARTIAL — CAPABILITY GAP

**FACT:** The canonical denominator is the union of every file path observed during the bounded reconciliation passes. One canonical ledger row exists per union path.

**FACT:** Inventory coverage, full-text coverage, static-parse coverage, and semantic-review coverage are separate metrics; none is substituted for another.

| Measure | Result |
| --- | ---: |
| Observed union denominator | 92079 |
| Unique canonical ledger paths | 92079 |
| Inventory reconciliation | PASS |
| Full streamed text scans | 1879 |
| Full-text coverage of all files | 2.0406% |
| Parser-eligible files | 1374 |
| Successful static parses | 1374 |
| Static-parse coverage | 100.0% |
| Semantic per-file reviews | 0 |
| Semantic-review coverage | 0.0% |
| Sensitive containers: metadata only | 27 |
| Runtime/business data: metadata only | 24261 |
| Fast-profile metadata-only rows | 65893 |
| Archives/packages total | 1433 |
| Archive envelope PASS | 0 |
| Archive envelope partial/unsupported/error | 0 |
| Binaries fully hashed | 19 |
| All stable files fully hashed | 1898 |
| Unreadable/error file rows | 0 |
| Volatile/changed file rows | 5 |
| Directory traversal errors | 0 |
| Reparse/special objects not followed | 0 |

## Coverage interpretation

- `FILE_LEDGER.jsonl` is canonical. `FILE_LEDGER.csv` is an Excel-safe display mirror.
- `FULL_TEXT_SCAN` means every stable byte was streamed, hashed, decoded, and checked by the declared rule pack.
- `BINARY_METADATA` means every stable byte was hashed; the file was never executed.
- `ARCHIVE_METADATA` means a full-file hash plus an attempted bounded envelope inspection. PASS, size-limit, unsupported, and error counts remain separate; archive members were not extracted and are not separate filesystem rows.
- `FAST_METADATA_ONLY` means the path has a canonical row and pre/post metadata checks, but its bytes, hash, archive envelope, and content were intentionally not inspected by the fast profile.
- Secret containers, databases, logs, and mutable business/runtime datasets are intentionally metadata-only. This preserves privacy and does not count as content verification.
- Unsupported parsers remain `NOT_SUPPORTED`; full lexical/text scanning is not mislabeled as a syntax parse.
- Automated static inspection is not human semantic review. The semantic-review percentage therefore remains independently visible.

## Verification gaps

- A live SMB share is not an atomic filesystem snapshot. Stable repeated inventories reduce but cannot eliminate this gap.
- Junction/reparse targets outside the declared workspace boundary were not followed.
- NTFS alternate data streams were not enumerated by this cross-platform scanner.
- This rule-pack scan is not a formal Codex Security scan and does not replace dynamic/runtime, production, or human semantic verification.

## Knowledge labels

- **FACT:** Directly supported by the ledger, scan metadata, or sanitized finding records.
- **ASSUMPTION:** Any interpretation beyond those artifacts.
- **RECOMMENDATION:** Future remediation or deeper verification work; no remediation was performed here.
