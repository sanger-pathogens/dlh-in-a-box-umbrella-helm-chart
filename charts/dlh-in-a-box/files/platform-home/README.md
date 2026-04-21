This directory contains static browser assets used by `platformHome`.

The main application HTML, CSS, and Python API code live inline in
[`../../templates/platform-home.yaml`](../../templates/platform-home.yaml).
This directory is only for file payloads that are easier to manage as separate
assets.

- `keycloak.js` is the vendored Keycloak browser adapter used by the launchpad
  so the portal does not depend on a separate `/js/keycloak.js` endpoint at
  runtime.
