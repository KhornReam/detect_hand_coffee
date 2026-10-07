# Brew & Co. Smart Coffee Ordering Kiosk

A local-first coffee kiosk with a responsive customer ordering flow, an admin workspace for products, categories, menu pricing, café contacts and customer records, server-validated pricing, MySQL order storage, drag-and-drop kitchen order statuses, and optional webcam hand gestures. The default ordering flow works with touch, mouse, and keyboard; camera support is optional.

## Run locally

Requires Python 3.11. From the project root:

```powershell
$python311 = Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\python.exe"
& $python311 --version
& $python311 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
$env:KIOSK_ADMIN_EMAIL = "admin@brewco.local"
$env:KIOSK_ADMIN_PASSWORD = "Choose-a-unique-long-password"
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8001 --reload
```

Open <http://127.0.0.1:8001>. Windows denied the default port 8000 on this machine (`WinError 10013`), so use port 8001. If that port is already in use, choose another port such as 8002 in both the command and browser URL. The app connects to the MySQL database `coffee_sell` and creates its `orders` table on first start. It serves its frontend and API from the same origin. Stop with Ctrl+C.

### MySQL connection

The backend reads its connection settings from the root `.env` file. The project `.env.example` shows the required names. Keep `.env` private; it is ignored by Git. Local Laragon defaults are `127.0.0.1:3306` and database `coffee_sell`. This project has a dedicated local account named `coffee_sell_app`, restricted to that database; its password is stored only in the ignored `.env` file. The account needs `SELECT`, `INSERT`, `UPDATE`, `DELETE`, and `CREATE` privileges. The app does not silently fall back to SQLite. The health endpoint at <http://127.0.0.1:8001/api/health> reports the connected database and MySQL version.

If you already have orders in the earlier `data/orders.sqlite3`, startup copies them into MySQL with duplicate-safe inserts and leaves the SQLite file intact. New orders and staff status changes are written to MySQL.

### Configure the administrator account

Set your own admin email and strong password in the same PowerShell window before starting Uvicorn. Replace these example values; the app does not ship with a shared default password:

```powershell
$env:KIOSK_ADMIN_EMAIL = "your-admin@email.com"
$env:KIOSK_ADMIN_PASSWORD = "Your-unique-long-password"
```

Open the customer menu at <http://127.0.0.1:8001> and choose **Admin sign in** in the footer. Admin sessions use an HttpOnly, SameSite cookie and expire after eight hours. The signing key is generated locally in `data/admin_signing.key`; keep it private and backed up if sessions must survive moving the installation. All admin menu, contact, customer-record and order management requires login. Customer menu and order submission remain public. This single-admin MVP has no password reset or staff accounts. Customers can create an account or sign in from the storefront; customer passwords are salted and hashed, and sessions use HttpOnly cookies. Contact form messages and customer accounts are stored in MySQL.

Hand controls work across the customer ordering pages. Choose **Camera & gestures**, then **Open camera** and allow access in the browser. After this one-time permission step, you can browse and order with gestures. Hand landmarks are detected in the browser using MediaPipe; only landmark coordinates are sent to the local backend for gesture mapping. Video frames are not sent to the backend or saved. Internet access is needed to load the MediaPipe browser assets on first use. Choose **Close camera** to stop the camera. The live badge shows the detected gesture and its shape confidence.

No extra Python computer-vision packages are required for browser hand controls. Touch, mouse and keyboard ordering always work.

Voice control is available from the **Voice control** button in the header on browsers that expose the Web Speech recognition API. Starting it requests microphone access; the status label reports listening, recognized commands, and permission or availability errors. Commands include “go home,” “open menu,” “next coffee,” “show me Latte,” “large,” “less sugar,” “add to cart,” “open cart,” “checkout,” “cancel,” “contact,” “sign in,” “register,” “refresh,” “sign out,” and “confirm order.” Slightly misheard drink names still match the menu, and the kiosk keeps listening after pauses until you press Stop voice. Commands are interpreted against the current page, so product customizations only apply while a drink is open, and customer commands are ignored inside the admin workspace — which instead answers “orders,” “products,” “categories,” “contact,” “messages,” “users,” “settings,” and “refresh.” A held fist (or “cancel”) steps back from any customer page — customization, bag, checkout, receipt, contact, sign in or admin sign in — without clearing the bag. Gallery photos open the drink they show. The **Sound on/off** control toggles short interface tones. Spoken responses follow Voice control and are disabled when listening is stopped. Speech recognition support and availability depend on the browser and device.

For macOS/Linux, create and activate `.venv` with the platform's normal `python3.11 -m venv .venv` and `. .venv/bin/activate` commands; the remaining commands are the same.

## Use the kiosk

1. Choose a category or search the menu.
2. Open a drink to select size, temperature, sugar, milk, extras and quantity.
3. Add it to the bag, review the bag, and open checkout.
4. Confirm the order. No payment is collected in this MVP.
5. Save the receipt with the browser's Print dialog. The single admin can sign in from **Admin sign in** in the footer. Order cards can be pinched and dragged to another status column or updated with the status selector.

Use **Contact** in the top navigation to send the café a message. Use **Sign in** in the top bar to register or sign in as a customer. MySQL creates the required customer account and contact message tables on the next server startup. The app uses a five-minute inactivity timeout with a 30-second warning. Session cart data stays in `sessionStorage` and is cleared after a completed order or timeout. The order submission key is retained across a retried request so a network retry cannot create a second order.

## Menu and pricing

Manage products, categories, product availability, customization prices and service fees from the authenticated admin dashboard. Changes are validated and atomically saved to [`data/menu.json`](data/menu.json), which remains available for direct local configuration. The Contact section manages the café details shown on the customer page. The customer Contact page stores messages in MySQL, and the admin Messages tab provides the inbox. The Users section manages customer contact records and registered customer details. On confirmation, the API independently checks product availability and customization IDs and recalculates prices from the menu before saving the order. Currency formatting is currently USD.

## Gestures

The **How to Use Hand Control** page explains the ordering flow. The index fingertip moves a visible cursor; a control glows green when targeted. Hold a natural pinch briefly and release once on that same control to select it. The target is locked when the pinch starts, so finger movement during the pinch will not cancel selection. Moving a closed pinch across controls never selects the release target. Directional hand movement scrolls or advances focus. On checkout, hold a pinch over **Confirm** to place the order. The receipt displays the order number. Landmark-shape confidence is a tracking estimate, not a calibrated probability.

| Gesture | Kiosk action |
| --- | --- |
| One finger | Point and move the hand cursor |
| Pinch and release | Select the highlighted item |
| Hold closed fist briefly | Cancel the current step and go back; cart contents are kept |
| Move hand right / left | Next / previous choice |
| Move hand up / down | Scroll the page |

Pinch distance is normalized against palm width (0.38 ratio) to reduce variation as the hand moves closer to or farther from the camera. The green target highlight includes a short jitter grace period, and customer selection uses the target chosen at pinch start, ignoring the index finger shift as the hand pinches. Lighting, camera angle, and tracking quality still affect reliability; the cursor and selection feedback help show when a control is ready.

## Architecture

```text
Browser kiosk (HTML / CSS / ES modules)
  ├── /api/menu ─────────────> menu.json
  ├── /api/orders ───────────> validation + MySQL (`coffee_sell`)
  ├── /api/admin/orders/{id} ──> authenticated kitchen status updates
  └── /ws/gestures ──────────> camera → MediaPipe landmarks → gesture commands
```

See [`docs/architecture.md`](docs/architecture.md) for the architecture and customer-flow diagrams, boundaries and manual verification checklist.

## Project layout

```text
backend/       FastAPI routes, menu/cart/order persistence, CV and gesture modules
data/menu.json Configurable starter menu
frontend/      Kiosk HTML, responsive CSS and separated browser modules
docs/          Architecture, customer flow, operational notes
```

## MVP boundaries

- Orders are saved in MySQL database `coffee_sell`. This is not a payment system; customer accounts use password hashes and signed browser sessions.
- The admin workspace uses one environment-configured account. Its customer records are not customer login accounts. It has no password reset, staff roles, or production deployment hardening. Keep the service on a trusted network.
- Photos are remote Unsplash URLs, so menu photography needs an internet connection. Replace them with licensed local assets for offline/commercial deployment.
- English is the implemented interface language. Khmer localization is not included yet.
- PostgreSQL, inventory management, order-preparation estimates and production deployment controls are future expansions.
