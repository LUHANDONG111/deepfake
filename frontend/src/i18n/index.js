import { createI18n } from "vue-i18n";

import en from "./messages/en";
import zh from "./messages/zh";

export const supportedLocales = [
  { value: "en", label: "English" },
  { value: "zh", label: "中文" },
];

const savedLocale = localStorage.getItem("app_locale");
const defaultLocale = supportedLocales.some((item) => item.value === savedLocale) ? savedLocale : "en";

export const i18n = createI18n({
  legacy: false,
  locale: defaultLocale,
  fallbackLocale: "en",
  messages: { en, zh },
});

export function setLocale(locale) {
  i18n.global.locale.value = locale;
  localStorage.setItem("app_locale", locale);
  document.documentElement.lang = locale === "zh" ? "zh-CN" : "en";
}

setLocale(defaultLocale);
