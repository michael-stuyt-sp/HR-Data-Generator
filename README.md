# Employee Generator

Fake employee data generator for identity management systems. Supports both AI-powered company research and fully offline generation using built-in industry presets.

## Modes

### AI Mode (local or cloud)
Uses an LLM to research a real or fictional company and generate industry-appropriate departments, job titles, and office locations. No data leaves your machine when using local providers.

**Local providers:**
- **Ollama** (default) — runs `llama3.2:3b` locally via [Ollama](https://ollama.ai/)
- **Apfel** — uses Apple Intelligence on-device via the `apple-fm-sdk` (macOS 26+ with Xcode 26+ required)

**Cloud providers:**
- **OpenAI** — uses `gpt-4o-mini` by default; requires `OPENAI_API_KEY`
- **Anthropic** — uses `claude-3-5-haiku-latest` by default; requires `ANTHROPIC_API_KEY`
- **Gemini** — uses `gemini-2.0-flash` by default; requires `GEMINI_API_KEY`

Use `-m / --model` to override the default model for any provider.

### Non-AI Mode (`--provider none`)
No LLM required. Uses one of seven built-in industry presets to generate employees entirely offline. Ideal for CI pipelines, air-gapped environments, or quick local testing.

## Features

- 4-level org hierarchy: Executive → VP → Manager → Individual Contributor
- Tier sizes derived automatically from total headcount
- Tier-appropriate job titles (e.g. "Chief Engineer" at L1, "Lead Engineer" at L3)
- Industry-specific departments and job titles
- Multiple office locations with domain-based emails
- CSV and JSON output formats
- Graceful error handling for LLM connectivity and malformed responses

## Requirements

- Python 3.10+
- **Ollama** (default): [Ollama](https://ollama.ai/) running locally with `llama3.2:3b` model
- **Apfel** (optional): macOS 26+ with Apple Intelligence enabled and Xcode 26+ command line tools ([setup guide](https://support.apple.com/en-us/121115))
- **OpenAI** (optional): `OPENAI_API_KEY` environment variable
- **Anthropic** (optional): `ANTHROPIC_API_KEY` environment variable
- **Gemini** (optional): `GEMINI_API_KEY` environment variable
- **None**: no external dependencies — uses built-in industry presets

## Installation

```bash
cd employee_generator
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

```bash
python main.py [company] [-n NUM] [-f FORMAT] [-p PROVIDER] [-i INDUSTRY] [-o FILE]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `company` | Company name to research (required for LLM providers) |
| `-n, --num` | Number of employees to generate (default: 100) |
| `-f, --format` | Output format: `csv` or `json` (default: csv) |
| `-p, --provider` | LLM provider: `ollama` (default), `apfel`, `openai`, `anthropic`, `gemini`, or `none` |
| `-m, --model` | Model name override for the selected provider (see defaults below) |
| `-i, --industry` | Industry preset — required when `--provider none` (see below) |
| `-o, --output` | Output file path (default: stdout) |

### Default Models per Provider

| Provider | Default model |
|----------|--------------|
| `ollama` | `llama3.2:3b` |
| `openai` | `gpt-4o-mini` |
| `anthropic` | `claude-3-5-haiku-latest` |
| `gemini` | `gemini-2.0-flash` |

### Industry Presets (`--provider none`)

| Key | Industry |
|-----|----------|
| `healthcare` | Regional health system |
| `university` | Public research university |
| `government` | Federal government agency |
| `finance` | Finance & insurance |
| `manufacturing` | Industrial manufacturing |
| `pharma` | Pharma & medical device |
| `utility` | Energy & utility |

### Examples

```bash
# --- AI Mode (local) ---

# Generate 100 employees by researching "Tesla" with Ollama (default)
python main.py "Tesla"

# Generate 50 employees using Apple Intelligence (Apfel)
python main.py "Acme Corp" -n 50 -p apfel

# Use a different Ollama model
python main.py "Tesla" -p ollama -m mistral

# --- AI Mode (cloud) ---

# Generate using OpenAI (requires OPENAI_API_KEY)
python main.py "Tesla" -p openai

# Use GPT-4o instead of the default gpt-4o-mini
python main.py "Tesla" -p openai -m gpt-4o

# Generate using Anthropic Claude (requires ANTHROPIC_API_KEY)
python main.py "Acme Corp" -n 50 -p anthropic

# Generate using Google Gemini (requires GEMINI_API_KEY)
python main.py "BioNTech" -n 200 -f json -o employees.json -p gemini

# --- Non-AI Mode ---

# Generate using built-in healthcare preset — no LLM required
python main.py -p none -i healthcare

# Generate 500 government employees in JSON format, save to file
python main.py -p none -i government -n 500 -f json -o employees.json
```

## Output

### Employee Fields

| Field | Description |
|-------|-------------|
| `employee_id` | Unique employee identifier (e.g., EMP12345) |
| `first_name` | Employee first name |
| `last_name` | Employee last name |
| `email` | Work email based on company domain |
| `phone` | Contact phone number |
| `job_title` | Tier-appropriate job title |
| `department` | Company department |
| `office_location` | City, Country |
| `manager_id` | Manager's employee_id (null for top-level exec) |
| `start_date` | Employment start date (YYYY-MM-DD) |
| `level` | Org level: 1=Executive, 2=VP, 3=Manager, 4=IC |
| `is_manager` | True for levels 1–3 |
| `direct_reports` | List of direct report employee_ids |

## Configuration

### Ollama Model

By default, uses `llama3.2:3b`. To change the model, edit the `_ollama_chat` function in `agent.py`:

```python
response = ollama.chat(
    model="your-model-name",  # Change this
    ...
)
```

### Org Hierarchy

The 4-level hierarchy is derived automatically from headcount using these ratios (edit `_tier_counts` in `generator.py` to adjust):

| Level | Role | Default ratio |
|-------|------|---------------|
| 1 | Executive | 1 (fixed) |
| 2 | VP | ~4% of total, min 2 |
| 3 | Manager | ~10% of total, min 1 |
| 4 | Individual Contributor | remainder |

### Custom Presets

To add or modify industry presets, edit `presets.py`. Each preset is a `CompanyProfile` with:
- `name` — organisation name used in output
- `industry` — industry label
- `departments` — list of department names
- `job_titles` — list of base job titles (prefixes are applied per level automatically)
- `office_locations` — list of `{city, country, domain}` dicts

## Error Handling

**Ollama not running:**
```
Error: Could not connect to Ollama. Make sure it is running locally.
```
Start Ollama before running the generator:
```bash
ollama serve
ollama pull llama3.2:3b
```

**Malformed LLM response:**
```
Error: LLM returned invalid JSON for company research.
```

**Missing API key (cloud providers):**
```
Error: OPENAI_API_KEY environment variable is not set.
```
Set the appropriate key before running:
```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GEMINI_API_KEY="AIza..."
```

**Apfel / Apple Intelligence unavailable:**
```
Error: Apple Foundation Models not available: <reason>
```
Ensure Apple Intelligence is enabled in System Settings and you are running macOS 26+ with Xcode 26+ command line tools installed.

> **Note:** Apfel runs entirely on-device with no API keys or network calls. Temperature and sampling parameters are not configurable — Apple's defaults are used.

**Missing --industry flag:**
```
error: --industry is required when --provider none.
```

## Project Structure

```
employee_generator/
├── agent.py          # LLM research agent (Ollama + Apfel backends)
├── company.py        # Company profile data model
├── employee.py       # Employee data model
├── generator.py      # Hierarchy generation logic
├── main.py           # CLI entry point
├── presets.py        # Built-in industry presets
├── README.md         # Documentation
├── requirements.txt  # Python dependencies
└── venv/             # Virtual environment
```
