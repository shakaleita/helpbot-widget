import os, sys, importlib, tempfile, unittest
from pathlib import Path
class InsightsTest(unittest.TestCase):
    def test_insights_and_health(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ['DATABASE_PATH']=str(Path(tmp)/'test.db')
            sys.modules.pop('app',None)
            api=importlib.import_module('app').app.test_client()
            r=api.get('/api/health')
            self.assertEqual(r.status_code,200)
            self.assertEqual(r.json['status'],'ok')
            self.assertEqual(r.headers['X-Content-Type-Options'],'nosniff')
            r=api.get('/api/insights')
            self.assertEqual(r.status_code,200)
            self.assertIsInstance(r.json,dict)
