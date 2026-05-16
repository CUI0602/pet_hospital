from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
db = SQLAlchemy()

class Owner(db.Model):
    __tablename__ = 'owners'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.now)
    pets = db.relationship('Pet', backref='owner', lazy=True)

class Pet(db.Model):
    __tablename__ = 'pets'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    species = db.Column(db.String(30), nullable=False)
    breed = db.Column(db.String(50))
    age = db.Column(db.Integer)
    weight = db.Column(db.Float)
    allergies = db.Column(db.Text)
    gender = db.Column(db.String(10))
    owner_id = db.Column(db.Integer, db.ForeignKey('owners.id'), nullable=False)
    medical_records = db.relationship('MedicalRecord', backref='pet', lazy=True)
    appointments = db.relationship('Appointment', backref='pet', lazy=True)

    __table_args__ = (
        db.Index('idx_pet_owner', 'owner_id'),
        db.Index('idx_pet_name', 'name'),
    )


class Veterinarian(db.Model):
    __tablename__ = 'veterinarians'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    specialty = db.Column(db.String(100))
    age = db.Column(db.Integer)


class Appointment(db.Model):
    __tablename__ = 'appointments'

    id = db.Column(db.Integer, primary_key=True)
    pet_id = db.Column(db.Integer, db.ForeignKey('pets.id'), nullable=False)
    vet_id = db.Column(db.Integer, db.ForeignKey('veterinarians.id'), nullable=False)
    appointment_time = db.Column(db.DateTime, nullable=False)
    service_type = db.Column(db.String(50))
    reason = db.Column(db.String(200))
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.now)

    __table_args__ = (
        db.Index('idx_appointment_pet', 'pet_id'),
        db.Index('idx_appointment_vet', 'vet_id'),
        db.Index('idx_appointment_time', 'appointment_time'),
    )


class MedicalRecord(db.Model): #病例
    __tablename__ = 'medical_records'

    id = db.Column(db.Integer, primary_key=True)
    diagnosis = db.Column(db.Text, nullable=False)
    treatment = db.Column(db.Text)
    pet_id = db.Column(db.Integer, db.ForeignKey('pets.id'), nullable=False)
    vet_id = db.Column(db.Integer, db.ForeignKey('veterinarians.id'))
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'))
    record_date = db.Column(db.DateTime, default=datetime.now)
    registration_fee = db.Column(db.Float, default=0.0) #挂号费
    treatment_fee = db.Column(db.Float, default=0.0)   #诊疗费
    total_fee = db.Column(db.Float, default=0.0)   #总费用
    version = db.Column(db.Integer, default=1)     #乐观锁
    medicines = db.relationship('MedicalRecordMedicine', backref='medical_record', lazy=True, cascade='all, delete-orphan')

    __table_args__ = (
        db.Index('idx_record_pet', 'pet_id'),
        db.Index('idx_record_vet', 'vet_id'),
        db.Index('idx_record_date', 'record_date'),
    )


class MedicalRecordMedicine(db.Model):
    __tablename__ = 'medical_record_medicines'

    id = db.Column(db.Integer, primary_key=True)
    medical_record_id = db.Column(db.Integer, db.ForeignKey('medical_records.id'), nullable=False)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicine.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    medicine = db.relationship('Medicine', backref='prescriptions')


class Medicine(db.Model):
    __tablename__ = 'medicine'

    id = db.Column(db.Integer, primary_key=True)
    medicine_name = db.Column(db.String(100))
    stock_quantity = db.Column(db.Integer, default=0)
    price = db.Column(db.Float)
    expiry_date = db.Column(db.Date) #有效期
    category = db.Column(db.String(100)) #类别


class Bill(db.Model): #账单
    __tablename__ = 'bills'

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('owners.id'), nullable=False)
    registration_fee = db.Column(db.Float, default=0.0)  # 挂号费
    treatment_fee = db.Column(db.Float, default=0.0)  # 诊疗费
    medicine_fee = db.Column(db.Float, default=0.0)  # 药品费
    total_fee = db.Column(db.Float, default=0.0)  # 总费用
    status = db.Column(db.String(20), default='unpaid')  # 状态：unpaid 或 paid
    pay_time = db.Column(db.DateTime)
    medical_record_id = db.Column(db.Integer, db.ForeignKey('medical_records.id'))
    owner = db.relationship('Owner', backref='bills')

    __table_args__ = (
        db.Index('idx_bill_owner', 'owner_id'),
        db.Index('idx_bill_status', 'status'),
    )


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='receptionist')  # admin, doctor, pharmacist, receptionist












