from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
FRAME_SIZE_720P = (1280, 720)


def _runtime_deps():
    import massing
    import settings
    import ws05

    return massing, settings, ws05


def build_transition_plan(regimes, total_frames):
    if len(regimes) < 2:
        raise ValueError("need at least two regimes")
    if total_frames < len(regimes):
        raise ValueError("total_frames must be at least the regime count")

    transition_count = len(regimes) - 1
    interval_count = total_frames - 1
    base_intervals, remainder = divmod(interval_count, transition_count)
    plan = []

    for pair_index in range(transition_count):
        steps = base_intervals + (1 if pair_index < remainder else 0)
        start_step = 0 if pair_index == 0 else 1
        for step in range(start_step, steps + 1):
            alpha = 1.0 if steps == 0 else step / steps
            plan.append(
                {
                    "pair_index": pair_index,
                    "from_regime": regimes[pair_index],
                    "to_regime": regimes[pair_index + 1],
                    "alpha": alpha,
                }
            )

    return plan


def frame_output_dir(root, slug, duration_s, fps, variant="seg_transition"):
    return Path(root) / slug / f"{variant}_{duration_s}s_{fps}fps"


def pair_records_by_geometry(from_recs, to_recs):
    from_map = {rec["geom"].wkb_hex: rec for rec in from_recs}
    to_map = {rec["geom"].wkb_hex: rec for rec in to_recs}
    keys = sorted(set(from_map) | set(to_map))
    return [{"key": key, "from_rec": from_map.get(key), "to_rec": to_map.get(key)} for key in keys]


def interpolate_scene_records(from_recs, to_recs, alpha):
    scene = []
    for pair in pair_records_by_geometry(from_recs, to_recs):
        from_rec = pair["from_rec"]
        to_rec = pair["to_rec"]
        base_rec = to_rec or from_rec
        from_h = float(from_rec["h"]) if from_rec else 0.0
        to_h = float(to_rec["h"]) if to_rec else 0.0
        h = (1.0 - alpha) * from_h + alpha * to_h
        if h <= 0:
            continue

        if from_rec and to_rec and from_rec["sh"] != to_rec["sh"]:
            sh = f"mix:{from_rec['sh']}:{to_rec['sh']}"
            sh_from = from_rec["sh"]
            sh_to = to_rec["sh"]
            mix = alpha
        else:
            sh = (to_rec or from_rec)["sh"]
            sh_from = sh
            sh_to = sh
            mix = alpha

        scene.append(
            {
                "geom": base_rec["geom"],
                "h": h,
                "sh": sh,
                "sh_from": sh_from,
                "sh_to": sh_to,
                "mix": mix,
                "area": base_rec.get("area", float(base_rec["geom"].area)),
                "frozen": bool(base_rec.get("frozen", False)),
            }
        )
    return scene


def _camera_for_frame(frame_index, total_frames, start_azim, end_azim, elev):
    if total_frames <= 1:
        azim = start_azim
    else:
        azim = start_azim + (end_azim - start_azim) * (frame_index / (total_frames - 1))
    return {"elev": elev, "azim": azim}


def _render_frame(recs, out_path, zmax, slug, context_recs, cam):
    massing, _, _ = _runtime_deps()
    return massing.render_massing(
        recs,
        out_path,
        color="sh",
        cam=cam,
        dpi=100,
        zmax=zmax,
        ground="sat",
        slug=slug,
        context_recs=context_recs,
        background="#000000",
        show_study_outline=False,
        figure_size_px=FRAME_SIZE_720P,
    )


def _build_scene_data(slug, regimes):
    _, _, ws05 = _runtime_deps()
    regime_recs, _ = ws05.regime_recs(slug, regimes)
    context_recs = ws05.load_context_recs(slug)
    zmax = max(max((rec["h"] for rec in recs), default=1) for recs in regime_recs.values()) * 1.05
    return regime_recs, context_recs, zmax


def render_frames(
    slug=None,
    regimes=None,
    duration_s=10,
    fps=24,
    output_dir=None,
    start_azim=None,
    end_azim=None,
    elev=None,
):
    from PIL import Image

    _, settings, _ = _runtime_deps()
    slug = slug or settings.SLUG
    regimes = list(regimes or settings.REGIMES)
    total_frames = duration_s * fps
    plan = build_transition_plan(regimes, total_frames)
    regime_recs, context_recs, zmax = _build_scene_data(slug, regimes)
    output_dir = Path(output_dir) if output_dir else frame_output_dir(OUT, slug, duration_s, fps)
    output_dir.mkdir(parents=True, exist_ok=True)

    start_azim = settings.CAM["azim"] if start_azim is None else start_azim
    end_azim = start_azim + 120 if end_azim is None else end_azim
    elev = max(settings.CAM["elev"], 52) if elev is None else elev

    with TemporaryDirectory(prefix="seg_transition_") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        for frame_index, step in enumerate(plan):
            frame_path = output_dir / f"f{frame_index:03d}.png"
            if frame_path.exists():
                continue
            if frame_index % 10 == 0 or frame_index == total_frames - 1:
                print(
                    f"frame {frame_index + 1}/{total_frames}: "
                    f"{step['from_regime']} -> {step['to_regime']} "
                    f"alpha={step['alpha']:.2f}"
                )
            cam = _camera_for_frame(frame_index, total_frames, start_azim, end_azim, elev)
            left_path = temp_dir / f"left_{frame_index:04d}.png"
            right_path = temp_dir / f"right_{frame_index:04d}.png"
            _render_frame(regime_recs[step["from_regime"]], left_path, zmax, slug, context_recs, cam)
            _render_frame(regime_recs[step["to_regime"]], right_path, zmax, slug, context_recs, cam)

            with Image.open(left_path).convert("RGBA") as left_img, Image.open(right_path).convert("RGBA") as right_img:
                blended = Image.blend(left_img, right_img, step["alpha"])
                blended.save(frame_path)

    return output_dir


def render_numeric_frames(
    slug=None,
    regimes=None,
    duration_s=10,
    fps=24,
    output_dir=None,
    start_azim=None,
    end_azim=None,
    elev=None,
):
    _, settings, _ = _runtime_deps()
    slug = slug or settings.SLUG
    regimes = list(regimes or settings.REGIMES)
    total_frames = duration_s * fps
    plan = build_transition_plan(regimes, total_frames)
    regime_recs, context_recs, zmax = _build_scene_data(slug, regimes)
    output_dir = Path(output_dir) if output_dir else frame_output_dir(
        OUT, slug, duration_s, fps, variant="seg_transition_numeric"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    start_azim = settings.CAM["azim"] if start_azim is None else start_azim
    end_azim = start_azim + 120 if end_azim is None else end_azim
    elev = max(settings.CAM["elev"], 52) if elev is None else elev

    for frame_index, step in enumerate(plan):
        frame_path = output_dir / f"f{frame_index:03d}.png"
        if frame_path.exists():
            continue
        if frame_index % 10 == 0 or frame_index == total_frames - 1:
            print(
                f"numeric frame {frame_index + 1}/{total_frames}: "
                f"{step['from_regime']} -> {step['to_regime']} "
                f"alpha={step['alpha']:.2f}"
            )
        cam = _camera_for_frame(frame_index, total_frames, start_azim, end_azim, elev)
        scene = interpolate_scene_records(
            regime_recs[step["from_regime"]],
            regime_recs[step["to_regime"]],
            step["alpha"],
        )
        _render_frame(scene, frame_path, zmax, slug, context_recs, cam)

    return output_dir


def encode_video(frames_dir, fps=24, out_path=None):
    import cv2
    import numpy as np
    from PIL import Image

    frames_dir = Path(frames_dir).resolve()
    out_path = Path(out_path) if out_path else frames_dir.parent / f"{frames_dir.name or 'video'}.mp4"
    frame_paths = sorted(frames_dir.glob("f*.png"))
    if not frame_paths:
        raise ValueError(f"no frames found in {frames_dir}")

    with Image.open(frame_paths[0]).convert("RGB") as first_image:
        first = cv2.cvtColor(np.array(first_image), cv2.COLOR_RGB2BGR)

    height, width = first.shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, fps, (width, height))
    if not writer.isOpened():
        raise ValueError(f"failed to open video writer for {out_path}")

    for frame_path in frame_paths:
        with Image.open(frame_path).convert("RGB") as frame_image:
            frame = cv2.cvtColor(np.array(frame_image), cv2.COLOR_RGB2BGR)
        if frame.shape[1] != width or frame.shape[0] != height:
            frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
        writer.write(frame)
    writer.release()
    return out_path
