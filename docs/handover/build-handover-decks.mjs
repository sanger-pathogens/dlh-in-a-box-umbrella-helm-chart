import fs from "node:fs/promises";
import { readFileSync } from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";

import PptxGenJS from "pptxgenjs";
import { chromium } from "playwright";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const DOCS_DIR = path.dirname(SCRIPT_DIR);
const REPO_DIR = path.dirname(DOCS_DIR);
const HANDOVER_DIR = path.join(DOCS_DIR, "handover");
const PPTX_DIR = path.join(HANDOVER_DIR, "pptx");
const PDF_DIR = path.join(HANDOVER_DIR, "pdf");
const PREVIEWS_DIR = path.join(HANDOVER_DIR, "previews");
const ASSETS_DIR = path.join(HANDOVER_DIR, "assets");
const MERMAID_DIR = path.join(ASSETS_DIR, "mermaid");
const ICEPANEL_LIGHT = path.join(
  DOCS_DIR,
  "architecture",
  "icepanel",
  "exports",
  "dlh-in-a-box",
  "png-light"
);
const ICON_PATH = path.join(DOCS_DIR, "assets", "dlh-in-a-box-icon.jpg");
const MERMAID_BROWSER_BUNDLE = path.join(
  DOCS_DIR,
  "node_modules",
  "mermaid",
  "dist",
  "mermaid.min.js"
);

const SLIDE_W = 13.333;
const SLIDE_H = 7.5;
const PX_W = 1920;
const PX_H = 1080;

const colors = {
  ink: "102A43",
  muted: "52606D",
  faint: "F8FAFC",
  surface: "EEF5F2",
  border: "CBD2D9",
  accent: "1B6E55",
  link: "0F6CBD",
  dark: "0B1F2A",
  white: "FFFFFF",
  sand: "F5F7F4",
  warn: "A65B00",
};

const mermaidSources = {
  repoShape: {
    source: "README.md",
    block: 0,
    title: "Repository shape and platform shape",
  },
  platformAllComponents: {
    source: "docs/umbrella-chart-manual.md",
    block: 0,
    title: "All optional platform components",
  },
  assemblyFlow: {
    source: "docs/umbrella-chart-manual.md",
    block: 1,
    title: "How the chart assembles the runtime",
  },
  profileMap: {
    source: "examples/README.md",
    block: 0,
    title: "Example profile taxonomy",
  },
  chartLogic: {
    source: "charts/dlh-in-a-box/README.md",
    block: 0,
    title: "Values into chart logic and runtime",
  },
  templateFlow: {
    source: "charts/dlh-in-a-box/templates/_README.txt",
    block: 0,
    title: "Umbrella template coordination flow",
  },
  authFlow: {
    source: "docs/umbrella-chart-manual.md",
    block: 3,
    title: "Identity and browser access flow",
  },
  rangerAutomation: {
    source: "docs/umbrella-chart-manual.md",
    block: 4,
    title: "Ranger automation flow",
  },
  dataPath: {
    source: "docs/umbrella-chart-manual.md",
    block: 5,
    title: "Query storage and metadata path",
  },
  trinoPatch: {
    source: "charts/dlh-in-a-box/charts/trino/templates/_README.txt",
    block: 0,
    title: "Trino patch model",
  },
  hiveFlow: {
    source: "charts/dlh-in-a-box/charts/hive/README.md",
    block: 0,
    title: "Hive subchart flow",
  },
  validationFlow: {
    source: "docs/umbrella-chart-manual.md",
    block: 6,
    title: "Local validation and CI flow",
  },
  workflowFlow: {
    source: ".github/workflows/README.md",
    block: 0,
    title: "GitHub workflow inventory",
  },
  scriptFlow: {
    source: "scripts/README.md",
    block: 0,
    title: "Maintainer script flow",
  },
};

const icepanel = {
  context: "01-context.png",
  packaging: "02-chart-product-and-packaging.png",
  runtime: "03-runtime-deployed-by-the-chart.png",
  chartSource: "04-chart-source-components.png",
  dependencies: "05-packaged-upstream-dependencies.png",
  trino: "06-vendored-trino-chart.png",
  hive: "07-hive-metastore-local-subchart.png",
  validation: "08-chart-validation-automation.png",
  publish: "09-chart-publish-automation.png",
  identity: "10-runtime-identity-access-secrets.png",
  dataRuntime: "11-runtime-data-analysis-orchestration.png",
};

const sessions = [
  {
    number: 1,
    slug: "repository-orientation-product-mental-model",
    title: "Repository Orientation And Product Mental Model",
    promise: "New maintainers can explain what the chart is, what it is not, and where to start.",
    sources: [
      "README.md",
      "docs/umbrella-chart-manual.md",
      "docs/architecture/dlh-in-a-box-icepanel-model.md",
    ],
    diagrams: ["repoShape", "context"],
    slides: [
      cover(
        "Repository Orientation And Product Mental Model",
        "Session 01 / DLH-in-a-box handover",
        "The repo is a reusable umbrella chart product, not a deployment repository or cluster bootstrap kit.",
        image("icepanel", "context"),
        [
          "Open by framing this as the first hour for developers who have never touched the work.",
          "The core handover message: they are inheriting a packaging and integration surface for a data lakehouse runtime.",
          "Point out that this series stays inside the published repository surface.",
        ]
      ),
      agenda(["Problem and boundary", "Repo shape", "First-success path", "Where to change things"], [
        "Set expectations: this is not a Kubernetes or Helm basics class.",
        "The goal is to give maintainers a map they can use when incidents or change requests arrive.",
      ]),
      bullets("The one-sentence product story", "What the repository publishes", [
        "One Helm chart named dlh-in-a-box.",
        "One install surface for login, query services, storage, browser tools, and access control.",
        "A reusable chart product consumed by institution-specific deployment repositories.",
        "A set of examples, scripts, and docs that define the supported operating lanes.",
      ], "Source: root README; manual, What This Repository Is For.", [
        "Do not start with the component list. Start with the decision this repo removes: teams do not wire every product together from scratch.",
        "Emphasize that the repository is valuable because the integration decisions are encoded and testable.",
      ]),
      imageSlide("Repo shape: source, examples, scripts, guides", image("mermaid", "repoShape"), [
        "The chart is the deployable product.",
        "Examples document supported install shapes.",
        "Scripts and workflows keep local and CI validation aligned.",
        "Guides explain ownership at the directory boundary.",
      ], "Source: README.md Mermaid diagram.", [
        "Use the diagram as the first mental map. The left side is repository material; the right side is what the chart can assemble.",
        "Tell the audience that every later deck is a zoom into one part of this map.",
      ]),
      imageSlide("Context: product, consumer repo, runtime", image("icepanel", "context"), [
        "Operators prepare institutional configuration.",
        "Consumer repos select chart versions and provide settings.",
        "The chart defines a generic lakehouse runtime.",
        "Users experience the deployed runtime, not this source repo directly.",
      ], "Source: IcePanel 01-context.", [
        "This is the handover's most important distinction: chart product versus runtime instance.",
        "If a future question mentions Sanger or icddr,b specifics, ask whether it belongs here or in a consumer deployment repository.",
      ]),
      tableSlide("What this repo is and is not", ["It is", "It is not"], [
        ["A Helm umbrella chart product", "A cluster bootstrap toolkit"],
        ["A reproducible package of upstream and local chart material", "A replacement for upstream product documentation"],
        ["A values contract plus examples and validation", "A source of real production secrets or DNS"],
        ["A maintainer workflow with CI parity", "An institution's governance approval process"],
      ], "Source: README.md; manual boundary sections.", [
        "Read this slide slowly. Many future mistakes come from assuming the chart owns infrastructure or policy decisions that it deliberately does not own.",
      ]),
      bullets("First success is deliberately small", "Recommended newcomer path", [
        "Start with examples/values-local.yaml.",
        "Refresh dependencies before rendering or installing.",
        "Use make smoke-install only when validating auth-heavy behavior.",
        "Treat values-local-auth.yaml as the smoke profile, not the easiest manual start.",
      ], "Source: README.md; manual One True First-Success Path.", [
        "This corrects a common newcomer trap. make local-install currently points at the auth-heavy local profile.",
        "The handover audience should know both paths, but only one is the first manual success path.",
      ]),
      demoSlide("Guided checkpoint: orient a new maintainer", [
        "./scripts/helm-dependency-update.sh",
        "helm template dlh charts/dlh-in-a-box -f examples/values-local.yaml >/tmp/dlh-local.yaml",
        "helm lint charts/dlh-in-a-box -f examples/values-local.yaml",
      ], [
        "Can they say which files explain the install path?",
        "Can they explain why smoke-install is a stronger but heavier path?",
        "Can they find the chart guide and template guide without searching randomly?",
      ], [
        "Do not require a live cluster for this checkpoint. The purpose is orientation and confidence.",
        "If running live, stop after render/lint unless you intentionally want a cluster install.",
      ]),
      tableSlide("If you need to change X, start here", ["Change request", "Start with"], [
        ["Chart metadata, dependency list, publish version", "charts/dlh-in-a-box/Chart.yaml"],
        ["Shared defaults or public values contract", "charts/dlh-in-a-box/values.yaml and values.schema.json"],
        ["Supported install profile", "examples/*.yaml"],
        ["Local validation or smoke behavior", "scripts/*.sh"],
        ["CI or release behavior", ".github/workflows/*.yaml"],
      ], "Source: README.md; manual Contributor Change Map.", [
        "This is not a complete change map, just the triage version for session one.",
        "Reinforce the habit: find ownership first, then edit.",
      ]),
      closeSlide("Session 01 landing", [
        "They can describe the repo in one sentence.",
        "They can distinguish chart product from deployed runtime.",
        "They know the safest first manual path.",
        "They have a first lookup map for future changes.",
      ], [
        "Close by previewing session two: the architecture model turns this orientation into a more precise runtime and packaging map.",
      ]),
    ],
  },
  {
    number: 2,
    slug: "architecture-model-runtime-topology",
    title: "Architecture Model And Runtime Topology",
    promise: "Developers can read the IcePanel model and use it to reason about packaging and runtime boundaries.",
    sources: [
      "docs/architecture/README.md",
      "docs/architecture/dlh-in-a-box-icepanel-model.md",
      "docs/umbrella-chart-manual.md",
    ],
    diagrams: ["context", "packaging", "runtime", "platformAllComponents", "assemblyFlow"],
    slides: [
      cover(
        "Architecture Model And Runtime Topology",
        "Session 02 / C4 and IcePanel handover",
        "The model separates chart product, published package, consumer configuration, and deployed runtime.",
        image("icepanel", "runtime"),
        ["Open with the promise: after this session, architecture diagrams should reduce confusion rather than add a new artifact to maintain."]
      ),
      agenda(["Modelling rules", "Packaging view", "Runtime view", "How diagrams support changes"], [
        "Explain that the model is intentionally generic and excludes deployment-specific infrastructure except as external context.",
      ]),
      bullets("The model is scoped to the reusable chart", "What belongs in this architecture view", [
        "DLH-in-a-box as a Helm chart product.",
        "The generic runtime instantiated by the chart.",
        "Upstream dependency sources and packaged artifacts.",
        "Owned component diagrams for chart source, Hive, Trino patch points, validation, and publish automation.",
      ], "Source: IcePanel model, Modelling Rules.", [
        "Use this slide to prevent scope creep. The architecture model is not the Sanger or icddr,b deployment architecture.",
      ]),
      imageSlide("Level 1: context and consumers", image("icepanel", "context"), [
        "Consumer repositories select chart versions.",
        "Institutional settings live outside the chart product.",
        "The runtime is the system operators and users experience.",
      ], "Source: IcePanel 01-context.", [
        "Point to the direction of flow: upstream dependencies feed the chart; consumer repos configure it; the runtime runs on a target cluster.",
      ]),
      imageSlide("Level 2A: chart product and packaging", image("icepanel", "packaging"), [
        "Chart source declares dependencies and templates.",
        "Packaged upstream archives make resolution reproducible.",
        "Validation and publish automation protect the package before release.",
        "The OCI package is what deployment repos consume.",
      ], "Source: IcePanel 02-chart-product-and-packaging.", [
        "This is the maintainers' build-and-release view. Use it when someone changes dependency versions or package contents.",
      ]),
      imageSlide("Level 2B: runtime deployed by the chart", image("icepanel", "runtime"), [
        "Trino sits at the centre of the query plane.",
        "Identity and browser entrypoints sit above runtime tools.",
        "Prefect, Spark, and optional apps surround the core data path.",
        "Support stores belong near the services that own them.",
      ], "Source: IcePanel 03-runtime-deployed-by-the-chart.", [
        "This is the operational view. It is dense, so narrate around the central Trino/data-plane cluster first.",
      ]),
      imageSlide("Manual view: everything enabled", image("mermaid", "platformAllComponents"), [
        "The chart is modular; not every install enables every component.",
        "Browser entrypoints, identity, governance, query, orchestration, and storage are separate lanes.",
        "Optional services are still part of the model because examples can turn them on.",
      ], "Source: manual Platform Architecture Mermaid.", [
        "Use this as a friendlier bridge between prose docs and the more formal IcePanel runtime view.",
      ]),
      imageSlide("How the chart assembles the runtime", image("mermaid", "assemblyFlow"), [
        "Values drive validation, templates, dependency charts, and rendered resources.",
        "Example overlays exercise supported combinations.",
        "CI tests rendering and packaging rather than pretending one deployment shape covers all cases.",
      ], "Source: manual How The Chart Assembles The Runtime Mermaid.", [
        "This is the transition from architecture to implementation. Session four will go deeper into this path.",
      ]),
      tableSlide("Use the right diagram for the question", ["Question", "Best diagram"], [
        ["Who consumes the chart?", "Context"],
        ["What gets packaged and published?", "Chart product and packaging"],
        ["What runs in a cluster?", "Runtime deployed by the chart"],
        ["Where is local chart logic?", "Chart source components"],
        ["How is CI or publish wired?", "Validation and publish automation"],
      ], "Source: IcePanel model diagram set.", [
        "Give maintainers permission to choose a diagram based on the question instead of opening the largest one first.",
      ]),
      demoSlide("Guided checkpoint: trace one feature through the model", [
        "Open docs/architecture/dlh-in-a-box-icepanel-model.md",
        "Find the Level 2 runtime object for Trino",
        "Follow its relationships to Hive, storage, identity, and Ranger",
      ], [
        "Can the developer explain whether the change belongs in chart source, a subchart, or consumer settings?",
        "Can they name the external systems versus repo-owned material?",
      ], [
        "Run this as a whiteboard exercise if not using a laptop. Pick Trino because it touches the most important boundaries.",
      ]),
      closeSlide("Session 02 landing", [
        "They know why there are separate product and runtime views.",
        "They can choose the diagram that answers a maintainer question.",
        "They understand why deployment-specific infrastructure is mostly outside this model.",
      ], ["Preview session three: now that the topology is clear, the next handover shows how install profiles choose runtime shapes."]),
    ],
  },
  {
    number: 3,
    slug: "install-profiles-first-successful-deployment",
    title: "Install Profiles And First Successful Deployment",
    promise: "Developers can choose the right example values file and understand what it proves.",
    sources: ["README.md", "docs/umbrella-chart-manual.md", "examples/README.md"],
    diagrams: ["profileMap"],
    slides: [
      cover("Install Profiles And First Successful Deployment", "Session 03 / Values overlays and first success", "Examples are not samples in a bag; they are the documented install profiles the repo maintains.", image("mermaid", "profileMap"), [
        "Open by explaining that many problems are caused by starting with the wrong values file.",
      ]),
      agenda(["Prerequisites", "Profile taxonomy", "Local versus shared", "Demo checkpoints"], [
        "This session should leave developers able to pick an overlay before running Helm.",
      ]),
      bullets("Prerequisites are operational, not optional", "Before any install path", [
        "A working Kubernetes cluster and current kubectl context.",
        "Helm installed; CI currently uses Helm v3.12.0.",
        "Enough cluster capacity for several services and jobs.",
        "Docker and kind only when using the disposable local path or Mermaid rendering.",
      ], "Source: manual Prerequisites.", [
        "Stress current kube context. Many apparent chart failures are actually wrong-context failures.",
      ]),
      imageSlide("Example files fall into two classes", image("mermaid", "profileMap"), [
        "Full profiles are meant to stand alone.",
        "Specialist overlays modify one concern and must be layered after a base profile.",
        "Local profiles can carry disposable credentials.",
        "Shared profiles expect real DNS, TLS, secrets, and identity inputs.",
      ], "Source: examples/README.md Mermaid.", [
        "This is the main teaching diagram for the session. Talk through local, shared, and specialist columns.",
      ]),
      tableSlide("Which profile should I start with?", ["Profile", "Use when", "Caveat"], [
        ["values-local.yaml", "Fastest local first success", "Does not test browser auth flows"],
        ["values-local-auth.yaml", "Smoke test login, proxies, Ranger", "Use make smoke-install normally"],
        ["values-dev.yaml", "Shared development baseline", "Needs real hostnames, secrets, LDAP"],
        ["values-prod.yaml", "Production-shaped baseline", "Still not turnkey production"],
        ["values-shared-auth.yaml", "External OIDC exists", "Does not bundle Keycloak"],
      ], "Source: examples/README.md.", [
        "Use this as a decision table. Keep the key caveat visible: local-auth is not the easiest first manual profile.",
      ]),
      bullets("The first manual path is intentionally smaller", "What values-local.yaml proves", [
        "Trino plus Hive plus MinIO wiring.",
        "Prefect server and worker local setup.",
        "Spark Operator and Vault defaults.",
        "Core rendering and install flow without browser SSO complexity.",
      ], "Source: examples/README.md; manual first-success path.", [
        "The point is not to prove every feature. The point is to get a known-good local release with the least identity complexity.",
      ]),
      bullets("The smoke path is intentionally stronger", "What values-local-auth.yaml proves", [
        "Bundled Keycloak with local demo users.",
        "OIDC client wiring and oauth2-proxy entrypoints.",
        "Ranger bootstrap and local-user sync.",
        "platformHome launchpad and protected app access.",
      ], "Source: README.md; scripts/smoke-install.sh guide.", [
        "The smoke path validates integration that simple local installs deliberately skip.",
      ]),
      tableSlide("Secrets and inputs by profile class", ["Class", "Secret posture", "Maintainer habit"], [
        ["Disposable local", "Inline demo values may exist", "Keep them local-only and documented"],
        ["Auth-heavy smoke", "Script seeds demo Secrets", "Do not run plain Helm and expect success"],
        ["Shared dev/prod", "External secret delivery expected", "Never add inline real secrets"],
        ["Specialist storage", "Inherits base auth and app shape", "Layer after the full profile"],
      ], "Source: examples/README.md; security-check.sh.", [
        "Connect this slide to the security check. The repo enforces that non-local examples stay free of inline sensitive values.",
      ]),
      demoSlide("Guided checkpoint: choose and render a profile", [
        "./scripts/helm-dependency-update.sh",
        "helm template dlh charts/dlh-in-a-box -f examples/values-local.yaml >/tmp/dlh-local.yaml",
        "helm template dlh charts/dlh-in-a-box -f examples/values-dev.yaml -f examples/values-external-s3.yaml >/tmp/dlh-dev-s3.yaml",
      ], [
        "Can they explain which one is standalone and which one is layered?",
        "Can they name what the local render proves and what it skips?",
      ], [
        "This demo is safe without a cluster. If rendering shared profiles fails, discuss missing external inputs rather than treating it as a chart defect.",
      ]),
      bullets("Common first-time failures", "Most failures have a short cause list", [
        "Dependencies or Chart.lock are stale.",
        "kubectl points at the wrong cluster.",
        "The cluster is too small for the chosen profile.",
        "The auth-heavy local profile was run without the smoke script's demo Secrets.",
      ], "Source: README.md; manual Troubleshooting.", [
        "This is a practical incident slide. Encourage maintainers to ask these four questions before diving into templates.",
      ]),
      closeSlide("Session 03 landing", [
        "They can choose the right values file for a goal.",
        "They know full profiles versus specialist overlays.",
        "They understand why first-success and smoke paths are different.",
      ], ["Preview session four: next we open the chart internals that make these profiles render into resources."]),
    ],
  },
  {
    number: 4,
    slug: "chart-internals-values-contract-render-flow",
    title: "Chart Internals, Values Contract, And Render Flow",
    promise: "Developers can trace values through validation, templates, dependencies, and rendered resources.",
    sources: [
      "charts/dlh-in-a-box/README.md",
      "charts/dlh-in-a-box/templates/_README.txt",
      "docs/umbrella-chart-manual.md",
    ],
    diagrams: ["chartSource", "chartLogic", "templateFlow"],
    slides: [
      cover("Chart Internals, Values Contract, And Render Flow", "Session 04 / How the chart works", "The chart is a shared contract plus umbrella-owned glue around upstream dependencies.", image("icepanel", "chartSource"), [
        "Open by saying: this is the hour where maintainers learn where not to edit as much as where to edit.",
      ]),
      agenda(["Ownership layers", "Values categories", "Validation templates", "Lookup behavior"], [
        "The goal is not to memorize files. The goal is to understand the render path.",
      ]),
      imageSlide("Chart source components", image("icepanel", "chartSource"), [
        "Chart.yaml and Chart.lock define packaged dependency state.",
        "values.yaml and values.schema.json define the public input surface.",
        "templates/ contains umbrella-owned behavior.",
        "third_party/ and notices travel with packaged material.",
      ], "Source: IcePanel 04-chart-source-components.", [
        "This diagram is intentionally file-heavy. Use it as an ownership map rather than a runtime diagram.",
      ]),
      imageSlide("Values drive validation, templates, and dependencies", image("mermaid", "chartLogic"), [
        "global.identity, global.authorization, global.storage, and global.dataCatalogs are cross-component contracts.",
        "App-specific sections configure repo-owned wrappers.",
        "Dependency sections pass through upstream chart values.",
      ], "Source: charts/dlh-in-a-box/README.md Mermaid.", [
        "Explain that values.yaml is large because it has two jobs: local contract plus upstream pass-through.",
      ]),
      tableSlide("Read values.yaml by category", ["Category", "Examples", "What changes"], [
        ["Shared contract", "global.identity, global.authorization, global.storage, global.dataCatalogs", "Cross-component behavior"],
        ["Repo-owned apps", "platformHome, cloudbeaver, auth proxy sections", "Umbrella-specific logic"],
        ["Dependency pass-through", "keycloak, minio, superset, jupyterhub, datahub", "Upstream chart configuration"],
        ["Local subcharts", "hive, hivePostgresql", "First-party metastore behavior"],
      ], "Source: chart guide, How Values Are Organized.", [
        "This is the reading strategy maintainers should use before touching values.",
      ]),
      imageSlide("Umbrella templates coordinate the runtime", image("mermaid", "templateFlow"), [
        "Validation templates fail fast on unsupported combinations.",
        "platformHome, CloudBeaver, Ranger, and DataHub helpers adapt upstream services.",
        "Template behavior is often where product assumptions live.",
      ], "Source: templates/_README.txt Mermaid.", [
        "Warn that the most behavior-heavy files are templates, not always separate application source files.",
      ]),
      tableSlide("Fail-fast validation lives in more than schema", ["File", "What it blocks"], [
        ["values.schema.json", "Input shape and allowed structural forms"],
        ["identity-validation.yaml", "Unsupported identity modes, missing client wiring, app auth inconsistencies"],
        ["governance-validation.yaml", "Broken platform roles, incomplete governance metadata, unsafe authorization settings"],
      ], "Source: manual Values Model And Render Flow.", [
        "Make clear that schema validation is necessary but not sufficient.",
      ]),
      bullets("Helm lookup makes upgrade renders different", "Upgrade-sensitive behavior", [
        "CloudBeaver can read existing Secrets for rollout checksums.",
        "DataHub auth material is preserved across upgrades.",
        "DataHub prerequisite compatibility can mirror existing MySQL Secrets.",
        "Trino helpers can read existing S3 credentials for generated catalogs.",
      ], "Source: manual Render-Time lookup Behavior.", [
        "This is one of the subtle maintainer topics. Offline helm template is not always the same as an in-cluster upgrade.",
      ]),
      demoSlide("Guided checkpoint: trace a values rule", [
        "Open charts/dlh-in-a-box/values.yaml",
        "Open charts/dlh-in-a-box/values.schema.json",
        "Open charts/dlh-in-a-box/templates/identity-validation.yaml",
        "Render one positive and one negative contract fixture with ./scripts/render-contract.sh",
      ], [
        "Can they explain whether a rule belongs in schema or a validation template?",
        "Can they explain what a render-contract fixture is proving?",
      ], [
        "If running live, render-contract can take a little time. The teaching value is the positive versus negative contract distinction.",
      ]),
      tableSlide("Behavior-heavy files worth reading first", ["Area", "Start file"], [
        ["platformHome launchpad and helper API", "templates/platform-home.yaml"],
        ["Ranger automation and audits", "templates/ranger-automation.yaml"],
        ["CloudBeaver bootstrap and trust behavior", "templates/cloudbeaver.yaml"],
        ["DataHub auth and prerequisite compatibility", "templates/datahub-auth-secrets.yaml; datahub-prerequisites-compat.yaml"],
        ["Ranger browser boundary", "templates/ranger-browser-proxy.yaml"],
      ], "Source: manual Component Guide.", [
        "Tell maintainers to start from the guide, not from a full-tree search. The guide names the files that carry product behavior.",
      ]),
      closeSlide("Session 04 landing", [
        "They can read values by ownership category.",
        "They know schema is not the full validation story.",
        "They can explain why lookup affects upgrade behavior.",
        "They know the main behavior-heavy template entrypoints.",
      ], ["Preview session five: identity is the most cross-cutting part of that render flow."]),
    ],
  },
  {
    number: 5,
    slug: "identity-browser-access",
    title: "Identity And Browser Access",
    promise: "Developers can reason about provider mode, directory mode, direct OIDC, and oauth2-proxy boundaries.",
    sources: ["charts/dlh-in-a-box/README.md", "docs/umbrella-chart-manual.md"],
    diagrams: ["authFlow", "identity"],
    slides: [
      cover("Identity And Browser Access", "Session 05 / Auth modes and entrypoints", "The chart orchestrates a system-wide identity contract rather than configuring each browser app independently.", image("icepanel", "identity"), [
        "Open by acknowledging this is the area most likely to confuse newcomers.",
      ]),
      agenda(["Two identity axes", "Browser entrypoints", "Direct OIDC versus proxy", "Local auth-heavy story"], [
        "The payoff is being able to debug auth issues by asking which axis or boundary is involved.",
      ]),
      imageSlide("Runtime identity, access, and secrets", image("icepanel", "identity"), [
        "Keycloak or external OIDC issues browser identity.",
        "Secrets may be supplied externally or by included services.",
        "Browser auth proxies protect selected apps.",
        "Trino, Ranger, and app runtimes consume identity differently.",
      ], "Source: IcePanel 10-runtime-identity-access-secrets.", [
        "Use this as the high-level runtime map. It is dense; narrate top-down from user entry to service access.",
      ]),
      imageSlide("Auth and control flow", image("mermaid", "authFlow"), [
        "Users enter through browser-facing applications.",
        "Apps either handle OIDC directly or sit behind oauth2-proxy.",
        "Ranger policies and generated file rules are authorization control planes.",
      ], "Source: manual Auth And Control Flow Mermaid.", [
        "This diagram shows why app-by-app auth debugging can be misleading. The chart wires a shared flow.",
      ]),
      tableSlide("Identity has two independent axes", ["Axis", "Setting", "Meaning"], [
        ["Provider", "bundledKeycloak", "The chart deploys Keycloak and manages clients"],
        ["Provider", "externalOidc", "An existing OIDC provider is consumed"],
        ["Directory", "externalLdap", "Users and groups come from LDAP or AD"],
        ["Directory", "keycloakLocal", "Keycloak manages local demo users"],
      ], "Source: chart guide Identity Model.", [
        "Do not let the audience collapse provider and directory into one question. They are separate axes.",
      ]),
      tableSlide("Supported combinations that matter", ["Provider", "Directory", "Use case"], [
        ["bundledKeycloak", "externalLdap", "Default shared dev and prod pattern"],
        ["bundledKeycloak", "keycloakLocal", "Local auth-heavy smoke and demo pattern"],
        ["externalOidc", "externalLdap", "Escape hatch when an external IdP exists"],
      ], "Source: manual Supported Combinations.", [
        "Also mention the restrictions: platformHome currently requires bundled Keycloak, and local Keycloak users plus LDAP-backed Ranger usersync are mutually exclusive.",
      ]),
      tableSlide("Which apps use which browser boundary?", ["App", "Pattern", "Why"], [
        ["Trino UI", "Direct OIDC", "Trino handles login itself"],
        ["JupyterHub, Superset, DataHub", "Direct OIDC", "Each app has its own OIDC client wiring"],
        ["CloudBeaver", "oauth2-proxy", "Proxy owns browser sign-in"],
        ["Prefect", "oauth2-proxy", "Proxy protects browser UI"],
        ["Ranger browser access", "oauth2-proxy plus browser proxy", "Ranger Admin is not exposed directly as the main surface"],
      ], "Source: manual Which Apps Use Direct OIDC.", [
        "This table is the fastest way to debug 'why does this app behave differently?'",
      ]),
      bullets("platformHome is special", "Current implementation constraint", [
        "It is a launchpad UI and helper API rendered by templates/platform-home.yaml.",
        "It currently uses the Keycloak JavaScript adapter directly.",
        "That means platformHome requires bundled Keycloak today.",
        "Most code lives inline in the template rather than files/platform-home/.",
      ], "Source: manual Component Guide; chart guide restrictions.", [
        "Call this out because it is a likely future change request and a common surprise.",
      ]),
      bullets("The local auth-heavy story is intentionally different", "Smoke path identity shape", [
        "Bundled Keycloak is enabled.",
        "Keycloak manages local users directly.",
        "Ranger LDAP usersync is disabled.",
        "Demo Secrets are seeded by smoke-install.sh.",
      ], "Source: manual Local Auth-Heavy Story.", [
        "This explains why a plain Helm install of values-local-auth.yaml is not equivalent to make smoke-install.",
      ]),
      demoSlide("Guided checkpoint: classify an auth problem", [
        "Ask: provider mode or directory mode?",
        "Ask: direct OIDC app or oauth2-proxy app?",
        "Ask: browser login problem or backend authorization problem?",
        "Then inspect values, validation output, generated client settings, and relevant app template.",
      ], [
        "Can the developer place CloudBeaver, Trino UI, and platformHome on the right boundary?",
        "Can they explain why a local auth smoke issue may involve seeded Secrets?",
      ], [
        "Use a hypothetical incident instead of a live cluster if needed: CloudBeaver login fails, Trino UI works, platformHome is enabled.",
      ]),
      closeSlide("Session 05 landing", [
        "They can separate provider mode from directory mode.",
        "They know which apps use direct OIDC versus proxy boundaries.",
        "They understand the platformHome bundled-Keycloak constraint.",
        "They can triage auth issues by boundary instead of by product name alone.",
      ], ["Preview session six: identity is only half the access story; authorization and Ranger are next."]),
    ],
  },
  {
    number: 6,
    slug: "governance-authorization-ranger",
    title: "Governance, Authorization, And Ranger",
    promise: "Developers can distinguish governance state, Ranger administration, and Trino query-time authorization.",
    sources: ["charts/dlh-in-a-box/README.md", "docs/umbrella-chart-manual.md"],
    diagrams: ["rangerAutomation", "identity"],
    slides: [
      cover("Governance, Authorization, And Ranger", "Session 06 / Roles, policies, and enforcement", "Ranger can exist as a governance service even when Trino is still authorized by generated file rules.", image("mermaid", "rangerAutomation"), [
        "Open with the subtlety: Ranger enabled does not automatically mean Trino queries are authorized by the Ranger plugin.",
      ]),
      agenda(["Governance concepts", "Validation rules", "Ranger automation", "Trino enforcement matrix"], [
        "This session is partly about terminology. Use precise language throughout.",
      ]),
      bullets("Governance is part of the chart contract", "Not just infrastructure wiring", [
        "Platform roles describe durable app and data entitlements.",
        "Direct-user exceptions require approval metadata and expiry.",
        "Governed catalogs carry PI, IRB, consent, and approval metadata.",
        "Ranger bootstrap policies can be reconciled into Ranger.",
      ], "Source: manual Governance Concepts.", [
        "Explain that these are institution-shaped concepts encoded by current chart validation, not generic Helm ideas.",
      ]),
      tableSlide("Core authorization values", ["Values path", "What it means"], [
        ["global.authorization.platformRoles", "Named roles mapped into app entitlements and Ranger roles"],
        ["global.authorization.platformRoleExceptions", "Controlled direct-user exceptions with approval metadata"],
        ["global.dataCatalogs.<name>.governance", "Catalog-level metadata that controls whether data may be exposed"],
        ["global.authorization.ranger.bootstrapPolicies", "Policy definitions reconciled into Ranger"],
      ], "Source: chart guide Governance And Authorization Model.", [
        "This table anchors the rest of the session in the values contract.",
      ]),
      bullets("Governance validation prevents unsafe combinations", "Representative enforced rules", [
        "Every platform role needs a description.",
        "App entitlements must use supported app names.",
        "Direct-user exceptions need approval reference, reason, grantor, and expiry.",
        "Restricted data cannot rely on unsafe wildcard access patterns.",
        "Identifiable restricted data needs masking or row-filter policy coverage.",
      ], "Source: manual What The Governance Validation Layer Enforces.", [
        "Do not present this as an exhaustive code listing. Present it as the shape of safety rails maintainers must preserve.",
      ]),
      imageSlide("Ranger automation flow", image("mermaid", "rangerAutomation"), [
        "Values become generated bootstrap configuration.",
        "Embedded Python reconciles Ranger state.",
        "Jobs and CronJobs handle bootstrap, usersync, local-user sync, and exception audits.",
        "The runtime target may be Ranger, LDAP or AD, or local Keycloak users.",
      ], "Source: manual Ranger Automation Flow Mermaid.", [
        "This is one of the behavior-heavy template areas. Connect it to templates/ranger-automation.yaml.",
      ]),
      tableSlide("Where authorization actually happens", ["Situation", "Ranger Admin?", "Trino query authorization"], [
        ["Ranger disabled", "No", "Generated file-based Trino rules"],
        ["Ranger enabled; ranger.trino=false", "Yes", "Generated file-based Trino rules"],
        ["Ranger enabled; ranger.trino=true; compatible Trino image", "Yes", "Ranger plugin path"],
      ], "Source: manual Trino And Ranger Control Matrix.", [
        "This is the key slide. Say it twice: Ranger as governance admin and Ranger as Trino query-time enforcement are related but not identical.",
      ]),
      bullets("Ranger templates are behavior-heavy", "Where to read code", [
        "templates/ranger-automation.yaml embeds reconciliation logic.",
        "templates/_ranger-admin.tpl owns bootstrap text templates.",
        "templates/ranger-admin.yaml renders runtime shell resources.",
        "templates/ranger-browser-proxy.yaml protects browser access.",
      ], "Source: manual Component Guide; templates guide.", [
        "Use this as an ownership handoff. These files need careful review when access behavior changes.",
      ]),
      demoSlide("Guided checkpoint: diagnose 'Ranger is enabled but Trino still uses file rules'", [
        "Check global.authorization.ranger.enabled",
        "Check global.authorization.ranger.trino.enabled",
        "Check the Trino image/plugin compatibility expectation",
        "Inspect rendered access-control config for coordinator",
      ], [
        "Can the developer explain why Ranger Admin may be present but not query-time enforcing?",
        "Can they find the template path that renders Trino access control?",
      ], [
        "This checkpoint should become a stock troubleshooting playbook for future maintainers.",
      ]),
      closeSlide("Session 06 landing", [
        "They know the governance values that matter.",
        "They understand why validation is strict for governed data.",
        "They can explain Ranger automation at a high level.",
        "They can distinguish Ranger Admin from Trino enforcement.",
      ], ["Preview session seven: now follow the actual query, storage, and metadata path."]),
    ],
  },
  {
    number: 7,
    slug: "query-storage-metadata-app-runtime",
    title: "Query, Storage, Metadata, And App Runtime",
    promise: "Developers can trace global.dataCatalogs through Hive, Trino, storage, metadata discovery, and analysis tools.",
    sources: [
      "docs/umbrella-chart-manual.md",
      "charts/dlh-in-a-box/charts/hive/README.md",
      "charts/dlh-in-a-box/charts/trino/OVERVIEW.md",
      "charts/dlh-in-a-box/charts/trino/templates/_README.txt",
    ],
    diagrams: ["dataPath", "trino", "hive", "dataRuntime", "trinoPatch", "hiveFlow"],
    slides: [
      cover("Query, Storage, Metadata, And App Runtime", "Session 07 / Data plane and surrounding tools", "global.dataCatalogs is the shared input that becomes Hive resources, Trino catalogs, governance validation, and Ranger policy inputs.", image("icepanel", "dataRuntime"), [
        "Open with the values key. If maintainers understand global.dataCatalogs, much of the data plane becomes easier.",
      ]),
      agenda(["Data path", "Hive subchart", "Trino patch points", "Storage modes", "Consumer apps"], [
        "This session is where runtime architecture connects to the chart's deepest local patch points.",
      ]),
      imageSlide("Data path from values to consumers", image("mermaid", "dataPath"), [
        "Catalogs drive Hive configuration and Trino catalog secrets.",
        "Storage settings wire Hive and Trino to MinIO or external S3.",
        "Governance metadata also feeds validation and access configuration.",
        "Tools consume data through Trino rather than each inventing a separate path.",
      ], "Source: manual Data Path Diagram.", [
        "This is the main data-plane diagram. Walk from left to right: inputs, generated paths, storage backends, consumers.",
      ]),
      imageSlide("Runtime data, analysis, and orchestration", image("icepanel", "dataRuntime"), [
        "Prefect workers run pipelines and can submit Spark jobs.",
        "Trino queries data and registers/transforms tables.",
        "CloudBeaver, JupyterHub, and Superset query through Trino.",
        "DataHub is optional discovery, not the query engine.",
      ], "Source: IcePanel 11-runtime-data-analysis-orchestration.", [
        "Use this to show how operational workloads and human tools both meet at the data plane.",
      ]),
      imageSlide("Hive local subchart", image("icepanel", "hive"), [
        "The Hive subchart is fully repo-owned.",
        "It can render one metastore service and deployment per catalog.",
        "It owns metastore config, database credentials, object storage credentials, and schema initialization.",
      ], "Source: IcePanel 07-hive-metastore-local-subchart.", [
        "Stress ownership: Hive is not just an upstream archive here; it is a first-party subchart.",
      ]),
      imageSlide("Hive flow from catalog input to metastore runtime", image("mermaid", "hiveFlow"), [
        "Catalog iteration is the core pattern.",
        "Storage wiring supports MinIO or S3.",
        "PostgreSQL backs metastore state.",
        "Schema initialization can happen through init containers and hook jobs.",
      ], "Source: Hive subchart README Mermaid.", [
        "This diagram is more implementation-adjacent than the IcePanel view. It is useful when changing the subchart.",
      ]),
      imageSlide("Vendored Trino chart patch points", image("icepanel", "trino"), [
        "Most of the Trino chart is upstream material.",
        "Local patch points generate catalogs, access-control config, secret mounts, and identity wiring.",
        "Coordinator and worker deployments consume the generated settings.",
      ], "Source: IcePanel 06-vendored-trino-chart.", [
        "This is where the ownership boundary matters most. Do not edit nearby upstream files casually.",
      ]),
      imageSlide("Trino patch model", image("mermaid", "trinoPatch"), [
        "Helpers support catalog, access-control, coordinator, and worker rendering.",
        "Generated catalog config comes from global.dataCatalogs and storage settings.",
        "Authorization can be file-based or Ranger-backed.",
      ], "Source: Trino template patch guide Mermaid.", [
        "Link this directly to the patch-point files listed in the Trino guide.",
      ]),
      tableSlide("Storage modes", ["Mode", "What changes", "Maintainer concern"], [
        ["MinIO", "Chart deploys in-cluster S3-compatible storage", "Good local default; not a production secret story"],
        ["External S3", "Hive and Trino point at an existing backend", "Needs real endpoint, credentials, TLS, and governance context"],
        ["Existing Secret", "Generated catalogs may read credentials via lookup", "Offline render and in-cluster upgrade can differ"],
      ], "Source: manual Storage Modes and lookup behavior.", [
        "This table brings sessions four and seven together: storage is both a values decision and an upgrade-time lookup concern.",
      ]),
      bullets("Where DataHub fits", "Optional discovery layer", [
        "DataHub is not Trino and not Hive Metastore.",
        "Its role here is metadata discovery and search.",
        "The chart carries compatibility templates for auth and prerequisite secret/service shape.",
        "Deployments decide whether DataHub is part of their runtime.",
      ], "Source: manual Where DataHub Fits; chart guide.", [
        "This corrects a common architecture overread: DataHub is optional and deployment-controlled in this chart.",
      ]),
      demoSlide("Guided checkpoint: trace a catalog", [
        "Find global.dataCatalogs in charts/dlh-in-a-box/values.yaml",
        "Follow it to Hive templates under charts/dlh-in-a-box/charts/hive/templates",
        "Follow it to Trino catalog rendering under charts/dlh-in-a-box/charts/trino/templates",
        "Check which example overlays enable MinIO or external S3",
      ], [
        "Can the developer name the generated Hive and Trino outputs?",
        "Can they explain how storage mode changes both paths?",
      ], [
        "This is the core implementation handover for the data plane. Encourage maintainers to trace one concrete catalog, not every catalog.",
      ]),
      closeSlide("Session 07 landing", [
        "They can trace global.dataCatalogs through runtime resources.",
        "They understand why Hive is first-party and Trino is vendored with patch points.",
        "They can place DataHub and analysis apps around, not inside, the core query path.",
      ], ["Preview session eight: the final handover is how to maintain, validate, and release the repo safely."]),
    ],
  },
  {
    number: 8,
    slug: "maintainer-workflow-ci-releases-change-ownership",
    title: "Maintainer Workflow, CI, Releases, And Change Ownership",
    promise: "Developers can make changes through the right ownership boundary and prove them with local and CI-equivalent checks.",
    sources: [
      "scripts/README.md",
      ".github/workflows/README.md",
      "docs/umbrella-chart-manual.md",
      "charts/README.md",
      "charts/dlh-in-a-box/third_party/README.md",
    ],
    diagrams: ["validation", "publish", "validationFlow", "workflowFlow", "scriptFlow"],
    slides: [
      cover("Maintainer Workflow, CI, Releases, And Change Ownership", "Session 08 / Keeping the repo healthy", "The maintainer habit is ownership first, local parity second, CI third.", image("icepanel", "validation"), [
        "Open by framing this as the operational survival kit for the team after handover.",
      ]),
      agenda(["Change ownership", "Local validation", "CI parity", "Dependency and release flow"], [
        "The aim is to make future changes boring and reviewable.",
      ]),
      imageSlide("Validation automation", image("icepanel", "validation"), [
        "Dependency refresh, docs checks, lint, render-contract, template, package, and smoke paths cover different risks.",
        "Render-contract checks prove both allowed and disallowed settings.",
        "Smoke install is separate because it needs a disposable cluster.",
      ], "Source: IcePanel 08-chart-validation-automation.", [
        "This is the validation architecture. Session eight turns it into a maintainer routine.",
      ]),
      imageSlide("Local validation and CI flow", image("mermaid", "validationFlow"), [
        "Local scripts are the source of CI parity.",
        "helm-lint workflow refreshes deps, lints, renders, and packages.",
        "Smoke workflow validates the auth-heavy cluster path.",
        "Publish workflow packages and pushes release artifacts.",
      ], "Source: manual Local Validation Flow Mermaid.", [
        "Use this to discourage fixing CI by editing workflow YAML first. Usually debug the local script first.",
      ]),
      imageSlide("Maintainer script flow", image("mermaid", "scriptFlow"), [
        "scripts/verify.sh is the main local validation entrypoint.",
        "docs-check enforces guide coverage, links, and Mermaid validity.",
        "render-contract catches both positive renders and expected failures.",
        "package and smoke-install cover release and cluster integration concerns.",
      ], "Source: scripts/README.md Mermaid.", [
        "Connect this to the recent CI fix pattern: docs-check caught missing guide files before Helm did anything interesting.",
      ]),
      tableSlide("Main local commands", ["Command", "What it proves"], [
        ["./scripts/helm-dependency-update.sh", "Chart.lock and packaged archives match Chart.yaml"],
        ["./scripts/docs-check.sh", "Guide coverage, local links, and Mermaid diagrams validate"],
        ["./scripts/render-contract.sh", "Supported renders succeed and unsafe values fail"],
        ["./scripts/verify.sh", "Main local validation path passes"],
        ["./scripts/template.sh", "Maintained example overlays render"],
        ["./scripts/package.sh", "The chart can be packaged"],
        ["./scripts/smoke-install.sh", "Auth-heavy local path installs and becomes ready"],
      ], "Source: manual Main Local Commands.", [
        "This slide is a checklist, not a command tutorial. Use it to choose the smallest meaningful check.",
      ]),
      imageSlide("GitHub workflow inventory", image("mermaid", "workflowFlow"), [
        "PRs and main pushes run the lint workflow.",
        "Smoke install is manual workflow_dispatch.",
        "Main and version tags can publish packages.",
        "Workflows intentionally call local scripts.",
      ], "Source: .github/workflows/README.md Mermaid.", [
        "Point out the trigger differences. Smoke is manual and cluster-based; lint is the normal PR gate.",
      ]),
      imageSlide("Publish automation", image("icepanel", "publish"), [
        "Package step builds versioned chart archives.",
        "OCI push publishes to GHCR.",
        "Main pushes produce prerelease-style versions.",
        "vX.Y.Z tags publish stable versions only when Chart.yaml matches.",
      ], "Source: IcePanel 09-chart-publish-automation; workflows guide.", [
        "This is the release steward view. It matters less for every contributor, but maintainers must know the tag rule.",
      ]),
      tableSlide("Dependency changes move together", ["When this changes", "Move these together"], [
        ["Chart.yaml dependency version", "Chart.lock and packaged archives"],
        ["Bundled third-party material", "THIRD_PARTY_NOTICES.md and third_party provenance"],
        ["Vendored Trino source", "Patch-point docs and validation fixtures as needed"],
        ["Validation rule", "Examples and render-contract fixtures"],
      ], "Source: chart guide; charts guide; third_party guide.", [
        "This is the antidote to partial dependency updates. Make the audience say the files that move together.",
      ]),
      demoSlide("Guided checkpoint: prepare a safe change", [
        "Identify the ownership boundary first",
        "Choose the narrowest validation command",
        "Run ./scripts/verify.sh before opening or updating a PR",
        "Use smoke-install only for auth-heavy integrated runtime changes",
      ], [
        "Can the developer pick a check for a docs-only change?",
        "Can they pick a check for a values validation change?",
        "Can they describe when a dependency update is incomplete?",
      ], [
        "Use three hypothetical changes: docs-only, governance rule, dependency version. Ask the team to pick files and checks.",
      ]),
      closeSlide("Session 08 landing", [
        "They can make an ownership decision before editing.",
        "They can choose local checks with CI parity.",
        "They know which files move together for dependency and release changes.",
        "They have a complete map for maintaining the repository after handover.",
      ], ["Close the series by pointing back to docs/handover/source-map.md and the folder-local guides as the ongoing reference set."]),
    ],
  },
];

function cover(title, subtitle, thesis, asset, notes) {
  return { type: "cover", title, subtitle, thesis, asset, notes, source: "Handover synthesis from published repository docs." };
}

function agenda(items, notes) {
  return { type: "agenda", title: "Session path", items, notes, source: "Handover session structure." };
}

function bullets(title, kicker, items, source, notes) {
  return { type: "bullets", title, kicker, items, source, notes };
}

function imageSlide(title, asset, items, source, notes) {
  return { type: "image", title, asset, items, source, notes };
}

function tableSlide(title, headers, rows, source, notes) {
  return { type: "table", title, headers, rows, source, notes };
}

function demoSlide(title, commands, checks, notes) {
  return { type: "demo", title, commands, checks, notes, source: "Guided demo/checkpoint for live handover delivery." };
}

function closeSlide(title, items, notes) {
  return { type: "close", title, items, notes, source: "Handover session wrap-up." };
}

function image(kind, key) {
  return { kind, key };
}

function sessionId(session) {
  return `session-${String(session.number).padStart(2, "0")}-${session.slug}`;
}

function relFromHandover(target) {
  return path.relative(HANDOVER_DIR, target).replaceAll(path.sep, "/");
}

function sourceRelFromHandover(source) {
  return path.relative(HANDOVER_DIR, path.join(REPO_DIR, source)).replaceAll(path.sep, "/");
}

function sourceRelFromScript(source) {
  return path.join(REPO_DIR, source);
}

function mermaidPath(key) {
  return path.join(MERMAID_DIR, `${key}.png`);
}

function assetPath(asset) {
  if (!asset) return null;
  if (asset.kind === "icepanel") return path.join(ICEPANEL_LIGHT, icepanel[asset.key]);
  if (asset.kind === "mermaid") return mermaidPath(asset.key);
  if (asset.kind === "icon") return ICON_PATH;
  throw new Error(`Unknown asset ${JSON.stringify(asset)}`);
}

function runCommand(command, args, message) {
  const binary = process.platform === "win32" ? `${command}.cmd` : command;
  const result = spawnSync(binary, args, {
    cwd: DOCS_DIR,
    stdio: "inherit",
    shell: false,
  });
  if (result.status !== 0) {
    throw new Error(`${message} failed with exit code ${result.status ?? "unknown"}.`);
  }
}

async function launchBrowser() {
  try {
    return await chromium.launch({ headless: true });
  } catch (error) {
    const text = String(error?.message || error);
    const needsInstall =
      text.includes("Executable doesn't exist") ||
      text.includes("Please run the following command");
    if (!needsInstall) throw error;
    console.log("Playwright Chromium is not installed yet. Installing it now...");
    runCommand("npx", ["playwright", "install", "chromium"], "Playwright browser install");
    return chromium.launch({ headless: true });
  }
}

async function ensureCleanDirs() {
  await fs.mkdir(HANDOVER_DIR, { recursive: true });
  for (const dir of [PPTX_DIR, PDF_DIR, PREVIEWS_DIR, MERMAID_DIR]) {
    await fs.rm(dir, { recursive: true, force: true });
    await fs.mkdir(dir, { recursive: true });
  }
  await fs.mkdir(ASSETS_DIR, { recursive: true });
}

async function extractMermaidBlocks(source) {
  const content = await fs.readFile(sourceRelFromScript(source), "utf8");
  return [...content.matchAll(/```mermaid\n([\s\S]*?)```/g)].map((match) => match[1].trim());
}

async function renderMermaidAssets(browser) {
  const page = await browser.newPage({ viewport: { width: 2400, height: 1800 }, deviceScaleFactor: 1 });
  await page.addScriptTag({ path: MERMAID_BROWSER_BUNDLE });

  for (const [key, spec] of Object.entries(mermaidSources)) {
    const blocks = await extractMermaidBlocks(spec.source);
    const source = blocks[spec.block];
    if (!source) {
      throw new Error(`Missing Mermaid block ${spec.block} in ${spec.source}`);
    }

    await page.setContent(`<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <style>
    body { margin: 0; padding: 28px; background: #ffffff; font-family: Helvetica, Arial, sans-serif; }
    .wrap { display: inline-block; padding: 18px; border: 1px solid #CBD2D9; border-radius: 14px; background: #ffffff; }
    .mermaid { background: #ffffff; }
    svg { display: block; max-width: none !important; height: auto !important; }
  </style>
</head>
<body>
  <div class="wrap"><pre class="mermaid">${escapeHtml(source)}</pre></div>
</body>
</html>`);
    await page.evaluate(async () => {
      window.mermaid.initialize({
        startOnLoad: false,
        securityLevel: "strict",
        theme: "default",
        flowchart: { useMaxWidth: false, htmlLabels: true },
      });
      await window.mermaid.run({ querySelector: "pre.mermaid" });
    });
    const element = page.locator(".wrap");
    await element.screenshot({ path: mermaidPath(key), omitBackground: false });
  }

  await page.close();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function hex(value) {
  return value.replace(/^#/, "");
}

function withHash(value) {
  return `#${value.replace(/^#/, "")}`;
}

async function imageSize(file) {
  const buffer = await fs.readFile(file);
  if (buffer.slice(0, 8).equals(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]))) {
    return { width: buffer.readUInt32BE(16), height: buffer.readUInt32BE(20) };
  }
  if (buffer[0] === 0xff && buffer[1] === 0xd8) {
    let offset = 2;
    while (offset < buffer.length) {
      if (buffer[offset] !== 0xff) break;
      const marker = buffer[offset + 1];
      const length = buffer.readUInt16BE(offset + 2);
      if ([0xc0, 0xc1, 0xc2, 0xc3].includes(marker)) {
        return { height: buffer.readUInt16BE(offset + 5), width: buffer.readUInt16BE(offset + 7) };
      }
      offset += 2 + length;
    }
  }
  return { width: 1600, height: 900 };
}

async function fitImage(file, box) {
  const { width, height } = await imageSize(file);
  const imageRatio = width / height;
  const boxRatio = box.w / box.h;
  if (boxRatio > imageRatio) {
    const h = box.h;
    const w = h * imageRatio;
    return { x: box.x + (box.w - w) / 2, y: box.y, w, h };
  }
  const w = box.w;
  const h = w / imageRatio;
  return { x: box.x, y: box.y + (box.h - h) / 2, w, h };
}

function addText(slide, text, opts) {
  slide.addText(text, {
    fontFace: "Aptos",
    color: colors.ink,
    margin: 0,
    fit: "shrink",
    breakLine: false,
    ...opts,
  });
}

function addFooter(slide, session, slideNumber, source) {
  addText(slide, `Session ${String(session.number).padStart(2, "0")} / ${session.title}`, {
    x: 0.55,
    y: 7.13,
    w: 7.2,
    h: 0.18,
    fontSize: 6.5,
    color: colors.muted,
  });
  addText(slide, source || "Published repository documentation.", {
    x: 7.7,
    y: 7.13,
    w: 4.7,
    h: 0.18,
    fontSize: 6.5,
    color: colors.muted,
    align: "right",
  });
  addText(slide, String(slideNumber).padStart(2, "0"), {
    x: 12.55,
    y: 7.08,
    w: 0.35,
    h: 0.22,
    fontSize: 7,
    bold: true,
    color: colors.accent,
    align: "right",
  });
}

async function addContainedImage(slide, asset, box, border = true) {
  const file = assetPath(asset);
  const fitted = await fitImage(file, box);
  if (border) {
    slide.addShape("roundRect", {
      x: box.x,
      y: box.y,
      w: box.w,
      h: box.h,
      rectRadius: 0.08,
      fill: { color: colors.white },
      line: { color: colors.border, transparency: 10 },
    });
  }
  slide.addImage({ path: file, ...fitted });
}

async function drawSlide(pptx, slide, spec, session, index) {
  slide.background = { color: colors.white };
  slide.addShape(pptx.ShapeType.rect, {
    x: 0,
    y: 0,
    w: SLIDE_W,
    h: SLIDE_H,
    fill: { color: colors.white },
    line: { color: colors.white },
  });

  if (spec.type === "cover") {
    slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 3.85, h: SLIDE_H, fill: { color: colors.dark }, line: { color: colors.dark } });
    slide.addShape(pptx.ShapeType.rect, { x: 3.85, y: 0, w: 0.12, h: SLIDE_H, fill: { color: colors.accent }, line: { color: colors.accent } });
    slide.addImage({ path: ICON_PATH, x: 0.55, y: 0.45, w: 1.2, h: 0.65 });
    addText(slide, spec.subtitle, { x: 0.55, y: 1.42, w: 2.75, h: 0.36, fontSize: 10, color: colors.surface, bold: true, charSpace: 0.6 });
    addText(slide, spec.title, { x: 0.55, y: 2.0, w: 2.95, h: 2.2, fontSize: 25, color: colors.white, bold: true, breakLine: false });
    addText(slide, "One hour handover deck", { x: 0.55, y: 5.82, w: 2.8, h: 0.3, fontSize: 10, color: colors.surface });
    addText(slide, "40-45 min narrative / 10-15 min checkpoint / 5 min Q&A", { x: 0.55, y: 6.22, w: 2.85, h: 0.42, fontSize: 8.5, color: colors.surface });
    await addContainedImage(slide, spec.asset, { x: 4.35, y: 0.5, w: 8.35, h: 4.95 }, true);
    addText(slide, spec.thesis, { x: 4.55, y: 5.72, w: 7.85, h: 0.8, fontSize: 21, bold: true, color: colors.ink, breakLine: false });
    addFooter(slide, session, index + 1, spec.source);
    return;
  }

  addText(slide, `Session ${String(session.number).padStart(2, "0")}`, { x: 0.55, y: 0.34, w: 1.5, h: 0.22, fontSize: 7.5, bold: true, color: colors.accent, charSpace: 1 });
  addText(slide, spec.title, { x: 0.55, y: 0.62, w: 8.7, h: 0.62, fontSize: 20, bold: true, color: colors.ink, breakLine: false });
  slide.addShape(pptx.ShapeType.line, { x: 0.55, y: 1.34, w: 12.2, h: 0, line: { color: colors.border, width: 1 } });

  if (spec.type === "agenda") {
    addText(slide, "What this hour covers", { x: 0.75, y: 1.72, w: 4.0, h: 0.34, fontSize: 13, color: colors.muted, bold: true });
    spec.items.forEach((item, i) => {
      const y = 2.25 + i * 0.78;
      slide.addShape(pptx.ShapeType.ellipse, { x: 0.78, y: y + 0.02, w: 0.38, h: 0.38, fill: { color: colors.surface }, line: { color: colors.accent } });
      addText(slide, String(i + 1), { x: 0.78, y: y + 0.1, w: 0.38, h: 0.14, fontSize: 6.5, bold: true, color: colors.accent, align: "center" });
      addText(slide, item, { x: 1.35, y, w: 7.9, h: 0.42, fontSize: 19, bold: true, color: colors.ink });
    });
    slide.addShape(pptx.ShapeType.roundRect, { x: 9.45, y: 1.78, w: 2.8, h: 4.35, fill: { color: colors.faint }, line: { color: colors.border } });
    addText(slide, "Session rhythm", { x: 9.75, y: 2.12, w: 2.2, h: 0.3, fontSize: 13, bold: true, color: colors.ink });
    addText(slide, "40-45 min narrative\n10-15 min checkpoint\n5 min Q&A", { x: 9.75, y: 2.72, w: 2.15, h: 1.35, fontSize: 14, color: colors.muted, breakLine: false });
    addText(slide, "Presenter notes carry the script and demo prompts.", { x: 9.75, y: 4.85, w: 2.15, h: 0.55, fontSize: 11, color: colors.accent, bold: true });
  } else if (spec.type === "bullets") {
    addText(slide, spec.kicker, { x: 0.75, y: 1.7, w: 10.6, h: 0.36, fontSize: 12, bold: true, color: colors.accent });
    addText(slide, spec.items.join("\n"), {
      x: 0.9,
      y: 2.25,
      w: 7.8,
      h: 3.45,
      fontSize: 17,
      color: colors.ink,
      breakLine: false,
      bullet: { type: "ul" },
      paraSpaceAfterPt: 8,
    });
    slide.addShape(pptx.ShapeType.rect, { x: 9.35, y: 1.76, w: 0.08, h: 4.4, fill: { color: colors.accent, transparency: 10 }, line: { color: colors.accent } });
    addText(slide, spec.items[0], { x: 9.75, y: 2.05, w: 2.4, h: 2.3, fontSize: 24, bold: true, color: colors.ink, breakLine: false });
  } else if (spec.type === "image") {
    await addContainedImage(slide, spec.asset, { x: 0.7, y: 1.68, w: 7.65, h: 4.95 }, true);
    addText(slide, spec.items.join("\n"), {
      x: 8.75,
      y: 1.92,
      w: 3.35,
      h: 4.35,
      fontSize: 13.5,
      color: colors.ink,
      breakLine: false,
      bullet: { type: "ul" },
      paraSpaceAfterPt: 7,
    });
  } else if (spec.type === "table") {
    const rows = [
      spec.headers.map((h) => ({
        text: h,
        options: { bold: true, color: colors.white, fill: { color: colors.accent }, margin: 0.08 },
      })),
      ...spec.rows.map((row) =>
        row.map((cell) => ({
          text: cell,
          options: { color: colors.ink, fill: { color: colors.white }, margin: 0.08 },
        }))
      ),
    ];
    slide.addTable(rows, {
      x: 0.72,
      y: 1.72,
      w: 11.9,
      h: 4.95,
      border: { type: "solid", color: colors.border, pt: 0.7 },
      fontFace: "Aptos",
      fontSize: spec.rows.length > 5 ? 8.5 : 10,
      valign: "mid",
      fit: "shrink",
      autoFit: true,
    });
  } else if (spec.type === "demo") {
    slide.addShape(pptx.ShapeType.rect, { x: 0.72, y: 1.7, w: 5.85, h: 4.85, fill: { color: colors.dark }, line: { color: colors.dark } });
    addText(slide, "Commands / prompts", { x: 1.05, y: 2.05, w: 4.8, h: 0.28, fontSize: 10, bold: true, color: colors.surface, charSpace: 0.5 });
    addText(slide, spec.commands.join("\n\n"), { x: 1.05, y: 2.55, w: 5.1, h: 3.3, fontFace: "Aptos Mono", fontSize: 10.5, color: colors.white, breakLine: false, fit: "shrink" });
    addText(slide, "Checkpoint questions", { x: 7.05, y: 1.9, w: 4.5, h: 0.34, fontSize: 14, bold: true, color: colors.accent });
    addText(slide, spec.checks.join("\n"), {
      x: 7.3,
      y: 2.55,
      w: 4.65,
      h: 3.25,
      fontSize: 14.5,
      color: colors.ink,
      breakLine: false,
      bullet: { type: "ul" },
      paraSpaceAfterPt: 8,
    });
  } else if (spec.type === "close") {
    addText(slide, "What the inheriting team should now be able to do", { x: 0.75, y: 1.75, w: 8.5, h: 0.36, fontSize: 13, bold: true, color: colors.accent });
    addText(slide, spec.items.join("\n"), {
      x: 0.92,
      y: 2.35,
      w: 8.2,
      h: 3.3,
      fontSize: 18,
      color: colors.ink,
      breakLine: false,
      bullet: { type: "ul" },
      paraSpaceAfterPt: 9,
    });
    slide.addShape(pptx.ShapeType.rect, { x: 9.55, y: 1.9, w: 2.65, h: 3.55, fill: { color: colors.surface }, line: { color: colors.surface } });
    addText(slide, "Leave-behind", { x: 9.88, y: 2.25, w: 2.0, h: 0.28, fontSize: 12, bold: true, color: colors.accent });
    addText(slide, "Use the PPTX notes as a presenter script and source-map.md as the reference trail.", { x: 9.88, y: 2.85, w: 1.95, h: 1.4, fontSize: 13, bold: true, color: colors.ink, breakLine: false });
  }

  addFooter(slide, session, index + 1, spec.source);
}

function notesFor(spec, session, index) {
  const parts = [
    `Session ${String(session.number).padStart(2, "0")}: ${session.title}`,
    `Slide ${String(index + 1).padStart(2, "0")}: ${spec.title}`,
    "",
    "Presenter script:",
    ...(spec.notes || ["Use this slide to advance the session narrative and keep the audience oriented."]),
    "",
    `Source: ${spec.source || "Published repository documentation."}`,
  ];
  if (spec.type === "demo") {
    parts.push("", "Demo/checkpoint cue:", "Treat this as optional live material. If time or tooling is unavailable, discuss the commands and expected reasoning instead.");
  }
  return parts.join("\n");
}

async function buildPptx(session) {
  const pptx = new PptxGenJS();
  pptx.defineLayout({ name: "DLH_WIDE", width: SLIDE_W, height: SLIDE_H });
  pptx.layout = "DLH_WIDE";
  pptx.author = "DLH-in-a-box maintainers";
  pptx.company = "Wellcome Sanger Institute";
  pptx.subject = "DLH-in-a-box repository handover";
  pptx.title = session.title;
  pptx.lang = "en-GB";
  pptx.theme = {
    headFontFace: "Aptos Display",
    bodyFontFace: "Aptos",
    lang: "en-GB",
  };
  pptx.margin = 0;

  for (const [index, spec] of session.slides.entries()) {
    const slide = pptx.addSlide();
    await drawSlide(pptx, slide, spec, session, index);
    slide.addNotes(notesFor(spec, session, index));
  }

  const out = path.join(PPTX_DIR, `${sessionId(session)}.pptx`);
  await pptx.writeFile({ fileName: out });
  return out;
}

function fileUrl(file) {
  return pathToFileURL(file).href;
}

function imageDataUrl(file) {
  const ext = path.extname(file).toLowerCase();
  const mime = ext === ".jpg" || ext === ".jpeg" ? "image/jpeg" : "image/png";
  return `data:${mime};base64,${readFileSync(file).toString("base64")}`;
}

function htmlForAsset(asset) {
  if (!asset) return "";
  return `<img class="asset" src="${imageDataUrl(assetPath(asset))}" alt="" />`;
}

function htmlList(items) {
  return `<ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

function htmlTable(headers, rows) {
  return `<table><thead><tr>${headers.map((h) => `<th>${escapeHtml(h)}</th>`).join("")}</tr></thead><tbody>${rows
    .map((row) => `<tr>${row.map((cell) => `<td>${escapeHtml(cell)}</td>`).join("")}</tr>`)
    .join("")}</tbody></table>`;
}

function slideHtml(spec, session, index) {
  const footer = `<footer><span>Session ${String(session.number).padStart(2, "0")} / ${escapeHtml(session.title)}</span><span>${escapeHtml(spec.source || "")}</span><b>${String(index + 1).padStart(2, "0")}</b></footer>`;
  if (spec.type === "cover") {
    return `<section class="slide cover">
      <div class="cover-band">
        <img class="icon" src="${imageDataUrl(ICON_PATH)}" alt="" />
        <p class="session-label">${escapeHtml(spec.subtitle)}</p>
        <h1>${escapeHtml(spec.title)}</h1>
        <p class="duration">One hour handover deck</p>
        <p class="timing">40-45 min narrative / 10-15 min checkpoint / 5 min Q&A</p>
      </div>
      <main class="cover-main">
        <div class="media">${htmlForAsset(spec.asset)}</div>
        <p class="thesis">${escapeHtml(spec.thesis)}</p>
      </main>
      ${footer}
    </section>`;
  }
  let body = "";
  if (spec.type === "agenda") {
    body = `<main class="agenda-body"><ol>${spec.items.map((item) => `<li><span>${escapeHtml(item)}</span></li>`).join("")}</ol><aside><b>Session rhythm</b><p>40-45 min narrative<br/>10-15 min checkpoint<br/>5 min Q&A</p><strong>Presenter notes carry the script and demo prompts.</strong></aside></main>`;
  } else if (spec.type === "bullets") {
    body = `<main class="bullet-body"><section><p class="kicker">${escapeHtml(spec.kicker)}</p>${htmlList(spec.items)}</section><aside>${escapeHtml(spec.items[0])}</aside></main>`;
  } else if (spec.type === "image") {
    body = `<main class="image-body"><div class="media">${htmlForAsset(spec.asset)}</div><section>${htmlList(spec.items)}</section></main>`;
  } else if (spec.type === "table") {
    body = `<main class="table-body">${htmlTable(spec.headers, spec.rows)}</main>`;
  } else if (spec.type === "demo") {
    body = `<main class="demo-body"><pre>${escapeHtml(spec.commands.join("\n\n"))}</pre><section><h2>Checkpoint questions</h2>${htmlList(spec.checks)}</section></main>`;
  } else if (spec.type === "close") {
    body = `<main class="close-body"><section><p class="kicker">What the inheriting team should now be able to do</p>${htmlList(spec.items)}</section><aside><b>Leave-behind</b><p>Use the PPTX notes as a presenter script and source-map.md as the reference trail.</p></aside></main>`;
  }
  return `<section class="slide ${spec.type}">
    <header><p>Session ${String(session.number).padStart(2, "0")}</p><h1>${escapeHtml(spec.title)}</h1></header>
    ${body}
    ${footer}
  </section>`;
}

function deckHtml(session) {
  return `<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>${escapeHtml(session.title)}</title>
  <style>
    @page { size: 13.333in 7.5in; margin: 0; }
    * { box-sizing: border-box; }
    body { margin: 0; background: #e5e7eb; color: ${withHash(colors.ink)}; font-family: "Aptos", "Helvetica Neue", Arial, sans-serif; }
    .slide { position: relative; width: ${PX_W}px; height: ${PX_H}px; margin: 0 auto; overflow: hidden; background: #fff; page-break-after: always; }
    header { position: absolute; left: 79px; top: 49px; width: 1250px; border-bottom: 1px solid ${withHash(colors.border)}; padding-bottom: 21px; }
    header p { margin: 0 0 10px; color: ${withHash(colors.accent)}; font-weight: 700; font-size: 18px; letter-spacing: 1.2px; }
    header h1 { margin: 0; font-size: 47px; line-height: 1.08; letter-spacing: 0; color: ${withHash(colors.ink)}; }
    footer { position: absolute; left: 79px; right: 79px; bottom: 28px; display: grid; grid-template-columns: 1fr 1.1fr 44px; gap: 18px; align-items: end; color: ${withHash(colors.muted)}; font-size: 15px; }
    footer span:nth-child(2) { text-align: right; }
    footer b { color: ${withHash(colors.accent)}; text-align: right; font-size: 17px; }
    .cover { display: grid; grid-template-columns: 554px 1fr; }
    .cover-band { background: ${withHash(colors.dark)}; border-right: 17px solid ${withHash(colors.accent)}; padding: 66px 78px; color: white; }
    .cover .icon { width: 173px; height: auto; margin-bottom: 108px; }
    .session-label { color: ${withHash(colors.surface)}; font-size: 23px; line-height: 1.2; font-weight: 700; letter-spacing: 1.1px; margin: 0 0 30px; }
    .cover h1 { font-size: 58px; line-height: 1.08; margin: 0; letter-spacing: 0; }
    .duration { margin: 230px 0 0; font-size: 22px; }
    .timing { font-size: 19px; color: ${withHash(colors.surface)}; line-height: 1.35; }
    .cover-main { padding: 72px 88px 80px; }
    .cover-main .media { height: 713px; border: 1px solid ${withHash(colors.border)}; border-radius: 14px; display: flex; align-items: center; justify-content: center; padding: 16px; }
    .asset { max-width: 100%; max-height: 100%; object-fit: contain; display: block; }
    .thesis { font-size: 45px; line-height: 1.12; font-weight: 800; margin: 44px 0 0; color: ${withHash(colors.ink)}; }
    .agenda-body, .bullet-body, .image-body, .table-body, .demo-body, .close-body { position: absolute; left: 102px; right: 102px; top: 245px; bottom: 88px; }
    .agenda-body { display: grid; grid-template-columns: 1fr 405px; gap: 70px; }
    .agenda-body ol { list-style: none; padding: 0; margin: 0; counter-reset: item; }
    .agenda-body li { counter-increment: item; display: grid; grid-template-columns: 58px 1fr; gap: 26px; align-items: center; font-size: 45px; font-weight: 800; margin: 0 0 49px; }
    .agenda-body li::before { content: counter(item); width: 54px; height: 54px; border-radius: 50%; border: 2px solid ${withHash(colors.accent)}; color: ${withHash(colors.accent)}; display: grid; place-items: center; font-size: 23px; }
    .agenda-body aside, .close-body aside { background: ${withHash(colors.faint)}; border: 1px solid ${withHash(colors.border)}; padding: 44px; border-radius: 10px; font-size: 29px; line-height: 1.35; }
    .agenda-body aside b, .close-body aside b { display: block; font-size: 31px; margin-bottom: 38px; color: ${withHash(colors.ink)}; }
    .agenda-body aside strong { color: ${withHash(colors.accent)}; font-size: 25px; }
    .bullet-body { display: grid; grid-template-columns: 1fr 410px; gap: 78px; }
    .kicker { color: ${withHash(colors.accent)}; font-weight: 800; font-size: 28px; margin: 0 0 39px; }
    ul { margin: 0; padding-left: 34px; }
    li { font-size: 36px; line-height: 1.22; margin-bottom: 27px; }
    .bullet-body aside { border-left: 12px solid ${withHash(colors.accent)}; padding: 42px 0 0 44px; font-size: 54px; line-height: 1.08; font-weight: 800; }
    .image-body { display: grid; grid-template-columns: 1110px 1fr; gap: 58px; align-items: start; }
    .image-body .media { height: 713px; border: 1px solid ${withHash(colors.border)}; border-radius: 14px; padding: 16px; display: flex; align-items: center; justify-content: center; }
    .image-body li { font-size: 31px; line-height: 1.25; margin-bottom: 28px; }
    table { width: 100%; border-collapse: collapse; font-size: 25px; line-height: 1.23; }
    th { background: ${withHash(colors.accent)}; color: white; text-align: left; padding: 18px 20px; }
    td { border: 1px solid ${withHash(colors.border)}; padding: 17px 20px; vertical-align: top; }
    tr:nth-child(even) td { background: ${withHash(colors.faint)}; }
    .demo-body { display: grid; grid-template-columns: 840px 1fr; gap: 70px; }
    pre { margin: 0; white-space: pre-wrap; background: ${withHash(colors.dark)}; color: white; font: 25px/1.35 "Aptos Mono", Menlo, Consolas, monospace; padding: 54px; height: 700px; border-radius: 0; }
    .demo-body h2 { margin: 0 0 48px; color: ${withHash(colors.accent)}; font-size: 34px; }
    .demo-body li, .close-body li { font-size: 34px; }
    .close-body { display: grid; grid-template-columns: 1fr 390px; gap: 84px; }
    @media print { body { background: white; } .slide { margin: 0; } }
  </style>
</head>
<body>
  ${session.slides.map((slide, index) => slideHtml(slide, session, index)).join("\n")}
</body>
</html>`;
}

async function buildPdfAndPreviews(browser, session) {
  const page = await browser.newPage({ viewport: { width: PX_W, height: PX_H }, deviceScaleFactor: 1 });
  await page.setContent(deckHtml(session), { waitUntil: "load" });
  const pdfPath = path.join(PDF_DIR, `${sessionId(session)}.pdf`);
  await page.pdf({
    path: pdfPath,
    printBackground: true,
    preferCSSPageSize: true,
    width: "13.333in",
    height: "7.5in",
    margin: { top: "0", right: "0", bottom: "0", left: "0" },
  });

  const slideLocators = await page.locator(".slide").all();
  const previewPaths = [];
  for (const [index, locator] of slideLocators.entries()) {
    await locator.scrollIntoViewIfNeeded();
    const previewPath = path.join(PREVIEWS_DIR, `${sessionId(session)}-slide-${String(index + 1).padStart(2, "0")}.png`);
    await locator.screenshot({ path: previewPath });
    previewPaths.push(previewPath);
  }
  await page.close();

  const contactPath = await buildContactSheet(browser, session, previewPaths);
  return { pdfPath, previewPaths, contactPath };
}

async function buildContactSheet(browser, session, previewPaths) {
  const page = await browser.newPage({ viewport: { width: 1600, height: 1200 }, deviceScaleFactor: 1 });
  const html = `<!doctype html><html><head><meta charset="utf-8" /><style>
    body { margin: 0; padding: 28px; background: #f3f6f8; font-family: Helvetica, Arial, sans-serif; color: #102A43; }
    h1 { margin: 0 0 20px; font-size: 30px; }
    .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; }
    figure { margin: 0; background: white; border: 1px solid #CBD2D9; padding: 8px; }
    img { width: 100%; display: block; }
    figcaption { font-size: 14px; margin-top: 6px; color: #52606D; }
  </style></head><body>
    <h1>${escapeHtml(session.title)} - contact sheet</h1>
    <div class="grid">${previewPaths
      .map((previewPath, i) => `<figure><img src="${imageDataUrl(previewPath)}" /><figcaption>Slide ${String(i + 1).padStart(2, "0")}</figcaption></figure>`)
      .join("")}</div>
  </body></html>`;
  await page.setContent(html, { waitUntil: "load" });
  const contactPath = path.join(PREVIEWS_DIR, `${sessionId(session)}-contact-sheet.png`);
  await page.screenshot({ path: contactPath, fullPage: true });
  await page.close();
  return contactPath;
}

async function writeGuideFiles(results) {
  const fence = "```";
  const guides = [
    {
      file: path.join(HANDOVER_DIR, "README.md"),
      title: "DLH-in-a-box Handover Deck Kit",
      body: [
        "This folder contains generated handover decks for developers inheriting the repository.",
        "",
        `${fence}mermaid`,
        "flowchart TD",
        "  Sources[published repository docs] --> Build[build-handover-decks.mjs]",
        "  Build --> Pptx[pptx decks]",
        "  Build --> Pdf[pdf decks]",
        "  Build --> Previews[preview PNGs]",
        "  Build --> Map[source map]",
        `${fence}`,
        "",
        "## Contents",
        "",
        "| Path | Purpose |",
        "| --- | --- |",
        "| [build-handover-decks.mjs](build-handover-decks.mjs) | Reproducible generator for the decks, PDFs, previews, and source map. |",
        "| [pptx/](pptx/) | Editable PowerPoint handover decks with speaker notes. |",
        "| [pdf/](pdf/) | PDF exports for presentation or handout use. |",
        "| [previews/](previews/) | Full-slide PNG previews and contact sheets used for visual QA. |",
        "| [assets/](assets/) | Rendered diagram assets used by the decks. |",
        "| [source-map.md](source-map.md) | Mapping from sessions to source documentation and diagrams. |",
        "",
        "## Rebuild",
        "",
        "From the repository root:",
        "",
        "```bash",
        "npm --prefix docs run build:handover",
        "```",
      ],
    },
    {
      file: path.join(PPTX_DIR, "README.md"),
      title: "Editable Handover PPTX Decks",
      body: [
        "This folder contains editable PowerPoint versions of the generated handover decks.",
        "",
        `${fence}mermaid`,
        "flowchart TD",
        "  Specs[session specs] --> PptxGen[PptxGenJS export]",
        "  PptxGen --> Decks[editable PPTX files]",
        "  Decks --> Notes[speaker notes]",
        `${fence}`,
        "",
        "Use these files when a maintainer needs to revise slide text, speaker notes, or deck order.",
      ],
    },
    {
      file: path.join(PDF_DIR, "README.md"),
      title: "PDF Handover Deck Exports",
      body: [
        "This folder contains PDF exports of the handover decks for presentation and sharing.",
        "",
        `${fence}mermaid`,
        "flowchart TD",
        "  Specs[session specs] --> Html[HTML slide render]",
        "  Html --> Pdf[PDF exports]",
        "  Pdf --> Delivery[presenter handout]",
        `${fence}`,
        "",
        "The PDFs are regenerated from the same session specifications as the PPTX files.",
      ],
    },
    {
      file: path.join(PREVIEWS_DIR, "README.md"),
      title: "Handover Deck Preview Images",
      body: [
        "This folder contains PNG previews and contact sheets for visual QA.",
        "",
        `${fence}mermaid`,
        "flowchart TD",
        "  Html[HTML slide render] --> Slides[per-slide PNG previews]",
        "  Slides --> Contact[contact sheets]",
        "  Contact --> QA[visual QA pass]",
        `${fence}`,
        "",
        "Use contact sheets for rhythm and individual slide PNGs for checking legibility.",
      ],
    },
    {
      file: path.join(ASSETS_DIR, "README.md"),
      title: "Handover Deck Assets",
      body: [
        "This folder contains generated and reused raster assets for the handover decks.",
        "",
        `${fence}mermaid`,
        "flowchart TD",
        "  Markdown[Mermaid blocks in repo docs] --> Rendered[mermaid PNG assets]",
        "  IcePanel[IcePanel PNG exports] --> Decks[handover decks]",
        "  Rendered --> Decks",
        `${fence}`,
        "",
        "The source IcePanel PNGs remain under [../../architecture/icepanel/exports/](../../architecture/icepanel/exports/).",
      ],
    },
    {
      file: path.join(MERMAID_DIR, "README.md"),
      title: "Rendered Mermaid Assets",
      body: [
        "This folder contains PNG renders of selected Mermaid diagrams from the published documentation surface.",
        "",
        `${fence}mermaid`,
        "flowchart TD",
        "  SourceDocs[source markdown files] --> Mermaid[Mermaid fences]",
        "  Mermaid --> Browser[Playwright render]",
        "  Browser --> PNG[PNG assets for decks]",
        `${fence}`,
        "",
        "Do not edit these PNG files by hand. Re-run the handover deck build instead.",
      ],
    },
  ];

  for (const guide of guides) {
    await fs.writeFile(guide.file, `# ${guide.title}\n\n${guide.body.join("\n")}\n`, "utf8");
  }

  await fs.writeFile(path.join(HANDOVER_DIR, "source-map.md"), sourceMapMarkdown(results), "utf8");
  await fs.writeFile(path.join(HANDOVER_DIR, "qa-report.md"), qaReportMarkdown(results), "utf8");
}

function sourceMapMarkdown(results) {
  const lines = [
    "# Handover Deck Source Map",
    "",
    "This file maps each handover deck to the published repository documentation and diagram assets used to build it.",
    "",
    "The deck kit intentionally excludes `references/**` and `docs/Internal/**`.",
    "",
    "## Decks",
    "",
    "| Session | PPTX | PDF | Contact sheet | Primary sources | Diagram assets |",
    "| --- | --- | --- | --- | --- | --- |",
  ];
  for (const result of results) {
    const session = result.session;
    const sourceLinks = session.sources
      .map((source) => `[${source}](${sourceRelFromHandover(source)})`)
      .join("<br>");
    const diagramLinks = session.diagrams
      .map((diagram) => {
        if (icepanel[diagram]) {
          const target = path.join("..", "architecture", "icepanel", "exports", "dlh-in-a-box", "png-light", icepanel[diagram]);
          return `[IcePanel ${icepanel[diagram]}](${target})`;
        }
        return `[Mermaid ${diagram}](assets/mermaid/${diagram}.png)`;
      })
      .join("<br>");
    lines.push(
      `| ${String(session.number).padStart(2, "0")} ${session.title} | [PPTX](${relFromHandover(result.pptxPath)}) | [PDF](${relFromHandover(result.pdfPath)}) | [PNG](${relFromHandover(result.contactPath)}) | ${sourceLinks} | ${diagramLinks} |`
    );
  }

  lines.push("", "## Build Command", "", "```bash", "npm --prefix docs run build:handover", "```");
  return `${lines.join("\n")}\n`;
}

function qaReportMarkdown(results) {
  const lines = [
    "# Handover Deck QA Report",
    "",
    "Generated by `npm --prefix docs run build:handover`.",
    "",
    "## Automated Checks",
    "",
    "| Check | Result |",
    "| --- | --- |",
    `| Sessions generated | ${results.length} |`,
    `| PPTX files generated | ${results.filter((r) => r.pptxPath).length} |`,
    `| PDF files generated | ${results.filter((r) => r.pdfPath).length} |`,
    `| Preview images generated | ${results.reduce((sum, r) => sum + r.previewPaths.length, 0)} |`,
    `| Contact sheets generated | ${results.filter((r) => r.contactPath).length} |`,
    `| Speaker notes expected | Every slide receives presenter-script notes in PPTX export |`,
    "",
    "## Contact Sheets",
    "",
  ];
  for (const result of results) {
    lines.push(`- [${String(result.session.number).padStart(2, "0")} ${result.session.title}](${relFromHandover(result.contactPath)})`);
  }
  return `${lines.join("\n")}\n`;
}

async function buildAll() {
  await ensureCleanDirs();
  const browser = await launchBrowser();
  const results = [];

  await renderMermaidAssets(browser);

  for (const session of sessions) {
    console.log(`Building ${sessionId(session)}`);
    const pptxPath = await buildPptx(session);
    const { pdfPath, previewPaths, contactPath } = await buildPdfAndPreviews(browser, session);
    results.push({ session, pptxPath, pdfPath, previewPaths, contactPath });
  }

  await browser.close();
  await writeGuideFiles(results);
  console.log(`Built ${results.length} handover sessions in ${relFromHandover(HANDOVER_DIR)}.`);
}

buildAll().catch((error) => {
  console.error(error);
  process.exit(1);
});
