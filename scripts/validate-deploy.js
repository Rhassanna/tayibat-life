const fs = require("fs");
const path = require("path");

const root = process.cwd();
const jsonFiles = [
  "data/foods_allowed.json",
  "data/foods_forbidden.json",
  "data/meals.json",
  "data/weekly_plans.json",
  "data/tips.json",
  "data/translations.json",
  "assets/config/admob.config.json",
  "assets/config/paypal.json",
  "manifest.webmanifest",
  "package.json",
  "capacitor.config.json"
];

for (const file of jsonFiles) {
  const fullPath = path.join(root, file);
  if (!fs.existsSync(fullPath)) {
    throw new Error(`Missing deploy file: ${file}`);
  }
  JSON.parse(fs.readFileSync(fullPath, "utf8"));
  console.log(`JSON OK ${file}`);
}

for (const file of ["index.html", "privacy.html", "app.js", "styles.css", "sw.js", "netlify.toml", "_redirects", "_headers"]) {
  const fullPath = path.join(root, file);
  if (!fs.existsSync(fullPath)) {
    throw new Error(`Missing deploy file: ${file}`);
  }
  console.log(`FILE OK ${file}`);
}

const textFiles = [
  ...jsonFiles,
  "index.html",
  "privacy.html",
  "app.js",
  "styles.css",
  "sw.js",
  "netlify.toml",
  "_redirects",
  "_headers"
];
const mojibakePattern = /(?:\u00c3[\u0080-\u00bf]|\u00c2[\u0080-\u00bf\s]|\u00e2[\u0080-\u00bf\u2019\u20ac\u2122\u0153\u201c]|\u00d8|\u00d9|\u00c5[\u0080-\u00bf\u2019\u201c]|\ufffd)/u;

for (const file of textFiles) {
  const contents = fs.readFileSync(path.join(root, file), "utf8");
  const match = contents.match(mojibakePattern);
  if (match) {
    throw new Error(`Mojibake marker found in ${file}: ${match[0]}`);
  }
  console.log(`ENCODING OK ${file}`);
}

for (const file of ["assets/logo.png", "assets/logo.webp", "assets/icon-192.png", "assets/icon-512.png", "assets/icon-512.webp"]) {
  const fullPath = path.join(root, file);
  if (!fs.existsSync(fullPath)) {
    throw new Error(`Missing image asset: ${file}`);
  }
  console.log(`IMAGE OK ${file}`);
}

const meals = JSON.parse(fs.readFileSync(path.join(root, "data/meals.json"), "utf8"));
for (const list of Object.values(meals.templates || {})) {
  for (const meal of list) {
    if (!meal.image) continue;
    const localImage = meal.image.replace(/^\.\//, "");
    const fullPath = path.join(root, localImage);
    if (!fs.existsSync(fullPath)) {
      throw new Error(`Missing meal image: ${meal.image}`);
    }
  }
}
console.log("MEAL IMAGES OK");
