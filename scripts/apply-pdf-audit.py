from __future__ import annotations

from pathlib import Path
import json
import re
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "tmp" / "pdfs" / "tayibat_life_audit" / "audit_specs.json"
TODAY = "2026-06-05"
SOURCE_BOOK = "Tayibat Life.pdf"


ALLOWED_CATS = {
    "Allowed grains and cereals": ("منتجات الدقيق والحبوب المسموحة", "Allowed grains and cereals", "Céréales et farines autorisées", "Cereales y harinas permitidas"),
    "Allowed drinks": ("المشروبات المسموحة", "Allowed drinks", "Boissons autorisées", "Bebidas permitidas"),
    "Allowed dairy and healthy fats": ("منتجات الأجبان والدهون الصحية المسموحة", "Allowed dairy and healthy fats", "Produits laitiers et graisses saines autorisés", "Lácteos y grasas saludables permitidos"),
    "Allowed vegetables": ("الخضار المسموحة", "Allowed vegetables", "Légumes autorisés", "Verduras permitidas"),
    "Allowed meats and poultry": ("اللحوم والطيور المسموحة", "Allowed meats and poultry", "Viandes et volailles autorisées", "Carnes y aves permitidas"),
    "Allowed fish and seafood": ("الأسماك والمأكولات البحرية المسموحة", "Allowed fish and seafood", "Poissons et fruits de mer autorisés", "Pescados y mariscos permitidos"),
    "Allowed fruits": ("الفواكه المسموحة", "Allowed fruits", "Fruits autorisés", "Frutas permitidas"),
    "Allowed fruit juices": ("عصائر الفواكه المسموحة", "Allowed fruit juices", "Jus de fruits autorisés", "Jugos de fruta permitidos"),
    "Allowed dried fruits": ("الفواكه المجففة المسموحة", "Allowed dried fruits", "Fruits secs autorisés", "Frutas deshidratadas permitidas"),
    "Allowed nuts": ("المكسرات المسموحة", "Allowed nuts", "Noix autorisées", "Frutos secos permitidos"),
    "Allowed herbs": ("الأعشاب المسموحة", "Allowed herbs", "Herbes autorisées", "Hierbas permitidas"),
    "Allowed sweets and sugars": ("الحلويات والسكريات المسموحة", "Allowed sweets and sugars", "Douceurs et sucres autorisés", "Dulces y azúcares permitidos"),
    "Plant milk alternatives": ("بدائل الحليب النباتية", "Plant milk alternatives", "Alternatives végétales au lait", "Alternativas vegetales a la leche"),
    "Limited exceptions": ("الاستثناءات المحدودة", "Limited exceptions", "Exceptions limitées", "Excepciones limitadas"),
    "Water and guidance": ("الماء والإرشادات", "Water and guidance", "Eau et conseils", "Agua y orientación"),
}

FORBIDDEN_CATS = {
    "Bread and Flour": ("الخبز والدقيق", "Bread and Flour", "Pain et farine", "Pan y harina"),
    "Pastries and Pasta": ("المعجنات والمكرونة", "Pastries and Pasta", "Pâtisseries et pâtes", "Pastelería y pasta"),
    "Forbidden processed foods": ("المأكولات المصنعة الممنوعة", "Forbidden processed foods", "Aliments transformés interdits", "Alimentos procesados prohibidos"),
    "Drinks": ("المشروبات", "Drinks", "Boissons", "Bebidas"),
    "Dairy and Cheese": ("الألبان والأجبان", "Dairy and Cheese", "Produits laitiers et fromages", "Lácteos y quesos"),
    "Vegetables and Plants": ("الخضار والنباتات", "Vegetables and Plants", "Légumes et plantes", "Verduras y plantas"),
    "Legumes and Seeds": ("البقوليات والبذور", "Legumes and Seeds", "Légumineuses et graines", "Legumbres y semillas"),
    "Forbidden grains and seeds": ("الحبوب والبذور الممنوعة", "Forbidden grains and seeds", "Céréales et graines interdites", "Cereales y semillas prohibidos"),
    "Spices and Herbs": ("التوابل والأعشاب", "Spices and Herbs", "Épices et herbes", "Especias y hierbas"),
    "Forbidden fruits": ("الفواكه الممنوعة", "Forbidden fruits", "Fruits interdits", "Frutas prohibidas"),
    "Forbidden sweets": ("الحلويات الممنوعة", "Forbidden sweets", "Douceurs interdites", "Dulces prohibidos"),
    "Meats and Animals": ("اللحوم والحيوانات", "Meats and Animals", "Viandes et animaux", "Carnes y animales"),
    "Fish and Birds": ("الأسماك والطيور", "Fish and Birds", "Poissons et oiseaux", "Pescados y aves"),
    "Other Forbidden Foods": ("ممنوعات أخرى", "Other Forbidden Foods", "Autres aliments interdits", "Otros alimentos prohibidos"),
}

ALLOWED_CATEGORY_IMAGES = {
    "Allowed grains and cereals": "./assets/categories/allowed-grains.webp",
    "Allowed drinks": "./assets/categories/drinks.webp",
    "Allowed dairy and healthy fats": "./assets/categories/allowed-dairy-fats.webp",
    "Allowed vegetables": "./assets/categories/allowed-vegetables.webp",
    "Allowed meats and poultry": "./assets/categories/allowed-meats.webp",
    "Allowed fish and seafood": "./assets/categories/allowed-fish.webp",
    "Allowed fruits": "./assets/categories/fruits.webp",
    "Allowed fruit juices": "./assets/categories/fruit-juices.webp",
    "Allowed dried fruits": "./assets/categories/dried-fruits.webp",
    "Allowed nuts": "./assets/categories/nuts.webp",
    "Allowed herbs": "./assets/categories/herbs.webp",
    "Allowed sweets and sugars": "./assets/categories/sweets.webp",
    "Plant milk alternatives": "./assets/categories/allowed-plant-milks.webp",
    "Limited exceptions": "./assets/categories/allowed-foods.webp",
    "Water and guidance": "./assets/categories/water.webp",
}

FORBIDDEN_CATEGORY_IMAGES = {
    "Bread and Flour": "./assets/categories/forbidden-bread.webp",
    "Pastries and Pasta": "./assets/categories/forbidden-pastries.webp",
    "Forbidden processed foods": "./assets/categories/forbidden-foods.webp",
    "Drinks": "./assets/categories/forbidden-drinks.webp",
    "Dairy and Cheese": "./assets/categories/forbidden-dairy.webp",
    "Vegetables and Plants": "./assets/categories/forbidden-vegetables.webp",
    "Legumes and Seeds": "./assets/categories/forbidden-legumes.webp",
    "Forbidden grains and seeds": "./assets/categories/forbidden-seeds.webp",
    "Spices and Herbs": "./assets/categories/forbidden-spices.webp",
    "Forbidden fruits": "./assets/categories/forbidden-fruits.webp",
    "Forbidden sweets": "./assets/categories/forbidden-sweets.webp",
    "Meats and Animals": "./assets/categories/forbidden-meat.webp",
    "Fish and Birds": "./assets/categories/forbidden-meat.webp",
    "Other Forbidden Foods": "./assets/categories/forbidden-foods.webp",
}


def read_json(path: str | Path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def write_json(path: str | Path, data):
    (ROOT / path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def slugify(value: str) -> str:
    value = value.lower().replace("&", " and ").replace("+", " and ").replace("'", "")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return re.sub(r"-+", "-", value).strip("-") or "item"


def norm(value: str) -> str:
    value = (value or "").lower()
    value = re.sub(r"\([^)]*\)", "", value)
    value = re.sub(r"[^\w\u0600-\u06ff]+", " ", value, flags=re.UNICODE)
    return re.sub(r"\s+", " ", value).strip()


def rel_to_abs(rel: str) -> Path:
    return ROOT / rel.replace("./", "")


def load_font(size: int, bold: bool = False):
    names = ["arialbd.ttf", "segoeuib.ttf"] if bold else ["arial.ttf", "segoeui.ttf"]
    for name in names:
        path = Path("C:/Windows/Fonts") / name
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int):
    lines, current = [], ""
    for word in text.split():
        trial = f"{current} {word}".strip()
        if not current or draw.textbbox((0, 0), trial, font=font)[2] <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines[:3]


def generate_card(rel: str, title: str, category: str, status: str, report: dict):
    path = rel_to_abs(rel)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    width, height = 800, 507
    allowed = status == "allowed"
    top = (246, 250, 242) if allowed else (254, 246, 244)
    bottom = (226, 240, 219) if allowed else (246, 224, 220)
    accent = (31, 112, 55) if allowed else (150, 45, 40)
    image = Image.new("RGB", (width, height), top)
    pixels = image.load()
    for y in range(height):
        mix = y / (height - 1)
        color = tuple(int(top[i] * (1 - mix) + bottom[i] * mix) for i in range(3))
        for x in range(width):
            pixels[x, y] = color
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((38, 34, width - 38, height - 34), radius=32, fill=(255, 255, 250), outline=accent, width=4)
    draw.ellipse((190, 102, 610, 332), fill=(247, 240, 222), outline=(202, 181, 145), width=5)
    draw.ellipse((238, 144, 562, 298), fill=(255, 252, 238), outline=(220, 202, 168), width=3)
    cat = category.lower()
    if "drink" in cat or "juice" in cat or "milk" in cat or "water" in cat:
        draw.rounded_rectangle((345, 128, 455, 290), radius=18, fill=(187, 217, 232), outline=accent, width=4)
        draw.rectangle((358, 168, 442, 278), fill=(245, 251, 253))
    elif "meat" in cat or "fish" in cat or "poultry" in cat:
        draw.ellipse((288, 154, 512, 280), fill=(185, 82, 70), outline=accent, width=4)
        draw.ellipse((352, 184, 450, 250), fill=(238, 182, 168))
    elif "dairy" in cat or "cheese" in cat:
        draw.polygon([(302, 260), (510, 260), (510, 144)], fill=(247, 206, 85), outline=accent)
        for cx, cy, radius in [(432, 214, 12), (472, 238, 9), (398, 238, 8)]:
            draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=(255, 238, 150))
    elif "vegetable" in cat:
        for index, x in enumerate([310, 365, 420, 475]):
            draw.ellipse((x, 150 + (index % 2) * 20, x + 72, 238 + (index % 2) * 20), fill=(78, 158, 75), outline=accent, width=3)
    elif "sweet" in cat or "fruit" in cat or "nut" in cat:
        colors = [(191, 74, 53), (232, 162, 47), (116, 90, 54), (220, 198, 104)]
        for index in range(12):
            x = 280 + (index % 6) * 42
            y = 160 + (index // 6) * 52
            draw.ellipse((x, y, x + 34, y + 34), fill=colors[index % len(colors)], outline=accent, width=2)
    else:
        for index in range(18):
            x = 255 + (index % 6) * 55
            y = 145 + (index // 6) * 42
            draw.ellipse((x, y, x + 38, y + 24), fill=(217, 176, 88), outline=accent, width=2)
    title_font = load_font(40, True)
    small_font = load_font(23)
    lines = wrap(draw, title, title_font, width - 120)
    y = height - 124 - (len(lines) * 44) // 2
    for line in lines:
        box = draw.textbbox((0, 0), line, font=title_font)
        draw.text(((width - (box[2] - box[0])) / 2, y), line, font=title_font, fill=(28, 55, 37))
        y += 44
    box = draw.textbbox((0, 0), category, font=small_font)
    draw.text(((width - (box[2] - box[0])) / 2, height - 58), category, font=small_font, fill=accent)
    image.save(path, "WEBP", quality=88, method=6)
    report["generated_images"].append(rel)


def find_image(status: str, slug: str, report: dict):
    prefixes = ["", f"{status}-", "forbidden-" if status == "forbidden" else "allowed-"]
    for prefix in prefixes:
        path = ROOT / "assets" / "foods" / status / f"{prefix}{slug}.webp"
        if path.exists():
            rel = "./" + str(path.relative_to(ROOT)).replace("\\", "/")
            report["reused_images"].append(rel)
            return rel
    return None


def ensure_food_image(status: str, slug: str, name_en: str, category_en: str, report: dict):
    existing = find_image(status, slug, report)
    if existing:
        return existing
    rel = f"./assets/foods/{status}/{slug}.webp"
    generate_card(rel, name_en, category_en, status, report)
    return rel


def make_allowed(spec: dict, report: dict):
    cat_ar, cat_en, cat_fr, cat_es = ALLOWED_CATS[spec["category"]]
    slug = spec.get("slug") or slugify(spec["en"])
    image = spec.get("image") or ensure_food_image("allowed", slug, spec["en"], cat_en, report)
    notes_ar = spec.get("notes_ar") or "مذكور في ملف Tayibat Life PDF ضمن المسموحات، مع الالتزام بالكمية أو الشرط المذكور عند وجوده."
    notes_en = spec.get("notes_en") or "Listed as allowed in the Tayibat Life PDF; follow the stated quantity or condition where provided."
    notes_fr = spec.get("notes_fr") or "Mentionné comme autorisé dans le PDF Tayibat Life; respecter la quantité ou la condition indiquée."
    notes_es = spec.get("notes_es") or "Figura como permitido en el PDF de Tayibat Life; respete la cantidad o condición indicada."
    freq_ar = spec.get("frequency_ar", "")
    freq_en = spec.get("frequency_en", "")
    return {
        "id": spec.get("id") or f"allowed-{slug}",
        "name": spec["ar"],
        "category": cat_ar,
        "status": "allowed",
        "image": image,
        "sourcePage": spec.get("page"),
        "sourcePages": spec.get("pages", [spec.get("page")]),
        "sourceBook": SOURCE_BOOK,
        "name_ar": spec["ar"],
        "name_en": spec["en"],
        "name_fr": spec.get("fr", spec["en"]),
        "name_es": spec.get("es", spec["en"]),
        "category_ar": cat_ar,
        "category_en": cat_en,
        "category_fr": cat_fr,
        "category_es": cat_es,
        "notes": notes_ar,
        "notes_ar": notes_ar,
        "notes_en": notes_en,
        "notes_fr": notes_fr,
        "notes_es": notes_es,
        "tags_ar": [cat_ar, "مصدر PDF", "مسموح"],
        "tags_en": [cat_en, "PDF source", "allowed"],
        "tags_fr": [cat_fr, "source PDF", "autorisé"],
        "tags_es": [cat_es, "fuente PDF", "permitido"],
        "benefits": notes_ar,
        "benefits_ar": notes_ar,
        "benefits_en": notes_en,
        "benefits_fr": notes_fr,
        "benefits_es": notes_es,
        "frequency": freq_ar or freq_en,
        "frequency_ar": freq_ar or freq_en,
        "frequency_en": freq_en,
        "frequency_fr": spec.get("frequency_fr", freq_en),
        "frequency_es": spec.get("frequency_es", freq_en),
        "alt_ar": spec["ar"],
        "alt_en": spec["en"],
        "alt_fr": spec.get("fr", spec["en"]),
        "alt_es": spec.get("es", spec["en"]),
    }


def make_forbidden(spec: dict, report: dict):
    cat_ar, cat_en, cat_fr, cat_es = FORBIDDEN_CATS[spec["category"]]
    slug = spec.get("slug") or slugify(spec["en"])
    image = spec.get("image") or ensure_food_image("forbidden", slug, spec["en"], cat_en, report)
    reason_ar = spec.get("reason_ar") or "مذكور في ملف Tayibat Life PDF ضمن الممنوعات أو التحذيرات."
    reason_en = spec.get("reason_en") or "Listed in the Tayibat Life PDF as forbidden or cautioned against."
    reason_fr = spec.get("reason_fr") or "Mentionné dans le PDF Tayibat Life comme interdit ou déconseillé."
    reason_es = spec.get("reason_es") or "Figura en el PDF de Tayibat Life como prohibido o desaconsejado."
    warning_ar = spec.get("warning_ar") or "تجنب هذا الصنف واتبع الاستثناءات المحددة فقط إذا ذُكرت في المصدر."
    warning_en = spec.get("warning_en") or "Avoid this item and follow only the explicit exceptions stated in the source."
    warning_fr = spec.get("warning_fr") or "Évitez cet aliment et ne suivez que les exceptions explicites de la source."
    warning_es = spec.get("warning_es") or "Evite este alimento y siga solo las excepciones explícitas de la fuente."
    alt_ar = "اختر بديلاً مطابقاً لقائمة المسموحات في ملف PDF."
    alt_en = "Choose an alternative from the allowed PDF list."
    alt_fr = "Choisissez une alternative dans la liste autorisée du PDF."
    alt_es = "Elija una alternativa de la lista permitida del PDF."
    return {
        "id": spec.get("id") or slug,
        "category": spec.get("category_key") or slugify(spec["category"]).replace("-", "_"),
        "status": "forbidden",
        "category_ar": cat_ar,
        "category_en": cat_en,
        "category_fr": cat_fr,
        "category_es": cat_es,
        "name": spec["ar"],
        "name_ar": spec["ar"],
        "name_en": spec["en"],
        "name_fr": spec.get("fr", spec["en"]),
        "name_es": spec.get("es", spec["en"]),
        "sourcePage": spec.get("page"),
        "sourcePages": spec.get("pages", [spec.get("page")]),
        "sourceBook": SOURCE_BOOK,
        "reason_ar": reason_ar,
        "reason_en": reason_en,
        "reason_fr": reason_fr,
        "reason_es": reason_es,
        "warning_ar": warning_ar,
        "warning_en": warning_en,
        "warning_fr": warning_fr,
        "warning_es": warning_es,
        "alternative_ar": alt_ar,
        "alternative_en": alt_en,
        "alternative_fr": alt_fr,
        "alternative_es": alt_es,
        "image": image,
        "alt_ar": spec["ar"],
        "alt_en": spec["en"],
        "alt_fr": spec.get("fr", spec["en"]),
        "alt_es": spec.get("es", spec["en"]),
        "reason": reason_ar,
        "warning": warning_ar,
        "alternative": alt_ar,
        "harms": reason_ar,
        "harms_ar": reason_ar,
        "harms_en": reason_en,
        "harms_fr": reason_fr,
        "harms_es": reason_es,
        "tags_ar": [cat_ar, "مصدر PDF", "ممنوع"],
        "tags_en": [cat_en, "PDF source", "forbidden"],
        "tags_fr": [cat_fr, "source PDF", "interdit"],
        "tags_es": [cat_es, "fuente PDF", "prohibido"],
    }


def existing_index(items):
    index = {}
    for item in items:
        index[("id", item.get("id"))] = item
        index[("en", norm(item.get("name_en")))] = item
        index[("ar", norm(item.get("name_ar")))] = item
    return index


def merge_missing(existing: dict, incoming: dict):
    for key, value in incoming.items():
        if existing.get(key) in (None, "", []) and value not in (None, "", []):
            existing[key] = value
    for lang in ("ar", "en", "fr", "es"):
        alt = f"alt_{lang}"
        if not existing.get(alt):
            existing[alt] = incoming.get(alt) or existing.get(f"name_{lang}") or existing.get("name")


def dedupe(items):
    seen, output = {}, []
    for item in items:
        item_id = item.get("id")
        if item_id in seen:
            merge_missing(seen[item_id], item)
        else:
            seen[item_id] = item
            output.append(item)
    return output


def update_sources(allowed, forbidden, tips):
    allowed["source"].update({
        "title": "Tayibat Life PDF",
        "pdf": SOURCE_BOOK,
        "rebuiltAt": TODAY,
        "pagesReviewed": list(range(1, 24)),
        "sourcePages": list(range(2, 13)) + [19, 20],
        "name_en": "Tayibat Life PDF",
        "note_ar": "تم تدقيق قائمة المسموح مقابل جميع صفحات ملف Tayibat Life PDF وعددها 23 صفحة، وتشمل الحبوب والمشروبات والأجبان والدهون والخضار واللحوم والأسماك والفواكه والفواكه المجففة والمكسرات والأعشاب والحلويات والاستثناءات والقيود الأسبوعية.",
        "note_en": "Allowed foods were audited against all 23 pages of the uploaded Tayibat Life PDF, including grains, drinks, dairy/fats, vegetables, meats, fish, fruits, dried fruits, nuts, herbs, sweets, exceptions, and weekly restrictions.",
        "note_fr": "La liste autorisée a été auditée avec les 23 pages du PDF Tayibat Life.",
        "note_es": "La lista permitida se auditó contra las 23 páginas del PDF Tayibat Life.",
    })
    forbidden["source"].update({
        "title": "Tayibat Life PDF forbidden audit",
        "type": "uploaded_pdf_visual_source",
        "rebuiltAt": TODAY,
        "pdf": SOURCE_BOOK,
        "pagesReviewed": list(range(1, 24)),
        "sourcePages": list(range(13, 24)),
        "name_en": "Tayibat Life PDF Forbidden Audit",
        "note_ar": "تمت مطابقة قائمة الممنوعات مع ملف Tayibat Life PDF المرفوع، مع فصل الصنف الكامل عن العصير أو الاستثناء عندما يذكر PDF ذلك.",
        "note_en": "Forbidden foods were matched to the uploaded Tayibat Life PDF, separating whole items from juices or exceptions when the PDF states that distinction.",
        "note_fr": "Les interdits ont été alignés sur le PDF Tayibat Life fourni.",
        "note_es": "Los prohibidos se alinearon con el PDF Tayibat Life cargado.",
    })
    tips["source"].update({
        "pdf": SOURCE_BOOK,
        "rebuiltAt": TODAY,
        "pagesReviewed": list(range(1, 24)),
        "sourcePages": [9, 10, 11, 12, 22, 23],
        "note_ar": "تمت مطابقة النصائح والملاحظات مع صفحات الملاحظات العامة وقيود التكرار في ملف Tayibat Life PDF.",
        "note_en": "Tips and notes were matched to the general doctor-note pages and frequency restrictions in the Tayibat Life PDF.",
    })


def update_categories(allowed, forbidden, report):
    for rel, title, status in [(rel, key, "allowed") for key, rel in ALLOWED_CATEGORY_IMAGES.items()] + [(rel, key, "forbidden") for key, rel in FORBIDDEN_CATEGORY_IMAGES.items()]:
        before = rel_to_abs(rel).exists()
        generate_card(rel, title, "Category", status, report)
        if not before and rel_to_abs(rel).exists():
            report["missing_categories_added"].append(rel)
    order = list(ALLOWED_CATS)
    allowed["categories"] = [ALLOWED_CATS[key][0] for key in order]
    allowed["categories_ar"] = [ALLOWED_CATS[key][0] for key in order]
    allowed["categories_en"] = [ALLOWED_CATS[key][1] for key in order]
    allowed["categories_fr"] = [ALLOWED_CATS[key][2] for key in order]
    allowed["categories_es"] = [ALLOWED_CATS[key][3] for key in order]
    allowed["categoryImages"] = [ALLOWED_CATEGORY_IMAGES[key] for key in order]
    order = list(FORBIDDEN_CATS)
    forbidden["categories"] = [slugify(key).replace("-", "_") for key in order]
    forbidden["categories_ar"] = [FORBIDDEN_CATS[key][0] for key in order]
    forbidden["categories_en"] = [FORBIDDEN_CATS[key][1] for key in order]
    forbidden["categories_fr"] = [FORBIDDEN_CATS[key][2] for key in order]
    forbidden["categories_es"] = [FORBIDDEN_CATS[key][3] for key in order]
    forbidden["categoryImages"] = [FORBIDDEN_CATEGORY_IMAGES[key] for key in order]


def resolve_known_conflicts(allowed, forbidden, report):
    allowed_before, forbidden_before = len(allowed["items"]), len(forbidden["items"])
    allowed["items"] = [item for item in allowed["items"] if item.get("id") != "allowed-banana-weekly"]
    forbidden["items"] = [item for item in forbidden["items"] if item.get("id") not in {"almond-milk", "pigeon"}]
    if len(allowed["items"]) != allowed_before:
        report["resolved_conflicts"].append("Removed allowed banana weekly because page 21 lists whole banana under forbidden fruits.")
    if len(forbidden["items"]) != forbidden_before:
        report["resolved_conflicts"].append("Removed forbidden almond milk and pigeon because the PDF lists almond milk as a plant alternative and pigeon meat as allowed poultry.")
    for item in allowed["items"]:
        if item.get("id") == "allowed-seedless-pomegranate":
            item.update({
                "name": "عصير الرمان بدون بذور",
                "name_ar": "عصير الرمان بدون بذور",
                "name_en": "Pomegranate juice without seeds",
                "name_fr": "Jus de grenade sans pépins",
                "name_es": "Jugo de granada sin semillas",
                "category": ALLOWED_CATS["Allowed fruit juices"][0],
                "category_ar": ALLOWED_CATS["Allowed fruit juices"][0],
                "category_en": ALLOWED_CATS["Allowed fruit juices"][1],
                "category_fr": ALLOWED_CATS["Allowed fruit juices"][2],
                "category_es": ALLOWED_CATS["Allowed fruit juices"][3],
                "sourcePage": 4,
                "sourcePages": [4],
                "sourceBook": SOURCE_BOOK,
                "notes": "مسموح كعصير رمان بدون بذور حسب صفحة المشروبات.",
                "notes_ar": "مسموح كعصير رمان بدون بذور حسب صفحة المشروبات.",
                "notes_en": "Allowed as pomegranate juice without seeds according to the drinks page.",
                "notes_fr": "Autorisé sous forme de jus de grenade sans pépins selon la page des boissons.",
                "notes_es": "Permitido como jugo de granada sin semillas según la página de bebidas.",
                "alt_ar": "عصير الرمان بدون بذور",
                "alt_en": "Pomegranate juice without seeds",
                "alt_fr": "Jus de grenade sans pépins",
                "alt_es": "Jugo de granada sin semillas",
            })
            report["resolved_conflicts"].append("Changed existing seedless pomegranate to pomegranate juice without seeds; page 21 forbids whole pomegranate fruit.")


def add_specs(allowed, forbidden, spec, report):
    index = existing_index(allowed["items"])
    for item_spec in spec["allowed"]:
        rec = make_allowed(item_spec, report)
        existing = index.get(("id", rec["id"])) or index.get(("en", norm(rec["name_en"]))) or index.get(("ar", norm(rec["name_ar"])))
        if existing:
            merge_missing(existing, rec)
            report["already_allowed"].append(rec["name_en"])
        else:
            allowed["items"].append(rec)
            report["new_allowed"].append(rec["name_en"])
            index[("id", rec["id"])] = rec
            index[("en", norm(rec["name_en"]))] = rec
            index[("ar", norm(rec["name_ar"]))] = rec
    index = existing_index(forbidden["items"])
    for item_spec in spec["forbidden"]:
        rec = make_forbidden(item_spec, report)
        existing = index.get(("id", rec["id"])) or index.get(("en", norm(rec["name_en"]))) or index.get(("ar", norm(rec["name_ar"])))
        if existing:
            merge_missing(existing, rec)
            report["already_forbidden"].append(rec["name_en"])
        else:
            forbidden["items"].append(rec)
            report["new_forbidden"].append(rec["name_en"])
            index[("id", rec["id"])] = rec
            index[("en", norm(rec["name_en"]))] = rec
            index[("ar", norm(rec["name_ar"]))] = rec


def update_tips(tips, spec, report):
    tip_cats = {
        "Doctor notes": ("ملاحظات الطبيب", "Doctor notes", "Notes médicales", "Notas médicas"),
        "Weekly restrictions": ("قيود أسبوعية", "Weekly restrictions", "Restrictions hebdomadaires", "Restricciones semanales"),
    }
    existing = {tip.get("id") for tip in tips["tips"]}
    for item in spec["tips"]:
        if item["id"] in existing:
            continue
        generate_card(item["image"], item["title_en"], item["category"], "allowed", report)
        cat_ar, cat_en, cat_fr, cat_es = tip_cats[item["category"]]
        tips["tips"].append({
            "id": item["id"],
            "category": cat_ar,
            "category_ar": cat_ar,
            "category_en": cat_en,
            "category_fr": cat_fr,
            "category_es": cat_es,
            "sourcePage": item["page"],
            "sourcePages": [item["page"]],
            "sourceBook": SOURCE_BOOK,
            "title_ar": item["title_ar"],
            "title_en": item["title_en"],
            "title_fr": item["title_fr"],
            "title_es": item["title_es"],
            "text_ar": item["text_ar"],
            "text_en": item["text_en"],
            "text_fr": item["text_fr"],
            "text_es": item["text_es"],
            "image": item["image"],
            "alt_ar": item["title_ar"],
            "alt_en": item["title_en"],
            "alt_fr": item["title_fr"],
            "alt_es": item["title_es"],
            "name_ar": item["title_ar"],
            "name_en": item["title_en"],
            "name_fr": item["title_fr"],
            "name_es": item["title_es"],
            "tags_ar": [cat_ar, "مصدر PDF"],
            "tags_en": [cat_en, "PDF source"],
            "tags_fr": [cat_fr, "source PDF"],
            "tags_es": [cat_es, "fuente PDF"],
        })
        report["new_tips"].append(item["title_en"])
    for tip in tips["tips"]:
        for lang in ("ar", "en", "fr", "es"):
            if not tip.get(f"alt_{lang}"):
                tip[f"alt_{lang}"] = tip.get(f"title_{lang}") or tip.get(f"name_{lang}") or tip.get("id", "Tayibat Life tip")
        tip.setdefault("sourceBook", SOURCE_BOOK)
    for key in tip_cats:
        cat_ar, cat_en, cat_fr, cat_es = tip_cats[key]
        for field, value in [("categories", cat_ar), ("categories_ar", cat_ar), ("categories_en", cat_en), ("categories_fr", cat_fr), ("categories_es", cat_es)]:
            tips.setdefault(field, [])
            if value not in tips[field]:
                tips[field].append(value)


def update_meals_and_weekly(meals, weekly):
    for group in meals.get("templates", {}).values():
        for meal in group:
            if meal.get("id") == "meal-lunch-pomegranate-walnut-apricot":
                meal["title_ar"] = "عصير رمان بدون بذور مع جوز ومشمش مجفف"
                meal["title_en"] = "Seedless pomegranate juice with walnuts and dried apricots"
                meal["title_fr"] = "Jus de grenade sans pépins avec noix et abricots secs"
                meal["title_es"] = "Jugo de granada sin semillas con nueces y albaricoques secos"
                meal["items_ar"] = ["عصير الرمان بدون بذور", "الجوز", "المشمش المجفف"]
                meal["items_en"] = ["Pomegranate juice without seeds", "Walnuts", "Dried apricots"]
                meal["items_fr"] = ["Jus de grenade sans pépins", "Noix", "Abricots secs"]
                meal["items_es"] = ["Jugo de granada sin semillas", "Nueces", "Albaricoques secos"]
                meal["alt_ar"] = meal["title_ar"]
                meal["alt_en"] = meal["title_en"]
                meal["alt_fr"] = meal["title_fr"]
                meal["alt_es"] = meal["title_es"]
                meal["sourcePages"] = sorted(set(meal.get("sourcePages", []) + [4, 21]))
    for plan in weekly.get("plans", []):
        if "رمان" in plan.get("lunch", ""):
            plan["lunch"] = "عصير رمان بدون بذور مع جوز ومشمش مجفف"
            plan["lunch_en"] = "Seedless pomegranate juice with walnuts and dried apricots"
            plan["lunch_fr"] = "Jus de grenade sans pépins avec noix et abricots secs"
            plan["lunch_es"] = "Jugo de granada sin semillas con nueces y albaricoques secos"
    weekly["sourceBook"] = SOURCE_BOOK
    weekly["sourcePage"] = 22
    weekly["sourcePages"] = [2, 4, 6, 7, 8, 9, 10, 11, 22, 23]
    weekly["weeklyRestrictions"] = [
        {"id": "freekeh-monthly", "title_ar": "الفريك مرة واحدة شهرياً", "title_en": "Freekeh once monthly", "title_fr": "Freekeh une fois par mois", "title_es": "Freekeh una vez al mes", "sourcePage": 2},
        {"id": "vermicelli-twice-weekly", "title_ar": "الشعيرية لا تزيد عن مرتين أسبوعياً ولا تكون إفطاراً", "title_en": "Vermicelli no more than twice weekly and not for breakfast", "title_fr": "Vermicelles deux fois par semaine au plus et pas au petit-déjeuner", "title_es": "Fideos finos no más de dos veces por semana y no en el desayuno", "sourcePage": 2},
        {"id": "potato-flour-twice-weekly", "title_ar": "دقيق البطاطا بحد أقصى مرتين أسبوعياً", "title_en": "Potato flour maximum twice weekly", "title_fr": "Farine de pomme de terre au maximum deux fois par semaine", "title_es": "Harina de patata máximo dos veces por semana", "sourcePage": 2},
        {"id": "orange-juice-weekly", "title_ar": "عصير البرتقال مرة واحدة أسبوعياً", "title_en": "Orange juice once weekly", "title_fr": "Jus d'orange une fois par semaine", "title_es": "Jugo de naranja una vez por semana", "sourcePage": 4},
        {"id": "mango-juice-monthly", "title_ar": "عصير المانجا مرة واحدة شهرياً", "title_en": "Mango juice once monthly", "title_fr": "Jus de mangue une fois par mois", "title_es": "Jugo de mango una vez al mes", "sourcePage": 4},
        {"id": "dates-daily", "title_ar": "التمر من 3 إلى 5 حبات يومياً", "title_en": "Dates 3 to 5 pieces daily", "title_fr": "Dattes 3 à 5 pièces par jour", "title_es": "Dátiles 3 a 5 piezas al día", "sourcePage": 3},
        {"id": "vegetable-weekly-monthly", "title_ar": "بعض الخضار أسبوعية وبعضها شهرية حسب صفحة الخضار", "title_en": "Some vegetables are weekly and others monthly according to the vegetable page", "title_fr": "Certains légumes sont hebdomadaires et d'autres mensuels selon la page des légumes", "title_es": "Algunas verduras son semanales y otras mensuales según la página de verduras", "sourcePage": 6},
        {"id": "fish-weekly", "title_ar": "الأسماك مرة واحدة أسبوعياً ويفضل البحري الطازج", "title_en": "Fish once weekly, preferably fresh sea fish", "title_fr": "Poisson une fois par semaine, de préférence poisson de mer frais", "title_es": "Pescado una vez por semana, preferiblemente pescado de mar fresco", "sourcePage": 7},
        {"id": "bone-broth-distribution", "title_ar": "شوربة العظام والكوارع توزع حسب الحاجة والتنظيم الغذائي", "title_en": "Bone and trotter soups are distributed by need and dietary planning", "title_fr": "Les bouillons d'os et de pieds se répartissent selon le besoin et l'organisation alimentaire", "title_es": "Los caldos de huesos y manitas se distribuyen según necesidad y planificación alimentaria", "sourcePage": 22},
        {"id": "orzo-monthly", "title_ar": "لسان العصفور مرة واحدة شهرياً", "title_en": "Orzo once monthly", "title_fr": "Orzo une fois par mois", "title_es": "Orzo una vez al mes", "sourcePage": 22},
    ]


def update_versions(translations, package, package_lock):
    for key, vals in {
        "pdfAudit": {"ar": "تدقيق PDF", "en": "PDF audit", "fr": "Audit PDF", "es": "Auditoría PDF"},
        "weeklyRestrictions": {"ar": "القيود الأسبوعية", "en": "Weekly restrictions", "fr": "Restrictions hebdomadaires", "es": "Restricciones semanales"},
        "sourcePdf": {"ar": "مصدر PDF", "en": "PDF source", "fr": "Source PDF", "es": "Fuente PDF"},
    }.items():
        for lang, value in vals.items():
            translations.setdefault(lang, {})[key] = value
    package["version"] = "1.0.1"
    package_lock["version"] = "1.0.1"
    package_lock.setdefault("packages", {}).setdefault("", {})["version"] = "1.0.1"
    app_js = (ROOT / "app.js").read_text(encoding="utf-8")
    app_js = app_js.replace('const APP_VERSION = "v75";', 'const APP_VERSION = "v76";')
    (ROOT / "app.js").write_text(app_js, encoding="utf-8")
    sw_js = (ROOT / "sw.js").read_text(encoding="utf-8")
    sw_js = sw_js.replace("tayibat-life-v75", "tayibat-life-v76").replace("?v75", "?v76")
    (ROOT / "sw.js").write_text(sw_js, encoding="utf-8")


def write_report(report, allowed, forbidden, tips):
    report_dir = ROOT / "tmp" / "pdfs" / "tayibat_life_audit"
    report_dir.mkdir(parents=True, exist_ok=True)
    report["totals"] = {
        "allowed": len(allowed["items"]),
        "forbidden": len(forbidden["items"]),
        "tips": len(tips["tips"]),
    }
    (report_dir / "audit-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown = [
        "# Tayibat Life PDF Audit Report",
        "",
        "PDF pages reviewed: 23",
        f"Allowed already in app: {len(report['already_allowed'])}",
        f"Forbidden already in app: {len(report['already_forbidden'])}",
        f"New allowed items added: {len(report['new_allowed'])}",
        f"New forbidden items added: {len(report['new_forbidden'])}",
        f"New tips added: {len(report['new_tips'])}",
        "",
        "## ALREADY IN APP",
        "Allowed: " + ", ".join(report["already_allowed"]),
        "Forbidden: " + ", ".join(report["already_forbidden"]),
        "",
        "## MISSING FROM APP",
        "All missing items represented in the audit spec were added. See NEW ITEMS ADDED.",
        "",
        "## CONFLICTS",
        "Resolved: " + "; ".join(report["resolved_conflicts"]),
        "",
        "## NEW ITEMS ADDED",
        "Allowed: " + ", ".join(report["new_allowed"]),
        "Forbidden: " + ", ".join(report["new_forbidden"]),
        "Tips: " + ", ".join(report["new_tips"]),
    ]
    (report_dir / "audit-report.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")


def main():
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    report = {
        "already_allowed": [],
        "already_forbidden": [],
        "new_allowed": [],
        "new_forbidden": [],
        "new_tips": [],
        "resolved_conflicts": [],
        "generated_images": [],
        "reused_images": [],
        "missing_categories_added": [],
    }
    allowed = read_json("data/foods_allowed.json")
    forbidden = read_json("data/foods_forbidden.json")
    tips = read_json("data/tips.json")
    weekly = read_json("data/weekly_plans.json")
    meals = read_json("data/meals.json")
    translations = read_json("data/translations.json")
    package = read_json("package.json")
    package_lock = read_json("package-lock.json")
    update_sources(allowed, forbidden, tips)
    update_categories(allowed, forbidden, report)
    resolve_known_conflicts(allowed, forbidden, report)
    add_specs(allowed, forbidden, spec, report)
    update_tips(tips, spec, report)
    update_meals_and_weekly(meals, weekly)
    for item in allowed["items"] + forbidden["items"]:
        item.setdefault("sourceBook", SOURCE_BOOK)
        for lang in ("ar", "en", "fr", "es"):
            if not item.get(f"alt_{lang}"):
                item[f"alt_{lang}"] = item.get(f"name_{lang}") or item.get("name") or item.get("id")
    allowed["items"] = dedupe(allowed["items"])
    forbidden["items"] = dedupe(forbidden["items"])
    tips["tips"] = dedupe(tips["tips"])
    update_versions(translations, package, package_lock)
    write_json("data/foods_allowed.json", allowed)
    write_json("data/foods_forbidden.json", forbidden)
    write_json("data/tips.json", tips)
    write_json("data/weekly_plans.json", weekly)
    write_json("data/meals.json", meals)
    write_json("data/translations.json", translations)
    write_json("package.json", package)
    write_json("package-lock.json", package_lock)
    write_report(report, allowed, forbidden, tips)
    print(json.dumps({
        "allowed_total": len(allowed["items"]),
        "forbidden_total": len(forbidden["items"]),
        "tips_total": len(tips["tips"]),
        "new_allowed": len(report["new_allowed"]),
        "new_forbidden": len(report["new_forbidden"]),
        "new_tips": len(report["new_tips"]),
        "generated_images": len(report["generated_images"]),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
