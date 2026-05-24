# MLOps Overview

What is MLOps and why and which tools and workflows.

```mermaid
graph LR
    A[Data Collection] --> B[Data Validation]
    B --> C[Feature Engineering]
    C --> D[Model Training]
    D --> E[Model Evaluation]
    E --> F{Approved?}
    F -->|Yes| G[Model Deployment]
    F -->|No| D
    G --> H[Model Monitoring]
    H --> I{Drift Detected?}
    I -->|Yes| A
    I -->|No| H
```

<figure markdown>
  ![MLOps Lifecycle Diagram](assets/images/mlops-lifecycle-diagram.png){ loading=lazy }
  <figcaption></figcaption>
</figure>

<!-- TODO - Should I create a dir and pack all the reading materials in that dir. Does it make sense? -->

* [Introduction](theory/introduction.md)
<!-- * [tbd](theory/???.md) -->
