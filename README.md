# git-anon

A small containerized tool that creates a **sanitized copy** of a codebase by
detecting and masking sensitive data (IP addresses, bearer tokens, API keys/secrets,
AWS access keys, and email addresses) with placeholder tags. This lets you safely
share a project — for example, with an LLM or a third party — without leaking
credentials or internal infrastructure details.

## How it works

`anonymizer.py` walks a source directory, and for every file:

1. Reads the file content as text.
2. Scans it against a set of regex patterns (see below) and replaces each match
   with a placeholder like `[MASKED_IP_ADDRESS_1]`, `[MASKED_AWS_KEY_2]`, etc.
   The same original value always maps to the same placeholder, so redacted
   files stay internally consistent.
3. Writes the redacted file to a destination directory, mirroring the original
   folder structure.
4. Files that can't be read as text (e.g. binaries) are copied over unchanged.

After the sweep, it writes `anonymization_report.md` to the destination
directory — a lookup table mapping every placeholder back to the original
sensitive value it replaced.

> **⚠️ Never share `anonymization_report.md`.** It contains the real secrets in
> plain text and defeats the purpose of anonymization. Only the sanitized
> project files are safe to share.

### Detected patterns

| Pattern             | Matches                                                        |
| -------------------- | --------------------------------------------------------------- |
| `IP_ADDRESS`         | IPv4 addresses (e.g. `192.168.1.10`)                            |
| `BEARER_TOKEN`       | `Bearer <token>` HTTP authorization headers                     |
| `GENERIC_SECRET`     | `password`/`secret`/`token`/`api_key`/`private_key`/`pwd` assignments (`key: "value"` or `key = "value"`) |
| `AWS_KEY`            | AWS access key IDs (`AKIA...`, `ASIA...`, `ASCA...`)             |
| `EMAIL`              | Email addresses                                                 |

### Ignored paths

The following are skipped entirely and copied as-is/excluded from the scan:
`.git`, `__pycache__`, `.venv`, `node_modules`, `.pytest_cache`, `.DS_Store`,
and `anonymizer` (to avoid recursively scanning its own output).

## Requirements

- [Docker](https://docs.docker.com/get-docker/) (recommended), **or**
- Python 3.11+ if you want to run the script directly without Docker.

## Running with Docker (recommended)

The `Dockerfile` builds an image that mounts your project as a volume, runs the
anonymizer, and writes results to a second mounted volume — nothing needs to
be copied into the image itself.

1. **Build the image:**

   ```bash
   docker build -t git-anon .
   ```

2. **Run it**, mounting the project you want to sanitize to `/app/src` (read-only
   is recommended) and an output folder to `/app/sanitized`:

   ```bash
   docker run --rm \
     -v /absolute/path/to/your-project:/app/src:ro \
     -v /absolute/path/to/output-folder:/app/sanitized \
     git-anon
   ```

3. **Check the output.** Your sanitized project will be in
   `/absolute/path/to/output-folder`, alongside `anonymization_report.md`.

### Example

```bash
docker build -t git-anon .

docker run --rm \
  -v "$HOME/projects/my-app:/app/src:ro" \
  -v "$HOME/projects/my-app-sanitized:/app/sanitized" \
  git-anon
```
If you need to remove company name or project name, run it with the flag -e:

```bash
docker run --rm \
  -e COMPANY_NAMES="your_company_name, your_project_name" \
  -v "$HOME/projects/my-app:/app/src:ro" \
  -v "$HOME/projects/my-app-sanitized:/app/sanitized" \
  git-anon

```

## Running without Docker

The script's source and destination paths are hardcoded to `/app/src` and
`/app/sanitized` (matching the Docker volume mounts). To run it locally:

1. Create the expected directories and place (or symlink) your project inside:

   ```bash
   sudo mkdir -p /app/src /app/sanitized
   cp -r /path/to/your-project/* /app/src/
   ```

2. Run the script:

   ```bash
   python3 anonymizer.py
   ```

Alternatively, edit the `SOURCE` and `DESTINATION` constants at the bottom of
`anonymizer.py` to point at paths of your choosing before running it.

## Project structure

```
.
├── anonymizer.py   # Core anonymization logic (CLI entrypoint)
└── Dockerfile       # Container definition; mounts /app/src and /app/sanitized
```

## Known limitations

- Pattern matching is regex-based and may produce false positives/negatives —
  always review the sanitized output before sharing it.
- `GENERIC_SECRET` only matches `key: "value"` / `key = "value"` style
  assignments with quoted values; other secret formats won't be caught.
- Only IPv4 addresses are detected (no IPv6).
- The destination directory's existing contents are deleted on every run
  before writing fresh output — don't point `/app/sanitized` at anything you
  care about.
