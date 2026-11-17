# Mail-Assistent

[English](README.md) · **Deutsch**

Ein lokaler E-Mail-Assistent. Er liest deine Gmail- und Outlook-Postfächer **ausschließlich lesend**, ordnet jede Nachricht mit einer **lokalen KI** (Ollama) ein, fasst sie in einem Satz zusammen und erkennt Rechnungen und Belege. Du prüfst alles in einer Übersicht, die nur auf deinem eigenen Rechner läuft. Auf Wunsch leitest du freigegebene Belege an die Buchhaltungssoftware [sevdesk](https://sevdesk.de) weiter, mit einem Klick pro Beleg.

Keine Cloud, kein Server des Entwicklers: Deine Mails verlassen den Rechner nur, wenn du ausdrücklich etwas versendest.

> **Stand:** Pilotversion, vom Entwickler täglich unter macOS (Apple Silicon) genutzt. Unter Linux und Windows sollte die Anwendung selbst laufen, ist dort aber ungetestet. Das Skript für den Zeitplan gibt es nur für macOS.

## Funktionen

- **Postfächer per Knopf verbinden**: „Mit Google verbinden" (Gmail, `gmail.readonly`) und „Mit Outlook verbinden" (Outlook/Hotmail, Microsoft Graph `Mail.Read`, nur Posteingang). Mehrere Postfächer gleichzeitig.
- **Einordnung durch lokale KI** mit [Ollama](https://ollama.com): Kategorie (Thema), Priorität (Dringlichkeit) und eine Zusammenfassung in einem Satz.
  - Kategorien: Projektanfrage, Termin, Buchhaltung, Konto & Sicherheit, Persönlich, Newsletter, Sonstiges.
  - Priorität: hoch, normal, niedrig.
- **Belegerkennung** in drei Arten: PDF oder Bild im Anhang, Rechnung im Mailtext (wird im Original-Layout samt Bildern als PDF gedruckt, du prüfst die Vorschau) oder Rechnung im Anbieterportal (du lädst sie selbst herunter und hoch).
- **Kompakte Übersicht**: eine Liste mit Suche, Kategorie-Chips und Filtern für Belege, Priorität, Zeitraum und Postfach. Details klappen pro Zeile auf.
- **Optionale Weiterleitung an sevdesk**: ab Werk aus. Jeder Beleg geht erst nach Klick und Bestätigung raus. Automatisches Senden gibt es im Code nicht.
- **Lokale Statistik** der KI: Token und Token pro Sekunde.

## Datenschutz und Sicherheit

- Alles läuft auf `127.0.0.1`. Die Übersicht ist durch ein erzeugtes Passwort geschützt und lehnt Anfragen anderer Rechner ab.
- Mailinhalte wertet nur das lokale Modell aus. Nichts geht an einen KI-Dienst im Internet.
- Der Zugriff auf Postfächer ist nur lesend. Senden braucht eine eigene, ausdrückliche Freigabe (`gmail.send`) und zusätzlich `ENABLE_SEND=1`.
- Zugänge, Passwörter, Belege und Datenbank liegen in `private/` und `state/`, nur für deinen Benutzer lesbar (`chmod 600/700`) und von Git ausgeschlossen.
- Der Mailtext gilt im Prompt als nicht vertrauenswürdige Daten, nie als Anweisung.
- Datenschutzerklärung: <https://magebane89.github.io/mail-assistent/datenschutz.html>

## Voraussetzungen

- Python 3.11 oder neuer (empfohlen 3.12)
- [Ollama](https://ollama.com/download) mit einem Modell, das strukturierte Ausgabe beherrscht, Standard `qwen3.5:9b` (etwa 7,6 GB; 16 GB Arbeitsspeicher empfohlen)
- Google Chrome, Chromium oder Edge (optional, für Rechnungen im Mailtext; ohne entsteht eine reine Text-PDF)
- Ein Gmail- und/oder Outlook.com-Postfach

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

<http://127.0.0.1:8765> öffnen. Benutzername `admin`, Passwort:

```bash
cat private/dashboard_password
```

Port 8765 nicht am Router freigeben.

## Postfächer verbinden

In der Übersicht oben rechts **Einstellungen** öffnen.

- **Gmail**: „Mit Google verbinden" klicken. Das Projekt liefert eine App-Kennung mit (`oauth_defaults.json`), daher klappt das sofort. Google zeigt den Hinweis, dass die App nicht überprüft ist; über „Erweitert" geht es weiter. Die gemeinsame Kennung erlaubt höchstens 100 Nutzer. Für eine eigene Kennung in der [Google Cloud Console](https://console.cloud.google.com/auth/clients) einen OAuth-Client vom Typ *Desktop-App* anlegen, die Gmail API aktivieren und die JSON-Datei in den Einstellungen hochladen. Eine eigene Kennung hat Vorrang.
- **Outlook / Hotmail**: Einmal im [Microsoft Entra Admin Center](https://entra.microsoft.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade) eine App registrieren (etwa 10 Minuten, die Schritte stehen auf der Einstellungsseite), die Anwendungs-ID eintragen und „Mit Outlook verbinden" klicken.

## Scannen

```bash
python assistant_app.py scan
```

Jeder Lauf liest alle verbundenen Postfächer. `GMAIL_QUERY` legt den Zeitraum fest (`newer_than:3d`, gilt auch für Outlook), `MAX_MESSAGES_PER_RUN` begrenzt die neuen Einordnungen pro Postfach. Bereits bekannte Nachrichten werden übersprungen.

**Zeitplan unter macOS** (standardmäßig alle 30 Minuten von 08:00 bis 18:00; startet Ollama bei Bedarf):

```bash
scripts/install_launchd.sh
SCAN_FROM=0 SCAN_TO=23 scripts/install_launchd.sh   # rund um die Uhr
scripts/remove_launchd.sh                            # wieder entfernen
```

Unter Linux per Cron-Job `scripts/scan_with_ollama.sh` aufrufen. Das Skript nutzt `open -a Ollama`; Ollama dort stattdessen als Dienst starten.

**Neu einordnen** nach Änderungen an den Regeln (Belegstatus und Freigaben bleiben erhalten):

```bash
python assistant_app.py reclassify
```

## Belege an sevdesk weiterleiten (optional)

sevdesk nimmt Belege an `autobox@sevdesk.email` nur von der Adresse an, mit der du bei sevdesk registriert bist ([sevdesk-Hilfe](https://hilfe.sevdesk.de/de/articles/9453113-belege-erfassen)).

1. In der `.env` `SEVDESK_REGISTERED_EMAIL` auf diese Adresse setzen. Es muss das Gmail-Konto sein, das sendet.
2. Senderecht einmalig erteilen: `python assistant_app.py auth --send`
3. In der `.env` `ENABLE_SEND=1` setzen, `AUTO_SEND=0` lassen, Übersicht neu starten.
4. Mit einem einzigen echten Beleg testen und Gmail „Gesendet" sowie den sevdesk-Eingang prüfen.

`AUTO_SEND` ist eine Sicherheitssperre: Jeder Wert außer `0` blockiert jeden Versand. Die Weiterleitung funktioniert bisher nur für Belege aus Gmail-Konten. Bricht ein Versand mittendrin ab, steht der Beleg auf „Status unklar" und wird nie automatisch wiederholt.

## Einstellungen (`.env`)

| Variable | Standard | Bedeutung |
|---|---|---|
| `OLLAMA_URL` | `http://127.0.0.1:11434` | Adresse von Ollama |
| `OLLAMA_MODEL` | `qwen3.5:9b` | Modell für die Einordnung |
| `OLLAMA_CONTEXT` | `8192` | Kontextfenster |
| `GMAIL_QUERY` | `newer_than:7d -in:spam -in:trash` | Gmail-Suche; der `newer_than`-Teil gilt auch für Outlook |
| `MAX_MESSAGES_PER_RUN` | `20` | Neue Einordnungen pro Postfach und Lauf |
| `SEVDESK_REGISTERED_EMAIL` | leer | Bei sevdesk registrierte Absenderadresse |
| `SEVDESK_EMAIL` | `autobox@sevdesk.email` | Belegeingang von sevdesk |
| `ENABLE_SEND` | `0` | `1` erlaubt die Weiterleitung nach Klick |
| `AUTO_SEND` | `0` | Sicherheitssperre, muss `0` bleiben |
| `PAPERCLIP_WEBHOOK_SECRET` | leer | Optional: Scans aus [Paperclip](https://docs.paperclip.ing/) auslösen |
| `PDF_LOAD_IMAGES` | `1` | Externe Bilder (Logos) in Rechnungs-PDFs laden; `0` = nur eingebettete Bilder, der Absender sieht dann nicht, dass die Mail geöffnet wurde |
| `CHROME_PATH` | leer | Pfad zu Chrome/Chromium/Edge, falls nicht automatisch gefunden |
| `WEB_PORT` | `8765` | Port der Übersicht |

## Wo die Daten liegen

| Pfad | Inhalt |
|---|---|
| `state/assistant.sqlite3` | Nachrichten, Kategorien, Zusammenfassungen, Belegstatus, KI-Statistik |
| `private/token_readonly.json`, `private/accounts/` | Zugänge zu den Postfächern |
| `private/token_with_send.json` | Senderecht (nur nach `auth --send`) |
| `private/credentials.json`, `private/microsoft_client.json` | Eigene App-Kennungen (optional) |
| `private/dashboard_password` | Passwort der Übersicht |
| `private/email_pdfs/`, `private/original_emails/`, `private/portal_uploads/` | Beleg-PDFs und Original-Mails |

Wer den Projektordner löscht, löscht alles. Zugriffe widerrufst du bei [Google](https://myaccount.google.com/permissions) oder [Microsoft](https://account.microsoft.com/privacy/app-access).

## Entwicklung

```bash
python -m unittest discover -s tests
```

## Lizenz

Copyright (C) 2026 magebane89

Dieses Programm ist freie Software: Du kannst es unter den Bedingungen der GNU General Public License, Version 3 oder (nach deiner Wahl) jeder späteren Version, wie von der Free Software Foundation veröffentlicht, weitergeben und verändern. Es wird ohne jede Gewährleistung bereitgestellt. Details in [LICENSE](LICENSE).

Mail-Assistent steht in keiner Verbindung zu Google, Microsoft oder sevdesk.
