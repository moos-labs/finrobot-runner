# finrobot-runner

Runs **[FinRobot](https://github.com/AI4Finance-Foundation/FinRobot)**
(AI4Finance-Foundation) via GitHub Actions. Part of the moos-labs
stock-tools fleet: one public repo per tool, commands in a repository
variable, manual dispatch, results as artifacts. Scripts are generic —
nothing is EGX- or market-hardcoded.

**This repo is smoke-only as set up.** No real analysis run is attempted
and no API keys are provisioned here (keys are provisioned separately).

## The pattern

1. Edit the repo **Actions variable `COMMANDS`** (Settings → Secrets and
   variables → Actions → Variables, or the variables API).
2. Dispatch the workflow: Actions → *Run analysis* → *Run workflow*
   (or `POST /repos/moos-labs/finrobot-runner/actions/workflows/run.yml/dispatches`).
3. Download the **`results`** artifact from the finished run.

The workflow (`.github/workflows/run.yml`) is **manual only**
(`workflow_dispatch`). It:

- sets up Python **3.11**,
- installs FinRobot per its upstream README: it clones
  `AI4Finance-Foundation/FinRobot` into `finrobot_src/` and runs
  `pip install -e ./finrobot_src` (upstream `setup.py` at the repo root
  maps the `finrobot` package to `finrobot_autogen/finrobot` and reads
  `finrobot_autogen/requirements.txt`; installing from inside
  `finrobot_autogen/` does not work),
- executes whatever is in the **COMMANDS** variable in the step named
  "Run commands" (`run: ${{ vars.COMMANDS }}`),
- uploads `results/` as the **results** artifact (`if: always()`).

Current `COMMANDS`:

```
mkdir -p results
set -o pipefail; python scripts/smoke.py 2>&1 | tee results/run.log
```

(`set -o pipefail;` matters: without it, piping through `tee` would mask
a script failure and the run would wrongly show as success.)

## Smoke test

`scripts/smoke.py` imports the `finrobot` package and the
`finrobot.data_source` / `finrobot.functional` submodules (the top-level
`finrobot/__init__.py` is empty upstream, so the submodules are the real
evidence), prints what imported and the installed distribution version
if exposed, and writes:

- `results/smoke.json` — `{"ok": ..., "imports": [...], ...}`
- `results/smoke.md` — the same evidence in readable form
- `results/run.log` — full run log (via the `tee` in `COMMANDS`)

No LLM calls are made and no API keys are used by the smoke test.

## KEY REQUIREMENTS (for real runs — not needed for the smoke test)

Per FinRobot's own README and its sample config files, a real run needs:

- **LLM key — `OAI_CONFIG_LIST`** (copy of
  `finrobot_autogen/OAI_CONFIG_LIST_sample`, placed in
  `finrobot_autogen/`): an **OpenAI API key** (`api_key` for the listed
  models, e.g. `gpt-4-0125-preview` / `gpt-4-1106-vision-preview`).
  Azure OpenAI is the documented alternative in the same file
  (deployment name + Azure API key + `base_url`, `api_type: azure`).
- **Financial-data keys — `config_api_keys`** (copy of
  `finrobot_autogen/config_api_keys_sample`, also in
  `finrobot_autogen/`):
  - `FINNHUB_API_KEY` — Finnhub
  - `FMP_API_KEY` — Financial Modeling Prep
  - `SEC_API_KEY` — SEC API (sec-api.io)
  - `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` — Reddit
  - `TWITTER_BEARER_TOKEN` — Twitter/X
- The newer generations in the same upstream repo ask for the same
  families of keys in their own config: V1 (`finrobot_equity/`) uses a
  `config.ini` with `fmp_api_key` and `openai_api_key` (optional
  `adanos_api_key`); V2 (`finrobot_desktop/`) uses data providers
  including FMP, Finnhub and SEC EDGAR.

Keys are provisioned separately — none are stored in this repo.

## Honest notes on the tool

- Upstream FinRobot is now three generations sharing one repo: V0
  (AutoGen, the `finrobot` PyPI package this runner installs), V1
  (`finrobot_equity/`, OpenAI Agents SDK web app) and V2
  (`finrobot_desktop/`, PydanticAI desktop app). This runner covers the
  V0 importable package.
- FinRobot's dependency tree is heavy (AutoGen, LangChain, marker-pdf,
  backtrader, tushare, … — see upstream `finrobot_autogen/requirements.txt`),
  so the install step is the long / fragile part of the run.
