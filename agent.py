"""
agent.py — Single Claude API call for investment outlook synthesis.

Sends all scraped source text to Claude in one request and returns
structured JSON with directional views and conviction scores.
"""

import json
import os
import re
from datetime import datetime

import anthropic

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are a senior macro strategist at a global investment bank.
You synthesize research from multiple financial institutions and produce
concise, authoritative investment outlooks with clear directional views.
You always respond with valid JSON only — no markdown, no commentary outside the JSON."""

ASSET_CLASSES = [
    "US Equities",
    "Bonds / Fixed Income",
    "FX / Currencies",
    "Commodities",
]

JSON_SCHEMA_EXAMPLE = """
{
  "report_month": "March 2026",
  "asset_classes": [
    {
      "name": "US Equities",
      "macro_summary": "2-3 sentence summary of the current macro environment for this asset class.",
      "direction": "Bullish",
      "conviction": 4,
      "risks": ["Risk description 1", "Risk description 2", "Risk description 3"]
    }
  ],
  "overall_macro_summary": "2-3 sentence overall macro summary covering key themes across all asset classes."
}
"""


def _build_prompt(sources: list[dict]) -> str:
    """Build the user message combining all scraped sources."""
    report_month = datetime.now().strftime("%B %Y")

    lines = [
        f"Today is {datetime.now().strftime('%d %B %Y')}. Generate the monthly investment outlook for {report_month}.",
        "",
        "## Research Sources",
        "",
    ]

    for i, src in enumerate(sources, 1):
        lines.append(f"### Source {i}: {src['source_name']}")
        lines.append(src["content"])
        lines.append("")

    lines += [
        "## Instructions",
        "",
        f"Based on the research above, produce a monthly investment outlook covering these asset classes: {', '.join(ASSET_CLASSES)}.",
        "",
        "For each asset class provide:",
        "  - macro_summary: 2-3 sentences on the current macro environment",
        "  - direction: exactly one of 'Bullish', 'Neutral', or 'Bearish'",
        "  - conviction: integer 1-5 (5 = highest conviction)",
        "  - risks: list of 2-4 key risks to the view",
        "",
        "End with an overall_macro_summary (2-3 sentences) covering cross-asset themes.",
        "",
        "Return ONLY valid JSON matching this schema exactly:",
        JSON_SCHEMA_EXAMPLE,
    ]

    return "\n".join(lines)


def synthesize(sources: list[dict]) -> dict:
    """
    Call Claude once to synthesize all source content into structured views.
    Returns parsed JSON dict.
    """
    if not sources:
        raise ValueError("No source content to synthesize — check scraper output.")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY not set. Add it to your .env file or environment."
        )

    client = anthropic.Anthropic(api_key=api_key)
    prompt = _build_prompt(sources)

    print(f"\n[Agent] Calling Claude ({MODEL}) for synthesis...")
    print(f"  Sources: {len(sources)} | Prompt chars: {len(prompt):,}")

    message = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()

    # Strip accidental markdown code fences if present
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Claude returned invalid JSON: {exc}\n\nRaw output:\n{raw}") from exc

    print(f"  -> Synthesis complete. Report month: {data.get('report_month', 'N/A')}")
    return data

