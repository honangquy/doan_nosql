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
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        ho_ten = request.form.get('ho_ten')
        email = request.form.get('email')
        sdt = request.form.get('sdt')
        
        # Validate
        if password != confirm_password:
            flash('Mật khẩu xác nhận không khớp')
            return render_template('auth/register.html')
            
        # Check if username exists - sử dụng đúng tên trường
        existing_user = mongo.db.TaiKhoan.find_one({'ten': username})
        if existing_user:
            flash('Tên đăng nhập đã tồn tại')
            return render_template('auth/register.html')
        
        # Create new user - sử dụng đúng schema database
        user_data = {
            'ten': username,  # Sử dụng 'ten' thay vì 'username'
            'matKhau': password,  # Sử dụng 'matKhau' thay vì 'password'
            'maLoai': 'USER',  # Sử dụng 'maLoai' thay vì 'role'
            'hoTen': ho_ten,
            'email': email,
            'soDienThoai': sdt,
            'ngayThem': datetime.now(),
            'trangThai': 'active'
        }
        
        result = mongo.db.TaiKhoan.insert_one(user_data)
        
        # Auto login after registration
        session['user_id'] = str(result.inserted_id)
        session['role'] = 'USER'
        session['username'] = username
        
        flash('Đăng ký thành công!')
        return redirect(url_for('user.index'))
        
    return render_template('auth/register.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('user.index'))
