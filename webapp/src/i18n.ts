// Minimal runtime i18n. The bot itself uses fluentogram with many locales, but
// the cabinet only ships the two its audience actually needs; anything else
// falls back to English.

const ru = {
  subscription: "Подписка",
  devices: "Устройства",
  store: "Тарифы",
  referral: "Друзья",

  active: "Активна",
  expired: "Истекла",
  disabled: "Отключена",
  limited: "Лимит исчерпан",
  trial: "Пробный период",

  noSubscription: "Подписки пока нет",
  noSubscriptionHint: "Выберите тариф или активируйте пробный период",
  choosePlan: "Выбрать тариф",

  connect: "Подключить",
  copyLink: "Скопировать ссылку",
  copy: "Копировать",
  copied: "Скопировано",
  reissue: "Перевыпустить ссылку",
  reissueConfirm: "Старая ссылка перестанет работать. Продолжить?",
  reissued: "Ссылка обновлена",

  traffic: "Трафик",
  trafficUsed: "{used} из {limit}",
  unlimited: "Безлимит",
  devicesUsed: "{used} из {limit}",
  deviceCount: "{count} устр.",
  plan: "Тариф",
  expiresToday: "Истекает сегодня",
  expiredOn: "Истекла {date}",
  daysLeft: "{count} дн. · до {date}",

  days: "{count} дн.",
  months: "{count} мес.",
  years: "{count} г.",

  noDevices: "Пока нет подключённых устройств",
  noDevicesHint: "Подключите приложение по ссылке из раздела «Подписка»",
  myDevices: "Мои устройства",
  connectedDevices: "Подключённые устройства",
  deviceUsage: "Лимит устройств",
  connected: "Подключено",
  available: "Доступно",
  connectDevice: "Подключить устройство",
  connectionNeedsSubscription: "Для подключения устройства нужна активная подписка",
  connectionLinkUnavailable: "Ссылка для подключения сейчас недоступна",
  removeDevice: "Отключить",
  removeDeviceConfirm: "Отключить это устройство?",
  removeAllDevices: "Отключить все",
  removeAllConfirm: "Отключить все устройства?",
  deviceRemoved: "Устройство отключено",

  extend: "Продлить",
  buy: "Купить",
  payWith: "Способ оплаты",
  duration: "Срок",
  free: "Бесплатно",
  discount: "−{percent}%",
  paymentOpened: "Окно оплаты открыто",
  paymentPaid: "Оплата прошла",
  paymentFailed: "Оплата не прошла",
  noGateways: "Способы оплаты не настроены",
  total: "Итого",

  promocode: "Промокод",
  promocodePlaceholder: "Введите промокод",
  activate: "Активировать",
  promocodeApplied: "Промокод применён",

  tryFree: "Попробовать бесплатно",
  trialActivated: "Пробный период активирован",

  referralProgram: "Реферальная программа",
  referralTitle: "Приглашайте друзей",
  referralHint: "Делитесь персональной ссылкой и получайте бонусы по условиям программы",
  referralRewardSummary: "Вознаграждение первого уровня — {reward}",
  referralStats: "Статистика реферальной программы",
  yourLink: "Ваша ссылка",
  referralLinkHint: "Отправьте её другу — приглашение будет привязано к вашему аккаунту.",
  share: "Поделиться",
  invited: "Приглашено",
  invitedPaid: "С покупкой",
  availableBonusBalance: "Доступный бонусный баланс",
  bonusBalanceHint: "Доступно для полной оплаты подписки",
  referralRules: "Как это работает",
  referralRuleLink: "Друг переходит по вашей персональной ссылке.",
  referralRuleFirstPayment: "Вознаграждение начисляется после первой оплаты приглашённого.",
  referralRuleEachPayment: "Вознаграждение начисляется с каждой оплаты приглашённого.",
  referralRuleLevels: "Бонусы начисляются по уровням реферальной программы.",
  referralRuleProgram: "Размер и условия бонуса определяются действующей программой.",
  referralRuleLevel: "Уровень {level} — {reward}",
  referralRuleFirstLevel: "{reward} от оплат приглашённых друзей.",
  referralRuleSecondLevel: "{reward} от оплат друзей ваших друзей.",
  referralRuleFullPayment: "При достаточном балансе бонусами можно полностью оплатить подписку.",
  referralRuleNoPartial: "Частичная оплата бонусами не поддерживается.",
  referralRuleBotPayment: "Оплатить подписку бонусами можно в Telegram-боте.",
  referralDisabled: "Реферальная программа отключена",
  referralNeedsSubscription: "Программа доступна с активной подпиской",
  referralNeedsEmail: "Подтвердите почту, чтобы участвовать в программе",

  retry: "Повторить",
  loadFailed: "Не удалось загрузить",
  openInTelegram: "Откройте кабинет через бота в Telegram",
};

// Typed against `ru`, so a key added on one side fails the build until both
// locales define it.
export type MessageKey = keyof typeof ru;
type Dict = Record<MessageKey, string>;

const en: Dict = {
  subscription: "Subscription",
  devices: "Devices",
  store: "Plans",
  referral: "Friends",

  active: "Active",
  expired: "Expired",
  disabled: "Disabled",
  limited: "Limit reached",
  trial: "Trial",

  noSubscription: "No subscription yet",
  noSubscriptionHint: "Pick a plan or start a free trial",
  choosePlan: "Choose a plan",

  connect: "Connect",
  copyLink: "Copy link",
  copy: "Copy",
  copied: "Copied",
  reissue: "Reissue link",
  reissueConfirm: "The old link will stop working. Continue?",
  reissued: "Link updated",

  traffic: "Traffic",
  trafficUsed: "{used} of {limit}",
  unlimited: "Unlimited",
  devicesUsed: "{used} of {limit}",
  deviceCount: "{count} devices",
  plan: "Plan",
  expiresToday: "Expires today",
  expiredOn: "Expired on {date}",
  daysLeft: "{count} days · until {date}",

  days: "{count} days",
  months: "{count} mo.",
  years: "{count} yr.",

  noDevices: "No connected devices yet",
  noDevicesHint: "Connect an app using the link from the Subscription tab",
  myDevices: "My devices",
  connectedDevices: "Connected devices",
  deviceUsage: "Device limit",
  connected: "Connected",
  available: "Available",
  connectDevice: "Connect device",
  connectionNeedsSubscription: "An active subscription is required to connect a device",
  connectionLinkUnavailable: "The connection link is currently unavailable",
  removeDevice: "Disconnect",
  removeDeviceConfirm: "Disconnect this device?",
  removeAllDevices: "Disconnect all",
  removeAllConfirm: "Disconnect all devices?",
  deviceRemoved: "Device disconnected",

  extend: "Extend",
  buy: "Buy",
  payWith: "Payment method",
  duration: "Duration",
  free: "Free",
  discount: "−{percent}%",
  paymentOpened: "Payment window opened",
  paymentPaid: "Payment received",
  paymentFailed: "Payment failed",
  noGateways: "No payment methods configured",
  total: "Total",

  promocode: "Promo code",
  promocodePlaceholder: "Enter promo code",
  activate: "Apply",
  promocodeApplied: "Promo code applied",

  tryFree: "Try for free",
  trialActivated: "Trial activated",

  referralProgram: "Referral program",
  referralTitle: "Invite friends",
  referralHint: "Share your personal link and earn bonuses under the program rules",
  referralRewardSummary: "First-level reward — {reward}",
  referralStats: "Referral program statistics",
  yourLink: "Your link",
  referralLinkHint: "Send it to a friend so their invitation is linked to your account.",
  share: "Share",
  invited: "Invited",
  invitedPaid: "Subscribed",
  availableBonusBalance: "Available bonus balance",
  bonusBalanceHint: "Available for full subscription payment",
  referralRules: "How it works",
  referralRuleLink: "A friend follows your personal referral link.",
  referralRuleFirstPayment: "The reward is credited after the invited user's first payment.",
  referralRuleEachPayment: "The reward is credited after every payment by the invited user.",
  referralRuleLevels: "Bonuses are awarded across the referral program levels.",
  referralRuleProgram: "Bonus amounts and conditions follow the active program.",
  referralRuleLevel: "Level {level} — {reward}",
  referralRuleFirstLevel: "{reward} from payments made by invited friends.",
  referralRuleSecondLevel: "{reward} from payments made by your friends' friends.",
  referralRuleFullPayment: "With sufficient balance, bonuses can pay for the subscription in full.",
  referralRuleNoPartial: "Partial payment with bonuses is not supported.",
  referralRuleBotPayment: "You can pay for a subscription with bonuses in the Telegram bot.",
  referralDisabled: "Referral program is disabled",
  referralNeedsSubscription: "Available once you have an active subscription",
  referralNeedsEmail: "Verify your email to join the program",

  retry: "Retry",
  loadFailed: "Failed to load",
  openInTelegram: "Open the cabinet from the bot in Telegram",
};

type Locale = "ru" | "en";

const DICTS: Record<Locale, Dict> = { ru, en };
const NUMBER_FORMATTERS: Record<Locale, Intl.NumberFormat> = {
  ru: new Intl.NumberFormat("ru", { maximumFractionDigits: 2 }),
  en: new Intl.NumberFormat("en", { maximumFractionDigits: 2 }),
};
const PLURAL_RULES: Record<Locale, Intl.PluralRules> = {
  ru: new Intl.PluralRules("ru"),
  en: new Intl.PluralRules("en"),
};

let activeLocale: Locale = "ru";
let active: Dict = ru;

export function setLocale(language: string | null | undefined): void {
  const code = (language ?? "").slice(0, 2).toLowerCase();
  activeLocale = code === "ru" ? "ru" : "en";
  active = DICTS[activeLocale];
}

export function formatNumber(value: number): string {
  return NUMBER_FORMATTERS[activeLocale].format(value);
}

export function formatPoints(value: number): string {
  const plural = PLURAL_RULES[activeLocale].select(value);
  const unit =
    activeLocale === "ru"
      ? plural === "one"
        ? "балл"
        : plural === "few"
          ? "балла"
          : "баллов"
      : plural === "one"
        ? "point"
        : "points";

  return `${formatNumber(value)} ${unit}`;
}

export function formatExtraDays(value: number): string {
  const plural = PLURAL_RULES[activeLocale].select(value);
  const unit =
    activeLocale === "ru"
      ? plural === "one"
        ? "доп. день"
        : plural === "few"
          ? "доп. дня"
          : "доп. дней"
      : plural === "one"
        ? "extra day"
        : "extra days";

  return `${formatNumber(value)} ${unit}`;
}

export function t(key: MessageKey, vars?: Record<string, string>): string {
  let value = active[key] ?? en[key] ?? String(key);
  if (vars) {
    for (const [name, replacement] of Object.entries(vars)) {
      value = value.replace(`{${name}}`, replacement);
    }
  }
  return value;
}
