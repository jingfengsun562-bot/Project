# CLAUDE.md — Monthly Investment Outlook Agent

## Project Overview

A CLI Python tool that generates a branded monthly investment outlook PDF report.

**Flow:**
1. **Scrape** — pure Python fetches investment bank pages + RSS news (zero AI tokens)
2. **Synthesize** — single Claude API call produces structured JSON with directional views
3. **Report** — ReportLab generates a branded PDF with conviction scores and risk summaries

## Project Structure

```
Project/
├── main.py                     # CLI entry point
├── scraper.py                  # URL fetching, PDF extraction, RSS feeds
├── agent.py                    # Claude synthesis (one API call)
├── report.py                   # ReportLab PDF generation
├── requirements.txt
├── .env                        # Your API key (gitignored)
├── .env.example                # Template
├── Investment_Outlook_url.txt  # Source URLs (10 investment bank pages)
└── output/                     # Generated PDFs (gitignored)
```

## How to Run

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set up your API key
```bash
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Run the agent
```bash
python main.py
```

The report is saved to `output/monthly_outlook_YYYYMM.pdf`.

### Optional flags
```bash
python main.py --output-dir reports/       # custom output folder
python main.py --url-file custom_urls.txt  # custom URL list
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key (set in `.env`) |

## Key Conventions

- **Token efficiency**: All web fetching is pure Python. Claude is called exactly once.
- **Model**: `claude-sonnet-4-6`
- **Source list**: Edit `Investment_Outlook_url.txt` to add or change sources (one URL per line).
- **PDF output**: One file per run, named `monthly_outlook_YYYYMM.pdf`.
- **Error handling**: Failed URL fetches are skipped with a warning — the report still generates from available sources.

## Adding Sources

Add any URL to `Investment_Outlook_url.txt` (one per line). The scraper will:
- Extract paragraph text from the HTML
- Automatically detect and download linked PDFs (e.g. CIO letters)

News RSS feeds (Reuters, CNBC, Bloomberg) are hardcoded in `scraper.py` → `RSS_FEEDS`.
