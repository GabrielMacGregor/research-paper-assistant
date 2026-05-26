# OnSign TV Dev Challenge

Minimal single-page app built with plain HTML, CSS, and native ES modules.

## What it does

- Fetches the challenge payload from the OnSign API.
- Retries failed requests up to 3 times after the initial attempt, for 4 calls max.
- Calculates suggested friends from the directional `friends` graph.
- Calculates suggested interests from the direct friends' interests.
- Sorts users by name and lets you reverse the order.
- Shows loading, error, and success states.

## Token input

The app accepts the token from any of these sources:

1. `?access_token=TOKEN` in the URL.
2. `config.js`, a local-only file that is ignored by git.
3. A manually entered token saved in the browser.

`config.example.js` shows the expected format for `config.js`.
The most explicit source wins, so a URL token overrides the local file, and the in-app `Change token` flow can switch the session over to a browser-saved token.

## Run

Serve the folder with any static file server and open `index.html`.

If you already have the token, you can also open:

```text
index.html?access_token=YOUR_TOKEN
```

## Files

- `index.html` - shell page and script loading order
- `config.js` - local-only token file
- `config.example.js` - token file template
- `api.js` - API fetch and retry logic
- `transform.js` - data transformation
- `ui.js` - HTML rendering helpers
- `main.js` - application state and event wiring
- `styles.css` - custom visual styling
