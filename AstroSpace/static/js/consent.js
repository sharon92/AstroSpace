(function () {
  const CONSENT_COOKIE = "astrospace_cookie_preferences";
  const THEME_COOKIE = "astrospace_theme";
  const COMMENTER_COOKIE = "astrospace_commenter_name";
  const VISITOR_COOKIE = "astrospace_visitor";
  const PREFERENCE_PREFIX = "astrospace_pref_";
  const DEFAULT_CONSENT = {
    version: 1,
    necessary: true,
    preferences: false,
    community: false,
  };
  const OPTIONAL_PREFERENCE_COOKIES = [THEME_COOKIE, COMMENTER_COOKIE];
  const OPTIONAL_COMMUNITY_COOKIES = [VISITOR_COOKIE];

  function sanitizeKey(key) {
    return String(key).replace(/[^a-zA-Z0-9_-]/g, "_");
  }

  function getCookie(name) {
    const encodedName = `${name}=`;
    const cookies = document.cookie ? document.cookie.split(";") : [];
    for (const cookiePart of cookies) {
      const cookie = cookiePart.trim();
      if (cookie.startsWith(encodedName)) {
        return decodeURIComponent(cookie.slice(encodedName.length));
      }
    }
    return null;
  }

  function setCookie(name, value, days) {
    const maxAge = Math.max(Number(days || 0), 0) * 24 * 60 * 60;
    const secure = window.location.protocol === "https:" ? "; Secure" : "";
    document.cookie = `${name}=${encodeURIComponent(value)}; Max-Age=${maxAge}; Path=/; SameSite=Lax${secure}`;
  }

  function deleteCookie(name) {
    const secure = window.location.protocol === "https:" ? "; Secure" : "";
    document.cookie = `${name}=; Max-Age=0; Path=/; SameSite=Lax${secure}`;
  }

  function parseConsent(rawValue) {
    if (!rawValue) {
      return { ...DEFAULT_CONSENT };
    }

    try {
      const parsed = JSON.parse(rawValue);
      return {
        ...DEFAULT_CONSENT,
        preferences: !!parsed.preferences,
        community: !!parsed.community,
        version: Number(parsed.version || DEFAULT_CONSENT.version),
      };
    } catch (_error) {
      return { ...DEFAULT_CONSENT };
    }
  }

  function getConsent() {
    return parseConsent(getCookie(CONSENT_COOKIE));
  }

  function hasStoredConsent() {
    return !!getCookie(CONSENT_COOKIE);
  }

  function has(category) {
    if (category === "necessary") {
      return true;
    }
    return !!getConsent()[category];
  }

  function clearPreferenceCookies() {
    OPTIONAL_PREFERENCE_COOKIES.forEach(deleteCookie);
    const cookies = document.cookie ? document.cookie.split(";") : [];
    for (const cookiePart of cookies) {
      const name = cookiePart.split("=")[0].trim();
      if (name.startsWith(PREFERENCE_PREFIX)) {
        deleteCookie(name);
      }
    }
  }

  function clearCommunityCookies() {
    OPTIONAL_COMMUNITY_COOKIES.forEach(deleteCookie);
  }

  function saveConsent(consent) {
    const payload = {
      ...DEFAULT_CONSENT,
      preferences: !!consent.preferences,
      community: !!consent.community,
    };
    setCookie(CONSENT_COOKIE, JSON.stringify(payload), 180);

    if (!payload.preferences) {
      clearPreferenceCookies();
    }
    if (!payload.community) {
      clearCommunityCookies();
    }

    window.dispatchEvent(
      new CustomEvent("astrospace:consent-changed", {
        detail: payload,
      })
    );
    return payload;
  }

  function getPreference(key) {
    if (!has("preferences")) {
      return null;
    }

    const rawValue = getCookie(`${PREFERENCE_PREFIX}${sanitizeKey(key)}`);
    if (rawValue === null) {
      return null;
    }

    try {
      return JSON.parse(rawValue);
    } catch (_error) {
      return rawValue;
    }
  }

  function setPreference(key, value, days) {
    if (!has("preferences")) {
      return false;
    }
    setCookie(
      `${PREFERENCE_PREFIX}${sanitizeKey(key)}`,
      JSON.stringify(value),
      days || 180
    );
    return true;
  }

  function removePreference(key) {
    deleteCookie(`${PREFERENCE_PREFIX}${sanitizeKey(key)}`);
  }

  function getTheme() {
    if (!has("preferences")) {
      return null;
    }
    return getCookie(THEME_COOKIE);
  }

  function setTheme(theme) {
    if (!has("preferences")) {
      deleteCookie(THEME_COOKIE);
      return false;
    }
    setCookie(THEME_COOKIE, theme, 180);
    return true;
  }

  function getRememberedCommenterName() {
    if (!has("preferences")) {
      return "";
    }
    return getCookie(COMMENTER_COOKIE) || "";
  }

  window.AstroSpaceConsent = {
    getConsent,
    hasStoredConsent,
    has,
    saveConsent,
    getPreference,
    setPreference,
    removePreference,
    getTheme,
    setTheme,
    getRememberedCommenterName,
    cookieNames: {
      consent: CONSENT_COOKIE,
      theme: THEME_COOKIE,
      commenter: COMMENTER_COOKIE,
      visitor: VISITOR_COOKIE,
      preferencePrefix: PREFERENCE_PREFIX,
    },
  };
})();
