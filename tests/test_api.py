import os, tempfile, unittest, importlib, sys
from pathlib import Path
class FAQTest(unittest.TestCase):
    def test_transaction_rolls_back_on_failure(self):
        """An exception must never leave a partially written transaction."""
        from importlib import import_module
        db_module = import_module('app')
        with self.assertRaises(RuntimeError):
            with db_module.conn() as connection:
                connection.execute("INSERT INTO faqs(question,answer) VALUES ('Transient question','Transient answer')")
                raise RuntimeError('simulate failed transaction')
        with db_module.conn() as connection:
            count = connection.execute("SELECT COUNT(*) FROM faqs WHERE question LIKE 'Transient%'").fetchone()[0]
        self.assertEqual(count, 0)

    def test_csv_export_endpoint(self):
        response=self.client.get('/api/export/faqs.csv')
        self.assertEqual(response.status_code,200)
        self.assertIn('text/csv',response.headers['content-type'])
        self.assertEqual(response.headers['cache-control'],'no-store')
        self.assertIn('"id"',response.get_data(as_text=True))


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
