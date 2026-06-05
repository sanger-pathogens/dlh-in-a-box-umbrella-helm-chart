# Specs

Design notes for chart behaviour that is larger than a single template or
values field.

```mermaid
flowchart LR
    Spec[Spec document] --> Values[values.yaml]
    Spec --> Templates[Helm templates]
    Templates --> Tests[render-contract fixtures]
```
