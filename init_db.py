from app import app, db
from models import (
    Owner, Pet, Veterinarian, Appointment,
    MedicalRecord, Medicine, Bill
)
with app.app_context():
    db.create_all()
    print("数据库表已创建！")