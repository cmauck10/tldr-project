#!/usr/bin/env python3
"""
TLDR Prospect Research & Brief Generator

Usage:
    python3 run.py "Company Name"     # Research single company
    python3 run.py --all              # Process entire book of business
    python3 run.py --list             # List all companies in accounts.csv
"""

import anthropic
import csv
import json
import os
import sys
import base64
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Initialize client
client = anthropic.Anthropic()

# Rate limiting config
RATE_LIMIT_DELAY = 15  # seconds between API calls to stay under 30k tokens/min

# Paths
BASE_DIR = Path(__file__).parent
ACCOUNTS_FILE = BASE_DIR / "accounts.csv"
CASES_FILE = BASE_DIR / "cases.csv"
PROMPTS_DIR = BASE_DIR / "prompts"
OUTPUT_DIR = BASE_DIR / "output"

# Ensure output directory exists
OUTPUT_DIR.mkdir(exist_ok=True)


def load_prompt(filename: str) -> str:
    """Load a prompt template from the prompts directory."""
    prompt_path = PROMPTS_DIR / filename
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    return prompt_path.read_text()


def load_cases() -> list[dict]:
    """Load case studies from CSV."""
    cases = []
    with open(CASES_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cases.append(row)
    return cases


def load_accounts() -> list[dict]:
    """Load accounts from CSV."""
    accounts = []
    seen = set()
    with open(ACCOUNTS_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Deduplicate by company name
            if row['company_name'] not in seen:
                accounts.append(row)
                seen.add(row['company_name'])
    return accounts


def rate_limit_wait(step_name: str):
    """Wait to respect rate limits."""
    print(f"  ⏳ Rate limit pause ({RATE_LIMIT_DELAY}s)...")
    time.sleep(RATE_LIMIT_DELAY)


def research_company(company_name: str) -> str:
    """Step 1: Research company using web search."""
    about_tldr = load_prompt("about_tldr.md")
    research_prompt = load_prompt("company_research.md")

    # Shorter system prompt to reduce tokens
    system_prompt = f"""You are a sales research assistant for TLDR, a tech newsletter company selling ad placements.

Research the target company concisely. Focus on:
1. What they do and who they sell to
2. Whether they target developers/technical buyers
3. Recent news (funding, launches, hiring)
4. Which TLDR newsletters would fit them

Be concise - bullet points preferred."""

    print(f"  → Researching {company_name}...")

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,  # Reduced from 2000
        system=system_prompt,
        tools=[{
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": 3  # Reduced from 5
        }],
        messages=[{
            "role": "user",
            "content": f"Research {company_name} for TLDR newsletter advertising. Be concise."
        }]
    )

    # Extract text from response
    research_text = ""
    for block in response.content:
        if hasattr(block, 'text'):
            research_text += block.text

    return research_text


def match_cases(company_name: str, research: str) -> str:
    """Step 2: Match company to relevant case studies."""
    cases = load_cases()

    # Compact case format to reduce tokens
    cases_text = "Case studies:\n"
    for case in cases:
        cases_text += f"- {case['client_name']} ({case['industry']}): {case['target_audience']} | {case['key_metrics']}\n"

    system_prompt = f"""Match 2-3 relevant case studies for the prospect. For each match, explain why it's relevant and the key proof point.

{cases_text}"""

    print(f"  → Matching case studies...")

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=800,  # Reduced from 1500
        system=system_prompt,
        messages=[{
            "role": "user",
            "content": f"Match cases for {company_name}:\n{research[:1500]}"  # Truncate research if too long
        }]
    )

    return response.content[0].text


def generate_brief(company_name: str, research: str, case_matches: str) -> str:
    """Step 3: Synthesize everything into a one-pager brief."""
    system_prompt = """Create a concise prospect brief with these sections:
1. **Header**: Company, Industry, Priority (High/Med/Low)
2. **Opportunity** (2 sentences): Why they're a fit for TLDR
3. **Recommended Approach**: Which newsletters, campaign type, key angle
4. **Proof Points**: 2-3 bullets from matched case studies
5. **Draft Outreach**: 3-sentence cold email
6. **Key Notes**: Important signals or questions

Keep it tight - this is a one-pager."""

    print(f"  → Generating brief...")

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1200,  # Reduced from 2500
        system=system_prompt,
        messages=[{
            "role": "user",
            "content": f"""Brief for {company_name}:

Research:
{research[:1500]}

Case matches:
{case_matches[:1000]}"""
        }]
    )

    return response.content[0].text


def create_output(company_name: str, brief_content: str) -> Path:
    """Step 4: Save brief as markdown (and optionally PDF if available)."""
    print(f"  → Saving brief...")

    safe_name = company_name.replace(' ', '_').replace('/', '_').replace(',', '')
    md_path = OUTPUT_DIR / f"{safe_name}_brief.md"

    # Save markdown
    md_path.write_text(f"# {company_name} - TLDR Prospect Brief\n\n{brief_content}")
    print(f"  ✓ Brief saved: {md_path}")

    # Try PDF generation if fpdf2 is available
    try:
        from fpdf import FPDF
        from fpdf.enums import XPos, YPos
        import re

        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_margins(20, 20, 20)

        # Title
        pdf.set_font('Helvetica', 'B', 18)
        pdf.cell(0, 10, company_name, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font('Helvetica', 'I', 11)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 6, 'TLDR Prospect Brief', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(4)

        # Body content
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(0, 0, 0)

        # Clean up markdown and process
        def clean_text(text):
            # Remove markdown bold markers and clean up
            text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
            # Replace special characters that cause issues
            text = text.replace('•', '-')
            text = text.replace('"', '"').replace('"', '"')
            text = text.replace(''', "'").replace(''', "'")
            text = text.replace('–', '-').replace('—', '-')
            # Handle encoding issues
            text = text.encode('latin-1', errors='replace').decode('latin-1')
            return text

        for line in brief_content.split('\n'):
            line = line.strip()
            if not line:
                pdf.ln(2)
            elif line.startswith('# ') and 'PROSPECT BRIEF' in line:
                # Skip duplicate title
                continue
            elif line.startswith('## '):
                pdf.ln(3)
                pdf.set_font('Helvetica', 'B', 11)
                pdf.set_text_color(0, 102, 204)
                pdf.cell(0, 7, clean_text(line[3:]), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.set_font('Helvetica', '', 10)
                pdf.set_text_color(0, 0, 0)
            elif line.startswith('- ') or line.startswith('* ') or line.startswith('• '):
                bullet_text = clean_text(line[2:])
                pdf.set_x(25)
                pdf.multi_cell(0, 5, '- ' + bullet_text)
            elif '|' in line and line.startswith('**'):
                # Header line like "**Company:** X | **Industry:** Y"
                pdf.set_font('Helvetica', 'B', 10)
                pdf.multi_cell(0, 6, clean_text(line))
                pdf.set_font('Helvetica', '', 10)
            else:
                pdf.multi_cell(0, 5, clean_text(line))

        pdf_path = OUTPUT_DIR / f"{safe_name}_brief.pdf"
        pdf.output(pdf_path)
        print(f"  ✓ PDF saved: {pdf_path}")
        return pdf_path

    except ImportError:
        print(f"  i PDF generation skipped (install fpdf2 for PDF output)")
        return md_path
    except Exception as e:
        print(f"  ! PDF generation failed: {e}")
        return md_path


def process_company(company_name: str) -> Path:
    """Run the full pipeline for a single company."""
    print(f"\n{'='*60}")
    print(f"Processing: {company_name}")
    print('='*60)

    # Step 1: Research
    research = research_company(company_name)
    rate_limit_wait("research")

    # Step 2: Match cases
    case_matches = match_cases(company_name, research)
    rate_limit_wait("case_matching")

    # Step 3: Generate brief
    brief = generate_brief(company_name, research, case_matches)
    rate_limit_wait("brief")

    # Step 4: Save output
    output_path = create_output(company_name, brief)

    print(f"\n✓ Complete: {output_path}")
    return output_path


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    arg = sys.argv[1]

    if arg == "--list":
        accounts = load_accounts()
        print(f"\nAccounts in book of business ({len(accounts)} companies):\n")
        for i, account in enumerate(accounts, 1):
            print(f"  {i:3}. {account['company_name']}")
        sys.exit(0)

    elif arg == "--all":
        accounts = load_accounts()
        print(f"\nProcessing all {len(accounts)} companies...")

        results = []
        for account in accounts:
            try:
                path = process_company(account['company_name'])
                results.append((account['company_name'], str(path), "success"))
            except Exception as e:
                print(f"  ✗ Error: {e}")
                results.append((account['company_name'], None, str(e)))

        # Summary
        print(f"\n{'='*60}")
        print("SUMMARY")
        print('='*60)
        success = sum(1 for r in results if r[2] == "success")
        print(f"Processed: {success}/{len(results)} companies")

    else:
        # Single company mode
        company_name = arg
        process_company(company_name)


if __name__ == "__main__":
    main()
