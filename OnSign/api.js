const API_URL = "https://api.onsign.tv/dev-challenge/";
const MAX_RETRIES = 3;
const MAX_ATTEMPTS = MAX_RETRIES + 1;
const RETRY_DELAY_MS = 1000;

function sleep(milliseconds) {
  return new Promise(function (resolve) {
    window.setTimeout(resolve, milliseconds);
  });
}

function validatePayload(payload) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw new Error("The API response is not a valid object.");
  }

  if (!Array.isArray(payload.users)) {
    throw new Error("The API response is missing the users array.");
  }

  if (!Array.isArray(payload.friends)) {
    throw new Error("The API response is missing the friends array.");
  }

  if (!payload.interests || typeof payload.interests !== "object" || Array.isArray(payload.interests)) {
    throw new Error("The API response is missing the interests object.");
  }
}

export async function fetchChallengeData(token) {
  const normalizedToken = String(token || "").trim();

  if (!normalizedToken) {
    throw new Error("An access token is required.");
  }

  const url = API_URL + "?access_token=" + encodeURIComponent(normalizedToken);
  let lastError = null;

  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt += 1) {
    try {
      const response = await fetch(url, {
        headers: {
          Accept: "application/json"
        }
      });

      if (response.status !== 200) {
        throw new Error("Request failed with status " + response.status + ".");
      }

      const payload = await response.json();
      validatePayload(payload);
      return payload;
    } catch (error) {
      lastError = error;

      if (attempt < MAX_ATTEMPTS) {
        await sleep(RETRY_DELAY_MS);
      }
    }
  }

  throw new Error(
    "Unable to load the challenge data after " +
      MAX_ATTEMPTS +
      " attempts. " +
      (lastError && lastError.message ? lastError.message : "Unknown error.")
  );
}

export { API_URL, MAX_ATTEMPTS, MAX_RETRIES };
