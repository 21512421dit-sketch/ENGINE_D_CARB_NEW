import json,hashlib,os,re,tempfile
from pathlib import Path
from flask import Blueprint,render_template,request,jsonify,redirect,url_for,flash,session,Response
from flask_login import login_user,logout_user,login_required,current_user
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from . import db
from .models import User,Recipient,Lead,Upload,Delivery,BatteryFitment,BatteryProduct,EngineCentre
from .services import ALLOWED_BRANDS,predict,public_result,extract_document,publish,load_data,load_form_schemas,validate_form,notify,norm,fitment_application
bp=Blueprint('main',__name__)
def csrf():
 import secrets
 if 'csrf' not in session:session['csrf']=secrets.token_urlsafe(24)
 return session['csrf']
def valid_csrf(): return request.form.get('csrf')==session.get('csrf')
def admin_required(fn):
 from functools import wraps
 @wraps(fn)
 @login_required
 def inner(*a,**k):
  if not current_user.is_admin:return ('Forbidden',403)
  return fn(*a,**k)
 return inner
@bp.app_context_processor
def inject(): return {'csrf_token':csrf()}
@bp.get('/')
def index():
 engine_domain=os.getenv('ENGINE_DCARB_DOMAIN','').split(':')[0].lower()
 if engine_domain and request.host.split(':')[0].lower()==engine_domain:
  from .portal import engine_site_response
  return engine_site_response()
 path=Path(__file__).resolve().parent.parent/'docs'/'optimized_main_prototype.html'
 html=path.read_text(encoding='utf-8')
 html=html.replace('© 2026 BatteryWala. Market-ready concept prototype.','© 2026 BatteryWala. Made by MANOZ TECH.')
 head='''<link rel="icon" href="/static/images/batterywala-logo-original.png"><link rel="stylesheet" href="/static/site-updates.css"><script>try{sessionStorage.setItem('bwRestoreSeen','1')}catch(e){}</script></head>'''
 body='''<script src="/static/site-updates.js"></script><script src="/static/quotation.js"></script></body>'''
 return Response(html.replace('</head>',head).replace('</body>',body),mimetype='text/html')
@bp.post('/api/predict')
def api_predict():
 form=dict(request.get_json(silent=True) or request.form.to_dict())
 consented=form.get('consent') is True or str(form.get('consent','')).lower()=='true'
 if not consented:return jsonify({'error':'Consent is required before we can store your details and prepare the recommendation.'}),400
 employee=current_user.is_authenticated and not current_user.is_admin
 if employee:
  form['brand']=form.get('expert_battery_brand') or form.get('brand','')
  form['model_no']=form.get('expert_battery_model') or form.get('model_no','')
 else:
  form.pop('expert_battery_brand',None);form.pop('expert_battery_model',None);form.pop('brand',None)
 form['application']=form.get('application') or form.get('battery_type','')
 form['vehicle_model']=form.get('vehicle_model') or form.get('car_model') or form.get('model_no') or form.get('vehicle_brand') or form.get('battery_type','')
 missing=validate_form(form) if form.get('application_key') else [x for x in ('name','phone','application') if not str(form.get(x,'')).strip()]
 if missing:return jsonify({'error':'Missing required fields','fields':missing}),400
 result=predict(form)
 lead=Lead(name=form.get('name'),email=form.get('email'),phone=form.get('phone'),form_json=json.dumps(form),result_json=json.dumps(result));db.session.add(lead);db.session.flush()
 from .portal import record_submission
 record_submission('batterywala','recommendation',form,result,lead.id,consented=True);db.session.commit();notify(lead,form,result,Recipient.query.all(),include_customer=False);return jsonify(public_result(result))
@bp.get('/api/pricing')
@admin_required
def pricing(): return jsonify(load_data())
@bp.get('/api/form-schemas')
def form_schemas(): return jsonify(load_form_schemas())
def display_options(rows,value_field,key_field):
 grouped={}
 for row in rows:
  value=getattr(row,value_field);key=getattr(row,key_field)
  current=grouped.get(key)
  if current is None or (current.isupper() and not value.isupper()) or len(value)<len(current):grouped[key]=value
 return sorted(grouped.values(),key=str.casefold)
@bp.get('/api/fitment-options')
def fitment_options():
 field=request.args.get('field','');application=fitment_application(request.args.get('application'))
 if field not in ('makes','models','brands') or not application:return jsonify(error='Invalid fitment option request.'),400
 if any(len(request.args.get(key,''))>240 for key in ('application','make','model','fuel')):return jsonify(error='Fitment option is too long.'),400
 query=BatteryFitment.query.filter_by(application=application)
 if field in ('models','brands'):
  make=norm(request.args.get('make'))
  if not make:return jsonify(options=[])
  query=query.filter_by(make_key=make)
 if field=='brands':
  model=norm(request.args.get('model'))
  if not model:return jsonify(options=[])
  rows=query.filter_by(model_key=model).all();fuel=norm(request.args.get('fuel'))
  if fuel:
   rows=[row for row in rows if row.fuel_key in (fuel,'')]
  values=display_options(rows,'brand','brand_key')
  capacities={row.capacity_ah for row in rows if row.capacity_ah is not None}
  if capacities:
   equivalent={row.brand_key for row in BatteryProduct.query.filter(BatteryProduct.capacity_ah.in_(capacities),
    BatteryProduct.application.in_((application,'vehicle'))).all()}
   values=[name for name in ALLOWED_BRANDS if norm(name) in equivalent or norm(name) in {norm(value) for value in values}]
 elif field=='models':values=display_options(query.all(),'vehicle_model','model_key')
 else:values=display_options(query.all(),'vehicle_make','make_key')
 return jsonify(options=values)
@bp.route('/admin/login',methods=['GET','POST'])
def login():
 if request.method=='POST':
  if not valid_csrf():return ('Invalid CSRF',400)
  u=User.query.filter_by(email=request.form['email'].lower()).first()
  if u and check_password_hash(u.password_hash,request.form['password']):
   login_user(u);return redirect(url_for('main.admin') if u.is_admin else url_for('portal.workspace'))
  flash('Invalid email or password','error')
 return render_template('login.html')
@bp.post('/admin/logout')
@login_required
def logout():
 if not valid_csrf():return ('Invalid CSRF',400)
 logout_user();return redirect(url_for('main.login'))
@bp.get('/admin')
@admin_required
def admin():
 from .models import Submission
 from .portal import SITES,filtered_submissions,purge_expired_submissions,submission_dict
 purge_expired_submissions();site,query=filtered_submissions(request.args)
 return render_template('admin.html',site=site,sites=SITES,submissions=[submission_dict(item) for item in query.limit(100).all()],
 submission_total=query.count(),site_totals={key:Submission.query.filter_by(site=key,consented=True).count() for key in SITES},
  employees=User.query.filter_by(is_admin=False).order_by(User.email).all(),recipients=Recipient.query.order_by(Recipient.id.desc()).all(),
  engine_centres=EngineCentre.query.order_by(EngineCentre.sort_order,EngineCentre.id).all(),
  uploads=Upload.query.order_by(Upload.id.desc()).limit(20),records=len(load_data().get('records',[])))
@bp.post('/admin/upload')
@admin_required
def upload():
 if not valid_csrf():return ('Invalid CSRF',400)
 f=request.files.get('file'); kind='retail'
 allowed={'.pdf','.png','.jpg','.jpeg','.webp','.tif','.tiff'}
 name=secure_filename(f.filename) if f else '';suffix=Path(name).suffix.lower()
 if not f or suffix not in allowed:flash('Upload a PDF or image file','error');return redirect(url_for('main.admin'))
 handle=tempfile.NamedTemporaryFile(suffix=suffix,delete=False);dst=Path(handle.name);handle.close();f.save(dst)
 try:
  payload=extract_document(dst,kind)
  for record in payload['records']:record['source']=name
  stats=publish(payload);sha=hashlib.sha256(dst.read_bytes()).hexdigest();db.session.add(Upload(filename=name,sha256=sha,record_count=len(payload['records']),status='published'));db.session.commit();flash(f"Published {len(payload['records'])} records: {stats['added']} new, {stats['updated']} updated.",'ok')
 except Exception as e: flash('Extraction failed: '+str(e),'error')
 finally: dst.unlink(missing_ok=True)
 return redirect(url_for('main.admin'))
@bp.post('/admin/recipients')
@admin_required
def add_recipient():
 if not valid_csrf():return ('Invalid CSRF',400)
 kind=request.form.get('kind'); value=request.form.get('value','').strip()
 if kind not in ('email','sms') or not value: flash('Invalid recipient','error')
 else: db.session.add(Recipient(kind=kind,value=value));db.session.commit();flash('Recipient added','ok')
 return redirect(url_for('main.admin'))
@bp.post('/admin/recipients/<int:rid>/delete')
@admin_required
def del_recipient(rid):
 if not valid_csrf():return ('Invalid CSRF',400)
 r=db.session.get(Recipient,rid)
 if r:db.session.delete(r);db.session.commit()
 return redirect(url_for('main.admin'))
