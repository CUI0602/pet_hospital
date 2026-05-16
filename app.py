import json
from flask import Flask, render_template, request, redirect, url_for, session, abort
from datetime import datetime, timedelta
from sqlalchemy import func
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, Owner, Pet, Veterinarian, Appointment, MedicalRecord, MedicalRecordMedicine, Medicine, Bill, User

app = Flask(__name__)
app.config.from_object('config.Config')
db.init_app(app)

app.secret_key = 'pet-hospital-secret-key'

ROLE_NAMES = {
    'admin': '管理员',
    'doctor': '医生',
    'pharmacist': '药房',
    'receptionist': '前台'
}

ROLE_MENU = {
    'admin': ['/', '/owners', '/pets', '/veterinarians', '/appointments', '/medical_records', '/medicines', '/bills', '/reports', '/users'],
    'doctor': ['/', '/pets', '/appointments', '/medical_records', '/medicines'],
    'pharmacist': ['/', '/medicines'],
    'receptionist': ['/', '/owners', '/pets', '/appointments', '/bills']
}

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get('role') not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated
    return decorator

def menu_for_role(role):
    items = []
    all_links = [
        ('/', '首页'), ('/owners', '主人'), ('/pets', '宠物'),
        ('/veterinarians', '兽医'), ('/appointments', '预约'),
        ('/medical_records', '病历'), ('/medicines', '药品'),
        ('/bills', '账单'), ('/reports', '报表'), ('/users', '用户')
    ]
    allowed = ROLE_MENU.get(role, [])
    for href, label in all_links:
        if href in allowed:
            items.append((href, label))
    return items

# 登录
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            return redirect('/')
        return render_template('login.html', error='用户名或密码错误')
    return render_template('login.html')

# 登出
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# 用户管理（仅管理员）
@app.route('/users')
@login_required
@role_required('admin')
def show_users():
    users = User.query.all()
    return render_template('users.html', users=users, ROLE_NAMES=ROLE_NAMES)

@app.route('/users/add', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_user():
    if request.method == 'POST':
        new_user = User(
            username=request.form['username'],
            password=generate_password_hash(request.form['password']),
            role=request.form['role']
        )
        db.session.add(new_user)
        db.session.commit()
        return redirect('/users')
    return render_template('add_user.html', ROLE_NAMES=ROLE_NAMES)

@app.route('/users/delete/<int:id>')
@login_required
@role_required('admin')
def delete_user(id):
    user = User.query.get(id)
    if user and user.id != session['user_id']:
        db.session.delete(user)
        db.session.commit()
    return redirect('/users')

# 403 页面
@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403

# 全局模板变量
@app.context_processor
def inject_user():
    return dict(
        session=session,
        ROLE_NAMES=ROLE_NAMES,
        menu_items=menu_for_role(session.get('role'))
    )

# 首页
@app.route('/')
@login_required
def index():
    return render_template('index.html')

# 显示主人列表
@app.route('/owners')
@login_required
def show_owners():
    owners = Owner.query.all()
    return render_template('owners.html', owners=owners)


# 处理添加主人功能
@app.route('/owners/add', methods=['GET', 'POST'])
@login_required
def add_owner():
    # 如果用户点击了“保存” (POST 请求)
    if request.method == 'POST':
        # 1. 获取网页传来的数据
        name = request.form.get('name')
        phone = request.form.get('phone')
        address = request.form.get('address')

        # 2. 创建一个新的主人对象
        new_owner = Owner(name=name, phone=phone, address=address)

        # 3. 保存到数据库
        db.session.add(new_owner)
        db.session.commit()

        # 4. 添加成功后，自动跳回列表页
        return redirect('/owners')

    # 如果用户只是刚点进来 (GET 请求)，显示空白表单
    return render_template('add_owner.html')

# 3. 修改主人功能
@app.route('/owners/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_owner(id):
    owner = Owner.query.get(id)
    if request.method == 'POST':
        owner.name = request.form['name']
        owner.phone = request.form['phone']
        owner.address = request.form['address']
        db.session.commit()
        return redirect('/owners')
    return render_template('edit_owner.html', owner=owner)

# 4. 删除主人功能
@app.route('/owners/delete/<int:id>')
@login_required
def delete_owner(id):
    # 找到这个主人
    owner = Owner.query.get(id)
    # 执行删除
    db.session.delete(owner)
    # 提交事务（保存更改）
    db.session.commit()
    # 回到列表页
    return redirect('/owners')

# 5. 宠物列表 (新写的)
@app.route('/pets')
@login_required
def show_pets():
    # 查询所有宠物
    pets = Pet.query.all()
    # 发送给 pets.html 显示
    return render_template('pets.html', pets=pets)


# 3. 新增宠物
@app.route('/pets/add', methods=['GET', 'POST'])
@login_required
def add_pet():
    # 如果是 POST，说明用户点击了“保存”
    if request.method == 'POST':
        # 获取表单里填的数据，注意名字要和 HTML 里的 name 属性对应
        new_pet = Pet(
            name=request.form['name'],
            species=request.form['species'],
            gender=request.form.get('gender'),
            weight=request.form.get('weight') or None,
            allergies=request.form.get('allergies'),
            age=request.form['age'],
            owner_id=request.form['owner_id']
        )

        db.session.add(new_pet)
        db.session.commit()

        return redirect('/pets')  # 成功后跳回列表
    # 如果是 GET，说明用户刚打开这个页面
    # 我们需要查所有主人，把数据传给 HTML 的下拉菜单
    owners = Owner.query.all()
    return render_template('add_pet.html', owners=owners)


# 4. 修改宠物
@app.route('/pets/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_pet(id):
    # 根据 ID 找到宠物
    pet = Pet.query.get(id)
    if request.method == 'POST':
        # 获取新数据并更新
        pet.name = request.form['name']
        pet.species = request.form['species']
        pet.gender = request.form.get('gender')
        pet.weight = request.form.get('weight') or None
        pet.allergies = request.form.get('allergies')
        pet.age = request.form['age']
        pet.owner_id = request.form['owner_id']

        db.session.commit()
        return redirect('/pets')
    # 如果是 GET 请求，需要显示页面
    # 必须查询所有主人 (owners) 以便下拉菜单显示
    owners = Owner.query.all()
    return render_template('edit_pet.html', pet=pet, owners=owners)

#添加兽医
@app.route('/veterinarians')
@login_required
@role_required('admin')
def show_veterinarians():
    veterinarians = Veterinarian.query.all()
    return render_template('veterinarians.html', veterinarians=veterinarians)

@app.route('/veterinarians/add', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_veterinarian():
    if request.method == 'POST':
        name = request.form['name']
        title = request.form['title']
        phone = request.form['phone']
        specialty = request.form['specialty']
        age = request.form['age']
        new_vet = Veterinarian(
            name=name, title=title,
            phone=phone, specialty=specialty,
            age=age
        )
        db.session.add(new_vet)
        db.session.commit()
        return redirect('/veterinarians')
    return render_template('add_veterinarian.html')

# 编辑兽医
@app.route('/veterinarians/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_veterinarian(id):
    vet = Veterinarian.query.get(id)
    if request.method == 'POST':
        vet.name = request.form['name']
        vet.title = request.form['title']
        vet.phone = request.form['phone']
        vet.specialty = request.form['specialty']
        vet.age = request.form['age']
        db.session.commit()
        return redirect('/veterinarians')
    return render_template('edit_veterinarian.html', veterinarian=vet)

# 删除兽医
@app.route('/veterinarians/delete/<int:id>')
@login_required
@role_required('admin')
def delete_veterinarian(id):
    vet = Veterinarian.query.get(id)
    db.session.delete(vet)
    db.session.commit()
    return redirect('/veterinarians')

# 预约列表
@app.route('/appointments')
@login_required
def show_appointments():
    appointments = Appointment.query.all()
    return render_template('appointments.html', appointments=appointments)

# 新增预约
@app.route('/appointments/add', methods=['GET', 'POST'])
@login_required
def add_appointment():
    if request.method == 'POST':
        date_str = f"{request.form['year']}-{request.form['month']}-{request.form['day']}"
        appointment_time = datetime.strptime(date_str, '%Y-%m-%d')
        new_appointment = Appointment(
            pet_id=request.form['pet_id'],
            vet_id=request.form['vet_id'],
            appointment_time=appointment_time,
            service_type=request.form.get('service_type'),
            reason=request.form['reason'],
            status=request.form['status']
        )
        db.session.add(new_appointment)
        db.session.commit()
        return redirect('/appointments')
    pets = Pet.query.all()
    veterinarians = Veterinarian.query.all()
    return render_template('add_appointment.html', pets=pets, veterinarians=veterinarians)
# 编辑预约
@app.route('/appointments/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_appointment(id):
    appointment = Appointment.query.get(id)
    if request.method == 'POST':
        appointment.pet_id = request.form['pet_id']
        appointment.vet_id = request.form['vet_id']
        date_str = f"{request.form['year']}-{request.form['month']}-{request.form['day']}"
        appointment.appointment_time = datetime.strptime(date_str, '%Y-%m-%d')
        appointment.service_type = request.form.get('service_type')
        appointment.reason = request.form['reason']
        appointment.status = request.form['status']
        db.session.commit()
        return redirect('/appointments')
    pets = Pet.query.all()
    veterinarians = Veterinarian.query.all()
    return render_template('edit_appointment.html', appointment=appointment, pets=pets, veterinarians=veterinarians)
# 删除预约
@app.route('/appointments/delete/<int:id>')
@login_required
def delete_appointment(id):
    appointment = Appointment.query.get(id)
    db.session.delete(appointment)
    db.session.commit()
    return redirect('/appointments')

# 病历列表
@app.route('/medical_records')
@login_required
def show_medical_records():
    records = MedicalRecord.query.all()
    return render_template('medical_records.html', records=records)
# 新增病历
@app.route('/medical_records/add', methods=['GET', 'POST'])
@login_required
def add_medical_record():
    if request.method == 'POST':
        reg_fee = float(request.form['registration_fee'] or 0)
        treat_fee = float(request.form['treatment_fee'] or 0)
        date_str = f"{request.form['year']}-{request.form['month']}-{request.form['day']}"
        vet_id = request.form.get('vet_id')

        medicine_ids = request.form.getlist('medicine_ids[]')
        quantities = request.form.getlist('quantities[]')
        medicines_json = []
        for mid, qty in zip(medicine_ids, quantities):
            if mid and int(qty) > 0:
                medicines_json.append({"medicine_id": int(mid), "quantity": int(qty)})

        db.session.execute(
            db.text("CALL sp_create_medical_record(:diagnosis, :treatment, :pet_id, :vet_id, :appointment_id, :record_date, :reg_fee, :treat_fee, :medicines)"),
            {
                "diagnosis": request.form['diagnosis'],
                "treatment": request.form['treatment'],
                "pet_id": int(request.form['pet_id']),
                "vet_id": int(vet_id) if vet_id else None,
                "appointment_id": request.form.get('appointment_id') or None,
                "record_date": date_str,
                "reg_fee": reg_fee,
                "treat_fee": treat_fee,
                "medicines": json.dumps(medicines_json)
            }
        )
        db.session.commit()
        return redirect('/medical_records')
    pets = Pet.query.all()
    veterinarians = Veterinarian.query.all()
    appointments = Appointment.query.all()
    medicines = Medicine.query.all()
    return render_template('add_medical_record.html', pets=pets, veterinarians=veterinarians, appointments=appointments, medicines=medicines)
# 编辑病历
@app.route('/medical_records/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_medical_record(id):
    record = MedicalRecord.query.get(id)
    pets = Pet.query.all()
    veterinarians = Veterinarian.query.all()
    appointments = Appointment.query.all()
    medicines = Medicine.query.all()
    if request.method == 'POST':
        reg_fee = float(request.form['registration_fee'] or 0)
        treat_fee = float(request.form['treatment_fee'] or 0)
        date_str = f"{request.form['year']}-{request.form['month']}-{request.form['day']}"
        vet_id = request.form.get('vet_id')
        if int(request.form['version']) != record.version:
            return render_template('edit_medical_record.html',
                                   record=record, pets=pets, veterinarians=veterinarians,
                                   appointments=appointments, medicines=medicines,
                                   error='该记录已被其他人修改，请刷新后重试')
        record.diagnosis = request.form['diagnosis']
        record.treatment = request.form['treatment']
        record.pet_id = request.form['pet_id']
        record.vet_id = int(vet_id) if vet_id else None
        record.appointment_id = request.form.get('appointment_id') or None
        record.record_date = datetime.strptime(date_str, '%Y-%m-%d')
        record.registration_fee = reg_fee
        record.treatment_fee = treat_fee
        record.total_fee = reg_fee + treat_fee

        MedicalRecordMedicine.query.filter_by(medical_record_id=record.id).delete()
        medicine_ids = request.form.getlist('medicine_ids[]')
        quantities = request.form.getlist('quantities[]')
        for mid, qty in zip(medicine_ids, quantities):
            if mid and int(qty) > 0:
                db.session.add(MedicalRecordMedicine(
                    medical_record_id=record.id,
                    medicine_id=int(mid),
                    quantity=int(qty)
                ))
        db.session.commit()

        medicine_total = db.session.query(
            func.coalesce(func.sum(Medicine.price * MedicalRecordMedicine.quantity), 0)
        ).join(MedicalRecordMedicine, MedicalRecordMedicine.medicine_id == Medicine.id
        ).filter(MedicalRecordMedicine.medical_record_id == record.id).scalar()
        record.total_fee = reg_fee + treat_fee + medicine_total
        record.version += 1
        db.session.commit()
        return redirect('/medical_records')
    return render_template('edit_medical_record.html', record=record, pets=pets,
                           veterinarians=veterinarians, appointments=appointments,
                           medicines=medicines, error=None)
# 删除病历
@app.route('/medical_records/delete/<int:id>')
@login_required
def delete_medical_record(id):
    record = MedicalRecord.query.get(id)
    db.session.delete(record)
    db.session.commit()
    return redirect('/medical_records')

# 药品列表
@app.route('/medicines')
@login_required
def show_medicines():
    medicines = Medicine.query.all()
    return render_template('medicines.html', medicines=medicines, now=datetime.now().date(), thirty_days=(datetime.now() + timedelta(days=30)).date())
# 新增药品
@app.route('/medicines/add', methods=['GET', 'POST'])
@login_required
def add_medicine():
    if request.method == 'POST':
        date_str = f"{request.form['year']}-{request.form['month']}-{request.form['day']}"
        new_medicine = Medicine(
            medicine_name=request.form['medicine_name'],
            stock_quantity=request.form['stock_quantity'],
            price=request.form['price'],
            expiry_date=datetime.strptime(date_str, '%Y-%m-%d'),
            category=request.form['category']
        )
        db.session.add(new_medicine)
        db.session.commit()
        return redirect('/medicines')
    return render_template('add_medicine.html')
# 编辑药品
@app.route('/medicines/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_medicine(id):
    medicine = Medicine.query.get(id)
    if request.method == 'POST':
        date_str = f"{request.form['year']}-{request.form['month']}-{request.form['day']}"
        medicine.medicine_name = request.form['medicine_name']
        medicine.stock_quantity = request.form['stock_quantity']
        medicine.price = request.form['price']
        medicine.expiry_date = datetime.strptime(date_str, '%Y-%m-%d')
        medicine.category = request.form['category']
        db.session.commit()
        return redirect('/medicines')
    return render_template('edit_medicine.html', medicine=medicine)
# 删除药品
@app.route('/medicines/delete/<int:id>')
@login_required
def delete_medicine(id):
    medicine = Medicine.query.get(id)
    db.session.delete(medicine)
    db.session.commit()
    return redirect('/medicines')


# 账单列表
@app.route('/bills')
@login_required
def show_bills():
    bills = Bill.query.all()
    return render_template('bills.html', bills=bills)
# 新增账单
@app.route('/bills/add', methods=['GET', 'POST'])
@login_required
def add_bill():
    if request.method == 'POST':
        reg_fee = float(request.form['registration_fee'] or 0)
        treat_fee = float(request.form['treatment_fee'] or 0)
        med_fee = float(request.form['medicine_fee'] or 0)
        new_bill = Bill(
            owner_id=request.form['owner_id'],
            registration_fee=reg_fee,
            treatment_fee=treat_fee,
            medicine_fee=med_fee,
            total_fee=reg_fee + treat_fee + med_fee,
            status='unpaid'
        )
        db.session.add(new_bill)
        db.session.commit()
        return redirect('/bills')
    owners = Owner.query.all()
    return render_template('add_bill.html', owners=owners)
# 切换支付状态
@app.route('/bills/toggle/<int:id>')
@login_required
def toggle_bill(id):
    bill = Bill.query.get(id)
    if bill.status == 'unpaid':
        bill.status = 'paid'
        bill.pay_time = datetime.now()
    else:
        bill.status = 'unpaid'
        bill.pay_time = None
    db.session.commit()
    return redirect('/bills')
# 删除账单
@app.route('/bills/delete/<int:id>')
@login_required
def delete_bill(id):
    bill = Bill.query.get(id)
    db.session.delete(bill)
    db.session.commit()
    return redirect('/bills')






# 统计报表
@app.route('/reports')
@login_required
@role_required('admin')
def reports():
    thirty_days = datetime.now() + timedelta(days=30)

    case_stats = db.session.query(
        MedicalRecord.diagnosis, func.count(MedicalRecord.id).label('count')
    ).group_by(MedicalRecord.diagnosis).order_by(func.count(MedicalRecord.id).desc()).limit(10).all()

    income_stats = db.session.query(
        func.date_format(Bill.pay_time, '%Y-%m').label('month'),
        func.sum(Bill.total_fee).label('total')
    ).filter(Bill.status == 'paid').group_by('month').order_by('month').all()

    expired_medicines = Medicine.query.filter(Medicine.expiry_date <= datetime.now()).all()
    expiring_medicines = Medicine.query.filter(
        Medicine.expiry_date > datetime.now(),
        Medicine.expiry_date <= thirty_days
    ).all()

    low_stock_medicines = Medicine.query.filter(Medicine.stock_quantity < 10).all()

    owner_summary = db.session.execute(db.text('SELECT * FROM owner_bill_summary ORDER BY total_spent DESC')).fetchall()
    monthly_revenue = db.session.execute(db.text('SELECT * FROM monthly_revenue ORDER BY month')).fetchall()

    return render_template('reports.html',
        case_stats=case_stats,
        income_stats=income_stats,
        expired_medicines=expired_medicines,
        expiring_medicines=expiring_medicines,
        low_stock_medicines=low_stock_medicines,
        owner_summary=owner_summary,
        monthly_revenue=monthly_revenue)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        db.session.execute(db.text('DROP VIEW IF EXISTS owner_bill_summary'))
        db.session.execute(db.text('''
            CREATE VIEW owner_bill_summary AS
            SELECT o.id AS owner_id, o.name AS owner_name,
                   COUNT(b.id) AS bill_count,
                   SUM(b.total_fee) AS total_spent,
                   SUM(CASE WHEN b.status = 'paid' THEN b.total_fee ELSE 0 END) AS paid_amount
            FROM owners o
            LEFT JOIN bills b ON o.id = b.owner_id
            GROUP BY o.id
        '''))

        db.session.execute(db.text('DROP VIEW IF EXISTS monthly_revenue'))
        db.session.execute(db.text('''
            CREATE VIEW monthly_revenue AS
            SELECT DATE_FORMAT(pay_time, '%Y-%m') AS month,
                   COUNT(id) AS bill_count,
                   SUM(total_fee) AS revenue
            FROM bills
            WHERE status = 'paid'
            GROUP BY month
        '''))

        db.session.execute(db.text('DROP TRIGGER IF EXISTS trg_after_insert_medical_record'))
        db.session.execute(db.text('''
            CREATE TRIGGER trg_after_insert_medical_record
            AFTER INSERT ON medical_records
            FOR EACH ROW
            BEGIN
                INSERT INTO bills (owner_id, registration_fee, treatment_fee, medicine_fee, total_fee, status, medical_record_id)
                SELECT p.owner_id, NEW.registration_fee, NEW.treatment_fee, 0, NEW.total_fee, 'unpaid', NEW.id
                FROM pets p WHERE p.id = NEW.pet_id;
            END;
        '''))

        db.session.execute(db.text('DROP TRIGGER IF EXISTS trg_after_insert_mrm'))
        db.session.execute(db.text('''
            CREATE TRIGGER trg_after_insert_mrm
            AFTER INSERT ON medical_record_medicines
            FOR EACH ROW
            BEGIN
                UPDATE bills
                SET medicine_fee = (
                    SELECT COALESCE(SUM(m.price * mrm.quantity), 0)
                    FROM medical_record_medicines mrm
                    JOIN medicine m ON mrm.medicine_id = m.id
                    WHERE mrm.medical_record_id = NEW.medical_record_id
                ),
                total_fee = registration_fee + treatment_fee + (
                    SELECT COALESCE(SUM(m.price * mrm.quantity), 0)
                    FROM medical_record_medicines mrm
                    JOIN medicine m ON mrm.medicine_id = m.id
                    WHERE mrm.medical_record_id = NEW.medical_record_id
                )
                WHERE medical_record_id = NEW.medical_record_id;
            END;
        '''))

        db.session.execute(db.text('DROP TRIGGER IF EXISTS trg_after_delete_mrm'))
        db.session.execute(db.text('''
            CREATE TRIGGER trg_after_delete_mrm
            AFTER DELETE ON medical_record_medicines
            FOR EACH ROW
            BEGIN
                UPDATE bills
                SET medicine_fee = (
                    SELECT COALESCE(SUM(m.price * mrm.quantity), 0)
                    FROM medical_record_medicines mrm
                    JOIN medicine m ON mrm.medicine_id = m.id
                    WHERE mrm.medical_record_id = OLD.medical_record_id
                ),
                total_fee = registration_fee + treatment_fee + (
                    SELECT COALESCE(SUM(m.price * mrm.quantity), 0)
                    FROM medical_record_medicines mrm
                    JOIN medicine m ON mrm.medicine_id = m.id
                    WHERE mrm.medical_record_id = OLD.medical_record_id
                )
                WHERE medical_record_id = OLD.medical_record_id;
            END;
        '''))

        db.session.execute(db.text('DROP PROCEDURE IF EXISTS sp_create_medical_record'))
        db.session.execute(db.text('''
            CREATE PROCEDURE sp_create_medical_record(
                p_diagnosis TEXT,
                p_treatment TEXT,
                p_pet_id INT,
                p_vet_id INT,
                p_appointment_id INT,
                p_record_date DATE,
                p_registration_fee DECIMAL(10,2),
                p_treatment_fee DECIMAL(10,2),
                p_medicines JSON
            )
            BEGIN
                DECLARE v_record_id INT;
                DECLARE v_medicine_total DECIMAL(10,2);
                DECLARE v_total_fee DECIMAL(10,2);

                INSERT INTO medical_records
                    (diagnosis, treatment, pet_id, vet_id, appointment_id, record_date,
                     registration_fee, treatment_fee, total_fee, version)
                VALUES
                    (p_diagnosis, p_treatment, p_pet_id, p_vet_id, p_appointment_id, p_record_date,
                     p_registration_fee, p_treatment_fee, p_registration_fee + p_treatment_fee, 1);

                SET v_record_id = LAST_INSERT_ID();

                INSERT INTO medical_record_medicines (medical_record_id, medicine_id, quantity)
                SELECT v_record_id, m.medicine_id, m.quantity
                FROM JSON_TABLE(p_medicines, '$[*]' COLUMNS (
                    medicine_id INT PATH '$.medicine_id',
                    quantity INT PATH '$.quantity'
                )) AS m;

                SELECT COALESCE(SUM(m.price * mrm.quantity), 0) INTO v_medicine_total
                FROM medical_record_medicines mrm
                JOIN medicine m ON mrm.medicine_id = m.id
                WHERE mrm.medical_record_id = v_record_id;

                SET v_total_fee = p_registration_fee + p_treatment_fee + v_medicine_total;
                UPDATE medical_records SET total_fee = v_total_fee WHERE id = v_record_id;

                SELECT v_record_id AS record_id, v_total_fee AS total_fee;
            END
        '''))

        if not User.query.filter_by(username='admin').first():
            db.session.add(User(username='admin', password=generate_password_hash('admin123'), role='admin'))
            db.session.add(User(username='doctor', password=generate_password_hash('doctor123'), role='doctor'))
            db.session.add(User(username='pharmacy', password=generate_password_hash('pharmacy123'), role='pharmacist'))
            db.session.add(User(username='reception', password=generate_password_hash('reception123'), role='receptionist'))
            db.session.commit()
            print('默认用户已创建：')
            print('  管理员 - admin / admin123')
            print('  医生   - doctor / doctor123')
            print('  药房   - pharmacy / pharmacy123')
            print('  前台   - reception / reception123')

    app.run(debug=True)