from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCUMENTS_DIR = PROJECT_ROOT / "data" / "documents"
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

styles = getSampleStyleSheet()


def create_pdf(filename, title, sections):
    output_path = DOCUMENTS_DIR / filename

    document = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=55,
        rightMargin=55,
        topMargin=55,
        bottomMargin=55,
    )

    content = [
        Paragraph(title, styles["Title"]),
        Spacer(1, 12),
        Paragraph(
            "Fictional restaurant policy for an AI project demonstration.",
            styles["Italic"],
        ),
        Spacer(1, 18),
    ]

    for heading, body in sections:
        content.append(Paragraph(heading, styles["Heading2"]))
        content.append(Paragraph(body, styles["BodyText"]))
        content.append(Spacer(1, 12))

    document.build(content)
    print(f"Created: {output_path}")


create_pdf(
    "refund_policy.pdf",
    "Restaurant Refund and Cancellation Policy",
    [
        (
            "Incorrect or missing item",
            "A customer should report an incorrect or missing item within "
            "24 hours of receiving the order. The restaurant will verify "
            "the order and offer a replacement or a refund for the affected item.",
        ),
        (
            "Food quality complaint",
            "A food quality complaint should be reported within 2 hours "
            "of delivery or collection. The customer should provide the "
            "order number and a photo where possible. A manager reviews "
            "the complaint before approving a replacement or refund.",
        ),
        (
            "Cancellation before preparation",
            "An order can be cancelled for a full refund before the kitchen "
            "starts preparing it. Once preparation has started, cancellation "
            "requires manager approval.",
        ),
        (
            "Refund processing",
            "Approved card refunds are sent to the original payment method. "
            "The restaurant initiates the refund within 3 working days. "
            "The bank may take additional time to show the amount.",
        ),
        (
            "How to request help",
            "Customers should contact the branch, provide their order number, "
            "explain the issue, and keep the receipt.",
        ),
    ],
)

create_pdf(
    "restaurant_sop.pdf",
    "Restaurant Operations SOP",
    [
        (
            "Opening procedure",
            "The shift supervisor checks kitchen cleanliness, equipment "
            "temperatures, staff attendance, and available stock before "
            "opening the branch.",
        ),
        (
            "Receiving supplies",
            "Staff compare each delivery with the purchase order. They "
            "check quantity, packaging, and expiry dates. Damaged or expired "
            "items must be rejected and reported to the supervisor.",
        ),
        (
            "Food handling",
            "Staff wash hands before handling food and after handling raw "
            "ingredients. Raw and ready-to-eat foods are prepared with "
            "separate equipment to reduce cross-contamination.",
        ),
        (
            "Order handover",
            "Before handing over an order, staff verify the order number, "
            "items, packaging, and any special instructions.",
        ),
        (
            "Closing procedure",
            "At closing, the supervisor checks the cash and card totals, "
            "records stock shortages, cleans work areas, and secures "
            "equipment and doors.",
        ),
    ],
)

print("Phase 3 documents created successfully.")