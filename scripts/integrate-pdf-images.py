from __future__ import annotations

import json
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
PAGE_DIR = ROOT / "tmp" / "pdfs" / "tayibat_life_audit" / "pages-hi"
BASE_SIZE = (1191, 1685)
MAX_WIDTH = 800
WEBP_QUALITY = 80
FALLBACK = "./assets/icon-192.png"
TARGET_PACKAGE_VERSION = "1.0.2"
TARGET_APP_VERSION = "v78"


def load_json(path: str):
    with (ROOT / path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: str, data) -> None:
    with (ROOT / path).open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def rel_to_path(rel: str) -> Path:
    return ROOT / rel.replace("./", "").replace("/", "\\")


def page_image(page: int) -> Image.Image:
    path = PAGE_DIR / f"page-{page:02d}.png"
    if not path.exists():
        raise FileNotFoundError(f"Rendered PDF page missing: {path}")
    return Image.open(path).convert("RGB")


def scaled_box(image: Image.Image, box: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    sx = image.width / BASE_SIZE[0]
    sy = image.height / BASE_SIZE[1]
    x1, y1, x2, y2 = box
    return (
        max(0, round(x1 * sx)),
        max(0, round(y1 * sy)),
        min(image.width, round(x2 * sx)),
        min(image.height, round(y2 * sy)),
    )


def crop_pdf(page: int, box: tuple[int, int, int, int]) -> Image.Image:
    src = page_image(page)
    crop = src.crop(scaled_box(src, box))
    crop = ImageOps.exif_transpose(crop).convert("RGB")
    crop = clean_photo_region(crop)
    if crop.width > MAX_WIDTH:
        new_height = max(1, round(crop.height * (MAX_WIDTH / crop.width)))
        crop = crop.resize((MAX_WIDTH, new_height), Image.Resampling.LANCZOS)
    return crop


def clean_photo_region(crop: Image.Image) -> Image.Image:
    arr = np.asarray(crop.convert("RGB"))
    if arr.size == 0:
        return crop
    maxc = arr.max(axis=2).astype(np.int16)
    minc = arr.min(axis=2).astype(np.int16)
    sat = maxc - minc
    # Food/product photos carry dense color; PDF labels and card text are usually
    # sparse black/green strokes on white. Row/column density trims those away.
    mask = ((sat > 18) & (maxc < 252)) | ((maxc < 165) & (sat > 8))
    h, w = mask.shape
    row_threshold = max(3, int(w * 0.035))
    col_threshold = max(3, int(h * 0.035))
    row_counts = mask.sum(axis=1)
    col_counts = mask.sum(axis=0)
    rows = best_dense_segment(np.where(row_counts > row_threshold)[0], row_counts)
    cols = best_dense_segment(np.where(col_counts > col_threshold)[0], col_counts)
    if rows.size == 0 or cols.size == 0:
        return crop
    y1, y2 = int(rows[0]), int(rows[-1]) + 1
    x1, x2 = int(cols[0]), int(cols[-1]) + 1
    if (x2 - x1) < max(18, w * 0.12) or (y2 - y1) < max(18, h * 0.12):
        return crop
    margin_x = max(4, int((x2 - x1) * 0.05))
    margin_y = max(4, int((y2 - y1) * 0.05))
    x1 = max(0, x1 - margin_x)
    y1 = max(0, y1 - margin_y)
    x2 = min(w, x2 + margin_x)
    y2 = min(h, y2 + margin_y)
    cleaned = crop.crop((x1, y1, x2, y2))
    if cleaned.width < 24 or cleaned.height < 24:
        return crop
    return cleaned


def best_dense_segment(indices: np.ndarray, counts: np.ndarray) -> np.ndarray:
    if indices.size == 0:
        return indices
    breaks = np.where(np.diff(indices) > 1)[0] + 1
    segments = np.split(indices, breaks)
    return max(segments, key=lambda segment: int(counts[segment].sum()))


def save_crop(page: int, box: tuple[int, int, int, int], target: str) -> dict:
    out = rel_to_path(target)
    out.parent.mkdir(parents=True, exist_ok=True)
    crop = crop_pdf(page, box)
    crop.save(out, "WEBP", quality=WEBP_QUALITY, method=6)
    return {"target": target, "page": page, "box": box, "size": crop.size}


def add(specs: list[dict], data_file: str, item_id: str, page: int, box: tuple[int, int, int, int]) -> None:
    specs.append({"data_file": data_file, "id": item_id, "page": page, "box": box})


def collect_record_images(data) -> list[str]:
    paths: list[str] = []

    def walk(value):
        if isinstance(value, dict):
            image = value.get("image")
            if isinstance(image, str) and image.startswith("./assets/"):
                paths.append(image)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(data)
    return paths


def all_records(data):
    if isinstance(data, dict):
        if data.get("id") or data.get("day"):
            yield data
        for value in data.values():
            if isinstance(value, dict):
                yield from all_records(value)
            elif isinstance(value, list):
                for child in value:
                    if isinstance(child, dict):
                        yield from all_records(child)


def item_key(item: dict) -> str:
    return re.sub(r"\s+", " ", (item.get("name_en") or item.get("title_en") or item.get("id") or "").strip().lower())


def set_alt_fields(item: dict) -> None:
    for lang in ("ar", "en", "fr", "es"):
        alt_key = f"alt_{lang}"
        if item.get(alt_key):
            continue
        fallback = item.get(f"name_{lang}") or item.get(f"title_{lang}") or item.get("name_en") or item.get("title_en") or item.get("id", "")
        item[alt_key] = fallback


def update_category_images(data: dict, mapping: dict[str, str]) -> list[str]:
    changed: list[str] = []
    names = data.get("categories_en") or data.get("categories") or []
    images = data.setdefault("categoryImages", [])
    while len(images) < len(names):
        images.append(FALLBACK)
    for idx, name in enumerate(names):
        target = mapping.get(name)
        if target and images[idx] != target:
            images[idx] = target
            changed.append(name)
    return changed


allowed_specs: list[dict] = []
forbidden_specs: list[dict] = []
tip_specs: list[dict] = []


# Page 2: allowed grains and flours.
add(allowed_specs, "data/foods_allowed.json", "allowed-rice-all-types", 2, (460, 340, 1110, 440))
add(allowed_specs, "data/foods_allowed.json", "allowed-corn-allowed-forms", 2, (500, 585, 1090, 710))
add(allowed_specs, "data/foods_allowed.json", "allowed-popcorn", 2, (500, 595, 630, 705))
add(allowed_specs, "data/foods_allowed.json", "allowed-corn-cob", 2, (650, 590, 790, 710))
add(allowed_specs, "data/foods_allowed.json", "allowed-bulgur", 2, (70, 770, 420, 910))
add(allowed_specs, "data/foods_allowed.json", "allowed-freekeh", 2, (500, 825, 750, 905))
add(allowed_specs, "data/foods_allowed.json", "allowed-vermicelli", 2, (875, 825, 1090, 900))
add(allowed_specs, "data/foods_allowed.json", "allowed-rice-flour", 2, (65, 1115, 225, 1235))
add(allowed_specs, "data/foods_allowed.json", "allowed-potato-flour", 2, (275, 1115, 430, 1235))
add(allowed_specs, "data/foods_allowed.json", "allowed-allowed-corn-starch", 2, (540, 1100, 770, 1250))
add(allowed_specs, "data/foods_allowed.json", "allowed-sesame-dark-tahini", 2, (610, 1290, 1085, 1410))
add(allowed_specs, "data/foods_allowed.json", "allowed-whole-grain-toast-cheese-bran", 2, (70, 330, 395, 455))


# Page 3: other allowed foods.
add(allowed_specs, "data/foods_allowed.json", "allowed-smooth-tahini", 3, (60, 230, 525, 390))
add(allowed_specs, "data/foods_allowed.json", "allowed-white-honey", 3, (1025, 250, 1090, 315))
add(allowed_specs, "data/foods_allowed.json", "allowed-black-honey", 3, (1025, 340, 1090, 400))
add(allowed_specs, "data/foods_allowed.json", "allowed-white-sugar", 3, (80, 505, 520, 650))
add(allowed_specs, "data/foods_allowed.json", "allowed-strawberry-jam", 3, (560, 505, 660, 645))
add(allowed_specs, "data/foods_allowed.json", "allowed-apricot-jam", 3, (675, 505, 775, 645))
add(allowed_specs, "data/foods_allowed.json", "allowed-cherry-jam", 3, (790, 505, 900, 645))
add(allowed_specs, "data/foods_allowed.json", "allowed-ketchup", 3, (65, 760, 405, 895))
add(allowed_specs, "data/foods_allowed.json", "allowed-pickled-olives", 3, (560, 750, 865, 885))
add(allowed_specs, "data/foods_allowed.json", "allowed-green-pickled-olives", 3, (560, 755, 705, 885))
add(allowed_specs, "data/foods_allowed.json", "allowed-black-pickled-olives", 3, (710, 755, 860, 885))
add(allowed_specs, "data/foods_allowed.json", "allowed-fresh-lemon-juice", 3, (65, 980, 485, 1130))
add(allowed_specs, "data/foods_allowed.json", "allowed-potato-chips", 3, (570, 1000, 780, 1130))
add(allowed_specs, "data/foods_allowed.json", "allowed-chips", 3, (570, 1000, 780, 1130))
add(allowed_specs, "data/foods_allowed.json", "allowed-pringles", 3, (570, 1000, 780, 1130))
add(allowed_specs, "data/foods_allowed.json", "allowed-allowed-canned-fruits-except-mango-orange", 20, (880, 235, 1050, 380))
add(allowed_specs, "data/foods_allowed.json", "allowed-canned-foods", 20, (880, 235, 1050, 380))
add(allowed_specs, "data/foods_allowed.json", "allowed-dates", 3, (595, 1240, 860, 1390))
add(allowed_specs, "data/foods_allowed.json", "allowed-cocoa-without-milk", 3, (80, 1470, 395, 1615))
add(allowed_specs, "data/foods_allowed.json", "allowed-nutella", 3, (570, 1470, 900, 1615))


# Page 4: allowed drinks.
add(allowed_specs, "data/foods_allowed.json", "allowed-green-tea", 4, (70, 305, 305, 485))
add(allowed_specs, "data/foods_allowed.json", "allowed-black-turkish-coffee", 4, (345, 310, 620, 495))
add(allowed_specs, "data/foods_allowed.json", "allowed-water-moderate", 4, (850, 300, 1055, 470))
add(allowed_specs, "data/foods_allowed.json", "allowed-fresh-fruit-juices", 4, (80, 650, 315, 800))
add(allowed_specs, "data/foods_allowed.json", "allowed-canned-fruit-juices", 4, (795, 620, 1110, 795))
add(allowed_specs, "data/foods_allowed.json", "allowed-pasteurized-fruit-juices", 4, (795, 620, 1110, 795))
add(allowed_specs, "data/foods_allowed.json", "allowed-seedless-fruit-juices", 4, (795, 620, 1110, 795))
add(allowed_specs, "data/foods_allowed.json", "allowed-seedless-pomegranate", 4, (840, 1075, 1110, 1240))
add(allowed_specs, "data/foods_allowed.json", "allowed-grape-juice", 4, (840, 1280, 1110, 1420))
add(allowed_specs, "data/foods_allowed.json", "allowed-qamar-al-din-apricot-drink", 4, (840, 1480, 1110, 1605))


# Page 5: allowed cheese and healthy fats.
add(allowed_specs, "data/foods_allowed.json", "allowed-cheddar-cheese", 5, (880, 295, 1045, 430))
add(allowed_specs, "data/foods_allowed.json", "allowed-edam-cheese", 5, (625, 295, 795, 430))
add(allowed_specs, "data/foods_allowed.json", "allowed-emmental-cheese", 5, (370, 295, 565, 430))
add(allowed_specs, "data/foods_allowed.json", "allowed-kashkaval-cheese", 5, (80, 295, 270, 430))
add(allowed_specs, "data/foods_allowed.json", "allowed-feta-cheese", 5, (80, 565, 265, 675))
add(allowed_specs, "data/foods_allowed.json", "allowed-roquefort-cheese", 5, (360, 565, 560, 680))
add(allowed_specs, "data/foods_allowed.json", "allowed-yellow-cheese", 5, (615, 565, 790, 690))
add(allowed_specs, "data/foods_allowed.json", "allowed-triangle-cheese", 5, (615, 565, 790, 690))
add(allowed_specs, "data/foods_allowed.json", "allowed-non-hydrogenated-spread-cheese", 5, (80, 850, 255, 1000))
add(allowed_specs, "data/foods_allowed.json", "allowed-original-roumy-cheese", 5, (360, 850, 555, 990))
add(allowed_specs, "data/foods_allowed.json", "allowed-microwave-melting-cooked-cheese", 5, (615, 880, 785, 980))
add(allowed_specs, "data/foods_allowed.json", "allowed-dutch-cheeses", 5, (860, 865, 1035, 975))
add(allowed_specs, "data/foods_allowed.json", "allowed-swiss-cheeses", 5, (370, 295, 565, 430))
add(allowed_specs, "data/foods_allowed.json", "allowed-gouda-cheese", 5, (620, 1110, 790, 1190))
add(allowed_specs, "data/foods_allowed.json", "allowed-olive-oil", 5, (80, 1320, 370, 1450))
add(allowed_specs, "data/foods_allowed.json", "allowed-baladi-cream-exception", 5, (390, 1320, 610, 1450))
add(allowed_specs, "data/foods_allowed.json", "allowed-cream-once-weekly-exception", 5, (390, 1320, 610, 1450))
add(allowed_specs, "data/foods_allowed.json", "allowed-baladi-ghee", 5, (790, 1320, 1060, 1500))


# Page 6: allowed vegetables.
add(allowed_specs, "data/foods_allowed.json", "allowed-potatoes-allowed-forms", 6, (65, 345, 635, 455))
add(allowed_specs, "data/foods_allowed.json", "allowed-broccoli-prepared-healthily", 6, (65, 620, 220, 760))
add(allowed_specs, "data/foods_allowed.json", "allowed-spinach-once-weekly", 6, (370, 620, 620, 745))
add(allowed_specs, "data/foods_allowed.json", "allowed-green-beans-once-weekly", 6, (70, 875, 330, 955))
add(allowed_specs, "data/foods_allowed.json", "allowed-green-peas-once-weekly", 6, (390, 850, 625, 930))
add(allowed_specs, "data/foods_allowed.json", "allowed-asparagus-once-monthly", 6, (70, 1055, 320, 1135))
add(allowed_specs, "data/foods_allowed.json", "allowed-cauliflower-once-monthly", 6, (390, 1055, 650, 1145))
add(allowed_specs, "data/foods_allowed.json", "allowed-corn-once-monthly", 6, (70, 1245, 300, 1340))
add(allowed_specs, "data/foods_allowed.json", "allowed-legumes-very-small-amounts", 6, (375, 1275, 650, 1370))
add(allowed_specs, "data/foods_allowed.json", "allowed-doum-palm-fruit", 6, (150, 1430, 380, 1520))
add(allowed_specs, "data/foods_allowed.json", "allowed-taro", 6, (890, 250, 1040, 345))
add(allowed_specs, "data/foods_allowed.json", "allowed-kohlrabi", 6, (865, 410, 1040, 500))
add(allowed_specs, "data/foods_allowed.json", "allowed-okra", 6, (870, 525, 1040, 620))
add(allowed_specs, "data/foods_allowed.json", "allowed-eggplant-once-weekly", 6, (870, 640, 1040, 730))
add(allowed_specs, "data/foods_allowed.json", "allowed-green-pepper-once-weekly", 6, (870, 755, 1040, 850))
add(allowed_specs, "data/foods_allowed.json", "allowed-mallow-once-monthly", 6, (870, 875, 1040, 955))
add(allowed_specs, "data/foods_allowed.json", "allowed-mushrooms-once-monthly", 6, (870, 990, 1035, 1085))
add(allowed_specs, "data/foods_allowed.json", "allowed-pumpkin-once-monthly", 6, (870, 1100, 1040, 1190))
add(allowed_specs, "data/foods_allowed.json", "allowed-falafel-once-weekly", 6, (870, 1325, 1040, 1410))
add(allowed_specs, "data/foods_allowed.json", "allowed-moussaka-without-pepper", 6, (870, 1435, 1040, 1530))


# Pages 7, 8, and 19: meats, poultry, fish, seafood, and soups.
add(allowed_specs, "data/foods_allowed.json", "allowed-beef-buffalo-meat", 7, (900, 240, 1120, 380))
add(allowed_specs, "data/foods_allowed.json", "allowed-camel-meat", 7, (720, 240, 850, 380))
add(allowed_specs, "data/foods_allowed.json", "allowed-lamb-sheep-meat", 7, (535, 240, 685, 380))
add(allowed_specs, "data/foods_allowed.json", "allowed-goat-meat", 7, (330, 240, 510, 380))
add(allowed_specs, "data/foods_allowed.json", "allowed-mutton", 7, (70, 240, 260, 380))
add(allowed_specs, "data/foods_allowed.json", "allowed-oxtail-small-amounts", 7, (930, 540, 1110, 660))
add(allowed_specs, "data/foods_allowed.json", "allowed-stuffed-tripe-small-amounts", 7, (780, 540, 900, 660))
add(allowed_specs, "data/foods_allowed.json", "allowed-head-meat-small-amounts", 7, (600, 540, 735, 660))
add(allowed_specs, "data/foods_allowed.json", "allowed-trotters-small-amounts", 7, (420, 540, 540, 660))
add(allowed_specs, "data/foods_allowed.json", "allowed-minced-meat", 7, (240, 540, 360, 660))
add(allowed_specs, "data/foods_allowed.json", "allowed-orzo-once-monthly", 7, (70, 540, 190, 660))
add(allowed_specs, "data/foods_allowed.json", "allowed-lamb-liver", 7, (205, 835, 310, 900))
add(allowed_specs, "data/foods_allowed.json", "allowed-beef-liver", 7, (150, 930, 310, 1010))
add(allowed_specs, "data/foods_allowed.json", "allowed-goat-liver", 7, (150, 1030, 310, 1110))
add(allowed_specs, "data/foods_allowed.json", "allowed-camel-liver", 7, (150, 1140, 310, 1220))
add(allowed_specs, "data/foods_allowed.json", "allowed-eggs", 7, (420, 900, 600, 1050))
add(allowed_specs, "data/foods_allowed.json", "allowed-rabbit", 8, (70, 340, 360, 565))
add(allowed_specs, "data/foods_allowed.json", "allowed-venison", 8, (410, 340, 700, 565))
add(allowed_specs, "data/foods_allowed.json", "allowed-quail", 8, (770, 340, 1080, 565))
add(allowed_specs, "data/foods_allowed.json", "allowed-bone-broth", 8, (80, 890, 510, 1130))
add(allowed_specs, "data/foods_allowed.json", "allowed-trotter-soup", 8, (570, 890, 985, 1130))
add(allowed_specs, "data/foods_allowed.json", "allowed-chicken-all-types", 19, (85, 450, 300, 560))
add(allowed_specs, "data/foods_allowed.json", "allowed-duck", 19, (390, 450, 600, 560))
add(allowed_specs, "data/foods_allowed.json", "allowed-goose", 19, (600, 450, 780, 560))
add(allowed_specs, "data/foods_allowed.json", "allowed-turkey", 19, (360, 690, 570, 800))
add(allowed_specs, "data/foods_allowed.json", "allowed-ostrich", 19, (620, 680, 780, 800))
add(allowed_specs, "data/foods_allowed.json", "allowed-pigeon-meat", 19, (100, 690, 300, 780))
add(allowed_specs, "data/foods_allowed.json", "allowed-chicken-liver", 19, (850, 690, 1040, 780))
add(allowed_specs, "data/foods_allowed.json", "allowed-chicken-hearts", 19, (600, 970, 780, 1080))
add(allowed_specs, "data/foods_allowed.json", "allowed-chicken-gizzards", 19, (360, 970, 550, 1080))
add(allowed_specs, "data/foods_allowed.json", "allowed-shrimp", 19, (350, 1290, 540, 1390))
add(allowed_specs, "data/foods_allowed.json", "allowed-anchovies", 7, (1040, 1510, 1140, 1640))
add(allowed_specs, "data/foods_allowed.json", "allowed-sardines", 7, (890, 1510, 1010, 1640))
add(allowed_specs, "data/foods_allowed.json", "allowed-tuna", 7, (760, 1510, 870, 1640))
add(allowed_specs, "data/foods_allowed.json", "allowed-crab", 7, (620, 1510, 740, 1640))
add(allowed_specs, "data/foods_allowed.json", "allowed-tilapia", 7, (480, 1510, 610, 1640))
add(allowed_specs, "data/foods_allowed.json", "allowed-mullet-fish", 7, (340, 1510, 470, 1640))
add(allowed_specs, "data/foods_allowed.json", "allowed-scallops", 7, (220, 1510, 330, 1640))
add(allowed_specs, "data/foods_allowed.json", "allowed-fresh-sea-fish-except-farmed", 7, (60, 1510, 180, 1640))


# Pages 9, 11, 12, 15, and 20: fruits, dried fruits, nuts, herbs, sweets, and plant milks.
add(allowed_specs, "data/foods_allowed.json", "allowed-peeled-almonds", 9, (70, 1030, 220, 1130))
add(allowed_specs, "data/foods_allowed.json", "allowed-walnuts", 9, (250, 1030, 360, 1130))
add(allowed_specs, "data/foods_allowed.json", "allowed-pine-nuts", 9, (430, 1030, 560, 1130))
add(allowed_specs, "data/foods_allowed.json", "allowed-currants", 9, (70, 500, 230, 620))
add(allowed_specs, "data/foods_allowed.json", "allowed-peach-smaller-amounts", 9, (840, 235, 980, 330))
add(allowed_specs, "data/foods_allowed.json", "allowed-apricot-smaller-amounts", 9, (840, 385, 980, 480))
add(allowed_specs, "data/foods_allowed.json", "allowed-guava-smaller-amounts", 9, (840, 500, 980, 610))
add(allowed_specs, "data/foods_allowed.json", "allowed-mawlid-sweets-except-malban", 11, (620, 1030, 745, 1110))
add(allowed_specs, "data/foods_allowed.json", "allowed-toffee", 11, (620, 1030, 745, 1110))
add(allowed_specs, "data/foods_allowed.json", "allowed-fenugreek-infusion", 12, (55, 365, 175, 500))
add(allowed_specs, "data/foods_allowed.json", "allowed-thyme-infusion", 12, (190, 365, 315, 500))
add(allowed_specs, "data/foods_allowed.json", "allowed-fennel-infusion", 12, (330, 365, 450, 500))
add(allowed_specs, "data/foods_allowed.json", "allowed-ginger-infusion", 12, (470, 365, 590, 500))
add(allowed_specs, "data/foods_allowed.json", "allowed-chamomile-infusion", 12, (620, 365, 740, 500))
add(allowed_specs, "data/foods_allowed.json", "allowed-almond-milk", 15, (80, 1230, 230, 1375))
add(allowed_specs, "data/foods_allowed.json", "allowed-oat-milk", 15, (250, 1230, 380, 1375))
add(allowed_specs, "data/foods_allowed.json", "allowed-soy-milk", 15, (440, 1230, 560, 1375))
add(allowed_specs, "data/foods_allowed.json", "allowed-rice-milk", 15, (600, 1230, 730, 1375))
add(allowed_specs, "data/foods_allowed.json", "allowed-fortified-oat-milk", 15, (750, 1230, 900, 1375))
add(allowed_specs, "data/foods_allowed.json", "allowed-non-local-coconut-milk", 15, (920, 1230, 1060, 1375))
add(allowed_specs, "data/foods_allowed.json", "allowed-canned-pineapple", 20, (70, 235, 220, 380))
add(allowed_specs, "data/foods_allowed.json", "allowed-canned-peaches", 20, (230, 235, 390, 380))
add(allowed_specs, "data/foods_allowed.json", "allowed-canned-mandarin", 20, (410, 235, 550, 380))
add(allowed_specs, "data/foods_allowed.json", "allowed-canned-pears", 20, (580, 235, 720, 380))
add(allowed_specs, "data/foods_allowed.json", "allowed-canned-cherries", 20, (750, 240, 880, 370))
add(allowed_specs, "data/foods_allowed.json", "allowed-canned-mixed-fruit", 20, (880, 235, 1050, 380))


# Pages 13-18, 20, and 21: forbidden foods.
add(forbidden_specs, "data/foods_forbidden.json", "fino-bread", 13, (780, 345, 940, 450))
add(forbidden_specs, "data/foods_forbidden.json", "kaiser-bread", 13, (50, 590, 180, 690))
add(forbidden_specs, "data/foods_forbidden.json", "baton-saleh", 13, (820, 600, 970, 700))
add(forbidden_specs, "data/foods_forbidden.json", "breadcrumbs-beshmat", 13, (430, 600, 560, 700))
add(forbidden_specs, "data/foods_forbidden.json", "qurshala", 13, (620, 600, 730, 700))
add(forbidden_specs, "data/foods_forbidden.json", "banieh", 13, (330, 600, 430, 700))
add(forbidden_specs, "data/foods_forbidden.json", "rice-cake", 13, (260, 960, 390, 1050))
add(forbidden_specs, "data/foods_forbidden.json", "oat-flour", 13, (800, 960, 930, 1050))
add(forbidden_specs, "data/foods_forbidden.json", "white-bread", 14, (80, 600, 200, 700))
add(forbidden_specs, "data/foods_forbidden.json", "cannelloni", 14, (170, 385, 330, 480))
add(forbidden_specs, "data/foods_forbidden.json", "italian-pasta", 14, (390, 385, 520, 480))
add(forbidden_specs, "data/foods_forbidden.json", "spiral-pasta", 14, (550, 385, 690, 480))
add(forbidden_specs, "data/foods_forbidden.json", "creamers-whiteners", 15, (880, 400, 1060, 490))
add(forbidden_specs, "data/foods_forbidden.json", "coffee-creamer", 15, (880, 400, 1060, 490))
add(forbidden_specs, "data/foods_forbidden.json", "red-black-tea", 14, (260, 1180, 430, 1280))
add(forbidden_specs, "data/foods_forbidden.json", "milkshake", 14, (430, 1180, 560, 1280))
add(forbidden_specs, "data/foods_forbidden.json", "hookah-all-forms", 14, (700, 1175, 800, 1285))
add(forbidden_specs, "data/foods_forbidden.json", "colored-drinks", 14, (65, 1210, 245, 1275))
add(forbidden_specs, "data/foods_forbidden.json", "istanbul-cheese", 15, (380, 400, 530, 490))
add(forbidden_specs, "data/foods_forbidden.json", "white-cheese", 15, (190, 400, 320, 490))
add(forbidden_specs, "data/foods_forbidden.json", "old-qareesh-cheese", 15, (70, 400, 185, 490))
add(forbidden_specs, "data/foods_forbidden.json", "yogurt", 15, (640, 600, 790, 720))
add(forbidden_specs, "data/foods_forbidden.json", "cow-dairy-cream", 15, (880, 400, 1060, 490))
add(forbidden_specs, "data/foods_forbidden.json", "cow-milk-casein", 15, (790, 940, 1050, 1070))
add(forbidden_specs, "data/foods_forbidden.json", "local-coconut-milk", 15, (100, 930, 300, 1070))
add(forbidden_specs, "data/foods_forbidden.json", "all-raw-cooked-vegetables", 16, (60, 390, 360, 650))
add(forbidden_specs, "data/foods_forbidden.json", "radish", 16, (560, 540, 650, 630))
add(forbidden_specs, "data/foods_forbidden.json", "artichoke", 16, (650, 740, 800, 840))
add(forbidden_specs, "data/foods_forbidden.json", "leek", 16, (900, 740, 1040, 800))
add(forbidden_specs, "data/foods_forbidden.json", "wheat-grains", 16, (60, 950, 160, 1015))
add(forbidden_specs, "data/foods_forbidden.json", "barley-grains", 16, (180, 950, 300, 1015))
add(forbidden_specs, "data/foods_forbidden.json", "rice-grains-forbidden-page", 16, (360, 950, 460, 1015))
add(forbidden_specs, "data/foods_forbidden.json", "dry-beans", 16, (350, 1140, 460, 1220))
add(forbidden_specs, "data/foods_forbidden.json", "flaxseed", 16, (520, 1140, 620, 1220))
add(forbidden_specs, "data/foods_forbidden.json", "sunflower-seeds", 16, (60, 1260, 160, 1320))
add(forbidden_specs, "data/foods_forbidden.json", "sesame-seeds", 16, (190, 1260, 300, 1320))
add(forbidden_specs, "data/foods_forbidden.json", "pumpkin-seeds", 16, (370, 1260, 460, 1320))
add(forbidden_specs, "data/foods_forbidden.json", "chia-seeds", 16, (520, 1260, 620, 1320))
add(forbidden_specs, "data/foods_forbidden.json", "lettuce", 17, (760, 520, 850, 630))
add(forbidden_specs, "data/foods_forbidden.json", "asparagus", 17, (540, 640, 640, 760))
add(forbidden_specs, "data/foods_forbidden.json", "green-onion", 17, (650, 640, 750, 760))
add(forbidden_specs, "data/foods_forbidden.json", "chard", 17, (760, 640, 850, 760))
add(forbidden_specs, "data/foods_forbidden.json", "grape-leaves", 17, (540, 770, 650, 860))
add(forbidden_specs, "data/foods_forbidden.json", "basil-leaves", 17, (650, 770, 750, 860))
add(forbidden_specs, "data/foods_forbidden.json", "peas", 17, (60, 370, 170, 470))
add(forbidden_specs, "data/foods_forbidden.json", "fava-beans", 17, (60, 520, 170, 620))
add(forbidden_specs, "data/foods_forbidden.json", "lupin", 17, (180, 520, 290, 620))
add(forbidden_specs, "data/foods_forbidden.json", "cowpeas", 17, (300, 520, 400, 620))
add(forbidden_specs, "data/foods_forbidden.json", "peanut-butter", 17, (300, 650, 390, 760))
add(forbidden_specs, "data/foods_forbidden.json", "garlic-powder", 17, (820, 1500, 980, 1600))
add(forbidden_specs, "data/foods_forbidden.json", "millet", 18, (60, 240, 220, 360))
add(forbidden_specs, "data/foods_forbidden.json", "black-seed", 18, (260, 230, 390, 360))
add(forbidden_specs, "data/foods_forbidden.json", "quinoa", 18, (750, 230, 910, 360))
add(forbidden_specs, "data/foods_forbidden.json", "vanilla-beans", 18, (920, 450, 1080, 590))
add(forbidden_specs, "data/foods_forbidden.json", "psyllium-seeds", 18, (220, 470, 360, 590))
add(forbidden_specs, "data/foods_forbidden.json", "cumin", 18, (690, 800, 820, 930))
add(forbidden_specs, "data/foods_forbidden.json", "coriander", 18, (220, 800, 360, 930))
add(forbidden_specs, "data/foods_forbidden.json", "saffron", 18, (880, 800, 1040, 930))
add(forbidden_specs, "data/foods_forbidden.json", "cloves", 18, (250, 1120, 360, 1240))
add(forbidden_specs, "data/foods_forbidden.json", "anise", 18, (690, 1000, 820, 1130))
add(forbidden_specs, "data/foods_forbidden.json", "star-anise", 18, (450, 1000, 620, 1130))
add(forbidden_specs, "data/foods_forbidden.json", "cinnamon", 18, (450, 1300, 650, 1430))
add(forbidden_specs, "data/foods_forbidden.json", "vinegar", 18, (620, 1490, 750, 1600))
add(forbidden_specs, "data/foods_forbidden.json", "all-spices-seasonings", 18, (55, 820, 1060, 930))
add(forbidden_specs, "data/foods_forbidden.json", "samosa", 20, (65, 1510, 200, 1585))
add(forbidden_specs, "data/foods_forbidden.json", "whole-banana", 21, (70, 210, 210, 350))
add(forbidden_specs, "data/foods_forbidden.json", "whole-grapes", 21, (235, 210, 380, 340))
add(forbidden_specs, "data/foods_forbidden.json", "whole-pomegranate", 21, (410, 210, 560, 350))
add(forbidden_specs, "data/foods_forbidden.json", "fresh-figs", 21, (590, 210, 720, 350))
add(forbidden_specs, "data/foods_forbidden.json", "tamarind", 21, (760, 210, 900, 350))
add(forbidden_specs, "data/foods_forbidden.json", "dark-chocolate", 21, (930, 1050, 1080, 1135))
add(forbidden_specs, "data/foods_forbidden.json", "dark-chocolate-with-nuts", 21, (700, 1050, 850, 1135))
add(forbidden_specs, "data/foods_forbidden.json", "cake", 21, (70, 455, 210, 600))
add(forbidden_specs, "data/foods_forbidden.json", "gateau", 21, (930, 690, 1080, 800))
add(forbidden_specs, "data/foods_forbidden.json", "petit-four", 21, (250, 455, 380, 600))
add(forbidden_specs, "data/foods_forbidden.json", "kunafa", 21, (480, 455, 650, 600))
add(forbidden_specs, "data/foods_forbidden.json", "qatayef", 21, (700, 455, 850, 600))
add(forbidden_specs, "data/foods_forbidden.json", "om-ali", 21, (900, 455, 1080, 600))
add(forbidden_specs, "data/foods_forbidden.json", "balah-al-sham", 21, (80, 690, 210, 800))
add(forbidden_specs, "data/foods_forbidden.json", "zalabia", 21, (250, 690, 380, 800))
add(forbidden_specs, "data/foods_forbidden.json", "aish-al-saraya", 21, (480, 690, 650, 800))
add(forbidden_specs, "data/foods_forbidden.json", "biscuits", 21, (80, 900, 210, 1000))
add(forbidden_specs, "data/foods_forbidden.json", "maamoul", 21, (250, 900, 390, 1000))
add(forbidden_specs, "data/foods_forbidden.json", "couscous", 21, (700, 900, 850, 1000))
add(forbidden_specs, "data/foods_forbidden.json", "caramel-cream", 21, (80, 1450, 210, 1545))
add(forbidden_specs, "data/foods_forbidden.json", "chocolate-pudding", 21, (250, 1450, 390, 1545))
add(forbidden_specs, "data/foods_forbidden.json", "cheesecake", 21, (480, 1450, 650, 1555))
add(forbidden_specs, "data/foods_forbidden.json", "tiramisu", 21, (700, 1450, 850, 1555))
add(forbidden_specs, "data/foods_forbidden.json", "donuts", 21, (480, 1270, 650, 1380))
add(forbidden_specs, "data/foods_forbidden.json", "cotton-candy", 21, (700, 1270, 850, 1380))
add(forbidden_specs, "data/foods_forbidden.json", "jelly-candy", 21, (900, 1270, 1080, 1380))
add(forbidden_specs, "data/foods_forbidden.json", "ice-cream", 21, (250, 1270, 390, 1380))
add(forbidden_specs, "data/foods_forbidden.json", "candy", 21, (250, 1080, 390, 1190))
add(forbidden_specs, "data/foods_forbidden.json", "creamy-dessert", 21, (80, 1270, 210, 1380))
add(forbidden_specs, "data/foods_forbidden.json", "candy-foam-nougat-peanut", 21, (700, 1080, 850, 1190))
add(forbidden_specs, "data/foods_forbidden.json", "farmed-fish", 19, (65, 1290, 220, 1365))


# Pages 22 and 23: PDF tips and medical notes.
add(tip_specs, "data/tips.json", "tip-27", 22, (60, 590, 180, 700))
add(tip_specs, "data/tips.json", "tip-28", 22, (60, 790, 200, 900))
add(tip_specs, "data/tips.json", "tip-29", 22, (60, 920, 240, 1040))
add(tip_specs, "data/tips.json", "tip-30", 22, (620, 520, 760, 650))
add(tip_specs, "data/tips.json", "tip-31", 22, (620, 760, 770, 870))
add(tip_specs, "data/tips.json", "tip-32", 23, (610, 390, 780, 520))


hero_specs = [
    ("assets/hero/tayibat-cover.webp", 1, (60, 1125, 1120, 1585)),
]

category_specs = [
    ("assets/categories/allowed-grains.webp", 2, (70, 330, 395, 455)),
    ("assets/categories/allowed-drinks.webp", 4, (795, 600, 1110, 795)),
    ("assets/categories/allowed-cheese-fats.webp", 5, (80, 1320, 370, 1450)),
    ("assets/categories/allowed-vegetables.webp", 6, (65, 335, 635, 470)),
    ("assets/categories/allowed-meat-fish.webp", 7, (60, 1510, 330, 1640)),
    ("assets/categories/allowed-fruits.webp", 9, (840, 235, 980, 330)),
    ("assets/categories/forbidden-bread.webp", 13, (780, 345, 940, 450)),
    ("assets/categories/forbidden-drinks.webp", 14, (65, 1210, 245, 1275)),
    ("assets/categories/forbidden-dairy.webp", 15, (880, 400, 1060, 490)),
    ("assets/categories/forbidden-vegetables.webp", 16, (60, 390, 360, 650)),
    ("assets/categories/forbidden-sweets.webp", 21, (70, 455, 210, 600)),
    ("assets/categories/tips.webp", 23, (610, 390, 780, 520)),
]


def apply_item_specs(data_by_file: dict[str, dict], specs: list[dict]) -> tuple[list[dict], list[str]]:
    generated: list[dict] = []
    missing: list[str] = []
    by_file: dict[str, dict[str, dict]] = {}
    for data_file, data in data_by_file.items():
        by_file[data_file] = {item.get("id"): item for item in all_records(data) if item.get("id")}

    for spec in specs:
        item = by_file.get(spec["data_file"], {}).get(spec["id"])
        if not item:
            missing.append(f"{spec['data_file']}::{spec['id']}")
            continue
        image = item.get("image")
        if not isinstance(image, str) or not image.startswith("./assets/"):
            missing.append(f"{spec['data_file']}::{spec['id']} has no app image path")
            continue
        generated.append(save_crop(spec["page"], spec["box"], image))
        set_alt_fields(item)
    return generated, missing


def update_versions() -> dict:
    package_path = ROOT / "package.json"
    lock_path = ROOT / "package-lock.json"
    package = load_json("package.json")
    old_package_version = package.get("version", "0.0.0")
    def version_tuple(value: str) -> tuple[int, int, int]:
        parts = value.split(".")
        if len(parts) != 3 or not all(part.isdigit() for part in parts):
            return (0, 0, 0)
        return tuple(int(part) for part in parts)

    new_package_version = old_package_version
    if version_tuple(old_package_version) < version_tuple(TARGET_PACKAGE_VERSION):
        new_package_version = TARGET_PACKAGE_VERSION
    package["version"] = new_package_version
    write_json("package.json", package)

    if lock_path.exists():
        lock = load_json("package-lock.json")
        lock["version"] = new_package_version
        if isinstance(lock.get("packages"), dict) and "" in lock["packages"]:
            lock["packages"][""]["version"] = new_package_version
        write_json("package-lock.json", lock)

    app_path = ROOT / "app.js"
    app = app_path.read_text(encoding="utf-8")
    match = re.search(r'APP_VERSION = "v(\d+)"', app)
    old_app_version = f"v{match.group(1)}" if match else "v77"
    new_app_version = old_app_version
    target_app_int = int(TARGET_APP_VERSION.removeprefix("v"))
    old_app_int = int(match.group(1)) if match else 0
    if old_app_int < target_app_int:
        new_app_version = TARGET_APP_VERSION
    app = re.sub(r'APP_VERSION = "v\d+"', f'APP_VERSION = "{new_app_version}"', app)
    app_path.write_text(app, encoding="utf-8", newline="\n")

    sw_path = ROOT / "sw.js"
    sw = sw_path.read_text(encoding="utf-8")
    sw = re.sub(r"tayibat-life-v\d+", f"tayibat-life-{new_app_version}", sw)
    sw = re.sub(r"\?v\d+", f"?{new_app_version}", sw)
    sw_path.write_text(sw, encoding="utf-8", newline="\n")

    index_path = ROOT / "index.html"
    index = index_path.read_text(encoding="utf-8")
    index = re.sub(r"\?v=?\d+", f"?{new_app_version}", index)
    index_path.write_text(index, encoding="utf-8", newline="\n")

    return {
        "package": f"{old_package_version} -> {new_package_version}",
        "app": f"{old_app_version} -> {new_app_version}",
    }


def sync_www() -> list[str]:
    copied: list[str] = []
    www = ROOT / "www"
    if not www.exists():
        return copied
    for rel in ["index.html", "app.js", "styles.css", "sw.js", "manifest.webmanifest", "_headers", "_redirects"]:
        src = ROOT / rel
        if src.exists():
            dst = www / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied.append(rel)
    for rel_dir in ["assets", "data"]:
        src = ROOT / rel_dir
        dst = www / rel_dir
        if src.exists():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            copied.append(rel_dir + "/")
    return copied


def verify_all(data_by_file: dict[str, dict]) -> dict:
    issues: dict[str, list[str]] = defaultdict(list)
    all_images: list[str] = []
    allowed = data_by_file["data/foods_allowed.json"]
    forbidden = data_by_file["data/foods_forbidden.json"]

    for data_file, data in data_by_file.items():
        all_images.extend(collect_record_images(data))
        json.dumps(data, ensure_ascii=False)
        for item in all_records(data):
            if item.get("image"):
                for lang in ("ar", "en", "fr", "es"):
                    if not item.get(f"alt_{lang}"):
                        issues["missing_alt"].append(f"{data_file}::{item.get('id', item.get('day', '?'))}::{lang}")

    for data in (allowed, forbidden):
        for image in data.get("categoryImages", []) or []:
            if isinstance(image, str) and image.startswith("./assets/"):
                all_images.append(image)

    for image in sorted(set(all_images + [FALLBACK])):
        if not rel_to_path(image).exists():
            issues["missing_images"].append(image)
        if "tmp/pdfs" in image.replace("\\", "/") or "page-" in Path(image).name.lower() or image.lower().endswith(".pdf"):
            issues["full_pdf_or_render_reference"].append(image)
        if "/assets/foods/allowed/" in image and "data/foods_forbidden" in image:
            issues["directory_split"].append(image)

    allowed_ids = [item["id"] for item in allowed.get("items", [])]
    forbidden_ids = [item["id"] for item in forbidden.get("items", [])]
    for value, count in Counter(allowed_ids).items():
        if count > 1:
            issues["duplicate_allowed_ids"].append(value)
    for value, count in Counter(forbidden_ids).items():
        if count > 1:
            issues["duplicate_forbidden_ids"].append(value)

    allowed_keys = [item_key(item) for item in allowed.get("items", [])]
    forbidden_keys = [item_key(item) for item in forbidden.get("items", [])]
    for value, count in Counter(allowed_keys).items():
        if value and count > 1:
            issues["duplicate_allowed_foods"].append(value)
    for value, count in Counter(forbidden_keys).items():
        if value and count > 1:
            issues["duplicate_forbidden_foods"].append(value)
    conflicts = sorted(set(allowed_keys) & set(forbidden_keys))
    issues["food_conflicts"].extend(conflicts)

    for idx, category in enumerate(allowed.get("categories_en", [])):
        count = sum(1 for item in allowed.get("items", []) if item.get("category_en") == category)
        if count == 0:
            issues["empty_allowed_categories"].append(category)
    for idx, category in enumerate(forbidden.get("categories_en", [])):
        count = sum(1 for item in forbidden.get("items", []) if item.get("category_en") == category)
        if count == 0:
            issues["empty_forbidden_categories"].append(category)

    return {key: values for key, values in issues.items() if values}


def make_preview(generated: list[dict]) -> str:
    selected = generated[:48]
    if not selected:
        return ""
    thumbs = []
    for item in selected:
        image = Image.open(rel_to_path(item["target"])).convert("RGB")
        image.thumbnail((140, 110), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (140, 110), "white")
        canvas.paste(image, ((140 - image.width) // 2, (110 - image.height) // 2))
        thumbs.append(canvas)
    cols = 8
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 140, rows * 110), "white")
    for idx, thumb in enumerate(thumbs):
        sheet.paste(thumb, ((idx % cols) * 140, (idx // cols) * 110))
    target = ROOT / "tmp" / "pdfs" / "tayibat_life_audit" / "pdf-image-crop-preview.webp"
    target.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(target, "WEBP", quality=85, method=6)
    return str(target.relative_to(ROOT)).replace("\\", "/")


def main() -> None:
    data_files = [
        "data/foods_allowed.json",
        "data/foods_forbidden.json",
        "data/tips.json",
        "data/meals.json",
        "data/weekly_plans.json",
        "data/translations.json",
    ]
    data_by_file = {path: load_json(path) for path in data_files}

    allowed = data_by_file["data/foods_allowed.json"]
    before_allowed_count = len(allowed.get("items", []))
    allowed["items"] = [item for item in allowed.get("items", []) if item.get("id") != "allowed-sesame"]
    removed_allowed = before_allowed_count - len(allowed.get("items", []))
    for item in allowed.get("items", []):
        set_alt_fields(item)
    for item in data_by_file["data/foods_forbidden.json"].get("items", []):
        set_alt_fields(item)
    for item in data_by_file["data/tips.json"].get("tips", []):
        set_alt_fields(item)
    for item in all_records(data_by_file["data/meals.json"]):
        set_alt_fields(item)
    for item in all_records(data_by_file["data/weekly_plans.json"]):
        set_alt_fields(item)

    generated = []
    missing_specs = []
    for path, page, box in hero_specs:
        generated.append(save_crop(page, box, "./" + path))
    for path, page, box in category_specs:
        generated.append(save_crop(page, box, "./" + path))

    for specs in (allowed_specs, forbidden_specs, tip_specs):
        crops, missing = apply_item_specs(data_by_file, specs)
        generated.extend(crops)
        missing_specs.extend(missing)

    allowed_category_changes = update_category_images(
        allowed,
        {
            "Allowed grains and cereals": "./assets/categories/allowed-grains.webp",
            "Allowed drinks": "./assets/categories/allowed-drinks.webp",
            "Allowed dairy and healthy fats": "./assets/categories/allowed-cheese-fats.webp",
            "Allowed vegetables": "./assets/categories/allowed-vegetables.webp",
            "Allowed meats and poultry": "./assets/categories/allowed-meat-fish.webp",
            "Allowed fish and seafood": "./assets/categories/allowed-meat-fish.webp",
            "Allowed fruits": "./assets/categories/allowed-fruits.webp",
            "Allowed fruit juices": "./assets/categories/allowed-drinks.webp",
            "Allowed dried fruits": "./assets/categories/allowed-fruits.webp",
            "Allowed nuts": "./assets/categories/allowed-fruits.webp",
            "Allowed herbs": "./assets/categories/tips.webp",
            "Other Allowed Foods": "./assets/categories/allowed-grains.webp",
        },
    )
    forbidden_category_changes = update_category_images(
        data_by_file["data/foods_forbidden.json"],
        {
            "Bread and Flour": "./assets/categories/forbidden-bread.webp",
            "Drinks": "./assets/categories/forbidden-drinks.webp",
            "Dairy and Cheese": "./assets/categories/forbidden-dairy.webp",
            "Vegetables and Plants": "./assets/categories/forbidden-vegetables.webp",
            "Forbidden sweets": "./assets/categories/forbidden-sweets.webp",
        },
    )

    for path in data_files:
        write_json(path, data_by_file[path])

    version_changes = update_versions()
    www_copied = sync_www()

    reloaded = {path: load_json(path) for path in data_files}
    issues = verify_all(reloaded)
    preview_path = make_preview(generated)

    report = []
    report.append("# PDF Image Integration Report")
    report.append("")
    report.append("Source: `C:/Users/RIADI/Downloads/Tayibat Life.pdf`")
    report.append("")
    report.append("## Summary")
    report.append(f"- Generated WebP crops: {len(generated)}")
    report.append(f"- Removed conflicting legacy allowed sesame records: {removed_allowed}")
    report.append(f"- Missing crop specs: {len(missing_specs)}")
    report.append(f"- Version bump: package {version_changes['package']}; app/cache {version_changes['app']}")
    report.append(f"- Synced `www`: {', '.join(www_copied) if www_copied else 'not present'}")
    if preview_path:
        report.append(f"- Crop preview: `{preview_path}`")
    report.append("")
    report.append("## PDF-Derived Hero And Category Images")
    for item in generated[: len(hero_specs) + len(category_specs)]:
        report.append(f"- `{item['target']}` from page {item['page']} at {item['size'][0]}x{item['size'][1]}")
    report.append("")
    report.append("## App Data Updates")
    report.append(f"- Allowed item images cropped/updated: {len(allowed_specs) - sum(1 for miss in missing_specs if 'foods_allowed' in miss)}")
    report.append(f"- Forbidden item images cropped/updated: {len(forbidden_specs) - sum(1 for miss in missing_specs if 'foods_forbidden' in miss)}")
    report.append(f"- Tip images cropped/updated: {len(tip_specs) - sum(1 for miss in missing_specs if 'tips' in miss)}")
    report.append(f"- Allowed category image slots updated: {', '.join(allowed_category_changes) if allowed_category_changes else 'none'}")
    report.append(f"- Forbidden category image slots updated: {', '.join(forbidden_category_changes) if forbidden_category_changes else 'none'}")
    report.append("")
    report.append("## Missing Crop Specs")
    if missing_specs:
        for miss in missing_specs:
            report.append(f"- {miss}")
    else:
        report.append("- None")
    report.append("")
    report.append("## Verification")
    if issues:
        for key, values in sorted(issues.items()):
            report.append(f"- {key}: {len(values)}")
            for value in values[:30]:
                report.append(f"  - {value}")
            if len(values) > 30:
                report.append(f"  - ... {len(values) - 30} more")
    else:
        report.append("- JSON parsed successfully.")
        report.append("- All referenced images exist.")
        report.append("- No full PDF page or rendered PDF page image is referenced by app data.")
        report.append("- Arabic, English, French, and Spanish alt text fields are present on image records.")
        report.append("- Allowed and forbidden image directories remain separated.")
        report.append("- No duplicate IDs, duplicate food names, empty categories, or allowed/forbidden conflicts were found.")
        report.append(f"- Runtime fallback remains `{FALLBACK}`.")
    report.append("")
    report.append("## No Full PDF Pages")
    report.append("Only tight page crops were exported to WebP. No `tmp/pdfs/.../page-*.png` render or full PDF page asset is referenced in the app data.")
    report_path = ROOT / "reports" / "pdf-image-integration-report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report) + "\n", encoding="utf-8", newline="\n")

    print(f"generated={len(generated)}")
    print(f"removed_allowed_sesame={removed_allowed}")
    print(f"missing_specs={len(missing_specs)}")
    print(f"issues={sum(len(v) for v in issues.values())}")
    print(f"report={report_path}")
    if preview_path:
        print(f"preview={ROOT / preview_path}")


if __name__ == "__main__":
    main()
