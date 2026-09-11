import re,json,os,smtplib,urllib.request
from pathlib import Path
from email.message import EmailMessage
from datetime import datetime,timezone
from . import db
from .models import Delivery
BASE=Path(__file__).resolve().parent
CATALOGS=BASE/'data/brands'
SCHEMAS=BASE/'data/form_schemas.json'
def norm(v):
 value=re.sub(r'[^a-z0-9]+',' ',str(v or '').lower()).strip()
 return {'maruti suzuki india ltd46':'maruti suzuki','renault india pvt ltd46':'renault'}.get(value,value)
def num(v):
 try:return float(str(v).replace(',',''))
 except:return None
def load_data():
 records=[]; sources=[]
 for path in sorted(CATALOGS.glob('*.json')) if CATALOGS.exists() else []:
  payload=json.loads(path.read_text(encoding='utf-8'));brand=payload['brand']
  for product in payload.get('products',[]):
   record={'source_type':'retail','brand':brand,**product}
   if product.get('tentative_price') is not None:record['mrp']=product['tentative_price']
   records.append(record)
  sources.append(path.name)
 return {'schema_version':'3.0','records':records,'catalogs':sources}
VEHICLE_APPLICATIONS=(('three_wheeler','Three Wheeler'),('four_wheeler','Four Wheeler'),
 ('commercial_vehicle','Commercial Vehicle'),('bus','Bus'),('truck','Truck'),('tractor','Tractor'),
 ('earth_mover','Earth Mover'))
def load_form_schemas():
 data=json.loads(SCHEMAS.read_text(encoding='utf-8'));applications=data['new']['applications'];expanded={}
 for key,schema in applications.items():
  if key!='vehicle':expanded[key]=schema;continue
  fields=[field for field in schema['fields'] if field['name']!='vehicle_type']
  for vehicle_key,label in VEHICLE_APPLICATIONS:expanded[vehicle_key]={**schema,'label':label,'fields':fields}
 data['new']['applications']=expanded
 return data
def validate_form(form):
 mode=form.get('solution_type','new'); application=form.get('application_key')
 schema=load_form_schemas().get(mode,{}).get('applications',{}).get(application)
 if not schema:return ['solution_type','application_key']
 missing=[]
 for field in schema['fields']:
  visible=all(str(form.get(k,''))==str(v) for k,v in field.get('show_when',{}).items())
  if visible and field.get('required') and not str(form.get(field['name'],'')).strip():missing.append(field['name'])
 return missing
def fitment_application(value):
 key=norm(value).replace(' ','_')
 return {'bus':'commercial_vehicle','truck':'commercial_vehicle','car_suv_muv':'four_wheeler'}.get(key,key)
ALLOWED_BRANDS=('EXIDE','AMARON','SF SONIC','POWER ZONE','TATA GREEN')
def brand_key(value):
 value=norm(value)
 return {'amron':'amaron','powerzone':'power zone','any verified brand':''}.get(value,value)
def product_record(product,fitment=None):
 return {'source_type':'catalogue','brand':product.brand,'model_no':product.model_no,
         'capacity_ah':product.capacity_ah or (fitment.capacity_ah if fitment else None),
         'voltage':product.voltage,'warranty':product.warranty,'mrp':product.tentative_price,
         'price_as_of':product.price_as_of,'source_url':product.source_url,
         'vehicle_model':fitment.vehicle_model if fitment else None}
def public_result(result):
 def safe(record):
  return {key:value for key,value in (record or {}).items()
          if key not in ('mrp','tentative_price','price','selling_price','discounted_price',
                         'price_without_exchange','price_with_exchange','exchange_value')}
 return {key:value for key,value in result.items() if key not in ('records','sources')} | {
  'prediction':safe(result.get('prediction')) if result.get('prediction') else None,
  'alternatives':[safe(row) for row in result.get('alternatives',[])]}
def predict(form):
 from .models import BatteryFitment,BatteryProduct
 application=fitment_application(form.get('application_key') or form.get('application'))
 preferred=brand_key(form.get('brand'))
 make=norm(form.get('vehicle_make'));model=norm(form.get('vehicle_model') or form.get('car_model'))
 fuel=norm(form.get('fuel_type'));rows=[];products=None
 if application and make and model:
  query=BatteryFitment.query.filter_by(application=application,make_key=make,model_key=model)
  rows=query.all()
  if fuel:
   rows=[row for row in rows if row.fuel_key in (fuel,'')]
  base_rows=rows
  if preferred:
   rows=[row for row in rows if row.brand_key==preferred]
   if not rows:
    capacities={row.capacity_ah for row in base_rows if row.capacity_ah is not None}
    if capacities:
     products=BatteryProduct.query.filter(BatteryProduct.brand_key==preferred,
       BatteryProduct.capacity_ah.in_(capacities),BatteryProduct.application.in_((application,'vehicle'))).all()
     rows=[None]*len(products)
 exact_model=norm(form.get('model_no'))
 if exact_model:
  products=BatteryProduct.query.filter_by(model_key=exact_model).all()
  if preferred:products=[row for row in products if row.brand_key==preferred]
  rows=[None]*len(products)
 elif products is None:
  products=[]
  for row in rows:
   matches=BatteryProduct.query.filter_by(brand_key=row.brand_key,model_key=norm(row.model_no)).all()
   products.append(matches[0] if matches else None)
 # Capacity-based applications and preferred-brand alternatives stay deterministic.
 requested_capacity=num(form.get('capacity_ah') or form.get('old_capacity_ah'))
 if not rows and requested_capacity is not None:
  query=BatteryProduct.query.filter_by(capacity_ah=requested_capacity)
  candidates=query.all()
  if preferred:candidates=[row for row in candidates if row.brand_key==preferred]
  if application:candidates=[row for row in candidates if row.application in (application,'vehicle')]
  products=candidates;rows=[None]*len(products)
 if products is None:products=[]
 ranked=[]
 for fitment,product in zip(rows,products):
  if product is None and fitment is not None:
   # A verified fitment may not have a price/specification row yet.
   record={'source_type':'official_fitment','brand':fitment.brand,'model_no':fitment.model_no,
           'capacity_ah':fitment.capacity_ah,'vehicle_model':fitment.vehicle_model}
  elif product is not None:record=product_record(product,fitment)
  else:continue
  ranked.append(record)
 unique={brand_key(row['brand'])+'|'+norm(row['model_no']):row for row in ranked}
 ranked=list(unique.values())
 if not ranked:
  return {'prediction':None,'alternatives':[],'confidence':'low','needs_manual_review':True,
          'message':'No verified catalogue match was found. A BatteryWala expert must confirm the fitment.',
          'records':[],'method':'sql_exact_filter'}
 order={brand_key(name):index for index,name in enumerate(ALLOWED_BRANDS)}
 ranked.sort(key=lambda row:(0 if preferred and brand_key(row['brand'])==preferred else 1,
                             order.get(brand_key(row['brand']),99),norm(row['model_no'])))
 return {'prediction':ranked[0],'alternatives':ranked[1:5],'confidence':'high' if make and model else 'medium',
         'needs_manual_review':False,'message':'Compatible battery found from the verified five-brand catalogue. Confirm dimensions and terminal orientation before installation.',
         'records':ranked,'method':'sql_exact_filter'}

def _brand(text):
 upper=text.upper()
 for token,label in (('EXIDE','EXIDE'),('AMARON','AMARON'),('AMRON','AMARON'),('POWER ZONE','POWER ZONE'),
                     ('POWERZONE','POWER ZONE'),('SF SONIC','SF SONIC'),('TATA GREEN','TATA GREEN')):
  if token in upper:return label
 return 'UNCLASSIFIED'
def _application(section):
 value=norm(section)
 if '2 wheeler' in value:return 'two_wheeler'
 if 'generator' in value:return 'generator'
 if 'inverter' in value or 'tubular' in value:return 'inverter'
 if 'ups' in value or 'smf' in value:return 'online_ups'
 if 'forklift' in value or 'traction' in value:return 'forklift_stacker'
 return 'vehicle'
def _record(source,source_type,page,brand,model=None,capacity=None,application=None,**prices):
 return {'source':source,'source_type':source_type,'page':page,'brand':brand,'model_no':model,
         'capacity_ah':capacity,'application':application,**prices}
def _parse_text(text,source,source_type,page,brand):
 records=[]; section=''
 money_re=r'\d[\d,]*(?:\.\d+)?'
 for raw in text.splitlines():
  line=re.sub(r'\s+',' ',raw).strip(); upper=line.upper()
  if not line:continue
  if any(word in upper for word in ('CAR/SUV:','2-WHEELER:','TRACTOR:','E-RICKSHAW:','AUTOMOTIVE SERIES')):section=line
  if source_type=='scrap':
   values=[float(x.replace(',','')) for x in re.findall(money_re,line)]
   if len(values)>=6:
    for offset in (0,3):
     records.append(_record(source,source_type,page,brand,capacity=values[offset],application='scrap',scrap_price=values[offset+1],unbranded_scrap_price=values[offset+2]))
   continue
  for match in re.finditer(rf'(?P<ah>\d+(?:\.\d+)?)\s+(?P<model>[A-Z0-9][A-Z0-9()./+\-]{{2,30}})\s+(?P<warranty>(?:\d{{1,2}}[A-Z](?:\+\d{{1,2}}[A-Z])?|\d{{1,2}}M FOC|NA))\s+(?P<price>{money_re})',upper):
   records.append(_record(source,source_type,page,brand,match['model'],float(match['ah']),_application(section),mrp=float(match['price'].replace(',','')),warranty=match['warranty']))
  prycal=re.search(rf'\b(PN(?:S)?\s+[A-Z0-9 /]+|DIN\s+[A-Z0-9 /]+)\s+(\d{{1,3}})\s+18\s*\+\s*18\s+36\D+({money_re})\s+({money_re})',upper)
  if prycal:records.append(_record(source,source_type,page,brand,re.sub(r'\s+',' ',prycal[1]),float(prycal[2]),'vehicle',dealer_price=float(prycal[3].replace(',','')),mrp=float(prycal[4].replace(',','')),warranty='18+18 months'))
  amaron=re.search(rf'\b((?:AAM|AMS)-[A-Z0-9-]+)\s+({money_re})\s*$',upper)
  if amaron:records.append(_record(source,source_type,page,brand,amaron[1],application='vehicle',mrp=float(amaron[2].replace(',',''))))
 return records
def extract_document(path,source_type='retail'):
 import fitz
 from PIL import Image
 import pytesseract
 path=Path(path); pages=[]
 if path.suffix.lower()=='.pdf':
  with fitz.open(path) as document:
   for page in document:
    text=page.get_text('text').strip()
    if len(re.sub(r'\s+','',text))<80:
     pix=page.get_pixmap(matrix=fitz.Matrix(2.5,2.5),alpha=False)
     text=pytesseract.image_to_string(Image.frombytes('RGB',[pix.width,pix.height],pix.samples),config='--psm 6')
    pages.append(text)
 else:
  with Image.open(path) as image:pages.append(pytesseract.image_to_string(image.convert('RGB'),config='--psm 6'))
 joined='\n'.join(pages);brand=_brand(joined);records=[]
 for page,text in enumerate(pages,1):records.extend(_parse_text(text,path.name,source_type,page,brand))
 unique={record_key(r):r for r in records if r.get('model_no') or r.get('capacity_ah') is not None}
 if not unique:raise ValueError('No battery price records could be extracted. Upload a clear table with model/capacity and price columns.')
 return {'schema_version':'2.0','generated_at':datetime.now(timezone.utc).isoformat(),'records':list(unique.values())}
extract_pdf=extract_document
def record_key(record):
 if record.get('source_type')=='scrap':return '|'.join(('scrap',norm(record.get('application')),str(num(record.get('capacity_ah')))))
 model=norm(record.get('model_no'))
 return '|'.join((norm(record.get('brand')),model or 'capacity',model or str(num(record.get('capacity_ah')))))
def _catalog_name(record):return re.sub(r'[^a-z0-9]+','-',norm(record.get('brand'))).strip('-')+'.json'
def publish(payload):
 CATALOGS.mkdir(parents=True,exist_ok=True);catalogs={}
 for path in CATALOGS.glob('*.json'):catalogs[path.name]=json.loads(path.read_text(encoding='utf-8'))
 locations={record_key({'brand':data['brand'],**record}):(name,index) for name,data in catalogs.items() for index,record in enumerate(data.get('products',[]))}
 added=updated=0
 for record in payload['records']:
  canonical=next((name for name in ALLOWED_BRANDS if brand_key(name)==brand_key(record.get('brand'))),None)
  if not canonical or record.get('source_type')=='scrap':continue
  record={'brand':canonical,'application':record.get('application') or 'vehicle','model_no':record.get('model_no'),
          'capacity_ah':record.get('capacity_ah'),'warranty':record.get('warranty'),
          'tentative_price':record.get('mrp'),'price_as_of':payload.get('generated_at'),
          'source_url':record.get('source_url') or record.get('source')}
  key=record_key(record)
  if key in locations:
   name,index=locations[key];catalogs[name]['products'][index]={k:v for k,v in record.items() if k!='brand'};updated+=1
  else:
   name=_catalog_name({'brand':canonical});data=catalogs.setdefault(name,{'schema_version':'3.0','brand':canonical,'source_urls':[],'products':[],'fitments':[]})
   locations[key]=(name,len(data['products']));data['products'].append({k:v for k,v in record.items() if k!='brand'});added+=1
 for name,data in catalogs.items():
  data['updated_at']=payload.get('generated_at');target=CATALOGS/name;tmp=target.with_suffix('.tmp')
  tmp.write_text(json.dumps(data,indent=2),encoding='utf-8');tmp.replace(target)
 from flask import has_app_context
 if has_app_context():
  from . import ensure_battery_catalog
  ensure_battery_catalog(force=True)
 return {'added':added,'updated':updated,'catalogs':len(catalogs)}
def notify(lead,form,result,recipients,include_customer=True):
 subject=f"BatteryWala recommendation for {lead.name}"; body=f"Hello {lead.name},\n\nRecommendation: {json.dumps(result,indent=2)}\n\nRequest: {json.dumps(form,indent=2)}"
 targets=[]
 if include_customer and lead.email: targets.append(('email',lead.email))
 if include_customer and lead.phone: targets.append(('sms',lead.phone))
 targets += [(r.kind,r.value) for r in recipients if r.active]
 for channel,target in targets:
  status='queued'; detail='Provider not configured'
  try:
   if channel=='email' and os.getenv('SMTP_HOST'):
    m=EmailMessage();m['Subject']=subject;m['From']=os.getenv('SMTP_FROM') or os.getenv('SMTP_USERNAME');m['To']=target;m.set_content(body)
    with smtplib.SMTP(os.getenv('SMTP_HOST'),int(os.getenv('SMTP_PORT','587')),timeout=15) as s:
     if os.getenv('SMTP_USE_TLS','true').lower()=='true':s.starttls()
     if os.getenv('SMTP_USERNAME'):s.login(os.getenv('SMTP_USERNAME'),os.getenv('SMTP_PASSWORD'))
     s.send_message(m)
    status='sent';detail='SMTP accepted'
   elif channel=='sms' and os.getenv('SMS_WEBHOOK_URL'):
    req=urllib.request.Request(os.getenv('SMS_WEBHOOK_URL'),data=json.dumps({'to':target,'message':body[:1000]}).encode(),headers={'Content-Type':'application/json'}); urllib.request.urlopen(req,timeout=15).read();status='sent';detail='Webhook accepted'
  except Exception as e: status='failed';detail=str(e)[:500]
  db.session.add(Delivery(lead_id=lead.id,channel=channel,target=target,status=status,detail=detail))
 db.session.commit()
