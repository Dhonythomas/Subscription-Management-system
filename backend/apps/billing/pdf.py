from io import BytesIO
from decimal import Decimal

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def generate_invoice_pdf(invoice):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4, pageCompression=0)
    width, height = A4
    left = 50
    right = width - 50
    y = height - 50

    def new_page():
        nonlocal y
        pdf.showPage()
        y = height - 50

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(left, y, "INVOICE")
    y -= 28
    pdf.setFont("Helvetica", 10)
    for label, value in (
        ("Invoice", invoice.number),
        ("Customer", invoice.customer.name),
        ("Status", invoice.get_status_display()),
        ("Period", f"{invoice.period_start} to {invoice.period_end}"),
        ("Due", str(invoice.due_date)),
    ):
        pdf.drawString(left, y, f"{label}: {value}")
        y -= 16

    y -= 8
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(left, y, "Description")
    pdf.drawString(360, y, "Qty")
    pdf.drawString(415, y, "Unit")
    pdf.drawRightString(right, y, "Amount")
    y -= 14
    pdf.setFont("Helvetica", 10)

    for line in invoice.lines.all():
        if y < 90:
            new_page()
            pdf.setFont("Helvetica", 10)
        pdf.drawString(left, y, line.description[:55])
        pdf.drawString(360, y, str(line.quantity))
        pdf.drawString(415, y, str(line.unit_price))
        pdf.drawRightString(right, y, str(line.amount))
        y -= 16

    y -= 8
    pdf.line(left, y, right, y)
    y -= 18
    for label, value in (
        ("Subtotal", invoice.subtotal),
        ("Tax", invoice.tax),
        ("Discount", invoice.discount),
        ("Total", invoice.total),
    ):
        pdf.drawRightString(440, y, f"{label}:")
        pdf.drawRightString(right, y, f"{Decimal(value):.2f}")
        y -= 16

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
