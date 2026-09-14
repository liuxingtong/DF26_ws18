#!/usr/bin/env python
"""06 entrypoint: build reports, canvas views, notebooks, and seg transition frames."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "engine"))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def main(argv):
    import settings
    import build_canvas
    import build_report
    import editorial_data_film
    import export_editorial_film
    import export_intro_story
    import intro_story
    import seg_transition
    import white_film_hybrid

    if not argv:
        sites = settings.REPORT_SITES
        for site in sites:
            build_report.build(site)
        build_report.build_index(sites, None)
        return

    cmd = argv[0]
    rest = argv[1:]

    if cmd == "canvas":
        for site in (rest or settings.REPORT_SITES):
            build_canvas.build(site)
    elif cmd == "report":
        for site in (rest or settings.REPORT_SITES):
            build_report.build(site)
    elif cmd == "context":
        import ws05

        margin = getattr(settings, "CONTEXT_MARGIN_M", 800)
        for site in (rest or settings.REPORT_SITES):
            ws05.use_site(site)
            ws05.C.build_context(site, margin_m=margin)
    elif cmd == "bridge":
        if len(rest) < 2:
            sys.exit("usage: python run.py bridge <slug> <05-step-05-dir>")
        build_report.build_bridge_index(rest[0], rest[1])
    elif cmd == "notebooks":
        import _build_notebooks

        _build_notebooks.main()
    elif cmd == "seg-anim":
        slug = rest[0] if rest else settings.SLUG
        out_dir = seg_transition.render_frames(slug=slug, regimes=settings.REGIMES)
        video_path = seg_transition.encode_video(out_dir, fps=24)
        print("seg frames:", out_dir)
        print("seg video:", video_path)
    elif cmd == "seg-anim-numeric":
        slug = rest[0] if rest else settings.SLUG
        out_dir = seg_transition.render_numeric_frames(slug=slug, regimes=settings.REGIMES)
        video_path = seg_transition.encode_video(out_dir, fps=24)
        print("numeric seg frames:", out_dir)
        print("numeric seg video:", video_path)
    elif cmd == "intro":
        slug = rest[0] if rest else settings.SLUG
        path = intro_story.build(slug)
        print("intro story:", path)
    elif cmd == "intro-video":
        slug = rest[0] if rest else settings.SLUG
        video = export_intro_story.export_video(slug, duration_s=15, fps=24)
        print("intro story video:", video)
    elif cmd == "editorial-data-film":
        slug = rest[0] if rest else settings.SLUG
        path = editorial_data_film.build(slug)
        print("editorial data film:", path)
    elif cmd == "editorial-data-film-video":
        slug = rest[0] if rest else settings.SLUG
        video = export_editorial_film.export_video(slug, duration_s=10, fps=24)
        print("editorial data film video:", video)
    elif cmd == "white-film-hybrid":
        slug = rest[0] if rest else settings.SLUG
        path = white_film_hybrid.build(slug)
        print("white film hybrid:", path)
    else:
        build_report.build(cmd)


if __name__ == "__main__":
    main(sys.argv[1:])
