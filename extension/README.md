# GBIS — GhostBusters In The Shell (Chrome Extension)

AI text detection and humanization tool. Scan text for AI patterns, generate human-sounding content, and rewrite AI-generated text — all from your browser toolbar.

## Requirements

- The full GBIS repo cloned and running via Docker
- Chrome or Chromium-based browser (Edge, Brave, etc.)

## Installation

1. **Clone the repo and start Docker:**

   ```bash
   git clone https://github.com/kenpodragon/GhostBustersInTheShell.git
   cd GhostBustersInTheShell
   docker compose up -d
   ```

2. **(Optional) Change ports** if defaults conflict:

   Edit `extension/config.json`:
   ```json
   {
     "backend_host": "localhost",
     "backend_port": 8066,
     "frontend_host": "localhost",
     "frontend_port": 5176
   }
   ```
   Then update the matching port values in `docker-compose.yml` and restart:
   ```bash
   docker compose up -d
   ```

3. **Load the extension:**

   - Open Chrome → navigate to `chrome://extensions`
   - Enable **Developer mode** (toggle in top right)
   - Click **Load unpacked**
   - Select the `extension/` folder from this repo
   - The GBIS icon appears in your toolbar

4. **Verify connection:**

   Click the GBIS icon — a green dot in the header means the backend is connected.

## Usage

### Scan Text
Paste text into the input area and click **ANALYZE**. The extension shows an AI score, classification (Clean / Ghost Touched / Ghost Written), and pattern count.

### Scan This Page
Click **Scan This Page** to extract the main content from the current tab. If you have text selected on the page, only the selection is scanned.

### Generate Content
Toggle to **GENERATE** mode (requires AI to be enabled in backend settings). Write a prompt and click **GENERATE** to create content in your voice profile's style.

### Rewrite
After analysis, click **REWRITE** to humanize the text. The rewritten text is auto-analyzed.

### Full Report
Click **VIEW FULL REPORT** to open the detailed analysis in the GBIS Dashboard, including sentence-level breakdown and pattern details.

## Troubleshooting

- **Red dot (offline):** Backend Docker container isn't running. Run `docker compose up -d` from the repo root.
- **GENERATE mode not visible:** AI is disabled in backend settings. Enable it via the GBIS Dashboard or API.
- **Scan This Page returns no text:** The page may block content scripts. Try selecting the text manually first.
- **Changed ports not working:** After editing `config.json`, reload the extension in `chrome://extensions` AND restart Docker.
