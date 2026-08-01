# Pull Request Template
# Delete sections that don't apply.

## Summary

<!-- One-liner: what does this PR change and why? -->

## Type of Change

- [ ] Bug fix (non-breaking)
- [ ] New feature (non-breaking)
- [ ] Breaking change (contracts / public API changed)
- [ ] Documentation only
- [ ] CI / build tooling

## Checklist

- [ ] All CI jobs pass (`lint`, `typecheck`, `test`, `docs`, `smoke`)
- [ ] New code has tests (`pytest --cov=ds_data_miner` still ≥ 85%)
- [ ] Docstrings updated (Sphinx reST format: `:param:`, `:return:`, `:raises:`)
- [ ] `CHANGELOG.md` entry added under `[Unreleased]`
- [ ] If this is a **breaking change**: `DatasetReport` JSON Schema version bumped

## Related Issues

<!-- Closes #123 -->
