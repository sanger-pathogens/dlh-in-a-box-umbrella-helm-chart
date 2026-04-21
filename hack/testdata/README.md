# Script Test Data

This folder contains small fake input files used by the maintainer scripts.

These files are not real deployments.

They are tiny fake inputs used only by local check scripts.

```mermaid
flowchart LR
  Fixtures[Test data files] --> Scripts[Maintainer scripts]
  Scripts --> PassFail[Expected pass or fail result]
```

## What is in this folder

| Path | Plain meaning |
| --- | --- |
| `render-contract/` | Small YAML files used by `hack/render-contract.sh` |

## When you can ignore this folder

You can ignore this folder unless you are changing validation or test scripts.

## Common mistake

These files are supposed to be small and fake. Do not turn them into full
real-world example files.
