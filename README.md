# pSEO Automation System

A complete Programmatic SEO (pSEO) automation system designed for AI Tool directory websites. This system operationalizes modern SEO methodologies by focusing on **Information Gain**, **Technical SEO**, and **Competitive Intelligence**.

## Features

- 🧠 **LLM-Powered Content Engine**: Generates high-quality, data-grounded pages (Alternatives, Comparisons, Listicles) using GPT-4o.
- 📊 **Structured Data Models**: Headless CMS approach using SQLAlchemy to manage tool features, pricing, and pros/cons.
- 🔍 **SEO Technical Auditor**: Automated checks for H1s, Meta tags, Alt attributes, and JSON-LD schema.
- 🚀 **Google Indexing API**: Instant URL submission to Google Search Console for rapid indexing.
- 🕵️ **Competitor Monitor**: Tracks competitor traffic surges and automatically discovers high-quality backlink opportunities (DR 30-60) via Ahrefs API.
- 🔔 **Feishu/Lark Integration**: Automated alerts for traffic anomalies and backlink opportunities.

## Installation

```bash
# Clone the repository
git clone https://github.com/kydlikebtc/pseo.git
cd pseo

# Install dependencies
pip install -e .

# Copy environment configuration
cp .env.example .env
```

## Configuration

Edit the `.env` file to configure your APIs and database:
- `OPENAI_API_KEY`: For the content generation engine.
- `AHREFS_API_KEY`: For competitor monitoring.
- `GOOGLE_SERVICE_ACCOUNT_FILE`: Path to your Google JSON key for the Indexing API.
- `FEISHU_WEBHOOK_URL`: For team notifications.

## Usage

The system provides a powerful CLI `pseo` for all operations.

### 1. Database & Seeding
```bash
# Initialize database tables
pseo init

# Seed with sample AI tools data
pseo seed
```

### 2. Content Generation
```bash
# Generate an alternative page
pseo generate --page-type alternative --tool-slug midjourney --category-slug ai-image-generator

# Generate a comparison page
pseo generate --page-type comparison --tool-slug chatgpt --tool-b-slug claude

# Batch generate all alternative pages for a category
pseo generate --page-type alternative --category-slug ai-image-generator --batch
```

### 3. SEO Auditing & Indexing
```bash
# Run a technical SEO audit on a URL
pseo audit https://your-site.com/alternatives/midjourney

# Generate sitemap.xml
pseo sitemap --output public/sitemap.xml

# Submit all published pages to Google
pseo submit-index --all-published
```

### 4. Competitor Monitoring
```bash
# Run weekly competitor report and discover backlinks
pseo monitor "futuretools.io, theresanaiforthat.com"

# List high-quality backlink opportunities
pseo list-opportunities --min-dr 30
```

## Testing

The project uses `pytest` with an in-memory SQLite database for testing.

```bash
pytest tests/ -v
```

## Architecture

The system is built on a modular architecture:
- `src.models`: SQLAlchemy ORM models defining the structured data schema.
- `src.engine`: Data collection, LLM prompt engineering, and page assembly.
- `src.checker`: Technical SEO auditing and sitemap/indexing automation.
- `src.monitor`: Competitor traffic tracking and backlink discovery.

## License

MIT License
