import io
import json
import re
from datetime import datetime, timedelta, timezone

from openpyxl import load_workbook
from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import Delivery, Lead, Submission, User


def make_app(tmp_path):
    return create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + str(tmp_path / 'portal.db'), 'SECRET_KEY': 'test'})


def login(client, email, password):
    page = client.get('/admin/login')
    token = re.search(b'name="csrf" value="([^"]+)', page.data).group(1).decode()
    return client.post('/admin/login', data={'csrf': token, 'email': email, 'password': password}, follow_redirects=False)


def engine_service(**changes):
    data = {'enquiryType': 'service', 'customerName': 'Engine Customer', 'servicePhone': '9876543210',
            'vehicleType': 'Car', 'vehicleBrand': 'Tata', 'vehicleModel': 'Nexon', 'passingYear': '2022',
            'fuelType': 'Diesel', 'engineCc': '1497', 'kilometres': '45000', 'area': 'Baner',
            'serviceCity': 'Pune', 'servicePin': '411045', 'consent': True}
    return data | changes


def test_consent_engine_pricing_and_retention(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    public_page = client.get('/engine-d-carb')
    assert b'Nothing is uploaded automatically' not in public_page.data
    assert b'engine-integration.js' in public_page.data
    assert client.post('/api/engine-d-carb/quotations', json=engine_service(consent=False)).status_code == 400
    response = client.post('/api/engine-d-carb/quotations', json=engine_service())
    assert response.status_code == 200
    assert response.json['indicative_cost'] == 2058
    with app.app_context():
        item = Submission.query.one()
        assert item.site == 'engine_dcarb' and item.submitted_by_id is None
        assert 729 <= (item.expires_at.replace(tzinfo=timezone.utc) - item.created_at.replace(tzinfo=timezone.utc)).days <= 731


def test_admin_adds_employee_employee_machine_and_filtered_excel(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    assert login(client, 'admin@test.local', 'TestPass123!').headers['Location'].endswith('/admin')
    admin_page = client.get('/admin')
    csrf = re.search(b'name="csrf" value="([^"]+)', admin_page.data).group(1).decode()
    added = client.post('/admin/employees', data={'csrf': csrf, 'email': 'employee@example.com', 'password': 'Employee123!'}, follow_redirects=False)
    assert added.status_code == 302
    client.post('/admin/logout', data={'csrf': csrf})
    assert login(client, 'employee@example.com', 'Employee123!').headers['Location'].endswith('/portal')
    response = client.post('/api/engine-d-carb/quotations', json=engine_service(expertMachine='DCC PD10K'))
    assert response.status_code == 200 and response.json['machine'] == 'DCC PD10K'
    with app.app_context():
        item = Submission.query.one()
        assert item.submitted_by.email == 'employee@example.com'
    client.get('/admin/logout')
    client = app.test_client()
    login(client, 'admin@test.local', 'TestPass123!')
    exported = client.get('/admin/export.xlsx?site=engine_dcarb&columns=name&columns=employee&columns=result')
    assert exported.status_code == 200
    book = load_workbook(io.BytesIO(exported.data))
    sheet = book.active
    assert sheet.title == 'Engine D-Carb'
    assert [cell.value for cell in sheet[1]] == ['Customer name', 'Submitted by', 'Quotation result']
    assert sheet.cell(2, 1).value == 'Engine Customer' and sheet.cell(2, 2).value == 'employee@example.com'


def test_expiry_purges_linked_customer_and_delivery_data(tmp_path):
    app = make_app(tmp_path)
    with app.app_context():
        lead = Lead(name='Expired Customer', phone='9000000000', form_json='{}', result_json='{}')
        db.session.add(lead); db.session.flush()
        db.session.add(Delivery(lead_id=lead.id, channel='sms', target='9000000000', status='sent'))
        db.session.add(Submission(site='batterywala', form_kind='quotation', name=lead.name, phone=lead.phone,
                                  form_json='{}', result_json='{}', consented=True, consent_version='test',
                                  lead_id=lead.id, expires_at=datetime.now(timezone.utc) - timedelta(days=1)))
        db.session.commit()
        from app.portal import purge_expired_submissions
        assert purge_expired_submissions() == 1
        assert Lead.query.count() == Delivery.query.count() == Submission.query.count() == 0
