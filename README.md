# TLDR Prospect Research Tool

Automated prospect research and brief generation for TLDR's sales team.

## Overview

This tool takes a company name, researches it via web search, matches relevant case studies, and generates a one-page prospect brief ready for outbound outreach.

## Two Ways to Use

### Option 1: Claude.ai Project (Recommended for Testing)

Best for: Individual research, demos, non-technical users

**Setup:**
1. Go to [claude.ai](https://claude.ai) and create a new Project
2. Paste the contents of `PROJECT_INSTRUCTIONS.md` into the Project Instructions
3. Upload these files to the Project:
   - `prompts/about_tldr.md`
   - `prompts/company_research.md`
   - `prompts/case_matching.md`
   - `prompts/synthesis.md`
   - `cases.csv`
   - `accounts.csv`

**Usage:**
Just ask Claude to research a company:
```
Research MongoDB and create a prospect brief
```

Claude will research, match cases, generate a brief, and can export to PDF.

---

### Option 2: Python Script (For Batch Processing)

Best for: Processing multiple companies, automation, integration

**Setup:**
```bash
pip install anthropic python-dotenv fpdf2
```

Create a `.env` file:
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

**Usage:**
```bash
# Research a single company
python3 run.py "MongoDB"

# List all companies in book of business
python3 run.py --list

# Process all companies (caution: rate limits apply)
python3 run.py --all
```

Output files are saved to `/output/` as markdown (and PDF if fpdf2 is installed).

---

## File Structure

```
tldr/
├── README.md                    # This file
├── PROJECT_INSTRUCTIONS.md      # Claude.ai Project setup
├── run.py                       # Python orchestration script
├── .env                         # API key (create this)
├── accounts.csv                 # Book of business
├── cases.csv                    # Case studies database
├── prompts/
│   ├── about_tldr.md           # Company context
│   ├── company_research.md     # Research instructions
│   ├── case_matching.md        # Case matching instructions
│   └── synthesis.md            # Brief generation instructions
└── output/                      # Generated briefs
```

## Customization

### Modifying Prompts
All prompts are in the `/prompts` folder as markdown files. Non-technical users can edit these to:
- Change the brief format
- Adjust research focus areas
- Update case matching criteria
- Modify the outreach email style

### Adding Case Studies
Edit `cases.csv` to add new case studies. Required fields:
- `case_id`, `client_name`, `industry`, `campaign_type`
- `target_audience`, `results_summary`, `key_metrics`, `testimonial`

### Updating Account List
Replace or edit `accounts.csv` with your current book of business.

## Rate Limits

The Python script includes a 15-second delay between API calls to stay under Anthropic's rate limits (30K tokens/minute on lower tiers). Adjust `RATE_LIMIT_DELAY` in `run.py` if needed.

## Output Example

Each brief includes:
- **Header**: Company, Industry, Priority score
- **Opportunity**: Why they're a fit (2 sentences)
- **Recommended Approach**: Newsletters, campaign type, key angle
- **Proof Points**: 2-3 matched case studies with metrics
- **Draft Outreach**: Ready-to-send cold email
- **Key Notes**: Signals, questions, next steps
