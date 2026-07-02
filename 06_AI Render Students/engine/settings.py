# settings.py —— 06 總開關讀取器。使用者改 config.yaml。
# 把 config.yaml 的值讀成模組屬性(SLUG/REPORT_SITES/REGIMES/MODEL/CAM/...)供 engine `import settings` 用。
# 命名 settings 而非 config,避免和 05 的 config.py 撞名。
import yaml
from pathlib import Path

HERE = Path(__file__).resolve().parent          # engine/
ROOT = HERE.parent                               # 06 根(config.yaml/out/web)
_cfg = yaml.safe_load(open(ROOT / "config.yaml", encoding="utf-8"))

SLUG = _cfg["site"]                                    # 單站預設
REPORT_SITES = _cfg["report_sites"]                    # 批量站點清單
REGIMES = _cfg["regimes"]                              # 權力體制(05 regimes.yaml key)
COUNTERFACTUAL_SCENARIOS = _cfg.get("counterfactual_scenarios", [])  # 反事實高度情景(05 power_scenarios.yaml key)
MODEL = _cfg["model"]                                  # AI 圖像模型(Replicate)
CAM = {"elev": _cfg["camera"]["elev"], "azim": _cfg["camera"]["azim"]}   # 固定機位
MASSING_DPI = _cfg["massing_dpi"]                      # 體塊參考圖 dpi
STUDY_FRAC = _cfg.get("study_frac", 0.5)               # 已停用(舊版中心矩形);保留避免 KeyError
CONTEXT_MARGIN_M = _cfg.get("context_margin_m", 800)   # 周邊語境環寬(米):study 街區外擴多少米當透明語境
WS05 = (ROOT / _cfg["ws05_dir"]).resolve()             # 依賴 05 資料夾

PROMPTS = _cfg["prompts"]                              # 提示詞論述層(prompt_gen 讀)
