# Paved road: what every tool gets when it moves into the Place GitHub organisation

A builder keeps building the way they do now - with Claude Code, Copilot or
Copilot Studio. Moving into the organisation adds the parts a pilot skips,
and none of them need the builder to become a platform engineer.

| File | What it does |
|---|---|
| `tool.yaml` | The tool's register entry: owner, tier, data classes, AI route. CI refuses a pull request that leaves it out of date. |
| `.github/workflows/gate.yml` | On every pull request: the production gate, dependency review and CodeQL. A refusal blocks the merge. |
| `.github/CODEOWNERS` | The owner reviews every change; tier 1 tools also need the platform lead. |
| `.github/dependabot.yml` | Weekly dependency updates, grouped so they arrive as one pull request. |
| `ruleset.json` | Branch protection: pull requests only, one approval that is not the author's, the gate must pass. |
| `infra/main.tf` | Hosting on the shared Azure platform, tagged with owner, tier and cost centre so cost reports by tool. |
| `.gitignore`, `.env.example` | Keys stay out of the repository; the variables are documented without values. |

Secret scanning with push protection is switched on for the whole
organisation, so a key is stopped before it reaches GitHub at all. The gate
still checks, because history imported from a personal account predates it.
