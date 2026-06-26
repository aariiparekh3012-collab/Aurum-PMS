@echo off
title Seed Verification
cd /d "%~dp0backend"
echo.
echo ============================================================
echo  SEED VERIFICATION — checking all data via the live API
echo ============================================================
echo.

call .venv\Scripts\activate.bat 2>nul

python -c "
import urllib.request, json, sys

BASE = 'http://localhost:8000/api/v1'

def get(path, tok=None):
    req = urllib.request.Request(BASE + path)
    if tok: req.add_header('Authorization', 'Bearer ' + tok)
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read())
    except Exception as e:
        return {'__error__': str(e)}

def post(path, data, tok=None):
    body = json.dumps(data).encode()
    req = urllib.request.Request(BASE + path, body, {'Content-Type': 'application/json'})
    if tok: req.add_header('Authorization', 'Bearer ' + tok)
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read())
    except Exception as e:
        return {'__error__': str(e)}

# Health
h = get('/healthz')
if '__error__' in h:
    print('ERROR: Backend not reachable:', h['__error__'])
    print('Make sure uvicorn is running (uvicorn app.main:app --reload)')
    sys.exit(1)
print('Backend health:', h)

# Dev token
t = post('/auth/token', {'username': 'seed.compliance', 'role': 'compliance'})
if '__error__' in t:
    print('ERROR: Token failed:', t['__error__'])
    sys.exit(1)
tok = t['access_token']

# ---- USERS ----
print()
print('=== USER LOGINS ===')
for email, pw in [
    ('admin@aurumpms.com',      'Admin@123'),
    ('compliance@aurumpms.com', 'Comply@123'),
    ('rm@aurumpms.com',         'Manager@123'),
    ('ojas@aurumpms.com',       'Investor@123'),
]:
    r = post('/auth/login', {'email': email, 'password': pw})
    status = 'OK  login works' if 'access_token' in r else 'MISSING  ' + r.get('__error__', str(r))
    print(f'  {email:35s} -> {status}')

# ---- DASHBOARD ----
d = get('/dashboard', tok)
print()
print('=== DASHBOARD STATS ===')
if '__error__' in d:
    print('  ERROR:', d['__error__'])
else:
    print(f'  Total clients:        {d[\"total_clients\"]}')
    print(f'  Active clients:       {d[\"active_clients\"]}')
    print(f'  Total applications:   {d[\"total_applications\"]}')
    print(f'  Pending review:       {d[\"pending_review\"]}')
    print(f'  Portfolio accounts:   {d[\"total_portfolio_accounts\"]}')
    print(f'  Pending orders:       {d[\"pending_orders\"]}')
    aum_cr = d['total_aum_paise'] / 1e9
    print(f'  AUM (approx):         Rs {aum_cr:.2f} Cr')
    print()
    print('  Applications by status:')
    for s in d.get('applications_by_status', []):
        print(f'    {s[\"status\"]:20s}: {s[\"count\"]}')
    print()
    print('  Clients by risk:')
    for r in d.get('clients_by_risk', []):
        print(f'    {r[\"category\"]:20s}: {r[\"count\"]}')

# ---- CLIENTS ----
clients = get('/clients', tok)
print()
print(f'=== CLIENTS ({len(clients) if isinstance(clients, list) else \"ERR\"}) ===')
if isinstance(clients, list):
    for c in clients:
        print(f'  {c[\"full_name\"]:22s} status={c[\"status\"]:10s} risk={c.get(\"risk_category\") or \"-\"}')
else:
    print('  ERROR:', clients)

# ---- APPLICATIONS ----
apps = get('/onboarding/applications', tok)
print()
print(f'=== ONBOARDING APPLICATIONS ({len(apps) if isinstance(apps, list) else \"ERR\"}) ===')
if isinstance(apps, list):
    for a in apps:
        print(f'  {a.get(\"full_name\",\"-\"):22s} status={a.get(\"status\",\"-\")}')

# ---- REFERENCE ----
sec = get('/reference/securities', tok)
strat = get('/reference/strategies', tok)
brok = get('/reference/brokers', tok)
print()
print(f'=== REFERENCE DATA ===')
print(f'  Securities: {len(sec) if isinstance(sec, list) else \"ERR\"}')
print(f'  Strategies: {len(strat) if isinstance(strat, list) else \"ERR\"}  -> ', end='')
if isinstance(strat, list):
    print(', '.join(s[\"code\"] for s in strat))
print(f'  Brokers:    {len(brok) if isinstance(brok, list) else \"ERR\"}')

# ---- ORDERS + TRADES ----
orders = get('/trading/orders', tok)
trades = get('/trading/trades', tok)
print()
print(f'=== TRADING ===')
print(f'  Orders: {len(orders) if isinstance(orders, list) else \"ERR\"}')
if isinstance(orders, list):
    pending = [o for o in orders if o.get('status') == 'pending_approval']
    filled  = [o for o in orders if o.get('status') == 'approved']
    print(f'    Pending approval: {len(pending)}')
    print(f'    Approved/filled:  {len(filled)}')
print(f'  Trades: {len(trades) if isinstance(trades, list) else \"ERR\"}')

# ---- PORTFOLIO ACCOUNTS ----
accts = get('/portfolio/accounts', tok)
print()
print(f'=== PORTFOLIO ACCOUNTS ({len(accts) if isinstance(accts, list) else \"ERR\"}) ===')
if isinstance(accts, list):
    for a in accts:
        print(f'  {a.get(\"account_code\",\"?\"):12s}  strategy={a.get(\"strategy_id\",\"?\")[:8]}...')

print()
print('============================================================')
print(' VERIFICATION COMPLETE')
print('============================================================')
print()
print('Open the app at: http://localhost:5173')
print('API docs at:     http://localhost:8000/docs')
"

echo.
pause
