"""Export a Vietnamese project-status PDF from the frozen publication evidence."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/report/project_status_and_next_steps_vi.pdf"
FONT_REGULAR = Path(r"C:\Windows\Fonts\arial.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\arialbd.ttf")


def _paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text.replace("\n", "<br/>"), style)


def _header_footer(canvas, document) -> None:  # type: ignore[no-untyped-def]
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#4A2F23"))
    canvas.setLineWidth(1)
    canvas.line(1.65 * cm, 28.2 * cm, 19.35 * cm, 28.2 * cm)
    canvas.setFont("Arial", 8)
    canvas.setFillColor(colors.HexColor("#6B7280"))
    canvas.drawString(1.65 * cm, 0.95 * cm, "Drosophila PD Neural Disease | Báo cáo tiến độ")
    canvas.drawRightString(19.35 * cm, 0.95 * cm, f"Trang {document.page}")
    canvas.restoreState()


def build_report() -> None:
    if not FONT_REGULAR.is_file() or not FONT_BOLD.is_file():
        raise FileNotFoundError("Arial Unicode fonts are required at C:\\Windows\\Fonts.")
    pdfmetrics.registerFont(TTFont("Arial", str(FONT_REGULAR)))
    pdfmetrics.registerFont(TTFont("Arial-Bold", str(FONT_BOLD)))

    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "TitleVi", parent=styles["Title"], fontName="Arial-Bold", fontSize=24,
        leading=30, alignment=TA_CENTER, textColor=colors.HexColor("#3D281D"), spaceAfter=14,
    )
    subtitle = ParagraphStyle(
        "SubtitleVi", parent=styles["Normal"], fontName="Arial", fontSize=12,
        leading=18, alignment=TA_CENTER, textColor=colors.HexColor("#4B5563"), spaceAfter=20,
    )
    h1 = ParagraphStyle(
        "Heading1Vi", parent=styles["Heading1"], fontName="Arial-Bold", fontSize=16,
        leading=21, textColor=colors.HexColor("#4A2F23"), spaceBefore=10, spaceAfter=8,
    )
    h2 = ParagraphStyle(
        "Heading2Vi", parent=styles["Heading2"], fontName="Arial-Bold", fontSize=12,
        leading=16, textColor=colors.HexColor("#7C4A2D"), spaceBefore=8, spaceAfter=5,
    )
    body = ParagraphStyle(
        "BodyVi", parent=styles["BodyText"], fontName="Arial", fontSize=10.2,
        leading=14.5, alignment=TA_LEFT, spaceAfter=6,
    )
    small = ParagraphStyle(
        "SmallVi", parent=body, fontSize=8.6, leading=11.5, spaceAfter=0,
    )
    quote = ParagraphStyle(
        "QuoteVi", parent=body, fontName="Arial-Bold", textColor=colors.HexColor("#344E41"),
        leftIndent=12, rightIndent=12, borderColor=colors.HexColor("#B7C9B4"),
        borderWidth=0.6, borderPadding=8, backColor=colors.HexColor("#F1F6EF"), spaceBefore=5,
        spaceAfter=10,
    )

    document = SimpleDocTemplate(
        str(OUTPUT), pagesize=A4, rightMargin=1.65 * cm, leftMargin=1.65 * cm,
        topMargin=1.8 * cm, bottomMargin=1.55 * cm, title="Bao cao tien do Drosophila PD Neural Disease",
        author="Nhom nghien cuu Drosophila PD Neural Disease",
    )
    story = [Spacer(1, 2.1 * cm)]
    story.extend([
        _paragraph("BÁO CÁO TIẾN ĐỘ VÀ KẾ HOẠCH HOÀN THIỆN", title),
        _paragraph("Drosophila PD Neural Disease", subtitle),
        _paragraph("Cập nhật: 07/09/2026 | Phạm vi: computational locomotion proxy trong FlyGym", subtitle),
        Spacer(1, 1.0 * cm),
        _paragraph("Tóm tắt điều hành", h1),
        _paragraph(
            "Nhóm đã xây dựng pipeline mô phỏng vận động tính toán của ruồi giấm có provenance, "
            "calibration, holdout, reproducibility và publication control plane. Evidence hiện tại đủ để "
            "báo cáo một computational locomotion proxy, nhưng không đủ để tuyên bố biological Parkinson "
            "validation hay gene-specific validation.", body),
        _paragraph(
            "Chen-calibrated organism-level computational locomotion proxy with directional Pozo holdout "
            "concordance and substantial quantitative ratio mismatch.", quote),
        _paragraph("Báo cáo này phân tách kết quả đã hoàn thành, giới hạn khoa học và các bước con người cần thực hiện trước khi nộp bài.", body),
        PageBreak(),
        _paragraph("1. Công việc đã hoàn thành", h1),
        _paragraph("Nền tảng kỹ thuật và tái lập", h2),
        _paragraph("• Healthy neural core da duoc khoa bang manifest, SHA256 va provenance; checkpoint healthy khong bi ghi de.<br/>"
                   "• Action hook Brain-to-Body da duoc xac dinh va ket noi: controller tao LocomotionAction, FlyGym nhan motor command va simulation tien buoc.<br/>"
                   "• Healthy baseline, contract metric, QC contact/joint/action, manifest va checksum da co.<br/>"
                   "• Gate 25 dong bang compact evidence package; raw video, checkpoint va rollout lon khong nam trong release package de tiet kiem dung luong.", body),
        _paragraph("Calibration, confirmation và holdout", h2),
        _paragraph("• Chen 2014 la target calibration theo ty le planar speed: disease/control = 0.6701.<br/>"
                   "• Gate 13B: simulated ratio = 0.5856; sai lech = 0.0845.<br/>"
                   "• Gate 13C: parameter da khoa duoc xac nhan lai; simulated ratio = 0.6142; sai lech = 0.0559.<br/>"
                   "• Gate 21: 25/25 Parkin class-level exploratory rollout pass QC.<br/>"
                   "• Gate 22: 55 dong comparison Healthy-Parkin proxy theo burden.<br/>"
                   "• Gate 23-24: Pozo distance directionality PASS, quantitative ratio MISMATCH va duoc giu nguyen.", body),
        _paragraph("Đóng gói công bố", h2),
        _paragraph("Gate 24 da tong hop concordance va figures co provenance. Gate 26 co manuscript draft, figures, tables, manifest va independent verifier. Gate 27-37 da co handoff, signoff, metadata, archive, submission, revision va acceptance templates. Regression suite tren main: 252 passed; publication-control verifier: 37 artifact; calibration audit: READY_FOR_CALIBRATION.", body),
        PageBreak(),
        _paragraph("2. Đánh giá evidence hiện tại", h1),
    ])

    rows = [
        ["Evidence", "Trạng thái", "Diễn giải"],
        ["Chen calibration", "PASS", "Calibration tính toán ở mức organism-level proxy."],
        ["Chen confirmation", "PASS", "Parameter đã khóa được xác nhận lại."],
        ["Parkin rollout runtime", "PASS", "Class-level exploratory có QC; không gene-specific."],
        ["Pozo directionality", "PASS", "Distance simulation giảm đúng hướng so với control."],
        ["Pozo quantitative ratio", "MISMATCH", "Không đạt đồng thuận định lượng; phải báo cáo rõ."],
        ["Gene-specific validation", "NOT AVAILABLE", "Chưa có mapping neuron/edge đủ provenance."],
        ["Biological PD validation", "NOT AVAILABLE", "Chưa có wet-lab validation độc lập."],
    ]
    table = Table([[ _paragraph(cell, small) for cell in row] for row in rows], colWidths=[4.2 * cm, 3.0 * cm, 10.35 * cm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4A2F23")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Arial-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D6D3D1")),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FAFAF9")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#FAFAF9"), colors.HexColor("#F5F2EE")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([
        table,
        Spacer(1, 10),
        _paragraph("Diễn giải bắt buộc", h2),
        _paragraph("Seed mô phỏng không được xem là mẫu sinh học độc lập để suy diễn p-value hay kết luận cơ chế sinh học. Mismatch Pozo là kết quả cần được giữ trong manuscript, không phải lỗi được phép ẩn bỏ. Parkin runtime evidence chỉ được gọi là class-level exploratory.", body),
        _paragraph("3. Kế hoạch hoàn thiện trước khi nộp bài", h1),
    ])
    steps = [
        ("Gate 31 - Internal Scientific Signoff", "Giảng viên, methods reviewer, corresponding author và toàn bộ tác giả đọc Methods, figures, mismatch Pozo, limitations và claim lock. Chỉ phê duyệt khi đồng ý giữ phạm vi computational proxy."),
        ("Gate 32 - Metadata Finalization", "Chốt license, tác giả, affiliation, ORCID, funding, COI, ethics statement và venue. Kiểm tra quyền phân phối tài liệu của bên thứ ba trước khi archive công khai."),
        ("Gate 33 - Venue-Specific Manuscript", "Chuyển manuscript sang template tiếng Anh của venue; kiểm tra page limit, bibliography, figures, declarations và cover letter."),
        ("Gate 34 - Public Archive Release", "Tạo GitHub Release từ commit/tag được duyệt, archive trên Zenodo/kho trường, nhận DOI thật và ghi receipt local."),
        ("Gate 35 - External Submission", "Corresponding author nộp qua portal, lưu submission ID/ngày nộp/venue trong receipt local."),
        ("Gate 36 - Reviewer Response / Revision", "Ghi từng comment và response. Bất kỳ experiment mới nào phải tạo gate mới; không sửa evidence frozen âm thầm."),
        ("Gate 37 - Acceptance and Final Archive", "Chốt camera-ready, DOI, bibliographic record, archive cuối và release notes sau khi có acceptance thật."),
    ]
    for heading, description in steps:
        story.append(KeepTogether([_paragraph(heading, h2), _paragraph(description, body)]))
    story.extend([
        PageBreak(),
        _paragraph("4. Checklist ký duyệt và kiểm tra", h1),
        _paragraph("Trước Gate 31, chạy các lệnh sau trên main:", h2),
        _paragraph("py -3.12 scripts\\verify_gates31_37_publication_control_plane.py<br/>"
                   "py -3.12 scripts\\audit_calibration_targets.py<br/>"
                   "py -3.12 -m compileall -q src scripts tests<br/>"
                   "py -3.12 -m pytest -q -rs -p no:cacheprovider<br/>"
                   "git diff --check", quote),
        _paragraph("Kết quả mong đợi là verifier pass, audit READY_FOR_CALIBRATION, test pass và không có whitespace error. Các trạng thái WAITING_* ở Gate 31-37 là việc cần người có thẩm quyền thực hiện, không phải lỗi code.", body),
        _paragraph("5. Hướng phát triển sau công bố", h1),
        _paragraph("Nhóm nên thu thập mapping neuron/edge có provenance cho từng condition, bổ sung cohort/paper độc lập và thiết kế wet-lab validation. Chỉ khi mapping, neural-level perturbation và phenotype độc lập đồng thuận mới được nâng cấp claim vượt qua class-level exploratory computational proxy.", body),
        Spacer(1, 10),
        _paragraph("Nguồn nội bộ: Gate 13-14 (calibration và holdout), Gate 21-24 (runtime/comparison/concordance), Gate 25-26 (freeze/package) và Gate 27-37 (publication handoff/control plane).", small),
    ])
    document.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)


if __name__ == "__main__":
    build_report()
    print(f"Created: {OUTPUT}")
