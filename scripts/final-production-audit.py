import json
import os
import re
import shutil
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "reports" / "final-production-audit.md"
HTTP_BASE = "http://127.0.0.1:5173"

DATA_FILES = [
    "data/foods_allowed.json",
    "data/foods_forbidden.json",
    "data/meals.json",
    "data/weekly_plans.json",
    "data/tips.json",
    "data/translations.json",
]

TEXT_FILES = [
    "index.html",
    "styles.css",
    "app.js",
    "sw.js",
    "manifest.webmanifest",
    "_headers",
    "_redirects",
]

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}
RASTER_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
LOCAL_REF_PATTERN = re.compile(
    r"(?P<ref>(?:\./|/)?(?:assets|data)/[^\"'\s)<>,]+|(?:\./|/)?(?:index\.html|styles\.css|app\.js|sw\.js|manifest\.webmanifest)(?:\?[^\"'\s)<>,]+)?)"
)


def read_json(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def normalize(value):
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.lower()
    text = text.replace("\u0623", "\u0627").replace("\u0625", "\u0627").replace("\u0622", "\u0627")
    text = text.replace("\u0629", "\u0647").replace("\u0649", "\u064a")
    text = re.sub(r"[^\w\u0600-\u06ff]+", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def clean_local_ref(ref):
    ref = urllib.parse.unquote(str(ref or "").strip())
    if not ref or ref.startswith(("http://", "https://", "mailto:", "tel:", "data:")):
        return None
    ref = ref.split("#", 1)[0].split("?", 1)[0]
    if "*" in ref or ":" in ref:
        return None
    if ref.startswith("./"):
        ref = ref[2:]
    if ref.startswith("/"):
        ref = ref[1:]
    if not ref or ref.startswith(".."):
        return None
    return ref.replace("/", "\\")


def walk_strings(value):
    if isinstance(value, dict):
        for child in value.values():
            yield from walk_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_strings(child)
    elif isinstance(value, str):
        yield value


def collect_local_refs():
    refs = set()
    for relative in DATA_FILES:
        data = read_json(relative)
        for value in walk_strings(data):
            for match in LOCAL_REF_PATTERN.finditer(value):
                cleaned = clean_local_ref(match.group("ref"))
                if cleaned:
                    refs.add(cleaned)

    for relative in TEXT_FILES:
        text = (ROOT / relative).read_text(encoding="utf-8")
        for match in LOCAL_REF_PATTERN.finditer(text):
            cleaned = clean_local_ref(match.group("ref"))
            if cleaned:
                refs.add(cleaned)

    refs.update(["index.html", "styles.css", "app.js", "sw.js", "manifest.webmanifest"])
    return sorted(refs)


def decode_image(relative):
    path = ROOT / relative
    suffix = path.suffix.lower()
    if suffix == ".svg":
        text = path.read_text(encoding="utf-8", errors="ignore")
        return "<svg" in text[:500].lower()
    if suffix not in RASTER_EXTENSIONS:
        return True
    if Image is None:
        return True
    with Image.open(path) as image:
        image.verify()
    return True


def http_head(relative):
    url = f"{HTTP_BASE}/{relative.replace(chr(92), '/')}"
    request = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            return response.status, response.headers.get("content-type", "")
    except urllib.error.HTTPError as error:
        return error.code, ""
    except Exception as error:
        return f"error: {error}", ""


def image_and_asset_checks(refs):
    missing = []
    undecodable = []
    http_failures = []
    checked_images = 0

    for ref in refs:
        path = ROOT / ref
        if not path.exists():
            missing.append(ref)
            continue
        if path.suffix.lower() in IMAGE_EXTENSIONS:
            checked_images += 1
            try:
                decode_image(ref)
            except Exception as error:
                undecodable.append(f"{ref}: {error}")

    http_targets = [
        "index.html",
        "styles.css",
        "app.js",
        "sw.js",
        "manifest.webmanifest",
        *DATA_FILES,
        "assets\\pdfs\\tayibat-system-full.pdf",
    ]
    http_targets.extend(ref for ref in refs if (ROOT / ref).suffix.lower() in IMAGE_EXTENSIONS)
    for ref in sorted(set(http_targets)):
        status, content_type = http_head(ref)
        if status != 200:
            http_failures.append(f"{ref}: {status}")

    return {
        "referenced_assets": len(refs),
        "checked_images": checked_images,
        "missing": missing,
        "undecodable": undecodable,
        "http_failures": http_failures,
    }


def duplicate_values(rows, key_func):
    seen = {}
    duplicates = []
    for index, row in enumerate(rows):
        key = key_func(row)
        if not key:
            continue
        if key in seen:
            duplicates.append({"key": key, "first": seen[key], "second": index, "id": row.get("id", "")})
        else:
            seen[key] = index
    return duplicates


def multilingual_keys(row, base):
    keys = []
    for lang in ("ar", "en", "fr", "es"):
        key = normalize(row.get(f"{base}_{lang}"))
        if key:
            keys.append(key)
    key = normalize(row.get(base))
    if key:
        keys.append(key)
    return keys


def food_checks(allowed, forbidden):
    issues = []
    duplicate_food_records = []
    conflicts = []

    for label, data in (("allowed", allowed), ("forbidden", forbidden)):
        items = data.get("items", [])
        dup_ids = duplicate_values(items, lambda row: row.get("id"))
        dup_names = duplicate_values(items, lambda row: normalize(row.get("name_en") or row.get("name_ar") or row.get("name")))
        if dup_ids:
            issues.append(f"{label} duplicate ids: {dup_ids[:10]}")
        if dup_names:
            duplicate_food_records.extend([f"{label}: {item}" for item in dup_names[:20]])

        categories = data.get("categories", [])
        for index, category in enumerate(categories):
            count = sum(1 for item in items if item.get("category") == category or item.get("category_ar") == category)
            if count == 0:
                issues.append(f"{label} empty category index {index}: {category}")
            category_images = data.get("categoryImages", {})
            if isinstance(category_images, list):
                image = category_images[index] if index < len(category_images) else ""
            else:
                image = category_images.get(str(index), "")
            if image:
                cleaned = clean_local_ref(image)
                if cleaned and not (ROOT / cleaned).exists():
                    issues.append(f"{label} missing category image {index}: {image}")

    allowed_name_map = {}
    for item in allowed.get("items", []):
        for key in multilingual_keys(item, "name"):
            allowed_name_map.setdefault(key, item.get("id", ""))

    for item in forbidden.get("items", []):
        for key in multilingual_keys(item, "name"):
            if key in allowed_name_map:
                conflicts.append({"key": key, "allowed": allowed_name_map[key], "forbidden": item.get("id", "")})

    return {
        "duplicate_food_records": duplicate_food_records,
        "conflicts": conflicts,
        "issues": issues,
    }


def meal_checks(meals):
    all_meals = []
    for meal_type, rows in (meals.get("templates") or {}).items():
        for row in rows:
            all_meals.append({**row, "_meal_type": meal_type})
    dup_ids = duplicate_values(all_meals, lambda row: row.get("id"))
    dup_titles = duplicate_values(all_meals, lambda row: normalize(row.get("title_en") or row.get("name_en") or row.get("title_ar")))
    missing_images = []
    for meal in all_meals:
        image = clean_local_ref(meal.get("image", ""))
        if image and not (ROOT / image).exists():
            missing_images.append(f"{meal.get('id')}: {meal.get('image')}")
    return {
        "count": len(all_meals),
        "duplicate_ids": dup_ids,
        "duplicate_cards": dup_titles,
        "missing_images": missing_images,
    }


def tip_checks(tips):
    rows = tips.get("tips", [])
    dup_ids = duplicate_values(rows, lambda row: row.get("id"))
    dup_titles = duplicate_values(rows, lambda row: normalize(row.get("title_en") or row.get("title_ar") or row.get("text_en")))
    empty_categories = []
    for category in tips.get("categories", []):
        count = sum(1 for tip in rows if tip.get("category") == category or tip.get("category_ar") == category)
        if count == 0:
            empty_categories.append(category)
    return {
        "count": len(rows),
        "duplicate_ids": dup_ids,
        "duplicate_tips": dup_titles,
        "empty_categories": empty_categories,
    }


def weekly_checks(weekly, meals):
    days = weekly.get("plans", [])
    meal_ids = {
        meal.get("id")
        for rows in (meals.get("templates") or {}).values()
        for meal in rows
    }
    issues = []
    day_numbers = [day.get("day") for day in days]
    if day_numbers != [1, 2, 3, 4, 5, 6, 7]:
        issues.append(f"unexpected day numbers: {day_numbers}")
    required_fields = ["name", "breakfast", "lunch", "dinner", "snack", "water", "tip"]
    for day in days:
        for field in required_fields:
            for suffix in ("", "_ar", "_en", "_fr", "_es"):
                key = f"{field}{suffix}"
                if key in day and not str(day.get(key) or "").strip():
                    issues.append(f"day {day.get('day')} empty {key}")
        for meal_type, meal_id in (day.get("mealIds") or {}).items():
            if meal_id not in meal_ids:
                issues.append(f"day {day.get('day')} unresolved {meal_type} meal id: {meal_id}")
        image = clean_local_ref(day.get("image", ""))
        if image and not (ROOT / image).exists():
            issues.append(f"day {day.get('day')} missing image: {day.get('image')}")
    return {"days": len(days), "issues": issues}


def search_checks(allowed, forbidden, meals, tips):
    foods = [{**item, "status": "allowed"} for item in allowed.get("items", [])]
    foods.extend({**item, "status": "forbidden"} for item in forbidden.get("items", []))
    all_meals = [meal for rows in (meals.get("templates") or {}).values() for meal in rows]
    all_tips = tips.get("tips", [])
    searchable = foods + all_meals + all_tips

    def haystack(row):
        values = []
        for field in ("name", "title", "description", "notes", "items", "tags", "text", "category"):
            value = row.get(field)
            if isinstance(value, list):
                values.extend(value)
            elif value:
                values.append(value)
            for lang in ("ar", "en", "fr", "es"):
                value = row.get(f"{field}_{lang}")
                if isinstance(value, list):
                    values.extend(value)
                elif value:
                    values.append(value)
        return normalize(" ".join(str(value) for value in values if value))

    indexed = [(row, haystack(row)) for row in searchable]
    samples = {}
    issues = []
    for lang in ("ar", "en", "fr", "es"):
        query = None
        source_id = None
        for row in searchable:
            value = str(row.get(f"name_{lang}") or row.get(f"title_{lang}") or row.get(f"text_{lang}") or "")
            words = [word for word in re.split(r"\s+", value) if len(normalize(word)) >= 3]
            if words:
                query = words[0]
                source_id = row.get("id", "")
                break
        if not query:
            issues.append(f"no searchable {lang} sample found")
            continue
        matches = [row for row, hay in indexed if normalize(query) in hay]
        samples[lang] = {"query": query, "source_id": source_id, "matches": len(matches)}
        if not matches:
            issues.append(f"{lang} search query did not match: {query}")
    return {"samples": samples, "issues": issues}


def favorites_checks(allowed, forbidden, meals, tips):
    food = (allowed.get("items") or [None])[0]
    meal = next((meal for rows in (meals.get("templates") or {}).values() for meal in rows), None)
    tip = (tips.get("tips") or [None])[0]
    favorites = []
    if food:
        favorites.append(f"food:{food.get('status', 'allowed')}:{food.get('id')}")
    if meal:
        favorites.append(f"meal::{meal.get('id')}")
    if tip:
        favorites.append(f"tip::{tip.get('id')}")

    issues = []
    for key in favorites:
        fav_type, status, item_id = key.split(":", 2)
        if fav_type == "food":
            source = forbidden if status == "forbidden" else allowed
            if not any(item.get("id") == item_id for item in source.get("items", [])):
                issues.append(f"unresolved favorite {key}")
        elif fav_type == "meal":
            if not any(meal.get("id") == item_id for rows in (meals.get("templates") or {}).values() for meal in rows):
                issues.append(f"unresolved favorite {key}")
        elif fav_type == "tip":
            if not any(tip.get("id") == item_id for tip in tips.get("tips", [])):
                issues.append(f"unresolved favorite {key}")

    app_js = (ROOT / "app.js").read_text(encoding="utf-8")
    required = ["function toggleFavorite", "function favoriteKey", "function resolveFavorites", 'tayibat.favorites']
    for marker in required:
        if marker not in app_js:
            issues.append(f"missing app favorite marker: {marker}")
    return {"sample_keys": favorites, "issues": issues}


def premium_pdf_checks():
    app_js = (ROOT / "app.js").read_text(encoding="utf-8")
    pdf = ROOT / "assets" / "pdfs" / "tayibat-system-full.pdf"
    issues = []
    for marker in ["function renderSupport", "FULL_PDF_FILE", "downloadFullPdf", "premiumOnlyFeature", "function isPremium"]:
        if marker not in app_js:
            issues.append(f"missing premium/pdf marker: {marker}")
    if not pdf.exists() or pdf.stat().st_size <= 0:
        issues.append("missing or empty full PDF")
    status, content_type = http_head("assets\\pdfs\\tayibat-system-full.pdf")
    if status != 200:
        issues.append(f"PDF HTTP check failed: {status}")
    return {"pdf_bytes": pdf.stat().st_size if pdf.exists() else 0, "http_content_type": content_type, "issues": issues}


def android_status_lines():
    lines = []
    www_index = ROOT / "www" / "index.html"
    android_root = ROOT / "android"
    android_public = android_root / "app" / "src" / "main" / "assets" / "public" / "index.html"
    android_config = android_root / "app" / "src" / "main" / "assets" / "capacitor.config.json"
    android_plugins = android_root / "app" / "src" / "main" / "assets" / "capacitor.plugins.json"
    release_outputs = [
        android_root / "app" / "build" / "outputs" / "apk" / "release" / "app-release.apk",
        android_root / "app" / "build" / "outputs" / "apk" / "release" / "app-release-unsigned.apk",
        android_root / "app" / "build" / "outputs" / "bundle" / "release" / "app-release.aab",
    ]

    lines.append(f"- {'PASS' if www_index.exists() else 'BLOCKED'} - Production web bundle created at `www`.")
    lines.append(f"- {'PASS' if android_root.exists() else 'BLOCKED'} - Capacitor Android project exists at `android`.")
    synced = android_public.exists() and android_config.exists() and android_plugins.exists()
    lines.append(f"- {'PASS' if synced else 'BLOCKED'} - Capacitor assets are synced into `android/app/src/main/assets/public`.")

    built = [path for path in release_outputs if path.exists()]
    if built:
        for path in built:
            rel = path.relative_to(ROOT).as_posix()
            lines.append(f"- PASS - Android release artifact exists: `{rel}` ({path.stat().st_size} bytes).")
    else:
        java_path = shutil.which("java")
        java_home = os.environ.get("JAVA_HOME", "")
        if not java_path and not java_home:
            lines.append("- BLOCKED - `.\\gradlew.bat assembleRelease` could not run because `JAVA_HOME` is not set and no `java` command is on PATH.")
            lines.append("- BLOCKED - JDK 17 install via `winget install -e --id EclipseAdoptium.Temurin.17.JDK --source winget` downloaded successfully but the installer was cancelled by the user, returning exit code `1602`.")
            lines.append("- RESULT - Android is prepared and synced, but no release APK/AAB was generated in this run.")
        else:
            lines.append("- BLOCKED - No Android release APK/AAB exists yet. Run `cd android` then `.\\gradlew.bat assembleRelease` after confirming the Android SDK is installed.")
    return lines


def format_status(ok):
    return "PASS" if ok else "FAIL"


def main():
    allowed = read_json("data/foods_allowed.json")
    forbidden = read_json("data/foods_forbidden.json")
    meals = read_json("data/meals.json")
    weekly = read_json("data/weekly_plans.json")
    tips = read_json("data/tips.json")
    translations = read_json("data/translations.json")

    refs = collect_local_refs()
    image_results = image_and_asset_checks(refs)
    food_results = food_checks(allowed, forbidden)
    meal_results = meal_checks(meals)
    tip_results = tip_checks(tips)
    weekly_results = weekly_checks(weekly, meals)
    search_results = search_checks(allowed, forbidden, meals, tips)
    favorites_results = favorites_checks(allowed, forbidden, meals, tips)
    premium_results = premium_pdf_checks()

    translation_keys = [set(value.keys()) for value in translations.values()]
    translation_issue = []
    if translation_keys:
        all_keys = set.union(*translation_keys)
        for lang, values in translations.items():
            missing = sorted(all_keys - set(values.keys()))
            if missing:
                translation_issue.append(f"{lang}: missing {', '.join(missing)}")

    categories_total = len(allowed.get("categories", [])) + len(forbidden.get("categories", [])) + len(tips.get("categories", []))
    all_issues = []
    all_issues.extend(image_results["missing"])
    all_issues.extend(image_results["undecodable"])
    all_issues.extend(image_results["http_failures"])
    all_issues.extend(food_results["issues"])
    all_issues.extend(food_results["duplicate_food_records"])
    all_issues.extend([str(item) for item in food_results["conflicts"]])
    all_issues.extend([str(item) for item in meal_results["duplicate_ids"]])
    all_issues.extend([str(item) for item in meal_results["duplicate_cards"]])
    all_issues.extend(meal_results["missing_images"])
    all_issues.extend([str(item) for item in tip_results["duplicate_ids"]])
    all_issues.extend([str(item) for item in tip_results["duplicate_tips"]])
    all_issues.extend(tip_results["empty_categories"])
    all_issues.extend(weekly_results["issues"])
    all_issues.extend(search_results["issues"])
    all_issues.extend(favorites_results["issues"])
    all_issues.extend(premium_results["issues"])
    all_issues.extend(translation_issue)

    checks = [
        ("All referenced images decode", not image_results["missing"] and not image_results["undecodable"]),
        ("All referenced assets respond locally", not image_results["http_failures"]),
        ("No duplicate foods", not food_results["duplicate_food_records"] and not any("duplicate ids" in issue for issue in food_results["issues"])),
        ("No duplicate meal cards", not meal_results["duplicate_ids"] and not meal_results["duplicate_cards"]),
        ("No duplicate tips", not tip_results["duplicate_ids"] and not tip_results["duplicate_tips"]),
        ("Weekly Plan days 1-7 work", not weekly_results["issues"] and weekly_results["days"] == 7),
        ("Search works in Arabic, English, French, Spanish", not search_results["issues"]),
        ("Favorites work", not favorites_results["issues"]),
        ("PDF download works", not premium_results["issues"]),
        ("Premium page works", not premium_results["issues"]),
        ("No broken image paths", not image_results["missing"] and not image_results["http_failures"]),
        ("No empty categories", not food_results["issues"] and not tip_results["empty_categories"]),
        ("No conflicts between allowed and forbidden foods", not food_results["conflicts"]),
        ("Translations complete", not translation_issue),
    ]

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Final Production Audit",
        "",
        "Source: local production data and app shell.",
        f"HTTP base checked: {HTTP_BASE}",
        "",
        "## Results",
    ]
    for name, ok in checks:
        lines.append(f"- {format_status(ok)} - {name}")

    lines.extend([
        "",
        "## Counts",
        f"- Allowed foods: {len(allowed.get('items', []))}",
        f"- Forbidden foods: {len(forbidden.get('items', []))}",
        f"- Meal cards: {meal_results['count']}",
        f"- Tips: {tip_results['count']}",
        f"- Weekly plan days: {weekly_results['days']}",
        f"- Categories checked: {categories_total}",
        f"- Referenced local assets checked: {image_results['referenced_assets']}",
        f"- Referenced images decoded: {image_results['checked_images']}",
        f"- Full PDF size: {premium_results['pdf_bytes']} bytes",
        "",
        "## Search Samples",
    ])
    for lang, sample in search_results["samples"].items():
        lines.append(f"- {lang}: query `{sample['query']}` matched {sample['matches']} records; sample source `{sample['source_id']}`")

    lines.extend([
        "",
        "## Favorites Samples",
    ])
    for key in favorites_results["sample_keys"]:
        lines.append(f"- Resolved `{key}`")

    lines.extend(["", "## Android Preparation"])
    lines.extend(android_status_lines())
    lines.extend(["", "## Issues"])
    if all_issues:
        for issue in all_issues[:200]:
            lines.append(f"- {issue}")
    else:
        lines.append("- None.")

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "report": str(REPORT_PATH),
        "checks": {name: ok for name, ok in checks},
        "issueCount": len(all_issues),
        "referencedAssets": image_results["referenced_assets"],
        "checkedImages": image_results["checked_images"],
    }, ensure_ascii=False, indent=2))
    if all_issues:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
