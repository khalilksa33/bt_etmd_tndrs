#!/usr/bin/env python3
import os
import re
import ssl
import json
import sqlite3
import urllib.request
import urllib.parse
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText

from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from dotenv import load_dotenv
from deep_translator import GoogleTranslator

load_dotenv()

FORSAH_API_BASE_URL = os.environ.get(
    "FORSAH_API_BASE_URL",
    "https://forsah-api.910ths.sa/api/v1/opportunities",
)
FORSAH_PER_PAGE = int(os.environ.get("FORSAH_PER_PAGE", "50"))
MAX_ROWS = int(os.environ.get("MAX_ROWS", "50"))
DATABASE_PATH = os.environ.get("DATABASE_PATH", "tenders.db")
SMTP_HOST = None
SMTP_PORT = 587
SMTP_USER = None
SMTP_PASS = None
EMAIL_FROM = None

conn = sqlite3.connect(DATABASE_PATH)
try:
    settings_rows = conn.execute("SELECT * FROM settings").fetchall()
    settings = {row[0]: row[1] for row in settings_rows}
    SMTP_HOST = settings.get("smtp_host") or os.environ.get("SMTP_HOST")
    SMTP_PORT = int(settings.get("smtp_port") or os.environ.get("SMTP_PORT", "587"))
    SMTP_USER = settings.get("smtp_user") or os.environ.get("SMTP_USER")
    SMTP_PASS = settings.get("smtp_pass") or os.environ.get("SMTP_PASS")
    EMAIL_FROM = settings.get("email_from") or os.environ.get("EMAIL_FROM", SMTP_USER)
except sqlite3.OperationalError:
    pass
conn.close()
EMAIL_TO = os.environ.get("EMAIL_TO")
REPORT_TITLE = os.environ.get("FORSAH_REPORT_TITLE", "Forsah Tenders – Daily Report")


FOOTER_TEXT = os.environ.get("FOOTER_TEXT", "")

translator = GoogleTranslator(source='ar', target='en')


def clean_text(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


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


def arabic_digits_to_ascii(text):
    if not text:
        return text
    trans = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
    return text.translate(trans)


def parse_date(value):
    if not value:
        return None
    text = arabic_digits_to_ascii(clean_text(value)).replace('/', '-').replace('.', '-').replace('\u200f', '').strip()
    text = re.sub(r'T', ' ', text)
    text = re.sub(r'Z$', '', text)
    text = re.sub(r'([+-]\d{2}:\d{2})$', '', text)
    patterns = [
        '%Y-%m-%d',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%d-%m-%Y',
        '%d %b %Y',
        '%d %B %Y',
        '%d %b, %Y',
        '%d %B, %Y',
    ]
    for pattern in patterns:
        try:
            return datetime.strptime(text, pattern)
        except Exception:
            continue
    return None


def is_today(value):
    date_obj = parse_date(value)
    return bool(date_obj and date_obj.date() == datetime.now().date())


def sort_rows(rows):
    def sort_key(row):
        pub_date = parse_date(row[6])
        return pub_date or datetime.min
    return sorted(rows, key=sort_key, reverse=True)


def get_localized_text(value):
    if isinstance(value, str):
        return clean_text(value)
    if isinstance(value, dict):
        return clean_text(value.get('en') or value.get('ar') or next(iter(value.values()), ''))
    return ''


def translate_arabic_to_english(text):
    if not text or not any('\u0600' <= char <= '\u06FF' for char in text):
        return text
    try:
        return translator.translate(text)
    except Exception:
        return text


def translate_rows(rows):
    translated_rows = []
    for row in rows:
        translated_rows.append([translate_arabic_to_english(cell) if cell else cell for cell in row])
    return translated_rows


def fetch_rows():
    rows = []
    page = 1
    while len(rows) < MAX_ROWS:
        params = urllib.parse.urlencode({
            'perPage': FORSAH_PER_PAGE,
            'page': page,
        })
        url = f"{FORSAH_API_BASE_URL}?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.load(response)

        result = data.get('result', [])
        if not result:
            break

        for item in result:
            title = get_localized_text(item.get('title')) or 'N/A'
            publisher_type = item.get('publisher', {}).get('publisherType', 'N/A')
            categories = item.get('categories', [])
            category_text = ', '.join(
                get_localized_text(cat.get('name')) for cat in categories if cat
            ) or 'General'
            tender_type = get_localized_text(item.get('type', {}).get('name')) or item.get('type', {}).get('key', 'General')
            activity_text = f"{item.get('daysToGo')} days to close" if item.get('daysToGo') is not None else get_localized_text(item.get('duration'))
            ref_val = item.get('id', '')
            pub_date = item.get('publishDate', '')
            inquiry_deadline = ''
            submit_date = item.get('dueDate', '')
            opening_date = item.get('awardDate') or item.get('closeDate') or ''
            price = get_localized_text(item.get('valueRange', {}).get('name')) or ''

            rows.append([
                title,
                publisher_type,
                category_text,
                tender_type,
                activity_text or 'General',
                ref_val,
                pub_date,
                inquiry_deadline,
                submit_date,
                opening_date,
                price,
            ])
            if len(rows) >= MAX_ROWS:
                break

        page += 1
        pagination = data.get('pagination', {})
        if pagination and page > pagination.get('pageCount', 0):
            break

    return sort_rows(rows)


def draw_page_header(canvas_obj: canvas.Canvas, doc, company_name=None, logo_path=None):
    width, height = doc.pagesize
    top_y = height - 16 * mm
    logo_width = 55 * mm
    logo_height = 24 * mm
    if logo_path and os.path.exists(logo_path):
        try:
            canvas_obj.drawImage(logo_path,
                doc.leftMargin,
                top_y - logo_height,
                width=logo_width,
                height=logo_height,
                preserveAspectRatio=True,
                mask='auto',
            )
        except Exception:
            pass

    if company_name:
        company_text = company_name.strip()
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

    page_num = canvas_obj.getPageNumber()
    canvas_obj.setFont("Helvetica", 10)
    canvas_obj.setFillColor(colors.red)
    canvas_obj.drawRightString(width - doc.rightMargin, height - 12 * mm, f"Page {page_num}")
    canvas_obj.setFillColor(colors.black)


def add_footer(canvas_obj: canvas.Canvas, doc):
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


def build_pdf(rows, path, company_name=None, logo_path=None):
    styles = getSampleStyleSheet()
    story = []
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
    story.append(Paragraph(datetime.now().strftime('Generated on %Y-%m-%d %H:%M'), timestamp_style))
    headers = [
        "#",
        "Tender title",
        "Publisher",
        "Category",
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
    table.setStyle(TableStyle([
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
    ]))
    story.append(table)
    doc = SimpleDocTemplate(
        path,
        pagesize=landscape(A4),
        rightMargin=15,
        leftMargin=15,
        topMargin=35 * mm,
        bottomMargin=24 * mm,
    )
    doc.build(story, onFirstPage=lambda canvas_obj, doc: (draw_page_header(canvas_obj, doc, company_name, logo_path), add_footer(canvas_obj, doc)), onLaterPages=lambda canvas_obj, doc: (draw_page_header(canvas_obj, doc, company_name, logo_path), add_footer(canvas_obj, doc)))


def send_email(pdf_path, email_to):
    if not all([SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, email_to]):
        raise RuntimeError("SMTP or email variables missing. Check .env")
    now = datetime.now().strftime("%Y-%m-%d")
    subject = f"{REPORT_TITLE} – {now}"
    body = "Attached is today’s generated Forsah tenders report in PDF format."
    msg = MIMEMultipart()
    msg["From"] = EMAIL_FROM
    msg["To"] = email_to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    with open(pdf_path, "rb") as f:
        part = MIMEApplication(f.read(), _subtype="pdf")
        part.add_header("Content-Disposition", "attachment", filename=os.path.basename(pdf_path))
        msg.attach(part)
    context = ssl.create_default_context()
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls(context=context)
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)


def main():
    print("🔄 Starting Forsah tenders scraper...")
    rows = fetch_rows()
    if not rows:
        print("❌ No Forsah tenders scraped; aborting.")
        return
    print(f"✅ Scraped {len(rows)} Forsah tenders")
    print("🌐 Translating to English...")
    rows = translate_rows(rows)
    print("✅ Translation complete")
    original_count = len(rows)
    print(f"✅ Keeping {original_count} Forsah tenders published today")
    init_db()
    new_count = save_rows_to_db(rows, "forsah")
    print(f"✅ Saved {new_count} new Forsah tenders to database")
    reported_file = 'reported_forsah_tenders.json'
    with open(reported_file, 'w', encoding='utf-8') as f:
        json.dump({row[5]: row for row in rows}, f, indent=2, ensure_ascii=False)
    today = datetime.now().strftime("%Y%m%d")
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        companies = conn.execute("SELECT * FROM companies").fetchall()
    except sqlite3.OperationalError:
        companies = []
    conn.close()
    
    if companies:
        for company in companies:
            c_name = company["name"]
            c_email = company["email"]
            c_logo = os.path.join("logos", company["logo"]) if company["logo"] else None
            
            company_pdf_name = f"forsah_tenders_report_{today}_{c_name.replace(' ', '_')}.pdf"
            print(f"📄 Building Forsah PDF for {c_name}: {company_pdf_name}")
            build_pdf(rows, company_pdf_name, company_name=c_name, logo_path=c_logo)
            
            print(f"✉️ Sending Forsah email with PDF to {c_email}...")
            try:
                send_email(company_pdf_name, c_email)
            except Exception as e:
                print(f"❌ Failed to send to {c_email}: {e}")
    else:
        print("⚠️ No companies found in the database. Generating default PDF.")
        pdf_name = f"forsah_tenders_report_{today}.pdf"
        build_pdf(rows, pdf_name)



if __name__ == "__main__":
    main()



