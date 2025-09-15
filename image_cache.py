# image_utils.py
import os
import requests
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QSize, QStandardPaths, Qt

from PIL import Image
from io import BytesIO

_cache_dir = os.path.join(
    "product_images"
)
os.makedirs(_cache_dir, exist_ok=True)

def get_cached_image(product_id: str, url: str, size: QSize | None = None):
    if not product_id:
        print("Nema product_id")
        return QPixmap()

    file_path = os.path.join(_cache_dir, f"{product_id}.png")

    if not os.path.exists(file_path):
        try:
            print(f"[DEBUG] Skidam sliku: {url}")
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            print(f"[DEBUG] HTTP status: {resp.status_code}")

            from PIL import Image
            from io import BytesIO

            img = Image.open(BytesIO(resp.content)).convert("RGBA")
            print(f"[DEBUG] Format pre konverzije: {img.format}")
            img.save(file_path, format="PNG")
            print(f"[DEBUG] Sačuvano kao: {file_path}")

        except Exception as e:
            print(f"[GREŠKA] {e}")
            return QPixmap()

    pm = QPixmap(file_path)
    if pm.isNull():
        print(f"[GREŠKA] QPixmap nije uspeo da učita: {file_path}")

    if not pm.isNull() and size and not size.isEmpty():
        pm = pm.scaled(size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    return pm
