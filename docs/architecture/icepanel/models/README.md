# IcePanel Model Files

This folder contains the canonical IcePanel-as-code model for the
`dlh-in-a-box` architecture and the JSON schema used to validate it.

```mermaid
flowchart TD
  Schema[dlh-in-a-box.schema.json] --> Model[dlh-in-a-box.json]
  Model --> Validator[JSON validator]
  Model --> Sync[IcePanel sync script]
  Model --> Exports[diagram exports]
```

## Files

| File | Purpose |
| --- | --- |
| [dlh-in-a-box.json](dlh-in-a-box.json) | Canonical model source. |
| [dlh-in-a-box.schema.json](dlh-in-a-box.schema.json) | Schema for the model file. |

## Maintenance

Edit the model source first, validate it with the architecture validation
script, and then regenerate exports from the validated model.
