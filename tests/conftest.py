"""pytest 公共配置。"""

import os
import sys
from pathlib import Path

# 必须在创建 QApplication 之前设置，测试无需真实窗口
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
