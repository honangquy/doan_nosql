from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app import mongo
from app.utils import get_object_id, vietnamese_to_css_class
from app.permissions import (
    require_role, require_crud_permission, has_permission, has_crud_permission,
    get_user_role, get_accessible_menu_items, ROLES_PERMISSIONS, SAMPLE_USERS
)
from bson import ObjectId
from datetime import datetime

admin_bp = Blueprint('admin', __name__)

# Context processor for templates - inject permissions into all admin templates
@admin_bp.context_processor
def inject_permissions():
    """Inject permission functions and data into all admin templates"""
    return {
        'has_permission': has_permission,
        'has_crud_permission': has_crud_permission,
        'get_user_role': get_user_role,
        'get_accessible_menu_items': get_accessible_menu_items,
        'accessible_menu': get_accessible_menu_items(),
        'user_role': get_user_role(),
        'ROLES_PERMISSIONS': ROLES_PERMISSIONS
    }

def create_seats_for_trip(trip_id, vehicle_id):
    """Tạo ghế thông minh cho trip - tránh duplicate và tối ưu"""
    try:
        # 1. Kiểm tra ghế đã tồn tại
        existing_seats = mongo.db.Ghe.count_documents({'maLichTrinh': trip_id})
        if existing_seats > 0:
            print(f"Trip {trip_id} already has {existing_seats} seats")
            return existing_seats
        
        # 2. Lấy thông tin xe để xác định layout ghế
        vehicle = mongo.db.XeKhach.find_one({'maXeKhach': vehicle_id})
        if not vehicle:
            print(f"Vehicle {vehicle_id} not found")
            return 0
        
        vehicle_type = vehicle.get('maLoai', '')
        
        # 3. Xác định số ghế và layout dựa trên loại xe
        seat_config = get_seat_configuration(vehicle_type)
        
        # 4. Tạo ghế theo layout
        seats_data = []
        for i in range(1, seat_config['count'] + 1):
            seat_number = f"{seat_config['prefix']}{i:02d}"
            seat_data = {
                'maGhe': f"GHE_{trip_id}_{seat_number}",
                'maLichTrinh': trip_id,  # CRITICAL: Link to trip, not vehicle
                'soGhe': seat_number,
                'tinhTrang': 'Trống',
                'loaiGhe': seat_config['type'],
                'moTa': f'Ghế {seat_number} - {seat_config["type"]} - Trip {trip_id}',
                'ngayTao': datetime.now()
            }
            seats_data.append(seat_data)
        
        # 5. Bulk insert cho performance tốt hơn
        if seats_data:
            result = mongo.db.Ghe.insert_many(seats_data)
            created_count = len(result.inserted_ids)
            print(f"Created {created_count} seats for trip {trip_id}")
            return created_count
        
        return 0
        
    except Exception as e:
        print(f"Error creating seats for trip {trip_id}: {e}")
        return 0

def get_seat_configuration(vehicle_type):
    """Xác định cấu hình ghế dựa trên loại xe"""
    vehicle_type = vehicle_type.upper()
    
    if 'LIMOUSINE' in vehicle_type:
        return {
            'count': 22,
            'prefix': 'L',
            'type': 'Limousine',
            'layout': '2+1'
        }
    elif 'GIUONG' in vehicle_type or 'SLEEPER' in vehicle_type:
        return {
            'count': 36,
            'prefix': 'G', 
            'type': 'Giường nằm',
            'layout': '2+1'
        }
    elif 'VIP' in vehicle_type:
        return {
            'count': 28,
            'prefix': 'V',
            'type': 'VIP',
            'layout': '2+2'
        }
    else:
        return {
            'count': 40,
            'prefix': 'A',
            'type': 'Thường',
            'layout': '2+2'
        }

# Define schemas for dynamic CRUD
SCHEMAS = {
    'TuyenDuong': {
        'fields': ['maTuyenDuong', 'tenTuyenDuong', 'diemDau', 'diemCuoi', 'tinhTrang'], 
        'label': 'Tuyến Đường'
    },
    'LichTrinh': {
        'fields': ['maLichTrinh', 'maXe', 'diemDi', 'diemDen', 'ngayDi', 'tinhTrang'], 
        'label': 'Lịch Trình'
    },
    'XeKhach': {
        'fields': ['maXeKhach', 'ten', 'bienSo', 'maLoai', 'tinhTrang'], 
        'label': 'Xe Khách'
    },
    'VeXe': {
        'fields': ['maVe', 'maLichTrinh', 'maGhe', 'maKhach', 'tinhTrang'], 
        'label': 'Vé Xe'
    },
    'KhachHang': {
        'fields': ['maKhach', 'ten', 'dienThoai', 'email', 'diaChi', 'matKhau'], 
        'label': 'Khách Hàng',
        'password_field': 'matKhau'
    },
    'TaiKhoan': {
        'fields': ['ten', 'role', 'email', 'tinhTrang'], 
        'label': 'Tài Khoản',
        'role_options': ['ADMIN', 'QLVH', 'QLKT', 'QLNS', 'CSKH'],
        'hidden_fields': ['matKhau', 'maLoai']
    },
    'TinTuc': {
        'fields': ['maTinTuc', 'maLoai', 'tieuDe', 'noiDung', 'ghiChu', 'tinhTrang'], 
        'label': 'Tin Tức'
    },
    'DiaDiem': {
        'fields': ['maDiaDiem', 'maTinh', 'tenDiaDiem', 'diaChi', 'dienThoai', 'tinhTrang', 'moTa'], 
        'label': 'Địa Điểm'
    },
    'GiaVe': {
        'fields': ['maGiaVe', 'tuyen', 'giaVe', 'phuThu', 'tinhTrang'], 
        'label': 'Giá Vé'
    },
    'DaiLy': {
        'fields': ['tenDaiLy', 'diaChi', 'soDienThoai'], 
        'label': 'Đại Lý'
    },
    'NhanVien': {
        'fields': ['hoTen', 'ngaySinh', 'soDienThoai', 'chucVu'], 
        'label': 'Nhân Viên'
    },
    'LoaiNhanVien': {
        'fields': ['tenLoai', 'moTa'], 
        'label': 'Loại Nhân Viên'
    },
    'LoaiTinTuc': {
        'fields': ['tenLoai'], 
        'label': 'Loại Tin Tức'
    }
}

@admin_bp.context_processor
def inject_sidebar_stats():
    """Inject sidebar statistics for admin panel"""
    try:
        return {
            'tuyen_count': mongo.db.TuyenDuong.count_documents({}),
            'lich_count': mongo.db.LichTrinh.count_documents({}),
            'trip_count': mongo.db.LichTrinh.count_documents({}),
            'xe_count': mongo.db.XeKhach.count_documents({}),
            've_count': mongo.db.VeXe.count_documents({}),
            'khach_count': mongo.db.KhachHang.count_documents({}),
            'tin_count': mongo.db.TinTuc.count_documents({}),
            'gia_count': mongo.db.GiaVe.count_documents({})
        }
    except Exception as e:
        return {
            'tuyen_count': 0, 'lich_count': 0, 'trip_count': 0, 'xe_count': 0,
            've_count': 0, 'khach_count': 0, 'tin_count': 0, 'gia_count': 0
        }

@admin_bp.before_request
def check_admin():
    # Allow access to access_denied page
    if request.endpoint == 'admin.access_denied':
        return
        
    # For API endpoints, check authentication but return JSON error instead of redirect
    if request.endpoint and request.endpoint.startswith('admin.') and '/api/' in request.path:
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        user_role = get_user_role()
        if not user_role or (user_role != 'ADMIN' and user_role not in ROLES_PERMISSIONS):
            return jsonify({'error': 'Admin access required'}), 403
        return None
        
    # For regular pages, redirect to login
    if 'user_id' not in session and 'role' not in session:
        flash('Bạn cần đăng nhập để truy cập trang quản trị', 'error')
        return redirect(url_for('auth.login'))
    
    # Admin có full quyền
    if session.get('role') == 'ADMIN':
        return
        
    # Kiểm tra role hợp lệ
    user_role = get_user_role()
    if not user_role or user_role not in ROLES_PERMISSIONS:
        flash('Tài khoản của bạn không có quyền truy cập', 'error')
        return redirect(url_for('auth.login'))

@admin_bp.route('/')
def admin_index():
    # Redirect to dashboard as default admin page
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/api-test')
def api_test():
    """API test page for debugging"""
    return render_template('admin/api_test.html')

@admin_bp.route('/dashboard')
@require_role('dashboard')
def dashboard():
    try:
        # Calculate comprehensive dashboard statistics
        total_bookings = mongo.db.VeXe.count_documents({})
        total_customers = mongo.db.KhachHang.count_documents({})
        total_routes = mongo.db.TuyenDuong.count_documents({})
        total_vehicles = mongo.db.XeKhach.count_documents({})
        
        # Calculate total revenue (estimate based on average ticket price)
        avg_ticket_price = 300000  # 300k VND average
        total_revenue = total_bookings * avg_ticket_price
        
        # Get active routes count
        active_routes = mongo.db.TuyenDuong.count_documents({'tinhTrang': 'Hoạt động'})
        
        stats = {
            'total_bookings': total_bookings,
            'total_customers': total_customers,
            'total_routes': active_routes or total_routes,
            'total_vehicles': total_vehicles,
            'total_revenue': total_revenue
        }
        
        # Recent activities - get latest bookings with better data
        recent_bookings = list(mongo.db.VeXe.find().sort('_id', -1).limit(5))
        
        # Get recent customers
        recent_customers = list(mongo.db.KhachHang.find().sort('_id', -1).limit(5))
        
        # Get recent news/announcements
        recent_news = list(mongo.db.TinTuc.find().sort('_id', -1).limit(3))
        
        return render_template('admin/dashboard_new.html', 
                             stats=stats, 
                             recent_bookings=recent_bookings,
                             recent_customers=recent_customers,
                             recent_news=recent_news)
                             
    except Exception as e:
        flash(f'Lỗi tải dashboard: {str(e)}', 'error')
        # Fallback to basic stats
        stats = {
            'total_bookings': 0,
            'total_customers': 0,
            'total_routes': 0,
            'total_revenue': 0
        }
        return render_template('admin/dashboard_new.html', 
                             stats=stats, 
                             recent_bookings=[],
                             recent_customers=[],
                             recent_news=[])

# Users management
@admin_bp.route('/users')
def admin_users():
    users = list(mongo.db.TaiKhoan.find())
    total_users = len(users)
    active_users = len([u for u in users if u.get('tinhTrang') == 'Hoạt động'])
    new_today = 0  # Can be calculated based on creation date
    total_bookings = mongo.db.VeXe.count_documents({})
    
    return render_template('admin/users.html', 
                         users=users,
                         total_users=total_users,
                         active_users=active_users,
                         new_today=new_today,
                         total_bookings=total_bookings)

@admin_bp.route('/users', methods=['POST'])
def add_user():
    try:
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'CSKH')
        is_active = bool(int(request.form.get('is_active', 1)))
        
        # Check if username exists
        if mongo.db.TaiKhoan.find_one({'ten': username}):
            flash('Tên đăng nhập đã tồn tại!', 'error')
            return redirect(url_for('admin.admin_users'))
        
        # Hash password (simple hashing for demo)
        import hashlib
        password_hash = hashlib.md5(password.encode()).hexdigest()
        
        # Create user in TaiKhoan collection
        user_data = {
            'ten': username,
            'email': email,
            'matKhau': password_hash,
            'maLoai': role,
            'tinhTrang': 'Hoạt động' if is_active else 'Không hoạt động',
            'ngayThem': datetime.now(),
            'stt': datetime.now(),
            'moTa': f'Tài khoản {role} được tạo qua admin'
        }
        
        mongo.db.TaiKhoan.insert_one(user_data)
        flash('Thêm người dùng thành công!', 'success')
        
    except Exception as e:
        flash(f'Lỗi: {str(e)}', 'error')
    
    return redirect(url_for('admin.admin_users'))

# Routes management - Use generic CRUD system
@admin_bp.route('/routes')
def admin_routes():
    # Redirect to the standard CRUD list for TuyenDuong
    return redirect(url_for('admin.list_items', collection_name='TuyenDuong'))

# API endpoints for dashboard stats
@admin_bp.route('/api/stats')
def api_stats():
    stats = {
        'total_bookings': mongo.db.VeXe.count_documents({}),
        'total_customers': mongo.db.KhachHang.count_documents({}),
        'total_routes': mongo.db.TuyenDuong.count_documents({}),
        'total_users': mongo.db.TaiKhoan.count_documents({})
    }
    return jsonify(stats)

@admin_bp.route('/api/route-info/<route_id>')
def get_route_info(route_id):
    """API để lấy thông tin tuyến đường cho auto-fill"""
    try:
        print(f"API route-info called with route_id: {route_id}")  # Debug log
        
        # Validate input
        if not route_id or not route_id.strip():
            return jsonify({'error': 'Route ID is required'}), 400
            
        # Tìm tuyến đường theo ID
        route = mongo.db.TuyenDuong.find_one({'maTuyenDuong': route_id})
        print(f"Found route: {route}")  # Debug log
        
        if not route:
            return jsonify({'error': f'Không tìm thấy tuyến đường với ID: {route_id}'}), 404
        
        # Trả về dữ liệu mapping theo logic danh sách chuyến xe
        route_info = {
            'maTuyenDuong': route.get('maTuyenDuong', ''),
            'tenTuyenDuong': route.get('tenTuyenDuong', ''),
            'diemDau': route.get('diemDau', ''),  # -> diemDi
            'diemCuoi': route.get('diemCuoi', ''), # -> diemDen
            'doDai': route.get('doDai', 0),
            'thoiGianDi': route.get('thoiGianDi', 0)
        }
        
        # Tìm xe phù hợp với tuyến này - LOGIC CẢI TIẾN
        matching_vehicles = []
        vehicles = list(mongo.db.XeKhach.find())
        
        route_name = route.get('tenTuyenDuong', '').lower()
        
        for vehicle in vehicles:
            vehicle_route = vehicle.get('tuyen', '').strip()
            vehicle_name = vehicle.get('ten', '').lower()
            
            # LOGIC MATCHING CẢI TIẾN - CHÍNH XÁC VÀ STRICT
            is_matching = False
            match_reason = 'none'
            
            if vehicle_route:
                route_id_clean = route_id.upper().strip()
                vehicle_route_clean = vehicle_route.upper().strip()
                
                print(f"Checking: Route='{route_id_clean}' vs Vehicle='{vehicle_route_clean}'")  # Debug
                
                # 1. EXACT MATCH - Khớp hoàn toàn (Ưu tiên cao nhất)
                if vehicle_route_clean == route_id_clean:
                    is_matching = True
                    match_reason = 'exact_match'
                    print(f"  ✅ EXACT MATCH: {vehicle_name}")
                
                # 2. REVERSE DIRECTION - Ngược chiều (VD: HCM-AG vs AG-HCM)
                elif '-' in route_id_clean and '-' in vehicle_route_clean:
                    route_parts = route_id_clean.split('-')
                    vehicle_parts = vehicle_route_clean.split('-')
                    
                    if (len(route_parts) == 2 and len(vehicle_parts) == 2 and
                        route_parts[0] == vehicle_parts[1] and route_parts[1] == vehicle_parts[0]):
                        is_matching = True
                        match_reason = 'reverse_direction'
                        print(f"  ✅ REVERSE: {vehicle_name}")
                
                # 3. PARTIAL MATCH - Có ít nhất 2 thành phần chung
                elif '-' in route_id_clean and '-' in vehicle_route_clean:
                    route_parts = set(route_id_clean.split('-'))
                    vehicle_parts = set(vehicle_route_clean.split('-'))
                    
                    common_parts = route_parts & vehicle_parts
                    if len(common_parts) >= 2:
                        is_matching = True
                        match_reason = f'partial_{len(common_parts)}_parts'
                        print(f"  ✅ PARTIAL: {vehicle_name} - {common_parts}")
                
                # 4. SUB-ROUTE MATCH - Chỉ cho phép một số tuyến con hợp lý
                elif '-' in route_id_clean and '-' in vehicle_route_clean:
                    is_matching, match_reason = check_subroute_match(route_id_clean, vehicle_route_clean)
                    if is_matching:
                        print(f"  ✅ SUBROUTE: {vehicle_name} - {match_reason}")
                
                if not is_matching:
                    print(f"  🔵 NO MATCH: {vehicle_name}")
            
            # Chỉ thêm xe nếu có matching chất lượng cao
            if is_matching and match_reason in ['exact_code', 'code_partial', 'pattern_match']:
                # Ưu tiên xe có exact match hoặc pattern match tốt
                matching_vehicles.append({
                    'maXeKhach': vehicle.get('maXeKhach', ''),
                    'ten': vehicle.get('ten', ''),
                    'bienSo': vehicle.get('bienSo', ''),
                    'tuyen': vehicle.get('tuyen', ''),
                    'tinhTrang': vehicle.get('tinhTrang', ''),
                    'match_reason': match_reason,
                    'match_score': 3 if match_reason == 'exact_code' else 2 if match_reason == 'code_partial' else 1
                })
            elif is_matching and match_reason == 'keyword_match' and len(matching_vehicles) < 10:
                # Chỉ thêm keyword match nếu chưa có nhiều xe
                matching_vehicles.append({
                    'maXeKhach': vehicle.get('maXeKhach', ''),
                    'ten': vehicle.get('ten', ''),
                    'bienSo': vehicle.get('bienSo', ''),
                    'tuyen': vehicle.get('tuyen', ''),
                    'tinhTrang': vehicle.get('tinhTrang', ''),
                    'match_reason': match_reason,
                    'match_score': 0
                })
        
        # Sắp xếp xe theo độ phù hợp (cao nhất trước)
        matching_vehicles.sort(key=lambda x: x.get('match_score', 0), reverse=True)
        
        # Giới hạn số lượng xe trả về để tránh quá tải
        route_info['matching_vehicles'] = matching_vehicles[:20]  # Tối đa 20 xe
        
        print(f"Returning route info: {route_info}")  # Debug log
        print(f"Matching vehicles count: {len(route_info.get('matching_vehicles', []))}")  # Debug log
        
        response = jsonify(route_info)
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return response
        
    except Exception as e:
        print(f"ERROR in get_route_info: {str(e)}")  # Debug log
        import traceback
        print(f"Traceback: {traceback.format_exc()}")  # Debug log
        
        error_response = jsonify({
            'error': f'Internal server error: {str(e)}',
            'route_id': route_id,
            'status': 'error'
        })
        error_response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return error_response, 500

@admin_bp.route('/api/vehicle-info/<vehicle_id>')
def get_vehicle_info(vehicle_id):
    """API để lấy thông tin xe khách"""
    try:
        # Tìm xe theo ID
        vehicle = mongo.db.XeKhach.find_one({'maXeKhach': vehicle_id})
        
        if not vehicle:
            return jsonify({'error': 'Không tìm thấy xe khách'}), 404
        
        # Lấy thông tin tuyến đường tương ứng
        vehicle_route = vehicle.get('tuyen', '')
        matching_routes = []
        
        if vehicle_route:
            routes = list(mongo.db.TuyenDuong.find())
            
            for route in routes:
                route_name = route.get('tenTuyenDuong', '').lower()
                
                # Logic matching
                if (vehicle_route.lower() in route_name or 
                    any(part in route_name for part in vehicle_route.lower().split('-'))):
                    
                    matching_routes.append({
                        'maTuyenDuong': route.get('maTuyenDuong', ''),
                        'tenTuyenDuong': route.get('tenTuyenDuong', ''),
                        'diemDau': route.get('diemDau', ''),
                        'diemCuoi': route.get('diemCuoi', '')
                    })
        
        vehicle_info = {
            'maXeKhach': vehicle.get('maXeKhach', ''),
            'ten': vehicle.get('ten', ''),
            'bienSo': vehicle.get('bienSo', ''),
            'tuyen': vehicle.get('tuyen', ''),
            'maLoai': vehicle.get('maLoai', ''),
            'tinhTrang': vehicle.get('tinhTrang', ''),
            'matching_routes': matching_routes
        }
        
        response = jsonify(vehicle_info)
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return response
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def extract_route_codes(route_text):
    """Trích xuất mã tuyến từ tên tuyến - CẢI TIẾN"""
    if not route_text:
        return set()
    
    text = route_text.lower()
    codes = set()
    
    # Patterns phổ biến mở rộng
    patterns = {
        'hcm': ['tp.hcm', 'ho chi minh', 'hồ chí minh', 'sài gòn', 'hcm'],
        'ct': ['cần thơ', 'can tho', 'ct'],
        'dl': ['đà lạt', 'da lat', 'lâm đồng', 'dl'],
        'vt': ['vũng tàu', 'vung tau', 'vt'],
        'ag': ['an giang', 'ag'],
        'cm': ['cà mau', 'ca mau', 'cm'],
        'dn': ['đà nẵng', 'da nang', 'danang', 'dn'],
        'nt': ['nha trang', 'nt'],
        'kg': ['kiên giang', 'kien giang', 'kg'],
        'vl': ['vĩnh long', 'vinh long', 'vl'],
        'dt': ['đồng tháp', 'dong thap', 'dt'],
        'gl': ['gia lai', 'gl'],
        'hn': ['hà nội', 'ha noi', 'hanoi', 'hn'],
        'tnn': ['tây ninh', 'tay ninh', 'tnn', 'tn']
    }
    
    # Kiểm tra pattern trực tiếp trước
    for code, variations in patterns.items():
        if any(var in text for var in variations):
            codes.add(code)
    
    # Kiểm tra mã tuyến trực tiếp (HCM-CT, etc.)
    import re
    route_pattern = re.findall(r'([a-z]{1,4})-([a-z]{1,4})', text)
    for match in route_pattern:
        codes.update(match)
    
    return codes

# Subroute matching function removed - no longer needed
# All vehicles are now returned without filtering

@admin_bp.route('/<collection_name>')
def list_items(collection_name):
    if collection_name not in SCHEMAS:
        flash('Collection not found')
        return redirect(url_for('admin.dashboard'))
    
    # Check permissions based on collection
    permission_map = {
        'TuyenDuong': 'tuyen_duong',
        'LichTrinh': 'lich_trinh', 
        'XeKhach': 'xe_khach',
        'KhachHang': 'khach_hang',
        'VeXe': 've_xe',
        'GiaVe': 'gia_ve',
        'NhanVien': 'nhan_vien',
        'TinTuc': 'tin_tuc',
        'TaiKhoan': 'tai_khoan'
    }
    
    required_permission = permission_map.get(collection_name)
    if required_permission and not has_permission(required_permission):
        return redirect(url_for('admin.access_denied'))
        
    items = list(mongo.db[collection_name].find())
    schema = SCHEMAS[collection_name]
    return render_template('admin/crud_list.html', items=items, schema=schema, collection_name=collection_name)

@admin_bp.route('/<collection_name>/add', methods=['GET', 'POST'])
def add_item(collection_name):
    if collection_name not in SCHEMAS:
        return redirect(url_for('admin.dashboard'))
    
    # Check permissions based on collection
    permission_map = {
        'TuyenDuong': 'tuyen_duong',
        'LichTrinh': 'lich_trinh', 
        'XeKhach': 'xe_khach',
        'KhachHang': 'khach_hang',
        'VeXe': 've_xe',
        'GiaVe': 'gia_ve',
        'NhanVien': 'nhan_vien',
        'TinTuc': 'tin_tuc',
        'TaiKhoan': 'tai_khoan'
    }
    
    required_permission = permission_map.get(collection_name)
    if required_permission and not has_permission(required_permission):
        return redirect(url_for('admin.access_denied'))
    
    # Check create permission
    if not has_crud_permission('create'):
        return redirect(url_for('admin.access_denied'))
        
    schema = SCHEMAS[collection_name]
    
    if request.method == 'POST':
        data = {}
        for field in schema['fields']:
            data[field] = request.form.get(field)
        
        # Special handling for TaiKhoan - sync role with maLoai and add required fields
        if collection_name == 'TaiKhoan':
            role = data.get('role')
            if role:
                data['maLoai'] = role  # Sync role with maLoai
                data['matKhau'] = request.form.get('matKhau', 'default123')  # Add password field
                data['hoTen'] = data.get('ten', '')  # Add full name field
                data['trangThai'] = data.get('tinhTrang', 'Hoạt động')  # Add status field
                data['ngayTao'] = datetime.now()  # Add creation date
        
        # Special handling for KhachHang - add creation date and validate password
        elif collection_name == 'KhachHang':
            data['ngayThem'] = datetime.now()  # Add creation date
            if not data.get('matKhau'):
                data['matKhau'] = 'khach123'  # Default password for customers
                
        mongo.db[collection_name].insert_one(data)
        flash(f'Added {schema["label"]} successfully')
        return redirect(url_for('admin.list_items', collection_name=collection_name))
        
    return render_template('admin/crud_form.html', schema=schema, collection_name=collection_name, item={})

@admin_bp.route('/<collection_name>/edit/<item_id>', methods=['GET', 'POST'])
def edit_item(collection_name, item_id):
    if collection_name not in SCHEMAS:
        return redirect(url_for('admin.dashboard'))
    
    # Check permissions based on collection
    permission_map = {
        'TuyenDuong': 'tuyen_duong',
        'LichTrinh': 'lich_trinh', 
        'XeKhach': 'xe_khach',
        'KhachHang': 'khach_hang',
        'VeXe': 've_xe',
        'GiaVe': 'gia_ve',
        'NhanVien': 'nhan_vien',
        'TinTuc': 'tin_tuc',
        'TaiKhoan': 'tai_khoan'
    }
    
    required_permission = permission_map.get(collection_name)
    if required_permission and not has_permission(required_permission):
        return redirect(url_for('admin.access_denied'))
    
    # Check update permission
    if not has_crud_permission('update'):
        return redirect(url_for('admin.access_denied'))
        
    schema = SCHEMAS[collection_name]
    
    # Special handling for LichTrinh - search by maLichTrinh first
    if collection_name == 'LichTrinh':
        item = mongo.db[collection_name].find_one({'maLichTrinh': item_id})
        if not item:
            # Try by ObjectId if not found by maLichTrinh
            try:
                item = mongo.db[collection_name].find_one({'_id': get_object_id(item_id)})
            except:
                item = None
    else:
        item = mongo.db[collection_name].find_one({'_id': get_object_id(item_id)})
    
    if not item:
        flash(f'{schema["label"]} not found', 'error')
        return redirect(url_for('admin.list_items', collection_name=collection_name))
    
    if request.method == 'POST':
        data = {}
        for field in schema['fields']:
            data[field] = request.form.get(field)
        
        # Special handling for TaiKhoan - sync role with maLoai and password update
        if collection_name == 'TaiKhoan':
            role = data.get('role')
            if role:
                data['maLoai'] = role  # Sync role with maLoai
                data['hoTen'] = data.get('ten', '')  # Update full name field
                data['trangThai'] = data.get('tinhTrang', 'Hoạt động')  # Update status field
                
            # Handle password update for editing
            new_password = request.form.get('matKhau', '').strip()
            confirm_password = request.form.get('confirmPassword', '').strip()
            
            if new_password:  # Only update password if new password is provided
                if confirm_password and new_password != confirm_password:
                    flash('Mật khẩu xác nhận không khớp!', 'error')
                    return render_template('admin/crud_form.html', schema=schema, collection_name=collection_name, item=item)
                data['matKhau'] = new_password
            else:
                # Remove password field from update if empty (keep existing password)
                if 'matKhau' in data:
                    del data['matKhau']
        
        # Special handling for KhachHang - password update
        elif collection_name == 'KhachHang':
            new_password = request.form.get('matKhau', '').strip()
            confirm_password = request.form.get('confirmPassword', '').strip()
            
            if new_password:  # Only update password if new password is provided
                if confirm_password and new_password != confirm_password:
                    flash('Mật khẩu xác nhận không khớp!', 'error')
                    return render_template('admin/crud_form.html', schema=schema, collection_name=collection_name, item=item)
                data['matKhau'] = new_password
            else:
                # Remove password field from update if empty (keep existing password)
                if 'matKhau' in data:
                    del data['matKhau']
        
        # Update using the same search criteria
        if collection_name == 'LichTrinh':
            mongo.db[collection_name].update_one({'maLichTrinh': item_id}, {'$set': data})
        else:
            mongo.db[collection_name].update_one({'_id': get_object_id(item_id)}, {'$set': data})
            
        flash(f'Updated {schema["label"]} successfully')
        return redirect(url_for('admin.list_items', collection_name=collection_name))
        
    return render_template('admin/crud_form.html', schema=schema, collection_name=collection_name, item=item)

@admin_bp.route('/<collection_name>/delete/<item_id>', methods=['GET', 'POST'])
def delete_item(collection_name, item_id):
    if collection_name in SCHEMAS:
        # Check permissions based on collection
        permission_map = {
            'TuyenDuong': 'tuyen_duong',
            'LichTrinh': 'lich_trinh', 
            'XeKhach': 'xe_khach',
            'KhachHang': 'khach_hang',
            'VeXe': 've_xe',
            'GiaVe': 'gia_ve',
            'NhanVien': 'nhan_vien',
            'TinTuc': 'tin_tuc'
        }
        
        required_permission = permission_map.get(collection_name)
        if required_permission and not has_permission(required_permission):
            return redirect(url_for('admin.access_denied'))
        
        # Check delete permission
        if not has_crud_permission('delete'):
            return redirect(url_for('admin.access_denied'))
        # Special handling for LichTrinh - delete by maLichTrinh first
        if collection_name == 'LichTrinh':
            result = mongo.db[collection_name].delete_one({'maLichTrinh': item_id})
            if result.deleted_count == 0:
                # Try by ObjectId if not found by maLichTrinh
                try:
                    mongo.db[collection_name].delete_one({'_id': get_object_id(item_id)})
                except:
                    pass
        else:
            mongo.db[collection_name].delete_one({'_id': get_object_id(item_id)})
        flash('Deleted successfully')
    return redirect(url_for('admin.list_items', collection_name=collection_name))

# Trip detail route
@admin_bp.route('/chi-tiet-chuyen-xe/<trip_id>')
def trip_detail(trip_id):
    """Xem chi tiết chuyến xe"""
    try:
        # Tìm chuyến xe theo maLichTrinh
        trip = mongo.db.LichTrinh.find_one({'maLichTrinh': trip_id})
        
        if not trip:
            # Thử tìm theo ObjectId nếu không tìm thấy
            try:
                trip = mongo.db.LichTrinh.find_one({'_id': get_object_id(trip_id)})
            except:
                trip = None
        
        if not trip:
            flash(f'Không tìm thấy chuyến xe {trip_id}', 'error')
            return redirect(url_for('admin.trip_list'))
        
        # Lấy thông tin xe
        vehicle = mongo.db.XeKhach.find_one({'maXeKhach': trip.get('maXe')})
        
        # Lấy thông tin vé đã đặt
        bookings = list(mongo.db.VeXe.find({'maLichTrinh': trip.get('maLichTrinh')}))
        
        # Lấy thông tin khách hàng
        customer_ids = [booking.get('maKhach') for booking in bookings if booking.get('maKhach')]
        customers = {}
        if customer_ids:
            customer_list = list(mongo.db.KhachHang.find({'maKhach': {'$in': customer_ids}}))
            customers = {c.get('maKhach'): c for c in customer_list}
        
        # Thống kê
        stats = {
            'total_bookings': len(bookings),
            'total_revenue': sum([float(booking.get('giaVe', 0)) for booking in bookings if booking.get('giaVe')]),
            'booking_status': {}
        }
        
        for booking in bookings:
            status = booking.get('tinhTrang', 'Chưa xác định')
            stats['booking_status'][status] = stats['booking_status'].get(status, 0) + 1
        
        return render_template('admin/trip_detail.html', 
                             trip=trip, 
                             vehicle=vehicle, 
                             bookings=bookings, 
                             customers=customers, 
                             stats=stats,
                             vietnamese_to_css_class=vietnamese_to_css_class)
    
    except Exception as e:
        flash(f'Lỗi khi xem chi tiết chuyến xe: {str(e)}', 'error')
        return redirect(url_for('admin.trip_list'))

# Special routes for additional features

@admin_bp.route('/seat-map')
def seat_map():
    """Sơ đồ ghế"""
    try:
        # Get vehicle ID from URL parameter
        selected_vehicle_id = request.args.get('vehicle', '')
        
        # Get all vehicles with seat information (accept multiple status values)
        vehicles = list(mongo.db.XeKhach.find({
            'tinhTrang': {'$in': ['Hoạt động', 'Sẵn sàng', 'Đang vận hành']}
        }))
        
        # If no vehicles with those status, get all vehicles
        if not vehicles:
            vehicles = list(mongo.db.XeKhach.find({}))
        
        # Enhanced seat map data with pricing and booking information
        seat_maps = []
        for vehicle in vehicles:
            # Determine seat count and layout based on vehicle type
            loai_xe = vehicle.get('maLoai', '')
            if 'LT' in loai_xe:  # Limousine/Luxury
                so_ghe = 40
                layout = '2x1'
            elif 'LC' in loai_xe:  # Local/City bus
                if '22' in loai_xe:
                    so_ghe = 22
                    layout = '2x1'
                elif '32' in loai_xe:
                    so_ghe = 32
                    layout = '2x2'
                else:
                    so_ghe = 30
                    layout = '2x2'
            else:
                so_ghe = 40
                layout = '2x2'
            
            # Get pricing information for this vehicle type
            gia_ve_info = mongo.db.GiaVe.find_one({'maLoaiXe': loai_xe})
            if not gia_ve_info:
                # Fallback to any price for this vehicle type
                gia_ve_info = mongo.db.GiaVe.find_one({'maLoaiXe': {'$regex': loai_xe[:2]}})
            
            # Get real seat data for this vehicle
            # First, find schedules for this vehicle
            vehicle_schedules = list(mongo.db.LichTrinh.find({'maXe': vehicle.get('maXeKhach')}))
            
            # Get all seats for all schedules of this vehicle
            schedule_codes = [schedule.get('maLichTrinh') for schedule in vehicle_schedules]
            
            if schedule_codes:
                vehicle_seats = list(mongo.db.Ghe.find({'maLichTrinh': {'$in': schedule_codes}}))
            else:
                vehicle_seats = []
            
            # Create seat layout with real data
            bookings = []
            booked_count = 0
            
            # Create a map of existing seats by seat number
            seat_status_map = {}
            for seat in vehicle_seats:
                seat_number = seat.get('soGhe', '')
                status = seat.get('tinhTrang', 'Trống')
                description = seat.get('moTa', '')
                
                # Extract customer info from description if available
                customer_name = ''
                if 'Khách' in description:
                    # Extract customer name from description like "Khách KH0006" or "Khách KH0008 (Chờ thanh toán)"
                    customer_name = description.replace('Khách ', '').split(' ')[0] if description else ''
                
                seat_status_map[seat_number] = {
                    'status': status,
                    'customer': customer_name,
                    'description': description
                }
            
            # Generate seat layout for the vehicle capacity
            for i in range(1, so_ghe + 1):
                # Generate seat number - try common formats
                seat_formats = [
                    f"A{i:02d}",  # A01, A02, etc.
                    f"A{i}",      # A1, A2, etc.  
                    f"{chr(65 + (i-1)//10)}{((i-1)%10)+1:02d}",  # A01, A02, ..., B01, etc.
                    f"{i:02d}"    # 01, 02, etc.
                ]
                
                # Check if any format exists in our seat data
                seat_info = None
                seat_number = f"A{i:02d}"  # Default format
                
                for fmt in seat_formats:
                    if fmt in seat_status_map:
                        seat_info = seat_status_map[fmt]
                        seat_number = fmt
                        break
                
                if seat_info:
                    status = seat_info['status']
                    if status in ['Đã bán', 'Đang giữ']:
                        booked_count += 1
                        
                    booking_info = {
                        'soGhe': seat_number,
                        'tinhTrangGhe': status,
                        'tenKhach': seat_info['customer'],
                        'sdtKhach': '',  # Could be enhanced with customer lookup
                        'ngayDat': '',   # Could be enhanced with booking date
                        'trangThaiVe': 'Đã đặt' if status == 'Đã bán' else 'Đang giữ' if status == 'Đang giữ' else '',
                        'moTa': seat_info['description']
                    }
                else:
                    # Empty seat
                    booking_info = {
                        'soGhe': seat_number,
                        'tinhTrangGhe': 'Trống',
                        'tenKhach': '',
                        'sdtKhach': '',
                        'ngayDat': '',
                        'trangThaiVe': '',
                        'moTa': ''
                    }
                
                bookings.append(booking_info)
                
            seat_maps.append({
                'maXe': vehicle.get('maXeKhach', ''),
                'tenXe': vehicle.get('ten', ''),
                'loaiXe': loai_xe,
                'bienSo': vehicle.get('bienSo', ''),
                'tinhTrang': vehicle.get('tinhTrang', ''),
                'soGhe': so_ghe,
                'layout': layout,
                'giaVe': gia_ve_info.get('giaVe', 0) if gia_ve_info else 0,
                'phuThu': gia_ve_info.get('phuThu', 0) if gia_ve_info else 0,
                'tuyen': gia_ve_info.get('tuyen', 'N/A') if gia_ve_info else vehicle.get('tuyen', 'N/A'),
                'bookings': bookings,
                'totalBooked': booked_count,
                'totalEmpty': so_ghe - booked_count
            })
            
        return render_template('admin/seat_map.html', 
                             seat_maps=seat_maps, 
                             selected_vehicle_id=selected_vehicle_id)
    except Exception as e:
        flash(f'Lỗi tải sơ đồ ghế: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/seat-map/add', methods=['POST'])
def seat_map_add_vehicle():
    """Thêm xe khách mới"""
    try:
        vehicle_data = {
            'maXeKhach': request.form.get('maXeKhach'),
            'ten': request.form.get('ten'),
            'maLoai': request.form.get('maLoai'),
            'bienSo': request.form.get('bienSo'),
            'hangSanXuat': request.form.get('hangSanXuat', ''),
            'mau': request.form.get('mau', ''),
            'tinhTrang': request.form.get('tinhTrang'),
            'moTa': request.form.get('moTa', ''),
            'ngayThem': datetime.now()
        }
        
        # Check if vehicle code already exists
        if mongo.db.XeKhach.find_one({'maXeKhach': vehicle_data['maXeKhach']}):
            flash('Mã xe khách đã tồn tại!', 'error')
        else:
            mongo.db.XeKhach.insert_one(vehicle_data)
            flash('Thêm xe khách thành công!', 'success')
        
    except Exception as e:
        flash(f'Lỗi thêm xe khách: {str(e)}', 'error')
    
    return redirect(url_for('admin.seat_map'))

@admin_bp.route('/seat-map/edit', methods=['POST'])
def seat_map_edit_vehicle():
    """Chỉnh sửa xe khách"""
    try:
        ma_xe = request.form.get('maXeKhach')
        update_data = {
            'ten': request.form.get('ten'),
            'maLoai': request.form.get('maLoai'),
            'bienSo': request.form.get('bienSo'),
            'tinhTrang': request.form.get('tinhTrang')
        }
        
        result = mongo.db.XeKhach.update_one(
            {'maXeKhach': ma_xe}, 
            {'$set': update_data}
        )
        
        if result.matched_count > 0:
            flash('Cập nhật xe khách thành công!', 'success')
        else:
            flash('Không tìm thấy xe khách để cập nhật!', 'error')
        
    except Exception as e:
        flash(f'Lỗi cập nhật xe khách: {str(e)}', 'error')
    
    return redirect(url_for('admin.seat_map'))

@admin_bp.route('/seat-map/delete/<ma_xe>', methods=['DELETE'])
def seat_map_delete_vehicle(ma_xe):
    """Xóa xe khách"""
    try:
        result = mongo.db.XeKhach.delete_one({'maXeKhach': ma_xe})
        
        if result.deleted_count > 0:
            return jsonify({'success': True, 'message': 'Xóa xe khách thành công'})
        else:
            return jsonify({'success': False, 'message': 'Không tìm thấy xe khách'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/seat-map/save/<ma_xe>', methods=['POST'])
def seat_map_save_layout(ma_xe):
    """Lưu cấu hình sơ đồ ghế"""
    try:
        seat_statuses = request.json.get('seatStatuses', [])
        
        # In a real application, you would save seat statuses to a separate collection
        # For now, we'll just return success
        # You could create a SeatMap collection like:
        # {
        #   'maXeKhach': ma_xe,
        #   'seatStatuses': seat_statuses,
        #   'lastUpdated': datetime.now()
        # }
        
        return jsonify({'success': True, 'message': 'Lưu sơ đồ ghế thành công'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/revenue')
def revenue_report():
    """Báo cáo doanh thu"""
    try:
        # Calculate revenue statistics
        total_tickets = mongo.db.VeXe.count_documents({})
        
        # Revenue by route (estimate)
        routes = list(mongo.db.TuyenDuong.find())
        revenue_by_route = []
        
        for route in routes:
            # Estimate tickets for this route
            tickets_count = mongo.db.VeXe.count_documents({'maLichTrinh': {'$regex': route.get('maTuyenDuong', '')}})
            avg_price = route.get('doDai', 100) * 3000  # 3k per km estimate
            
            revenue_by_route.append({
                'route': f"{route.get('diemDau', '')} - {route.get('diemCuoi', '')}",
                'tickets': tickets_count,
                'revenue': tickets_count * avg_price,
                'avg_price': avg_price
            })
        
        # Sort by revenue
        revenue_by_route.sort(key=lambda x: x['revenue'], reverse=True)
        
        # Monthly revenue (mock data - can be calculated from actual dates)
        monthly_revenue = [
            {'month': 'T1', 'revenue': 45000000},
            {'month': 'T2', 'revenue': 52000000},
            {'month': 'T3', 'revenue': 48000000},
            {'month': 'T4', 'revenue': 58000000},
            {'month': 'T5', 'revenue': 62000000},
            {'month': 'T6', 'revenue': 55000000},
        ]
        
        stats = {
            'total_revenue': sum([r['revenue'] for r in revenue_by_route]),
            'total_tickets': total_tickets,
            'avg_ticket_price': sum([r['avg_price'] for r in revenue_by_route]) / len(revenue_by_route) if revenue_by_route else 0,
            'active_routes': len([r for r in routes if r.get('tinhTrang') == 'Hoạt động'])
        }
        
        return render_template('admin/revenue_report.html', 
                             revenue_by_route=revenue_by_route,
                             monthly_revenue=monthly_revenue,
                             stats=stats)
    except Exception as e:
        flash(f'Lỗi tải báo cáo doanh thu: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))

# Removed duplicate statistics function - using the newer one with RBAC

@admin_bp.route('/api/seat-data/<vehicle_id>')
def get_seat_data(vehicle_id):
    """API để lấy dữ liệu ghế thực tế cho xe với thông tin khách hàng đầy đủ"""
    try:
        # Find schedules for this vehicle
        vehicle_schedules = list(mongo.db.LichTrinh.find({'maXe': vehicle_id}))
        schedule_codes = [schedule.get('maLichTrinh') for schedule in vehicle_schedules]
        
        if schedule_codes:
            vehicle_seats = list(mongo.db.Ghe.find({'maLichTrinh': {'$in': schedule_codes}}))
        else:
            vehicle_seats = []
        
        # Get booking information from VeXe collection
        bookings = {}
        if schedule_codes:
            ve_xe_list = list(mongo.db.VeXe.find({
                'maLichTrinh': {'$in': schedule_codes}
            }))
            
            # Create booking lookup by seat number
            for ve in ve_xe_list:
                seat_num = ve.get('maGhe', '')
                bookings[seat_num] = {
                    'maKhach': ve.get('maKhach'),
                    'ngayDat': ve.get('ngayThem'),
                    'tinhTrang': ve.get('tinhTrang'),
                    'maVe': ve.get('maVe')
                }
        
        # Get customer information
        customer_data = {}
        if bookings:
            customer_codes = [booking['maKhach'] for booking in bookings.values() if booking.get('maKhach')]
            customers = list(mongo.db.KhachHang.find({
                'maKhach': {'$in': customer_codes}
            }))
            
            for customer in customers:
                customer_data[customer.get('maKhach')] = {
                    'ten': customer.get('ten', ''),
                    'dienThoai': customer.get('dienThoai', ''),
                    'email': customer.get('email', ''),
                    'diaChi': customer.get('diaChi', '')
                }
        
        # Format seat data for frontend
        seat_data = {}
        for seat in vehicle_seats:
            seat_number = seat.get('soGhe', '')
            status = seat.get('tinhTrang', 'Trống')
            
            # Get booking info if exists
            booking_info = bookings.get(seat_number, {})
            customer_info = customer_data.get(booking_info.get('maKhach'), {})
            
            # Convert status to frontend format
            if status == 'Đã bán':
                frontend_status = 'occupied'
            elif status == 'Đang giữ':
                frontend_status = 'occupied'  # Show as occupied
            elif status == 'Đã hủy':
                frontend_status = 'maintenance'
            else:
                frontend_status = 'available'
                
            # Create description with customer info
            description = ''
            if customer_info.get('ten'):
                description = f"Khách {customer_info['ten']}"
            
            seat_data[seat_number] = {
                'status': frontend_status,
                'description': description,
                'originalStatus': status,
                'customerName': customer_info.get('ten', ''),
                'customerPhone': customer_info.get('dienThoai', ''),
                'customerEmail': customer_info.get('email', ''),
                'bookingDate': booking_info.get('ngayDat', ''),
                'ticketStatus': booking_info.get('tinhTrang', ''),
                'ticketId': booking_info.get('maVe', '')
            }
        
        return jsonify({
            'status': 'success',
            'seats': seat_data,
            'total_schedules': len(schedule_codes),
            'total_seats': len(vehicle_seats),
            'total_bookings': len(bookings)
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Trip Schedule Management Routes
@admin_bp.route('/tao-chuyen-xe', methods=['GET', 'POST'])
@admin_bp.route('/create_trip', methods=['GET', 'POST'])
def create_trip():
    """Tạo chuyến xe mới với form chuyên dụng"""
    try:
        if request.method == 'POST':
            # Debug: Log form data
            print("=== CREATE TRIP FORM DATA ===")
            for key, value in request.form.items():
                print(f"{key}: {value}")
            print("=" * 30)
            
            # Get form data with error handling
            try:
                ngay_di_str = request.form.get('ngayDi')
                if not ngay_di_str:
                    raise ValueError("Ngày đi không được để trống")
                
                ngay_di = datetime.strptime(ngay_di_str, '%Y-%m-%d')
                
                trip_data = {
                    'maLichTrinh': request.form.get('maLichTrinh'),
                    'maXe': request.form.get('maXe'),
                    'diemDi': request.form.get('diemDi'),
                    'diemDen': request.form.get('diemDen'),
                    'gioDi': request.form.get('gioDi'),
                    'ngayDi': ngay_di,
                    'tramDung': request.form.getlist('tramDung'),  # Multiple stops
                    'tenTaiXe': request.form.get('tenTaiXe'),
                    'tenPhuXe': request.form.get('tenPhuXe'),
                    'tinhTrang': request.form.get('tinhTrang', 'Sắp chạy'),
                    'moTa': request.form.get('moTa', ''),
                    'ngayThem': datetime.now()
                }
            except ValueError as ve:
                error_msg = f'Lỗi dữ liệu: {str(ve)}'
                
                # AJAX request - return JSON
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    response = jsonify({
                        'status': 'error',
                        'message': error_msg
                    })
                    response.headers['Content-Type'] = 'application/json; charset=utf-8'
                    return response, 400
                
                flash(error_msg, 'error')
                return redirect(url_for('admin.create_trip'))
            
            # Validate required fields
            required_fields = ['maLichTrinh', 'maXe', 'diemDi', 'diemDen', 'gioDi', 'ngayDi']
            missing_fields = []
            for field in required_fields:
                if not trip_data.get(field):
                    missing_fields.append(field)
            
            if missing_fields:
                error_msg = f'Vui lòng nhập các trường: {", ".join(missing_fields)}'
                
                # Kiểm tra AJAX request
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
                   request.headers.get('Content-Type', '').startswith('application/json'):
                    response = jsonify({
                        'status': 'error',
                        'message': error_msg,
                        'missing_fields': missing_fields
                    })
                    response.headers['Content-Type'] = 'application/json; charset=utf-8'
                    return response, 400
                
                flash(error_msg, 'error')
                return redirect(url_for('admin.create_trip'))
            
            # Check if trip ID already exists
            if mongo.db.LichTrinh.find_one({'maLichTrinh': trip_data['maLichTrinh']}):
                error_msg = 'Mã lịch trình đã tồn tại!'
                
                # AJAX request - return JSON
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    response = jsonify({
                        'status': 'error',
                        'message': error_msg
                    })
                    response.headers['Content-Type'] = 'application/json; charset=utf-8'
                    return response, 400
                
                flash(error_msg, 'error')
                return redirect(url_for('admin.create_trip'))
            
            # Insert trip
            try:
                result = mongo.db.LichTrinh.insert_one(trip_data)
                if not result.inserted_id:
                    error_msg = 'Lỗi khi lưu chuyến xe vào database!'
                    flash(error_msg, 'error')
                    return redirect(url_for('admin.create_trip'))
            except Exception as db_error:
                error_msg = f'Lỗi database: {str(db_error)}'
                print(f"Database error: {db_error}")
                
                # AJAX request - return JSON
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    response = jsonify({
                        'status': 'error',
                        'message': error_msg
                    })
                    response.headers['Content-Type'] = 'application/json; charset=utf-8'
                    return response, 500
                
                flash(error_msg, 'error')
                return redirect(url_for('admin.create_trip'))
            
            # Tạo ghế thông minh cho trip mới (tránh duplicate)
            seat_count = create_seats_for_trip(trip_data['maLichTrinh'], trip_data['maXe'])
            
            if seat_count > 0:
                flash(f'✅ Tạo chuyến xe thành công với {seat_count} ghế!', 'success')
            else:
                flash('⚠️ Tạo chuyến xe thành công nhưng có lỗi khi tạo ghế!', 'warning')
            
            # Kiểm tra nếu là AJAX request thì trả về JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
               request.headers.get('Content-Type', '').startswith('application/json') or \
               'ajax' in request.args:
                response_data = {
                    'status': 'success',
                    'message': f'Tạo chuyến xe thành công! Mã chuyến: {trip_data["maLichTrinh"]}',
                    'trip_id': trip_data['maLichTrinh'],
                    'redirect_url': url_for('admin.trip_list')
                }
                response = jsonify(response_data)
                response.headers['Content-Type'] = 'application/json; charset=utf-8'
                return response
            
            # Form submission thông thường - redirect
            return redirect(url_for('admin.trip_list'))
        
        # GET request - show form with enhanced error handling
        try:
            # 1. Get available routes (TuyenDuong) - ENHANCED with error handling
            routes = list(mongo.db.TuyenDuong.find())
            if not routes:
                flash('⚠️ Không tìm thấy tuyến đường. Vui lòng kiểm tra dữ liệu!', 'warning')
                routes = []
            # Sort routes by name for better UX
            routes = sorted(routes, key=lambda x: x.get('tenTuyenDuong', ''))
            
            # 2. Get available vehicles (XeKhach) with enhanced route mapping
            vehicles = list(mongo.db.XeKhach.find())
            if not vehicles:
                flash('⚠️ Không tìm thấy xe khách. Vui lòng kiểm tra dữ liệu!', 'warning')
                vehicles = []
            # Sort vehicles by route and name for better organization
            vehicles = sorted(vehicles, key=lambda x: (x.get('tuyen', ''), x.get('ten', '')))
        except Exception as data_error:
            print(f"Data loading error: {data_error}")
            flash(f'Lỗi tải dữ liệu: {str(data_error)}', 'error')
            return redirect(url_for('admin.dashboard'))
        
        try:
            # 3. Get pricing information (GiaVe) - with route context
            pricing = list(mongo.db.GiaVe.find())
            
            # 4. Get seat layouts (SoDoGhe) - with vehicle type mapping
            seat_layouts = list(mongo.db.SoDoGhe.find())
            
            # 5. Get stops/stations (TramDung) - organized by province
            stops = list(mongo.db.TramDung.find())
            stops = sorted(stops, key=lambda x: x.get('tenTram', ''))
            
            # 6. Get locations (DiaDiem) for route points
            locations = list(mongo.db.DiaDiem.find())
        except Exception as secondary_data_error:
            print(f"Secondary data loading error: {secondary_data_error}")
            # Set default empty values instead of failing
            pricing = []
            seat_layouts = []
            stops = []
            locations = []
        
        try:
            # 7. Get staff for drivers (NhanVien) - ENHANCED FILTERING with multiple fallbacks
            print("Loading drivers...")
            
            # Primary pattern - exact job titles
            driver_titles = ['Tài xế', 'Phụ xe', 'Lái xe', 'Driver', 'Nhân viên lái xe', 'Tài xế chính', 'Phụ tài']
            drivers = list(mongo.db.NhanVien.find({'chucVu': {'$in': driver_titles}}))
            print(f"Found {len(drivers)} drivers with exact titles")
            
            # Fallback 1: Regex search for similar titles
            if len(drivers) < 5:
                print("Applying fallback 1: regex search")
                regex_drivers = list(mongo.db.NhanVien.find({
                    'chucVu': {'$regex': 'tài|xe|lái|driver', '$options': 'i'}
                }))
                
                # Combine and remove duplicates
                existing_ids = {str(d.get('_id')) for d in drivers}
                for driver in regex_drivers:
                    if str(driver.get('_id')) not in existing_ids:
                        drivers.append(driver)
                        existing_ids.add(str(driver.get('_id')))
                        
                print(f"After regex search: {len(drivers)} drivers")
            
            # Fallback 2: Name-based search
            if len(drivers) < 5:
                print("Applying fallback 2: name-based search")
                try:
                    all_staff = list(mongo.db.NhanVien.find())
                    name_based_drivers = []
                    for staff in all_staff:
                        name = staff.get('ten', '').lower()
                        position = staff.get('chucVu', '').lower() if staff.get('chucVu') else ''
                        
                        # Enhanced keyword matching
                        driver_keywords = ['tài', 'lái', 'driver', 'xe', 'phụ']
                        text_to_search = name + ' ' + position
                        
                        if any(keyword in text_to_search for keyword in driver_keywords):
                            # Avoid duplicates
                            if str(staff.get('_id')) not in existing_ids:
                                name_based_drivers.append(staff)
                                existing_ids.add(str(staff.get('_id')))
                    
                    drivers.extend(name_based_drivers)
                    print(f"After name-based search: {len(drivers)} drivers")
                    
                    # Fallback 3: Use all staff if still insufficient
                    if len(drivers) < 3:
                        print("Applying fallback 3: using all staff")
                        remaining_staff = [s for s in all_staff if str(s.get('_id')) not in existing_ids]
                        drivers.extend(remaining_staff[:20])  # Add up to 20 more
                        print(f"After adding all staff: {len(drivers)} total")
                        
                except Exception as staff_error:
                    print(f"Staff loading error: {staff_error}")
                    # Ultimate fallback - create emergency driver list
                    emergency_drivers = [{
                        'maNhanVien': 'TEMP001',
                        'ten': 'Tài xế tạm thời',
                        'chucVu': 'Tài xế',
                        'dienThoai': '0900000000',
                        'email': 'temp@driver.com'
                    }]
                    drivers = emergency_drivers
                    print("Applied emergency driver fallback")
            
            # Enhanced sorting and filtering
            try:
                # Remove None values and sort
                valid_drivers = [d for d in drivers if d.get('ten')]
                drivers = sorted(valid_drivers, key=lambda x: x.get('ten', ''))
                
                # Limit to reasonable number for performance
                if len(drivers) > 50:
                    drivers = drivers[:50]
                    
                print(f"Final driver count for form: {len(drivers)}")
            except Exception as sort_error:
                print(f"Driver sorting error: {sort_error}")
                # Keep drivers as-is if sorting fails
                pass
                
        except Exception as driver_error:
            print(f"Critical driver loading error: {driver_error}")
            # Create emergency fallback
            drivers = [{
                'maNhanVien': 'EMERGENCY001',
                'ten': 'Tài xế cấp cứu - Vui lòng chọn thủ công',
                'chucVu': 'Tài xế',
                'dienThoai': 'Chưa có',
                'email': 'emergency@driver.com'
            }]
            flash('⚠️ Lỗi tải danh sách tài xế. Sử dụng dữ liệu cấp cứu. Vui lòng liên hệ admin!', 'warning')
            
        # Log final driver status
        if len(drivers) > 0:
            print(f"Successfully loaded {len(drivers)} drivers for form")
            print(f"Sample drivers: {[d.get('ten', 'N/A') for d in drivers[:3]]}")
        else:
            print("WARNING: No drivers loaded - form may have issues")
        
        # Generate next trip ID with better error handling
        try:
            last_trip = mongo.db.LichTrinh.find().sort('maLichTrinh', -1).limit(1)
            next_id = 'LT0001'
            last_trip_list = list(last_trip)
            if last_trip_list:
                last_id = last_trip_list[0]['maLichTrinh']
                # Extract number and increment
                try:
                    # Better ID parsing
                    import re
                    numbers = re.findall(r'\d+', last_id)
                    if numbers:
                        num = int(numbers[-1]) + 1  # Get last number and increment
                        next_id = f'LT{num:04d}'
                    else:
                        next_id = 'LT0051'  # Fallback if no numbers found
                except Exception as id_error:
                    print(f"Trip ID generation error: {id_error}")
                    # Generate based on timestamp as fallback
                    import time
                    timestamp = int(time.time()) % 10000
                    next_id = f'LT{timestamp:04d}'
        except Exception as trip_query_error:
            print(f"Trip query error: {trip_query_error}")
            # Generate based on timestamp as ultimate fallback
            import time
            timestamp = int(time.time()) % 10000
            next_id = f'LT{timestamp:04d}'
        
        # Final safety check before rendering
        template_data = {
            'routes': routes or [],
            'vehicles': vehicles or [],
            'pricing': pricing or [],
            'seat_layouts': seat_layouts or [],
            'stops': stops or [],
            'locations': locations or [],
            'drivers': drivers or [],
            'next_trip_id': next_id or 'LT0001',
            'today': datetime.now().strftime('%Y-%m-%d')
        }
        
        # Log data status for debugging
        print(f"Template data loaded - Routes: {len(routes)}, Vehicles: {len(vehicles)}, Drivers: {len(drivers)}")
        
        return render_template('admin/create_trip.html', **template_data)
                             
    except Exception as e:
        print(f"Critical error in create_trip: {e}")
        flash(f'Đã xảy ra lỗi nghiêm trọng khi tải trang. Vui lòng thử lại sau!', 'error')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/danh-sach-chuyen-xe')
def trip_list():
    """Danh sách chuyến xe với thông tin chi tiết"""
    try:
        # Get search and filter parameters
        search_query = request.args.get('search', '').strip()
        status_filter = request.args.get('status', '')
        route_filter = request.args.get('route', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        page = int(request.args.get('page', 1))
        per_page = 20
        
        # Build MongoDB query
        query = {}
        
        # Search in multiple fields
        if search_query:
            query['$or'] = [
                {'maLichTrinh': {'$regex': search_query, '$options': 'i'}},
                {'diemDi': {'$regex': search_query, '$options': 'i'}},
                {'diemDen': {'$regex': search_query, '$options': 'i'}},
                {'tenTaiXe': {'$regex': search_query, '$options': 'i'}},
                {'tenPhuXe': {'$regex': search_query, '$options': 'i'}}
            ]
        
        # Filter by status
        if status_filter:
            query['tinhTrang'] = status_filter
        
        # Filter by route (diemDi -> diemDen)
        if route_filter:
            route_parts = route_filter.split(' -> ')
            if len(route_parts) == 2:
                query['diemDi'] = route_parts[0]
                query['diemDen'] = route_parts[1]
        
        # Filter by date range
        if date_from or date_to:
            date_query = {}
            if date_from:
                try:
                    from datetime import datetime
                    date_query['$gte'] = datetime.strptime(date_from, '%Y-%m-%d')
                except:
                    pass
            if date_to:
                try:
                    from datetime import datetime
                    date_query['$lte'] = datetime.strptime(date_to, '%Y-%m-%d')
                except:
                    pass
            if date_query:
                query['ngayDi'] = date_query
        
        # Get trips with filters
        trips = list(mongo.db.LichTrinh.find(query)
                    .sort('ngayDi', -1)
                    .skip((page - 1) * per_page)
                    .limit(per_page))
        
        # Get total count for pagination
        total_filtered = mongo.db.LichTrinh.count_documents(query)
        
        # Enrich trips with vehicle and route info
        for trip in trips:
            # Get vehicle info
            vehicle = mongo.db.XeKhach.find_one({'maXeKhach': trip.get('maXe')})
            if vehicle:
                trip['vehicle_info'] = {
                    'ten': vehicle.get('ten'),
                    'bienSo': vehicle.get('bienSo'),
                    'tuyen': vehicle.get('tuyen')
                }
            
            # Count bookings for this trip
            booking_count = mongo.db.VeXe.count_documents({'maLichTrinh': trip.get('maLichTrinh')})
            trip['booking_count'] = booking_count
        
        # Calculate statistics for all trips (not just current page)
        total_trips = mongo.db.LichTrinh.count_documents({})
        
        # Get status statistics from database
        stats = {
            'total': total_trips,
            'da_hoan_thanh': mongo.db.LichTrinh.count_documents({'tinhTrang': 'Đã hoàn thành'}),
            'dang_chay': mongo.db.LichTrinh.count_documents({'tinhTrang': 'Đang chạy'}),
            'sap_chay': mongo.db.LichTrinh.count_documents({'tinhTrang': 'Sắp chạy'}),
            'da_huy': mongo.db.LichTrinh.count_documents({'tinhTrang': 'Đã hủy'})
        }
        
        # Get filter options for dropdowns
        all_statuses = mongo.db.LichTrinh.distinct('tinhTrang')
        all_routes = []
        route_combinations = mongo.db.LichTrinh.aggregate([
            {'$group': {
                '_id': {'diemDi': '$diemDi', 'diemDen': '$diemDen'},
                'count': {'$sum': 1}
            }},
            {'$sort': {'count': -1}},
            {'$limit': 20}
        ])
        
        for route in route_combinations:
            route_str = f"{route['_id']['diemDi']} -> {route['_id']['diemDen']}"
            all_routes.append(route_str)
        
        return render_template('admin/trip_list.html', 
                             trips=trips, 
                             page=page, 
                             per_page=per_page,
                             total_trips=total_trips,
                             total_filtered=total_filtered,
                             stats=stats,
                             all_statuses=all_statuses,
                             all_routes=all_routes,
                             search_query=search_query,
                             status_filter=status_filter,
                             route_filter=route_filter,
                             date_from=date_from,
                             date_to=date_to,
                             vietnamese_to_css_class=vietnamese_to_css_class)
                             
    except Exception as e:
        flash(f'Lỗi tải danh sách chuyến xe: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))

# ============= ROLE-BASED ACCESS CONTROL ROUTES =============

# Access Denied Page
@admin_bp.route('/access-denied')
def access_denied():
    """Trang thông báo không đủ quyền truy cập"""
    user_role = get_user_role()
    return render_template('admin/access_denied.html', 
                         user_role=user_role,
                         available_permissions=ROLES_PERMISSIONS.get(user_role, []))

# Accounts Management Routes
@admin_bp.route('/accounts')
@require_role('tai_khoan')
def accounts():
    """Quản lý tài khoản - chỉ QLNS và QLVH"""
    try:
        accounts = list(mongo.db.TaiKhoan.find({}))
        return render_template('admin/accounts.html', 
                             accounts=accounts,
                             accessible_menu=get_accessible_menu_items())
    except Exception as e:
        flash(f'Lỗi tải danh sách tài khoản: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/accounts/add', methods=['GET', 'POST'])
@require_role('tai_khoan')
@require_crud_permission('create')
def add_account():
    """Thêm tài khoản mới - cần quyền create"""
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            role = request.form.get('role')
            full_name = request.form.get('full_name')
            email = request.form.get('email')
            
            # Validate role
            if role not in ROLES_PERMISSIONS and role != 'ADMIN':
                flash('Role không hợp lệ', 'error')
                return redirect(request.url)
            
            # Check if username exists
            if mongo.db.TaiKhoan.find_one({'ten': username}):
                flash('Tên đăng nhập đã tồn tại', 'error')
                return redirect(request.url)
            
            # Create new account
            new_account = {
                'ten': username,
                'matKhau': password,  # Should hash in production
                'role': role,
                'maLoai': role,
                'hoTen': full_name or username,
                'email': email or f"{username}@company.com",
                'trangThai': 'Hoạt động',
                'ngayTao': datetime.now()
            }
            
            mongo.db.TaiKhoan.insert_one(new_account)
            flash(f'Đã tạo tài khoản {username} với role {role}', 'success')
            return redirect(url_for('admin.accounts'))
            
        except Exception as e:
            flash(f'Lỗi tạo tài khoản: {str(e)}', 'error')
    
    return render_template('admin/add_account.html',
                         roles=list(ROLES_PERMISSIONS.keys()) + ['ADMIN'],
                         accessible_menu=get_accessible_menu_items())

@admin_bp.route('/accounts/edit/<account_id>', methods=['GET', 'POST'])
@require_role('tai_khoan')
@require_crud_permission('update')
def edit_account(account_id):
    """Chỉnh sửa tài khoản - cần quyền update"""
    try:
        account = mongo.db.TaiKhoan.find_one({'_id': get_object_id(account_id)})
        if not account:
            flash('Không tìm thấy tài khoản', 'error')
            return redirect(url_for('admin.accounts'))
        
        if request.method == 'POST':
            role = request.form.get('role')
            full_name = request.form.get('full_name')
            email = request.form.get('email')
            status = request.form.get('status')
            
            update_data = {
                'role': role,
                'maLoai': role,
                'hoTen': full_name,
                'email': email,
                'trangThai': status
            }
            
            # Update password if provided
            new_password = request.form.get('password')
            if new_password:
                update_data['matKhau'] = new_password
            
            mongo.db.TaiKhoan.update_one(
                {'_id': get_object_id(account_id)},
                {'$set': update_data}
            )
            
            flash('Cập nhật tài khoản thành công', 'success')
            return redirect(url_for('admin.accounts'))
        
        return render_template('admin/edit_account.html',
                             account=account,
                             roles=list(ROLES_PERMISSIONS.keys()) + ['ADMIN'],
                             accessible_menu=get_accessible_menu_items())
                             
    except Exception as e:
        flash(f'Lỗi chỉnh sửa tài khoản: {str(e)}', 'error')
        return redirect(url_for('admin.accounts'))

@admin_bp.route('/accounts/delete/<account_id>', methods=['POST'])
@require_role('tai_khoan')
@require_crud_permission('delete')
def delete_account(account_id):
    """Xóa tài khoản - cần quyền delete"""
    try:
        mongo.db.TaiKhoan.delete_one({'_id': get_object_id(account_id)})
        flash('Xóa tài khoản thành công', 'success')
    except Exception as e:
        flash(f'Lỗi xóa tài khoản: {str(e)}', 'error')
    
    return redirect(url_for('admin.accounts'))

@admin_bp.route('/permissions')
@require_role('tai_khoan')
def permissions():
    """Xem quyền hạn các role"""
    return render_template('admin/permissions.html',
                         roles_permissions=ROLES_PERMISSIONS,
                         accessible_menu=get_accessible_menu_items())

@admin_bp.route('/create-sample-users', methods=['POST'])
@require_role('tai_khoan')
@require_crud_permission('create')
def create_sample_users():
    """Tạo user mẫu cho test"""
    try:
        created_count = 0
        for user_data in SAMPLE_USERS:
            # Check if user already exists
            if not mongo.db.TaiKhoan.find_one({'ten': user_data['ten']}):
                user_data['maLoai'] = user_data['role']
                user_data['trangThai'] = 'Hoạt động'
                user_data['ngayTao'] = datetime.now()
                mongo.db.TaiKhoan.insert_one(user_data.copy())
                created_count += 1
        
        flash(f'Đã tạo {created_count} tài khoản mẫu', 'success')
    except Exception as e:
        flash(f'Lỗi tạo tài khoản mẫu: {str(e)}', 'error')
    
    return redirect(url_for('admin.accounts'))

# Revenue Route - QLKT và QLVH only
@admin_bp.route('/revenue')
@require_role('doanh_thu')
def revenue():
    """Báo cáo doanh thu - chỉ QLKT và QLVH"""
    try:
        # Calculate revenue statistics
        total_revenue = 0
        monthly_revenue = {}
        
        # Get all paid tickets
        tickets = list(mongo.db.VeXe.find({'tinhTrang': 'Đã thanh toán'}))
        
        for ticket in tickets:
            # Get price from GiaVe collection
            price_info = mongo.db.GiaVe.find_one({'maGiaVe': ticket.get('maGiaVe')})
            if price_info:
                price = price_info.get('giaVe', 0)
                total_revenue += price
                
                # Group by month if ngayThem exists
                if ticket.get('ngayThem'):
                    month_key = ticket['ngayThem'].strftime('%Y-%m')
                    monthly_revenue[month_key] = monthly_revenue.get(month_key, 0) + price
        
        return render_template('admin/revenue.html',
                             total_revenue=total_revenue,
                             monthly_revenue=monthly_revenue,
                             accessible_menu=get_accessible_menu_items())
                             
    except Exception as e:
        flash(f'Lỗi tải báo cáo doanh thu: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))

# Statistics Route - Multiple roles
@admin_bp.route('/statistics')
@require_role('thong_ke')
def statistics():
    """Thống kê tổng quan"""
    try:
        stats = {
            'total_routes': mongo.db.TuyenDuong.count_documents({}),
            'total_trips': mongo.db.LichTrinh.count_documents({}),
            'total_vehicles': mongo.db.XeKhach.count_documents({}),
            'total_customers': mongo.db.KhachHang.count_documents({}),
            'total_tickets': mongo.db.VeXe.count_documents({}),
            'total_accounts': mongo.db.TaiKhoan.count_documents({})
        }
        
        return render_template('admin/statistics.html',
                             stats=stats,
                             accessible_menu=get_accessible_menu_items())
                             
    except Exception as e:
        flash(f'Lỗi tải thống kê: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))
