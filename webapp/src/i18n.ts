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

  promocode: "Промокод",
  promocodePlaceholder: "Введите промокод",
  activate: "Активировать",
  promocodeApplied: "Промокод применён",

  tryFree: "Попробовать бесплатно",
  trialActivated: "Пробный период активирован",

  referralTitle: "Приглашайте друзей",
  referralHint: "Отправьте ссылку — получите бонус за каждого, кто оформит подписку",
  yourLink: "Ваша ссылка",
  share: "Поделиться",
  invited: "Приглашено",
  invitedPaid: "С покупкой",
  referralDisabled: "Реферальная программа отключена",
  referralNeedsSubscription: "Программа доступна с активной подпиской",
  referralNeedsEmail: "Подтвердите почту, чтобы участвовать в программе",

  retry: "Повторить",
  loadFailed: "Не удалось загрузить",
  openInTelegram: "Откройте кабинет через бота в Telegram",

  authTitle: "Личный кабинет",
  authSubtitle: "Покупка и управление подпиской — без Telegram",
  signIn: "Вход",
  signUp: "Регистрация",
  email: "Email",
  password: "Пароль",
  passwordHint: "Не меньше 8 символов",
  enter: "Войти",
  createAccount: "Создать аккаунт",
  termsPrefix: "Регистрируясь, вы принимаете",
  termsOffer: "оферту",
  termsAnd: "и",
  termsPrivacy: "политику конфиденциальности",
  orTelegram: "Есть Telegram?",
  openBot: "Открыть бота",
  toSite: "На главную",
  logout: "Выйти",
  errBadLogin: "Неверный email или пароль",
  errEmailTaken: "Этот email уже зарегистрирован — войдите",
  errBlocked: "Аккаунт заблокирован. Напишите в поддержку",
  errInvalid: "Проверьте email и пароль",
  errGeneric: "Что-то пошло не так. Попробуйте ещё раз",
  verifyTitle: "Подтвердите почту",
  verifyHint: "Введите 6-значный код из письма на {email}. Подтверждение нужно для покупки.",
  verifyCode: "Код из письма",
  verifyConfirm: "Подтвердить",
  verifyResend: "Отправить код ещё раз",
  verifyResendIn: "Новый код — через {count} с",
  verifySent: "Код отправлен",
  verifyDone: "Почта подтверждена",
  errCode: "Неверный или устаревший код",
  errMailOff: "Подтверждение почты пока не работает. Купить можно в Telegram‑боте",
  errMailFailed: "Не удалось отправить письмо. Попробуйте позже",
  paymentReturned: "Спасибо! Подписка обновится в течение минуты",
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

  promocode: "Promo code",
  promocodePlaceholder: "Enter promo code",
  activate: "Apply",
  promocodeApplied: "Promo code applied",

  tryFree: "Try for free",
  trialActivated: "Trial activated",

  referralTitle: "Invite friends",
  referralHint: "Share your link and earn a bonus for everyone who subscribes",
  yourLink: "Your link",
  share: "Share",
  invited: "Invited",
  invitedPaid: "Subscribed",
  referralDisabled: "Referral program is disabled",
  referralNeedsSubscription: "Available once you have an active subscription",
  referralNeedsEmail: "Verify your email to join the program",

  retry: "Retry",
  loadFailed: "Failed to load",
  openInTelegram: "Open the cabinet from the bot in Telegram",

  authTitle: "Personal cabinet",
  authSubtitle: "Buy and manage your subscription without Telegram",
  signIn: "Sign in",
  signUp: "Sign up",
  email: "Email",
  password: "Password",
  passwordHint: "At least 8 characters",
  enter: "Sign in",
  createAccount: "Create account",
  termsPrefix: "By signing up you accept the",
  termsOffer: "terms",
  termsAnd: "and",
  termsPrivacy: "privacy policy",
  orTelegram: "Have Telegram?",
  openBot: "Open the bot",
  toSite: "Home",
  logout: "Sign out",
  errBadLogin: "Wrong email or password",
  errEmailTaken: "This email is already registered — sign in",
  errBlocked: "The account is blocked. Contact support",
  errInvalid: "Check the email and password",
  errGeneric: "Something went wrong. Try again",
  verifyTitle: "Verify your email",
  verifyHint: "Enter the 6-digit code from the email sent to {email}. It is needed to buy.",
  verifyCode: "Code from the email",
  verifyConfirm: "Verify",
  verifyResend: "Send the code again",
  verifyResendIn: "New code in {count} s",
  verifySent: "Code sent",
  verifyDone: "Email verified",
  errCode: "Wrong or expired code",
  errMailOff: "Email confirmation is not available yet. You can buy in the Telegram bot",
  errMailFailed: "Could not send the email. Try later",
  paymentReturned: "Thank you! The subscription updates within a minute",
};

const DICTS: Record<string, Dict> = { ru, en };

let active: Dict = ru;

export function setLocale(language: string | null | undefined): void {
  const code = (language ?? "").slice(0, 2).toLowerCase();
  active = DICTS[code] ?? en;
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
