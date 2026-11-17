#!/usr/bin/env python3
"""Optional: Erzeuge EINEN process-Agenten über die Paperclip-API.

NUR nach manueller Prüfung/Tests starten. Keine Credential-Dateien werden gesendet.
Benötigt Board/Admin-API-Zugang und eine lokal ausgeführte Paperclip-Installation.
"""
from pathlib import Path
import json
import os
import sys
import requests

root=Path(__file__).resolve().parents[1]
url=os.environ.get('PAPERCLIP_API_URL','').rstrip('/')
company=os.environ.get('PAPERCLIP_COMPANY_ID','')
api_key=os.environ.get('PAPERCLIP_API_KEY','')
if not all((url,company,api_key)):
    sys.exit('Bitte PAPERCLIP_API_URL, PAPERCLIP_COMPANY_ID, PAPERCLIP_API_KEY als Umgebungsvariablen setzen.')
if not url.startswith('http://127.0.0.1:') and not url.startswith('http://localhost:'):
    sys.exit('Sicherheitsbremse: Dieser Setup-Helfer erlaubt nur die lokale Paperclip-API.')

python=str(root/'.venv'/'bin'/'python')
command=str(root/'assistant_app.py')
payload={
    'name':'Gmail & sevdesk Freigabe-Assistent',
    'role':'general',
    'title':'Lokaler Kommunikations- und Belegassistent',
    'capabilities':'Gmail nur lesen; Nachrichten mit Ollama kategorisieren; Belege zur manuellen Freigabe bereitstellen; nie selbst versenden.',
    'adapterType':'process',
    'adapterConfig':{
        'command':python,
        'args':[command,'scan'],
        'cwd':str(root),
        'timeoutSec':1800,
        'graceSec':30
    },
    'runtimeConfig':{
        'heartbeat':{'enabled':True,'intervalSec':1800}
    },
    'budgetMonthlyCents':0
}
print('Paperclip wird diesen Prozess alle 30 Minuten ausführen:')
print(json.dumps({k:v for k,v in payload.items() if k!='capabilities'},ensure_ascii=False,indent=2))
if input('Agent in Paperclip wirklich anlegen? [ja/NEIN] ').strip().lower()!='ja':
    sys.exit('Nicht angelegt.')
response=requests.post(f'{url}/api/companies/{company}/agent-hires',
                       headers={'Authorization':'Bearer '+api_key},json=payload,timeout=15)
try:
    response.raise_for_status()
except requests.HTTPError:
    print('Paperclip-API:',response.status_code,response.text[:1200],file=sys.stderr)
    raise
print('Server-Antwort:',response.text[:2000])
print('Bitte in Paperclip prüfen, ob ggf. eine Genehmigung erforderlich ist. Kein LaunchAgent parallel aktivieren.')
