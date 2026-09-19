# Security and data handling

- Do not commit credentials, tokens, private paths, raw connectomes,
  checkpoints, videos, or large rollout arrays.
- Treat external archives and datasets as untrusted input; validate members,
  paths, size, license, and checksums before use.
- Keep source and generated artifacts under ignored directories and record
  provenance in manifests.
- Redact local machine paths and private metadata from public reports.
- Do not use a source report as if it were the underlying dataset.

This is an operational review, not a security certification.
