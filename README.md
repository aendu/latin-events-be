# Latin Events Switzerland

A React app for finding upcoming Latin dance events, with a desktop table, mobile event cards, and filters for region, event type, and start date. Python crawlers collect data from latino.ch, bachata-bern.ch, and dimelocantando.ch. The project folder is named `latin-events-bern`; the GitHub repository is [aendu/latin-events-be](https://github.com/aendu/latin-events-be).


## Tools

- Cursor and Git.
- Node.js 22.12 or newer in the 22.x series, or Node.js 24.x, with npm. The installed Vite 7 release requires Node `^20.19.0 || >=22.12.0`; older Node 20 releases do not work.
- Python 3.11 with pip and venv for updating event data. GitHub Actions also uses Python 3.11. Python is not needed just to run the frontend with existing CSV data.
- GitHub write access to push changes, and a Netlify account with access to the project to deploy it.

The commands below assume macOS/Linux and a terminal opened in the project root (the folder containing `package.json`). No application API keys are currently required.


## Open and run in Cursor

1. Open the existing project using **File → Open Folder**. For a fresh checkout, first run:

   ```bash
   git clone https://github.com/aendu/latin-events-be.git
   cd latin-events-be
   ```

   Open that cloned folder in Cursor. The clone's default folder name differs from the existing `latin-events-bern` folder; both are valid.

2. Open Cursor's integrated terminal with **Terminal → New Terminal**. Check your tools and install the locked JavaScript dependencies:

   ```bash
   node --version
   npm --version
   git --version
   npm ci
   ```

3. Start the development server:

   ```bash
   npm run dev
   ```

   -> run crawlers (## Set up and run the crawlers) for the data

4. Open the URL printed in the terminal, normally `http://localhost:5173`. Use the hostname `localhost` to load the local CSV. Vite updates the browser as you save source files. Stop the server with **Ctrl+C**.

Keep the server running in one terminal and use a second terminal for Git, builds, and crawlers. Cursor's Source Control panel lets you inspect changes and stage individual files; the Git commands below work in the integrated terminal too.

For testing on a phone connected to the same network:

```bash
npm run dev -- --host 0.0.0.0
```

Open Vite's network URL on the phone. With the current hostname-based data selection, a LAN IP uses the GitHub CSV rather than your local CSV.

## Compile and preview the production build

```bash
npm run lint
npm run build
npm run preview
```

`npm run build` compiles the frontend into `dist/`. `npm run preview` serves that build, normally at `http://localhost:4173`; use the actual URL printed in the terminal. Rebuild after changing code to update the preview. Preview is for checking the build locally, not for hosting the live site. See [Vite's deployment guide](https://vite.dev/guide/static-deploy.html).

| Command | Purpose |
| --- | --- |
| `npm ci` | Install dependencies exactly from `package-lock.json` |
| `npm run dev` | Start development with automatic browser updates |
| `npm run lint` | Run ESLint |
| `npm run build` | Generate the deployable `dist/` folder |
| `npm run preview` | Serve the latest production build locally |

There is currently no automated test script. Before publishing, check desktop and narrow mobile layouts, logo navigation, each filter, event links, and loading more events while scrolling. The initial filter is Region Bern, without course-only or shopping-only events, from today onward. The visible date window starts at 14 days and grows on scroll; clear filters or adjust the date when investigating missing events.


## Where event data comes from

The `EVENTS_CSV_URL` constant in `src/App.jsx` selects the source:

| Browser hostname | CSV source |
| --- | --- |
| Exactly `localhost` | `/events.csv`, served from `public/events.csv` during development or from the build during preview |
| Any other hostname, including Netlify, `127.0.0.1`, and LAN IPs | `https://raw.githubusercontent.com/aendu/latin-events-be/refs/heads/main/public/events.csv` |

The live site therefore reads the latest published CSV from GitHub `main` when the page loads. Updating that file on GitHub does not require rebuilding the frontend to make the new data available, though caches may delay visibility. An already-open page needs a reload. Deploy previews also read the `main` branch's data, not their own branch's CSV.

If you fork or rename the repository, change this URL in `src/App.jsx`. It is currently hardcoded, not configured through an environment variable. To serve the CSV packaged with every deployment instead, change the source to `/events.csv` and rebuild; with that approach, data updates require a new deployment.

## Set up and run the crawlers

open file scripts/crawl_all_events.py
-> right click run python file in terminal.

or

Create a virtual environment outside the checkout so it cannot accidentally be committed:

```bash
python3 -m venv ../latin-events-venv
source ../latin-events-venv/bin/activate
python -m pip install -r requirements.txt
python scripts/crawl_all_events.py
```

In later terminal sessions, activate the same environment before running crawler commands. Use `deactivate` to leave it. On Windows PowerShell, the activation command is `..\latin-events-venv\Scripts\Activate.ps1`.

Always run crawlers from the project root: their output paths are relative to the current directory. Network access to the source websites is required. The master script:

1. Runs all three source crawlers with a configured horizon of 90 days.
2. Writes each source's CSV in `data/`.
3. Merges and deduplicates events by date and normalized event name, keeping the first matching entry. Time and city are not part of the duplicate comparison.
4. Sorts the result and writes `data/events.csv`, then copies it to `public/events.csv`.

If a source crawler fails, the master script reuses its existing CSV if available, or skips that source if none exists. A successful run can therefore contain stale or incomplete source data; inspect warnings and event counts. An empty merged result causes failure.

For debugging a single source:

```bash
python scripts/crawl_events_latino_ch.py
python scripts/crawl_events_bachata_bern_ch.py
python scripts/crawl_events_dimelocantando_ch.py
```

Individual scripts only update their source CSV. Run the master script afterward to refresh the combined files; this also reruns all sources.

The shared schema is `date,time,name,flyer,url,host,city,region,source,labels`. Dates use `YYYY-MM-DD`; labels are pipe-separated, for example `party|show`. Keep this schema aligned with `FIELDNAMES` in `scripts/crawl_settings.py` and the parser in `src/App.jsx`.

Crawler settings in `scripts/crawl_settings.py`:

| Setting | Default | How to change |
| --- | --- | --- |
| Date horizon | 90 days | Edit `TARGET_DAY_SPAN` |
| Delay between requests | 1.5 seconds | `CRAWLER_REQUEST_DELAY_SECONDS` environment variable |
| Maximum request attempts | 4 | `CRAWLER_REQUEST_MAX_ATTEMPTS` environment variable |
| Base retry delay | 5 seconds | `CRAWLER_REQUEST_BACKOFF_SECONDS` environment variable |

For example, slow requests down when a source is rate-limiting:

```bash
CRAWLER_REQUEST_DELAY_SECONDS=3 python scripts/crawl_all_events.py
```

## Commit and push to GitHub

Review `git status` before changing branches or pulling. Commit ongoing work or stash it first. Start a new change from an up-to-date `main`:

```bash
git switch main
git pull --ff-only origin main
git switch -c docs/development-guide
```

Choose a descriptive branch name for your actual change. After editing and checking the app, stage only intended files. For a README-only change:

```bash
git diff
git add README.md
git diff --cached
git commit -m "docs: document development and deployment"
git push -u origin docs/development-guide
```

Open the repository on GitHub, create a pull request from that branch into `main`, review it, and merge it. Then return locally to `main` and pull the merged changes. If your repository workflow permits direct pushes, commit on `main` and use `git push origin main` instead.

For a data refresh, stage all five generated CSVs together:

```bash
git add data/events.csv data/events_latino_ch.csv data/events-bachata-bern.csv data/events-dimelocantando.csv public/events.csv
```

If Git requests your author identity, configure it with your own name and email:

```bash
git config user.name "Your Name"
git config user.email "you@example.com"
```

Use GitHub's supported browser/credential-manager login or a personal access token for HTTPS authentication, or configure SSH. Do not put credentials in the repository. Check `git remote -v` if a push targets the wrong repository. If a push is rejected because the remote advanced, fetch and merge the remote branch, resolve any conflicts in Cursor, rerun relevant checks, and push again; do not overwrite remote commits with a force push. The data-update bot can create commits while you work.

`node_modules/` and `dist/` are ignored. Commit `package-lock.json` when intentionally updating JavaScript dependencies. Review untracked files before staging so scratch scripts, virtual environments, and credentials stay out of commits.

## Deploy on Netlify

### Connect GitHub for automatic deployment

1. Push the project to GitHub.
2. In Netlify, choose **Add new project → Import an existing project**, select GitHub, and authorize access to `aendu/latin-events-be`.
3. Set the production branch to `main` and configure:

   | Setting | Value |
   | --- | --- |
   | Base directory | Repository root; leave blank |
   | Build command | `npm run build` |
   | Publish directory | `dist` |
   | Build environment variable | `NODE_VERSION=22` (latest 22.x; at least 22.12) |

4. Deploy and check the build log. Open the provided Netlify URL and verify events, filters, event links, and both layouts.

These are the [Netlify Vite build settings](https://docs.netlify.com/build/frameworks/framework-setup-guides/vite/). Subsequent pushes to the configured production branch trigger builds when continuous deployment is enabled; see [repository deployment setup](https://docs.netlify.com/start/quickstarts/deploy-from-repository/). Keep the local and Netlify Node versions aligned using Netlify's [dependency configuration](https://docs.netlify.com/build/configure-builds/manage-dependencies/).

No `netlify.toml` is currently tracked; configure the settings in Netlify. The frontend build does not run the crawlers. Netlify hosts the static output; the crawlers run locally or in GitHub Actions. The current app has no client-side routes requiring an SPA redirect rule. For a custom domain, use the project's domain management settings and follow the DNS instructions Netlify provides.

### Deploy manually

Run `npm ci`, `npm run lint`, and `npm run build` locally. Upload the generated **`dist/` folder** to Netlify's manual deploy dropzone. For an existing project, use that project's Deploys page to update it rather than creating another project. Repeat the build and upload after changes. See [Netlify's manual deployment instructions](https://docs.netlify.com/deploy/create-deploys/).

Manual uploads do not establish Git-based deployment. On a Git-connected project, a later automatic deployment can replace a manual upload. A manual upload still uses the GitHub CSV described above.

## Automated event updates

`.github/workflows/update-events.yml` runs the **Update events data** workflow at **01:00 and 13:00 UTC** daily: 02:00/14:00 in Swiss winter time and 03:00/15:00 in summer time. It installs Python 3.11 dependencies, runs the master crawler, commits changed CSVs, and pushes them back. It does not commit when data is unchanged.

To refresh manually on GitHub, open **Actions → Update events data → Run workflow** and select `main` for production data. Inspect the run's logs and resulting CSV commit. The workflow declares `contents: write`; repository rules must allow the bot to push. Check Actions settings and branch protection if the push step fails.

## Project map

| Path | Purpose |
| --- | --- |
| `src/App.jsx` | CSV loading, filters, desktop/mobile views, and logo navigation |
| `src/App.css`, `src/index.css` | Responsive layout and shared styles |
| `src/assets/` | Logo and icons |
| `public/events.csv` | Merged CSV shipped with the app and read from GitHub in production |
| `data/` | Source CSVs and merged output; also used as crawler fallback data |
| `scripts/crawl_all_events.py` | Run sources, merge, deduplicate, and publish CSV locally |
| `scripts/crawl_events_*.py` | Source-specific extraction and normalization |
| `scripts/crawl_settings.py` | Schema, horizon, throttling, and retries |
| `scripts/style_detection.py` | Dance-style detection helper |
| `.github/workflows/update-events.yml` | Scheduled and manually triggered data refresh |
| `vite.config.js` | React/Vite configuration and a legacy refresh middleware |
| `package.json`, `package-lock.json` | Frontend commands and dependencies |
| `requirements.txt` | Python dependencies |

## Maintenance and troubleshooting

- **Local CSV changes do not appear:** use `localhost`, rerun the master crawler, and reload. For production preview, rebuild so `dist/events.csv` includes the changes. On other hostnames, check the CSV on GitHub `main`.
- **No events appear:** clear region/type filters and choose an appropriate date. Inspect the browser's Network and Console panels for failed CSV requests. The default filters and initial 14-day window can hide existing entries.
- **A source stops updating:** inspect workflow/crawler warnings and source CSV diffs. Website markup or API changes can require updating that source's parser. Fallback data can hide a failed source behind an otherwise successful workflow.
- **Events disappear during merging:** compare source CSVs with `data/events.csv`. The current duplicate rule can collapse same-name events on the same date even if time or city differs.
- **Build fails:** check the Node version and run `npm ci` again. Keep dev dependencies available during builds because Vite and ESLint are dev dependencies. Inspect Netlify's deploy log for the actual error.
- **Python reports a missing module:** activate the virtual environment and run `python -m pip install -r requirements.txt` with that interpreter.
- **Port already in use:** use the URL Vite prints, or run `npm run dev -- --port 5174`.
- **Refresh API fails:** the development-only `/api/refresh-events` middleware in `vite.config.js` references `scripts/crawl_events.py`, which does not exist. It is not used by the UI and is not deployed on Netlify. Use `python scripts/crawl_all_events.py` or GitHub Actions for refreshes; repair that path before trying to use the endpoint.

For frontend dependency maintenance, inspect `npm outdated`, update selected packages deliberately, commit both package files, and rerun lint/build plus the manual layout checks. For crawler dependency changes, update `requirements.txt`, install into the virtual environment, run the crawlers, and inspect output quality before committing.

To add a data source, create a parser that writes the shared schema, register its crawler and CSV path in `crawl_all_events.py`, and add its output to the workflow's staging list. Verify region/label normalization and duplicate handling with the existing sources.

For a faulty code release, revert the responsible commit through Git/GitHub and redeploy the corrected branch. Reverting frontend code does not restore live event data: the hosted app reads GitHub `main`, so a bad data update must be corrected or reverted there separately.
