import { fetchChallengeData } from "./api.js";
import { buildEnrichedUsers, buildFriendsMap, buildInterestsByUserId } from "./transform.js";
import { renderApp } from "./ui.js";

const root = document.getElementById("app");
const LOCAL_TOKEN_KEY = "onsign-access-token";
const IGNORE_CONFIG_KEY = "onsign-ignore-config-token";

let activeRequestId = 0;

const state = {
  errorMessage: "",
  sortedUsers: [],
  stage: "boot",
  sortDirection: "asc",
  token: "",
  tokenFormError: "",
  users: []
};

function safeStorage(storageName) {
  try {
    return window[storageName];
  } catch (error) {
    return null;
  }
}

function readUrlToken() {
  try {
    const params = new URLSearchParams(window.location.search);
    return String(params.get("access_token") || "").trim();
  } catch (error) {
    return "";
  }
}

function readConfigToken() {
  const config = window.__ONSIGN_CONFIG__;

  if (!config || typeof config !== "object") {
    return "";
  }

  return typeof config.accessToken === "string" ? config.accessToken.trim() : "";
}

function readStoredToken() {
  const storage = safeStorage("localStorage");

  if (!storage) {
    return "";
  }

  try {
    return String(storage.getItem(LOCAL_TOKEN_KEY) || "").trim();
  } catch (error) {
    return "";
  }
}

function setStoredToken(token) {
  const storage = safeStorage("localStorage");

  if (!storage) {
    return;
  }

  try {
    storage.setItem(LOCAL_TOKEN_KEY, String(token || "").trim());
  } catch (error) {
    return;
  }
}

function clearStoredToken() {
  const storage = safeStorage("localStorage");

  if (!storage) {
    return;
  }

  try {
    storage.removeItem(LOCAL_TOKEN_KEY);
  } catch (error) {
    return;
  }
}

function shouldIgnoreConfigToken() {
  const storage = safeStorage("sessionStorage");

  if (!storage) {
    return false;
  }

  try {
    return storage.getItem(IGNORE_CONFIG_KEY) === "1";
  } catch (error) {
    return false;
  }
}

function setIgnoreConfigToken(value) {
  const storage = safeStorage("sessionStorage");

  if (!storage) {
    return;
  }

  try {
    if (value) {
      storage.setItem(IGNORE_CONFIG_KEY, "1");
    } else {
      storage.removeItem(IGNORE_CONFIG_KEY);
    }
  } catch (error) {
    return;
  }
}

function persistToken(token) {
  const normalizedToken = String(token || "").trim();

  if (!normalizedToken) {
    return;
  }

  setIgnoreConfigToken(true);
  setStoredToken(normalizedToken);

  try {
    const cleanUrl = window.location.href.split("?")[0] + window.location.hash;
    window.history.replaceState({}, document.title, cleanUrl);
  } catch (error) {
    return;
  }
}

function sortUsers(users) {
  const collator = new Intl.Collator("en", {
    sensitivity: "base",
    numeric: true
  });
  const compare = collator.compare.bind(collator);

  return users.slice().sort(function (left, right) {
    const nameComparison = compare(left.name, right.name);

    if (nameComparison !== 0) {
      return state.sortDirection === "asc" ? nameComparison : -nameComparison;
    }

    if (left.id === right.id) {
      return 0;
    }

    return state.sortDirection === "asc" ? left.id - right.id : right.id - left.id;
  });
}

function syncSortedUsers() {
  state.sortedUsers = sortUsers(state.users);
}

function render() {
  if (!root) {
    return;
  }

  root.innerHTML = renderApp(state);

  if (state.stage === "needs-token") {
    window.setTimeout(function () {
      const tokenInput = document.getElementById("accessToken");

      if (tokenInput) {
        tokenInput.focus();
      }
    }, 0);
  }
}

async function loadData() {
  const requestId = activeRequestId + 1;
  activeRequestId = requestId;

  if (!state.token) {
    state.stage = "needs-token";
    state.errorMessage = "";
    state.tokenFormError = "";
    state.users = [];
    state.sortedUsers = [];
    render();
    return;
  }

  state.stage = "loading";
  state.errorMessage = "";
  state.tokenFormError = "";
  state.users = [];
  state.sortedUsers = [];
  render();

  try {
    const payload = await fetchChallengeData(state.token);

    if (requestId !== activeRequestId) {
      return;
    }

    const friendsMap = buildFriendsMap(payload.friends);
    const interestsByUserId = buildInterestsByUserId(payload.interests);
    const enrichedUsers = buildEnrichedUsers(payload.users, friendsMap, interestsByUserId);

    state.users = enrichedUsers;
    syncSortedUsers();
    state.stage = "success";
    render();
  } catch (error) {
    if (requestId !== activeRequestId) {
      return;
    }

    state.errorMessage = error && error.message ? error.message : "An unknown error occurred while loading the data.";
    state.stage = "error";
    state.users = [];
    state.sortedUsers = [];
    render();
  }
}

function handleSubmit(event) {
  const form = event.target.closest('[data-role="token-form"]');

  if (!form) {
    return;
  }

  event.preventDefault();

  const input = form.querySelector('[name="accessToken"]');
  const token = input ? input.value.trim() : "";

  if (!token) {
    state.tokenFormError = "Please enter a valid access token.";
    render();
    return;
  }

  state.tokenFormError = "";
  state.token = token;
  persistToken(token);
  loadData();
}

function handleClick(event) {
  const target = event.target.closest("[data-action]");

  if (!target) {
    return;
  }

  const action = target.getAttribute("data-action");

  if (action === "toggle-sort") {
    state.sortDirection = state.sortDirection === "asc" ? "desc" : "asc";
    syncSortedUsers();
    render();
    return;
  }

  if (action === "retry-load") {
    loadData();
    return;
  }

  if (action === "clear-token") {
    activeRequestId += 1;
    setIgnoreConfigToken(true);
    clearStoredToken();
    state.token = "";
    state.users = [];
    state.sortedUsers = [];
    state.errorMessage = "";
    state.tokenFormError = "";
    state.stage = "needs-token";
    render();
  }
}

function bootstrap() {
  document.addEventListener("submit", handleSubmit);
  document.addEventListener("click", handleClick);

  const urlToken = readUrlToken();

  if (urlToken) {
    state.token = urlToken;
    persistToken(urlToken);
    loadData();
    return;
  }

  const storedToken = readStoredToken();

  if (shouldIgnoreConfigToken()) {
    if (storedToken) {
      state.token = storedToken;
      loadData();
      return;
    }

    state.stage = "needs-token";
    render();
    return;
  }

  const configToken = readConfigToken();

  if (configToken) {
    state.token = configToken;
    loadData();
    return;
  }

  if (storedToken) {
    state.token = storedToken;
    loadData();
    return;
  }

  state.stage = "needs-token";
  render();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", bootstrap);
} else {
  bootstrap();
}
