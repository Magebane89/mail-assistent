# Mail-Assistent

**English** · [Deutsch](README.de.md)

A local email assistant. It reads your Gmail and Outlook mailboxes **read-only**, categorizes and summarizes each message with a **local LLM** (Ollama), and flags invoices and receipts. You review everything in a dashboard that only runs on your own machine. Optionally, approved receipts can be forwarded to the bookkeeping software [sevdesk](https://sevdesk.de), one click per receipt.

No cloud, no server of ours: your mail never leaves your computer except for what you explicitly send.

> **Status:** Pilot, used daily by the author on macOS (Apple Silicon). Linux and Windows should work for the core app but are untested, and the scheduler script is macOS-only. The user interface is in German.

## Features

- **Connect mailboxes with one click**: "Connect with Google" (Gmail, `gmail.readonly`) and "Connect with Outlook" (Outlook/Hotmail, Microsoft Graph `Mail.Read`, inbox only). Several mailboxes at once.
- **Local AI categorization** with [Ollama](https://ollama.com): category (topic), priority (urgency) and a one-sentence summary per message.
  - Categories: Projektanfrage (project inquiry), Termin (appointment), Buchhaltung (accounting), Konto & Sicherheit (account & security), Persönlich (personal), Newsletter, Sonstiges (other).
  - Priority: hoch / normal / niedrig (high / normal / low).
- **Receipt detection** in three kinds: PDF/image attachment, invoice in the email body (turned into a PDF you preview first), or invoice in a provider portal (you download it yourself and upload it).
- **Compact dashboard**: one list with search, category chips, filters for receipts, priority, period and mailbox; details expand per row.
- **Optional forwarding to sevdesk**: off by default. Each receipt is sent only after you click and confirm. No automatic sending exists in the code.
- **Local statistics** of the LLM: tokens and tokens per second.

## Privacy and security

- Everything runs on `127.0.0.1`. The dashboard is protected by a generated password and refuses requests from other hosts.
- Mail content is analyzed by a local model only. Nothing is sent to an AI service on the internet.
- Mailbox access is read-only. Sending requires a separate, explicit grant (`gmail.send`) plus `ENABLE_SEND=1`.
- Tokens, passwords, receipts and the database live in `private/` and `state/`, readable only by your user (`chmod 600/700`) and excluded from Git.
- Email text is treated as untrusted data in the prompt, never as instructions.
- Privacy policy: <https://magebane89.github.io/mail-assistent/privacy.html>

## Requirements

- Python 3.11 or newer (3.12 recommended)
- [Ollama](https://ollama.com/download) with a model that supports structured output, default `qwen3.5:9b` (about 7.6 GB; 16 GB RAM recommended)
- A Gmail and/or Outlook.com mailbox

## Installation

```bash
git clone https://github.com/magebane89/mail-assistent.git
cd mail-assistent
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
chmod 600 .env
ollama pull qwen3.5:9b
python assistant_app.py web
```

Open <http://127.0.0.1:8765>. User name `admin`, password:

```bash
cat private/dashboard_password
```

Do not expose port 8765 on your router.

## Connecting mailboxes

Open **Einstellungen** (settings) in the dashboard.

- **Gmail**: click "Mit Google verbinden". The project ships an app ID (`oauth_defaults.json`), so this works right away. Google shows a warning that the app is not verified; continue via "Advanced". The shared app ID is limited to 100 users. To use your own instead, create an OAuth client of type *Desktop app* in the [Google Cloud Console](https://console.cloud.google.com/auth/clients), enable the Gmail API and upload the JSON file in the settings. Your own ID takes precedence.
- **Outlook / Hotmail**: register an app once in the [Microsoft Entra admin center](https://entra.microsoft.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade) (about 10 minutes, step-by-step instructions are on the settings page), paste its application ID, then click "Mit Outlook verbinden".

## Scanning

```bash
python assistant_app.py scan
```

Each run reads every connected mailbox. `GMAIL_QUERY` sets the period (`newer_than:3d`, also used for Outlook) and `MAX_MESSAGES_PER_RUN` limits new classifications per mailbox. Messages already in the database are skipped.

**Schedule on macOS** (every 30 minutes, 08:00 to 18:00 by default; starts Ollama if needed):

```bash
scripts/install_launchd.sh
SCAN_FROM=0 SCAN_TO=23 scripts/install_launchd.sh   # around the clock
scripts/remove_launchd.sh                            # remove again
```

On Linux, use a cron job that runs `scripts/scan_with_ollama.sh` (it uses `open -a Ollama`, so start Ollama as a service instead).

**Re-run categorization** after changing the rules (keeps receipt status and approvals):

```bash
python assistant_app.py reclassify
```

## Forwarding receipts to sevdesk (optional)

sevdesk accepts receipts at `autobox@sevdesk.email` only from the address registered with your sevdesk account ([sevdesk help](https://hilfe.sevdesk.de/de/articles/9453113-belege-erfassen)).

1. In `.env`, set `SEVDESK_REGISTERED_EMAIL` to that address. It must be the Gmail account that sends.
2. Grant the send permission once: `python assistant_app.py auth --send`
3. Set `ENABLE_SEND=1` in `.env`, leave `AUTO_SEND=0`, restart the dashboard.
4. Test with a single real receipt and check Gmail "Sent" and the sevdesk inbox.

`AUTO_SEND` is a safety lock: any value other than `0` blocks every send. Forwarding currently works for receipts from Gmail accounts only. If a send fails midway, the receipt is marked "Status unklar" and is never retried automatically.

## Configuration (`.env`)

| Variable | Default | Meaning |
|---|---|---|
| `OLLAMA_URL` | `http://127.0.0.1:11434` | Ollama endpoint |
| `OLLAMA_MODEL` | `qwen3.5:9b` | Model used for categorization |
| `OLLAMA_CONTEXT` | `8192` | Context window |
| `GMAIL_QUERY` | `newer_than:7d -in:spam -in:trash` | Gmail search; the `newer_than` part sets the period for Outlook too |
| `MAX_MESSAGES_PER_RUN` | `20` | New classifications per mailbox and run |
| `SEVDESK_REGISTERED_EMAIL` | empty | Sender address registered with sevdesk |
| `SEVDESK_EMAIL` | `autobox@sevdesk.email` | sevdesk receipt inbox |
| `ENABLE_SEND` | `0` | `1` enables forwarding after click |
| `AUTO_SEND` | `0` | Safety lock, must stay `0` |
| `PAPERCLIP_WEBHOOK_SECRET` | empty | Optional: trigger scans from [Paperclip](https://docs.paperclip.ing/) |
| `WEB_PORT` | `8765` | Dashboard port |

## Where data is stored

| Path | Content |
|---|---|
| `state/assistant.sqlite3` | Messages, categories, summaries, receipt status, LLM statistics |
| `private/token_readonly.json`, `private/accounts/` | Mailbox access tokens |
| `private/token_with_send.json` | Send permission (only after `auth --send`) |
| `private/credentials.json`, `private/microsoft_client.json` | Your own app IDs (optional) |
| `private/dashboard_password` | Dashboard password |
| `private/email_pdfs/`, `private/original_emails/`, `private/portal_uploads/` | Receipt PDFs and original messages |

Deleting the project folder removes everything. Revoke access at [Google](https://myaccount.google.com/permissions) or [Microsoft](https://account.microsoft.com/privacy/app-access).

## Development

```bash
python -m unittest discover -s tests
```

## License

Copyright (C) 2026 magebane89

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version. It is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY. See [LICENSE](LICENSE).

Mail-Assistent is not affiliated with Google, Microsoft or sevdesk.
