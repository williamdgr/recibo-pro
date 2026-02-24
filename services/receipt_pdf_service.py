from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
import os
import re

from database.connection import get_connection, get_db_path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


def _reports_dir():
    db_path = get_db_path()
    app_base_dir = db_path.parent.parent
    reports_path = app_base_dir / "reports"
    reports_path.mkdir(parents=True, exist_ok=True)
    return reports_path


def _format_currency(value):
    amount = Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    integer_part = int(amount)
    decimal_part = int((amount - Decimal(integer_part)) * 100)

    integer_text = f"{integer_part:,}".replace(",", ".")
    return f"R$ {integer_text},{decimal_part:02d}"


def _only_digits(value):
    return re.sub(r"\D", "", str(value or ""))


def _format_document(value):
    digits = _only_digits(value)
    if len(digits) == 11:
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:11]}"
    if len(digits) == 14:
        return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:14]}"
    return value or "-"


def _unit_to_words(number):
    units = [
        "zero",
        "um",
        "dois",
        "três",
        "quatro",
        "cinco",
        "seis",
        "sete",
        "oito",
        "nove",
        "dez",
        "onze",
        "doze",
        "treze",
        "quatorze",
        "quinze",
        "dezesseis",
        "dezessete",
        "dezoito",
        "dezenove",
    ]
    tens = ["", "", "vinte", "trinta", "quarenta", "cinquenta", "sessenta", "setenta", "oitenta", "noventa"]
    hundreds = ["", "cento", "duzentos", "trezentos", "quatrocentos", "quinhentos", "seiscentos", "setecentos", "oitocentos", "novecentos"]

    if number == 0:
        return units[0]
    if number < 20:
        return units[number]
    if number < 100:
        ten = number // 10
        remainder = number % 10
        return tens[ten] if remainder == 0 else f"{tens[ten]} e {_unit_to_words(remainder)}"
    if number == 100:
        return "cem"
    if number < 1000:
        hundred = number // 100
        remainder = number % 100
        return hundreds[hundred] if remainder == 0 else f"{hundreds[hundred]} e {_unit_to_words(remainder)}"
    if number < 1_000_000:
        thousand = number // 1000
        remainder = number % 1000
        thousand_part = "mil" if thousand == 1 else f"{_unit_to_words(thousand)} mil"
        if remainder == 0:
            return thousand_part
        connector = " e " if remainder < 100 else " "
        return f"{thousand_part}{connector}{_unit_to_words(remainder)}"

    million = number // 1_000_000
    remainder = number % 1_000_000
    million_part = "um milhão" if million == 1 else f"{_unit_to_words(million)} milhões"
    if remainder == 0:
        return million_part
    connector = " e " if remainder < 100 else " "
    return f"{million_part}{connector}{_unit_to_words(remainder)}"


def _value_to_words(value):
    amount = Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    reais = int(amount)
    cents = int((amount - Decimal(reais)) * 100)

    reais_text = "real" if reais == 1 else "reais"
    cents_text = "centavo" if cents == 1 else "centavos"

    if cents == 0:
        return f"{_unit_to_words(reais)} {reais_text}"
    return f"{_unit_to_words(reais)} {reais_text} e {_unit_to_words(cents)} {cents_text}"


def _as_decimal(value):
    text_value = str(value or "").strip().replace(".", "").replace(",", ".")
    if not text_value:
        raise ValueError("Informe o valor do recibo.")
    try:
        decimal_value = Decimal(text_value)
    except InvalidOperation as exc:
        raise ValueError("Valor inválido. Use apenas números e até 2 casas decimais.") from exc

    if decimal_value <= 0:
        raise ValueError("O valor do recibo deve ser maior que zero.")

    return decimal_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _normalize_multiline(text):
    return " ".join(str(text or "").strip().split())


def _safe_filename(text):
    sanitized = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(text or "").strip().lower())
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    return sanitized or "cliente"


def _draw_header_logo(pdf, logo_path, x, y, max_width, max_height):
    if not logo_path:
        return False

    try:
        image_reader = ImageReader(logo_path)
        width, height = image_reader.getSize()
    except Exception:
        return False

    if width <= 0 or height <= 0:
        return False

    ratio = min(max_width / width, max_height / height, 1)
    draw_width = width * ratio
    draw_height = height * ratio
    pdf.drawImage(image_reader, x, y - draw_height, width=draw_width, height=draw_height, preserveAspectRatio=True, mask="auto")
    return True


def _next_receipt_id(conn):
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO receipts (
            client_name, cpf_cnpj, description, amount, payment_method,
            pix_key, logo_path, city, issuer_name
        ) VALUES ('', '', '', 0, '', '', '', '', '')
        """
    )
    conn.commit()
    return cursor.lastrowid


def generate_receipt_pdf(data):
    client_name = _normalize_multiline(data.get("client_name"))
    if not client_name:
        raise ValueError("Informe o nome do cliente.")

    document = _normalize_multiline(data.get("cpf_cnpj"))
    description = _normalize_multiline(data.get("description"))
    if not description:
        raise ValueError("Informe a descrição do serviço/produto.")

    amount = _as_decimal(data.get("amount"))
    payment_method = _normalize_multiline(data.get("payment_method")) or "Não informado"
    pix_key = _normalize_multiline(data.get("pix_key"))
    include_logo = bool(data.get("include_logo"))
    logo_path = _normalize_multiline(data.get("logo_path")) if include_logo else ""
    city = _normalize_multiline(data.get("city")) or "Curitiba"
    issuer_name = _normalize_multiline(data.get("issuer_name")) or "Responsável"

    if include_logo and logo_path and not Path(logo_path).exists():
        raise ValueError("Arquivo de logo não encontrado.")

    conn = get_connection()
    try:
        receipt_id = _next_receipt_id(conn)

        report_dir = _reports_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"recibo_{receipt_id:04d}_{_safe_filename(client_name)}_{timestamp}.pdf"
        report_path = report_dir / filename

        pdf = canvas.Canvas(str(report_path), pagesize=A4)
        page_width, page_height = A4

        margin_x = 70
        cursor_y = page_height - 80

        header_drawn = False
        if include_logo and logo_path:
            header_drawn = _draw_header_logo(pdf, logo_path, margin_x, cursor_y + 6, 165, 60)

        if not header_drawn:
            pdf.setStrokeColor(colors.HexColor("#88B6E8"))
            pdf.setLineWidth(1)
            pdf.line(margin_x, cursor_y - 20, margin_x + 112, cursor_y - 20)
            pdf.setFont("Helvetica-Bold", 14)
            pdf.setFillColor(colors.HexColor("#27496D"))
            pdf.drawString(margin_x + 8, cursor_y - 12, "SUA LOGO AQUI")

        pdf.setFillColor(colors.HexColor("#1F3A5A"))
        pdf.setFont("Helvetica-Bold", 30)
        pdf.drawString(margin_x, cursor_y - 85, "RECIBO")

        formatted_date = datetime.now().strftime("%d/%m/%Y")
        pdf.setFont("Helvetica", 15)
        pdf.setFillColor(colors.HexColor("#334155"))
        pdf.drawString(margin_x, cursor_y - 130, f"Nº {receipt_id:03d}")
        pdf.drawRightString(page_width - margin_x, cursor_y - 130, formatted_date)

        pdf.setStrokeColor(colors.HexColor("#CBD5E1"))
        pdf.setLineWidth(0.8)
        pdf.line(margin_x, cursor_y - 142, page_width - margin_x, cursor_y - 142)

        pdf.setFont("Helvetica", 14)
        pdf.drawString(margin_x, cursor_y - 175, "CPF / CNPJ")
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(margin_x + 118, cursor_y - 175, _format_document(document))

        pdf.setStrokeColor(colors.HexColor("#E2E8F0"))
        pdf.line(margin_x, cursor_y - 188, page_width - margin_x, cursor_y - 188)

        amount_text = _format_currency(amount)
        value_words = _value_to_words(amount)
        body_text = (
            f"Recebemos de {client_name}, CPF/CNPJ {_format_document(document)}, a importância de "
            f"<b>{amount_text}</b> ({value_words}), referente à <b>{description}</b>."
        )

        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph

        style = getSampleStyleSheet()["Normal"]
        style.fontName = "Helvetica"
        style.fontSize = 13.5
        style.leading = 20
        style.textColor = colors.HexColor("#334155")

        paragraph = Paragraph(body_text, style)
        available_width = page_width - (margin_x * 2)
        para_width, para_height = paragraph.wrap(available_width, 300)
        paragraph.drawOn(pdf, margin_x, cursor_y - 228 - para_height)

        section_top = cursor_y - 260 - para_height
        pdf.setStrokeColor(colors.HexColor("#E2E8F0"))
        pdf.line(margin_x, section_top, page_width - margin_x, section_top)

        info_y = section_top - 28
        pdf.setFillColor(colors.HexColor("#334155"))
        pdf.setFont("Helvetica", 14)
        pdf.drawString(margin_x, info_y, f"Forma de pagamento: {payment_method}")

        if payment_method.lower() == "pix":
            pix_label_y = info_y - 34
            pdf.drawString(margin_x, pix_label_y, "Chave Pix:")
            pdf.setFont("Helvetica-Bold", 13)
            pdf.drawString(margin_x + 74, pix_label_y, pix_key or "-")

        location_date = datetime.now().strftime("%d de %B de %Y")
        location_date = (
            location_date.replace("January", "janeiro")
            .replace("February", "fevereiro")
            .replace("March", "março")
            .replace("April", "abril")
            .replace("May", "maio")
            .replace("June", "junho")
            .replace("July", "julho")
            .replace("August", "agosto")
            .replace("September", "setembro")
            .replace("October", "outubro")
            .replace("November", "novembro")
            .replace("December", "dezembro")
        )

        footer_y = 120
        pdf.setStrokeColor(colors.HexColor("#E2E8F0"))
        pdf.line(margin_x, footer_y + 28, page_width - margin_x, footer_y + 28)
        pdf.setFillColor(colors.HexColor("#334155"))
        pdf.setFont("Helvetica", 13)
        pdf.drawString(margin_x, footer_y, f"{city}, {location_date}")

        signature_line_width = 165
        signature_line_x = page_width - margin_x - signature_line_width
        pdf.line(signature_line_x, footer_y - 14, signature_line_x + signature_line_width, footer_y - 14)
        pdf.setFont("Helvetica", 12)
        pdf.drawCentredString(signature_line_x + (signature_line_width / 2), footer_y - 34, issuer_name)

        pdf.showPage()
        pdf.save()

        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE receipts
               SET client_name = ?,
                   cpf_cnpj = ?,
                   description = ?,
                   amount = ?,
                   payment_method = ?,
                   pix_key = ?,
                   logo_path = ?,
                   city = ?,
                   issuer_name = ?,
                   pdf_path = ?,
                   created_at = CURRENT_TIMESTAMP
             WHERE id = ?
            """,
            (
                client_name,
                document,
                description,
                float(amount),
                payment_method,
                pix_key,
                logo_path,
                city,
                issuer_name,
                str(report_path),
                receipt_id,
            ),
        )
        conn.commit()

        return str(report_path)
    finally:
        conn.close()


def list_receipts(limit=100):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, client_name, amount, payment_method, created_at, pdf_path
            FROM receipts
            WHERE pdf_path IS NOT NULL AND pdf_path <> ''
            ORDER BY id DESC
            LIMIT ?
            """,
            (int(limit),),
        )
        return cursor.fetchall()
    finally:
        conn.close()


def open_receipt_pdf(path):
    if path and Path(path).exists():
        os.startfile(path)
