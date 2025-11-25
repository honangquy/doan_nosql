from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app import mongo
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Sửa lại để phù hợp với schema database thực tế
        user = mongo.db.TaiKhoan.find_one({'ten': username})
        
        # Kiểm tra mật khẩu - xử lý cả plain text và hashed
        password_match = False
        if user:
            stored_password = user.get('matKhau', '')
            if stored_password == password:  # Plain text match
                password_match = True
            elif stored_password == f'hashed_password_{password}':  # Format: hashed_password_123
                password_match = True
            elif stored_password.startswith('hashed_') and stored_password.replace('hashed_password_', '') == password:
                password_match = True
        
        if user and password_match: 
            session['user_id'] = str(user['_id'])
            session['role'] = user.get('maLoai', 'USER')  # Sử dụng maLoai thay vì role
            session['username'] = user['ten']  # Sử dụng ten thay vì username
            
            if user.get('maLoai') == 'ADMIN':
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('user.index'))
        else:
            flash('Invalid username or password')
            
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        ho_ten = request.form.get('ho_ten')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        email = request.form.get('email')
        sdt = request.form.get('sdt')
        dia_chi = request.form.get('dia_chi', '')
        
        # Validate
        if not ho_ten or not password or not sdt:
            flash('Vui lòng điền đầy đủ thông tin bắt buộc (Họ tên, Mật khẩu, Số điện thoại)')
            return render_template('auth/register.html')
            
        if password != confirm_password:
            flash('Mật khẩu xác nhận không khớp')
            return render_template('auth/register.html')
            
        # Check if phone number exists
        existing_customer = mongo.db.KhachHang.find_one({'dienThoai': sdt})
        if existing_customer:
            flash('Số điện thoại đã được đăng ký')
            return render_template('auth/register.html')
        
        # Check if email exists (if provided)
        if email:
            existing_email = mongo.db.KhachHang.find_one({'email': email})
            if existing_email:
                flash('Email đã được đăng ký')
                return render_template('auth/register.html')
        
        # Generate new customer code
        last_customer = mongo.db.KhachHang.find_one(
            {'maKhach': {'$regex': '^KH[0-9]+$'}},
            sort=[('maKhach', -1)]
        )
        
        if last_customer and last_customer.get('maKhach'):
            try:
                last_num = int(last_customer['maKhach'].replace('KH', ''))
                new_code = f'KH{str(last_num + 1).zfill(4)}'
            except (ValueError, TypeError):
                # Fallback if parsing fails
                new_code = f'KH{str(mongo.db.KhachHang.count_documents({}) + 1).zfill(4)}'
        else:
            new_code = 'KH0001'
        
        # Create new customer account - đúng cấu trúc KhachHang
        customer_data = {
            'maKhach': new_code,
            'ten': ho_ten,
            'dienThoai': sdt,
            'email': email if email else '',
            'diaChi': dia_chi,
            'soCmnd': '',
            'moTa': 'Khách hàng đăng ký online',
            'matKhau': password,
            'ngayThem': datetime.now()
        }
        
        result = mongo.db.KhachHang.insert_one(customer_data)
        
        # Auto login after registration
        session['customer_id'] = str(result.inserted_id)
        session['customer_code'] = new_code
        session['customer_name'] = ho_ten
        session['role'] = 'CUSTOMER'
        
        flash('Đăng ký thành công!', 'success')
        return redirect(url_for('user.index'))
        
    return render_template('auth/register.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('user.index'))
