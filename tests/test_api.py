import os, tempfile, unittest, importlib, sys
from pathlib import Path
class FAQTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        os.environ['DATABASE_PATH']=str(Path(cls.tmp.name)/'test.db')
        sys.modules.pop('app',None)
        cls.client=importlib.import_module('app').app.test_client()
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def test_create_search_delete(self):
        r=self.client.post('/api/faqs',json={'question':'How to export?','answer':'Click Export','category':'Reports'})
        self.assertEqual(r.status_code,201)
        ident=r.json['id']
        self.assertTrue(any(x['id']==ident for x in self.client.get('/api/faqs?q=export').json))
        self.assertEqual(self.client.delete(f'/api/faqs/{ident}').status_code,200)
        self.assertFalse(any(x['id']==ident for x in self.client.get('/api/faqs?q=export').json))
    def test_validation(self):
        self.assertEqual(self.client.post('/api/faqs',json={'question':'','answer':'Hi'}).status_code,422)
