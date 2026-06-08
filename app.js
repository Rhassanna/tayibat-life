const APP_VERSION = "v83";
const SEO_TITLE = "Tayibat Life - Healthy Nutrition, Meal Planner and Wellness Tracker";

const ADMOB_CONFIG_FILE = "/assets/config/admob.config.json";
const ADMOB_DEFAULT_CONFIG = Object.freeze({
  androidAppId: "ca-app-pub-4441958861355825~6983634337",
  appId: "ca-app-pub-4441958861355825~6983634337",
  bannerEnabled: true,
  bannerAdUnitId: "ca-app-pub-4441958861355825/8264926419",
  interstitialEnabled: true,
  interstitialAdUnitId: "ca-app-pub-4441958861355825/5478980972",
  rewardedEnabled: false,
  rewardedAdUnitId: "",
  testMode: false
});
const ADMOB_INTERSTITIAL_STORAGE_KEY = "tayibat.admobInterstitial";
const ADMOB_INTERSTITIAL_SECTION_THRESHOLD = 4;
const ADMOB_INTERSTITIAL_TIP_THRESHOLD = 3;
const ADMOB_INTERSTITIAL_COOLDOWN_MS = 4 * 60 * 1000;
const PAYPAL_CONFIG_FILE = "/assets/config/paypal.json";
const PAYPAL_SUPPORT_EMAIL = "hassannariadi@gmail.com";
const PAYPAL_SUPPORT_MAILTO = "mailto:hassannariadi@gmail.com";
const SUPPORT_EMAIL = "hassannacreative@gmail.com";
const SUPPORT_MAILTO = "mailto:hassannacreative@gmail.com?subject=Tayibat%20Life%20Feedback";
const REVIEW_EMAIL_SUBJECT = "Tayibat Life Feedback & Review";
const PREMIUM_STORAGE_KEY = "tayibatPremium";
const PREMIUM_AMOUNT_STORAGE_KEY = "tayibatPremiumAmount";
const PREMIUM_DATE_STORAGE_KEY = "tayibatPremiumActivatedAt";
const PREMIUM_SOURCE_STORAGE_KEY = "tayibatPremiumSource";
const FULL_PDF_FILE = "./assets/pdfs/tayibat-system-full.pdf";
const IMAGE_FALLBACK = "./assets/icon-192.png";
const TIP_IMAGE_DIR = "./assets/tips/";
const FORBIDDEN_TIP_IMAGES = new Set(["./assets/logo.png", "./assets/logo.webp"]);

const DATA_FILES = {
  allowed: "/data/foods_allowed.json",
  forbidden: "/data/foods_forbidden.json",
  meals: "/data/meals.json",
  weekly: "/data/weekly_plans.json",
  tips: "/data/tips.json",
  translations: "/data/translations.json"
};

const SUPPORTED_LANGS = ["ar", "en", "fr", "es"];
const VALID_SUPPORT_CODES = new Set(["TAYIBAT-VIP-2026"]);
const WEEKLY_PLAN_DAY_COUNT = 7;

const VIEW_META = {
  home: { icon: "⌂", labelKey: "home" },
  search: { icon: "⌕", labelKey: "search" },
  favorites: { icon: "★", labelKey: "favorites" },
  notifications: { icon: "♧", labelKey: "notifications" },
  settings: { icon: "⚙", labelKey: "settings" }
};

const HOME_ACTIONS = [
  ["today", "🍽", "todayMeals", "meal"],
  ["allowed", "✓", "allowed", "allowed"],
  ["forbidden", "×", "forbidden", "forbidden"],
  ["weekly", "7", "weekly", "weekly"],
  ["tips", "☼", "tips", "tips"],
  ["water", "💧", "water", "water"],
  ["weight", "▥", "weight", "weight"],
  ["favorites", "★", "favorites", "favorite"],
  ["support", "♥", "supportApp", "support"],
  ["settings", "⚙", "settings", "settings"]
];

const DEFAULT_SETTINGS = {
  language: "auto",
  waterGoal: 2000,
  cupSize: 250,
  notifications: false,
  premium: false,
  supportCodeActivatedAt: "",
  premiumActivatedAt: "",
  premiumSupportAmount: "",
  premiumSource: "",
  disclaimerAccepted: false
};

const state = {
  view: "home",
  filter: { allowed: "all", forbidden: "all" },
  data: null,
  translations: null,
  settings: { ...DEFAULT_SETTINGS },
  favorites: [],
  mealSalt: 0,
  selectedWeekDay: 0,
  reminderTimers: [],
  pendingAdResolve: null,
  loadErrors: [],
  adMob: {
    config: null,
    initialized: false,
    nativeReady: false,
    bannerShown: false,
    interstitialShowing: false,
    sectionNavigationsSinceAd: 0,
    tipOpensSinceAd: 0,
    lastInterstitialAt: 0
  },
  paypal: {
    config: null,
    loadError: null
  }
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

window.addEventListener("DOMContentLoaded", init);

async function init() {
  state.settings = loadSettings();
  state.favorites = loadJSON("tayibat.favorites", []);
  applyInitialViewFromUrl();
  handlePremiumReturn();
  setDocumentLanguage();
  bindEvents();
  await loadData();
  if (isPremium()) hideAllAds();
  await initAdMob();
  registerServiceWorker();
  render();
  setupReminders();
}

function applyInitialViewFromUrl() {
  const requestedView = new URLSearchParams(window.location.search).get("view");
  const validViews = new Set(["home", "search", "today", "allowed", "forbidden", "weekly", "tips", "water", "weight", "favorites", "notifications", "support", "settings"]);
  if (validViews.has(requestedView)) state.view = requestedView;
}

async function loadData() {
  const entries = await Promise.all(
    Object.entries(DATA_FILES).map(async ([key, path]) => {
      const url = `${path}?${APP_VERSION}`;
      try {
        const response = await fetch(url, { cache: "no-cache" });
        if (!response.ok) {
          throw new Error(`HTTP ${response.status} ${response.statusText}`);
        }
        return [key, await response.json(), null];
      } catch (error) {
        const detail = { key, path, url, error: error.message || String(error) };
        console.error(`[Tayibat Life] Failed to load ${path}`, detail, error);
        return [key, fallbackDataFor(key), detail];
      }
    })
  );

  const loaded = Object.fromEntries(entries.map(([key, data]) => [key, data]));
  state.loadErrors = entries.map(([, , error]) => error).filter(Boolean);
  state.data = {
    allowed: loaded.allowed,
    forbidden: loaded.forbidden,
    meals: loaded.meals,
    weekly: loaded.weekly,
    tips: loaded.tips
  };
  state.translations = loaded.translations || fallbackTranslations();

  if (state.loadErrors.length) {
    console.warn("[Tayibat Life] Data loaded with fallbacks", state.loadErrors);
  }
}

function detectLanguage() {
  const lang = (navigator.language || "ar").slice(0, 2).toLowerCase();
  return SUPPORTED_LANGS.includes(lang) ? lang : "ar";
}

function setDocumentLanguage() {
  const lang = resolvedLanguage();
  document.documentElement.lang = lang;
  document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
  document.title = SEO_TITLE;
}

function t(key) {
  const lang = resolvedLanguage();
  return state.translations?.[lang]?.[key] || state.translations?.ar?.[key] || key;
}

function optionalTranslation(key) {
  const lang = resolvedLanguage();
  return state.translations?.[lang]?.[key] || state.translations?.ar?.[key] || "";
}

function resolvedLanguage() {
  const lang = state.settings.language === "auto" ? detectLanguage() : (state.settings.language || "ar");
  return SUPPORTED_LANGS.includes(lang) ? lang : "ar";
}

function localized(record, field) {
  if (!record) return "";
  const lang = resolvedLanguage();
  const localizedKey = `${field}_${lang}`;
  if (record[localizedKey] !== undefined) return record[localizedKey];
  if (lang !== "ar" && record[`${field}_en`] !== undefined) return record[`${field}_en`];
  if (record[`${field}_ar`] !== undefined) return record[`${field}_ar`];
  return record[field] ?? "";
}

function localizedArray(record, field) {
  const value = localized(record, field);
  if (Array.isArray(value)) return value;
  return value ? [value] : [];
}

function normalizeWeeklyPlanDays(plans) {
  const source = Array.isArray(plans) ? plans : [];
  if (!source.length) return [];
  return Array.from({ length: WEEKLY_PLAN_DAY_COUNT }, (_, index) => {
    const dayNumber = index + 1;
    return source.find((day) => Number(day?.day) === dayNumber) || source[index] || { day: dayNumber };
  });
}

function weeklyDayTabLabel(day, index) {
  const dayNumber = Number(day?.day) || index + 1;
  return optionalTranslation(`weekDay${dayNumber}`) || localized(day, "shortName") || localized(day, "name") || String(dayNumber);
}

function localizedObjectValue(record, field, key) {
  if (!record || !key) return "";
  const lang = resolvedLanguage();
  const localizedObject = record[`${field}_${lang}`] || (lang !== "ar" ? record[`${field}_en`] : null) || record[`${field}_ar`] || record[field];
  return localizedObject?.[key] || "";
}

function mealTypeLabelForDay(day, type) {
  return localizedObjectValue(day, "mealLabels", type) || t(type);
}

function localizedCategory(source, category) {
  const lang = resolvedLanguage();
  const index = source.categories.indexOf(category);
  return source[`categories_${lang}`]?.[index] || source.categories_ar?.[index] || category;
}

function multilingualHaystack(record, fields) {
  const values = [];
  fields.forEach((field) => {
    const base = record[field];
    if (Array.isArray(base)) values.push(...base);
    else if (base) values.push(base);
    SUPPORTED_LANGS.forEach((lang) => {
      const value = record[`${field}_${lang}`];
      if (Array.isArray(value)) values.push(...value);
      else if (value) values.push(value);
    });
  });
  return values.filter(Boolean).join(" ");
}

function listSeparator() {
  return resolvedLanguage() === "ar" ? "، " : ", ";
}

function formatProtein(grams) {
  return resolvedLanguage() === "ar" ? `${grams}غ` : `${grams}g`;
}

function isImagePath(value) {
  return typeof value === "string" && /\.(png|jpe?g|webp|gif|svg)$/i.test(value);
}

function normalizedImagePath(value) {
  return typeof value === "string" ? value.trim().replace(/\\/g, "/") : "";
}

function safeTipImagePath(value) {
  const image = normalizedImagePath(value);
  if (!image || FORBIDDEN_TIP_IMAGES.has(image)) return IMAGE_FALLBACK;
  return image.startsWith(TIP_IMAGE_DIR) && isImagePath(image) ? image : IMAGE_FALLBACK;
}

function imageFallbackHandler() {
  return `this.onerror=null;this.src='${IMAGE_FALLBACK}'`;
}

function renderSafeImage(src, alt, width, height, loading = "lazy") {
  const image = isImagePath(src) ? src : IMAGE_FALLBACK;
  return `<img src="${escapeAttr(image)}" alt="${escapeAttr(alt || "Tayibat Life")}" width="${width}" height="${height}" loading="${escapeAttr(loading)}" decoding="async" onerror="${escapeAttr(imageFallbackHandler())}">`;
}

function localizedImageAlt(record, fallback = "") {
  return localized(record, "alt") || fallback || localized(record, "name") || localized(record, "title") || "Tayibat Life";
}

function renderVisual(value, className = "result-icon", alt = "") {
  if (isImagePath(value)) {
    return `<span class="${className} image-visual">${renderSafeImage(value, alt, 64, 64)}</span>`;
  }
  return `<span class="${className}">${escapeHTML(value || "")}</span>`;
}

function searchSuggestions() {
  const suggestions = {
    ar: ["الأرز", "الدجاج", "زيت الزيتون", "المشروبات الغازية", "التمر", "البهارات"],
    en: ["Rice", "Chicken", "Olive oil", "Soft drinks", "Dates", "Spices"],
    fr: ["Riz", "Poulet", "Huile d'olive", "Boissons gazeuses", "Dattes", "Épices"],
    es: ["Arroz", "Pollo", "Aceite de oliva", "Bebidas gaseosas", "Dátiles", "Especias"]
  };
  return suggestions[resolvedLanguage()] || suggestions.ar;
}

function languageOptions() {
  const labels = {
    ar: [["auto", "تلقائي"], ["ar", "العربية"], ["en", "الإنجليزية"], ["fr", "الفرنسية"], ["es", "الإسبانية"]],
    en: [["auto", "Auto"], ["ar", "Arabic"], ["en", "English"], ["fr", "French"], ["es", "Spanish"]],
    fr: [["auto", "Auto"], ["ar", "Arabe"], ["en", "Anglais"], ["fr", "Français"], ["es", "Espagnol"]],
    es: [["auto", "Auto"], ["ar", "Árabe"], ["en", "Inglés"], ["fr", "Francés"], ["es", "Español"]]
  };
  return labels[resolvedLanguage()] || labels.ar;
}

function fallbackDataFor(key) {
  if (key === "allowed" || key === "forbidden") {
    return {
      source: {
        note_ar: "تعذر تحميل هذا الملف.",
        note_en: "This data file could not be loaded.",
        note_fr: "Ce fichier de données n’a pas pu être chargé.",
        note_es: "No se pudo cargar este archivo de datos."
      },
      categories: [],
      categories_ar: [],
      categories_en: [],
      categories_fr: [],
      categories_es: [],
      items: []
    };
  }
  if (key === "meals") {
    return {
      name_ar: "وجبات اليوم",
      name_en: "Today's Meals",
      name_fr: "Repas du jour",
      name_es: "Comidas de hoy",
      rules: [],
      templates: { breakfast: [], lunch: [], dinner: [], snack: [] }
    };
  }
  if (key === "weekly") {
    return {
      waterDefault_ar: "",
      waterDefault_en: "",
      waterDefault_fr: "",
      waterDefault_es: "",
      plans: []
    };
  }
  if (key === "tips") {
    return {
      tips: [{
        id: "fallback-tip",
        text_ar: "تعذر تحميل النصائح حالياً.",
        text_en: "Tips could not be loaded right now.",
        text_fr: "Les conseils ne peuvent pas être chargés pour le moment.",
        text_es: "No se pudieron cargar los consejos por ahora.",
        category_ar: "",
        category_en: "",
        category_fr: "",
        category_es: ""
      }]
    };
  }
  if (key === "translations") return fallbackTranslations();
  return {};
}

function fallbackTranslations() {
  const supportDefaults = {
    ar: {
      supportStatus: "حالة الدعم",
      supportActive: "الدعم مفعل",
      adsActive: "الإعلانات مفعلة",
      adsRemoved: "تم حذف الإعلانات",
      webAdsActive: "إعلانات الويب مفعلة",
      supportCodeTitle: "كود تفعيل الدعم",
      supportCodeIntro: "بعد الدعم عبر PayPal أدخل كود التفعيل لإزالة الإعلانات من هذا الجهاز.",
      activationCode: "كود التفعيل",
      activationCodePlaceholder: "مثال: TAYIBAT-VIP-2026",
      activateCode: "تفعيل الكود",
      activationSuccess: "تم تفعيل الدعم وإزالة الإعلانات.",
      activationInvalid: "كود التفعيل غير صحيح.",
      priorityUpdates: "أولوية في التحديثات الجديدة",
      earlyFeatureAccess: "الوصول المبكر للميزات الجديدة",
      directDeveloperSuggestions: "إمكانية إرسال اقتراحات مباشرة للمطور",
      requestFoodsRecipes: "طلب إضافة أطعمة أو وصفات جديدة",
      voteUpcomingFeatures: "التصويت على الميزات القادمة",
      supportFeedbackEyebrow: "ملاحظات واقتراحات",
      developerContactTitle: "تواصل مع المطور",
      developerContactBody: "إذا كانت لديك ملاحظات، تقييمات، اقتراحات، أو طلبات لإضافة ميزات جديدة، يمكنك التواصل معنا مباشرة عبر البريد الإلكتروني.",
      developerContactButton: "إرسال ملاحظة أو اقتراح",
      reviewTitle: "قيّم التطبيق وشارك ملاحظاتك",
      reviewIntro: "أرسل تقييمك أو ملاحظاتك أو اقتراحاتك أو بلاغات الأخطاء مباشرة إلى المطور.",
      reviewRatingLabel: "التقييم من 1 إلى 5 نجوم",
      reviewStars: "نجوم",
      reviewFeedbackLabel: "ملاحظاتك",
      reviewFeedbackPlaceholder: "اكتب رأيك في التطبيق أو تجربتك معه...",
      reviewAdditionsLabel: "ماذا يجب أن نضيف؟",
      reviewAdditionsPlaceholder: "ميزات جديدة، أطعمة، وصفات، خطط أسبوعية...",
      reviewImproveLabel: "ماذا يجب أن نحذف أو نحسّن؟",
      reviewImprovePlaceholder: "أجزاء غير واضحة، تصميم، نصوص، تجربة الاستخدام...",
      reviewBugLabel: "بلاغ عن مشكلة",
      reviewBugPlaceholder: "صف المشكلة، الصفحة، وما الذي حدث...",
      sendReview: "إرسال التقييم",
      sendDeveloperNote: "إرسال ملاحظة للمطور",
      reviewFeedbackRequired: "يرجى كتابة ملاحظة قبل الإرسال.",
      reviewEmailOpened: "تم فتح تطبيق البريد لإرسال ملاحظتك.",
      reviewQuickLike: "أعجبني التطبيق",
      reviewQuickSuggestion: "لدي اقتراح",
      reviewQuickBug: "وجدت مشكلة",
      reviewQuickFoodRecipe: "أريد إضافة طعام أو وصفة",
      reviewQuickLikeValue: "أعجبني التطبيق وأريد مشاركة تقييمي:",
      reviewQuickSuggestionValue: "لدي اقتراح لتحسين التطبيق:",
      reviewQuickBugValue: "وجدت مشكلة في التطبيق:",
      reviewQuickFoodRecipeValue: "أريد إضافة طعام أو وصفة جديدة:",
      premiumHeadline: "تجربة Premium بدون إعلانات وتواصل مباشر",
      premiumBody: "فعّل الدعم لإزالة الإعلانات، الحصول على شارة Premium، وإرسال الملاحظات والاقتراحات وطلبات إضافة أطعمة أو وصفات جديدة."
    },
    en: {
      supportStatus: "Support status",
      supportActive: "Support active",
      adsActive: "Ads active",
      adsRemoved: "Ads removed",
      webAdsActive: "Web ads active",
      supportCodeTitle: "Support activation code",
      supportCodeIntro: "After supporting via PayPal, enter your activation code to remove ads on this device.",
      activationCode: "Activation code",
      activationCodePlaceholder: "Example: TAYIBAT-VIP-2026",
      activateCode: "Activate code",
      activationSuccess: "Support activated and ads removed.",
      activationInvalid: "Invalid activation code.",
      priorityUpdates: "Priority for new updates",
      earlyFeatureAccess: "Early access to new features",
      directDeveloperSuggestions: "Send suggestions directly to the developer",
      requestFoodsRecipes: "Request new foods or recipes",
      voteUpcomingFeatures: "Vote on upcoming features",
      supportFeedbackEyebrow: "Feedback and suggestions",
      developerContactTitle: "Contact the developer",
      developerContactBody: "If you have feedback, ratings, suggestions, bug reports, or requests for new features, you can contact us directly by email.",
      developerContactButton: "Send feedback or suggestion",
      reviewTitle: "Rate the app and share your feedback",
      reviewIntro: "Send your rating, feedback, suggestions, or bug reports directly to the developer.",
      reviewRatingLabel: "Rating from 1 to 5 stars",
      reviewStars: "stars",
      reviewFeedbackLabel: "Feedback",
      reviewFeedbackPlaceholder: "Write your opinion of the app or your experience with it...",
      reviewAdditionsLabel: "What should we add?",
      reviewAdditionsPlaceholder: "New features, foods, recipes, weekly plans...",
      reviewImproveLabel: "What should we remove or improve?",
      reviewImprovePlaceholder: "Unclear parts, design, text, user experience...",
      reviewBugLabel: "Bug report",
      reviewBugPlaceholder: "Describe the issue, page, and what happened...",
      sendReview: "Send review",
      sendDeveloperNote: "Send note to developer",
      reviewFeedbackRequired: "Please write feedback before sending.",
      reviewEmailOpened: "Your email app was opened to send the feedback.",
      reviewQuickLike: "I like the app",
      reviewQuickSuggestion: "I have a suggestion",
      reviewQuickBug: "I found a problem",
      reviewQuickFoodRecipe: "I want to add a food or recipe",
      reviewQuickLikeValue: "I like the app and want to share my rating:",
      reviewQuickSuggestionValue: "I have a suggestion to improve the app:",
      reviewQuickBugValue: "I found a problem in the app:",
      reviewQuickFoodRecipeValue: "I want to add a new food or recipe:",
      premiumHeadline: "Premium ad-free experience and direct contact",
      premiumBody: "Activate support to remove ads, receive a Premium badge, and send feedback, suggestions, and requests for new foods or recipes."
    },
    fr: {
      supportStatus: "Statut du soutien",
      supportActive: "Soutien actif",
      adsActive: "Publicites actives",
      adsRemoved: "Publicites supprimees",
      webAdsActive: "Publicites web actives",
      supportCodeTitle: "Code d'activation du soutien",
      supportCodeIntro: "Apres le soutien via PayPal, entrez votre code d'activation pour supprimer les publicites sur cet appareil.",
      activationCode: "Code d'activation",
      activationCodePlaceholder: "Exemple : TAYIBAT-VIP-2026",
      activateCode: "Activer le code",
      activationSuccess: "Soutien active et publicites supprimees.",
      activationInvalid: "Code d'activation invalide.",
      priorityUpdates: "Priorite pour les nouvelles mises a jour",
      earlyFeatureAccess: "Acces anticipe aux nouvelles fonctionnalites",
      directDeveloperSuggestions: "Envoyer des suggestions directement au developpeur",
      requestFoodsRecipes: "Demander de nouveaux aliments ou recettes",
      voteUpcomingFeatures: "Voter pour les prochaines fonctionnalites",
      supportFeedbackEyebrow: "Avis et suggestions",
      developerContactTitle: "Contacter le developpeur",
      developerContactBody: "Si vous avez des avis, notes, suggestions, rapports de bugs ou demandes de nouvelles fonctionnalites, vous pouvez nous contacter directement par e-mail.",
      developerContactButton: "Envoyer un avis ou une suggestion",
      reviewTitle: "Notez l’application et partagez vos retours",
      reviewIntro: "Envoyez votre note, vos avis, suggestions ou rapports de bugs directement au developpeur.",
      reviewRatingLabel: "Note de 1 a 5 etoiles",
      reviewStars: "etoiles",
      reviewFeedbackLabel: "Avis",
      reviewFeedbackPlaceholder: "Ecrivez votre avis sur l’application ou votre experience...",
      reviewAdditionsLabel: "Que devons-nous ajouter ?",
      reviewAdditionsPlaceholder: "Nouvelles fonctionnalites, aliments, recettes, programmes hebdomadaires...",
      reviewImproveLabel: "Que devons-nous supprimer ou ameliorer ?",
      reviewImprovePlaceholder: "Parties peu claires, design, textes, experience utilisateur...",
      reviewBugLabel: "Rapport de bug",
      reviewBugPlaceholder: "Decrivez le probleme, la page et ce qui s’est passe...",
      sendReview: "Envoyer l’avis",
      sendDeveloperNote: "Envoyer un message au developpeur",
      reviewFeedbackRequired: "Veuillez ecrire un avis avant l’envoi.",
      reviewEmailOpened: "Votre application e-mail a ete ouverte pour envoyer le retour.",
      reviewQuickLike: "J’aime l’application",
      reviewQuickSuggestion: "J’ai une suggestion",
      reviewQuickBug: "J’ai trouve un probleme",
      reviewQuickFoodRecipe: "Je veux ajouter un aliment ou une recette",
      reviewQuickLikeValue: "J’aime l’application et je veux partager ma note :",
      reviewQuickSuggestionValue: "J’ai une suggestion pour ameliorer l’application :",
      reviewQuickBugValue: "J’ai trouve un probleme dans l’application :",
      reviewQuickFoodRecipeValue: "Je veux ajouter un nouvel aliment ou une recette :",
      premiumHeadline: "Experience Premium sans publicite et contact direct",
      premiumBody: "Activez le soutien pour supprimer les publicites, recevoir un badge Premium et envoyer des avis, suggestions ou demandes de nouveaux aliments et recettes."
    },
    es: {
      supportStatus: "Estado del apoyo",
      supportActive: "Apoyo activo",
      adsActive: "Anuncios activos",
      adsRemoved: "Anuncios eliminados",
      webAdsActive: "Anuncios web activos",
      supportCodeTitle: "Codigo de activacion de apoyo",
      supportCodeIntro: "Despues de apoyar por PayPal, introduce tu codigo de activacion para quitar anuncios en este dispositivo.",
      activationCode: "Codigo de activacion",
      activationCodePlaceholder: "Ejemplo: TAYIBAT-VIP-2026",
      activateCode: "Activar codigo",
      activationSuccess: "Apoyo activado y anuncios eliminados.",
      activationInvalid: "Codigo de activacion no valido.",
      priorityUpdates: "Prioridad en las nuevas actualizaciones",
      earlyFeatureAccess: "Acceso anticipado a nuevas funciones",
      directDeveloperSuggestions: "Enviar sugerencias directamente al desarrollador",
      requestFoodsRecipes: "Solicitar nuevos alimentos o recetas",
      voteUpcomingFeatures: "Votar por las proximas funciones",
      supportFeedbackEyebrow: "Opiniones y sugerencias",
      developerContactTitle: "Contactar al desarrollador",
      developerContactBody: "Si tienes comentarios, valoraciones, sugerencias, informes de errores o solicitudes de nuevas funciones, puedes contactarnos directamente por correo electronico.",
      developerContactButton: "Enviar comentario o sugerencia",
      reviewTitle: "Valora la app y comparte tus comentarios",
      reviewIntro: "Envia tu valoracion, comentarios, sugerencias o informes de errores directamente al desarrollador.",
      reviewRatingLabel: "Valoracion de 1 a 5 estrellas",
      reviewStars: "estrellas",
      reviewFeedbackLabel: "Comentarios",
      reviewFeedbackPlaceholder: "Escribe tu opinion sobre la app o tu experiencia...",
      reviewAdditionsLabel: "¿Que deberiamos añadir?",
      reviewAdditionsPlaceholder: "Nuevas funciones, alimentos, recetas, planes semanales...",
      reviewImproveLabel: "¿Que deberiamos eliminar o mejorar?",
      reviewImprovePlaceholder: "Partes poco claras, diseño, textos, experiencia de uso...",
      reviewBugLabel: "Informe de error",
      reviewBugPlaceholder: "Describe el problema, la pantalla y lo que ocurrio...",
      sendReview: "Enviar valoracion",
      sendDeveloperNote: "Enviar nota al desarrollador",
      reviewFeedbackRequired: "Escribe un comentario antes de enviar.",
      reviewEmailOpened: "Se abrio tu app de correo para enviar los comentarios.",
      reviewQuickLike: "Me gusta la app",
      reviewQuickSuggestion: "Tengo una sugerencia",
      reviewQuickBug: "Encontre un problema",
      reviewQuickFoodRecipe: "Quiero añadir un alimento o receta",
      reviewQuickLikeValue: "Me gusta la app y quiero compartir mi valoracion:",
      reviewQuickSuggestionValue: "Tengo una sugerencia para mejorar la app:",
      reviewQuickBugValue: "Encontre un problema en la app:",
      reviewQuickFoodRecipeValue: "Quiero añadir un nuevo alimento o receta:",
      premiumHeadline: "Experiencia Premium sin anuncios y contacto directo",
      premiumBody: "Activa el apoyo para eliminar anuncios, recibir una insignia Premium y enviar comentarios, sugerencias o solicitudes de nuevos alimentos y recetas."
    }
  };
  const common = { appName: "Tayibat Life", adBanner: "Banner Ad", premiumUnlocked: "Premium" };
  return {
    ar: {
      ...common,
      ...supportDefaults.ar,
      appNameLocal: "نظام طيبات",
      tagline: "دليلك اليومي للحياة الصحية المتوازنة",
      searchPlaceholder: "ابحث عن طعام أو مشروب أو نصيحة...",
      todayMeals: "وجبات اليوم",
      allowed: "قائمة المسموح",
      forbidden: "قائمة الممنوع",
      weekly: "برنامج الأسبوع",
      tips: "نصائح يومية",
      water: "تتبع الماء",
      weight: "تتبع الوزن",
      favorites: "المفضلة",
      settings: "الإعدادات",
      supportApp: "ادعم التطبيق",
      supportTitle: "ادعم تطبيق Tayibat Life",
      supportEyebrow: "دعم مميز",
      supportMessage: "الدعم يساعد على تطوير Tayibat Life، إزالة الإعلانات، وإعطاء الأولوية لملاحظاتك واقتراحاتك وطلبات الميزات الجديدة.",
      smallSupport: "دعم بسيط",
      supporter: "داعم",
      premiumSupporter: "داعم مميز",
      goldSupporter: "داعم ذهبي",
      customAmount: "مبلغ مخصص",
      customAmountPlaceholder: "أدخل المبلغ",
      donateNow: "الدعم عبر PayPal",
      paypalUnavailable: "رابط PayPal غير متوفر حالياً. يرجى ضبط ملف الإعدادات أولاً.",
      openingPayPal: "يتم فتح PayPal...",
      premiumBenefits: "مزايا Premium للداعمين",
      removeAds: "إزالة الإعلانات",
      extraWeeklyPlans: "برامج أسبوعية إضافية",
      premiumPdfs: "ملفات PDF مميزة",
      exclusiveHealthContent: "محتوى صحي حصري",
      supportFutureUpdates: "دعم التحديثات القادمة",
      supportFooter: "شكراً لدعمك تطوير Tayibat Life وتجربة صحية أفضل.",
      notifications: "الإشعارات",
      home: "الرئيسية",
      search: "البحث",
      back: "رجوع",
      dailyTip: "نصيحة اليوم",
      addFavorite: "إضافة للمفضلة",
      removeFavorite: "إزالة من المفضلة",
      newMeals: "توليد وجبات جديدة",
      mealGuideEyebrow: "وجبات من نظام طيبات",
      mealGuideIntro: "وجبات يومية مبنية على المسموح في الكتاب.",
      breakfast: "الفطور",
      lunch: "الغداء",
      dinner: "العشاء",
      snack: "سناك",
      ingredients: "المكونات",
      allowedLibraryEyebrow: "مكتبة المسموح",
      forbiddenLibraryEyebrow: "مكتبة التنبيهات",
      weeklyPlannerEyebrow: "مخطط 7 أيام",
      weekDay1: "الأول",
      weekDay2: "الثاني",
      weekDay3: "الثالث",
      weekDay4: "الرابع",
      weekDay5: "الخامس",
      weekDay6: "السادس",
      weekDay7: "السابع",
      hydrationEyebrow: "الترطيب",
      progressEyebrow: "التقدم",
      savedEyebrow: "المحفوظات",
      remindersEyebrow: "التذكيرات",
      profileEyebrow: "الملف الشخصي",
      kcal: "سعرة حرارية",
      protein: "بروتين",
      statusAllowed: "مسموح",
      statusForbidden: "ممنوع",
      ads: "الإعلانات",
      noResults: "لا توجد نتائج.",
      dataWarningTitle: "تم تحميل التطبيق مع بيانات ناقصة",
      dataWarningBody: "بعض ملفات البيانات لم تُحمّل. يمكنك استعمال التطبيق، والملفات المتأثرة ظاهرة هنا.",
      medicalDisclaimerTitle: "تنبيه صحي",
      medicalDisclaimerBody: "هذا التطبيق يقدم معلومات غذائية عامة ولا يغني عن استشارة الطبيب أو المختص.",
      privacyPolicy: "سياسة الخصوصية",
      close: "إغلاق",
      deleteWeight: "حذف الوزن",
      understood: "فهمت"
    },
    en: {
      ...common,
      ...supportDefaults.en,
      appNameLocal: "Tayibat System",
      tagline: "Your daily guide to balanced healthy living",
      searchPlaceholder: "Search food, drinks, herbs, meals, tips...",
      todayMeals: "Today's Meals",
      allowed: "Allowed Foods",
      forbidden: "Forbidden Foods",
      weekly: "Weekly Plan",
      tips: "Daily Tips",
      water: "Water Tracker",
      weight: "Weight Tracker",
      favorites: "Favorites",
      settings: "Settings",
      supportApp: "Support the App",
      supportTitle: "Support Tayibat Life",
      supportEyebrow: "Premium Support",
      supportMessage: "Support helps improve Tayibat Life, remove ads, and give priority to your feedback, ratings, suggestions, and feature requests.",
      smallSupport: "Small Support",
      supporter: "Supporter",
      premiumSupporter: "Premium Supporter",
      goldSupporter: "Gold Supporter",
      customAmount: "Custom Amount",
      customAmountPlaceholder: "Enter amount",
      donateNow: "Support via PayPal",
      paypalUnavailable: "PayPal link is not available yet. Please configure the PayPal settings file first.",
      openingPayPal: "Opening PayPal...",
      premiumBenefits: "Premium supporter benefits",
      removeAds: "Remove ads",
      extraWeeklyPlans: "Extra weekly plans",
      premiumPdfs: "Premium PDFs",
      exclusiveHealthContent: "Exclusive health content",
      supportFutureUpdates: "Support future updates",
      supportFooter: "Thank you for supporting Tayibat Life and a better healthy-living experience.",
      notifications: "Notifications",
      home: "Home",
      search: "Search",
      back: "Back",
      dailyTip: "Daily Tip",
      addFavorite: "Add to Favorites",
      removeFavorite: "Remove Favorite",
      newMeals: "Generate New Meals",
      mealGuideEyebrow: "Tayibat Food System",
      mealGuideIntro: "Daily meals built from the allowed foods in the book.",
      breakfast: "Breakfast",
      lunch: "Lunch",
      dinner: "Dinner",
      snack: "Snack",
      ingredients: "Ingredients",
      allowedLibraryEyebrow: "Allowed Library",
      forbiddenLibraryEyebrow: "Warning Library",
      weeklyPlannerEyebrow: "7-Day Planner",
      weekDay1: "Day 1",
      weekDay2: "Day 2",
      weekDay3: "Day 3",
      weekDay4: "Day 4",
      weekDay5: "Day 5",
      weekDay6: "Day 6",
      weekDay7: "Day 7",
      hydrationEyebrow: "Hydration",
      progressEyebrow: "Progress",
      savedEyebrow: "Saved",
      remindersEyebrow: "Reminders",
      profileEyebrow: "Profile",
      kcal: "kcal",
      protein: "Protein",
      statusAllowed: "Allowed",
      statusForbidden: "Forbidden",
      ads: "Ads",
      noResults: "No results.",
      dataWarningTitle: "App loaded with missing data",
      dataWarningBody: "Some data files did not load. You can still use the app; affected files are listed here.",
      medicalDisclaimerTitle: "Health Disclaimer",
      medicalDisclaimerBody: "This app provides general nutrition information and does not replace medical advice.",
      privacyPolicy: "Privacy Policy",
      close: "Close",
      deleteWeight: "Delete weight entry",
      understood: "Understood"
    },
    fr: {
      ...common,
      ...supportDefaults.fr,
      appNameLocal: "Système Tayibat",
      tagline: "Votre guide quotidien pour une vie saine et équilibrée",
      searchPlaceholder: "Rechercher aliments, boissons, herbes, repas, conseils...",
      todayMeals: "Repas du jour",
      allowed: "Aliments autorisés",
      forbidden: "Aliments interdits",
      weekly: "Programme hebdomadaire",
      tips: "Conseils quotidiens",
      water: "Suivi de l'eau",
      weight: "Suivi du poids",
      favorites: "Favoris",
      settings: "Paramètres",
      supportApp: "Soutenir l'application",
      supportTitle: "Soutenir Tayibat Life",
      supportEyebrow: "Soutien premium",
      supportMessage: "Le soutien aide à améliorer Tayibat Life, supprimer les publicités et donner la priorité à vos avis, notes, suggestions et demandes de fonctionnalités.",
      smallSupport: "Petit soutien",
      supporter: "Soutien",
      premiumSupporter: "Soutien premium",
      goldSupporter: "Soutien or",
      customAmount: "Montant personnalisé",
      customAmountPlaceholder: "Saisir le montant",
      donateNow: "Soutenir via PayPal",
      paypalUnavailable: "Le lien PayPal n'est pas encore disponible. Veuillez d'abord configurer le fichier PayPal.",
      openingPayPal: "Ouverture de PayPal...",
      premiumBenefits: "Avantages des soutiens premium",
      removeAds: "Supprimer les publicités",
      extraWeeklyPlans: "Programmes hebdomadaires supplémentaires",
      premiumPdfs: "PDF premium",
      exclusiveHealthContent: "Contenu santé exclusif",
      supportFutureUpdates: "Soutenir les futures mises à jour",
      supportFooter: "Merci de soutenir Tayibat Life et une meilleure expérience de vie saine.",
      notifications: "Notifications",
      home: "Accueil",
      search: "Recherche",
      back: "Retour",
      dailyTip: "Conseil du jour",
      addFavorite: "Ajouter aux favoris",
      removeFavorite: "Retirer des favoris",
      newMeals: "Générer des repas",
      mealGuideEyebrow: "Système alimentaire Tayibat",
      mealGuideIntro: "Repas du jour composés des aliments autorisés du livre.",
      breakfast: "Petit-déjeuner",
      lunch: "Déjeuner",
      dinner: "Dîner",
      snack: "Collation",
      ingredients: "Ingrédients",
      allowedLibraryEyebrow: "Bibliothèque autorisée",
      forbiddenLibraryEyebrow: "Bibliothèque d'alertes",
      weeklyPlannerEyebrow: "Planificateur 7 jours",
      weekDay1: "Jour 1",
      weekDay2: "Jour 2",
      weekDay3: "Jour 3",
      weekDay4: "Jour 4",
      weekDay5: "Jour 5",
      weekDay6: "Jour 6",
      weekDay7: "Jour 7",
      hydrationEyebrow: "Hydratation",
      progressEyebrow: "Progression",
      savedEyebrow: "Enregistrés",
      remindersEyebrow: "Rappels",
      profileEyebrow: "Profil",
      kcal: "kcal",
      protein: "Protéines",
      statusAllowed: "Autorisé",
      statusForbidden: "Interdit",
      ads: "Publicités",
      noResults: "Aucun résultat.",
      dataWarningTitle: "Application chargée avec des données manquantes",
      dataWarningBody: "Certains fichiers de données n’ont pas été chargés. L’application reste utilisable; les fichiers concernés sont listés ici.",
      medicalDisclaimerTitle: "Avertissement santé",
      medicalDisclaimerBody: "Cette application fournit des informations nutritionnelles générales et ne remplace pas un avis médical.",
      privacyPolicy: "Politique de confidentialité",
      close: "Fermer",
      deleteWeight: "Supprimer le poids",
      understood: "Compris"
    },
    es: {
      ...common,
      ...supportDefaults.es,
      appNameLocal: "Sistema Tayibat",
      tagline: "Tu guía diaria para una vida saludable y equilibrada",
      searchPlaceholder: "Buscar alimentos, bebidas, hierbas, comidas, consejos...",
      todayMeals: "Comidas de hoy",
      allowed: "Permitidos",
      forbidden: "Prohibidos",
      weekly: "Plan semanal",
      tips: "Consejos diarios",
      water: "Agua",
      weight: "Peso",
      favorites: "Favoritos",
      settings: "Ajustes",
      supportApp: "Apoyar la app",
      supportTitle: "Apoya Tayibat Life",
      supportEyebrow: "Apoyo premium",
      supportMessage: "El apoyo ayuda a mejorar Tayibat Life, quitar anuncios y dar prioridad a tus comentarios, valoraciones, sugerencias y solicitudes de funciones.",
      smallSupport: "Apoyo pequeño",
      supporter: "Colaborador",
      premiumSupporter: "Colaborador premium",
      goldSupporter: "Colaborador oro",
      customAmount: "Cantidad personalizada",
      customAmountPlaceholder: "Ingresa la cantidad",
      donateNow: "Apoyar con PayPal",
      paypalUnavailable: "El enlace de PayPal aún no está disponible. Configura primero el archivo de PayPal.",
      openingPayPal: "Abriendo PayPal...",
      premiumBenefits: "Beneficios de colaborador premium",
      removeAds: "Eliminar anuncios",
      extraWeeklyPlans: "Planes semanales extra",
      premiumPdfs: "PDF premium",
      exclusiveHealthContent: "Contenido de salud exclusivo",
      supportFutureUpdates: "Apoyar futuras actualizaciones",
      supportFooter: "Gracias por apoyar Tayibat Life y una mejor experiencia de vida saludable.",
      notifications: "Notificaciones",
      home: "Inicio",
      search: "Buscar",
      back: "Atrás",
      dailyTip: "Consejo del día",
      addFavorite: "Añadir a favoritos",
      removeFavorite: "Quitar favorito",
      newMeals: "Generar comidas",
      mealGuideEyebrow: "Sistema alimentario Tayibat",
      mealGuideIntro: "Comidas diarias basadas en los alimentos permitidos del libro.",
      breakfast: "Desayuno",
      lunch: "Almuerzo",
      dinner: "Cena",
      snack: "Snack",
      ingredients: "Ingredientes",
      allowedLibraryEyebrow: "Biblioteca permitida",
      forbiddenLibraryEyebrow: "Biblioteca de avisos",
      weeklyPlannerEyebrow: "Plan de 7 días",
      weekDay1: "Día 1",
      weekDay2: "Día 2",
      weekDay3: "Día 3",
      weekDay4: "Día 4",
      weekDay5: "Día 5",
      weekDay6: "Día 6",
      weekDay7: "Día 7",
      hydrationEyebrow: "Hidratación",
      progressEyebrow: "Progreso",
      savedEyebrow: "Guardados",
      remindersEyebrow: "Recordatorios",
      profileEyebrow: "Perfil",
      kcal: "kcal",
      protein: "Proteína",
      statusAllowed: "Permitido",
      statusForbidden: "Prohibido",
      ads: "Anuncios",
      noResults: "Sin resultados.",
      dataWarningTitle: "La app cargó con datos faltantes",
      dataWarningBody: "Algunos archivos de datos no se cargaron. La app sigue disponible; los archivos afectados aparecen aquí.",
      medicalDisclaimerTitle: "Aviso de salud",
      medicalDisclaimerBody: "Esta aplicación proporciona información nutricional general y no reemplaza el consejo médico.",
      privacyPolicy: "Política de privacidad",
      close: "Cerrar",
      deleteWeight: "Eliminar peso",
      understood: "Entendido"
    }
  };
}

function bindEvents() {
  document.addEventListener("click", handleClick);
  document.addEventListener("input", handleInput);
  document.addEventListener("change", handleChange);
  $("#modal-root").addEventListener("click", handleModalClick, true);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && event.target.id === "support-code-input") {
      event.preventDefault();
      activateSupportCode();
    }
    if ((event.key === "Enter" || event.key === " ") && event.target.closest?.("[data-tip-open]")) {
      event.preventDefault();
      openTipDetail(event.target.closest("[data-tip-open]").dataset.tipId);
    }
    if (event.key === "Escape") closeModal();
  });
}

function handleModalClick(event) {
  const closeAction = event.target.closest('button[data-action="close-modal"], button[data-action="ad-close"]');
  if (closeAction && $("#modal-root").contains(closeAction)) {
    event.preventDefault();
    event.stopPropagation();
    closeModal();
    return;
  }

  if (event.target.classList?.contains("modal-backdrop")) {
    event.preventDefault();
    event.stopPropagation();
    closeModal();
  }
}

function handleClick(event) {
  const viewButton = event.target.closest("[data-view]");
  if (viewButton) {
    navigate(viewButton.dataset.view);
    return;
  }

  const filterButton = event.target.closest("[data-filter-kind]");
  if (filterButton) {
    state.filter[filterButton.dataset.filterKind] = filterButton.dataset.filter;
    render();
    return;
  }

  const weekDayTab = event.target.closest(".week-day-tab[data-day]");
  if (weekDayTab) {
    const nextDay = Number(weekDayTab.dataset.day);
    if (Number.isFinite(nextDay)) {
      state.selectedWeekDay = nextDay;
      render();
    }
    return;
  }

  const foodButton = event.target.closest("[data-food-id]");
  if (foodButton) {
    openFoodDetail(foodButton.dataset.foodId, foodButton.dataset.foodStatus);
    return;
  }

  const tipCard = event.target.closest("[data-tip-open]");
  if (tipCard && (tipCard.tagName === "BUTTON" || !event.target.closest("button, a, input, select, textarea"))) {
    openTipDetail(tipCard.dataset.tipId);
    return;
  }

  const suggestionButton = event.target.closest("[data-search-term]");
  if (suggestionButton) {
    const input = $("#global-search");
    const term = suggestionButton.dataset.searchTerm || "";
    if (input) {
      input.value = term;
      input.focus();
    }
    renderSearchResults(term);
    return;
  }

  const action = event.target.closest("[data-action]");
  if (!action) return;

  const name = action.dataset.action;
  if (name === "close-modal") closeModal();
  if (name === "generate-meals") {
    state.mealSalt += 1;
    render();
  }
  if (name === "toggle-favorite") {
    toggleFavorite(action.dataset.favoriteType, action.dataset.favoriteId, action.dataset.favoriteStatus || "");
  }
  if (name === "share-tip") shareTip(action.dataset.tipId);
  if (name === "add-cup") addWaterCup();
  if (name === "undo-cup") addWaterCup(-1);
  if (name === "reset-water") resetWater();
  if (name === "save-weight") saveWeight();
  if (name === "delete-weight") deleteWeight(action.dataset.date);
  if (name === "download-weekly") downloadWeeklyPlan();
  if (name === "enable-notifications") enableNotifications();
  if (name === "test-notification") sendNotification(t("appNameLocal"), t("mealWaterReminder"));
  if (name === "ad-continue") resolveAd(true);
  if (name === "ad-close") closeModal();
  if (name === "accept-disclaimer") acceptDisclaimer();
  if (name === "support-donate") openSupportDonation(action);
  if (name === "activate-support-code") activateSupportCode();
  if (name === "restore-premium") restorePremiumAccess();
  if (name === "set-review-rating") setReviewRating(action);
  if (name === "set-review-template") applyReviewTemplate(action);
  if (name === "send-review") sendReviewEmail(action);
}

function handleInput(event) {
  if (event.target.id === "global-search") {
    renderSearchResults(event.target.value);
  }

  if (event.target.id === "water-goal") {
    state.settings.waterGoal = clampNumber(event.target.value, 250, 6000, 2000);
    saveSettings();
    renderWaterProgressOnly();
  }

  if (event.target.id === "cup-size") {
    state.settings.cupSize = clampNumber(event.target.value, 50, 1000, 250);
    saveSettings();
  }
}

function handleChange(event) {
  if (event.target.id === "language-select") {
    state.settings.language = event.target.value;
    saveSettings();
    setDocumentLanguage();
    render();
  }

  if (event.target.id === "notifications-toggle") {
    state.settings.notifications = event.target.checked;
    saveSettings();
    if (event.target.checked) enableNotifications();
    setupReminders();
    render();
  }
}

function navigate(view) {
  const previousView = state.view;
  state.view = view;
  render();
  resetScroll();
  if (view !== previousView && view !== "home") {
    recordSectionNavigationForInterstitial(view);
  }
  if (view === "support") {
    trackAnalytics("support_page_opened");
  }
}

function render() {
  if (!state.data || !state.translations) return;
  setDocumentLanguage();
  const app = $("#app");
  const viewHeading = state.view === "home" ? "" : `<h1 class="sr-only">${escapeHTML(`${getViewTitle()} - ${t("appName")}`)}</h1>`;
  app.innerHTML = `
    ${renderTopbar()}
    <main class="main">${viewHeading}${renderView()}</main>
    ${renderAdBanner()}
    ${renderBottomNav()}
  `;
  afterRender();
}

function resetScroll() {
  requestAnimationFrame(() => {
    window.scrollTo(0, 0);
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;
  });
}

function renderTopbar() {
  const title = getViewTitle();
  const isHome = state.view === "home";
  return `
    <header class="topbar ${isHome ? "home-topbar" : "inner-topbar"}">
      ${isHome ? `<button class="icon-button ghost-button" data-view="notifications" aria-label="${escapeAttr(t("notifications"))}">♧</button>` : `<button class="icon-button ghost-button" data-view="home" aria-label="${escapeAttr(t("back"))}">‹</button>`}
      <button class="brand" data-view="home" aria-label="${escapeHTML(t("appNameLocal"))}">
        ${brandLogo("header-logo")}
        <span class="brand-title">
          <strong>${isHome ? escapeHTML(t("appName")) : escapeHTML(title)}</strong>
          <span>${escapeHTML(t("appNameLocal"))}</span>
        </span>
      </button>
      ${isHome ? `<button class="icon-button ghost-button" data-view="settings" aria-label="${escapeHTML(t("settings"))}">☰</button>` : `<span class="status-pill">✓ ${escapeHTML(t("offlineReady"))}</span>`}
    </header>
  `;
}

function brandLogo(className = "") {
  return `
    <picture class="brand-logo-wrap">
      <source srcset="./assets/logo.webp" type="image/webp">
      <img class="${escapeAttr(className)}" src="./assets/logo.png" alt="Tayibat Life" width="48" height="48" loading="eager" decoding="async" onerror="this.onerror=null;this.src='./assets/icon-192.png'">
    </picture>
  `;
}

function renderBottomNav() {
  return `
    <nav class="bottom-nav" aria-label="Navigation">
      <div class="nav-scroller">
        ${Object.entries(VIEW_META).map(([key, meta]) => `
          <button class="nav-button ${state.view === key ? "is-active" : ""}" data-view="${key}">
            <span>${meta.icon}</span>
            <span>${escapeHTML(t(meta.labelKey))}</span>
          </button>
        `).join("")}
      </div>
    </nav>
  `;
}

function renderAdBanner() {
  if (isPremium()) return "";
  if (state.view !== "home") return "";
  if (state.adMob.config && !state.adMob.config.bannerEnabled) return "";
  if (state.adMob.nativeReady && state.adMob.bannerShown) return "";
  return `
    <aside class="ad-banner" aria-label="${escapeHTML(t("ads"))}">
      <div class="ad-banner-inner">AdMob ${escapeHTML(t("adBanner"))}</div>
    </aside>
  `;
}

function renderView() {
  const views = {
    home: renderHome,
    search: renderSearchPage,
    today: renderTodayMeals,
    allowed: () => renderFoodDirectory("allowed"),
    forbidden: () => renderFoodDirectory("forbidden"),
    weekly: renderWeeklyPlan,
    tips: renderTips,
    water: renderWaterTracker,
    weight: renderWeightTracker,
    favorites: renderFavorites,
    notifications: renderNotifications,
    support: renderSupport,
    settings: renderSettings
  };
  return (views[state.view] || renderHome)();
}

function getViewTitle() {
  const titles = {
    home: t("appNameLocal"),
    search: t("smartSearch"),
    today: t("todayMeals"),
    allowed: t("allowed"),
    forbidden: t("forbidden"),
    weekly: t("weekly"),
    tips: t("tips"),
    water: t("water"),
    weight: t("weight"),
    favorites: t("favorites"),
    notifications: t("notifications"),
    support: t("supportApp"),
    settings: t("settings")
  };
  return titles[state.view] || t("appNameLocal");
}

function renderHome() {
  const allowedCount = state.data.allowed.items?.length || 0;
  const forbiddenCount = state.data.forbidden.items?.length || 0;
  const tipsCount = state.data.tips.tips?.length || 0;
  const tip = getDailyTip();
  return `
    ${renderLoadWarnings()}

    <section class="hero premium-hero">
      <div class="hero-visual" aria-hidden="true">
        <div class="hero-leaf">
          ${renderSafeImage("./assets/hero/tayibat-cover.webp", "Tayibat Life", 800, 450, "eager").replace("<img ", '<img fetchpriority="high" ')}
        </div>
      </div>
      <div class="hero-copy">
        <h1>${escapeHTML(t("appNameLocal"))}</h1>
        <h2>${escapeHTML(t("appName"))}</h2>
        <p>${escapeHTML(t("tagline"))}</p>
      </div>
    </section>

    ${renderSearchBox()}

    <section class="actions-grid">
      ${HOME_ACTIONS.map(([view, icon, label, tone]) => `
        <button class="action-button tone-${tone}" data-view="${view}">
          <span class="icon">${icon}</span>
          <span class="label">${escapeHTML(t(label))}</span>
        </button>
      `).join("")}
    </section>

    <section class="tip-card featured">
      ${renderTipMedia(tip, true)}
      <div class="tip-content">
        <span class="tip-category">${escapeHTML(localized(tip, "category"))}</span>
        <h3 class="tip-title">${escapeHTML(localized(tip, "title") || t("dailyTip"))}</h3>
        <p class="tip-description">${escapeHTML(localized(tip, "text"))}</p>
      </div>
      <div class="tip-actions">
        ${favoriteButton("tip", tip.id)}
      </div>
    </section>

    <section class="quick-stats">
      <div class="stat"><strong>${allowedCount}</strong><span>${escapeHTML(t("allowed"))}</span></div>
      <div class="stat"><strong>${forbiddenCount}</strong><span>${escapeHTML(t("forbidden"))}</span></div>
      <div class="stat"><strong>${tipsCount}</strong><span>${escapeHTML(t("tips"))}</span></div>
    </section>
  `;
}

function renderLoadWarnings() {
  if (!state.loadErrors.length) return "";
  return `
    <section class="data-warning" role="alert">
      <strong>${escapeHTML(t("dataWarningTitle"))}</strong>
      <p>${escapeHTML(t("dataWarningBody"))}</p>
      <ul>
        ${state.loadErrors.map((item) => `<li><code>${escapeHTML(item.path)}</code>: ${escapeHTML(item.error)}</li>`).join("")}
      </ul>
    </section>
  `;
}

function renderSearchBox() {
  return `
    <section class="search-zone">
      <div class="search-box">
        <span>⌕</span>
        <input id="global-search" type="search" placeholder="${escapeHTML(t("searchPlaceholder"))}" autocomplete="off">
      </div>
      <div id="search-results" class="result-list" aria-live="polite"></div>
    </section>
  `;
}

function renderSearchPage() {
  return `
    <section class="section-head premium-title">
      <div>
        <span class="eyebrow">${escapeHTML(t("smartSearchEyebrow"))}</span>
        <h2>${escapeHTML(t("smartSearch"))}</h2>
        <p>${escapeHTML(t("smartSearchIntro"))}</p>
      </div>
    </section>
    ${renderSearchBox()}
    <section class="grid compact-grid">
      ${searchSuggestions().map((term) => `
        <button class="suggestion-card" data-search-term="${escapeAttr(term)}">
          <span>⌕</span>
          <strong>${escapeHTML(term)}</strong>
        </button>
      `).join("")}
    </section>
  `;
}

function renderSearchResults(rawQuery) {
  const box = $("#search-results");
  if (!box) return;
  const query = normalize(rawQuery);
  if (!query) {
    box.innerHTML = "";
    return;
  }

  const foodMatches = getFoods().filter((item) => normalize(foodHaystack(item)).includes(query)).slice(0, 24);
  const mealMatches = getAllMeals().filter((meal) => normalize(mealHaystack(meal)).includes(query)).slice(0, 8);
  const tipMatches = state.data.tips.tips.filter((tip) => normalize(tipHaystack(tip)).includes(query)).slice(0, 8);
  const rows = [
    ...foodMatches.map((item) => renderResultRow(item.image, localized(item, "name"), localized(item, "category"), item.status, `data-food-id="${item.id}" data-food-status="${item.status}"`)),
    ...mealMatches.map((meal) => renderResultRow(meal.image, localized(meal, "title"), localizedArray(meal, "items").join(listSeparator()), "meal", "")),
    ...tipMatches.map((tip) => renderResultRow(tip.image || "✦", localized(tip, "title") || localized(tip, "name") || localized(tip, "text"), localized(tip, "category"), "tip", ""))
  ];
  box.innerHTML = rows.length ? rows.join("") : `<div class="empty-state">${escapeHTML(t("noResults"))}</div>`;
}

function renderResultRow(icon, title, subtitle, status, attrs) {
  const label = status === "allowed" ? `✓ ${t("statusAllowed")}` : status === "forbidden" ? `× ${t("statusForbidden")}` : status === "meal" ? t("todayMeals") : t("tips");
  const badgeClass = status === "forbidden" ? "forbidden" : status === "allowed" ? "allowed" : "";
  const buttonAttrs = attrs ? attrs : "";
  return `
    <button class="result-row" ${buttonAttrs}>
      ${renderVisual(icon, "result-icon", title)}
      <span>
        <strong>${escapeHTML(title)}</strong>
        <p>${escapeHTML(subtitle || "")}</p>
      </span>
      <span class="badge ${badgeClass}">${escapeHTML(label)}</span>
    </button>
  `;
}

function renderTodayMeals() {
  const meals = buildDailyMeals();
  const mealEntries = Object.entries(meals).filter(([, meal]) => meal);
  return `
    <section class="section-head premium-title">
      <div>
        <span class="eyebrow">${escapeHTML(t("mealGuideEyebrow"))}</span>
        <h2>${escapeHTML(t("todayMeals"))}</h2>
        <p>${escapeHTML(t("mealGuideIntro"))}</p>
      </div>
      <button class="primary-button" data-action="generate-meals">↻ ${escapeHTML(t("newMeals"))}</button>
    </section>
    <section class="meal-grid">
      ${mealEntries.length ? mealEntries.map(([type, meal]) => renderMealCard(type, meal)).join("") : `<div class="empty-state">${escapeHTML(t("noResults"))}</div>`}
    </section>
  `;
}

function renderMealCard(type, meal, typeLabel = t(type)) {
  const title = localized(meal, "title");
  const description = localized(meal, "description") || localized(meal, "notes");
  const ingredients = localizedArray(meal, "items");
  const mealIsFavorite = isFavorite("meal", meal.id);
  const kcal = meal.kcal || 420;
  const protein = meal.protein_g || 28;
  return `
    <article class="meal-card">
      <div class="meal-photo">
        ${renderSafeImage(meal.image, localizedImageAlt(meal, title), 800, 507)}
        <span class="meal-type-badge">${escapeHTML(typeLabel)}</span>
        <button class="floating-heart ${mealIsFavorite ? "is-active" : ""}" data-action="toggle-favorite" data-favorite-type="meal" data-favorite-id="${escapeAttr(meal.id)}" aria-label="${escapeAttr(mealIsFavorite ? t("removeFavorite") : t("addFavorite"))}">${mealIsFavorite ? "★" : "♡"}</button>
      </div>
      <div class="meal-content">
        <h3>${escapeHTML(title)}</h3>
        <p>${escapeHTML(description)}</p>
        <div class="meal-ingredients">
          <strong>${escapeHTML(t("ingredients"))}</strong>
          <ul>${ingredients.map((item) => `<li>${escapeHTML(item)}</li>`).join("")}</ul>
        </div>
      </div>
      <div class="nutrition-row">
        <span><strong>${escapeHTML(String(kcal))}</strong><small>${escapeHTML(t("kcal"))}</small></span>
        <span><strong>${escapeHTML(formatProtein(protein))}</strong><small>${escapeHTML(t("protein"))}</small></span>
        <span><strong>✓</strong><small>${escapeHTML(t("statusAllowed"))}</small></span>
      </div>
    </article>
  `;
}

function renderFoodDirectory(kind) {
  const source = kind === "allowed" ? state.data.allowed : state.data.forbidden;
  const selected = state.filter[kind];
  const items = selected === "all" ? source.items : source.items.filter((item) => item.category === selected);
  return `
    <section class="section-head premium-title">
      <div>
        <span class="eyebrow">${escapeHTML(t(kind === "allowed" ? "allowedLibraryEyebrow" : "forbiddenLibraryEyebrow"))}</span>
        <h2>${escapeHTML(t(kind))}</h2>
        <p>${escapeHTML(localized(source.source, "note"))}</p>
      </div>
      ${renderCategoryHero(source, selected)}
    </section>
    ${renderSearchBox()}
    <div class="category-filters category-tabs" data-category-tabs="${escapeAttr(kind)}">
      <button class="chip category-chip ${selected === "all" ? "is-active active" : ""}" data-filter-kind="${kind}" data-filter="all">${escapeHTML(t("all"))}</button>
      ${source.categories.map((category) => `
        <button class="chip category-chip ${selected === category ? "is-active active" : ""}" data-filter-kind="${kind}" data-filter="${escapeAttr(category)}">${escapeHTML(localizedCategory(source, category))}</button>
      `).join("")}
    </div>
    <section class="grid">
      ${items.map((item) => renderFoodCard(item)).join("")}
    </section>
  `;
}

function renderCategoryHero(source, selected) {
  const image = categoryImageFor(source, selected);
  if (!image) return "";
  const alt = selected === "all" ? localizedImageAlt(source.source, localized(source.source, "name")) : localizedCategory(source, selected);
  return `
    <div class="category-hero-media">
      ${renderSafeImage(image, alt, 800, 450)}
    </div>
  `;
}

function categoryImageFor(source, selected) {
  if (selected === "all") return source.source?.image || "";
  const index = source.categories.indexOf(selected);
  return source.categoryImages?.[index] || source.source?.image || "";
}

function renderFoodMedia(item) {
  return `
    <span class="food-card-media">
      ${renderSafeImage(item.image, localizedImageAlt(item, localized(item, "name")), 640, 420)}
    </span>
  `;
}

function renderFoodCard(item) {
  const statusLabel = item.status === "allowed" ? t("statusAllowed") : t("statusForbidden");
  const forbiddenDetails = item.status === "forbidden"
    ? [
        [t("reason"), localized(item, "reason")],
        [t("warning"), localized(item, "warning")],
        [t("alternative"), localized(item, "alternative")]
      ].filter(([, value]) => value)
    : [];
  const summary = localizedArray(item, "benefits")[0] || localized(item, "notes") || "";
  const secondary = item.status === "allowed" ? (localized(item, "frequency") || localized(item, "notes")) : "";
  return `
    <button class="food-card ${escapeAttr(item.status)}" data-food-id="${escapeAttr(item.id)}" data-food-status="${escapeAttr(item.status)}">
      ${renderFoodMedia(item)}
      <span class="food-body">
        <span class="status-badge ${item.status}">${escapeHTML(statusLabel)}</span>
        <h3>${escapeHTML(localized(item, "name"))}</h3>
        ${forbiddenDetails.length
          ? forbiddenDetails.map(([label, value]) => `<p class="food-card-detail"><strong>${escapeHTML(label)}:</strong> ${escapeHTML(value)}</p>`).join("")
          : `<p>${escapeHTML(summary)}</p>${secondary ? `<p class="food-card-note">${escapeHTML(secondary)}</p>` : ""}`}
        <span class="badge-row">
          <span class="badge">${escapeHTML(localized(item, "category"))}</span>
        </span>
      </span>
      <span class="card-arrow">&gt;</span>
    </button>
  `;
}

function renderWeeklyPlan() {
  const days = normalizeWeeklyPlanDays(state.data.weekly.plans);
  if (!days.length) {
    return `
      <section class="section-head premium-title">
        <div>
          <span class="eyebrow">${escapeHTML(t("weeklyPlannerEyebrow"))}</span>
          <h2>${escapeHTML(t("weekly"))}</h2>
          <p>${escapeHTML(localized(state.data.weekly, "waterDefault"))}</p>
        </div>
      </section>
    `;
  }

  const selectedIndex = Math.min(Math.max(Number(state.selectedWeekDay) || 0, 0), days.length - 1);
  state.selectedWeekDay = selectedIndex;
  const selectedDay = days[selectedIndex];
  const timelineItems = [
    ["☀", mealTypeLabelForDay(selectedDay, "breakfast"), localized(selectedDay, "breakfast")],
    ["🍽", mealTypeLabelForDay(selectedDay, "lunch"), localized(selectedDay, "lunch")],
    ["☾", mealTypeLabelForDay(selectedDay, "dinner"), localized(selectedDay, "dinner")],
    ["🌿", mealTypeLabelForDay(selectedDay, "snack"), localized(selectedDay, "snack")],
    ["💧", t("water"), localized(selectedDay, "water")],
    ["✦", t("dailyTip"), localized(selectedDay, "tip")]
  ];

  return `
    <section class="section-head premium-title">
      <div>
        <span class="eyebrow">${escapeHTML(t("weeklyPlannerEyebrow"))}</span>
        <h2>${escapeHTML(t("weekly"))}</h2>
        <p>${escapeHTML(localized(state.data.weekly, "waterDefault"))}</p>
      </div>
      <button class="primary-button" data-action="download-weekly">⬇ ${escapeHTML(t("downloadPdf"))}</button>
    </section>
    <section class="week-strip week-tabs week-days week-nav" role="tablist" aria-label="${escapeAttr(t("weekly"))}">
      ${days.map((day, index) => `
        <button
          type="button"
          class="week-day-tab week-tab ${index === selectedIndex ? "is-active" : ""}"
          data-day="${index}"
          role="tab"
          aria-selected="${index === selectedIndex ? "true" : "false"}"
          aria-controls="weekly-day-panel"
        >${escapeHTML(weeklyDayTabLabel(day, index))}</button>
      `).join("")}
    </section>
    <section class="plan-grid">
      <article class="plan-day" id="weekly-day-panel" role="tabpanel">
        <h3><span>${escapeHTML(localized(selectedDay, "name"))}</span><span class="day-number">${selectedDay.day}</span></h3>
        <div class="weekly-nutrition-summary" aria-label="${escapeAttr(t("weekly"))} ${escapeAttr(t("kcal"))} ${escapeAttr(t("protein"))}">
          <span><strong>${escapeHTML(String(selectedDay.calories || 0))}</strong><small>${escapeHTML(t("kcal"))}</small></span>
          <span><strong>${escapeHTML(formatProtein(selectedDay.protein_g || 0))}</strong><small>${escapeHTML(t("protein"))}</small></span>
          <span><strong>✓</strong><small>${escapeHTML(t("statusAllowed"))}</small></span>
        </div>
        ${selectedDay.image ? `
          <div class="weekly-plan-media">
            ${renderSafeImage(selectedDay.image, localizedImageAlt(selectedDay, localized(selectedDay, "name")), 800, 507)}
          </div>
        ` : ""}
        <div class="timeline">
          ${timelineItems.map(([icon, label, value]) => `
            <div class="timeline-item">
              <span>${icon}</span>
              <p><strong>${escapeHTML(label)}</strong>${escapeHTML(value)}</p>
            </div>
          `).join("")}
        </div>
      </article>
    </section>
    ${renderWeeklyMealDetails(selectedDay)}
  `;
}

function renderWeeklyMealDetails(day) {
  const entries = weeklyMealEntriesForDay(day);
  if (!entries.length) return "";
  return `
    <section class="meal-grid weekly-meal-grid">
      ${entries.map(([type, meal]) => renderMealCard(type, meal, mealTypeLabelForDay(day, type))).join("")}
    </section>
  `;
}

function weeklyMealEntriesForDay(day) {
  const ids = day?.mealIds || {};
  return ["breakfast", "lunch", "dinner", "snack"]
    .map((type) => [type, getMealById(ids[type])])
    .filter(([, meal]) => meal);
}

function renderTips() {
  const tip = getDailyTip();
  return `
    <section class="section-head premium-title">
      <div>
        <h2>${escapeHTML(t("tips"))}</h2>
        <p>${escapeHTML(localized(tip, "text"))}</p>
      </div>
      ${favoriteButton("tip", tip.id)}
    </section>
    ${renderSearchBox()}
    <section class="grid tips-grid">
      ${state.data.tips.tips.map((item) => `
        <article class="tip-card" data-tip-open data-tip-id="${escapeAttr(item.id)}" role="button" tabindex="0">
          ${renderTipMedia(item)}
          <div class="tip-content">
            <span class="tip-category">${escapeHTML(localized(item, "category"))}</span>
            <h3 class="tip-title">${escapeHTML(localized(item, "title") || localized(item, "name") || t("dailyTip"))}</h3>
            <p class="tip-description">${escapeHTML(localized(item, "text"))}</p>
          </div>
          <div class="tip-actions">
            ${favoriteButton("tip", item.id)}
            <button class="secondary-button" data-action="share-tip" data-tip-id="${escapeAttr(item.id)}">${escapeHTML(t("shareTip"))}</button>
          </div>
        </article>
      `).join("")}
    </section>
  `;
}

function renderTipMedia(item, featured = false) {
  const image = safeTipImagePath(item?.image);
  const alt = localizedImageAlt(item, localized(item, "title") || localized(item, "name") || t("dailyTip"));
  return renderSafeImage(image, alt, 800, 507).replace("<img ", '<img class="tip-image" ');
}

function renderWaterTracker() {
  const water = getWaterState();
  const goal = state.settings.waterGoal || 2000;
  const percent = Math.min(100, Math.round((water.ml / goal) * 100));
  const glasses = Math.max(6, Math.ceil(goal / (state.settings.cupSize || 250)));
  const filled = Math.min(glasses, Math.floor(water.ml / (state.settings.cupSize || 250)));
  return `
    <section class="section-head premium-title">
      <div>
        <span class="eyebrow">${escapeHTML(t("hydrationEyebrow"))}</span>
        <h2>${escapeHTML(t("water"))}</h2>
        <p>${escapeHTML(t("waterGoal"))}: ${goal} ml</p>
      </div>
    </section>
    <section class="tracker-layout">
      <div class="tracker-panel">
        <div id="water-ring" class="progress-ring" style="--progress: ${percent}%">
          <div class="progress-ring-inner">
            <span>
              <strong id="water-percent">${percent}%</strong>
              <small id="water-ml">${water.ml} / ${goal} ml</small>
            </span>
          </div>
        </div>
        <div class="button-row">
          <button class="primary-button" data-action="add-cup">+ ${escapeHTML(t("addCup"))}</button>
          <button class="secondary-button" data-action="undo-cup" aria-label="${escapeAttr(t("decreaseWater"))}" title="${escapeAttr(t("decreaseWater"))}">−</button>
          <button class="secondary-button" data-action="reset-water" aria-label="${escapeAttr(t("resetWater"))}" title="${escapeAttr(t("resetWater"))}">↺</button>
        </div>
        <div class="water-glasses">
          ${Array.from({ length: glasses }, (_, index) => `<span class="${index < filled ? "filled" : ""}">💧</span>`).join("")}
        </div>
      </div>
      <div class="tracker-panel">
        <h3>${escapeHTML(t("todayStats"))}</h3>
        <div class="mini-chart">
          ${[48, 66, 38, 82, 58, 74, percent].map((value) => `<span style="--bar:${value}%"></span>`).join("")}
        </div>
        <div class="form-grid">
          <label class="field">
            <span>${escapeHTML(t("waterGoal"))} (ml)</span>
            <input id="water-goal" type="number" min="250" max="6000" step="50" value="${goal}">
          </label>
          <label class="field">
            <span>${escapeHTML(t("cupSize"))} (ml)</span>
            <input id="cup-size" type="number" min="50" max="1000" step="25" value="${state.settings.cupSize || 250}">
          </label>
        </div>
        <div class="button-row">
          <button class="secondary-button" data-action="enable-notifications">${escapeHTML(t("enableNotifications"))}</button>
          <button class="secondary-button" data-action="test-notification">${escapeHTML(t("notifications"))}</button>
        </div>
      </div>
    </section>
  `;
}

function renderWeightTracker() {
  const entries = getWeights();
  const stats = getWeightStats(entries);
  const latest = entries[entries.length - 1]?.value || 0;
  const bmi = latest ? (latest / (1.7 * 1.7)).toFixed(1) : "--";
  return `
    <section class="section-head premium-title">
      <div>
        <span class="eyebrow">${escapeHTML(t("progressEyebrow"))}</span>
        <h2>${escapeHTML(t("weight"))}</h2>
        <p>${escapeHTML(t("weekChange"))}: ${stats.week} | ${escapeHTML(t("monthChange"))}: ${stats.month}</p>
      </div>
    </section>
    <section class="tracker-layout">
      <div class="tracker-panel">
        <div class="bmi-card">
          <span>BMI</span>
          <strong>${bmi}</strong>
          <small>${latest ? `${latest} kg` : t("addCurrentWeight")}</small>
        </div>
        <div class="form-grid">
          <label class="field">
            <span>${escapeHTML(t("currentWeight"))} (kg)</span>
            <input id="weight-input" type="number" min="20" max="300" step="0.1" inputmode="decimal">
          </label>
          <label class="field">
            <span>${escapeHTML(t("date"))}</span>
            <input id="weight-date" type="date" value="${todayKey()}">
          </label>
        </div>
        <div class="button-row">
          <button class="primary-button" data-action="save-weight">${escapeHTML(t("saveWeight"))}</button>
        </div>
        <div class="history-list">
          ${entries.slice(-8).reverse().map((entry) => `
            <div class="history-row">
              <span>${escapeHTML(entry.date)}</span>
              <strong>${entry.value} kg</strong>
              <button class="icon-button" data-action="delete-weight" data-date="${escapeAttr(entry.date)}" aria-label="${escapeAttr(t("deleteWeight"))}" title="${escapeAttr(t("deleteWeight"))}">×</button>
            </div>
          `).join("") || `<div class="empty-state">${escapeHTML(t("noResults"))}</div>`}
        </div>
      </div>
      <div class="chart-wrap">
        <canvas id="weight-chart" width="800" height="360" aria-label="${escapeHTML(t("weight"))}"></canvas>
      </div>
    </section>
  `;
}

function renderFavorites() {
  const favorites = resolveFavorites();
  return `
    <section class="section-head premium-title">
      <div>
        <span class="eyebrow">${escapeHTML(t("savedEyebrow"))}</span>
        <h2>${escapeHTML(t("favorites"))}</h2>
        <p>${favorites.length}</p>
      </div>
    </section>
    <section class="result-list">
      ${favorites.length ? favorites.map((fav) => `
        <div class="favorite-row">
          ${renderVisual(fav.image, "result-icon", fav.title)}
          <span>
            <strong>${escapeHTML(fav.title)}</strong>
            <p>${escapeHTML(fav.subtitle)}</p>
          </span>
          <button class="icon-button" data-action="toggle-favorite" data-favorite-type="${escapeAttr(fav.type)}" data-favorite-id="${escapeAttr(fav.id)}" data-favorite-status="${escapeAttr(fav.status || "")}" aria-label="${escapeAttr(t("removeFavorite"))}">★</button>
        </div>
      `).join("") : `<div class="empty-state">${escapeHTML(t("noResults"))}</div>`}
    </section>
  `;
}

function renderNotifications() {
  return `
    <section class="section-head premium-title">
      <div>
        <span class="eyebrow">${escapeHTML(t("remindersEyebrow"))}</span>
        <h2>${escapeHTML(t("notifications"))}</h2>
        <p>${escapeHTML(t("notificationsIntro"))}</p>
      </div>
    </section>
    <section class="grid compact-grid">
      ${[
        ["🍽", t("mealReminderTitle"), t("mealWaterReminder")],
        ["💧", t("waterReminderTitle"), t("waterReminderBody")],
        ["✦", t("dailyTip"), localized(getDailyTip(), "text")],
        ["📄", t("weekly"), t("weeklyReminderBody")]
      ].map(([icon, title, text]) => `
        <article class="tip-card notification-card">
          <span class="result-icon">${icon}</span>
          <h3>${escapeHTML(title)}</h3>
          <p>${escapeHTML(text)}</p>
        </article>
      `).join("")}
    </section>
    <div class="button-row">
      <button class="primary-button" data-action="enable-notifications">${escapeHTML(t("enableNotifications"))}</button>
      <button class="secondary-button" data-action="test-notification">${escapeHTML(t("notifications"))}</button>
    </div>
  `;
}

function renderSupportLegacy() {
  const options = [
    { key: "smallSupport", amount: "1" },
    { key: "supporter", amount: "3" },
    { key: "premiumSupporter", amount: "5" },
    { key: "goldSupporter", amount: "10" }
  ];
  const benefits = [
    "removeAds",
    "priorityUpdates",
    "earlyFeatureAccess",
    "directDeveloperSuggestions",
    "requestFoodsRecipes",
    "voteUpcomingFeatures"
  ];
  return `
    <section class="support-hero">
      <div class="support-hero-copy">
        <span class="eyebrow">${escapeHTML(t("supportEyebrow"))}</span>
        <h2>${escapeHTML(t("supportTitle"))}</h2>
        <p>${escapeHTML(t("supportMessage"))}</p>
        <span class="badge ${state.settings.premium ? "allowed" : ""}">${escapeHTML(state.settings.premium ? t("premiumSupporter") : t("adsActive"))}</span>
      </div>
      <div class="paypal-logo" aria-label="PayPal">
        <span>P</span>
        <strong>PayPal</strong>
      </div>
    </section>

    <section class="donation-grid">
      ${options.map((option) => `
        <article class="donation-card">
          <span class="donation-tier">${escapeHTML(t(option.key))}</span>
          <strong>${escapeHTML(option.amount)} <small>USD</small></strong>
          <button class="primary-button" data-action="support-donate" data-amount="${escapeAttr(option.amount)}">${escapeHTML(t("donateNow"))}</button>
        </article>
      `).join("")}
      <article class="donation-card donation-card-custom">
        <span class="donation-tier">${escapeHTML(t("customAmount"))}</span>
        <label class="field">
          <span>USD</span>
          <input id="custom-donation-amount" type="number" min="1" step="1" inputmode="decimal" placeholder="${escapeAttr(t("customAmountPlaceholder"))}">
        </label>
        <button class="secondary-button" data-action="support-donate" data-amount="custom">${escapeHTML(t("donateNow"))}</button>
      </article>
    </section>

    <section class="support-benefits">
      <div class="section-head">
        <div>
          <span class="eyebrow">${escapeHTML(t("premium"))}</span>
          <h2>${escapeHTML(t("premiumBenefits"))}</h2>
        </div>
      </div>
      <div class="benefit-list">
        ${benefits.map((key) => `
          <div class="benefit-item">
            <span>✓</span>
            <strong>${escapeHTML(t(key))}</strong>
          </div>
        `).join("")}
      </div>
    </section>

    <section class="support-contact">
      <div class="section-head">
        <div>
          <span class="eyebrow">${escapeHTML(t("supportFeedbackEyebrow"))}</span>
          <h2>${escapeHTML(t("developerContactTitle"))}</h2>
          <p>${escapeHTML(t("developerContactBody"))}</p>
        </div>
        <span class="badge ${state.settings.premium ? "allowed" : ""}">${escapeHTML(state.settings.premium ? t("premiumUnlocked") : t("premium"))}</span>
      </div>
      <a class="support-email-link" href="${SUPPORT_MAILTO}">${escapeHTML(SUPPORT_EMAIL)}</a>
      <a class="primary-button support-mail-button" href="${SUPPORT_MAILTO}">${escapeHTML(t("developerContactButton"))}</a>
    </section>

    ${renderReviewForm("support")}

    <footer class="support-footer">${escapeHTML(t("supportFooter"))}</footer>
  `;
}

function renderSettingsLegacy() {
  return `
    <section class="section-head premium-title">
      <div>
        <span class="eyebrow">${escapeHTML(t("profileEyebrow"))}</span>
        <h2>${escapeHTML(t("settings"))}</h2>
        <p>${escapeHTML(t("appName"))}</p>
      </div>
    </section>
    <section class="tracker-panel">
      <div class="setting-row">
        <label for="language-select">${escapeHTML(t("language"))}</label>
        <select id="language-select">
          ${languageOptions().map(([value, label]) => `<option value="${value}" ${state.settings.language === value ? "selected" : ""}>${label}</option>`).join("")}
        </select>
      </div>
      <div class="setting-row">
        <label for="notifications-toggle">${escapeHTML(t("notifications"))}</label>
        <input id="notifications-toggle" type="checkbox" ${state.settings.notifications ? "checked" : ""}>
      </div>
      <div class="setting-row">
        <span>${escapeHTML(t("supportStatus"))}</span>
        <span class="badge ${state.settings.premium ? "allowed" : ""}">${escapeHTML(state.settings.premium ? t("supportActive") : t("adsActive"))}</span>
      </div>
      <div class="support-code-panel">
        <div>
          <strong>${escapeHTML(t("supportCodeTitle"))}</strong>
          <p>${escapeHTML(t("supportCodeIntro"))}</p>
        </div>
        <label class="field" for="support-code-input">
          <span>${escapeHTML(t("activationCode"))}</span>
          <input id="support-code-input" type="text" inputmode="text" autocomplete="one-time-code" placeholder="${escapeAttr(t("activationCodePlaceholder"))}" ${state.settings.premium ? "disabled" : ""}>
        </label>
        <button class="primary-button" data-action="activate-support-code" ${state.settings.premium ? "disabled" : ""}>${escapeHTML(state.settings.premium ? t("premiumUnlocked") : t("activateCode"))}</button>
      </div>
      <div class="setting-row">
        <span>${escapeHTML(t("theme"))}</span>
        <span class="badge allowed">Luxury Light</span>
      </div>
      <div class="setting-row">
        <span>${escapeHTML(t("ads"))}</span>
        <span class="badge">${escapeHTML(state.settings.premium ? t("adsRemoved") : t("webAdsActive"))}</span>
      </div>
      <button class="setting-row action-row support-setting" type="button" data-view="support">
        <span>${escapeHTML(t("supportApp"))}</span>
        <span class="badge allowed">PayPal</span>
      </button>
      ${renderReviewForm("settings")}
      <div class="disclaimer-card">
        <strong>${escapeHTML(t("medicalDisclaimerTitle"))}</strong>
        <p>${escapeHTML(t("medicalDisclaimerBody"))}</p>
        <a class="support-email-link" href="./privacy.html">${escapeHTML(t("privacyPolicy"))}</a>
      </div>
      <div class="premium-card">
        <span>Premium</span>
        <h3>${escapeHTML(t("premiumHeadline"))}</h3>
        <p>${escapeHTML(t("premiumBody"))}</p>
      </div>
    </section>
  `;
}

function renderSupport() {
  const premium = isPremium();
  const options = [
    { key: "smallSupport", amount: "1" },
    { key: "supporter", amount: "3" },
    { key: "premiumSupporter", amount: "5" },
    { key: "goldSupporter", amount: "10" }
  ];
  const benefits = [
    "removeAds",
    "fullPdfDownload",
    "premiumPdfUpdates",
    "exclusiveHealthContent",
    "premiumWeeklyPlans",
    "earlyFeatureAccess",
    "directDeveloperSuggestions",
    "prioritySupport",
    "requestFoodsRecipes",
    "voteUpcomingFeatures"
  ];
  const feedbackTypes = [
    "feedbackSuggestions",
    "feedbackRatings",
    "feedbackBugReports",
    "feedbackFeatureRequests",
    "feedbackFoodAdditions",
    "feedbackRecipeRequests",
    "feedbackDesignImprovements",
    "feedbackGeneral"
  ];
  const pdfAction = premium
    ? `<a class="primary-button support-mail-button" href="${escapeAttr(FULL_PDF_FILE)}" download="tayibat-system-full.pdf">${escapeHTML(t("downloadFullPdf"))}</a>`
    : `<p class="locked-message">${escapeHTML(t("premiumOnlyFeature"))}</p>`;

  return `
    <section class="support-hero">
      <div class="support-hero-copy">
        <span class="eyebrow">${escapeHTML(t("supportEyebrow"))}</span>
        <h2>${escapeHTML(t("supportTitle"))}</h2>
        <p>${escapeHTML(t("supportMessage"))}</p>
        <span class="badge ${premium ? "allowed" : ""}">${escapeHTML(premium ? t("premiumBadge") : t("freeVersion"))}</span>
      </div>
      <div class="paypal-logo" aria-label="PayPal">
        <span>P</span>
        <strong>PayPal</strong>
      </div>
    </section>

    <section class="support-email-split" aria-label="${escapeAttr(t("supportEmailRoles"))}">
      <div>
        <span class="eyebrow">${escapeHTML(t("financialSupportPaypal"))}</span>
        <a class="support-email-link" href="${PAYPAL_SUPPORT_MAILTO}">${escapeHTML(PAYPAL_SUPPORT_EMAIL)}</a>
      </div>
      <div>
        <span class="eyebrow">${escapeHTML(t("developerContactEmailLabel"))}</span>
        <a class="support-email-link" href="${SUPPORT_MAILTO}">${escapeHTML(SUPPORT_EMAIL)}</a>
      </div>
    </section>

    <section class="donation-grid">
      ${options.map((option) => `
        <article class="donation-card">
          <span class="donation-tier">${escapeHTML(t(option.key))}</span>
          <strong>${escapeHTML(option.amount)} <small>USD</small></strong>
          <button class="primary-button" data-action="support-donate" data-amount="${escapeAttr(option.amount)}">${escapeHTML(t("donateNow"))}</button>
        </article>
      `).join("")}
      <article class="donation-card donation-card-custom">
        <span class="donation-tier">${escapeHTML(t("customAmount"))}</span>
        <label class="field">
          <span>USD</span>
          <input id="custom-donation-amount" type="number" min="1" step="1" inputmode="decimal" placeholder="${escapeAttr(t("customAmountPlaceholder"))}">
        </label>
        <button class="secondary-button" data-action="support-donate" data-amount="custom">${escapeHTML(t("donateNow"))}</button>
      </article>
    </section>

    <section class="support-benefits">
      <div class="section-head">
        <div>
          <span class="eyebrow">${escapeHTML(t("premium"))}</span>
          <h2>${escapeHTML(t("premiumBenefits"))}</h2>
        </div>
      </div>
      <div class="benefit-list">
        ${benefits.map((key) => `
          <div class="benefit-item">
            <span>✓</span>
            <strong>${escapeHTML(t(key))}</strong>
          </div>
        `).join("")}
      </div>
    </section>

    <section class="support-premium-section">
      <div class="section-head">
        <div>
          <span class="eyebrow">${escapeHTML(t("premiumPdfs"))}</span>
          <h2>${escapeHTML(t("premiumPdfTitle"))}</h2>
          <p>${escapeHTML(t("premiumPdfDescription"))}</p>
        </div>
        <span class="badge ${premium ? "allowed" : ""}">${escapeHTML(premium ? t("premiumActive") : t("premium"))}</span>
      </div>
      ${pdfAction}
    </section>

    <section class="support-contact">
      <div class="section-head">
        <div>
          <span class="eyebrow">${escapeHTML(t("supportFeedbackEyebrow"))}</span>
          <h2>${escapeHTML(t("developerContactTitle"))}</h2>
          <p>${escapeHTML(t("developerContactBody"))}</p>
        </div>
        <span class="badge ${premium ? "allowed" : ""}">${escapeHTML(premium ? t("premiumUnlocked") : t("premium"))}</span>
      </div>
      <a class="support-email-link" href="${SUPPORT_MAILTO}">${escapeHTML(SUPPORT_EMAIL)}</a>
      <div class="feedback-type-list" aria-label="${escapeAttr(t("feedbackTypesTitle"))}">
        ${feedbackTypes.map((key) => `<span>${escapeHTML(t(key))}</span>`).join("")}
      </div>
      <a class="primary-button support-mail-button" href="${SUPPORT_MAILTO}">${escapeHTML(t("developerContactButton"))}</a>
    </section>

    ${renderReviewForm("support")}

    <footer class="support-footer">${escapeHTML(t("supportFooter"))}</footer>
  `;
}

function renderSettings() {
  const premium = isPremium();
  const activationDate = formatPremiumDate(getPremiumActivationDate());
  const supportAmount = formatSupportAmount(getPremiumSupportAmount());

  return `
    <section class="section-head premium-title">
      <div>
        <span class="eyebrow">${escapeHTML(t("profileEyebrow"))}</span>
        <h2>${escapeHTML(t("settings"))}</h2>
        <p>${escapeHTML(t("appName"))}</p>
      </div>
      ${premium ? `<span class="premium-status-badge">${escapeHTML(t("premiumBadge"))}</span>` : ""}
    </section>
    <section class="tracker-panel">
      <div class="setting-row">
        <label for="language-select">${escapeHTML(t("language"))}</label>
        <select id="language-select">
          ${languageOptions().map(([value, label]) => `<option value="${value}" ${state.settings.language === value ? "selected" : ""}>${label}</option>`).join("")}
        </select>
      </div>
      <div class="setting-row">
        <label for="notifications-toggle">${escapeHTML(t("notifications"))}</label>
        <input id="notifications-toggle" type="checkbox" ${state.settings.notifications ? "checked" : ""}>
      </div>
      <div class="setting-row">
        <span>${escapeHTML(t("supportStatus"))}</span>
        <span class="badge ${premium ? "allowed" : ""}">${escapeHTML(premium ? t("supportActive") : t("adsActive"))}</span>
      </div>
      <div class="premium-status-panel">
        <div class="premium-status-title">
          <span>${escapeHTML(t("premiumStatus"))}</span>
          <strong class="${premium ? "is-active" : ""}">${escapeHTML(premium ? t("premiumActive") : t("freeVersion"))}</strong>
        </div>
        <div class="setting-row compact-row">
          <span>${escapeHTML(t("activationDate"))}</span>
          <span>${escapeHTML(activationDate)}</span>
        </div>
        <div class="setting-row compact-row">
          <span>${escapeHTML(t("supportAmount"))}</span>
          <span>${escapeHTML(supportAmount)}</span>
        </div>
        <button class="secondary-button" data-action="restore-premium">${escapeHTML(t("restorePremiumAccess"))}</button>
      </div>
      <div class="support-code-panel">
        <div>
          <strong>${escapeHTML(t("supportCodeTitle"))}</strong>
          <p>${escapeHTML(t("supportCodeIntro"))}</p>
        </div>
        <label class="field" for="support-code-input">
          <span>${escapeHTML(t("activationCode"))}</span>
          <input id="support-code-input" type="text" inputmode="text" autocomplete="one-time-code" placeholder="${escapeAttr(t("activationCodePlaceholder"))}" ${premium ? "disabled" : ""}>
        </label>
        <button class="primary-button" data-action="activate-support-code" ${premium ? "disabled" : ""}>${escapeHTML(premium ? t("premiumUnlocked") : t("activateCode"))}</button>
      </div>
      <div class="setting-row">
        <span>${escapeHTML(t("theme"))}</span>
        <span class="badge allowed">Luxury Light</span>
      </div>
      <div class="setting-row">
        <span>${escapeHTML(t("ads"))}</span>
        <span class="badge ${premium ? "allowed" : ""}">${escapeHTML(premium ? t("adsRemoved") : t("webAdsActive"))}</span>
      </div>
      <button class="setting-row action-row support-setting" type="button" data-view="support">
        <span>${escapeHTML(t("supportApp"))}</span>
        <span class="badge allowed">PayPal</span>
      </button>
      ${renderReviewForm("settings")}
      <div class="disclaimer-card">
        <strong>${escapeHTML(t("medicalDisclaimerTitle"))}</strong>
        <p>${escapeHTML(t("medicalDisclaimerBody"))}</p>
        <a class="support-email-link" href="./privacy.html">${escapeHTML(t("privacyPolicy"))}</a>
      </div>
      <div class="premium-card">
        <span>Premium</span>
        <h3>${escapeHTML(t("premiumHeadline"))}</h3>
        <p>${escapeHTML(t("premiumBody"))}</p>
      </div>
    </section>
  `;
}

function renderReviewForm(context) {
  const id = (name) => `review-${name}-${context}`;
  const quickButtons = [
    ["like", "reviewQuickLike"],
    ["suggestion", "reviewQuickSuggestion"],
    ["bug", "reviewQuickBug"],
    ["food-recipe", "reviewQuickFoodRecipe"]
  ];

  return `
    <section class="review-panel" data-review-form="${escapeAttr(context)}">
      <div class="section-head">
        <div>
          <span class="eyebrow">${escapeHTML(t("supportFeedbackEyebrow"))}</span>
          <h2>${escapeHTML(t("reviewTitle"))}</h2>
          <p>${escapeHTML(t("reviewIntro"))}</p>
        </div>
      </div>

      <input id="${id("rating")}" type="hidden" value="">
      <div class="review-field">
        <span>${escapeHTML(t("reviewRatingLabel"))}</span>
        <div class="rating-control" role="radiogroup" aria-label="${escapeAttr(t("reviewRatingLabel"))}">
          ${[1, 2, 3, 4, 5].map((rating) => `
            <button class="rating-star" type="button" role="radio" aria-checked="false" data-action="set-review-rating" data-review-context="${escapeAttr(context)}" data-review-rating="${rating}" aria-label="${rating} ${escapeAttr(t("reviewStars"))}">★</button>
          `).join("")}
        </div>
      </div>

      <div class="quick-feedback-row">
        ${quickButtons.map(([type, label]) => `
          <button class="secondary-button" type="button" data-action="set-review-template" data-review-context="${escapeAttr(context)}" data-review-template="${escapeAttr(type)}">${escapeHTML(t(label))}</button>
        `).join("")}
      </div>

      <label class="review-field" for="${id("feedback")}">
        <span>${escapeHTML(t("reviewFeedbackLabel"))}</span>
        <textarea id="${id("feedback")}" rows="4" placeholder="${escapeAttr(t("reviewFeedbackPlaceholder"))}"></textarea>
      </label>
      <label class="review-field" for="${id("additions")}">
        <span>${escapeHTML(t("reviewAdditionsLabel"))}</span>
        <textarea id="${id("additions")}" rows="3" placeholder="${escapeAttr(t("reviewAdditionsPlaceholder"))}"></textarea>
      </label>
      <label class="review-field" for="${id("improvements")}">
        <span>${escapeHTML(t("reviewImproveLabel"))}</span>
        <textarea id="${id("improvements")}" rows="3" placeholder="${escapeAttr(t("reviewImprovePlaceholder"))}"></textarea>
      </label>
      <label class="review-field" for="${id("bug")}">
        <span>${escapeHTML(t("reviewBugLabel"))}</span>
        <textarea id="${id("bug")}" rows="3" placeholder="${escapeAttr(t("reviewBugPlaceholder"))}"></textarea>
      </label>
      <div class="button-row">
        <button class="primary-button" type="button" data-action="send-review" data-review-context="${escapeAttr(context)}">${escapeHTML(t("sendReview"))}</button>
        <button class="secondary-button" type="button" data-action="send-review" data-review-context="${escapeAttr(context)}">${escapeHTML(t("sendDeveloperNote"))}</button>
      </div>
    </section>
  `;
}

function afterRender() {
  if (state.view === "weight") {
    requestAnimationFrame(drawWeightChart);
  }
  syncAdMobBannerForView();
  if (!state.settings.disclaimerAccepted) {
    requestAnimationFrame(showFirstLaunchDisclaimer);
  }
}

function showFirstLaunchDisclaimer() {
  if (state.settings.disclaimerAccepted || $("#modal-root").innerHTML.trim()) return;
  $("#modal-root").innerHTML = `
    <div class="modal-backdrop">
      <article class="modal" role="dialog" aria-modal="true">
        <header class="modal-header">
          <div class="modal-title">
            <span class="food-visual">i</span>
            <div>
              <h2>${escapeHTML(t("medicalDisclaimerTitle"))}</h2>
              <span class="badge">${escapeHTML(t("appName"))}</span>
            </div>
          </div>
          <button class="icon-button modal-close-button" data-action="close-modal" aria-label="${escapeAttr(t("close"))}">×</button>
        </header>
        <div class="modal-body">
          <p>${escapeHTML(t("medicalDisclaimerBody"))}</p>
          <div class="button-row">
            <button class="primary-button" data-action="accept-disclaimer">${escapeHTML(t("understood"))}</button>
          </div>
        </div>
      </article>
    </div>
  `;
}

function acceptDisclaimer() {
  state.settings.disclaimerAccepted = true;
  saveSettings();
  closeModal();
}

function activateSupportCode() {
  if (isPremium()) {
    toast(t("premiumUnlocked"));
    return;
  }
  const input = $("#support-code-input");
  const code = normalizeSupportCode(input?.value);
  if (!VALID_SUPPORT_CODES.has(code)) {
    toast(t("activationInvalid"));
    input?.focus();
    return;
  }
  activatePremium({
    source: "activation-code",
    activatedAt: new Date().toISOString()
  });
}

function normalizeSupportCode(value) {
  return String(value || "").trim().toUpperCase().replace(/\s+/g, "");
}

function activatePremium({ amount = "", source = "manual", activatedAt = new Date().toISOString(), silent = false } = {}) {
  state.settings.premium = true;
  state.settings.supportCodeActivatedAt ||= activatedAt;
  state.settings.premiumActivatedAt = state.settings.premiumActivatedAt || activatedAt;
  state.settings.premiumSupportAmount = amount || state.settings.premiumSupportAmount || "";
  state.settings.premiumSource = source || state.settings.premiumSource || "manual";
  persistPremiumStorage(state.settings);
  saveSettings();
  hideAllAds();
  if (state.data) render();
  if (!silent) toast(t("activationSuccess"));
}

function restorePremiumAccess() {
  if (storedPremiumFlag()) {
    activatePremium({
      amount: storedValue(PREMIUM_AMOUNT_STORAGE_KEY),
      source: storedValue(PREMIUM_SOURCE_STORAGE_KEY) || "restore",
      activatedAt: storedValue(PREMIUM_DATE_STORAGE_KEY) || new Date().toISOString(),
      silent: true
    });
    toast(t("restorePremiumSuccess"));
    return;
  }
  if (isPremium()) {
    persistPremiumStorage(state.settings);
    toast(t("restorePremiumSuccess"));
    return;
  }
  toast(t("restorePremiumMissing"));
}

function handlePremiumReturn() {
  const params = new URLSearchParams(window.location.search);
  const premiumReturn = params.get("premium") === "success" || params.get("support") === "success";
  if (!premiumReturn) return;
  activatePremium({
    amount: params.get("amount") || "",
    source: params.get("source") || "paypal",
    silent: true
  });
  const cleanUrl = new URL(window.location.href);
  ["premium", "support", "amount", "source"].forEach((key) => cleanUrl.searchParams.delete(key));
  window.history.replaceState({}, "", cleanUrl.toString());
}

function isPremium() {
  return Boolean(state.settings.premium || storedPremiumFlag());
}

function storedPremiumFlag() {
  try {
    return localStorage.getItem(PREMIUM_STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

function storedValue(key) {
  try {
    return localStorage.getItem(key) || "";
  } catch {
    return "";
  }
}

function syncPremiumFromStorage(settings) {
  if (storedPremiumFlag()) {
    settings.premium = true;
    settings.premiumActivatedAt ||= storedValue(PREMIUM_DATE_STORAGE_KEY);
    settings.supportCodeActivatedAt ||= settings.premiumActivatedAt;
    settings.premiumSupportAmount ||= storedValue(PREMIUM_AMOUNT_STORAGE_KEY);
    settings.premiumSource ||= storedValue(PREMIUM_SOURCE_STORAGE_KEY);
  }
  if (settings.premium) {
    settings.premiumActivatedAt ||= settings.supportCodeActivatedAt || new Date().toISOString();
    persistPremiumStorage(settings);
  }
  return settings;
}

function persistPremiumStorage(settings) {
  try {
    localStorage.setItem(PREMIUM_STORAGE_KEY, "true");
    if (settings.premiumActivatedAt) localStorage.setItem(PREMIUM_DATE_STORAGE_KEY, settings.premiumActivatedAt);
    if (settings.premiumSupportAmount) localStorage.setItem(PREMIUM_AMOUNT_STORAGE_KEY, settings.premiumSupportAmount);
    if (settings.premiumSource) localStorage.setItem(PREMIUM_SOURCE_STORAGE_KEY, settings.premiumSource);
  } catch (error) {
    console.warn("[Tayibat Life] Premium storage unavailable", error);
  }
}

function getPremiumActivationDate() {
  return state.settings.premiumActivatedAt || state.settings.supportCodeActivatedAt || storedValue(PREMIUM_DATE_STORAGE_KEY);
}

function getPremiumSupportAmount() {
  return state.settings.premiumSupportAmount || storedValue(PREMIUM_AMOUNT_STORAGE_KEY);
}

function formatPremiumDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  try {
    return new Intl.DateTimeFormat(resolvedLanguage(), { dateStyle: "medium" }).format(date);
  } catch {
    return date.toLocaleDateString();
  }
}

function formatSupportAmount(amount) {
  return amount ? `$${amount}` : "-";
}

function setReviewRating(action) {
  const context = action?.dataset.reviewContext || "";
  const rating = action?.dataset.reviewRating || "";
  const input = $(`#review-rating-${cssEscape(context)}`);
  if (!input) return;
  input.value = rating;
  const panel = action.closest("[data-review-form]");
  $$(".rating-star", panel).forEach((button) => {
    const value = Number(button.dataset.reviewRating || 0);
    button.classList.toggle("is-active", value <= Number(rating));
    button.setAttribute("aria-checked", value === Number(rating) ? "true" : "false");
  });
}

function applyReviewTemplate(action) {
  const context = action?.dataset.reviewContext || "";
  const type = action?.dataset.reviewTemplate || "";
  const targetMap = {
    like: ["feedback", "reviewQuickLikeValue"],
    suggestion: ["additions", "reviewQuickSuggestionValue"],
    bug: ["bug", "reviewQuickBugValue"],
    "food-recipe": ["additions", "reviewQuickFoodRecipeValue"]
  };
  const [field, key] = targetMap[type] || [];
  const target = field ? $(`#review-${field}-${cssEscape(context)}`) : null;
  if (!target) return;
  appendTextareaText(target, t(key));
  target.focus();
}

function appendTextareaText(textarea, text) {
  const current = String(textarea.value || "").trim();
  textarea.value = current ? `${current}\n${text}` : text;
}

function sendReviewEmail(action) {
  const context = action?.dataset.reviewContext || "";
  const form = collectReviewForm(context);
  if (!form.feedback) {
    toast(t("reviewFeedbackRequired"));
    form.feedbackEl?.focus();
    return;
  }
  const body = [
    "Tayibat Life Feedback & Review",
    "",
    `Rating: ${form.rating ? `${form.rating}/5` : "Not provided"}`,
    `Feedback: ${form.feedback}`,
    `Suggested additions: ${form.additions || "Not provided"}`,
    `Suggested removals/improvements: ${form.improvements || "Not provided"}`,
    `Bug report: ${form.bug || "Not provided"}`,
    `App language: ${resolvedLanguage()}`,
    `App version: ${APP_VERSION}`,
    `Date: ${new Date().toISOString()}`
  ].join("\n");
  const mailto = `mailto:${SUPPORT_EMAIL}?subject=${encodeURIComponent(REVIEW_EMAIL_SUBJECT)}&body=${encodeURIComponent(body)}`;
  openMailtoUrl(mailto);
  toast(t("reviewEmailOpened"));
}

function collectReviewForm(context) {
  const value = (name) => String($(`#review-${name}-${cssEscape(context)}`)?.value || "").trim();
  return {
    rating: value("rating"),
    feedback: value("feedback"),
    additions: value("additions"),
    improvements: value("improvements"),
    bug: value("bug"),
    feedbackEl: $(`#review-feedback-${cssEscape(context)}`)
  };
}

function openMailtoUrl(url) {
  const link = document.createElement("a");
  link.href = url;
  link.style.display = "none";
  document.body.appendChild(link);
  link.click();
  link.remove();
}

async function openSupportDonation(action) {
  const amount = donationAmountFromAction(action);
  trackAnalytics("donation_button_clicked", { amount: amount || "custom" });
  const config = await loadPayPalConfig();
  if (!config?.enabled) {
    toast(t("paypalUnavailable"));
    return;
  }
  const donationUrl = buildPayPalDonationUrl(config, amount);
  if (!donationUrl) {
    toast(t("paypalUnavailable"));
    return;
  }
  toast(t("openingPayPal"));
  try {
    await openExternalUrl(donationUrl);
  } catch (error) {
    console.warn("[Tayibat Life] PayPal browser open failed; using current window", error);
    window.location.href = donationUrl;
  }
}

async function openExternalUrl(url) {
  const browser = window.Capacitor?.Plugins?.Browser;
  if (browser && typeof browser.open === "function") {
    await browser.open({ url });
    return;
  }
  const opened = window.open(url, "_blank", "noopener,noreferrer");
  if (!opened) {
    window.location.href = url;
  }
}

function donationAmountFromAction(action) {
  const raw = action?.dataset.amount || "";
  const value = raw === "custom" ? $("#custom-donation-amount")?.value : raw;
  const amount = Number.parseFloat(String(value || "").replace(",", "."));
  if (!Number.isFinite(amount) || amount <= 0) return "";
  return String(Math.round(amount * 100) / 100);
}

async function loadPayPalConfig() {
  if (state.paypal.config) return state.paypal.config;
  try {
    const response = await fetch(`${PAYPAL_CONFIG_FILE}?${APP_VERSION}`, { cache: "no-cache" });
    if (!response.ok) throw new Error(`HTTP ${response.status} ${response.statusText}`);
    const config = await response.json();
    const paypalUrl = typeof config.paypalUrl === "string" ? config.paypalUrl.trim() : "";
    const paypalEmail = typeof config.paypalEmail === "string" ? config.paypalEmail.trim() : "";
    const enabled = config.enabled !== false;
    if (enabled && !paypalUrl && !paypalEmail) throw new Error("Missing paypalUrl or paypalEmail");
    state.paypal.config = { paypalUrl, paypalEmail, enabled };
    state.paypal.loadError = null;
    return state.paypal.config;
  } catch (error) {
    state.paypal.loadError = error.message || String(error);
    console.warn("[Tayibat Life] PayPal config unavailable", error);
    return null;
  }
}

function buildPayPalDonationUrl(config, amount) {
  const paypalUrl = String(config?.paypalUrl || "").trim();
  const paypalEmail = String(config?.paypalEmail || "").trim();
  if (paypalUrl && !isPlaceholderPayPalUrl(paypalUrl)) {
    return buildPayPalMeUrl(paypalUrl, amount);
  }
  if (paypalEmail) {
    return buildPayPalEmailDonationUrl(paypalEmail, amount);
  }
  return "";
}

function buildPayPalMeUrl(paypalUrl, amount) {
  if (!amount) return paypalUrl;
  try {
    const url = new URL(paypalUrl);
    url.pathname = `${url.pathname.replace(/\/$/, "")}/${encodeURIComponent(amount)}`;
    return url.toString();
  } catch {
    return paypalUrl;
  }
}

function buildPayPalEmailDonationUrl(email, amount) {
  const url = new URL("https://www.paypal.com/cgi-bin/webscr");
  url.searchParams.set("cmd", "_donations");
  url.searchParams.set("business", email);
  url.searchParams.set("currency_code", "USD");
  url.searchParams.set("item_name", "Tayibat Life support");
  url.searchParams.set("return", buildPremiumReturnUrl(amount));
  url.searchParams.set("cancel_return", window.location.href);
  if (amount) url.searchParams.set("amount", amount);
  return url.toString();
}

function isPlaceholderPayPalUrl(paypalUrl) {
  return /YOUR_PAYPAL/i.test(paypalUrl);
}

function buildPremiumReturnUrl(amount) {
  const url = new URL(window.location.href);
  url.searchParams.set("premium", "success");
  url.searchParams.set("source", "paypal");
  if (amount) url.searchParams.set("amount", amount);
  return url.toString();
}

function trackAnalytics(eventName, payload = {}) {
  const events = loadJSON("tayibat.analytics", []);
  const next = Array.isArray(events) ? events : [];
  next.push({
    event: eventName,
    payload,
    language: resolvedLanguage(),
    view: state.view,
    at: new Date().toISOString()
  });
  saveJSON("tayibat.analytics", next.slice(-500));
  console.info("[Tayibat Life] Analytics event", eventName, payload);
}

function buildDailyMeals() {
  const templates = state.data.meals.templates || {};
  const seed = dayOfYear(new Date()) + state.mealSalt;
  return {
    breakfast: pick(templates.breakfast, seed + 1),
    lunch: pick(templates.lunch, seed + 2),
    dinner: pick(templates.dinner, seed + 3),
    snack: pick(templates.snack, seed + 4)
  };
}

function pick(list, seed) {
  if (!Array.isArray(list) || !list.length) return null;
  return list[Math.abs(seed) % list.length];
}

function getDailyTip() {
  const tips = state.data.tips.tips || fallbackDataFor("tips").tips;
  return tips[dayOfYear(new Date()) % tips.length];
}

function getFoods() {
  return [
    ...(state.data.allowed.items || []).map((item) => ({ ...item, status: "allowed" })),
    ...(state.data.forbidden.items || []).map((item) => ({ ...item, status: "forbidden" }))
  ];
}

function getFoodById(id, status) {
  const list = status === "forbidden" ? state.data.forbidden.items : state.data.allowed.items;
  return list.find((item) => item.id === id) || getFoods().find((item) => item.id === id);
}

function getAllMeals() {
  return Object.values(state.data.meals.templates || {}).flat();
}

function getMealById(id) {
  if (!id) return null;
  return getAllMeals().find((meal) => meal.id === id) || null;
}

function foodHaystack(item) {
  return multilingualHaystack(item, ["name", "category", "notes", "frequency", "reason", "warning", "alternative", "benefits", "harms", "tags"]);
}

function mealHaystack(meal) {
  return multilingualHaystack(meal, ["name", "title", "description", "notes", "items", "tags"]);
}

function tipHaystack(tip) {
  return multilingualHaystack(tip, ["title", "name", "text", "category", "tags"]);
}

function openFoodDetail(id, status) {
  const item = getFoodById(id, status);
  if (!item) return;
  const isAllowed = item.status === "allowed";
  const detail = isAllowed ? `
    ${renderDetailSection(t("benefits"), localizedArray(item, "benefits"))}
    ${renderDetailSection(t("frequency"), localized(item, "frequency"))}
    ${renderDetailSection(t("notes"), localized(item, "notes"))}
  ` : `
    ${renderDetailSection(t("reason"), localized(item, "reason"))}
    ${renderDetailSection(t("warning"), localized(item, "warning") || localizedArray(item, "harms"))}
    ${renderDetailSection(t("alternative"), localized(item, "alternative"))}
    ${renderDetailSection(t("notes"), localized(item, "notes"))}
  `;

  $("#modal-root").innerHTML = `
    <div class="modal-backdrop" data-action="close-modal">
      <article class="modal" role="dialog" aria-modal="true">
        <header class="modal-header detail-modal-header">
          <div class="modal-title">
            <div>
              <h2>${escapeHTML(localized(item, "name"))}</h2>
              <span class="badge ${item.status}">${isAllowed ? "✓ " + t("statusAllowed") : "× " + t("statusForbidden")}</span>
              <span class="badge">${escapeHTML(localized(item, "category"))}</span>
            </div>
          </div>
          <button class="icon-button" data-action="close-modal" aria-label="${escapeAttr(t("close"))}">×</button>
        </header>
        <div class="modal-body">
          <section class="detail-hero ${item.status}">
            ${renderSafeImage(item.image, localizedImageAlt(item, localized(item, "name")), 800, 507)}
          </section>
          ${detail}
          <div class="button-row">
            ${favoriteButton("food", item.id, item.status)}
          </div>
        </div>
      </article>
    </div>
  `;
}

function openTipDetail(id, options = {}) {
  const { countOpen = true } = options;
  const item = state.data.tips.tips.find((tip) => tip.id === id);
  if (!item) return;
  const title = localized(item, "title") || localized(item, "name") || t("dailyTip");
  if (countOpen) {
    recordTipOpenForInterstitial();
  }

  $("#modal-root").innerHTML = `
    <div class="modal-backdrop" data-action="close-modal">
      <article class="modal" role="dialog" aria-modal="true">
        <header class="modal-header detail-modal-header">
          <div class="modal-title">
            <div>
              <h2>${escapeHTML(title)}</h2>
              <span class="badge">${escapeHTML(localized(item, "category") || t("tips"))}</span>
            </div>
          </div>
          <button class="icon-button" data-action="close-modal" aria-label="${escapeAttr(t("close"))}">Ã—</button>
        </header>
        <div class="modal-body">
          <section class="detail-hero">
            ${renderTipMedia(item, true)}
          </section>
          ${renderDetailSection(t("dailyTip"), localized(item, "text"))}
          <div class="button-row">
            ${favoriteButton("tip", item.id)}
            <button class="secondary-button" data-action="share-tip" data-tip-id="${escapeAttr(item.id)}">${escapeHTML(t("shareTip"))}</button>
          </div>
        </div>
      </article>
    </div>
  `;
}

function renderDetailSection(title, value) {
  if (!value || (Array.isArray(value) && value.length === 0)) return "";
  const content = Array.isArray(value)
    ? `<ul class="detail-list">${value.map((item) => `<li>${escapeHTML(item)}</li>`).join("")}</ul>`
    : `<p>${escapeHTML(value)}</p>`;
  return `
    <section class="detail-section">
      <h3>${escapeHTML(title)}</h3>
      ${content}
    </section>
  `;
}

function closeModal(result = false) {
  const pendingAdResolve = state.pendingAdResolve;
  state.pendingAdResolve = null;
  $("#modal-root").innerHTML = "";
  if (pendingAdResolve) {
    pendingAdResolve(result);
  }
}

function favoriteButton(type, id, status = "") {
  const active = isFavorite(type, id, status);
  return `
    <button class="${active ? "primary-button" : "secondary-button"}" data-action="toggle-favorite" data-favorite-type="${escapeAttr(type)}" data-favorite-id="${escapeAttr(id)}" data-favorite-status="${escapeAttr(status)}">
      ${active ? "★ " + escapeHTML(t("removeFavorite")) : "☆ " + escapeHTML(t("addFavorite"))}
    </button>
  `;
}

function favoriteKey(type, id, status = "") {
  return `${type}:${status}:${id}`;
}

function isFavorite(type, id, status = "") {
  return state.favorites.includes(favoriteKey(type, id, status));
}

function toggleFavorite(type, id, status = "") {
  const key = favoriteKey(type, id, status);
  state.favorites = state.favorites.includes(key)
    ? state.favorites.filter((item) => item !== key)
    : [...state.favorites, key];
  saveJSON("tayibat.favorites", state.favorites);
  toast(state.favorites.includes(key) ? t("addFavorite") : t("removeFavorite"));
  if ($("#modal-root").innerHTML) {
    if (type === "food") openFoodDetail(id, status);
    if (type === "tip") openTipDetail(id, { countOpen: false });
  } else {
    render();
  }
}

async function shareTip(id) {
  const tip = state.data.tips.tips.find((item) => item.id === id);
  if (!tip) return;
  const title = localized(tip, "title") || localized(tip, "name") || t("dailyTip");
  const text = `${title}\n${localized(tip, "text")}`;
  try {
    if (navigator.share) {
      await navigator.share({ title, text });
    } else if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      toast(t("tipCopied"));
    } else {
      toast(text);
    }
  } catch (error) {
    if (error?.name !== "AbortError") toast(t("tipCopied"));
  }
}

function resolveFavorites() {
  return state.favorites.map((key) => {
    const [type, status, id] = key.split(":");
    if (type === "food") {
      const food = getFoodById(id, status);
      if (!food) return null;
      return {
        type,
        status,
        id,
        image: food.image,
        title: localized(food, "name"),
        subtitle: `${localized(food, "category")} - ${food.status === "allowed" ? t("statusAllowed") : t("statusForbidden")}`
      };
    }
    if (type === "meal") {
      const meal = getAllMeals().find((item) => item.id === id);
      if (!meal) return null;
      return { type, status, id, image: meal.image, title: localized(meal, "title"), subtitle: localizedArray(meal, "items").join(listSeparator()) };
    }
    if (type === "tip") {
      const tip = state.data.tips.tips.find((item) => item.id === id);
      if (!tip) return null;
      return { type, status, id, image: tip.image || "✦", title: localized(tip, "title") || localized(tip, "text"), subtitle: localized(tip, "category") };
    }
    return null;
  }).filter(Boolean);
}

function todayKey() {
  const date = new Date();
  const month = `${date.getMonth() + 1}`.padStart(2, "0");
  const day = `${date.getDate()}`.padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

function getWaterState() {
  return loadJSON(`tayibat.water.${todayKey()}`, { ml: 0 });
}

function saveWaterState(value) {
  saveJSON(`tayibat.water.${todayKey()}`, value);
}

function addWaterCup(direction = 1) {
  const water = getWaterState();
  const next = Math.max(0, water.ml + (state.settings.cupSize || 250) * direction);
  saveWaterState({ ml: next });
  render();
}

function resetWater() {
  saveWaterState({ ml: 0 });
  render();
}

function renderWaterProgressOnly() {
  const ring = $("#water-ring");
  if (!ring) return;
  const water = getWaterState();
  const goal = state.settings.waterGoal || 2000;
  const percent = Math.min(100, Math.round((water.ml / goal) * 100));
  ring.style.setProperty("--progress", `${percent}%`);
  $("#water-percent").textContent = `${percent}%`;
  $("#water-ml").textContent = `${water.ml} / ${goal} ml`;
}

function getWeights() {
  return loadJSON("tayibat.weights", []).sort((a, b) => a.date.localeCompare(b.date));
}

function saveWeight() {
  const input = $("#weight-input");
  const dateInput = $("#weight-date");
  const value = Number(input?.value);
  const date = dateInput?.value || todayKey();
  if (!Number.isFinite(value) || value <= 0) {
    toast(t("currentWeight"));
    return;
  }
  const entries = getWeights().filter((entry) => entry.date !== date);
  entries.push({ date, value: Number(value.toFixed(1)) });
  saveJSON("tayibat.weights", entries.sort((a, b) => a.date.localeCompare(b.date)));
  toast(t("saveWeight"));
  render();
}

function deleteWeight(date) {
  saveJSON("tayibat.weights", getWeights().filter((entry) => entry.date !== date));
  render();
}

function getWeightStats(entries) {
  if (entries.length < 2) return { week: "0 kg", month: "0 kg" };
  const latest = entries[entries.length - 1];
  const latestDate = new Date(latest.date);
  const findBefore = (days) => {
    const cutoff = new Date(latestDate);
    cutoff.setDate(cutoff.getDate() - days);
    return [...entries].reverse().find((entry) => new Date(entry.date) <= cutoff) || entries[0];
  };
  const format = (previous) => {
    const delta = latest.value - previous.value;
    const sign = delta > 0 ? "+" : "";
    return `${sign}${delta.toFixed(1)} kg`;
  };
  return { week: format(findBefore(7)), month: format(findBefore(30)) };
}

function drawWeightChart() {
  const canvas = $("#weight-chart");
  if (!canvas) return;
  const entries = getWeights();
  const rect = canvas.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.max(640, Math.round(rect.width * ratio));
  canvas.height = Math.round(260 * ratio);
  const ctx = canvas.getContext("2d");
  ctx.scale(ratio, ratio);
  const width = canvas.width / ratio;
  const height = canvas.height / ratio;
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, width, height);
  ctx.strokeStyle = "#dfe7dd";
  ctx.lineWidth = 1;
  for (let i = 0; i < 5; i += 1) {
    const y = 24 + i * ((height - 52) / 4);
    ctx.beginPath();
    ctx.moveTo(36, y);
    ctx.lineTo(width - 18, y);
    ctx.stroke();
  }
  if (entries.length === 0) {
    ctx.fillStyle = "#647067";
    ctx.font = "16px Tahoma";
    ctx.textAlign = "center";
    ctx.fillText(t("noResults"), width / 2, height / 2);
    return;
  }
  const values = entries.map((entry) => entry.value);
  const min = Math.min(...values) - 1;
  const max = Math.max(...values) + 1;
  const xFor = (index) => 36 + index * ((width - 64) / Math.max(1, entries.length - 1));
  const yFor = (value) => 24 + (max - value) * ((height - 52) / Math.max(1, max - min));
  ctx.strokeStyle = "#2e7d32";
  ctx.lineWidth = 3;
  ctx.beginPath();
  entries.forEach((entry, index) => {
    const x = xFor(index);
    const y = yFor(entry.value);
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
  entries.forEach((entry, index) => {
    const x = xFor(index);
    const y = yFor(entry.value);
    ctx.fillStyle = "#d4af37";
    ctx.beginPath();
    ctx.arc(x, y, 5, 0, Math.PI * 2);
    ctx.fill();
  });
}

async function downloadWeeklyPlan() {
  const ok = await showRewardedAd();
  if (!ok) return;
  printWeeklyPlan();
}

function printWeeklyPlan() {
  const days = state.data.weekly.plans;
  const rows = days.map((day) => `
    <section>
      <h2>${escapeHTML(localized(day, "name"))}</h2>
      <p><strong>${escapeHTML(t("breakfast"))}:</strong> ${escapeHTML(localized(day, "breakfast"))}</p>
      <p><strong>${escapeHTML(t("lunch"))}:</strong> ${escapeHTML(localized(day, "lunch"))}</p>
      <p><strong>${escapeHTML(t("dinner"))}:</strong> ${escapeHTML(localized(day, "dinner"))}</p>
      <p><strong>${escapeHTML(t("snack"))}:</strong> ${escapeHTML(localized(day, "snack"))}</p>
      <p><strong>${escapeHTML(t("water"))}:</strong> ${escapeHTML(localized(day, "water"))}</p>
      <p><strong>${escapeHTML(t("dailyTip"))}:</strong> ${escapeHTML(localized(day, "tip"))}</p>
    </section>
  `).join("");
  const html = `
    <!doctype html>
    <html lang="${escapeAttr(resolvedLanguage())}" dir="${resolvedLanguage() === "ar" ? "rtl" : "ltr"}">
      <head>
        <meta charset="utf-8">
        <title>${escapeHTML(t("weekly"))}</title>
        <style>
          body{font-family:Tahoma,Arial,sans-serif;margin:28px;color:#162017;line-height:1.7}
          header{border-bottom:3px solid #2E7D32;margin-bottom:18px}
          h1{color:#17491f;margin:0 0 4px;font-size:28px}
          h2{color:#2E7D32;margin:18px 0 8px;font-size:20px}
          section{break-inside:avoid;border:1px solid #dfe7dd;border-radius:8px;padding:14px;margin:10px 0}
          strong{color:#17491f}
          @page{size:A4;margin:16mm}
        </style>
      </head>
      <body>
        <header>
          <h1>${escapeHTML(t("appNameLocal"))}</h1>
          <p>${escapeHTML(t("tagline"))}</p>
        </header>
        ${rows}
      </body>
    </html>
  `;
  const printWindow = window.open("", "_blank");
  if (!printWindow) {
    const blob = new Blob([html], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "tayibat-weekly-plan.html";
    link.click();
    URL.revokeObjectURL(url);
    return;
  }
  printWindow.document.open();
  printWindow.document.write(html);
  printWindow.document.close();
  setTimeout(() => {
    printWindow.focus();
    printWindow.print();
  }, 350);
}

async function showInterstitialAd() {
  if (isPremium()) return false;
  if (!state.adMob.config?.interstitialEnabled || !state.adMob.config?.interstitialAdUnitId) return false;
  const adMob = getAdMobPlugin();
  if (state.adMob.nativeReady && adMob) {
    try {
      if (typeof adMob.prepareInterstitial === "function") {
        await adMob.prepareInterstitial({
          adId: state.adMob.config?.interstitialAdUnitId,
          isTesting: isAdMobTestMode()
        });
      }
      if (typeof adMob.showInterstitial === "function") {
        await adMob.showInterstitial();
        return true;
      }
      if (typeof adMob.showInterstitialAd === "function") {
        await adMob.showInterstitialAd();
        return true;
      }
      return false;
    } catch (error) {
      console.warn("[Tayibat Life] Native interstitial failed, using fallback", error);
    }
  }
  if ($("#modal-root").innerHTML.trim()) return false;
  await showAdModal("Interstitial", t("appNameLocal"), "AdMob Interstitial");
  return true;
}

function showRewardedAd() {
  if (isPremium()) return Promise.resolve(true);
  if (!state.adMob.config?.rewardedEnabled || !state.adMob.config?.rewardedAdUnitId) return Promise.resolve(true);
  const adMob = getAdMobPlugin();
  if (state.adMob.nativeReady && adMob) {
    return (async () => {
      try {
        if (typeof adMob.prepareRewardVideoAd === "function") {
          await adMob.prepareRewardVideoAd({
            adId: state.adMob.config?.rewardedAdUnitId,
            isTesting: isAdMobTestMode()
          });
        }
        if (typeof adMob.showRewardVideoAd === "function") {
          await adMob.showRewardVideoAd();
          return true;
        }
        if (typeof adMob.showRewardedVideoAd === "function") {
          await adMob.showRewardedVideoAd();
          return true;
        }
      } catch (error) {
        console.warn("[Tayibat Life] Native rewarded ad failed, using fallback", error);
      }
      return showAdModal("Rewarded", t("downloadPdf"), "AdMob Rewarded");
    })();
  }
  return showAdModal("Rewarded", t("downloadPdf"), "AdMob Rewarded");
}

async function initAdMob() {
  if (isPremium()) {
    hideAllAds();
    return;
  }
  state.adMob.config = await loadAdMobConfig();
  state.adMob.lastInterstitialAt = loadInterstitialAdState().lastShownAt || 0;
  if (isAdMobTestMode()) {
    console.info("[Tayibat Life] AdMob test mode enabled");
  }
  const adMob = getAdMobPlugin();
  if (!isCapacitorAndroid()) {
    console.info("[Tayibat Life] AdMob unavailable on web; using fallback ads");
    state.adMob.nativeReady = false;
    return;
  }
  if (!adMob) {
    console.info("[Tayibat Life] AdMob plugin unavailable on Android; using fallback ads");
    state.adMob.nativeReady = false;
    return;
  }

  try {
    if (typeof adMob.initialize === "function") {
      await adMob.initialize({
        requestTrackingAuthorization: false,
        testingDevices: [],
        initializeForTesting: isAdMobTestMode()
      });
    }
    state.adMob.initialized = true;
    state.adMob.nativeReady = true;
    console.info("[Tayibat Life] AdMob initialized on Android");
    await syncAdMobBannerForView();
  } catch (error) {
    state.adMob.nativeReady = false;
    console.warn("[Tayibat Life] AdMob initialization failed; web fallback will be used", error);
  }
}

async function loadAdMobConfig() {
  try {
    const response = await fetch(`${ADMOB_CONFIG_FILE}?${APP_VERSION}`, { cache: "no-cache" });
    if (!response.ok) throw new Error(`HTTP ${response.status} ${response.statusText}`);
    return normalizeAdMobConfig(await response.json());
  } catch (error) {
    console.warn("[Tayibat Life] AdMob config missing; production defaults will be used", error);
    return normalizeAdMobConfig({});
  }
}

function normalizeAdMobConfig(config = {}) {
  return {
    ...ADMOB_DEFAULT_CONFIG,
    ...config,
    bannerEnabled: config.bannerEnabled !== false,
    interstitialEnabled: config.interstitialEnabled !== false,
    rewardedEnabled: config.rewardedEnabled === true && Boolean(config.rewardedAdUnitId),
    testMode: config.testMode === true
  };
}

function isAdMobTestMode() {
  return state.adMob.config?.testMode === true;
}

function loadInterstitialAdState() {
  const stored = loadJSON(ADMOB_INTERSTITIAL_STORAGE_KEY, { lastShownAt: 0 });
  return {
    lastShownAt: Number(stored?.lastShownAt) || 0
  };
}

function saveInterstitialAdState() {
  saveJSON(ADMOB_INTERSTITIAL_STORAGE_KEY, {
    lastShownAt: state.adMob.lastInterstitialAt
  });
}

function recordSectionNavigationForInterstitial(view) {
  if (!view || view === "home" || view === "notifications" || view === "settings") return;
  state.adMob.sectionNavigationsSinceAd += 1;
  maybeShowInterstitialAd("section");
}

function recordTipOpenForInterstitial() {
  state.adMob.tipOpensSinceAd += 1;
  maybeShowInterstitialAd("tip");
}

function canShowInterstitialAd(trigger) {
  if (isPremium()) return false;
  if (state.adMob.interstitialShowing) return false;
  if (!state.adMob.config?.interstitialEnabled || !state.adMob.config?.interstitialAdUnitId) return false;
  const now = Date.now();
  if (now - state.adMob.lastInterstitialAt < ADMOB_INTERSTITIAL_COOLDOWN_MS) return false;
  if (trigger === "tip") return state.adMob.tipOpensSinceAd >= ADMOB_INTERSTITIAL_TIP_THRESHOLD;
  if (trigger === "section") return state.adMob.sectionNavigationsSinceAd >= ADMOB_INTERSTITIAL_SECTION_THRESHOLD;
  return false;
}

async function maybeShowInterstitialAd(trigger) {
  if (!canShowInterstitialAd(trigger)) return false;
  state.adMob.interstitialShowing = true;
  try {
    const shown = await showInterstitialAd();
    if (!shown) return false;
    state.adMob.sectionNavigationsSinceAd = 0;
    state.adMob.tipOpensSinceAd = 0;
    state.adMob.lastInterstitialAt = Date.now();
    saveInterstitialAdState();
    return true;
  } finally {
    state.adMob.interstitialShowing = false;
  }
}

function shouldShowBannerAdOnCurrentView() {
  return state.view === "home" && !isPremium() && state.adMob.config?.bannerEnabled !== false;
}

async function syncAdMobBannerForView() {
  if (!state.adMob.nativeReady) return;
  if (shouldShowBannerAdOnCurrentView()) {
    await showNativeBannerAd();
  } else if (state.adMob.bannerShown) {
    await hideAdMobBanner();
  }
}

async function showNativeBannerAd() {
  if (isPremium()) {
    hideAllAds();
    return;
  }
  const adMob = getAdMobPlugin();
  if (!shouldShowBannerAdOnCurrentView()) return;
  if (state.adMob.bannerShown) return;
  if (!state.adMob.nativeReady || !adMob || !state.adMob.config?.bannerEnabled || !state.adMob.config?.bannerAdUnitId) return;
  try {
    if (typeof adMob.showBanner === "function") {
      await adMob.showBanner({
        adId: state.adMob.config.bannerAdUnitId,
        adSize: "ADAPTIVE_BANNER",
        position: "BOTTOM_CENTER",
        margin: 0,
        isTesting: isAdMobTestMode()
      });
      state.adMob.bannerShown = true;
      $$(".ad-banner").forEach((banner) => banner.remove());
    }
  } catch (error) {
    state.adMob.bannerShown = false;
    console.warn("[Tayibat Life] Native banner failed; web fallback will be used", error);
  }
}

async function hideAdMobBanner() {
  const adMob = getAdMobPlugin();
  if (!adMob) return;
  try {
    if (typeof adMob.hideBanner === "function") {
      await adMob.hideBanner();
    }
    if (typeof adMob.removeBanner === "function") {
      await adMob.removeBanner();
    }
  } catch (error) {
    console.warn("[Tayibat Life] Native banner hide failed", error);
  } finally {
    state.adMob.bannerShown = false;
  }
}

function hideAllAds() {
  hideAdMobBanner();
  $$(".ad-banner").forEach((banner) => banner.remove());
  if (state.pendingAdResolve) {
    closeModal(true);
  }
}

function getAdMobPlugin() {
  return window.Capacitor?.Plugins?.AdMob || window.Capacitor?.Plugins?.AdMobPlugin || null;
}

function isCapacitorAndroid() {
  const capacitor = window.Capacitor;
  if (!capacitor) return false;
  if (typeof capacitor.getPlatform === "function") return capacitor.getPlatform() === "android";
  if (typeof capacitor.platform === "string") return capacitor.platform === "android";
  return Boolean(capacitor.isNativePlatform?.()) && /android/i.test(navigator.userAgent);
}

function showAdModal(kind, title, body) {
  return new Promise((resolve) => {
    state.pendingAdResolve = resolve;
    $("#modal-root").innerHTML = `
      <div class="modal-backdrop">
        <article class="modal" role="dialog" aria-modal="true">
          <header class="modal-header">
            <div class="modal-title">
              <span class="food-visual">Ad</span>
              <div>
                <h2>${escapeHTML(title)}</h2>
                <span class="badge">${escapeHTML(kind)}</span>
              </div>
            </div>
            <button class="icon-button" data-action="ad-close" aria-label="${escapeAttr(t("close"))}">×</button>
          </header>
          <div class="modal-body">
            <p>${escapeHTML(body)}</p>
            <div class="button-row">
              <button class="primary-button" data-action="ad-continue">✓</button>
              <button class="secondary-button" data-action="ad-close">×</button>
            </div>
          </div>
        </article>
      </div>
    `;
  });
}

function resolveAd(value) {
  closeModal(value);
}

async function enableNotifications() {
  if (!("Notification" in window)) {
    toast(t("notifications"));
    return;
  }
  const permission = await Notification.requestPermission();
  state.settings.notifications = permission === "granted";
  saveSettings();
  setupReminders();
  render();
  if (permission === "granted") {
    sendNotification(t("appNameLocal"), t("mealWaterReminder"));
  }
}

function setupReminders() {
  state.reminderTimers.forEach((id) => clearInterval(id));
  state.reminderTimers = [];
  if (!state.settings.notifications || Notification.permission !== "granted") return;
  state.reminderTimers.push(setInterval(() => {
    sendNotification(t("water"), t("waterReminderBody"));
  }, 90 * 60 * 1000));
  state.reminderTimers.push(setInterval(() => {
    sendNotification(t("dailyTip"), localized(getDailyTip(), "text"));
  }, 6 * 60 * 60 * 1000));
}

function sendNotification(title, body) {
  if (!("Notification" in window) || Notification.permission !== "granted") return;
  if (navigator.serviceWorker?.controller) {
    navigator.serviceWorker.ready.then((registration) => {
      registration.showNotification(title, { body, icon: "./assets/icon-192.png", badge: "./assets/icon-192.png" });
    });
  } else {
    new Notification(title, { body, icon: "./assets/icon-192.png" });
  }
}

function loadSettings() {
  const stored = loadJSON("tayibat.settings", null);
  const settings = { ...DEFAULT_SETTINGS, ...(stored || {}) };
  if (!stored || !stored.language) {
    settings.language = detectLanguage();
  }
  if (settings.language !== "auto" && !SUPPORTED_LANGS.includes(settings.language)) {
    settings.language = "ar";
  }
  return syncPremiumFromStorage(settings);
}

function loadJSON(key, fallback) {
  try {
    const value = localStorage.getItem(key);
    return value ? JSON.parse(value) : fallback;
  } catch {
    return fallback;
  }
}

function saveJSON(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

function saveSettings() {
  if (state.settings.premium) persistPremiumStorage(state.settings);
  saveJSON("tayibat.settings", state.settings);
}

function clampNumber(value, min, max, fallback) {
  const number = Number(value);
  if (!Number.isFinite(number)) return fallback;
  return Math.min(max, Math.max(min, number));
}

function dayOfYear(date) {
  const start = new Date(date.getFullYear(), 0, 0);
  return Math.floor((date - start) / 86400000);
}

function normalize(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[أإآ]/g, "ا")
    .replace(/ة/g, "ه")
    .replace(/ى/g, "ي")
    .replace(/[ًٌٍَُِّْ]/g, "")
    .trim();
}

function escapeHTML(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function escapeAttr(value) {
  return escapeHTML(value).replace(/`/g, "&#096;");
}

function cssEscape(value) {
  if (window.CSS?.escape) return CSS.escape(String(value || ""));
  return String(value || "").replace(/[^a-zA-Z0-9_-]/g, "\\$&");
}

function toast(message) {
  const existing = $(".toast");
  if (existing) existing.remove();
  const el = document.createElement("div");
  el.className = "toast";
  el.textContent = message;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 2400);
}

function registerServiceWorker() {
  if (!("serviceWorker" in navigator)) return;
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    const reloadKey = `tayibat.swReloaded.${APP_VERSION}`;
    if (sessionStorage.getItem(reloadKey)) return;
    sessionStorage.setItem(reloadKey, "1");
    window.location.reload();
  });
  navigator.serviceWorker
    .register("./sw.js")
    .then((registration) => registration.update?.())
    .catch((error) => console.warn("Service worker failed", error));
}
