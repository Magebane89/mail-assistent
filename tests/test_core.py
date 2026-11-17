import base64
import importlib.util
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
import unittest

BASE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('assistant_app',BASE/'assistant_app.py')
appmod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(appmod)


class CoreTests(unittest.TestCase):
    def test_multipart_message(self):
        payload={'mimeType':'multipart/mixed','parts':[
            {'mimeType':'text/plain','body':{'data':base64.urlsafe_b64encode('Sehr geehrte Damen'.encode()).decode()}},
            {'filename':'Rechnung.pdf','mimeType':'application/pdf','body':{'size':120,'attachmentId':'abc'}}]}
        text,files=appmod.body_and_attachments(payload)
        self.assertIn('Damen',text)
        self.assertEqual(files[0]['name'],'Rechnung.pdf')

    def test_html_disables_script(self):
        parser=appmod.PlainHtml();parser.feed('<p>Rechnung</p><script>send all mail</script>')
        self.assertNotIn('send all', ''.join(parser.fragments))

    def test_receipt_types_for_three_cases(self):
        self.assertEqual(appmod.fallback_receipt_type('Ihre Rechnung', 'Lieferant', 'Hallo', [{'name':'rechnung.pdf','inline':False}]), 'attachment')
        self.assertEqual(appmod.fallback_receipt_type('Ihre Apple Rechnung', 'Apple', 'Ihre monatliche Rechnung 2026. Gesamtsumme 9,99 EUR inkl. MwSt. Vielen Dank für Ihren Einkauf.', []), 'email_pdf')
        self.assertEqual(appmod.fallback_receipt_type('Tesla Rechnung verfügbar', 'Tesla', 'Rechnung im Kundenkonto herunterladen', []), 'portal')

    def test_inline_logo_is_not_invoice_attachment(self):
        payload={'mimeType':'multipart/related','parts':[
            {'mimeType':'text/html','body':{'data':base64.urlsafe_b64encode(('Vielen Dank für Ihren Kauf. Rechnung 2026-10, Betrag 10 Euro. ' * 3).encode()).decode()}},
            {'filename':'logo.png','mimeType':'image/png', 'headers':[{'name':'Content-ID','value':'<logo>'}], 'body':{'attachmentId':'xxx','size':200}}]}
        text,files=appmod.body_and_attachments(payload)
        self.assertTrue(files[0]['inline'])
        self.assertEqual(appmod.fallback_receipt_type('Apple Rechnung','Apple',text,files),'email_pdf')

    def test_email_to_pdf(self):
        from io import BytesIO
        text='Rechnung 2026/45, Summe 14,95 EUR, Cloud-Abo. ' * 3
        pdf=appmod.create_email_pdf({'body':text,'subject':'Ihre Rechnung','sender':'Test','received_at':'2026-11-13'})
        self.assertTrue(pdf.startswith(b'%PDF-'))
        self.assertGreater(len(pdf),1000)

    def test_model_fallback_with_invoice(self):
        class Fail:
            def __call__(self,*a,**k):
                raise appmod.requests.Timeout('offline')
        with patch.object(appmod.requests,'post',Fail()):
            result=appmod.classify('Ihre Rechnung','Firma','Hallo',[{'name':'2026.pdf'}])
        self.assertTrue(result['receipt_candidate'])
        self.assertEqual(result['category'],'Buchhaltung')

    def test_send_disabled_by_default(self):
        with patch.dict(appmod.os.environ,{'ENABLE_SEND':'0'},clear=False):
            with self.assertRaisesRegex(RuntimeError,'deaktiviert'):
                appmod.send_approved('real-id')

    def test_demo_cannot_send(self):
        with patch.dict(appmod.os.environ,{'ENABLE_SEND':'1'},clear=False):
            with self.assertRaisesRegex(RuntimeError,'Demo'):
                appmod.send_approved('demo-rechnung-1')

    def test_dashboard_requires_basic_auth(self):
        client=appmod.app.test_client()
        r=client.get('/',base_url='http://127.0.0.1:8765')
        self.assertEqual(r.status_code,401)

    def test_webhook_requires_secret(self):
        client=appmod.app.test_client()
        r=client.post('/paperclip/heartbeat',base_url='http://127.0.0.1:8765',json={})
        self.assertEqual(r.status_code,401)


    # --- Mehrere Postfächer / Verbinden per Knopf ---
    def _auth(self):
        token=base64.b64encode(('admin:'+appmod.DASHBOARD_PASSWORD).encode()).decode()
        return {'Authorization':'Basic '+token}

    def test_outlook_ids_are_short_and_safe(self):
        local=appmod.ms_local_id('Me@Example.org','AAMkAD/+=='*20)
        self.assertEqual(appmod.safe_message_id(local),local)
        self.assertEqual(local,appmod.ms_local_id('me@example.org','AAMkAD/+=='*20))

    def test_scan_days_follow_query(self):
        with patch.dict(appmod.os.environ,{'GMAIL_QUERY':'newer_than:30d -in:spam'},clear=False):
            self.assertEqual(appmod.scan_days(),30)
        with patch.dict(appmod.os.environ,{'GMAIL_QUERY':'is:unread'},clear=False):
            self.assertEqual(appmod.scan_days(),7)

    def test_pkce_challenge_matches_verifier(self):
        import hashlib
        verifier,challenge=appmod.pkce_pair()
        expected=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        self.assertEqual(challenge,expected)

    def test_settings_require_basic_auth(self):
        client=appmod.app.test_client()
        self.assertEqual(client.get('/einstellungen',base_url='http://127.0.0.1:8765').status_code,401)
        self.assertEqual(client.post('/einstellungen/verbinden/google',base_url='http://127.0.0.1:8765').status_code,401)

    def test_connect_requires_csrf(self):
        client=appmod.app.test_client()
        r=client.post('/einstellungen/verbinden/google',base_url='http://127.0.0.1:8765',headers=self._auth())
        self.assertEqual(r.status_code,403)

    def test_actions_without_session_token_are_refused(self):
        client=appmod.app.test_client()
        for path in ('/action/abcdef','/portal/upload/abcdef','/einstellungen/konto/1/trennen','/einstellungen/kennung/microsoft'):
            r=client.post(path,base_url='http://127.0.0.1:8765',headers=self._auth(),data={'do':'ignore','csrf':''})
            self.assertEqual(r.status_code,403,path)

    def test_callback_rejects_unknown_state(self):
        client=appmod.app.test_client()
        r=client.get('/oauth/callback/google?state=erfunden&code=x',base_url='http://127.0.0.1:8765')
        self.assertEqual(r.status_code,400)
        self.assertEqual(client.get('/oauth/callback/microsoft',base_url='http://localhost:8765').status_code,400)

    def _token_response(self,payload):
        class Fake:
            status_code=200
            def json(self_inner): return payload
        return Fake()

    def test_google_grant_beyond_readonly_is_refused(self):
        entry={'client':{'client_id':'x','client_secret':'y'},'redirect_uri':'http://127.0.0.1:8765/oauth/callback/google','verifier':'v'}
        payload={'access_token':'a','refresh_token':'r','scope':appmod.READ_SCOPE+' '+appmod.SEND_SCOPE}
        with patch.object(appmod.requests,'post',return_value=self._token_response(payload)), \
             patch.object(appmod,'upsert_account') as saved:
            with self.assertRaisesRegex(RuntimeError,'mehr als den Lesezugriff'):
                appmod.finish_google(entry,'code')
            saved.assert_not_called()

    def test_microsoft_grant_beyond_readonly_is_refused(self):
        entry={'client':{'client_id':'x','tenant':'common'},'redirect_uri':'http://localhost:8765/oauth/callback/microsoft','verifier':'v'}
        payload={'access_token':'a','refresh_token':'r','scope':'https://graph.microsoft.com/Mail.Read https://graph.microsoft.com/Mail.Send'}
        with patch.object(appmod.requests,'post',return_value=self._token_response(payload)), \
             patch.object(appmod,'upsert_account') as saved:
            with self.assertRaisesRegex(RuntimeError,'mehr als den Lesezugriff'):
                appmod.finish_microsoft(entry,'code')
            saved.assert_not_called()

    def test_microsoft_connect_saves_readonly_account(self):
        claims=base64.urlsafe_b64encode(json.dumps({'email':'Person@Outlook.com'}).encode()).decode().rstrip('=')
        entry={'client':{'client_id':'x','tenant':'common'},'redirect_uri':'http://localhost:8765/oauth/callback/microsoft','verifier':'v'}
        payload={'access_token':'a','refresh_token':'r','expires_in':3600,'id_token':'h.'+claims+'.s',
                 'scope':'openid email https://graph.microsoft.com/Mail.Read'}
        with patch.object(appmod.requests,'post',return_value=self._token_response(payload)), \
             patch.object(appmod,'upsert_account') as saved:
            self.assertEqual(appmod.finish_microsoft(entry,'code'),'person@outlook.com')
            self.assertEqual(saved.call_args[0][:2],('microsoft','Person@Outlook.com'))

    def test_outlook_message_is_normalised(self):
        box=appmod.MicrosoftBox.__new__(appmod.MicrosoftBox)
        box.account={'email':'me@outlook.com'}; box.token='t'
        message={'id':'RID','conversationId':'C1','subject':'Ihre Rechnung','hasAttachments':True,'isDraft':False,
                 'from':{'emailAddress':{'name':'Lieferant GmbH','address':'billing@example.org'}},
                 'receivedDateTime':'2026-11-15T12:01:00Z','body':{'contentType':'text','content':'Anbei die Rechnung.'},
                 'webLink':'https://outlook.live.com/owa/?ItemID=RID'}
        files={'value':[{'name':'Rechnung.pdf','contentType':'application/pdf','size':1200,'isInline':False}]}
        with patch.object(box,'_get',side_effect=[message,files]):
            msg=box.fetch('RID')
        self.assertEqual(msg['sender'],'Lieferant GmbH <billing@example.org>')
        self.assertEqual(msg['received_at'],'2026-11-15T12:01:00+00:00')
        self.assertEqual(msg['parts'][0]['name'],'Rechnung.pdf')
        self.assertEqual(msg['id'],appmod.ms_local_id('me@outlook.com','RID'))
        self.assertEqual(appmod.fallback_receipt_type(msg['subject'],msg['sender'],msg['body'],msg['parts']),'attachment')

    def test_graph_token_never_leaves_microsoft(self):
        box=appmod.MicrosoftBox.__new__(appmod.MicrosoftBox)
        box.account={'email':'me@outlook.com'}; box.token='t'
        with patch.object(appmod.requests,'get') as call:
            with self.assertRaises(RuntimeError):
                box._get('https://evil.example/v1.0/me/messages')
            call.assert_not_called()

    def test_login_code_gets_low_priority(self):
        answer={'category':'Konto & Sicherheit','priority':'hoch','summary':'E-Mail mit einem Anmeldecode (10 Minuten gültig).',
                'receipt_type':'none','confidence':0.9}
        class Fake:
            def raise_for_status(self): pass
            def json(self): return {'message':{'content':json.dumps(answer)}}
        with patch.object(appmod.requests,'post',return_value=Fake()):
            result=appmod.classify('Dein Code','noreply@example.org','Code: 123456',[])
        self.assertEqual(result['priority'],'niedrig')
        self.assertIn('Konto & Sicherheit',appmod.VALID_CATEGORIES)
        self.assertNotIn('Wichtig',appmod.VALID_CATEGORIES)

    def _mime(self, html):
        from email.message import EmailMessage
        m=EmailMessage(); m['From']='a@example.org'; m['Subject']='Rechnung'
        m.set_content('Text'); m.add_alternative(html,subtype='html')
        m.get_payload()[1].add_related(b'\x89PNG fake',maintype='image',subtype='png',cid='<logo1>')
        return m.as_bytes()

    def test_html_pdf_document_is_inert(self):
        html=('<html><body onload="x()"><script>alert(1)</script><iframe src="https://e.example"></iframe>'
              '<a href="javascript:alert(1)">x</a><img src="cid:logo1"><img src="https://img.example/t.gif">'
              '<form action="https://e.example"><input></form><p style="background:url(https://img.example/b.png)">Summe 9,99</p></body></html>')
        with patch.dict(appmod.os.environ,{'PDF_LOAD_IMAGES':'0'}), patch.object(appmod.requests,'get') as net:
            doc=appmod.mail_html_document(self._mime(html),{'sender':'<b>A</b>','subject':'S','received_at':'2026-11-13T10:00:00+00:00'})
            net.assert_not_called()
        low=doc.lower()
        for bad in ('<script','onload','<iframe','javascript:','<form','https://img.example'):
            self.assertNotIn(bad,low)
        self.assertIn('data:image/png;base64,',doc)        # eingebettetes cid-Bild
        self.assertIn("default-src 'none'",doc)             # Dokument darf selbst nichts laden
        self.assertIn('&lt;b&gt;A&lt;/b&gt;',doc)           # Kopfzeile escaped
        self.assertIn('Summe 9,99',doc)

    def test_remote_images_only_from_public_hosts(self):
        loader=appmod.ImageLoader({},True)
        with patch.object(appmod.requests,'get') as net:
            for url in ('http://127.0.0.1:8765/x.png','http://localhost/x.png','http://192.168.1.1/x.png','ftp://e.example/x.png'):
                self.assertEqual(loader.data_uri(url),'')
            net.assert_not_called()

    def test_receipt_pdf_falls_back_to_text(self):
        msg={'sender':'a@example.org','subject':'Rechnung','received_at':'2026-11-13T10:00:00+00:00',
             'body':'Rechnung Nr. 1, Betrag 9,99 EUR, zahlbar sofort. '*3}
        with patch.object(appmod,'find_chrome',return_value=None):
            pdf=appmod.build_receipt_pdf(self._mime('<p>Rechnung</p>'),msg)
        self.assertTrue(pdf.startswith(b'%PDF-'))

if __name__=='__main__':
    unittest.main()
