import json,os,re
from pathlib import Path
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from dotenv import load_dotenv

db=SQLAlchemy(); login=LoginManager()
def create_app(test_config=None):
 load_dotenv()
 app=Flask(__name__)
 app.config.update(SECRET_KEY=os.getenv('SECRET_KEY','dev-change-me'),SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL','sqlite:///batterywala.db'),SQLALCHEMY_TRACK_MODIFICATIONS=False,MAX_CONTENT_LENGTH=int(os.getenv('MAX_UPLOAD_MB','25'))*1024*1024)
 if test_config: app.config.update(test_config)
 db.init_app(app); login.init_app(app); login.login_view='main.login'
 from .models import User
 @login.user_loader
 def load_user(uid): return db.session.get(User,int(uid))
 from .routes import bp
 app.register_blueprint(bp)
 from .quotations import bp as quotations_bp
 app.register_blueprint(quotations_bp)
 from .portal import bp as portal_bp
 app.register_blueprint(portal_bp)
 with app.app_context():
  db.create_all(); ensure_admin(app); ensure_battery_catalog(force=True)
  from .portal import purge_expired_submissions
  from .portal import ensure_engine_centres
  ensure_engine_centres()
  purge_expired_submissions()
 return app

def ensure_admin(app):
 from .models import User
 from werkzeug.security import generate_password_hash
 email=os.getenv('ADMIN_EMAIL','admin@batterywala.local').lower()
 if not User.query.filter_by(email=email).first():
  db.session.add(User(email=email,password_hash=generate_password_hash(os.getenv('ADMIN_PASSWORD','ChangeMe123!')),is_admin=True)); db.session.commit()

def ensure_battery_catalog(force=False):
 from .models import BatteryFitment,BatteryProduct
 paths=sorted((Path(__file__).resolve().parent/'data'/'brands').glob('*.json'))
 payloads=[json.loads(path.read_text(encoding='utf-8')) for path in paths]
 expected_fitments=sum(len(data.get('fitments',[])) for data in payloads)
 expected_products=sum(len(data.get('products',[])) for data in payloads)
 if not force and BatteryFitment.query.count()==expected_fitments and BatteryProduct.query.count()==expected_products:return
 BatteryFitment.query.delete();BatteryProduct.query.delete()
 def key(value):
  value=re.sub(r'[^a-z0-9]+',' ',str(value or '').lower()).strip()
  return {'maruti suzuki india ltd46':'maruti suzuki','renault india pvt ltd46':'renault'}.get(value,value)
 fitments=[];products=[]
 for data in payloads:
  brand=data['brand']
  for item in data.get('fitments',[]):
   fitments.append({'application':item['application'],'vehicle_make':item['vehicle_make'],'make_key':key(item['vehicle_make']),
    'vehicle_model':item['vehicle_model'],'model_key':key(item['vehicle_model']),'fuel_type':item.get('fuel_type'),
    'fuel_key':key(item.get('fuel_type')),'brand':brand,'brand_key':key(brand),
    'model_no':item['model_no'],'capacity_ah':item.get('capacity_ah')})
  for item in data.get('products',[]):
   products.append({'brand':brand,'brand_key':key(brand),'application':item.get('application','vehicle'),
    'model_no':item['model_no'],'model_key':key(item['model_no']),'capacity_ah':item.get('capacity_ah'),
    'voltage':item.get('voltage'),'warranty':item.get('warranty'),'tentative_price':item.get('tentative_price'),
    'price_as_of':item.get('price_as_of'),'source_url':item.get('source_url')})
 if fitments:db.session.bulk_insert_mappings(BatteryFitment,fitments)
 if products:db.session.bulk_insert_mappings(BatteryProduct,products)
 db.session.commit()
