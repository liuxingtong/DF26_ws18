import shutil
import time
from tempfile import gettempdir
from pathlib import Path

import intro_story
import seg_transition
import settings


def staging_frame_output_dir(slug, duration_s=15, fps=24):
    return Path(gettempdir()) / "codex_intro_story_export" / slug / f"frames_{duration_s}s_{fps}fps"


def staging_video_output_path(slug, duration_s=15):
    return Path(gettempdir()) / "codex_intro_story_export" / slug / f"intro_story_dark_{duration_s}s.mp4"


def capture_frames(page_path, frames_dir, duration_s=15, fps=24, width=1920, height=1080, start_index=0, end_index=None):
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.edge.options import Options as EdgeOptions

    frames_dir = Path(frames_dir)
    frames_dir.mkdir(parents=True, exist_ok=True)

    driver = None
    last_error = None
    try:
        edge_options = EdgeOptions()
        edge_options.use_chromium = True
        for arg in (
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--allow-file-access-from-files",
            "--force-device-scale-factor=1",
        ):
            edge_options.add_argument(arg)
        driver = webdriver.Edge(options=edge_options)
    except Exception as exc:
        last_error = exc

    if driver is None:
        try:
            chrome_options = ChromeOptions()
            for arg in (
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                "--allow-file-access-from-files",
                "--force-device-scale-factor=1",
            ):
                chrome_options.add_argument(arg)
            driver = webdriver.Chrome(options=chrome_options)
        except Exception as exc:
            raise RuntimeError(f"Unable to start a Selenium browser for export: {last_error or exc}") from exc

    try:
        driver.set_window_size(width, height)
        driver.get(page_path.resolve().as_uri())
        time.sleep(4.0)
        total_frames = duration_s * fps
        final_index = total_frames if end_index is None else min(end_index, total_frames)
        for index in range(start_index, final_index):
            frame_path = frames_dir / f"f{index:03d}.png"
            if frame_path.exists():
                continue
            if index % fps == 0 or index == total_frames - 1:
                print(f"capturing frame {index + 1}/{total_frames}")
            elapsed_ms = (index / fps) * 1000
            driver.execute_script("window.__codexRenderAt(arguments[0]);", float(elapsed_ms))
            time.sleep(0.08)
            driver.save_screenshot(str(frame_path))
    finally:
        if driver is not None:
            driver.quit()
    return frames_dir


def assemble_video_from_frames(slug, duration_s=15, fps=24, frames_dir=None, out_path=None):
    frames_dir = Path(frames_dir) if frames_dir else staging_frame_output_dir(slug, duration_s=duration_s, fps=fps)
    out_path = Path(out_path) if out_path else staging_video_output_path(slug, duration_s=duration_s)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    return seg_transition.encode_video(frames_dir, fps=fps, out_path=out_path)


def export_video(slug=None, duration_s=15, fps=24):
    slug = slug or settings.SLUG
    html_path = intro_story.build(slug)
    frames_dir = staging_frame_output_dir(slug, duration_s=duration_s, fps=fps)
    capture_frames(html_path, frames_dir, duration_s=duration_s, fps=fps)
    staged_video = assemble_video_from_frames(slug, duration_s=duration_s, fps=fps, frames_dir=frames_dir)
    final_video = intro_story.video_output_path(slug, duration_s=duration_s)
    final_video.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(staged_video, final_video)
    return final_video
