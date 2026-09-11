from datetime import datetime, timezone
from flask_login import UserMixin
from . import db
class User(UserMixin,db.Model):
 id=db.Column(db.Integer,primary_key=True); email=db.Column(db.String(255),unique=True,nullable=False); password_hash=db.Column(db.String(255),nullable=False); is_admin=db.Column(db.Boolean,default=False)
 @property
 def role(self):return 'admin' if self.is_admin else 'employee'
class Recipient(db.Model):
 id=db.Column(db.Integer,primary_key=True); kind=db.Column(db.String(10),nullable=False); value=db.Column(db.String(255),nullable=False); active=db.Column(db.Boolean,default=True); created_at=db.Column(db.DateTime,default=lambda:datetime.now(timezone.utc))
class Lead(db.Model):
 id=db.Column(db.Integer,primary_key=True); name=db.Column(db.String(120)); email=db.Column(db.String(255)); phone=db.Column(db.String(40)); form_json=db.Column(db.Text); result_json=db.Column(db.Text); created_at=db.Column(db.DateTime,default=lambda:datetime.now(timezone.utc))
class Submission(db.Model):
 id=db.Column(db.Integer,primary_key=True)
 site=db.Column(db.String(30),nullable=False,index=True)
 form_kind=db.Column(db.String(40),nullable=False,index=True)
 name=db.Column(db.String(120));email=db.Column(db.String(255));phone=db.Column(db.String(40))
 form_json=db.Column(db.Text,nullable=False);result_json=db.Column(db.Text)
 consented=db.Column(db.Boolean,nullable=False,default=False,index=True)
 consent_version=db.Column(db.String(30),nullable=False,default='2026-09')
 submitted_by_id=db.Column(db.Integer,db.ForeignKey('user.id'),index=True)
 lead_id=db.Column(db.Integer,index=True)
 created_at=db.Column(db.DateTime,default=lambda:datetime.now(timezone.utc),nullable=False,index=True)
 expires_at=db.Column(db.DateTime,nullable=False,index=True)
 submitted_by=db.relationship('User',foreign_keys=[submitted_by_id])
class Upload(db.Model):
 id=db.Column(db.Integer,primary_key=True); filename=db.Column(db.String(255)); sha256=db.Column(db.String(64)); record_count=db.Column(db.Integer); status=db.Column(db.String(30)); created_at=db.Column(db.DateTime,default=lambda:datetime.now(timezone.utc))
class Delivery(db.Model):
 id=db.Column(db.Integer,primary_key=True); lead_id=db.Column(db.Integer); channel=db.Column(db.String(20)); target=db.Column(db.String(255)); status=db.Column(db.String(30)); detail=db.Column(db.Text); created_at=db.Column(db.DateTime,default=lambda:datetime.now(timezone.utc))
class EngineCentre(db.Model):
 id=db.Column(db.Integer,primary_key=True)
 key=db.Column(db.String(40),unique=True,nullable=False,index=True)
 name=db.Column(db.String(120),nullable=False)
 address=db.Column(db.String(500),nullable=False)
 sort_order=db.Column(db.Integer,nullable=False,default=0)
 contacts=db.relationship('EngineCentreContact',back_populates='centre',cascade='all, delete-orphan',order_by='EngineCentreContact.id')
class EngineCentreContact(db.Model):
 id=db.Column(db.Integer,primary_key=True)
 centre_id=db.Column(db.Integer,db.ForeignKey('engine_centre.id'),nullable=False,index=True)
 contact_name=db.Column(db.String(120),nullable=False,default='Centre contact')
 phone=db.Column(db.String(10),nullable=False)
 centre=db.relationship('EngineCentre',back_populates='contacts')
 __table_args__=(db.UniqueConstraint('centre_id','phone',name='uq_engine_centre_phone'),)
class BatteryFitment(db.Model):
 id=db.Column(db.Integer,primary_key=True)
 application=db.Column(db.String(40),nullable=False,index=True)
 vehicle_make=db.Column(db.String(120),nullable=False);make_key=db.Column(db.String(120),nullable=False,index=True)
 vehicle_model=db.Column(db.String(240),nullable=False);model_key=db.Column(db.String(240),nullable=False,index=True)
 fuel_type=db.Column(db.String(40));fuel_key=db.Column(db.String(40),nullable=False,default='')
 brand=db.Column(db.String(80),nullable=False);brand_key=db.Column(db.String(80),nullable=False,index=True)
 model_no=db.Column(db.String(100),nullable=False);capacity_ah=db.Column(db.Float)
 __table_args__=(db.Index('ix_fitment_lookup','application','make_key','model_key','fuel_key'),)
class BatteryProduct(db.Model):
 id=db.Column(db.Integer,primary_key=True)
 brand=db.Column(db.String(80),nullable=False);brand_key=db.Column(db.String(80),nullable=False,index=True)
 application=db.Column(db.String(40),nullable=False,index=True)
 model_no=db.Column(db.String(100),nullable=False);model_key=db.Column(db.String(100),nullable=False,index=True)
 capacity_ah=db.Column(db.Float);voltage=db.Column(db.Float);warranty=db.Column(db.String(100))
 tentative_price=db.Column(db.Float);price_as_of=db.Column(db.String(20));source_url=db.Column(db.String(500))
 __table_args__=(db.UniqueConstraint('brand_key','application','model_key',name='uq_battery_product'),
                 db.Index('ix_product_lookup','application','brand_key','capacity_ah'))
