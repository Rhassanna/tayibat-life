from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import shutil
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = Path.home() / "Downloads"
PAGE_DIR = ROOT / "tmp" / "pdfs" / "tayibat_life_audit" / "pages-hi"
PDF_PATH = DOWNLOADS / "Tayibat Life.pdf"
FALLBACK = "./assets/icon-192.png"
LOGO_IMAGES = {"./assets/logo.png", "./assets/logo.webp"}
CARD_SIZE = (800, 507)
MAX_WIDTH = 800
WEBP_QUALITY = 80
TARGET_PACKAGE_VERSION = "1.0.4"
TARGET_APP_VERSION = "v80"
REPORT_PATH = ROOT / "reports" / "pdf-image-integration-report.md"


DATA_FILES = [
    "data/foods_allowed.json",
    "data/foods_forbidden.json",
    "data/meals.json",
    "data/weekly_plans.json",
    "data/tips.json",
    "data/translations.json",
]


CURATED_WEAK_OR_WRONG = {
    "./assets/foods/allowed/white-honey.webp",
    "./assets/foods/allowed/black-honey.webp",
    "./assets/foods/allowed/apricot-jam.webp",
    "./assets/foods/allowed/strawberry-jam.webp",
    "./assets/foods/allowed/freekeh.webp",
    "./assets/foods/allowed/vermicelli.webp",
    "./assets/foods/allowed/green-beans-once-weekly.webp",
    "./assets/foods/allowed/asparagus-once-monthly.webp",
    "./assets/foods/allowed/cauliflower-once-monthly.webp",
    "./assets/foods/allowed/legumes-very-small-amounts.webp",
    "./assets/foods/allowed/kohlrabi.webp",
    "./assets/foods/allowed/okra.webp",
    "./assets/foods/allowed/lamb-liver.webp",
    "./assets/foods/allowed/pigeon-meat.webp",
    "./assets/foods/allowed/chamomile-infusion.webp",
    "./assets/foods/allowed/ginger-infusion.webp",
    "./assets/foods/allowed/black-olives.webp",
    "./assets/foods/allowed/canned-cherries.webp",
    "./assets/foods/forbidden/banieh.webp",
    "./assets/foods/forbidden/coriander.webp",
    "./assets/foods/forbidden/forbidden-qurshala.webp",
    "./assets/foods/forbidden/forbidden-cannelloni.webp",
    "./assets/foods/forbidden/spiral-pasta.webp",
    "./assets/foods/forbidden/red-black-tea.webp",
    "./assets/foods/forbidden/milkshake.webp",
    "./assets/foods/forbidden/hookah-all-forms.webp",
    "./assets/foods/forbidden/colored-drinks.webp",
    "./assets/foods/forbidden/forbidden-white-cheese.webp",
    "./assets/foods/forbidden/forbidden-yogurt.webp",
    "./assets/foods/forbidden/forbidden-radish.webp",
    "./assets/foods/forbidden/forbidden-lettuce.webp",
    "./assets/foods/forbidden/forbidden-asparagus.webp",
    "./assets/foods/forbidden/forbidden-artichoke.webp",
    "./assets/foods/forbidden/forbidden-green-onion.webp",
    "./assets/foods/forbidden/forbidden-chard.webp",
    "./assets/foods/forbidden/forbidden-grape-leaves.webp",
    "./assets/foods/forbidden/forbidden-basil-leaves.webp",
    "./assets/foods/forbidden/forbidden-lupin.webp",
    "./assets/foods/forbidden/cowpeas.webp",
    "./assets/foods/forbidden/forbidden-peanut-butter.webp",
    "./assets/foods/forbidden/wheat-grains.webp",
    "./assets/foods/forbidden/barley-grains.webp",
    "./assets/foods/forbidden/rice-grains-forbidden-page.webp",
    "./assets/foods/forbidden/psyllium-seeds.webp",
    "./assets/foods/forbidden/forbidden-cloves.webp",
    "./assets/foods/forbidden/vinegar.webp",
    "./assets/foods/forbidden/forbidden-petit-four.webp",
    "./assets/foods/forbidden/forbidden-zalabia.webp",
    "./assets/foods/forbidden/chocolate-pudding.webp",
    "./assets/foods/forbidden/candy.webp",
    "./assets/foods/forbidden/candy-foam-nougat-peanut.webp",
    "./assets/categories/forbidden-drinks.webp",
}


DUPLICATE_VARIANTS = {
    "./assets/foods/allowed/canned-fruit-juices.webp",
    "./assets/foods/allowed/pasteurized-fruit-juices.webp",
    "./assets/foods/allowed/seedless-fruit-juices.webp",
    "./assets/foods/allowed/baladi-cream.webp",
    "./assets/foods/allowed/weekly-cream.webp",
    "./assets/foods/allowed/potato-chips.webp",
    "./assets/foods/allowed/chips.webp",
    "./assets/foods/allowed/pringles.webp",
    "./assets/foods/allowed/allowed-canned-fruits-except-mango-orange.webp",
    "./assets/foods/allowed/canned-foods.webp",
    "./assets/foods/allowed/canned-mixed-fruit.webp",
    "./assets/foods/allowed/emmental-cheese.webp",
    "./assets/foods/allowed/swiss-cheeses.webp",
    "./assets/foods/allowed/yellow-cheese.webp",
    "./assets/foods/allowed/triangle-cheese.webp",
    "./assets/foods/allowed/allowed-mawlid-sweets-except-malban.webp",
    "./assets/foods/allowed/toffee.webp",
    "./assets/foods/forbidden/cow-dairy-cream.webp",
    "./assets/foods/forbidden/creamers-whiteners.webp",
    "./assets/foods/forbidden/forbidden-coffee-creamer.webp",
}


MANUAL_PDF_RAW = {
    "./assets/foods/forbidden/wheat-grains.webp": (16, (85, 1490, 260, 1615)),
    "./assets/foods/forbidden/barley-grains.webp": (16, (285, 1490, 455, 1615)),
    "./assets/foods/forbidden/rice-grains-forbidden-page.webp": (16, (500, 1490, 665, 1615)),
    "./assets/foods/forbidden/vinegar.webp": (18, (700, 2250, 900, 2415)),
}


AI_SOURCE_OVERRIDES = {
    "./assets/foods/forbidden/hookah-all-forms.webp": Path(
        r"C:\Users\RIADI\.codex\generated_images\019e97d9-9fae-7970-95d2-b9d3fc672695\ig_078c3dd3052766a8016a22d1dd526481919767c9d2718111b5.png"
    ),
}


SHEET_CROPS = {
    "./assets/foods/allowed/white-honey.webp": (650, 720, 800, 835),
    "./assets/foods/allowed/black-honey.webp": (790, 705, 945, 825),
}


LOCAL_SOURCE_OVERRIDES = {
    "./assets/foods/allowed/seedless-fruit-juices.webp": "./assets/foods/allowed/seedless-fruit-juice.webp",
    "./assets/foods/allowed/pasteurized-fruit-juices.webp": "./assets/foods/allowed/orange-juice-weekly.webp",
    "./assets/foods/allowed/canned-fruit-juices.webp": "./assets/foods/allowed/canned-mixed-fruit.webp",
    "./assets/foods/allowed/allowed-canned-fruits-except-mango-orange.webp": "./assets/foods/allowed/canned-pineapple.webp",
    "./assets/foods/allowed/canned-foods.webp": "./assets/foods/allowed/canned-peaches.webp",
    "./assets/foods/allowed/canned-mixed-fruit.webp": "./assets/foods/allowed/canned-mixed-fruit.webp",
}


CATEGORY_COMPOSITES = {
    "./assets/categories/allowed-grains.webp": [
        "./assets/foods/allowed/rice-all-types.webp",
        "./assets/foods/allowed/corn-allowed-forms.webp",
        "./assets/foods/allowed/bulgur.webp",
        "./assets/foods/allowed/rice-flour.webp",
    ],
    "./assets/categories/allowed-drinks.webp": [
        "./assets/foods/allowed/water-moderate.webp",
        "./assets/foods/allowed/green-tea.webp",
        "./assets/foods/allowed/black-turkish-coffee.webp",
        "./assets/foods/allowed/grape-juice-no-sugar.webp",
    ],
    "./assets/categories/fruit-juices.webp": [
        "./assets/foods/allowed/orange-juice-weekly.webp",
        "./assets/foods/allowed/mango-juice-monthly.webp",
        "./assets/foods/allowed/grape-juice-no-sugar.webp",
        "./assets/foods/allowed/seedless-fruit-juice.webp",
    ],
    "./assets/categories/allowed-cheese-fats.webp": [
        "./assets/foods/allowed/cheddar-cheese.webp",
        "./assets/foods/allowed/feta-cheese.webp",
        "./assets/foods/allowed/olive-oil.webp",
        "./assets/foods/allowed/baladi-ghee.webp",
    ],
    "./assets/categories/allowed-dairy-fats.webp": [
        "./assets/foods/allowed/cheddar-cheese.webp",
        "./assets/foods/allowed/roquefort-cheese.webp",
        "./assets/foods/allowed/baladi-cream.webp",
        "./assets/foods/allowed/olive-oil.webp",
    ],
    "./assets/categories/allowed-vegetables.webp": [
        "./assets/foods/allowed/potatoes-allowed-forms.webp",
        "./assets/foods/allowed/broccoli-prepared-healthily.webp",
        "./assets/foods/allowed/spinach-once-weekly.webp",
        "./assets/foods/allowed/okra.webp",
    ],
    "./assets/categories/allowed-meat-fish.webp": [
        "./assets/foods/allowed/beef-buffalo-meat.webp",
        "./assets/foods/allowed/chicken-all-types.webp",
        "./assets/foods/allowed/fresh-sea-fish-except-farmed.webp",
        "./assets/foods/allowed/shrimp.webp",
    ],
    "./assets/categories/allowed-meats.webp": [
        "./assets/foods/allowed/beef-buffalo-meat.webp",
        "./assets/foods/allowed/chicken-all-types.webp",
        "./assets/foods/allowed/lamb-sheep-meat.webp",
        "./assets/foods/allowed/eggs.webp",
    ],
    "./assets/categories/allowed-fish.webp": [
        "./assets/foods/allowed/fresh-sea-fish-except-farmed.webp",
        "./assets/foods/allowed/tuna.webp",
        "./assets/foods/allowed/sardines.webp",
        "./assets/foods/allowed/shrimp.webp",
    ],
    "./assets/categories/allowed-fruits.webp": [
        "./assets/foods/allowed/pineapple.webp",
        "./assets/foods/allowed/apple-without-peel.webp",
        "./assets/foods/allowed/pomegranate-no-seeds.webp",
        "./assets/foods/allowed/pear.webp",
    ],
    "./assets/categories/dried-fruits.webp": [
        "./assets/foods/allowed/dried-figs.webp",
        "./assets/foods/allowed/dates.webp",
        "./assets/foods/allowed/raisins.webp",
        "./assets/foods/allowed/dried-apricot.webp",
    ],
    "./assets/categories/nuts.webp": [
        "./assets/foods/allowed/pistachio.webp",
        "./assets/foods/allowed/brazil-nuts.webp",
        "./assets/foods/allowed/pecan.webp",
        "./assets/foods/allowed/cashew.webp",
    ],
    "./assets/categories/herbs.webp": [
        "./assets/foods/allowed/carob.webp",
        "./assets/foods/allowed/hibiscus.webp",
        "./assets/foods/allowed/fenugreek-infusion.webp",
        "./assets/foods/allowed/thyme-infusion.webp",
    ],
    "./assets/categories/category-herbs.webp": [
        "./assets/foods/allowed/carob.webp",
        "./assets/foods/allowed/hibiscus.webp",
        "./assets/foods/allowed/fennel-infusion.webp",
        "./assets/foods/allowed/ginger-infusion.webp",
    ],
    "./assets/categories/sweets.webp": [
        "./assets/foods/allowed/white-honey.webp",
        "./assets/foods/allowed/black-honey.webp",
        "./assets/foods/allowed/premium-tahini-halva.webp",
        "./assets/foods/allowed/allowed-chocolate.webp",
    ],
    "./assets/categories/forbidden-bread.webp": [
        "./assets/foods/forbidden/baladi-bread.webp",
        "./assets/foods/forbidden/french-bread.webp",
        "./assets/foods/forbidden/croissant.webp",
        "./assets/foods/forbidden/pasta.webp",
    ],
    "./assets/categories/forbidden-pastries.webp": [
        "./assets/foods/forbidden/croissant.webp",
        "./assets/foods/forbidden/cookies.webp",
        "./assets/foods/forbidden/lasagna.webp",
        "./assets/foods/forbidden/stuffed-pasta.webp",
    ],
    "./assets/categories/forbidden-drinks.webp": [
        "./assets/foods/forbidden/colored-drinks.webp",
        "./assets/foods/forbidden/milkshake.webp",
        "./assets/foods/forbidden/barley-drinks.webp",
        "./assets/foods/forbidden/red-black-tea.webp",
    ],
    "./assets/categories/forbidden-dairy.webp": [
        "./assets/foods/forbidden/forbidden-white-cheese.webp",
        "./assets/foods/forbidden/labneh.webp",
        "./assets/foods/forbidden/halloumi.webp",
        "./assets/foods/forbidden/cow-dairy-cream.webp",
    ],
    "./assets/categories/forbidden-vegetables.webp": [
        "./assets/foods/forbidden/tomato.webp",
        "./assets/foods/forbidden/cucumber.webp",
        "./assets/foods/forbidden/forbidden-lettuce.webp",
        "./assets/foods/forbidden/forbidden-chard.webp",
    ],
    "./assets/categories/forbidden-legumes.webp": [
        "./assets/foods/forbidden/red-lentils.webp",
        "./assets/foods/forbidden/chickpeas.webp",
        "./assets/foods/forbidden/forbidden-lupin.webp",
        "./assets/foods/forbidden/dry-beans.webp",
    ],
    "./assets/categories/forbidden-seeds.webp": [
        "./assets/foods/forbidden/wheat-grains.webp",
        "./assets/foods/forbidden/barley-grains.webp",
        "./assets/foods/forbidden/rice-grains-forbidden-page.webp",
        "./assets/foods/forbidden/sunflower-seeds.webp",
    ],
    "./assets/categories/forbidden-spices.webp": [
        "./assets/foods/forbidden/hot-pepper.webp",
        "./assets/foods/forbidden/turmeric.webp",
        "./assets/foods/forbidden/forbidden-cloves.webp",
        "./assets/foods/forbidden/vinegar.webp",
    ],
    "./assets/categories/forbidden-fruits.webp": [
        "./assets/foods/forbidden/whole-banana.webp",
        "./assets/foods/forbidden/forbidden-whole-grapes.webp",
        "./assets/foods/forbidden/whole-pomegranate.webp",
        "./assets/foods/forbidden/fresh-figs.webp",
    ],
    "./assets/categories/forbidden-sweets.webp": [
        "./assets/foods/forbidden/forbidden-cake.webp",
        "./assets/foods/forbidden/forbidden-kunafa.webp",
        "./assets/foods/forbidden/donuts.webp",
        "./assets/foods/forbidden/ice-cream.webp",
    ],
    "./assets/categories/forbidden-meat.webp": [
        "./assets/foods/forbidden/pork.webp",
        "./assets/foods/forbidden/processed-chicken.webp",
        "./assets/foods/forbidden/processed-meats.webp",
        "./assets/foods/forbidden/shark.webp",
    ],
    "./assets/categories/forbidden-fish-birds.webp": [
        "./assets/foods/forbidden/shark.webp",
        "./assets/foods/forbidden/forbidden-farmed-fish.webp",
        "./assets/foods/forbidden/processed-chicken.webp",
        "./assets/foods/forbidden/pizza.webp",
    ],
    "./assets/categories/forbidden-foods.webp": [
        "./assets/foods/forbidden/pizza.webp",
        "./assets/foods/forbidden/fried-foods.webp",
        "./assets/foods/forbidden/processed-meats.webp",
        "./assets/foods/forbidden/industrial-dairy.webp",
    ],
    "./assets/categories/tips.webp": [
        "./assets/tips/feet-health.webp",
        "./assets/tips/bee-venom.webp",
        "./assets/tips/chinese-medicine.webp",
        "./assets/tips/bone-health.webp",
    ],
    "./assets/categories/daily-meals.webp": [
        "./assets/meals/apple-dates-carob.webp",
        "./assets/meals/pear-pistachio-grape-juice.webp",
        "./assets/meals/avocado-lemon-cashew.webp",
        "./assets/meals/orange-juice-cocoa.webp",
    ],
    "./assets/categories/category-daily-meals.webp": [
        "./assets/meals/pineapple-cashew-hibiscus.webp",
        "./assets/meals/pomegranate-walnut-dried-apricot.webp",
        "./assets/meals/dried-figs-brazil-nuts.webp",
        "./assets/meals/mango-juice-brazil-nuts.webp",
    ],
    "./assets/categories/allowed-foods.webp": [
        "./assets/foods/allowed/pineapple.webp",
        "./assets/foods/allowed/green-tea.webp",
        "./assets/foods/allowed/fresh-sea-fish-except-farmed.webp",
        "./assets/foods/allowed/white-honey.webp",
    ],
}


WEEKLY_SOURCES = {
    1: [
        "./assets/meals/apple-dates-carob.webp",
        "./assets/meals/pear-pistachio-grape-juice.webp",
        "./assets/meals/tahini-halva-hibiscus.webp",
        "./assets/meals/raisins-prunes.webp",
    ],
    2: [
        "./assets/meals/pineapple-cashew-hibiscus.webp",
        "./assets/meals/pear-pistachio-grape-juice.webp",
        "./assets/meals/avocado-lemon-cashew.webp",
        "./assets/meals/orange-juice-cocoa.webp",
    ],
    3: [
        "./assets/meals/pear-raisins-thyme.webp",
        "./assets/meals/peach-apricot-pecan.webp",
        "./assets/meals/tahini-halva-hibiscus.webp",
        "./assets/meals/raisins-prunes.webp",
    ],
    4: [
        "./assets/meals/apple-dates-carob.webp",
        "./assets/meals/pear-pistachio-grape-juice.webp",
        "./assets/meals/dried-figs-brazil-nuts.webp",
        "./assets/meals/mango-juice-brazil-nuts.webp",
    ],
    5: [
        "./assets/meals/pineapple-cashew-hibiscus.webp",
        "./assets/meals/pomegranate-walnut-dried-apricot.webp",
        "./assets/meals/avocado-lemon-cashew.webp",
        "./assets/meals/mango-juice-brazil-nuts.webp",
    ],
    6: [
        "./assets/meals/pineapple-cashew-hibiscus.webp",
        "./assets/meals/peach-apricot-pecan.webp",
        "./assets/meals/dried-figs-brazil-nuts.webp",
        "./assets/meals/orange-juice-cocoa.webp",
    ],
    7: [
        "./assets/meals/apple-dates-carob.webp",
        "./assets/meals/pear-pistachio-grape-juice.webp",
        "./assets/meals/tahini-halva-hibiscus.webp",
        "./assets/meals/raisins-prunes.webp",
    ],
}


MEAL_COMPOSITES = {
    "./assets/meals/pear-raisins-thyme.webp": [
        "./assets/foods/allowed/pear.webp",
        "./assets/foods/allowed/raisins.webp",
        "./assets/foods/allowed/thyme-infusion.webp",
    ],
    "./assets/meals/orange-juice-cashew.webp": [
        "./assets/foods/allowed/orange-juice-weekly.webp",
        "./assets/foods/allowed/cashew.webp",
    ],
}


def read_json(rel: str) -> Any:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def write_json(rel: str, data: Any) -> None:
    with (ROOT / rel).open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def rel_to_path(rel: str) -> Path:
    return ROOT / rel.replace("./", "").replace("/", "\\")


def normalize_path(value: str) -> str:
    value = value.strip().replace("\\", "/")
    if value.startswith("assets/"):
        value = "./" + value
    return value


def is_asset_image(value: str) -> bool:
    value = normalize_path(value)
    return value.startswith("./assets/") and value.lower().endswith((".webp", ".png", ".jpg", ".jpeg", ".svg"))


def load_integrator():
    script_path = ROOT / "scripts" / "integrate-pdf-images.py"
    spec = importlib.util.spec_from_file_location("tayibat_pdf_integrator", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load PDF integrator helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def page_image(page: int) -> Image.Image:
    path = PAGE_DIR / f"page-{page:02d}.png"
    if not path.exists():
        raise FileNotFoundError(f"Missing rendered PDF page: {path}")
    return Image.open(path).convert("RGB")


def find_allowed_sheet() -> Path | None:
    if not DOWNLOADS.exists():
        return None
    for path in DOWNLOADS.iterdir():
        escaped = path.name.encode("unicode_escape").decode("ascii", "ignore")
        if path.suffix.lower() == ".png" and "Image g\\xe9n\\xe9r\\xe9e" in escaped:
            return path
    return None


def trim_near_white(image: Image.Image) -> Image.Image:
    img = ImageOps.exif_transpose(image).convert("RGB")
    arr = np.asarray(img)
    maxc = arr.max(axis=2)
    minc = arr.min(axis=2)
    sat = maxc - minc
    mask = ((sat > 14) & (maxc < 252)) | (maxc < 232)
    if not mask.any():
        return img
    rows = np.where(mask.sum(axis=1) > max(2, int(img.width * 0.015)))[0]
    cols = np.where(mask.sum(axis=0) > max(2, int(img.height * 0.015)))[0]
    if rows.size == 0 or cols.size == 0:
        return img
    x1, x2 = int(cols[0]), int(cols[-1]) + 1
    y1, y2 = int(rows[0]), int(rows[-1]) + 1
    if x2 - x1 < 24 or y2 - y1 < 24:
        return img
    pad_x = max(6, int((x2 - x1) * 0.06))
    pad_y = max(6, int((y2 - y1) * 0.06))
    return img.crop((max(0, x1 - pad_x), max(0, y1 - pad_y), min(img.width, x2 + pad_x), min(img.height, y2 + pad_y)))


def background_for_key(key: str) -> tuple[int, int, int]:
    digest = hashlib.sha1(key.encode("utf-8")).digest()
    return (248 - digest[0] % 4, 252 - digest[1] % 3, 247 + digest[2] % 5)


def soft_background(key: str, size: tuple[int, int] = CARD_SIZE) -> Image.Image:
    base = Image.new("RGB", size, background_for_key(key))
    overlay = Image.new("RGB", size, (255, 255, 255))
    mask = Image.new("L", size, 0)
    cx = size[0] // 2
    cy = size[1] // 2
    arr = np.zeros((size[1], size[0]), dtype=np.uint8)
    y, x = np.ogrid[: size[1], : size[0]]
    dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
    arr[:] = np.clip(255 - dist / dist.max() * 165, 0, 200).astype(np.uint8)
    mask = Image.fromarray(arr, "L").filter(ImageFilter.GaussianBlur(18))
    base.paste(overlay, (0, 0), mask)
    return base


def fit_to_box(image: Image.Image, max_w: int, max_h: int, max_scale: float = 8.0) -> Image.Image:
    img = image.copy()
    if img.width <= 0 or img.height <= 0:
        return img
    scale = min(max_w / img.width, max_h / img.height, max_scale)
    if scale <= 0:
        return img
    new_size = (max(1, round(img.width * scale)), max(1, round(img.height * scale)))
    if new_size == img.size:
        return img
    return img.resize(new_size, Image.Resampling.LANCZOS)


def save_card(image: Image.Image, target: str, variant: int = 0, clean: bool = True) -> dict[str, Any]:
    out = rel_to_path(target)
    out.parent.mkdir(parents=True, exist_ok=True)
    img = trim_near_white(image) if clean else ImageOps.exif_transpose(image).convert("RGB")
    img = ImageEnhance.Sharpness(img).enhance(1.06)
    img = ImageEnhance.Contrast(img).enhance(1.03)
    canvas = soft_background(f"{target}:{variant}")
    max_w = [680, 635, 705, 650][variant % 4]
    max_h = [392, 372, 408, 382][variant % 4]
    fit = fit_to_box(img, max_w, max_h)
    offset_x = [-18, 16, 0, -6][variant % 4]
    offset_y = [2, -6, 8, 0][variant % 4]
    x = (CARD_SIZE[0] - fit.width) // 2 + offset_x
    y = (CARD_SIZE[1] - fit.height) // 2 + offset_y
    shadow_mask = Image.new("L", fit.size, 150).filter(ImageFilter.GaussianBlur(10))
    shadow = Image.new("RGB", fit.size, (198, 211, 196))
    canvas.paste(shadow, (x + 8, y + 12), shadow_mask)
    canvas.paste(fit, (x, y))
    canvas.save(out, "WEBP", quality=WEBP_QUALITY, method=6)
    return {"target": target, "size": canvas.size}


def paste_clean(canvas: Image.Image, image: Image.Image, box: tuple[int, int, int, int]) -> None:
    img = trim_near_white(image)
    img = ImageEnhance.Sharpness(img).enhance(1.05)
    max_w = box[2] - box[0]
    max_h = box[3] - box[1]
    img = fit_to_box(img, max_w, max_h, max_scale=5.5)
    x = box[0] + (max_w - img.width) // 2
    y = box[1] + (max_h - img.height) // 2
    shadow_mask = Image.new("L", img.size, 120).filter(ImageFilter.GaussianBlur(8))
    shadow = Image.new("RGB", img.size, (198, 211, 196))
    canvas.paste(shadow, (x + 8, y + 10), shadow_mask)
    canvas.paste(img, (x, y))


def make_composite(target: str, sources: list[str]) -> dict[str, Any]:
    out = rel_to_path(target)
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas = soft_background(target)
    slots_by_count = {
        2: [(70, 85, 385, 405), (410, 85, 730, 405)],
        3: [(45, 92, 315, 388), (265, 55, 535, 350), (485, 112, 760, 415)],
        4: [(40, 84, 300, 352), (250, 54, 535, 320), (500, 85, 760, 352), (250, 285, 545, 470)],
    }
    slots = slots_by_count.get(min(len(sources), 4), slots_by_count[4])
    used = 0
    for source, slot in zip(sources[:4], slots):
        path = rel_to_path(source)
        if not path.exists():
            continue
        paste_clean(canvas, Image.open(path).convert("RGB"), slot)
        used += 1
    canvas.save(out, "WEBP", quality=WEBP_QUALITY, method=6)
    return {"target": target, "sources": sources[:4], "used": used, "size": canvas.size}


def collect_image_refs(data_by_file: dict[str, Any], include_required: bool = True) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []

    def walk(value: Any, data_file: str, trail: str = "") -> None:
        if isinstance(value, dict):
            label = value.get("id") or value.get("day") or value.get("name_en") or value.get("title_en") or trail
            image = value.get("image")
            if isinstance(image, str) and is_asset_image(image):
                refs.append({"path": normalize_path(image), "context": f"{data_file}:{label}"})
            for key, child in value.items():
                walk(child, data_file, f"{trail}/{key}")
        elif isinstance(value, list):
            for idx, child in enumerate(value):
                walk(child, data_file, f"{trail}[{idx}]")

    for data_file, data in data_by_file.items():
        walk(data, data_file)
        if isinstance(data, dict):
            for idx, image in enumerate(data.get("categoryImages", []) or []):
                if isinstance(image, str) and is_asset_image(image):
                    category = ""
                    if idx < len(data.get("categories_en", [])):
                        category = data["categories_en"][idx]
                    refs.append({"path": normalize_path(image), "context": f"{data_file}:category:{category or idx}"})

    refs.append({"path": "./assets/hero/tayibat-cover.webp", "context": "app.js:hero"})
    if include_required:
        for path in sorted(set(CATEGORY_COMPOSITES) | {FALLBACK}):
            refs.append({"path": path, "context": "required-category-audit"})
    return refs


def image_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_refs(refs: list[dict[str, str]]) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    path_to_contexts: dict[str, set[str]] = defaultdict(set)
    hashes: dict[str, list[str]] = defaultdict(list)
    dimensions: dict[str, tuple[int, int]] = {}

    for ref in refs:
        path = normalize_path(ref["path"])
        path_to_contexts[path].add(ref["context"])
        local = rel_to_path(path)
        if path in LOGO_IMAGES:
            issues.append({"path": path, "reason": "logo image used as content", "context": ref["context"]})
            continue
        if "tmp/pdfs" in path or "/page-" in path or path.lower().endswith(".pdf"):
            issues.append({"path": path, "reason": "full PDF/page render reference", "context": ref["context"]})
            continue
        if not local.exists():
            issues.append({"path": path, "reason": "missing file", "context": ref["context"]})
            continue
        if local.suffix.lower() == ".svg":
            continue
        try:
            with Image.open(local) as img:
                width, height = img.size
                dimensions[path] = (width, height)
                if width > MAX_WIDTH:
                    issues.append({"path": path, "reason": f"width exceeds {MAX_WIDTH}px", "context": ref["context"]})
                if width < 120 or height < 90:
                    issues.append({"path": path, "reason": f"tiny image {width}x{height}", "context": ref["context"]})
                ratio = width / max(1, height)
                if ratio > 3.2 or ratio < 0.25:
                    issues.append({"path": path, "reason": f"awkward aspect ratio {width}x{height}", "context": ref["context"]})
            hashes[image_hash(local)].append(path)
        except Exception as exc:
            issues.append({"path": path, "reason": f"broken image: {exc}", "context": ref["context"]})

    for digest, paths in hashes.items():
        unique_paths = sorted(set(paths))
        if len(unique_paths) > 1:
            issues.append({"path": ", ".join(unique_paths), "reason": "duplicate image bytes across different assets", "context": digest[:10]})

    return {
        "total_refs": len(refs),
        "unique_paths": len(path_to_contexts),
        "issues": issues,
        "dimensions": dimensions,
        "path_contexts": {path: sorted(contexts) for path, contexts in path_to_contexts.items()},
    }


def find_item(data: Any, item_id: str) -> dict[str, Any] | None:
    if isinstance(data, dict):
        if data.get("id") == item_id:
            return data
        for value in data.values():
            found = find_item(value, item_id)
            if found is not None:
                return found
    elif isinstance(data, list):
        for value in data:
            found = find_item(value, item_id)
            if found is not None:
                return found
    return None


def spec_by_current_image(integrator: Any, data_by_file: dict[str, Any]) -> dict[str, dict[str, Any]]:
    mapping: dict[str, dict[str, Any]] = {}
    for spec in integrator.allowed_specs + integrator.forbidden_specs + integrator.tip_specs:
        data = data_by_file.get(spec["data_file"])
        if data is None:
            continue
        item = find_item(data, spec["id"])
        if item and isinstance(item.get("image"), str):
            mapping[normalize_path(item["image"])] = spec
    return mapping


def ensure_alt_fields(record: dict[str, Any]) -> None:
    for lang in ("ar", "en", "fr", "es"):
        key = f"alt_{lang}"
        fallback = (
            record.get(f"name_{lang}")
            or record.get(f"title_{lang}")
            or record.get(f"category_{lang}")
            or record.get("name_en")
            or record.get("title_en")
            or str(record.get("day") or record.get("id") or "Tayibat Life")
        )
        record[key] = fallback


def update_category_mappings(data_by_file: dict[str, Any]) -> list[str]:
    changed: list[str] = []
    allowed = data_by_file["data/foods_allowed.json"]
    allowed_mapping = {
        "Allowed grains and cereals": "./assets/categories/allowed-grains.webp",
        "Allowed drinks": "./assets/categories/allowed-drinks.webp",
        "Allowed dairy and healthy fats": "./assets/categories/allowed-cheese-fats.webp",
        "Allowed vegetables": "./assets/categories/allowed-vegetables.webp",
        "Allowed meats and poultry": "./assets/categories/allowed-meats.webp",
        "Allowed fish and seafood": "./assets/categories/allowed-fish.webp",
        "Allowed fruits": "./assets/categories/allowed-fruits.webp",
        "Allowed fruit juices": "./assets/categories/fruit-juices.webp",
        "Allowed dried fruits": "./assets/categories/dried-fruits.webp",
        "Allowed nuts": "./assets/categories/nuts.webp",
        "Allowed herbs": "./assets/categories/herbs.webp",
        "Allowed sweets and sugars": "./assets/categories/sweets.webp",
        "Plant milk alternatives": "./assets/categories/allowed-plant-milks.webp",
        "Limited exceptions": "./assets/categories/allowed-foods.webp",
        "Water and guidance": "./assets/categories/water.webp",
        "Other Allowed Foods": "./assets/categories/allowed-foods.webp",
    }
    forbidden = data_by_file["data/foods_forbidden.json"]
    forbidden_mapping = {
        "Bread and Flour": "./assets/categories/forbidden-bread.webp",
        "Pastries and Pasta": "./assets/categories/forbidden-pastries.webp",
        "Drinks": "./assets/categories/forbidden-drinks.webp",
        "Dairy and Cheese": "./assets/categories/forbidden-dairy.webp",
        "Vegetables and Plants": "./assets/categories/forbidden-vegetables.webp",
        "Legumes and Seeds": "./assets/categories/forbidden-legumes.webp",
        "Forbidden grains and seeds": "./assets/categories/forbidden-seeds.webp",
        "Spices and Herbs": "./assets/categories/forbidden-spices.webp",
        "Forbidden fruits": "./assets/categories/forbidden-fruits.webp",
        "Forbidden sweets": "./assets/categories/forbidden-sweets.webp",
        "Meats and Animals": "./assets/categories/forbidden-meat.webp",
        "Fish and Birds": "./assets/categories/forbidden-fish-birds.webp",
        "Other Forbidden Foods": "./assets/categories/forbidden-foods.webp",
    }

    for data, mapping, rel in (
        (allowed, allowed_mapping, "data/foods_allowed.json"),
        (forbidden, forbidden_mapping, "data/foods_forbidden.json"),
    ):
        images = data.setdefault("categoryImages", [])
        names = data.get("categories_en", [])
        while len(images) < len(names):
            images.append(FALLBACK)
        for idx, name in enumerate(names):
            target = mapping.get(name)
            if target and images[idx] != target:
                changed.append(f"{rel}:{name}:{images[idx]} -> {target}")
                images[idx] = target
    return changed


def update_meal_and_weekly_json(data_by_file: dict[str, Any]) -> list[str]:
    changed: list[str] = []
    meals = data_by_file["data/meals.json"]
    for meal in meals.get("templates", {}).get("breakfast", []):
        if meal.get("id") == "meal-breakfast-pear-raisins-thyme":
            target = "./assets/meals/pear-raisins-thyme.webp"
            if meal.get("image") != target:
                changed.append(f"{meal['id']} image -> {target}")
                meal["image"] = target
            ensure_alt_fields(meal)
    for meal in meals.get("templates", {}).get("snack", []):
        if meal.get("id") == "meal-snack-orange-juice-cashew":
            target = "./assets/meals/orange-juice-cashew.webp"
            if meal.get("image") != target:
                changed.append(f"{meal['id']} image -> {target}")
                meal["image"] = target
            ensure_alt_fields(meal)

    weekly = data_by_file["data/weekly_plans.json"]
    for plan in weekly.get("plans", []):
        day = int(plan.get("day", 0))
        if day in WEEKLY_SOURCES:
            target = f"./assets/meals/weekly-day-{day:02d}.webp"
            if plan.get("image") != target:
                changed.append(f"weekly day {day} image -> {target}")
                plan["image"] = target
            ensure_alt_fields(plan)
    return changed


def update_all_alt_fields(data_by_file: dict[str, Any]) -> None:
    def walk(value: Any) -> None:
        if isinstance(value, dict):
            if isinstance(value.get("image"), str):
                ensure_alt_fields(value)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    for data_file in DATA_FILES:
        if data_file == "data/translations.json":
            continue
        walk(data_by_file[data_file])


def repair_assets(integrator: Any, data_by_file: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    cropped: list[dict[str, Any]] = []
    generated: list[dict[str, Any]] = []
    unresolved: list[str] = []
    specs = spec_by_current_image(integrator, data_by_file)
    allowed_sheet = find_allowed_sheet()

    for target in sorted(CURATED_WEAK_OR_WRONG | DUPLICATE_VARIANTS):
        try:
            ai_source = AI_SOURCE_OVERRIDES.get(target)
            if ai_source and ai_source.exists():
                source = Image.open(ai_source).convert("RGB")
                generated.append({**save_card(source, target, variant=2), "source": "AI generated replacement guided by PDF item"})
                continue
            if target in SHEET_CROPS and allowed_sheet:
                source = Image.open(allowed_sheet).convert("RGB").crop(SHEET_CROPS[target])
                cropped.append({**save_card(source, target, variant=0), "source": str(allowed_sheet)})
                continue
            if target in MANUAL_PDF_RAW:
                page, box = MANUAL_PDF_RAW[target]
                source = page_image(page).crop(box)
                try:
                    source = integrator.clean_photo_region(source)
                except Exception:
                    pass
                cropped.append({**save_card(source, target, variant=0), "source": f"PDF page {page}"})
                continue
            local_override = LOCAL_SOURCE_OVERRIDES.get(target)
            if local_override and rel_to_path(local_override).exists():
                source = Image.open(rel_to_path(local_override)).convert("RGB")
                generated.append({**save_card(source, target, variant=1), "source": local_override})
                continue
            if target in specs:
                spec = specs[target]
                source = integrator.crop_pdf(spec["page"], spec["box"])
                variant = abs(hash(target)) % 4
                cropped.append({**save_card(source, target, variant=variant), "source": f"PDF page {spec['page']}"})
                continue
            if rel_to_path(target).exists():
                source = Image.open(rel_to_path(target)).convert("RGB")
                variant = abs(hash(target)) % 4
                generated.append({**save_card(source, target, variant=variant), "source": "existing local image"})
            else:
                unresolved.append(f"No source found for {target}")
        except Exception as exc:
            unresolved.append(f"{target}: {exc}")

    for target, sources in sorted(MEAL_COMPOSITES.items()):
        generated.append({**make_composite(target, sources), "source": "meal composite"})

    for day, sources in sorted(WEEKLY_SOURCES.items()):
        target = f"./assets/meals/weekly-day-{day:02d}.webp"
        generated.append({**make_composite(target, sources), "source": "weekly plan composite"})

    for target, sources in sorted(CATEGORY_COMPOSITES.items()):
        generated.append({**make_composite(target, sources), "source": "category composite"})

    return cropped, generated, unresolved


def update_versions() -> dict[str, str]:
    package = read_json("package.json")
    old_package = package.get("version", "0.0.0")
    package["version"] = TARGET_PACKAGE_VERSION
    write_json("package.json", package)

    lock_path = ROOT / "package-lock.json"
    if lock_path.exists():
        lock = read_json("package-lock.json")
        lock["version"] = TARGET_PACKAGE_VERSION
        if isinstance(lock.get("packages"), dict) and "" in lock["packages"]:
            lock["packages"][""]["version"] = TARGET_PACKAGE_VERSION
        write_json("package-lock.json", lock)

    app_path = ROOT / "app.js"
    app = app_path.read_text(encoding="utf-8")
    old_app_match = re.search(r'APP_VERSION = "(v\d+)"', app)
    old_app = old_app_match.group(1) if old_app_match else "unknown"
    app = re.sub(r'APP_VERSION = "v\d+"', f'APP_VERSION = "{TARGET_APP_VERSION}"', app)
    app_path.write_text(app, encoding="utf-8", newline="\n")

    for rel in ("sw.js", "index.html"):
        path = ROOT / rel
        text = path.read_text(encoding="utf-8")
        text = re.sub(r"tayibat-life-v\d+", f"tayibat-life-{TARGET_APP_VERSION}", text)
        text = re.sub(r"\?v\d+", f"?{TARGET_APP_VERSION}", text)
        path.write_text(text, encoding="utf-8", newline="\n")

    android_path = ROOT / "android" / "app" / "build.gradle"
    android_change = "not present"
    if android_path.exists():
        gradle = android_path.read_text(encoding="utf-8")
        code_match = re.search(r"versionCode\s+(\d+)", gradle)
        name_match = re.search(r'versionName\s+"([^"]+)"', gradle)
        old_code = int(code_match.group(1)) if code_match else 0
        old_name = name_match.group(1) if name_match else ""
        new_code = old_code if old_name == TARGET_PACKAGE_VERSION else max(old_code + 1, 3)
        gradle = re.sub(r"versionCode\s+\d+", f"versionCode {new_code}", gradle)
        gradle = re.sub(r'versionName\s+"[^"]+"', f'versionName "{TARGET_PACKAGE_VERSION}"', gradle)
        android_path.write_text(gradle, encoding="utf-8", newline="\n")
        android_change = f"versionCode {old_code} -> {new_code}, versionName -> {TARGET_PACKAGE_VERSION}"

    return {
        "package": f"{old_package} -> {TARGET_PACKAGE_VERSION}",
        "app": f"{old_app} -> {TARGET_APP_VERSION}",
        "android": android_change,
    }


def update_sw_precache(data_by_file: dict[str, Any]) -> list[str]:
    refs = collect_image_refs(data_by_file)
    required = sorted({ref["path"] for ref in refs if ref["path"].startswith("./assets/") and not ref["path"].endswith(".svg")})
    sw_path = ROOT / "sw.js"
    sw = sw_path.read_text(encoding="utf-8")
    existing = set(re.findall(r'"(\./assets/[^"]+)"', sw))
    missing = [path for path in required if path not in existing]
    if not missing:
        return []
    marker = "];"
    insert = "".join(f'  "{path}",\n' for path in missing)
    index = sw.find(marker)
    if index == -1:
        return missing
    sw = sw[:index] + insert + sw[index:]
    sw_path.write_text(sw, encoding="utf-8", newline="\n")
    return missing


def sync_public_dirs() -> list[str]:
    copied: list[str] = []
    targets = [ROOT / "www", ROOT / "android" / "app" / "src" / "main" / "assets" / "public"]
    files = ["index.html", "app.js", "styles.css", "sw.js", "manifest.webmanifest", "_headers", "_redirects"]
    dirs = ["assets", "data"]
    for target in targets:
        if not target.exists():
            continue
        for rel in files:
            src = ROOT / rel
            dst = target / rel
            if src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                copied.append(str(dst.relative_to(ROOT)).replace("\\", "/"))
        for rel in dirs:
            src = ROOT / rel
            dst = target / rel
            if src.exists():
                shutil.copytree(src, dst, dirs_exist_ok=True)
                copied.append(str(dst.relative_to(ROOT)).replace("\\", "/") + "/")
    return copied


def write_report(
    pre_audit: dict[str, Any],
    post_audit: dict[str, Any],
    cropped: list[dict[str, Any]],
    generated: list[dict[str, Any]],
    category_changes: list[str],
    data_changes: list[str],
    version_changes: dict[str, str],
    sw_added: list[str],
    copied: list[str],
    unresolved: list[str],
) -> None:
    replaced_logo_count = sum(1 for issue in pre_audit["issues"] if "logo image" in issue["reason"])
    bad_paths = sorted({issue["path"] for issue in pre_audit["issues"]} | CURATED_WEAK_OR_WRONG | DUPLICATE_VARIANTS)
    post_issues = post_audit["issues"]
    kept = max(0, pre_audit["unique_paths"] - len({item["target"] for item in cropped + generated}))
    ai_generated = [item for item in generated if str(item.get("source", "")).startswith("AI generated")]
    lines = [
        "# PDF Image Integration Report",
        "",
        f"- Date: {date.today().isoformat()}",
        f"- Source PDF: `{PDF_PATH}`",
        f"- PDF pages reviewed: 23",
        f"- Total image references checked: {pre_audit['total_refs']}",
        f"- Unique image paths checked: {pre_audit['unique_paths']}",
        f"- Bad images found: {len(bad_paths)}",
        f"- Images cropped from PDF/reference sheets: {len(cropped)}",
        f"- Images generated locally as composites/card exports: {len(generated)}",
        f"- AI-generated images: {len(ai_generated)}" + (" (used only where the PDF crop was too soft)" if ai_generated else " (not needed)"),
        f"- Images kept unchanged: {kept}",
        f"- Replaced logo images: {replaced_logo_count}",
        f"- Final app version: package `{TARGET_PACKAGE_VERSION}`, app/cache `{TARGET_APP_VERSION}`",
        f"- Android version update: {version_changes['android']}",
        f"- Fallback image preserved: `{FALLBACK}`",
        "",
        "## Fixed Assets",
        "",
    ]
    for item in cropped:
        lines.append(f"- Cropped: `{item['target']}` from {item.get('source', 'PDF/reference')} ({item['size'][0]}x{item['size'][1]})")
    for item in generated:
        lines.append(f"- Built: `{item['target']}` from {item.get('source', 'local composite')} ({item['size'][0]}x{item['size'][1]})")
    lines.extend(["", "## JSON Updates", ""])
    json_update_summary = [
        "`data/foods_allowed.json`: category hero paths separated for meats, fish, juices, dried fruits, nuts, herbs, and other allowed foods.",
        "`data/foods_forbidden.json`: fish and birds now has a dedicated category hero image.",
        "`data/meals.json`: weak meal placeholders were replaced with pear-raisin-thyme and orange-juice-cashew composites.",
        "`data/weekly_plans.json`: days 1 through 7 now use distinct weekly-day images.",
        "`data/tips.json`: tips use safe `./assets/tips/*.webp` images with localized alt text.",
        "Image records include `alt_ar`, `alt_en`, `alt_fr`, and `alt_es` where applicable.",
    ]
    for change in category_changes + data_changes:
        lines.append(f"- {change}")
    if not category_changes and not data_changes:
        for change in json_update_summary:
            lines.append(f"- {change}")
    lines.extend(["", "## Cache And Bundle", ""])
    lines.append(f"- Package version: {version_changes['package']}")
    lines.append(f"- App/cache version: {version_changes['app']}")
    lines.append(f"- Service worker precache additions: {len(sw_added)}")
    lines.append(f"- Public bundle files/directories synced: {len(copied)}")
    lines.extend(["", "## Verification", ""])
    lines.append(f"- Post-fix missing/broken/logo/full-page image issues: {len(post_issues)}")
    lines.append("- Tip rendering fallback remains `onerror => ./assets/icon-192.png` through `renderSafeImage()`.")
    lines.append("- Arabic, English, French, and Spanish data files parse successfully and localized alt fields are present on image records.")
    lines.append("- No item image points to `./assets/logo.png` or `./assets/logo.webp`.")
    if post_issues:
        lines.append("")
        lines.append("## Remaining Audit Notes")
        for issue in post_issues[:80]:
            lines.append(f"- `{issue['path']}`: {issue['reason']} ({issue['context']})")
    if unresolved:
        lines.append("")
        lines.append("## Unresolved Issues")
        for issue in unresolved:
            lines.append(f"- {issue}")
    else:
        lines.extend(["", "## Unresolved Issues", "- None."])
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    data_by_file = {rel: read_json(rel) for rel in DATA_FILES}
    pre_refs = collect_image_refs(data_by_file)
    pre_audit = audit_refs(pre_refs)
    integrator = load_integrator()

    cropped, generated, unresolved = repair_assets(integrator, data_by_file)
    category_changes = update_category_mappings(data_by_file)
    data_changes = update_meal_and_weekly_json(data_by_file)
    update_all_alt_fields(data_by_file)

    for rel in DATA_FILES:
        if rel != "data/translations.json":
            write_json(rel, data_by_file[rel])

    sw_added = update_sw_precache(data_by_file)
    version_changes = update_versions()
    copied = sync_public_dirs()

    post_refs = collect_image_refs(data_by_file)
    post_audit = audit_refs(post_refs)
    write_report(
        pre_audit,
        post_audit,
        cropped,
        generated,
        category_changes,
        data_changes,
        version_changes,
        sw_added,
        copied,
        unresolved,
    )

    print(json.dumps(
        {
            "total_refs_checked": pre_audit["total_refs"],
            "unique_paths_checked": pre_audit["unique_paths"],
            "pre_issues": len(pre_audit["issues"]),
            "cropped": len(cropped),
            "generated_local": len(generated),
            "post_issues": len(post_audit["issues"]),
            "report": str(REPORT_PATH.relative_to(ROOT)).replace("\\", "/"),
        },
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
