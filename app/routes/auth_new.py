from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app import mongo
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')  # Có thể là email cho customer
        password = request.form.get('password')
        
        # 1. KIỂM TRA ADMIN/STAFF LOGIN (TaiKhoan table)
        admin_user = mongo.db.TaiKhoan.find_one({'ten': username})
        
        if admin_user:
            # Kiểm tra mật khẩu admin - xử lý cả plain text và hashed
            password_match = False
            stored_password = admin_user.get('matKhau', '')
            if stored_password == password:  # Plain text match
                password_match = True
            elif stored_password == f'hashed_password_{password}':  # Format: hashed_password_123
                password_match = True
            elif stored_password.startswith('hashed_') and stored_password.replace('hashed_password_', '') == password:
                password_match = True
            
            if password_match:
                session['user_id'] = str(admin_user['_id'])
                session['role'] = admin_user.get('maLoai', 'ADMIN')
                session['username'] = admin_user['ten']
                return redirect(url_for('admin.dashboard'))
        
        # 2. KIỂM TRA CUSTOMER LOGIN (KhachHang table)
        # Customer có thể đăng nhập bằng email hoặc số điện thoại
        customer = mongo.db.KhachHang.find_one({
            '$or': [
                {'email': username},
                {'dienThoai': username}
            ]
        })
        
        if customer and customer.get('matKhau') == password:
            session['customer_id'] = str(customer['_id'])
            session['ma_khach'] = customer.get('maKhach')
            session['role'] = 'CUSTOMER'
            session['customer_name'] = customer.get('ten')
            session['customer_email'] = customer.get('email')
            flash(f'Chào mừng {customer.get("ten")}! Đăng nhập thành công.')
            return redirect(url_for('user.index'))  # Redirect to homepage
        
        # Nếu không match admin hay customer
        flash('Sai thông tin đăng nhập hoặc mật khẩu')
            
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        ho_ten = request.form.get('ho_ten')
        email = request.form.get('email')
        sdt = request.form.get('sdt')
        
        # Validate
        if password != confirm_password:
            flash('Mật khẩu xác nhận không khớp')
            return render_template('auth/register.html')
            
        # Check if customer exists - kiểm tra email và số điện thoại
        existing_email = mongo.db.KhachHang.find_one({'email': email})
        if existing_email:
            flash('Email đã được sử dụng')
            return render_template('auth/register.html')
            
        existing_phone = mongo.db.KhachHang.find_one({'dienThoai': sdt})
        if existing_phone:
            flash('Số điện thoại đã được sử dụng')
            return render_template('auth/register.html')
        
        # Tạo mã khách hàng mới
        last_customer = mongo.db.KhachHang.find().sort('maKhach', -1).limit(1)
        last_customer_list = list(last_customer)
        if last_customer_list:
            last_ma = last_customer_list[0]['maKhach']
            # Extract number from KH0001 format
            last_num = int(last_ma[2:])  # Remove 'KH' prefix
            new_num = last_num + 1
        else:
            new_num = 1
        new_ma_khach = f'KH{new_num:04d}'  # Format as KH0001
        
        # Create new customer - lưu vào bảng KhachHang
        customer_data = {
            'maKhach': new_ma_khach,
            'ten': ho_ten,  # Họ tên đầy đủ
            'dienThoai': sdt,
            'email': email,
            'diaChi': '',  # Có thể để trống, cập nhật sau
            'soCmnd': '',  # Có thể để trống, cập nhật sau
            'moTa': 'Khách hàng đăng ký online',
            'matKhau': password,  # Thêm mật khẩu để đăng nhập
            'ngayThem': datetime.now()
        }
        
        result = mongo.db.KhachHang.insert_one(customer_data)
        
        # Auto login after registration
        session['customer_id'] = str(result.inserted_id)
        session['ma_khach'] = new_ma_khach
        session['role'] = 'CUSTOMER'
        session['customer_name'] = ho_ten
        session['customer_email'] = email
        
        flash(f'Chào mừng {ho_ten}! Đăng ký thành công và đã đăng nhập.')
        return redirect(url_for('user.index'))
        
    return render_template('auth/register.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('user.index'))