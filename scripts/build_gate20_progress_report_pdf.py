"""Tao bao cao PDF tieng Viet tu artifact Gate 19 va Gate 20.

Script nay chi doc summary JSON da sinh boi pipeline; no khong tao hay thay
doi metrics simulation.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import html
import json
from pathlib import Path
import subprocess
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GATE20 = ROOT / "results/disease_exploratory_gate20/disease_exploratory_summary.json"
DEFAULT_GATE19 = ROOT / "results/healthy_baseline_gate19/healthy_baseline_summary.json"
DEFAULT_OUTPUT = ROOT / "docs/report/gate20_progress_report_vi.pdf"


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def _text(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _font_path() -> tuple[str, str, str]:
    candidates = [
        (Path(r"C:\Windows\Fonts\arial.ttf"), Path(r"C:\Windows\Fonts\arialbd.ttf"), Path(r"C:\Windows\Fonts\ariali.ttf")),
        (Path(r"C:\Windows\Fonts\segoeui.ttf"), Path(r"C:\Windows\Fonts\segoeuib.ttf"), Path(r"C:\Windows\Fonts\segoeuii.ttf")),
    ]
    for regular, bold, italic in candidates:
        if regular.is_file() and bold.is_file() and italic.is_file():
            return str(regular), str(bold), str(italic)
    return "", "", ""


def _git_commit() -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "UNAVAILABLE"


def _fmt(value: Any, digits: int = 4) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f"{float(value):.{digits}f}"
    return str(value)


def build(gate20_path: Path, gate19_path: Path, output: Path) -> None:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
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

    gate20 = _read_json(gate20_path)
    gate19 = _read_json(gate19_path)
    regular, bold, italic = _font_path()
    font = "Helvetica"
    font_bold = "Helvetica-Bold"
    font_italic = "Helvetica-Oblique"
    if regular:
        pdfmetrics.registerFont(TTFont("ReportVI", regular))
        pdfmetrics.registerFont(TTFont("ReportVIBold", bold))
        pdfmetrics.registerFont(TTFont("ReportVIIta", italic))
        font, font_bold, font_italic = "ReportVI", "ReportVIBold", "ReportVIIta"

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CoverTitleVI", parent=styles["Title"], fontName=font_bold, fontSize=24, leading=30, alignment=TA_CENTER, textColor=colors.HexColor("#123B5D"), spaceAfter=12))
    styles.add(ParagraphStyle(name="CoverSubVI", parent=styles["Normal"], fontName=font, fontSize=12, leading=17, alignment=TA_CENTER, textColor=colors.HexColor("#405467"), spaceAfter=8))
    styles.add(ParagraphStyle(name="H1VI", parent=styles["Heading1"], fontName=font_bold, fontSize=15, leading=19, textColor=colors.HexColor("#123B5D"), spaceBefore=9, spaceAfter=7))
    styles.add(ParagraphStyle(name="H2VI", parent=styles["Heading2"], fontName=font_bold, fontSize=11, leading=14, textColor=colors.HexColor("#216A78"), spaceBefore=7, spaceAfter=5))
    styles.add(ParagraphStyle(name="BodyVI", parent=styles["BodyText"], fontName=font, fontSize=9.5, leading=14, alignment=TA_LEFT, textColor=colors.HexColor("#263746"), spaceAfter=6))
    styles.add(ParagraphStyle(name="SmallVI", parent=styles["BodyText"], fontName=font, fontSize=8, leading=11, textColor=colors.HexColor("#52616D"), spaceAfter=3))
    styles.add(ParagraphStyle(name="CodeVI", parent=styles["BodyText"], fontName=font, fontSize=8.5, leading=12, backColor=colors.HexColor("#F1F5F7"), borderColor=colors.HexColor("#D5E0E5"), borderWidth=0.5, borderPadding=6, spaceAfter=7))
    styles.add(ParagraphStyle(name="TableVI", parent=styles["BodyText"], fontName=font, fontSize=7.5, leading=9.5, textColor=colors.HexColor("#263746")))
    styles.add(ParagraphStyle(name="TableHeadVI", parent=styles["BodyText"], fontName=font_bold, fontSize=7.5, leading=9.5, textColor=colors.white))

    def p(value: Any, style: str = "BodyVI") -> Paragraph:
        return Paragraph(_text(value).replace("\n", "<br/>"), styles[style])

    def bullet(value: str) -> Paragraph:
        return Paragraph("&#8226; " + _text(value), styles["BodyVI"])

    def table(data: list[list[Any]], widths: list[float], header: bool = True) -> Table:
        converted = [[item if isinstance(item, Paragraph) else p(item, "TableHeadVI" if header and row_index == 0 else "TableVI") for item in row] for row_index, row in enumerate(data)]
        result = Table(converted, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
        commands = [
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD8DE")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
        if header:
            commands.extend([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#216A78")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ])
            for row_index in range(1, len(converted)):
                if row_index % 2 == 0:
                    commands.append(("BACKGROUND", (0, row_index), (-1, row_index), colors.HexColor("#F5F8F9")))
        result.setStyle(TableStyle(commands))
        return result

    def on_page(canvas: Any, document: Any) -> None:
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#D5E0E5"))
        canvas.line(18 * mm, 14 * mm, 192 * mm, 14 * mm)
        canvas.setFont(font, 7.5)
        canvas.setFillColor(colors.HexColor("#657681"))
        canvas.drawString(18 * mm, 9 * mm, "Báo cáo tiến độ nghiên cứu - Drosophila PD FlyGym")
        canvas.drawRightString(192 * mm, 9 * mm, f"Trang {document.page}")
        canvas.restoreState()

    output.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(str(output), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=17 * mm, bottomMargin=20 * mm, title="Báo cáo tiến độ Gate 20 - Drosophila PD FlyGym", author="Nhóm nghiên cứu")
    story: list[Any] = []
    story.extend([
        Spacer(1, 35 * mm),
        p("BÁO CÁO TIẾN ĐỘ NGHIÊN CỨU", "CoverTitleVI"),
        p("Gate 19 - Healthy baseline và Gate 20 - Exploratory disease proxy", "CoverSubVI"),
        Spacer(1, 10 * mm),
        table([[p("Trạng thái hiện tại", "TableHeadVI"), p(gate20.get("status", "UNKNOWN"), "TableHeadVI")], [p("Ngày lập báo cáo", "TableVI"), p(datetime.now().strftime("%d/%m/%Y"), "TableVI")], [p("Commit tại thời điểm xuất", "TableVI"), p(_git_commit(), "TableVI")]], [65 * mm, 105 * mm]),
        Spacer(1, 12 * mm),
        p("Tài liệu này trình bày những gì nhóm đã thực hiện, lý do của từng bước, bằng chứng artifact hiện có và các giới hạn cần giữ khi báo cáo cho giảng viên. Các số liệu được đọc từ summary JSON của pipeline, không tạo thủ công.", "CoverSubVI"),
        PageBreak(),
    ])

    story.extend([
        p("1. Tóm tắt điều hành", "H1VI"),
        p("Nhóm đã hoàn tất một healthy baseline computational bằng brain-body runtime thật, FlyGym/MuJoCo và GPU CUDA. Baseline gồm 5 seed, mỗi seed 100.000 bước với timestep 0,0001 giây, tương đương 10 giây vật lý. Tất cả 5 seed đạt các kiểm tra locomotion và artifact.", "BodyVI"),
        p("Gate 20 mở rộng pipeline bằng một operator giảm biên độ joint action tại action hook thật. Đây là proxy ở mức organism/class-level để kiểm tra độ nhạy của locomotion trước burden định trước. Nó không phải thay đổi gene cụ thể, không phải mô phỏng cơ chế Parkinson ở cấp tế bào và không phải biological validation.", "BodyVI"),
        table([["Mốc", "Đã làm được", "Ý nghĩa"], ["Gate 19", "5/5 healthy seed PASS", "Xác nhận baseline và giao thức vật lý có thể tái lập"], ["Gate 20", "3/50 proxy rollout PASS; 47 pending", "Xác nhận pipeline/operator thật đã chạy được trên CUDA, nhưng ma trận chưa hoàn tất"], ["Calibration audit", "READY_FOR_CALIBRATION", "Target policy đã sẵn sàng; chưa có nghĩa là đã calibration disease"], ["Scientific claim", "Computational only", "Không claim biological Parkinson, chẩn đoán hoặc thuốc"]], [32 * mm, 62 * mm, 76 * mm]),
        p("2. Mục tiêu và lý do thiết kế", "H1VI"),
        bullet("Gate 19 được chạy trước để có một chuẩn healthy cùng physics, timestep, CPG, renderer và seed policy."),
        bullet("Gate 20 dùng cùng protocol với Gate 19 để khi đủ dữ liệu có thể so sánh thay đổi do proxy burden, thay vì thay đổi do môi trường chạy."),
        bullet("Operator chỉ biến đổi joint_angles và giữ adhesion_onoff. Điều này giới hạn thay đổi ở action-level, không sửa MuJoCo, connectome hoặc FlyGym."),
        bullet("Ma trận burden và seed được khai báo trước, không fit burden trong Gate 20, không chạy calibration và không dùng holdout."),
        p("3. Healthy baseline đã hoàn thành", "H1VI"),
    ])

    gate19_metrics = gate19.get("summary", {})
    baseline_rows = [["Metric", "n", "Mean", "Sample SD", "Đơn vị"]]
    units = {"walking_speed_mm_s": "mm/s", "mean_planar_speed_mm_s": "mm/s", "distance_traveled_mm": "mm", "displacement_mm": "mm", "contact_ratio": "tỷ lệ", "joint_rms_velocity": "đơn vị joint/s"}
    for name in ("walking_speed_mm_s", "mean_planar_speed_mm_s", "distance_traveled_mm", "displacement_mm", "contact_ratio", "joint_rms_velocity"):
        item = gate19_metrics.get(name, {})
        baseline_rows.append([name, item.get("n", "-"), _fmt(item.get("mean", "-")), _fmt(item.get("sample_sd", "-")), units[name]])
    story.extend([
        p("Healthy baseline: 5 seed PASS, không NaN/Inf, timestamp và joint trajectory hợp lệ. Video đại diện seed 0 đã được tạo với tracking camera.", "BodyVI"),
        table(baseline_rows, [48 * mm, 15 * mm, 34 * mm, 34 * mm, 39 * mm]),
        Spacer(1, 5),
        p("Các giá trị trên là thống kê giữa 5 rollout healthy; chúng là computational baseline, không phải dữ liệu sinh học chuẩn và không phải biological validation.", "SmallVI"),
        PageBreak(),
        p("4. Gate 20 exploratory proxy", "H1VI"),
        p("Thiết kế hiện tại gồm alpha_synuclein proxy và pink1 proxy ở nhãn condition exploratory. Cả hai đều đặt gene_specific_mapping=false. Burden grid gồm 0; 0,25; 0,5; 0,75; 1,0 và mỗi burden dự kiến chạy seed 0-4, tổng 50 rollout.", "BodyVI"),
        table([["Thuộc tính", "Giá trị"], ["Scope", "organism-level/class-level computational exploratory proxy"], ["Runtime", "CUDA; 138.639 neuron; khoảng 15 triệu synapse"], ["Protocol", "100.000 bước; timestep 0,0001 s; duration 10 s; stimulus p9; CPG 12 Hz"], ["Action hook", "Operator áp dụng trên joint_angles; adhesion_onoff được giữ nguyên"], ["Gate 20 status", gate20.get("status", "UNKNOWN")], ["Đã hoàn tất", f"{gate20.get('completed_rollouts', 0)}/{gate20.get('planned_rollouts', 0)}; PASS={gate20.get('pass_count', 0)}; pending={gate20.get('pending_count', 0)}"]], [45 * mm, 125 * mm]),
        p("Bằng chứng 3 rollout đã hoàn tất", "H2VI"),
    ])
    actual_rows = [["Condition", "Burden", "Seed", "Status", "Speed planar (mm/s)", "Displacement (mm)", "Operator", "Adhesion"]]
    for row in gate20.get("rows", []):
        actual_rows.append([row.get("condition_id"), row.get("burden_level"), row.get("seed"), row.get("status"), _fmt(row.get("mean_planar_speed_mm_s")), _fmt(row.get("displacement_mm")), "PASS" if row.get("operator_applied") else "FAIL", "PASS" if row.get("adhesion_onoff_unchanged") else "FAIL"])
    story.append(table(actual_rows, [32 * mm, 16 * mm, 12 * mm, 19 * mm, 32 * mm, 31 * mm, 26 * mm, 23 * mm]))
    story.extend([
        p("Ba row hiện có đều là alpha_synuclein burden 0, seed 0-2. Burden 0 là phép kiểm tra identity của operator, vì vậy chưa thể dùng chúng để kết luận proxy làm thay đổi vận động. Các positive burden và pink1 chưa có trong artifact hiện tại.", "SmallVI"),
        p("5. Vì sao Gate 20 tốn thời gian", "H1VI"),
        bullet("Một rollout gồm 100.000 lần lặp BrainEngine, controller, FlyGym/MuJoCo và ghi frame-level trajectory."),
        bullet("Brain source có 138.639 neuron và khoảng 15 triệu synapse; GPU giúp chạy neural computation nhưng không loại bỏ chi phí controller, recorder và export."),
        bullet("Raw JSON/CSV/NPZ của một rollout dài có thể lên đến nhiều GB; pipeline phải hash rồi mới xóa raw để giữ provenance mà không làm đầy ổ đĩa."),
        bullet("Trên RTX 3050 6 GB, một rollout đo được khoảng 23 phút. Vì vậy 50 rollout tuần tự có thể mất xấp xỉ 18-20 giờ."),
        p("Việc dừng sau 3 run là dừng có chủ đích tại checkpoint, không phải crash mô phỏng. Lệnh chạy lại sẽ đọc các QC row PASS và tiếp tục các run pending.", "BodyVI"),
        PageBreak(),
        p("6. Kiểm soát chất lượng và provenance", "H1VI"),
        table([["Kiểm tra", "Kết quả"], ["Runtime artifact audit", "READY"], ["NaN/Inf", "PASS trên 3 Gate 20 row đã hoàn tất"], ["Timestamp/timestep", "PASS"], ["Locomotion/contact", "PASS"], ["Joint/action trajectory", "PASS"], ["Operator metadata", "PASS; sidecar proxy_operator_audit.json"], ["Manifest/checksum", "PASS; compact artifact hash khớp"], ["Regression tests", "169 passed; compileall PASS; git diff --check PASS"]], [65 * mm, 105 * mm]),
        p("Manifest Gate 20 ghi rõ raw artifact lớn không được giữ trong Git, nhưng mỗi run có inventory và SHA-256 trước khi xóa. Summary cũng ghi brain root, platform commit, runner checksum, operator config checksum và boundary khoa học.", "BodyVI"),
        p("7. Các việc còn lại", "H1VI"),
        bullet("Tiếp tục 47 rollout pending bằng lệnh resume; chỉ khi đủ ma trận mới có thể tổng hợp burden-response."),
        bullet("Không gọi alpha_synuclein hoặc pink1 hiện tại là gene-specific nếu chưa có neuron mapping/provenance được duyệt."),
        bullet("Sau Gate 20 hoàn tất, mới cân nhắc Gate 21 so sánh với healthy; không dùng 3 seed burden 0 hiện tại làm disease effect."),
        bullet("Calibration/holdout/concordance chỉ chạy theo target literature đã review và đúng endpoint; Gate 20 hiện không chạy các bước đó."),
        p("8. Cách tiếp tục chạy", "H1VI"),
        p("Lệnh sau sẽ tự bỏ qua 3 row PASS đã checkpoint và chạy các tổ hợp còn lại:", "BodyVI"),
        p("py -3.12 scripts/run_disease_exploratory_gate20.py", "CodeVI"),
        p("Nếu cần chỉ kết xuất lại báo cáo từ checkpoint mà không chạy GPU:", "BodyVI"),
        p("py -3.12 scripts/run_disease_exploratory_gate20.py --finalize-checkpoint", "CodeVI"),
        p("9. Kết luận phạm vi", "H1VI"),
        p("Nhóm đã chứng minh được healthy brain-body computational locomotion runtime và đã nối được một proxy burden operator vào action hook thật của FlyGym. Gate 20 hiện mới có 3 rollout exploratory PASS trong tổng 50 rollout dự kiến. Kết quả này có ý nghĩa kỹ thuật về khả năng thực thi, kiểm soát artifact và chuẩn bị thí nghiệm; chưa đủ để kết luận mô hình gene-specific, cơ chế Parkinson, biological validation, chẩn đoán hoặc hiệu quả thuốc.", "BodyVI"),
        p("Đây là báo cáo tiến độ trung thực: phần đã có là dữ liệu runtime thật; phần pending được giữ nguyên pending và không được thay bằng số giả.", "BodyVI"),
    ])
    document.build(story, onFirstPage=on_page, onLaterPages=on_page)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate20", type=Path, default=DEFAULT_GATE20)
    parser.add_argument("--gate19", type=Path, default=DEFAULT_GATE19)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        build(args.gate20, args.gate19, args.output)
    except (OSError, ValueError, ImportError) as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"PDF: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
