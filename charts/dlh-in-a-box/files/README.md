This directory contains static assets packaged into rendered Kubernetes
objects.

Most readers do not need this directory directly. It matters when you are
working on chart-owned browser assets or other file payloads that are embedded
into ConfigMaps or mounted volumes.

- `platform-home/` stores the browser-launchpad asset(s) packaged by
  `templates/platform-home.yaml`.

See [platform-home/README.md](platform-home/README.md) for the only current
child guide here.
