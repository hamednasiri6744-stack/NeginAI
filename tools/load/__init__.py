"""Safe, read-only load-test tooling for NeginAI."""

# Keep package import side-effect free. Public helpers live in ``harness``;
# avoiding an eager import also makes ``python -m tools.load.harness`` clean.
