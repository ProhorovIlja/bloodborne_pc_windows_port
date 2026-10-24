from html.parser import HTMLParser
from pathlib import Path
import unittest

HERE=Path(__file__).parent/"site"
class HtmlAudit(HTMLParser):
    def __init__(self):
        super().__init__()
        self.external_scripts=[]
        self.links=[]
        self.ids=set()
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=="script" and a.get("src","").startswith(("http:","https:")):
            self.external_scripts.append(a["src"])
        if tag=="a":self.links.append(a.get("href",""))
        if "id" in a:self.ids.add(a["id"])
class TestSite(unittest.TestCase):
    def test_portal_never_fakes_live_metrics(self):
        text=(HERE/"index.html").read_text("utf-8")
        html=HtmlAudit();html.feed(text)
        self.assertEqual(html.external_scripts,[])
        for id in ["hunters","areas","feed","status","area-rows"]:
            self.assertIn(id,html.ids)
        self.assertIn('fetch("/api/public/v1/presence"',text)
        self.assertIn('data.source!=="authoritative_server"',text)
        self.assertIn('data.location_precision!=="area_only"',text)
        self.assertIn('textContent=',text)
        self.assertIn("No verified data available",text)
        self.assertNotIn("618 hunters",text)
        self.assertTrue(any("github.com/ProhorovIlja/bloodborne_pc_windows_port/releases" in l
                            for l in html.links))
    def test_no_unimplemented_account_login(self):
        text=(HERE/"index.html").read_text("utf-8")
        self.assertIn("not available yet",text)
        self.assertNotIn('type="password"',text)
        self.assertNotIn("Discord OAuth",text)
    def test_challenge_exists_without_game_modifications(self):
        h=(HERE/"challenge.html").read_text("utf-8")
        self.assertIn('import {generateChallenge} from "./challenges.mjs"',h)
        self.assertIn("Offline",h.title() if hasattr(h,"title") else h)
        self.assertNotIn('type="file"',h)
if __name__=="__main__":unittest.main()
