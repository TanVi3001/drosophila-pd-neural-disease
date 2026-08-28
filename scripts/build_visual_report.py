"""Create visualizations and a Vietnamese PDF report from one real rollout."""

from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any, Sequence

import imageio.v2 as imageio
import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as font_manager
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image as PdfImage
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN = ROOT / "results" / "healthy_gpu_seed0"


def _read_json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return document


def _scalar_metrics(metrics: dict[str, Any]) -> dict[str, float]:
    source = metrics.get("scalar_metrics", metrics)
    if not isinstance(source, dict):
        return {}
    return {
        str(key): float(value)
        for key, value in source.items()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    }


def _font_path() -> Path:
    path = Path(font_manager.findfont("DejaVu Sans"))
    if not path.is_file():
        raise RuntimeError("Khong tim thay font Unicode DejaVu Sans de tao PDF tieng Viet.")
    return path


def _load_run(run: Path) -> dict[str, Any]:
    npz_path = run / "rollout.npz"
    metrics_path = run / "metrics" / "metrics.json"
    metadata_path = run / "metadata.json"
    video_path = run / "flygym_rollout.mp4"
    for path in (npz_path, metrics_path, metadata_path, video_path):
        if not path.is_file():
            raise FileNotFoundError(f"Thieu artifact: {path}")

    arrays = np.load(npz_path, allow_pickle=False)
    required = ("timestamp_s", "thorax", "com", "orientation", "joint_positions", "joint_velocity", "joint_acceleration")
    missing = [key for key in required if key not in arrays]
    if missing:
        raise ValueError(f"rollout.npz thieu array: {', '.join(missing)}")
    timestamps = np.asarray(arrays["timestamp_s"], dtype=float)
    thorax = np.asarray(arrays["thorax"], dtype=float)
    com = np.asarray(arrays["com"], dtype=float)
    orientation = np.asarray(arrays["orientation"], dtype=float)
    joints = np.asarray(arrays["joint_positions"], dtype=float)
    joint_velocity = np.asarray(arrays["joint_velocity"], dtype=float)
    joint_acceleration = np.asarray(arrays["joint_acceleration"], dtype=float)
    if timestamps.ndim != 1 or len(timestamps) < 2:
        raise ValueError("timestamp_s phai la vector co it nhat hai frame.")
    if any(len(array) != len(timestamps) for array in (thorax, com, orientation, joints, joint_velocity, joint_acceleration)):
        raise ValueError("Cac rollout array khong cung so frame.")
    if not np.isfinite(timestamps).all() or not np.isfinite(thorax).all() or not np.isfinite(com).all() or not np.isfinite(orientation).all():
        raise ValueError("Rollout chua gia tri NaN/Inf trong cac truong chinh.")
    deltas = np.diff(timestamps)
    if not (deltas > 0).all():
        raise ValueError("timestamp_s khong tang nghiem ngat; khong tao report.")
    dt = float(np.median(deltas))
    orientation_norms = np.linalg.norm(orientation, axis=1)
    if not np.isfinite(orientation_norms).all() or (orientation_norms <= 0).any():
        raise ValueError("Orientation co quaternion khong hop le.")
    thorax_speed = np.zeros(len(timestamps), dtype=float)
    com_speed = np.zeros(len(timestamps), dtype=float)
    thorax_speed[1:] = np.linalg.norm(np.diff(thorax, axis=0), axis=1) / deltas
    com_speed[1:] = np.linalg.norm(np.diff(com, axis=0), axis=1) / deltas
    yaw = _yaw_from_wxyz(orientation)
    contact = None
    if "contact_found" in arrays:
        contact = np.asarray(arrays["contact_found"], dtype=float)
        if len(contact) != len(timestamps):
            contact = None
    metrics = _read_json(metrics_path)
    metadata = _read_json(metadata_path)
    return {
        "run": run,
        "arrays": arrays,
        "timestamps": timestamps,
        "thorax": thorax,
        "com": com,
        "orientation": orientation,
        "joints": joints,
        "joint_velocity": joint_velocity,
        "joint_acceleration": joint_acceleration,
        "thorax_speed": thorax_speed,
        "com_speed": com_speed,
        "yaw": yaw,
        "contact": contact,
        "orientation_norms": orientation_norms,
        "dt": dt,
        "metrics": metrics,
        "metadata": metadata,
        "video": run / "flygym_rollout.mp4",
    }


def _yaw_from_wxyz(quaternions: np.ndarray) -> np.ndarray:
    w, x, y, z = quaternions.T
    sin_yaw = 2.0 * (w * z + x * y)
    cos_yaw = 1.0 - 2.0 * (y * y + z * z)
    return np.unwrap(np.arctan2(sin_yaw, cos_yaw))


def _save_plot(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=170, bbox_inches="tight")
    plt.close()


def _build_plots(data: dict[str, Any], output: Path) -> list[Path]:
    output.mkdir(parents=True, exist_ok=True)
    time = data["timestamps"] - data["timestamps"][0]
    thorax = data["thorax"]
    com = data["com"]
    paths: list[Path] = []

    plt.style.use("ggplot")
    path = output / "01_trajectory_xy.png"
    figure, axis = plt.subplots(figsize=(8, 4.6))
    axis.plot(thorax[:, 0], thorax[:, 1], label="Thorax", linewidth=2)
    axis.plot(com[:, 0], com[:, 1], label="COM", linewidth=1.5)
    axis.scatter(thorax[0, 0], thorax[0, 1], label="Start", s=35)
    axis.scatter(thorax[-1, 0], thorax[-1, 1], label="End", s=35)
    axis.set_title("Trajectory overview (Tổng quan quỹ đạo)")
    axis.set_xlabel("x (mm)")
    axis.set_ylabel("y (mm)")
    axis.axis("equal")
    axis.legend()
    _save_plot(path)
    paths.append(path)

    path = output / "02_speed.png"
    figure, axis = plt.subplots(figsize=(8, 4.6))
    axis.plot(time, data["thorax_speed"], label="Thorax speed")
    axis.plot(time, data["com_speed"], label="COM speed")
    axis.set_title("Walking speed (Tốc độ di chuyển)")
    axis.set_xlabel("Time (Thời gian, s)")
    axis.set_ylabel("Speed (Tốc độ, mm/s)")
    axis.legend()
    _save_plot(path)
    paths.append(path)

    path = output / "03_com_trajectory.png"
    figure, axis = plt.subplots(figsize=(8, 4.6))
    axis.plot(time, com[:, 0], label="COM x")
    axis.plot(time, com[:, 1], label="COM y")
    axis.plot(time, com[:, 2], label="COM z")
    axis.set_title("COM trajectory (Quỹ đạo tâm khối lượng)")
    axis.set_xlabel("Time (Thời gian, s)")
    axis.set_ylabel("Position (Vị trí, mm)")
    axis.legend()
    _save_plot(path)
    paths.append(path)

    path = output / "04_orientation.png"
    figure, axis = plt.subplots(figsize=(8, 4.6))
    axis.plot(time, data["yaw"])
    axis.set_title("Body orientation (Định hướng thân)")
    axis.set_xlabel("Time (Thời gian, s)")
    axis.set_ylabel("Yaw (Góc quay, rad)")
    _save_plot(path)
    paths.append(path)

    path = output / "05_joint_motion.png"
    figure, axis = plt.subplots(figsize=(8, 4.6))
    velocity_rms = np.sqrt(np.mean(data["joint_velocity"] ** 2, axis=1))
    acceleration_rms = np.sqrt(np.mean(data["joint_acceleration"] ** 2, axis=1))
    axis.plot(time, velocity_rms, label="Joint velocity RMS")
    axis.plot(time, acceleration_rms, label="Joint acceleration RMS")
    axis.set_title("Joint motion (Chuyển động khớp)")
    axis.set_xlabel("Time (Thời gian, s)")
    axis.set_ylabel("RMS (Giá trị RMS)")
    axis.legend()
    _save_plot(path)
    paths.append(path)

    path = output / "06_contact_ratio.png"
    figure, axis = plt.subplots(figsize=(8, 4.6))
    if data["contact"] is None:
        axis.text(0.5, 0.5, "Contact data unavailable (Chưa có dữ liệu tiếp xúc)", ha="center", va="center")
        axis.set_axis_off()
    else:
        contact_ratio = np.mean(data["contact"] > 0, axis=1)
        axis.plot(time, contact_ratio)
        axis.set_ylim(-0.02, 1.02)
        axis.set_title("Contact ratio (Tỷ lệ tiếp xúc)")
        axis.set_xlabel("Time (Thời gian, s)")
        axis.set_ylabel("Ratio (Tỷ lệ)")
    _save_plot(path)
    paths.append(path)
    return paths


def _summary_rows(data: dict[str, Any]) -> list[tuple[str, str, str]]:
    scalar = _scalar_metrics(data["metrics"])
    thorax = data["thorax"]
    displacement = float(np.linalg.norm(thorax[-1, :2] - thorax[0, :2]))
    path_length = float(np.linalg.norm(np.diff(thorax[:, :2], axis=0), axis=1).sum())
    velocity_rms = float(np.sqrt(np.mean(data["joint_velocity"] ** 2)))
    acceleration_rms = float(np.sqrt(np.mean(data["joint_acceleration"] ** 2)))
    contact_ratio = "unavailable"
    if data["contact"] is not None:
        contact_ratio = f"{float(np.mean(data['contact'] > 0)):.6g}"
    rows = [
        ("Frame count (Số frame)", str(len(data["timestamps"])), "frame"),
        ("Simulation duration (Thời gian mô phỏng)", f"{data['timestamps'][-1] - data['timestamps'][0]:.8g}", "s"),
        ("Timestep (Bước thời gian)", f"{data['dt']:.8g}", "s"),
        ("Thorax displacement (Độ dời thorax)", f"{displacement:.8g}", "mm"),
        ("Thorax path length (Độ dài quỹ đạo thorax)", f"{path_length:.8g}", "mm"),
        ("Walking speed (Tốc độ di chuyển)", f"{scalar.get('walking_speed_mm_s', float(np.mean(data['thorax_speed']))):.8g}", "mm/s"),
        ("COM velocity mean (Vận tốc COM trung bình)", f"{scalar.get('com_velocity_mean_mm_s', float(np.mean(data['com_speed']))):.8g}", "mm/s"),
        ("Joint velocity RMS (RMS vận tốc khớp)", f"{velocity_rms:.8g}", "raw unit/s"),
        ("Joint acceleration RMS (RMS gia tốc khớp)", f"{acceleration_rms:.8g}", "raw unit/s2"),
        ("Contact ratio (Tỷ lệ tiếp xúc)", contact_ratio, "ratio"),
        ("Quaternion norm min (Norm quaternion nhỏ nhất)", f"{float(np.min(data['orientation_norms'])):.8g}", "norm"),
        ("Timestamp monotonic (Timestamp tăng nghiêm ngặt)", "PASS", "check"),
        ("Finite values (Giá trị hữu hạn)", "PASS", "check"),
    ]
    # Keep source ASCII while emitting correctly encoded Vietnamese labels.
    rows = [
        ("Frame count (S\u1ed1 frame)", str(len(data["timestamps"])), "frame"),
        ("Simulation duration (Th\u1eddi gian m\u00f4 ph\u1ecfng)", f"{data['timestamps'][-1] - data['timestamps'][0]:.8g}", "s"),
        ("Timestep (B\u01b0\u1edbc th\u1eddi gian)", f"{data['dt']:.8g}", "s"),
        ("Thorax displacement (\u0110\u1ed9 d\u1eddi thorax)", f"{displacement:.8g}", "mm"),
        ("Thorax path length (\u0110\u1ed9 d\u00e0i qu\u1ef9 \u0111\u1ea1o thorax)", f"{path_length:.8g}", "mm"),
        ("Walking speed (T\u1ed1c \u0111\u1ed9 di chuy\u1ec3n)", f"{scalar.get('walking_speed_mm_s', float(np.mean(data['thorax_speed']))):.8g}", "mm/s"),
        ("COM velocity mean (V\u1eadn t\u1ed1c trung b\u00ecnh c\u1ee7a COM)", f"{scalar.get('com_velocity_mean_mm_s', float(np.mean(data['com_speed']))):.8g}", "mm/s"),
        ("Joint velocity RMS (RMS v\u1eadn t\u1ed1c kh\u1edbp)", f"{velocity_rms:.8g}", "raw unit/s"),
        ("Joint acceleration RMS (RMS gia t\u1ed1c kh\u1edbp)", f"{acceleration_rms:.8g}", "raw unit/s2"),
        ("Contact ratio (T\u1ef7 l\u1ec7 ti\u1ebfp x\u00fac)", contact_ratio, "ratio"),
        ("Quaternion norm min (Norm quaternion nh\u1ecf nh\u1ea5t)", f"{float(np.min(data['orientation_norms'])):.8g}", "norm"),
        ("Timestamp monotonic (Timestamp t\u0103ng nghi\u00eam ng\u1eb7t)", "PASS", "check"),
        ("Finite values (Gi\u00e1 tr\u1ecb h\u1eefu h\u1ea1n)", "PASS", "check"),
    ]
    return rows


def _write_summary(data: dict[str, Any], output: Path, plots: list[Path], video_output: Path) -> Path:
    rows = _summary_rows(data)
    with (output / "summary_metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["metric", "value", "unit"])
        writer.writerows(rows)
    payload = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "source_run": str(data["run"]),
        "source_video": str(data["video"]),
        "video_review_output": str(video_output),
        "plots": [str(path) for path in plots],
        "metrics": [{"metric": name, "value": value, "unit": unit} for name, value, unit in rows],
        "scientific_scope": "Truc quan hoa va tom tat rollout tinh toan; khong phai xac nhan Parkinson sinh hoc.",
    }
    (output / "visualization_summary.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown = [
        "# B\u00e1o c\u00e1o tr\u1ef1c quan h\u00f3a rollout",
        "",
        "\u0110\u00e2y l\u00e0 t\u00f3m t\u1eaft t\u1eeb artifact rollout th\u1eadt; kh\u00f4ng t\u1ea1o d\u1eef li\u1ec7u khoa h\u1ecdc m\u1edbi v\u00e0 kh\u00f4ng ph\u1ea3i x\u00e1c nh\u1eadn Parkinson sinh h\u1ecdc.",
        "",
        f"- Nguon: `{data['run']}`",
        f"- Video goc: `{data['video']}`",
        f"- Video review: `{video_output}`",
        "",
        "## Metrics",
        "",
        "| Metric | Value | Unit |",
        "| --- | ---: | --- |",
    ]
    markdown.extend(f"| {name} | {value} | {unit} |" for name, value, unit in rows)
    markdown.extend(["", "## H\u00ecnh \u1ea3nh", ""])
    markdown.extend(f"- `{path.name}`" for path in plots)
    markdown.extend(
        [
            "",
            "## Ghi ch\u00fa di\u1ec5n gi\u1ea3i",
            "",
            "- Video review \u0111\u01b0\u1ee3c k\u00e9o d\u00e0i b\u1eb1ng c\u00e1ch ph\u00e1t ch\u1eadm v\u00e0 l\u1eb7p l\u1ea1i frame video th\u1eadt; kh\u00f4ng ph\u1ea3i rollout d\u00e0i h\u01a1n.",
            "- Th\u1eddi gian m\u00f4 ph\u1ecfng trong artifact v\u1eabn gi\u1eef nguy\u00ean; kh\u00f4ng \u0111\u01b0\u1ee3c \u0111\u1ed3ng nh\u1ea5t v\u1edbi th\u1eddi gian ph\u00e1t video.",
            "- C\u00e1c k\u1ebft lu\u1eadn v\u1ec1 sinh h\u1ecdc, ch\u1ea9n \u0111o\u00e1n, l\u00e2m s\u00e0ng ho\u1eb7c thu\u1ed1c n\u1eb1m ngo\u00e0i ph\u1ea1m vi artifact n\u00e0y.",
        ]
    )
    report = output / "visualization_report_vi.md"
    report.write_text("\n".join(markdown) + "\n", encoding="utf-8")
    return report


def _slow_video(data: dict[str, Any], output: Path, duration_s: float) -> Path:
    reader = imageio.get_reader(data["video"])
    frames = [frame for frame in reader]
    metadata = reader.get_meta_data()
    reader.close()
    if not frames:
        raise ValueError("Video khong co frame.")
    fps = 30
    count = max(1, int(round(duration_s * fps)))
    indices = np.rint(np.linspace(0, len(frames) - 1, count)).astype(int)
    font = ImageFont.truetype(str(_font_path()), 16)
    writer = imageio.get_writer(output, fps=fps, codec="libx264", quality=8, macro_block_size=1)
    try:
        source_frame_count = len(data["timestamps"])
        for output_index, source_index in enumerate(indices):
            image = Image.fromarray(np.asarray(frames[source_index]).astype(np.uint8)).convert("RGB")
            draw = ImageDraw.Draw(image)
            mapped_index = int(round(source_index / max(1, len(frames) - 1) * (source_frame_count - 1)))
            mapped_time = float(data["timestamps"][mapped_index] - data["timestamps"][0])
            label = f"FlyGym rollout | video {output_index / fps:.2f}s | simulation {mapped_time:.4f}s"
            draw.rectangle((8, 8, min(image.width - 8, 8 + len(label) * 9), 34), fill=(15, 23, 42))
            draw.text((14, 12), label, font=font, fill=(240, 248, 255))
            writer.append_data(np.asarray(image))
    finally:
        writer.close()
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError(f"Khong tao duoc video review: {output}")
    return output


def _write_pdf(data: dict[str, Any], output: Path, plots: list[Path], video_output: Path) -> Path:
    font_path = _font_path()
    pdfmetrics.registerFont(TTFont("ReportDejaVu", str(font_path)))
    styles = getSampleStyleSheet()
    title = ParagraphStyle("TitleVi", parent=styles["Title"], fontName="ReportDejaVu", alignment=TA_CENTER, fontSize=19, leading=24, textColor=colors.HexColor("#0f172a"))
    heading = ParagraphStyle("HeadingVi", parent=styles["Heading2"], fontName="ReportDejaVu", fontSize=13, leading=17, textColor=colors.HexColor("#0f4c5c"))
    body = ParagraphStyle("BodyVi", parent=styles["BodyText"], fontName="ReportDejaVu", fontSize=9.5, leading=14)
    small = ParagraphStyle("SmallVi", parent=body, fontSize=8, leading=11, textColor=colors.HexColor("#475569"))
    document = SimpleDocTemplate(str(output), pagesize=A4, rightMargin=1.6 * cm, leftMargin=1.6 * cm, topMargin=1.5 * cm, bottomMargin=1.4 * cm)
    story: list[Any] = [
        Paragraph("Báo cáo rollout và visualization", title),
        Spacer(1, 0.3 * cm),
        Paragraph("Healthy GPU rollout - Healthy computational locomotion", heading),
        Paragraph("Báo cáo này đọc trực tiếp artifact đã sinh: rollout.npz, metrics.json, metadata.json và flygym_rollout.mp4. Không tạo dữ liệu khoa học mới.", body),
        Spacer(1, 0.25 * cm),
        Paragraph(f"Nguồn: {data['run']}", small),
        Paragraph(f"Video review: {video_output}", small),
        Spacer(1, 0.3 * cm),
        Paragraph("1. Tóm tắt trạng thái", heading),
        Paragraph("Rollout được kiểm tra có timestamp tăng nghiêm ngặt, các trường chính hữu hạn và quaternion không có norm bằng 0. Thời gian mô phỏng và thời gian phát video là hai khái niệm khác nhau.", body),
        Spacer(1, 0.25 * cm),
    ]
    table_data = [[Paragraph("Metric", body), Paragraph("Giá trị", body), Paragraph("Đơn vị", body)]]
    for name, value, unit in _summary_rows(data):
        table_data.append([Paragraph(name, body), Paragraph(value, body), Paragraph(unit, body)])
    table = Table(table_data, colWidths=[10.5 * cm, 3.0 * cm, 2.3 * cm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(table)
    story.extend([
        PageBreak(),
        Paragraph("2. Visualization", heading),
        Paragraph("Các hình dưới đây dùng dữ liệu rollout thật. Tiêu đề giữ tiếng Anh kèm tiếng Việt để nhóm dễ đối chiếu với metric trong pipeline.", body),
    ])
    for index, plot in enumerate(plots):
        story.append(Spacer(1, 0.25 * cm))
        story.append(Paragraph(f"Figure {index + 1}: {plot.stem}", heading))
        story.append(PdfImage(str(plot), width=17.5 * cm, height=10.0 * cm))
        if index != len(plots) - 1:
            story.append(PageBreak())
    story.extend([
        PageBreak(),
        Paragraph("3. Giới hạn và cách đọc", heading),
        Paragraph("Video review được kéo dài bằng cách phát chậm/lặp lại frame video có thật. Vì rollout gốc chỉ chứa thời gian mô phỏng ngắn, bản video dài hơn không chứng minh rằng mô phỏng đã chạy lâu hơn và cũng không tạo thêm hành vi mới.", body),
        Spacer(1, 0.2 * cm),
        Paragraph("Các số đo trong báo cáo chỉ mô tả computational locomotion rollout. Chúng không phải biological Parkinson validation, chẩn đoán, dự đoán lâm sàng hoặc đánh giá thuốc.", body),
    ])
    document.build(story)
    return output


def build_report(run: Path, output: Path, video_duration_s: float) -> dict[str, str]:
    data = _load_run(run)
    output.mkdir(parents=True, exist_ok=True)
    plots = _build_plots(data, output)
    video_output = _slow_video(data, output / "flygym_rollout_review_12s.mp4", video_duration_s)
    report = _write_summary(data, output, plots, video_output)
    pdf = _write_pdf(data, output / "healthy_gpu_seed0_report_vi.pdf", plots, video_output)
    return {"output": str(output), "report": str(report), "pdf": str(pdf), "video": str(video_output)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--video-duration", type=float, default=12.0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.video_duration <= 0:
        print("ERROR: video-duration phai > 0", file=sys.stderr)
        return 2
    run = args.run.expanduser().resolve()
    output = (args.output or run / "visualization").expanduser().resolve()
    try:
        result = build_report(run, output, args.video_duration)
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
