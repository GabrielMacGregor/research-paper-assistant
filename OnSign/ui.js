function escapeHtml(value) {
  const text = value === null || value === undefined ? "" : String(value);

  return text.replace(/[&<>"']/g, function (character) {
    const replacements = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;"
    };

    return replacements[character];
  });
}

function renderEmptyValue() {
  return '<span class="empty-value">&mdash;</span>';
}

function renderList(items) {
  if (!items || !items.length) {
    return renderEmptyValue();
  }

  return items
    .map(function (item) {
      return escapeHtml(item);
    })
    .join(", ");
}

function renderSortButton(direction) {
  const label = direction === "asc" ? "Name A-Z" : "Name Z-A";
  const arrow = direction === "asc" ? "&uarr;" : "&darr;";

  return (
    '<button type="button" class="btn btn-outline-accent rounded-pill px-3 py-2 d-inline-flex align-items-center gap-2" data-action="toggle-sort" aria-label="Toggle user sort order">' +
    "<span>Sort by name</span>" +
    '<span class="sort-pill__arrow">' +
    arrow +
    "</span>" +
    "<span>" +
    escapeHtml(label) +
    "</span>" +
    "</button>"
  );
}

function renderTokenPrompt(state) {
  return (
    '<section class="panel-card">' +
    '<div class="panel-card__body">' +
    '<div class="status-card status-card--token">' +
    "<div>" +
    '<p class="status-card__label">Access token</p>' +
    '<h2 class="status-card__title">Set your token to load the challenge data</h2>' +
    '<p class="status-card__text">Paste the token from your local config.js or append it to the URL as <code>?access_token=TOKEN</code>. The value is stored locally in this browser session.</p>' +
    "</div>" +
    '<form class="token-form" data-role="token-form">' +
    '<div class="row g-3 align-items-end">' +
    '<div class="col-12 col-md">' +
    '<label class="form-label fw-semibold" for="accessToken">Access token</label>' +
    '<input id="accessToken" name="accessToken" type="password" class="form-control form-control-lg' +
    (state.tokenFormError ? " is-invalid" : "") +
    '" placeholder="Paste your token here" autocomplete="off" />' +
    (state.tokenFormError
      ? '<div class="invalid-feedback">' + escapeHtml(state.tokenFormError) + "</div>"
      : "") +
    "</div>" +
    '<div class="col-12 col-md-auto">' +
    '<button type="submit" class="btn btn-accent btn-lg w-100 px-4">Save and load</button>' +
    "</div>" +
    "</div>" +
    "</form>" +
    '<p class="helper-text">Use config.example.js as a template if you want to prefill the token locally.</p>' +
    "</div>" +
    "</div>" +
    "</section>"
  );
}

function renderLoadingState() {
  return (
    '<section class="panel-card">' +
    '<div class="status-shell">' +
    '<div class="status-card status-card--loading">' +
    '<div class="spinner-border text-success loading-spinner" role="status" aria-hidden="true"></div>' +
    "<div>" +
    '<p class="status-card__label">Loading</p>' +
    '<h2 class="status-card__title">Fetching the challenge data</h2>' +
    '<p class="status-card__text">If the request fails, the app will retry automatically up to three times after the initial attempt, with a one-second pause between each retry.</p>' +
    "</div>" +
    "</div>" +
    "</div>" +
    "</section>"
  );
}

function renderErrorState(state) {
  return (
    '<section class="panel-card">' +
    '<div class="status-shell">' +
    '<div class="status-card status-card--error">' +
    "<div>" +
    '<p class="status-card__label" style="color: var(--danger);">Error</p>' +
    '<h2 class="status-card__title">We could not load the challenge data</h2>' +
    '<p class="status-card__text">' +
    escapeHtml(state.errorMessage) +
    "</p>" +
    "</div>" +
    '<div class="d-flex flex-wrap gap-2">' +
    '<button type="button" class="btn btn-accent" data-action="retry-load">Try again</button>' +
    '<button type="button" class="btn btn-outline-secondary" data-action="clear-token">Use a different token</button>' +
    "</div>" +
    "</div>" +
    "</div>" +
    "</section>"
  );
}

function renderSuccessState(state) {
  const rows = state.sortedUsers.length
    ? state.sortedUsers
        .map(function (user) {
          return (
            "<tr>" +
            '<td class="id-cell">' +
            escapeHtml(user.id) +
            "</td>" +
            '<td class="name-cell">' +
            escapeHtml(user.name) +
            "</td>" +
            "<td>" +
            renderList(user.suggestedFriends) +
            "</td>" +
            "<td>" +
            renderList(user.suggestedInterests) +
            "</td>" +
            "</tr>"
          );
        })
        .join("")
    : '<tr><td colspan="4" class="text-center py-5 text-muted">No users were returned by the API.</td></tr>';

  return (
    '<section class="panel-card table-shell">' +
    '<div class="panel-card__body d-flex flex-column flex-md-row gap-3 justify-content-between align-items-md-end border-bottom" style="border-color: rgba(15, 23, 42, 0.08) !important;">' +
    "<div>" +
    '<h2 class="panel-title">Users table</h2>' +
    '<p class="panel-subtitle">Sorted by name ' +
    escapeHtml(state.sortDirection === "asc" ? "A-Z" : "Z-A") +
    '. Suggested values are deduplicated and ordered alphabetically.</p>' +
    "</div>" +
    '<div class="d-flex flex-wrap gap-2 align-items-center">' +
    '<span class="sort-pill" aria-live="polite">' +
    "<span>" +
    escapeHtml(String(state.sortedUsers.length)) +
    " users</span>" +
    "</span>" +
    "</div>" +
    "</div>" +
    '<div class="table-responsive">' +
    '<table class="table table-striped table-hover align-middle challenge-table">' +
    "<thead>" +
    "<tr>" +
    '<th scope="col">ID</th>' +
    '<th scope="col">Name</th>' +
    '<th scope="col">Suggested Friends</th>' +
    '<th scope="col">Suggested Interests</th>' +
    "</tr>" +
    "</thead>" +
    "<tbody>" +
    rows +
    "</tbody>" +
    "</table>" +
    "</div>" +
    "</section>"
  );
}

export function renderApp(state) {
  let controls = "";

  if (state.stage === "success") {
    controls += renderSortButton(state.sortDirection);
  }

  if (state.token) {
    controls +=
      '<button type="button" class="btn btn-outline-accent rounded-pill px-3" data-action="clear-token">Change token</button>';
  }

  let mainContent = "";

  if (state.stage === "needs-token") {
    mainContent = renderTokenPrompt(state);
  } else if (state.stage === "loading") {
    mainContent = renderLoadingState();
  } else if (state.stage === "error") {
    mainContent = renderErrorState(state);
  } else if (state.stage === "success") {
    mainContent = renderSuccessState(state);
  }

  return (
    '<div class="page-shell container">' +
    '<header class="hero-card mb-4">' +
    '<div class="d-flex flex-column flex-lg-row gap-4 justify-content-between align-items-lg-center">' +
    "<div>" +
    '<p class="eyebrow">OnSign TV Dev Challenge</p>' +
    '<h1 class="hero-title">Directional data, minimal UI, clean sorting</h1>' +
    '<p class="hero-text">This page fetches the API payload, computes suggested friends and interests from the directional graph, retries on failure, and keeps the table sorted by name.</p>' +
    "</div>" +
    '<div class="hero-controls">' +
    controls +
    "</div>" +
    "</div>" +
    "</header>" +
    mainContent +
    "</div>"
  );
}
