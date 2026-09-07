# BatteryWala + Engine D-Carb Full Stack

A deployable Flask application containing:
- Separate BatteryWala and Engine D-Carb public websites on two domains
- One role-based operations portal for administrators and employees
- Consented customer-request storage with automatic 24-month deletion
- Per-business dashboard filters and selectable-column Excel exports
- Admin-managed employee accounts and employee-only expert recommendation fields
- Public battery recommendation form
- Admin-only pricing workspace
- PDF upload, OCR fallback, preview and publish
- Atomic replacement of the current pricing JSON, with backup and upload history
- Recipient management for email and phone numbers
- Lead storage and notification delivery logs
- SQLite by default, configurable with `DATABASE_URL`

## Local run
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```
Open `http://127.0.0.1:8000`. Engine D-Carb is also available at
`http://127.0.0.1:8000/engine-d-carb`. Admin and employee login is at `/admin/login`.

The first start creates the admin from `ADMIN_EMAIL` and `ADMIN_PASSWORD`.
Admins land on `/admin`; employees land on `/portal`. Set `ENGINE_DCARB_DOMAIN`
to the Engine D-Carb hostname when both DNS names point to the same deployment.
That hostname serves Engine D-Carb at `/`, while every other hostname serves
BatteryWala. `BATTERYWALA_DOMAIN` documents the paired BatteryWala hostname.
Email is sent when SMTP values are configured. SMS is sent by POSTing JSON to `SMS_WEBHOOK_URL` when configured. Without providers, the lead and delivery attempt are still saved.

## Test
```bash
pytest -q
```

## Automatic quotations

Battery recommendations use deterministic SQLite filtering only—there is no Google,
search API, or AI call. Vehicle make filters model, model filters the compatible set,
and preferred brand filters that set to Exide, Amaron, SF Sonic, Power Zone or Tata
Green. The five compact source catalogues are under `app/data/brands/`; the repeatable
conversion and source audit is in `scripts/build_battery_catalog.py`.

The application stores a minimal lead and immutable quotation snapshot so its private PDF can
be delivered. The public download control and download URL are not exposed. The
customer may send the quotation by email, mobile number (SMS link), or both, and
delivery starts only after clicking **Send quotation**.

Tentative prices are never included in the public recommendation or quotation-creation
response. They appear only in the private PDF after the customer chooses email or
mobile delivery. Prices are frozen in that saved quotation. Only exact battery-model,
verified vehicle-fitment, or exact-capacity matches are quoted; brand and Ah preferences
are respected. Catalogue customer prices must include 18% GST.
`price_without_exchange`, `discounted_price`, or `selling_price` is used, in that
order, falling back to MRP if no customer selling price is provided. Dealer cost
is never exposed as the customer price. Exchange quotes use `price_with_exchange`
or deduct the record's `exchange_value` from the regular customer price. Missing
matches or exchange values produce a PDF explicitly marked for price confirmation.
The customer form is driven by `app/data/form_schemas.json`, with separate question
sets for each new-battery and restoration application.

Admin PDF/image uploads run text extraction or OCR immediately. Retail records are
upserted by brand and battery model; scrap records are upserted by application and
capacity. A matching record is replaced with the newly extracted values while new
brands/models are added without deleting unrelated catalogue data.

Example verified catalogue record (illustrative, not installed as live pricing):

```json
{"source_type":"retail","brand":"Exide","model_no":"35B20L","vehicle_model":"Alto","capacity_ah":35,"mrp":5096,"selling_price":3500,"exchange_value":500,"warranty":"24+12 months"}
```

Email uses the existing `SMTP_*` settings and attaches the PDF. SMS posts the
existing `{ "to": "...", "message": "..." } payload to `SMS_WEBHOOK_URL`; set
`PUBLIC_BASE_URL` to the deployed HTTPS origin so the PDF link works on a phone.
Without providers, the UI explicitly reports that delivery is not configured
(nothing is falsely reported as sent or queued).
PDF links contain a random access token: treat them as private share links.
Delivery attempts are logged in the existing `Delivery` table. Consented form data,
linked BatteryWala leads, and linked delivery records are removed after 24 months.
The original `/api/predict` endpoint remains available and now requires consent.
