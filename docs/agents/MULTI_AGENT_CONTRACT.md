# NeginAI Multi-Agent Coding Contract

## Objective

Allow the human owner, Codex, NeginAI Principal Engineer and other coding agents to increase throughput without
overwriting each other, mixing unrelated diffs or losing business intent.

## Default rule: one file, one active owner

At any moment, a materially edited file should have one active owner.

Before editing, every agent must:

1. read `git status --short --branch`;
2. inspect the diff for already-dirty files;
3. treat unexplained dirty/untracked files as somebody else's work;
4. avoid editing them unless the user explicitly assigns ownership or the current owner hands them off.

## Safe collaboration patterns

### Pattern A — subsystem split (preferred)

Example:
- Codex: Android/native bridge and UI shell
- NeginAI Principal Engineer: FastAPI contract, service logic and tests
- Integration owner: one named agent/user validates the combined boundary

### Pattern B — producer/consumer split

First agree on an interface contract.
One agent implements the producer; the other implements the consumer.
Neither changes the other's side without handoff.

### Pattern C — review + fix

One agent implements.
The other performs read-only review and returns exact findings.
The implementation owner applies fixes unless the user explicitly transfers ownership.

## Forbidden collision patterns

- two agents editing the same function simultaneously;
- automatic overwrite because one agent has "newer" output;
- `git reset --hard`, `git clean`, destructive checkout or forced restore to remove another agent's changes;
- hidden stash/rebase/merge used as conflict resolution;
- broad formatting of files outside the assigned task;
- mixing refactor and behavior change across multiple agents without a single integration owner.

## Branch/worktree policy

Parallel branches/worktrees are allowed only when the user explicitly asks for parallel implementation or the
integration owner decides they are necessary.

Do not create, delete, move or relocate a worktree automatically.
If a worktree is used, name the branch by task and define:
- owner;
- source branch/SHA;
- owned paths;
- integration owner;
- required cross-boundary tests.

## Handoff record

For material parallel work, create a short handoff under:

`docs/agents/collab/`

Include:
- task id;
- owner;
- base SHA;
- owned files;
- interface/assumptions;
- completed evidence;
- remaining risks;
- integration instructions.

Do not place secrets or temporary runtime data in handoffs.

## Integration gate

Before combining parallel work:

1. inspect both diffs;
2. check that no file ownership overlap occurred unexpectedly;
3. reconcile interface changes;
4. run boundary tests plus the narrow tests from both sides;
5. run the repository guardian;
6. only then commit/integrate.

## Human override

The user's explicit current instruction can reassign ownership or permit overlap.
When overlap is authorized, one agent must still be named integration owner.
