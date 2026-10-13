"""Sweet Cravings local web server. Python 3.9+, no external packages."""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlparse
import sqlite3, json, os, hashlib, hmac, secrets, time, re

ROOT = Path(__file__).resolve().parent
DB = ROOT / 'bakery.sqlite3'

def db():
    conn = sqlite3.connect(DB, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    return conn

def init():
    with db() as c:
        c.execute('CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, salt BLOB NOT NULL, password BLOB NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), expires INTEGER NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS orders(user_id INTEGER PRIMARY KEY REFERENCES users(id), data TEXT NOT NULL)')

def password_hash(password, salt):
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 260000)

class Handler(BaseHTTPRequestHandler):
    def send(self, code, payload, cookie=None):
        raw = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(raw)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        if cookie: self.send_header('Set-Cookie',cookie)
        self.end_headers(); self.wfile.write(raw)
    def current_user(self):
        cookie=SimpleCookie()
        try: cookie.load(self.headers.get('Cookie',''))
        except Exception: return None
        if 'session' not in cookie:return None
        token=cookie['session'].value
        with db() as c:
            return c.execute('SELECT users.id, users.name, users.email FROM sessions JOIN users ON users.id=sessions.user_id WHERE token_hash=? AND expires>?',(hashlib.sha256(token.encode()).hexdigest(),int(time.time()))).fetchone()
    def create_session(self, user_id):
        token=secrets.token_urlsafe(40)
        with db() as c:
            c.execute('INSERT INTO sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),user_id,int(time.time())+7*86400))
        return f'session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=604800'
    def read_json(self):
        size=int(self.headers.get('Content-Length','0'))
        if size>1000000: raise ValueError('Request too large')
        return json.loads(self.rfile.read(size))
    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/':
            raw=(ROOT/'index.html').read_bytes()
            self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw);return
        if path=='/api/me':
            u=self.current_user();return self.send(200,{'user':dict(u) if u else None})
        if path=='/api/orders':
            u=self.current_user()
            if not u:return self.send(401,{'error':'Please log in'})
            with db() as c: row=c.execute('SELECT data FROM orders WHERE user_id=?',(u['id'],)).fetchone()
            return self.send(200,{'orders':json.loads(row['data']) if row else []})
        self.send(404,{'error':'Not found'})
    def do_POST(self):
        path=urlparse(self.path).path
        try: body=self.read_json()
        except (ValueError,TypeError,json.JSONDecodeError):return self.send(400,{'error':'Invalid request'})
        if path=='/api/register':
            name=str(body.get('name','')).strip()[:100];email=str(body.get('email','')).strip().lower();password=str(body.get('password',''))
            if not name or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email) or len(email)>254 or len(password)<10 or len(password)>200:
                return self.send(400,{'error':'Enter your name, a valid email, and a password of at least 10 characters.'})
            salt=os.urandom(16)
            try:
                with db() as c:
                    cur=c.execute('INSERT INTO users(name,email,salt,password) VALUES(?,?,?,?)',(name,email,salt,password_hash(password,salt)))
                    user_id=cur.lastrowid
            except sqlite3.IntegrityError:return self.send(409,{'error':'An account with this email already exists.'})
            return self.send(201,{'user':{'id':user_id,'name':name,'email':email}},self.create_session(user_id))
        if path=='/api/login':
            email=str(body.get('email','')).strip().lower();password=str(body.get('password',''))
            with db() as c: user=c.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
            if not user or not hmac.compare_digest(password_hash(password,user['salt']),user['password']):return self.send(401,{'error':'Incorrect email or password.'})
            return self.send(200,{'user':{'id':user['id'],'name':user['name'],'email':user['email']}},self.create_session(user['id']))
        if path=='/api/logout':
            cookie=SimpleCookie()
            try:cookie.load(self.headers.get('Cookie',''))
            except Exception:pass
            if 'session' in cookie:
                with db() as c:c.execute('DELETE FROM sessions WHERE token_hash=?',(hashlib.sha256(cookie['session'].value.encode()).hexdigest(),))
            return self.send(200,{'ok':True},'session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
        if path=='/api/orders':
            u=self.current_user()
            if not u:return self.send(401,{'error':'Please log in'})
            orders=body.get('orders')
            if not isinstance(orders,list) or len(orders)>10000:return self.send(400,{'error':'Invalid orders'})
            with db() as c:c.execute('INSERT INTO orders(user_id,data) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET data=excluded.data',(u['id'],json.dumps(orders)))
            return self.send(200,{'ok':True})
        return self.send(404,{'error':'Not found'})

if __name__=='__main__':
    init()
    print('Open http://localhost:8765 in your browser')
    ThreadingHTTPServer(('127.0.0.1',8765),Handler).serve_forever()
