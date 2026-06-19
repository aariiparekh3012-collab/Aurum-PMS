# Aurum PMS — Mobile App

React Native (Expo) app for the Aurum PMS platform.
Connects to the same FastAPI backend as the web app.

---

## Quick start (2 steps)

### Prerequisites
- Node 20+ installed
- Expo Go app on your phone ([iOS](https://apps.apple.com/app/expo-go/id982107779) / [Android](https://play.google.com/store/apps/details?id=host.exp.exponent))
- Backend running (`docker compose up -d` in the project root)

### Step 1 — Install & start

```bash
cd mobile
npm install
npm start
```

Expo will print a QR code in the terminal.

### Step 2 — Connect

**On your phone:** open **Expo Go** → scan the QR code.

> Make sure your phone and computer are on the **same WiFi network**.

---

## API URL configuration

`app.json` → `extra.apiBaseUrl` controls which backend the app talks to:

| Where you're running | Set apiBaseUrl to |
|---|---|
| Android emulator | `http://10.0.2.2:8000/api/v1` (default) |
| iOS simulator | `http://localhost:8000/api/v1` |
| Physical phone on same WiFi | `http://YOUR_COMPUTER_IP:8000/api/v1` |
| Production server | `https://yourdomain.com/api/v1` |

Find your computer's IP:
- **Windows**: `ipconfig` → look for IPv4 Address (e.g. `192.168.1.45`)
- **Mac/Linux**: `ifconfig | grep "inet "` → look for your local IP

Then update `app.json`:
```json
"extra": {
  "apiBaseUrl": "http://192.168.1.45:8000/api/v1"
}
```

---

## Login

Use the same credentials as the web app:

| Role | Email | Password |
|---|---|---|
| Investor | `asha@example.com` | `investor123` |
| Compliance / RM | Register via onboarding flow or use backend admin |

> The mobile app uses real JWT auth against the backend.
> The Quick Demo Access buttons (dev-token) are web-only.

---

## Features

- **Login** with JWT + biometric unlock (Face ID / fingerprint) on re-open
- **Dashboard** — KPIs, application status donut chart, risk bar chart, recent applications
- **Onboarding** — 4-step form: personal details → KYC → risk profile → agreement
- **Applications** — list with status filter, approve/reject for compliance
- **Compliance review** — dedicated compliance queue with decision modal
- **Clients** — searchable list, tap for full client detail
- **Portfolio** — account selector, holdings table, cash ledger
- **Trading** — order book with status filter, place new orders
- **Performance** — period returns (1M/3M/6M/1Y/SI), NAV chart, AUM
- **Reports** — generate PDF statements per account
- **Investor portal** — investor-only view: own portfolio, returns, holdings
- **Settings** — theme, notification prefs
- **Profile** — user info, sign out

---

## Run on emulator

```bash
# Android (requires Android Studio + emulator running)
npm run android

# iOS (Mac only, requires Xcode)
npm run ios
```

---

## Troubleshooting

**"Network request failed"**
→ Phone can't reach the backend. Update `apiBaseUrl` in `app.json` to your computer's IP address (see above).

**"Unable to resolve module expo-constants"**
→ Run `npm install` again.

**Expo QR code not scanning**
→ Make sure phone and laptop are on the same WiFi. Try pressing `w` in the Expo terminal to open web version for quick verification.

**Backend not running**
→ From the project root: `docker compose up -d` then wait ~30 sec for health checks.
