# Creator Revocation and Reuse Blocking

CreatorIdentityPack versions preserve the rights snapshot that existed when the pack was created. They are historical evidence and should not be rewritten when consent later changes.

Current authorization lives in the separate local-store `revocations` collection.

## Revoke a creator

```bash
python .archon/scripts/ugc/creator_revocation.py \
  --root ugc-studio/data \
  revoke creator-123 \
  --reason "creator withdrew consent" \
  --evidence-reference "agreement/ticket/notice-id"
```

An immediately effective revocation:

1. writes an immutable current-state revocation record,
2. finds stored jobs associated with that creator,
3. sets `rights_approved=false`,
4. sets `approved_for_spend=false`,
5. marks stored derived artifacts `reuse_blocked=true`, and
6. marks those artifacts `distribution_review_required=true`.

Historical CreativeSpecs, CreatorIdentityPacks, QA, and performance records are kept for audit rather than rewritten.

## Scheduled revocation

A future effective time can be recorded:

```bash
python .archon/scripts/ugc/creator_revocation.py \
  revoke creator-123 \
  --reason "agreement ends" \
  --effective-at 2027-01-01T00:00:00Z
```

Once effective, apply propagation:

```bash
python .archon/scripts/ugc/creator_revocation.py apply creator-123
```

A future production scheduler can invoke `apply` automatically when the effective time arrives.

## Check status

```bash
python .archon/scripts/ugc/creator_revocation.py status creator-123
```

## Render-preparation enforcement

`prepare_creator_assets.py` now checks the current revocation registry by default when used through its CLI. This check is separate from historical agreement-validity evaluation.

That distinction matters: passing an older `--on-date` cannot make a new render legal inside the system if the creator is revoked today.

The normal CLI uses:

```text
UGC_STORE_DIR=ugc-studio/data
```

or `--store-root <path>`.

## External takedown boundary

UGC Studio can stop new jobs and mark its own artifact records as restricted. It cannot automatically guarantee deletion from every external place an asset may already have been distributed, such as social networks, ad platforms, client downloads, or third-party storage.

`distribution_review_required=true` therefore means a downstream takedown/review workflow must decide what external action is required by the applicable agreement and circumstances.
