# Etimad Tenders Daily Report Generator

This Python script scrapes daily tenders from the Etimad platform, generates a PDF report, and sends it via email.

## Features

- Scrapes tender data from Etimad website using its async JSON API
- Scrapes separate tender listings from Forsah.sa via its API
- Translates Arabic text to English for all scraped tenders
- Stores all scraped tenders in SQLite for future portal and attendance expansion
- Generates professional PDF reports with company branding
- Sends automated email notifications
- Scheduled execution via cron at 09:00, 11:00, 13:00, and 15:00 Saudi time

## Prerequisites

- Python 3.10+
- Virtual environment (recommended)
- GitHub repository for CI/CD

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/kamy100seo/bt_etmd_tndrs.git bt_tndrs_etimad
   cd bt_tndrs_etimad
   ```

2. Create and activate virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   playwright install
   ```

4. Create `.env` file with your configuration:
   ```env
   TARGET_URL=https://tenders.etimad.sa/Tender/AllTendersForVisitor?PageNumber=1
   TARGET_API_URL=https://tenders.etimad.sa/Tender/AllSupplierTendersForVisitorAsync?PublishDateId=5
   FORSAH_API_BASE_URL=https://forsah-api.910ths.sa/api/v1/opportunities
   DATABASE_PATH=tenders.db
   SMTP_HOST=your-smtp-host
   SMTP_PORT=587
   SMTP_USER=your-email@example.com
   SMTP_PASS=your-password
   EMAIL_FROM=your-email@example.com
   EMAIL_TO=recipient@example.com
   REPORT_TITLE=Etimad Tenders - Daily Report
   COMPANY_NAME=Insight International Contracting Company (IICC)
   WEBSITE_LINK=www.iicc.sa
   LOGO_PATH=images/iicc_final_logo.jpeg
   ```

## Usage

### Manual Execution
```bash
python bt-etmd-tndrs.py
```

### Scheduled Execution
Use the provided shell scripts with cron to run the Etimad report four times per day at Saudi time:

```bash
# Edit crontab
crontab -e

# Add these lines to run at 09:00, 11:00, 13:00, and 15:00
0 9 * * * /path/to/bt_tndrs_etimad/run_etimad_report.sh
0 11 * * * /path/to/bt_tndrs_etimad/run_etimad_report.sh
0 13 * * * /path/to/bt_tndrs_etimad/run_etimad_report.sh
0 15 * * * /path/to/bt_tndrs_etimad/run_etimad_report.sh
```

The new Forsah scraper has its own script and report file, so run it separately with:

```bash
0 9 * * * /path/to/bt_tndrs_etimad/run_forsah_report.sh
0 11 * * * /path/to/bt_tndrs_etimad/run_forsah_report.sh
0 13 * * * /path/to/bt_tndrs_etimad/run_forsah_report.sh
0 15 * * * /path/to/bt_tndrs_etimad/run_forsah_report.sh
```

## Project Structure

```
bt_tndrs_etimad/
├── bt-etmd-tndrs.py          # Main Etimad script
├── forsah_tenders.py         # Separate Forsah scraper and report generator
├── run_etimad_report.sh      # Etimad cron execution script
├── run_forsah_report.sh      # Forsah cron execution script
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables (not in repo)
├── .gitignore                # Git ignore rules
├── images/
│   └── iicc_final_logo.jpeg  # Company logo
└── .github/
    └── workflows/
        └── ci.yml            # GitHub Actions CI/CD
```

## CI/CD

The project includes GitHub Actions workflow for:
- Code linting with flake8
- Python compilation checks
- Basic functionality tests
- Automated builds

## Dependencies

- `playwright`: Web scraping
- `beautifulsoup4`: HTML parsing
- `reportlab`: PDF generation
- `python-dotenv`: Environment management
- `deep-translator`: Arabic to English translation

## License

This project is proprietary. All rights reserved.