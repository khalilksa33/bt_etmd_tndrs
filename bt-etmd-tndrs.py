#!/usr/bin/env python3
import os
import re
import smtplib
import ssl
import asyncio
import json
import sqlite3
import shutil
import calendar
from pypdf import PdfWriter
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from datetime import datetime

from playwright.async_api import async_playwright
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Image,
    Spacer,
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from dotenv import load_dotenv
from deep_translator import GoogleTranslator

# Load environment variables from .env if present
load_dotenv()

# Keywords for relevant services
RELEVANT_KEYWORDS = {
    'accommodation': ['accommodation', 'hotel', 'resort', 'lodging', 'housing', 'apartment', 'villa', 'guesthouse'],
    'catering': ['catering', 'food', 'restaurant', 'meal', 'dining', 'kitchen', 'cook', 'chef'],
    'construction': ['construction', 'building', 'contractor', 'renovation', 'repair', 'maintenance', 'infrastructure', 'civil', 'engineering'],
    'it_software': ['software', 'it', 'development', 'programming', 'ai', 'artificial intelligence', 'e-commerce', 'website', 'app', 'digital', 'tech'],
    'logistics': ['logistics', 'transportation', 'rental', 'machinery', 'heavy duty', 'equipment', 'vehicle', 'truck', 'crane'],
    'recruitment': ['recruitment', 'manpower', 'staff', 'personnel', 'hr', 'human resources', 'employment', 'hiring'],
    'travel_tourism': ['travel', 'tourism', 'hajj', 'umrah', 'pilgrimage', 'tour', 'agency', 'booking'],
    'textile': ['textile', 'fabric', 'manufacturing', 'garment', 'cloth', 'home textile', 'bedding', 'curtain']
}

# Configuration from environment
TARGET_URL = os.environ.get(
    "TARGET_URL",
    "https://tenders.etimad.sa/Tender/AllTendersForVisitor?PageNumber=1",
)
TARGET_API_URL = os.environ.get(
    "TARGET_API_URL",
    "https://tenders.etimad.sa/Tender/AllSupplierTendersForVisitorAsync?PublishDateId=5",
)
API_PAGE_SIZE = int(os.environ.get("ETIMAD_API_PAGE_SIZE", "50"))

SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASS = os.environ.get("SMTP_PASS")
EMAIL_FROM = os.environ.get("EMAIL_FROM", SMTP_USER)
EMAIL_TO = os.environ.get("EMAIL_TO")

REPORT_TITLE = os.environ.get(
    "ETIMAD_REPORT_TITLE",
    os.environ.get("REPORT_TITLE", "Etimad Tenders – Daily Report"),
)
MAX_ROWS = int(os.environ.get("MAX_ROWS", "50"))
DATABASE_PATH = os.environ.get("DATABASE_PATH", "tenders.db")

COMPANY_NAME = os.environ.get("COMPANY_NAME", "")
LOGO_PATH = os.environ.get("LOGO_PATH")
FOOTER_TEXT = os.environ.get(
    "FOOTER_TEXT",
    "",
)


def init_db():
    conn = sqlite3.connect(DATABASE_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tenders (
            tender_id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            reference TEXT NOT NULL,
            title TEXT,
            entity TEXT,
            sub_entity TEXT,
            tender_type TEXT,
            activity TEXT,
            publication TEXT,
            inquiry_deadline TEXT,
            submission_deadline TEXT,
            opening TEXT,
            price TEXT,
            raw_json TEXT,
            scraped_at TEXT,
            UNIQUE(source, reference)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS attendance (
            attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
            tender_id INTEGER,
            attendee_name TEXT,
            status TEXT,
            timestamp TEXT,
            FOREIGN KEY(tender_id) REFERENCES tenders(tender_id)
        )
        """
    )
    conn.commit()
    conn.close()


def save_rows_to_db(rows, source, raw_rows=None):
    conn = sqlite3.connect(DATABASE_PATH)
    cur = conn.cursor()
    now = datetime.now().isoformat()
    before = conn.total_changes
    for idx, row in enumerate(rows):
        reference = row[5] if len(row) > 5 and row[5] else str(hash(str(row)))
        raw_json = None
        if raw_rows and idx < len(raw_rows):
            try:
                raw_json = json.dumps(raw_rows[idx], ensure_ascii=False)
            except Exception:
                raw_json = None
        cur.execute(
            """
            INSERT OR IGNORE INTO tenders (
                source, reference, title, entity, sub_entity,
                tender_type, activity, publication, inquiry_deadline,
                submission_deadline, opening, price, raw_json, scraped_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source,
                reference,
                row[0],
                row[1],
                row[2],
                row[3],
                row[4],
                row[6],
                row[7],
                row[8],
                row[9],
                row[10],
                raw_json,
                now,
            ),
        )
    conn.commit()
    inserted = conn.total_changes - before
    conn.close()
    return inserted


def load_rows_from_db(source):
    conn = sqlite3.connect(DATABASE_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT title, entity, sub_entity, tender_type, activity, reference,
               publication, inquiry_deadline, submission_deadline, opening, price
        FROM tenders
        WHERE source = ?
        ORDER BY scraped_at DESC, tender_id DESC
        """,
        (source,),
    )
    rows = cur.fetchall()
    conn.close()
    return [list(row) for row in rows]


def clean_text(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def extract_activity_days(activity_text):
    """Extract numeric days value from activity text (e.g., '8 days' -> 8)."""
    if not activity_text:
        return 0
    
    # Extract numbers from the activity text
    numbers = re.findall(r'\d+', str(activity_text))
    if numbers:
        try:
            return int(numbers[0])
        except (ValueError, IndexError):
            return 0
    return 0


def is_relevant_tender(row):
    """Check if a tender has activity value >= 8 days."""
    if len(row) > 4 and row[4]:
        activity_days = extract_activity_days(row[4])
        return activity_days >= 8
    return False


def get_text_by_label(card, label_patterns):
    element = card.find(
        string=lambda t: any(pattern in t for pattern in label_patterns)
        if t is not None else False
    )
    if element:
        for candidate in [element.find_next('span'), element.find_next('div'), element.find_next('p'), element.next_sibling, element.parent.next_sibling]:
            if candidate and getattr(candidate, 'text', '').strip():
                return clean_text(candidate.text)

        parent_text = clean_text(element.parent.get_text(separator=' ', strip=True))
        label_text = next((pattern for pattern in label_patterns if pattern in parent_text), '')
        return clean_text(parent_text.replace(label_text, ''))
    return ""


def get_text_from_selectors(card, selectors):
    for selector in selectors:
        node = card.select_one(selector)
        if node and node.text.strip():
            return clean_text(node.text)
    return ""


def arabic_digits_to_ascii(text):
    if not text:
        return text
    trans = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
    return text.translate(trans)


def parse_date(value):
    if not value:
        return None
    text = arabic_digits_to_ascii(clean_text(value)).replace('/', '-').replace('.', '-').replace('\u200f', '').strip()
    patterns = [
        '%Y-%m-%d',
        '%d-%m-%Y',
        '%d %b %Y',
        '%d %B %Y',
        '%d %b, %Y',
        '%d %B, %Y',
        '%Y-%m-%d %H:%M',
        '%d-%m-%Y %H:%M',
    ]
    for pattern in patterns:
        try:
            return datetime.strptime(text, pattern)
        except Exception:
            continue
    return None


def sort_rows(rows):
    def sort_key(row):
        pub_date = parse_date(row[6])
        return pub_date or datetime.min

    return sorted(rows, key=sort_key, reverse=True)


def is_heading_row(values):
    normalized = [clean_text(str(v)).lower() for v in values if v]
    headings = {
        'tender title',
        'procuring entity',
        'sub-entity',
        'sub-entity / dept',
        'type',
        'activity',
        'ref no.',
        'publication',
        'inquiry deadline',
        'submission deadline',
        'opening',
        'doc price',
        'procuring agency',
    }
    return any(value in headings for value in normalized)


translator = GoogleTranslator(source='ar', target='en')


def translate_arabic_to_english(text):
    """Translate Arabic text to English using Google Translate."""
    if not text or not any('\u0600' <= char <= '\u06FF' for char in text):
        return text  # Return as-is if no Arabic characters
    
    try:
        translated = translator.translate(text)
        return translated
    except Exception as e:
        print(f"Translation error for '{text}': {e}")
        return text  # Return original text if translation fails


def translate_rows(rows):
    """Translate all Arabic text in the rows to English."""
    translated_rows = []
    for row in rows:
        translated_row = []
        for cell in row:
            translated_cell = translate_arabic_to_english(cell)
            translated_row.append(translated_cell)
        translated_rows.append(translated_row)
    return translated_rows


def fetch_rows():
    """Fetch Etimad tenders using the site’s async JSON API."""
    if not TARGET_API_URL:
        raise RuntimeError("TARGET_API_URL is not set")

    return asyncio.run(_fetch_rows_async())


async def _fetch_rows_async():
    async with async_playwright() as p:
        request_context = await p.request.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            extra_http_headers={
                "Accept": "*/*",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": TARGET_URL,
            },
        )

        try:
            formatted_rows = []
            page_number = 1

            while len(formatted_rows) < MAX_ROWS:
                timestamp = int(datetime.now().timestamp() * 1000)
                url = f"{TARGET_API_URL}&PageSize={API_PAGE_SIZE}&PageNumber={page_number}&_={timestamp}"
                response = await request_context.get(url, timeout=60000)

                if response.status != 200:
                    raise RuntimeError(f"Etimad API request failed: {response.status}")

                text = await response.text()
                try:
                    payload = json.loads(text)
                except Exception as exc:
                    raise RuntimeError(f"Invalid Etimad API response: {exc}") from exc

                page_data = payload.get("data") or []
                if not page_data:
                    break

                for item in page_data:
                    title_text = clean_text(item.get("tenderName") or item.get("referenceNumber") or "")
                    if not title_text:
                        continue

                    entity_text = clean_text(item.get("agencyName") or "")
                    sub_entity_text = clean_text(item.get("branchName") or "")
                    tender_type = clean_text(item.get("tenderTypeName") or "General")
                    activity_text = clean_text(item.get("tenderActivityName") or "General")
                    ref_val = clean_text(item.get("referenceNumber") or item.get("tenderNumber") or item.get("tenderIdString") or str(item.get("tenderId", "")))
                    pub_date = clean_text(item.get("currentDate") or item.get("currentDateTime") or item.get("createdAt") or "")
                    inquiry_deadline = clean_text(item.get("lastEnqueriesDate") or "")
                    submit_date = clean_text(item.get("submitionDate") or "")
                    opening_date = clean_text(item.get("lastOfferPresentationDate") or item.get("offersOpeningDate") or "")
                    price_value = item.get("buyingCost") if item.get("buyingCost") not in (None, 0) else item.get("invitationCost") if item.get("invitationCost") not in (None, 0) else item.get("condetionalBookletPrice")
                    price = f"{price_value:.2f}" if isinstance(price_value, (int, float)) else clean_text(price_value)

                    formatted_rows.append([
                        title_text,
                        entity_text or 'N/A',
                        sub_entity_text or '',
                        tender_type,
                        activity_text,
                        ref_val,
                        pub_date,
                        inquiry_deadline,
                        submit_date,
                        opening_date,
                        price,
                    ])

                    if len(formatted_rows) >= MAX_ROWS:
                        break

                if len(page_data) < API_PAGE_SIZE:
                    break

                page_number += 1

            return sort_rows(formatted_rows)

        finally:
            await request_context.dispose()



def draw_page_header(canvas_obj: canvas.Canvas, doc):
    """Draw the company logo and name in the page header."""
    width, height = doc.pagesize
    top_y = height - 16 * mm

    logo_width = 55 * mm
    logo_height = 24 * mm
    if LOGO_PATH and os.path.exists(LOGO_PATH):
        try:
            canvas_obj.drawImage(
                LOGO_PATH,
                doc.leftMargin,
                top_y - logo_height,
                width=logo_width,
                height=logo_height,
                preserveAspectRatio=True,
                mask='auto',
            )
        except Exception:
            pass

    if COMPANY_NAME:
        company_text = COMPANY_NAME.strip()
        url_match = re.search(r'(https?://[^\s,]+|www\.[^\s,]+)', company_text)
        if url_match:
            url_text = url_match.group(1)
            href = url_text if url_text.startswith('http') else f'https://{url_text}'
            company_text = company_text.replace(url_text, f'<a href="{href}">{url_text}</a>')

        company_style = ParagraphStyle(
            'company_header',
            parent=getSampleStyleSheet()["Normal"],
            fontName='Helvetica-Bold',
            fontSize=18,
            leading=20,
            textColor=colors.red,
            alignment=1,
        )

        company_para = Paragraph(company_text, company_style)
        company_width, company_height = company_para.wrap(doc.width, 30 * mm)
        company_para.drawOn(canvas_obj, doc.leftMargin, top_y - company_height + 2 * mm)

    # Add page number in header
    page_num = canvas_obj.getPageNumber()
    canvas_obj.setFont("Helvetica", 10)
    canvas_obj.setFillColor(colors.red)
    canvas_obj.drawRightString(width - doc.rightMargin, height - 12 * mm, f"Page {page_num}")
    canvas_obj.setFillColor(colors.black)  # Reset color


def add_footer(canvas_obj: canvas.Canvas, doc):
    """Draw red separator line and footer text on each page."""
    width, _ = doc.pagesize
    line_y = 15 * mm

    if FOOTER_TEXT:
        canvas_obj.setStrokeColor(colors.red)
        canvas_obj.setLineWidth(0.5)
        canvas_obj.line(0, line_y, width, line_y)

        footer_style = getSampleStyleSheet()["Normal"].clone('footer')
        footer_style.alignment = 1
        footer_style.textColor = colors.red
        footer_style.fontName = "Helvetica"
        footer_style.fontSize = 9
        footer_style.leading = 11

        footer_para = Paragraph(FOOTER_TEXT, footer_style)
        footer_width, footer_height = footer_para.wrap(doc.width, 30 * mm)
        footer_para.drawOn(canvas_obj, doc.leftMargin, line_y - footer_height - 4 * mm)


def build_pdf(rows, path):
    styles = getSampleStyleSheet()
    story = []

    # Title and timestamp
    title_style = ParagraphStyle(
        'reportTitle',
        parent=styles['Title'],
        alignment=1,
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        spaceAfter=4 * mm,
    )
    story.append(Paragraph(REPORT_TITLE, title_style))

    timestamp_style = ParagraphStyle(
        'reportTimestamp',
        parent=styles['Normal'],
        alignment=1,
        fontName='Helvetica',
        fontSize=10,
        leading=12,
        textColor=colors.grey,
        spaceAfter=4 * mm,
    )
    story.append(
        Paragraph(
            datetime.now().strftime('Generated on %Y-%m-%d %H:%M'),
            timestamp_style,
        )
    )

    # Table header row (English only)
    headers = [
        "#",
        "Tender title",
        "Procuring entity",
        "Sub-entity / Dept",
        "Type",
        "Activity",
        "Ref no.",
        "Publication",
        "Inquiry deadline",
        "Submission deadline",
        "Opening",
        "Doc price",
    ]

    cell_style = styles["BodyText"]
    cell_style.fontSize = 6
    cell_style.leading = 8
    cell_style.spaceBefore = 0
    cell_style.spaceAfter = 0

    header_style = ParagraphStyle(
        'tableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=1,
    )

    wrapped_headers = []
    for header in headers:
        if header in ('Inquiry deadline', 'Submission deadline'):
            wrapped_headers.append(Paragraph(header.replace(' ', '<br/>', 1), header_style))
        elif ' / ' in header:
            wrapped_headers.append(Paragraph(header.replace(' / ', '<br/>/ '), header_style))
        else:
            wrapped_headers.append(Paragraph(header, header_style))
    data = [wrapped_headers]
    for i, row in enumerate(rows, start=1):
        data.append([Paragraph(str(i), cell_style)] + [Paragraph(str(cell or ""), cell_style) for cell in row])

    col_widths = [8*mm, 75*mm, 33*mm, 26*mm, 20*mm, 18*mm, 25*mm, 18*mm, 18*mm, 18*mm, 18*mm, 12*mm]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.red),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("ALIGN", (0, 1), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 1),
                ("RIGHTPADDING", (0, 0), (-1, -1), 1),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("GRID", (0, 0), (-1, 0), 0.5, colors.white),
                ("GRID", (0, 1), (-1, -1), 0.5, colors.red),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.red),
                ("LINEABOVE", (0, 0), (-1, 0), 0.5, colors.white),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.white),
            ]
        )
    )

    story.append(table)

    doc = SimpleDocTemplate(
        path,
        pagesize=landscape(A4),
        rightMargin=15,
        leftMargin=15,
        topMargin=28 * mm,
        bottomMargin=24 * mm,  # space for footer
    )

    doc.build(
        story,
        onFirstPage=lambda canvas_obj, doc: (draw_page_header(canvas_obj, doc), add_footer(canvas_obj, doc)),
        onLaterPages=lambda canvas_obj, doc: (draw_page_header(canvas_obj, doc), add_footer(canvas_obj, doc)),
    )


def send_email(pdf_path):
    if not all([SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, EMAIL_TO]):
        raise RuntimeError("SMTP or email variables missing. Check .env")

    now = datetime.now().strftime("%Y-%m-%d")
    subject = f"{REPORT_TITLE} – {now}"
    body = "Attached is today’s generated report in PDF format."

    msg = MIMEMultipart()
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with open(pdf_path, "rb") as f:
        part = MIMEApplication(f.read(), _subtype="pdf")
        part.add_header(
            "Content-Disposition",
            "attachment",
            filename=os.path.basename(pdf_path),
        )
        msg.attach(part)

    context = ssl.create_default_context()
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls(context=context)
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)


def main():
    print("🔄 Starting Etimad tenders scraper...")
    rows = fetch_rows()
    if not rows:
        print("❌ No rows scraped; aborting.")
        return

    print(f"✅ Scraped {len(rows)} tenders")

    # Translate Arabic text to English
    print("🌐 Translating to English...")
    rows = translate_rows(rows)
    print("✅ Translation complete")

    # Keep all scraped tenders (no filter applied)
    original_count = len(rows)
    print(f"✅ Keeping all {original_count} scraped tenders")

    init_db()
    new_count = save_rows_to_db(rows, "etimad")
    print(f"✅ Saved {new_count} new tenders to database")

    all_rows = load_rows_from_db("etimad")
    print(f"✅ Loaded {len(all_rows)} distinct tenders from database")

    reported_file = 'reported_tenders.json'
    with open(reported_file, 'w', encoding='utf-8') as f:
        json.dump({row[5]: row for row in all_rows}, f, indent=2, ensure_ascii=False)

    today = datetime.now().strftime("%Y%m%d")
    pdf_name = f"tenders_report_{today}.pdf"
    print(f"📄 Building PDF: {pdf_name}")
    build_pdf(all_rows, pdf_name)

    print(f"✉️ Sending email with PDF...")
    send_email(pdf_name)
    print(f"✅ Done! Report sent to {EMAIL_TO}")

    # Save third report for monthly compilation
    now = datetime.now()
    if now.hour == 15:
        monthly_dir = 'monthly_reports'
        os.makedirs(monthly_dir, exist_ok=True)
        monthly_pdf = os.path.join(monthly_dir, f"tenders_report_{now.strftime('%Y%m%d')}_final.pdf")
        shutil.copy(pdf_name, monthly_pdf)
        print(f"📁 Saved final daily report for monthly: {monthly_pdf}")
        
        # Check if it's month end and compile monthly report
        last_day = calendar.monthrange(now.year, now.month)[1]
        if now.day == last_day:
            print("📊 Compiling monthly report...")
            merger = PdfWriter()
            month_pattern = f"tenders_report_{now.strftime('%Y%m')}*_final.pdf"
            final_pdfs = [f for f in os.listdir(monthly_dir) if f.startswith(f"tenders_report_{now.strftime('%Y%m')}") and f.endswith('_final.pdf')]
            final_pdfs.sort()
            for pdf in final_pdfs:
                merger.append(os.path.join(monthly_dir, pdf))
            monthly_compiled = os.path.join(monthly_dir, f"monthly_tenders_report_{now.strftime('%Y%m')}.pdf")
            merger.write(monthly_compiled)
            merger.close()
            print(f"📄 Monthly report compiled: {monthly_compiled}")
            
            # Send monthly report email
            monthly_subject = f"Monthly Tenders Report – {now.strftime('%B %Y')}"
            monthly_body = f"Attached is the compiled monthly tenders report for {now.strftime('%B %Y')}."
            msg = MIMEMultipart()
            msg["From"] = EMAIL_FROM
            msg["To"] = EMAIL_TO
            msg["Subject"] = monthly_subject
            msg.attach(MIMEText(monthly_body, "plain"))
            with open(monthly_compiled, "rb") as f:
                part = MIMEApplication(f.read(), _subtype="pdf")
                part.add_header("Content-Disposition", "attachment", filename=os.path.basename(monthly_compiled))
                msg.attach(part)
            context = ssl.create_default_context()
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls(context=context)
                server.login(SMTP_USER, SMTP_PASS)
                server.send_message(msg)
            print(f"✉️ Monthly report sent to {EMAIL_TO}")


if __name__ == "__main__":
    main()
