const site = (process.argv[2] || process.env.SITE_URL || "https://tayibat-life.netlify.app").replace(/\/$/, "");

const files = [
  "data/foods_allowed.json",
  "data/foods_forbidden.json",
  "data/meals.json",
  "data/weekly_plans.json",
  "data/tips.json",
  "data/translations.json"
];

(async () => {
  for (const file of files) {
    const url = `${site}/${file}`;
    const response = await fetch(url, { redirect: "follow" });
    const text = await response.text();
    const first = text.trimStart().slice(0, 1);
    if (!response.ok) {
      throw new Error(`${url} returned HTTP ${response.status}`);
    }
    if (first === "<") {
      throw new Error(`${url} returned HTML instead of JSON`);
    }
    JSON.parse(text);
    console.log(`JSON OK ${url}`);
  }
})().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
