import time
from pathlib import Path

import editorial_data_film
import seg_transition
import settings


ROOT = Path(__file__).resolve().parent.parent


def capture_frame_indices(duration_s=10, fps=24):
    return list(range(duration_s * fps))


def capture_frames(page_path, frames_dir, duration_s=10, fps=24, width=1920, height=1080):
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
        for index in capture_frame_indices(duration_s=duration_s, fps=fps):
            frame_path = frames_dir / f"f{index:03d}.png"
            if frame_path.exists():
                continue
            elapsed_ms = (index / fps) * 1000
            driver.execute_script("window.__codexRenderAt(arguments[0]);", float(elapsed_ms))
            time.sleep(0.08)
            driver.save_screenshot(str(frame_path))
    finally:
        if driver is not None:
            driver.quit()
    return frames_dir


def assemble_video_from_frames(slug, duration_s=10, fps=24):
    frames_dir = editorial_data_film.frame_output_dir(slug, duration_s=duration_s, fps=fps)
    video_path = editorial_data_film.video_output_path(slug, duration_s=duration_s)
    return seg_transition.encode_video(frames_dir, fps=fps, out_path=video_path)


def export_video(slug=None, duration_s=10, fps=24):
    slug = slug or settings.SLUG
    html_path = editorial_data_film.build(slug)
    frames_dir = editorial_data_film.frame_output_dir(slug, duration_s=duration_s, fps=fps)
    capture_frames(html_path, frames_dir, duration_s=duration_s, fps=fps)
    return assemble_video_from_frames(slug, duration_s=duration_s, fps=fps)
