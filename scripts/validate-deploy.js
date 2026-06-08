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

const productionAdMob = {
  androidAppId: "ca-app-pub-4441958861355825~6983634337",
  appId: "ca-app-pub-4441958861355825~6983634337",
  bannerAdUnitId: "ca-app-pub-4441958861355825/8264926419",
  interstitialAdUnitId: "ca-app-pub-4441958861355825/5478980972"
};

function readJson(relativePath) {
  return JSON.parse(fs.readFileSync(path.join(root, relativePath), "utf8"));
}

function assertEqual(actual, expected, label) {
  if (actual !== expected) {
    throw new Error(`${label}: expected ${JSON.stringify(expected)}, found ${JSON.stringify(actual)}`);
  }
}

function validateAdMobConfig(relativePath, expectedTestMode) {
  const config = readJson(relativePath);
  for (const [key, value] of Object.entries(productionAdMob)) {
    assertEqual(config[key], value, `${relativePath} ${key}`);
  }
  assertEqual(config.bannerEnabled, true, `${relativePath} bannerEnabled`);
  assertEqual(config.interstitialEnabled, true, `${relativePath} interstitialEnabled`);
  assertEqual(config.rewardedEnabled, false, `${relativePath} rewardedEnabled`);
  assertEqual(config.testMode, expectedTestMode, `${relativePath} testMode`);
  console.log(`ADMOB OK ${relativePath}`);
}

for (const file of jsonFiles) {
  const fullPath = path.join(root, file);
  if (!fs.existsSync(fullPath)) {
    throw new Error(`Missing deploy file: ${file}`);
  }
  readJson(file);
  console.log(`JSON OK ${file}`);
}

validateAdMobConfig("assets/config/admob.config.json", false);
validateAdMobConfig("android/app/src/debug/assets/public/assets/config/admob.config.json", true);
assertEqual(readJson("capacitor.config.json").appId, "com.tayibat.life", "capacitor.config.json appId");
console.log("ANDROID PACKAGE OK com.tayibat.life");

for (const file of ["index.html", "privacy.html", "app-ads.txt", "app.js", "styles.css", "sw.js", "netlify.toml", "_redirects", "_headers"]) {
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
  "app-ads.txt",
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
