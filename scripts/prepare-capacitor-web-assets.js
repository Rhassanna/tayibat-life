const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const outDir = path.join(root, "www");

const requiredFiles = [
  "index.html",
  "app.js",
  "styles.css",
  "sw.js",
  "manifest.webmanifest",
  "privacy.html"
];

const optionalFiles = ["_headers", "_redirects"];
const requiredDirs = ["assets", "data"];

function copyEntry(relativePath) {
  const source = path.join(root, relativePath);
  const target = path.join(outDir, relativePath);

  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.cpSync(source, target, { recursive: true });
  console.log(`CAP WEB OK ${relativePath}`);
}

for (const relativePath of [...requiredFiles, ...requiredDirs]) {
  if (!fs.existsSync(path.join(root, relativePath))) {
    throw new Error(`Missing Capacitor web asset source: ${relativePath}`);
  }
}

fs.rmSync(outDir, { recursive: true, force: true });
fs.mkdirSync(outDir, { recursive: true });

for (const relativePath of requiredFiles) {
  copyEntry(relativePath);
}

for (const relativePath of optionalFiles) {
  if (fs.existsSync(path.join(root, relativePath))) {
    copyEntry(relativePath);
  }
}

for (const relativePath of requiredDirs) {
  copyEntry(relativePath);
}
