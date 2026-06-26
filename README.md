# Prism - Tech Stack Reverse Engineering Tool

Reverse engineer company tech stacks by analyzing employee hiring patterns and backgrounds using CrustData API.

## What It Does

Instead of relying on job postings or surveys, Prism infers a company's tech stack by analyzing their employees:

- If 80% of engineers have Python in their profile, they probably use Python
- Recent hires with Rust experience suggest potential migration or new projects
- Clustering of specific frameworks indicates architectural choices

## Architecture

```
prism/
├── api/          # CrustData API client with caching
├── analyzer/     # Tech stack detection algorithms
├── cli/          # Beautiful terminal interface
├── models/       # Data models (Company, Employee, TechSignal)
└── utils/        # Utilities
```

## Key Features

- **Smart Caching**: Disk-based cache speeds up repeated queries
- **Evidence-Based**: Shows which employees mention each technology
- **Confidence Scoring**: Quantifies certainty (% of employees mentioning tech)
- **Beautiful CLI**: Tree visualizations, progress bars, color coding
- **Optional AI Insights**: Uses AWS Bedrock to turn detected signals into strategic analysis

## Installation

```bash
# Install dependencies
pip install -e .

# Configure API key
cp .env.example .env
# Edit .env and add your CRUSTDATA_API_KEY
```

## Usage

### Interactive Menu (Recommended for Beginners)

```bash
# Launch interactive menu
prism

# Or explicitly
prism interactive
```

The menu provides a guided interface for all features.

### Company Info Command

```bash
# Get company information
prism info stripe.com
```

### Analysis Command

```bash
# Analyze with 10 employees
prism analyze stripe.com

# Larger sample for better accuracy
prism analyze stripe.com --sample 20

# Generate AI insights via AWS Bedrock
prism analyze stripe.com --sample 15 --insights

# Show evidence and verbose output
prism analyze stripe.com --sample 15 --verbose

# Filter low confidence results
prism analyze stripe.com --min-confidence 0.3
```

## How It Works

1. **Company Identification**
   - Uses `/company/identify` endpoint to get company ID and basic info

2. **Employee Sampling**
   - Fetches N employee profiles via `/person/search`
   - Focuses on current employees

3. **Tech Signal Extraction**
   - Scans job titles, headlines, skills for tech keywords
   - Uses regex with word boundaries for accurate matching
   - Tracks evidence (who mentioned what)

4. **Confidence Calculation**
   - Confidence = (employees mentioning tech) / (total employees sampled)
   - Groups by category (languages, databases, frameworks, infrastructure)
   - Sorts by confidence score

5. **Display**
   - Tree structure grouped by category
   - Visual confidence bars
   - Color coding (green=high, yellow=medium, red=low)
   - Optional evidence display

## Tech Stack

- **Python 3.8+**: Core language
- **Typer**: CLI framework
- **Rich**: Terminal formatting
- **Pydantic**: Data validation
- **DiskCache**: SQLite-backed caching
- **Requests**: HTTP client

## Future Enhancements

- Temporal analysis (track tech stack changes over time)
- Comparison mode (compare two companies)
- Export to JSON/CSV
- Job posting analysis integration
- GitHub repository analysis
