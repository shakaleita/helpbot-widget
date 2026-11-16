import os, sqlite3
from contextlib import contextmanager
from flask import Flask, jsonify, request, render_template
app=Flask(__name__)
app.config['MAX_CONTENT_LENGTH']=32768

# Optional local API token; production mode rejects unauthenticated API requests.
import hmac

@app.before_request
def require_api_auth():
    if not request.path.startswith('/api/') or request.path == '/api/health':
        return None
    token = os.getenv('API_TOKEN')
    if os.getenv('APP_ENV') != 'production' and not token:
        return None
    if not token:
        return jsonify(error='API authentication must be configured in production'), 503
    if not hmac.compare_digest(request.headers.get('X-API-Token', ''), token):
        return jsonify(error='Unauthorized'), 401
    return None


@contextmanager
def conn():
    db=sqlite3.connect(os.getenv('DATABASE_PATH','app.db'));db.row_factory=sqlite3.Row
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
with conn() as db:
    db.execute('CREATE TABLE IF NOT EXISTS faqs(id INTEGER PRIMARY KEY,question TEXT NOT NULL,answer TEXT NOT NULL,category TEXT NOT NULL DEFAULT "General")')
    if db.execute('SELECT COUNT(*) FROM faqs').fetchone()[0]==0:
        db.executemany('INSERT INTO faqs(question,answer,category) VALUES(?,?,?)',[('How do I reset my password?','Open settings and select Reset password.','Accounts'),('Where can I see my invoices?','Open Billing → Invoices.','Billing')])
@app.get('/')
def home():return render_template('index.html')
@app.get('/api/faqs')
def faqs():
    query=request.args.get('q','').strip().lower()
    if len(query)>120:return jsonify(error='Search query too long'),422
    with conn() as db:
        if query:
            # Literal substring search: wildcard characters are not SQL operators.
            literal=query.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
            pattern='%'+literal+'%'
            result=db.execute("""SELECT * FROM faqs
                WHERE lower(question) LIKE ? ESCAPE '\\'
                   OR lower(answer) LIKE ? ESCAPE '\\'
                ORDER BY CASE WHEN lower(question) LIKE ? ESCAPE '\\' THEN 0 ELSE 1 END,
                         id DESC LIMIT 50""",(pattern,pattern,pattern)).fetchall()
        else:result=db.execute('SELECT * FROM faqs ORDER BY id DESC LIMIT 50').fetchall()
        return jsonify([dict(row) for row in result])
@app.post('/api/faqs')
def create_faq():
    data=request.get_json(silent=True) or {};question=str(data.get('question','')).strip();answer=str(data.get('answer','')).strip();category=str(data.get('category','General')).strip() or 'General'
    if not question or not answer:return jsonify(error='Question and answer are required'),422
    with conn() as db:
        cur=db.execute('INSERT INTO faqs(question,answer,category) VALUES(?,?,?)',(question,answer,category))
        return jsonify(id=cur.lastrowid,question=question,answer=answer,category=category),201
@app.delete('/api/faqs/<int:id>')
def delete_faq(id):
    with conn() as db:
        if not db.execute('DELETE FROM faqs WHERE id=?',(id,)).rowcount:return jsonify(error='Not found'),404
        return jsonify(deleted=True)

@app.after_request
def security_headers(response):
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['X-Frame-Options']='DENY'
    return response
@app.get('/api/health')
def health():
    return jsonify(status='ok')
@app.get('/api/insights')
def insights():
    with conn() as db:
        return jsonify(total_faqs=db.execute('SELECT COUNT(*) FROM faqs').fetchone()[0],categories=[dict(r) for r in db.execute('SELECT category,COUNT(*) count FROM faqs GROUP BY category ORDER BY category')])




@app.get('/api/export/faqs.csv')
def export_faqs_csv():
    """Download a read-only snapshot of the local demo dataset."""
    from flask import Response
    from data_export import serialize_csv
    with conn() as connection:
        cursor = connection.execute("SELECT id,question,answer,category FROM faqs ORDER BY id")
        columns = [column[0] for column in cursor.description]
        content = serialize_csv(cursor.fetchall(), columns)
    response = Response(content, mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename="faqs.csv"'
    response.headers['Cache-Control'] = 'no-store'
    return response

if __name__=='__main__':app.run(debug=os.getenv('FLASK_DEBUG') == '1')
