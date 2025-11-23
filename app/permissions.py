"""
Hệ thống phân quyền Role-Based Access Control (RBAC) cho Flask
"""

from functools import wraps
from flask import session, redirect, url_for, flash, render_template, abort
from app import mongo

# 1. Cấu trúc phân quyền cho 4 vai trò
ROLES_PERMISSIONS = {
    "QLVH": [  # Quản lý vận hành chung - Full access
        "dashboard", "tuyen_duong", "lich_trinh", "xe_khach", "so_do_ghe",
        "gia_ve", "chuyen_xe", "ve_xe", "khach_hang", "tai_khoan",
        "tin_tuc", "dia_diem", "doanh_thu", "thong_ke",
        "create", "read", "update", "delete"  # CRUD permissions
    ],
    
    "QLKT": [  # Kế toán trưởng - Finance focused
        "dashboard", "gia_ve", "ve_xe", "khach_hang", "doanh_thu", "thong_ke",
        "lich_trinh", "chuyen_xe",  # Cần xem lịch trình để tính toán
        "read", "update"  # Chỉ xem và cập nhật, không tạo/xóa
    ],
    
    "QLNS": [  # Trưởng phòng nhân sự - HR focused
        "dashboard", "tai_khoan", "nhan_vien", "thong_ke",
        "dia_diem",  # Quản lý thông tin địa điểm làm việc
        "create", "read", "update", "delete"  # Full CRUD cho nhân sự
    ],
    
    "CSKH": [  # Nhân viên chăm sóc khách hàng - Customer service
        "dashboard", "ve_xe", "khach_hang", "lich_trinh", "chuyen_xe",
        "tuyen_duong", "gia_ve", "tin_tuc",  # Thông tin cần thiết để hỗ trợ KH
        "read", "update"  # Chỉ xem và cập nhật thông tin KH, không xóa
    ]
}

# 2. Middleware và Decorators
def get_user_role():
    """Lấy role của user từ session hoặc database"""
    if 'user_id' not in session:
        return None
    
    user_id = session.get('user_id')
    user = mongo.db.TaiKhoan.find_one({'_id': user_id}) if mongo else None
    
    if user:
        return user.get('role', user.get('maLoai'))  # Support both 'role' and 'maLoai'
    
    # Fallback: check session directly
    return session.get('role')

def has_permission(permission):
    """Kiểm tra user có quyền truy cập permission không"""
    user_role = get_user_role()
    if not user_role:
        return False
    
    # Admin luôn có full quyền
    if user_role == 'ADMIN':
        return True
    
    return permission in ROLES_PERMISSIONS.get(user_role, [])

def has_crud_permission(action):
    """Kiểm tra quyền CRUD cụ thể: create, read, update, delete"""
    return has_permission(action)

def require_role(*allowed_permissions):
    """
    Decorator yêu cầu user phải có ít nhất một trong các quyền được chỉ định
    
    Usage:
    @require_role('dashboard')
    @require_role('tuyen_duong', 'read')
    @require_role('gia_ve', 'update')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Kiểm tra đăng nhập
            if 'user_id' not in session:
                flash('Vui lòng đăng nhập để truy cập', 'error')
                return redirect(url_for('auth.login'))
            
            # Admin có full quyền
            user_role = get_user_role()
            if user_role == 'ADMIN':
                return f(*args, **kwargs)
            
            # Kiểm tra quyền
            if not user_role:
                return redirect(url_for('admin.access_denied'))
            
            # Kiểm tra có ít nhất một quyền được yêu cầu
            has_required_permission = False
            for permission in allowed_permissions:
                if has_permission(permission):
                    has_required_permission = True
                    break
            
            if not has_required_permission:
                return redirect(url_for('admin.access_denied'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_crud_permission(action):
    """
    Decorator yêu cầu quyền CRUD cụ thể
    
    Usage:
    @require_crud_permission('create')
    @require_crud_permission('delete')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not has_crud_permission(action):
                flash(f'Bạn không có quyền {action}', 'error')
                return redirect(url_for('admin.access_denied'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# 3. Context Processor cho Templates
def inject_permissions():
    """Inject quyền vào template context"""
    return dict(
        has_permission=has_permission,
        has_crud_permission=has_crud_permission,
        user_role=get_user_role(),
        ROLES_PERMISSIONS=ROLES_PERMISSIONS
    )

# 4. Utility Functions
def get_accessible_menu_items():
    """Lấy danh sách menu items mà user có quyền truy cập"""
    user_role = get_user_role()
    if not user_role:
        return []
    
    if user_role == 'ADMIN':
        # Admin có full quyền
        return [
            {'name': 'Dashboard', 'url': 'admin.dashboard', 'icon': 'bi-speedometer2', 'permission': 'dashboard'},
            {'name': 'Tuyến Đường', 'url': 'admin.crud_list', 'params': {'collection_name': 'TuyenDuong'}, 'icon': 'bi-signpost-2', 'permission': 'tuyen_duong'},
            {'name': 'Lịch Trình', 'url': 'admin.crud_list', 'params': {'collection_name': 'LichTrinh'}, 'icon': 'bi-calendar3', 'permission': 'lich_trinh'},
            {'name': 'Xe Khách', 'url': 'admin.crud_list', 'params': {'collection_name': 'XeKhach'}, 'icon': 'bi-bus-front', 'permission': 'xe_khach'},
            {'name': 'Sơ Đồ Ghế', 'url': 'admin.crud_list', 'params': {'collection_name': 'SoDoGhe'}, 'icon': 'bi-grid-3x3', 'permission': 'so_do_ghe'},
            {'name': 'Giá Vé', 'url': 'admin.crud_list', 'params': {'collection_name': 'GiaVe'}, 'icon': 'bi-tag', 'permission': 'gia_ve'},
            {'name': 'Chuyến Xe', 'url': 'admin.crud_list', 'params': {'collection_name': 'LichTrinh'}, 'icon': 'bi-truck', 'permission': 'chuyen_xe'},
            {'name': 'Vé Xe', 'url': 'admin.crud_list', 'params': {'collection_name': 'VeXe'}, 'icon': 'bi-ticket', 'permission': 've_xe'},
            {'name': 'Khách Hàng', 'url': 'admin.crud_list', 'params': {'collection_name': 'KhachHang'}, 'icon': 'bi-people', 'permission': 'khach_hang'},
            {'name': 'Tài Khoản', 'url': 'admin.accounts', 'icon': 'bi-person-gear', 'permission': 'tai_khoan'},
            {'name': 'Tin Tức', 'url': 'admin.crud_list', 'params': {'collection_name': 'TinTuc'}, 'icon': 'bi-newspaper', 'permission': 'tin_tuc'},
            {'name': 'Địa Điểm', 'url': 'admin.crud_list', 'params': {'collection_name': 'DiaDiem'}, 'icon': 'bi-geo-alt', 'permission': 'dia_diem'},
            {'name': 'Doanh Thu', 'url': 'admin.revenue', 'icon': 'bi-graph-up', 'permission': 'doanh_thu'},
            {'name': 'Thống Kê', 'url': 'admin.statistics', 'icon': 'bi-bar-chart', 'permission': 'thong_ke'},
        ]
    
    # Menu items cho các role khác
    all_menu_items = [
        {'name': 'Dashboard', 'url': 'admin.dashboard', 'icon': 'bi-speedometer2', 'permission': 'dashboard'},
        {'name': 'Tuyến Đường', 'url': 'admin.crud_list', 'params': {'collection_name': 'TuyenDuong'}, 'icon': 'bi-signpost-2', 'permission': 'tuyen_duong'},
        {'name': 'Lịch Trình', 'url': 'admin.crud_list', 'params': {'collection_name': 'LichTrinh'}, 'icon': 'bi-calendar3', 'permission': 'lich_trinh'},
        {'name': 'Xe Khách', 'url': 'admin.crud_list', 'params': {'collection_name': 'XeKhach'}, 'icon': 'bi-bus-front', 'permission': 'xe_khach'},
        {'name': 'Sơ Đồ Ghế', 'url': 'admin.crud_list', 'params': {'collection_name': 'SoDoGhe'}, 'icon': 'bi-grid-3x3', 'permission': 'so_do_ghe'},
        {'name': 'Giá Vé', 'url': 'admin.crud_list', 'params': {'collection_name': 'GiaVe'}, 'icon': 'bi-tag', 'permission': 'gia_ve'},
        {'name': 'Chuyến Xe', 'url': 'admin.crud_list', 'params': {'collection_name': 'LichTrinh'}, 'icon': 'bi-truck', 'permission': 'chuyen_xe'},
        {'name': 'Vé Xe', 'url': 'admin.crud_list', 'params': {'collection_name': 'VeXe'}, 'icon': 'bi-ticket', 'permission': 've_xe'},
        {'name': 'Khách Hàng', 'url': 'admin.crud_list', 'params': {'collection_name': 'KhachHang'}, 'icon': 'bi-people', 'permission': 'khach_hang'},
        {'name': 'Tài Khoản', 'url': 'admin.accounts', 'icon': 'bi-person-gear', 'permission': 'tai_khoan'},
        {'name': 'Tin Tức', 'url': 'admin.crud_list', 'params': {'collection_name': 'TinTuc'}, 'icon': 'bi-newspaper', 'permission': 'tin_tuc'},
        {'name': 'Địa Điểm', 'url': 'admin.crud_list', 'params': {'collection_name': 'DiaDiem'}, 'icon': 'bi-geo-alt', 'permission': 'dia_diem'},
        {'name': 'Doanh Thu', 'url': 'admin.revenue', 'icon': 'bi-graph-up', 'permission': 'doanh_thu'},
        {'name': 'Thống Kê', 'url': 'admin.statistics', 'icon': 'bi-bar-chart', 'permission': 'thong_ke'},
    ]
    
    # Lọc menu items theo quyền
    accessible_items = []
    for item in all_menu_items:
        if has_permission(item['permission']):
            accessible_items.append(item)
    
    return accessible_items

# 5. Role Management Functions
def create_user_with_role(username, password, role, full_name=None, email=None):
    """Tạo user mới với role"""
    if role not in ROLES_PERMISSIONS:
        raise ValueError(f"Invalid role: {role}")
    
    user_data = {
        'ten': username,
        'matKhau': password,  # Should be hashed in production
        'role': role,
        'maLoai': role,  # Backward compatibility
        'hoTen': full_name or username,
        'email': email or f"{username}@company.com",
        'trangThai': 'Hoạt động',
        'ngayTao': mongo.db.now() if mongo else None
    }
    
    if mongo:
        return mongo.db.TaiKhoan.insert_one(user_data)
    
    return user_data

def update_user_role(user_id, new_role):
    """Cập nhật role cho user"""
    if new_role not in ROLES_PERMISSIONS:
        raise ValueError(f"Invalid role: {new_role}")
    
    if mongo:
        return mongo.db.TaiKhoan.update_one(
            {'_id': user_id},
            {'$set': {'role': new_role, 'maLoai': new_role}}
        )
    
    return True

# 6. Sample Users for Testing
SAMPLE_USERS = [
    {
        'ten': 'qlvh_user',
        'matKhau': '123456',
        'role': 'QLVH',
        'hoTen': 'Nguyễn Văn Quản Lý',
        'email': 'qlvh@company.com'
    },
    {
        'ten': 'qlkt_user', 
        'matKhau': '123456',
        'role': 'QLKT',
        'hoTen': 'Trần Thị Kế Toán',
        'email': 'qlkt@company.com'
    },
    {
        'ten': 'qlns_user',
        'matKhau': '123456', 
        'role': 'QLNS',
        'hoTen': 'Lê Văn Nhân Sự',
        'email': 'qlns@company.com'
    },
    {
        'ten': 'cskh_user',
        'matKhau': '123456',
        'role': 'CSKH', 
        'hoTen': 'Phạm Thị Chăm Sóc',
        'email': 'cskh@company.com'
    }
]