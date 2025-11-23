from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from app import mongo
from app.utils import parse_json, get_object_id
from datetime import datetime, timedelta
from bson import ObjectId

user_bp = Blueprint('user', __name__)

@user_bp.route('/')
def index():
    # Chỉ lấy các trường cần thiết và giới hạn số lượng để tăng tốc độ
    tuyen_duong = list(mongo.db.TuyenDuong.find(
        {}, 
        {'maTuyenDuong': 1, 'tenTuyenDuong': 1, 'diemDau': 1, 'diemCuoi': 1}
    ).limit(20))  # Giới hạn 20 tuyến phổ biến
    
    tin_tuc = list(mongo.db.TinTuc.find(
        {}, 
        {'maTinTuc': 1, 'tieuDe': 1, 'noiDung': 1, 'ngayDang': 1}
    ).sort('ngayDang', -1).limit(3))  # 3 tin mới nhất
    
    # Lấy danh sách các trạm để hiển thị trong dropdown
    stations = set()
    for td in tuyen_duong:
        stations.add(td.get('diemDau'))
        stations.add(td.get('diemCuoi'))
    
    stations_list = sorted(list(stations))
    
    return render_template('user/index.html', 
                          tuyen_duong=tuyen_duong, 
                          tin_tuc=tin_tuc,
                          stations=stations_list)

@user_bp.route('/api/available-dates')
def get_available_dates():
    """API để lấy ngày có chuyến đi và giá vé cho Flatpickr"""
    try:
        diem_di = request.args.get('diem_di') or request.args.get('from_location')
        diem_den = request.args.get('diem_den') or request.args.get('to_location')
        
        # Nếu có specific route request
        if diem_di and diem_den:
            # Tìm tuyến đường phù hợp
            tuyen_query = {
                '$or': [
                    {'diemDau': diem_di, 'diemCuoi': diem_den},
                    {'maTuyenDuong': f'{diem_di}-{diem_den}'}
                ]
            }
            tuyen_duong = mongo.db.TuyenDuong.find_one(tuyen_query)
            
            if not tuyen_duong:
                return jsonify({'dates': [], 'message': 'Không tìm thấy tuyến đường'})
                
            # Tìm lịch trình có điểm đi/đến phù hợp
            lich_trinh_query = {
                '$or': [
                    {'diemDi': tuyen_duong.get('diemDau'), 'diemDen': tuyen_duong.get('diemCuoi')},
                    {'diemDi': diem_di, 'diemDen': diem_den}
                ],
                'tinhTrang': {'$in': ['Sắp chạy', 'Đang chạy']},
                'ngayDi': {'$gte': datetime.now()}
            }
            
            lich_trinh_list = list(mongo.db.LichTrinh.find(lich_trinh_query))
            
            # Tìm giá vé cho tuyến này
            gia_ve = mongo.db.GiaVe.find_one({
                'tuyen': tuyen_duong.get('maTuyenDuong'),
                'tinhTrang': 'Hoạt động'
            })
            
            base_price = gia_ve.get('giaVe', 0) if gia_ve else 0
            
            # Format dữ liệu cho Flatpickr
            available_dates = []
            for lt in lich_trinh_list:
                date_str = lt['ngayDi'].strftime('%Y-%m-%d')
                available_dates.append({
                    'date': date_str,
                    'price': base_price,
                    'time': lt.get('gioDi', ''),
                    'trip_id': lt.get('maLichTrinh'),
                    'status': lt.get('tinhTrang')
                })
                
            return jsonify({
                'dates': available_dates,
                'route': tuyen_duong.get('tenTuyenDuong'),
                'base_price': base_price
            })
            
        else:
            # Return all available routes with dates and prices
            routes_data = []
            
            # Get all active trips in future với logic trạng thái chính xác
            current_time = datetime.now()
            today = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            
            lich_trinh_list = list(mongo.db.LichTrinh.find({
                '$and': [
                    {'ngayDi': {'$gte': today}},
                    {'$or': [
                        {'ngayDi': {'$gte': today, '$lt': today + timedelta(days=1)}, 'tinhTrang': 'Đang chạy'},
                        {'ngayDi': {'$gte': today + timedelta(days=1)}, 'tinhTrang': 'Sắp chạy'}
                    ]}
                ]
            }))
            
            # Group by route
            route_map = {}
            for lt in lich_trinh_list:
                route_key = f"{lt.get('diemDi')}-{lt.get('diemDen')}"
                date_str = lt['ngayDi'].strftime('%Y-%m-%d')
                
                if route_key not in route_map:
                    # Find price for this route
                    gia_ve = mongo.db.GiaVe.find_one({
                        '$or': [
                            {'tuyen': route_key},
                            {'maTuyenDuong': route_key}
                        ]
                    })
                    price = gia_ve.get('giaVe', 180000) if gia_ve else 180000
                    
                    route_map[route_key] = {
                        'from': lt.get('diemDi'),
                        'to': lt.get('diemDen'), 
                        'price': price,
                        'dates': []
                    }
                
                route_map[route_key]['dates'].append(date_str)
            
            # Convert to list format
            for route_info in route_map.values():
                route_info['dates'] = sorted(list(set(route_info['dates'])))  # Remove duplicates and sort
                routes_data.append(route_info)
            
            return jsonify({
                'status': 'success',
                'routes': routes_data
            })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@user_bp.route('/search')
def search():
    diem_di = request.args.get('diem_di')
    diem_den = request.args.get('diem_den')
    ngay_di = request.args.get('ngay_di')
    so_khach = request.args.get('so_khach', '1')
    
    if not diem_di or not diem_den:
        flash('Vui lòng chọn điểm đi và điểm đến')
        return redirect(url_for('user.index'))
        
    # Build search query với logic đúng - chỉ lấy chuyến khả dụng
    current_time = datetime.now()
    today = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
    
    query = {
        '$and': [
            # Chỉ lấy chuyến từ hôm nay trở đi
            {'ngayDi': {'$gte': today}},
            # Trạng thái phù hợp theo ngày
            {'$or': [
                {'ngayDi': {'$gte': today, '$lt': today + timedelta(days=1)}, 'tinhTrang': 'Đang chạy'},
                {'ngayDi': {'$gte': today + timedelta(days=1)}, 'tinhTrang': 'Sắp chạy'}
            ]}
        ]
    }
    
    # Tìm theo tuyến đường trước
    tuyen_query = {
        '$or': [
            {'diemDau': diem_di, 'diemCuoi': diem_den},
            {'maTuyenDuong': f'{diem_di}-{diem_den}'}
        ]
    }
    tuyen_duong = mongo.db.TuyenDuong.find_one(tuyen_query)
    
    if tuyen_duong:
        query['$or'] = [
            {'diemDi': tuyen_duong.get('diemDau'), 'diemDen': tuyen_duong.get('diemCuoi')},
            {'diemDi': diem_di, 'diemDen': diem_den}
        ]
    else:
        query['diemDi'] = diem_di
        query['diemDen'] = diem_den
    
    # Filter theo ngày nếu có
    if ngay_di:
        try:
            ngay_obj = datetime.strptime(ngay_di, '%Y-%m-%d')
            query['ngayDi'] = {
                '$gte': ngay_obj,
                '$lt': ngay_obj.replace(hour=23, minute=59, second=59)
            }
        except:
            pass
            
    lich_trinh = list(mongo.db.LichTrinh.find(query).sort('ngayDi', 1))
    
    # Enrich data với thông tin xe và giá vé
    for lt in lich_trinh:
        # Thông tin xe
        xe = mongo.db.XeKhach.find_one({'maXeKhach': lt.get('maXe')})
        lt['xe_info'] = xe if xe else {}
        
        # Tuyến đường
        if tuyen_duong:
            lt['tuyen_duong'] = tuyen_duong
            lt['tenTuyenDuong'] = tuyen_duong.get('tenTuyenDuong')
        else:
            lt['tenTuyenDuong'] = f"{lt.get('diemDi')} → {lt.get('diemDen')}"
            
        # Giá vé
        gia_ve = mongo.db.GiaVe.find_one({
            'tuyen': tuyen_duong.get('maTuyenDuong') if tuyen_duong else f"{diem_di}-{diem_den}",
            'tinhTrang': 'Hoạt động'
        })
        lt['gia_ve'] = gia_ve.get('giaVe', 0) if gia_ve else 0
        
        # Số ghế còn trống - FIXED: dùng maLichTrinh thay vì maXe
        booked_seats = mongo.db.VeXe.count_documents({'maLichTrinh': lt.get('maLichTrinh')})
        total_seats = mongo.db.Ghe.count_documents({'maLichTrinh': lt.get('maLichTrinh')})  # FIX: theo trip, không phải xe
        lt['ghe_trong'] = max(0, total_seats - booked_seats)
        
        # Debug log
        if lt.get('maLichTrinh', '').startswith('TEST_TRIP'):
            print(f"Trip {lt.get('maLichTrinh')}: {total_seats} total seats, {booked_seats} booked, {lt['ghe_trong']} available")
        
    return render_template('user/search_results.html', 
                          lich_trinh=lich_trinh,
                          search_params={
                              'diem_di': diem_di,
                              'diem_den': diem_den, 
                              'ngay_di': ngay_di,
                              'so_khach': so_khach
                          })

@user_bp.route('/booking-demo')
def booking_demo():
    """Demo route to test new seat design"""
    # Create dummy data for demo
    demo_xe = {
        'bienSo': 'X001-Demo',
        'ten': 'Xe Demo 45 chỗ',
        'maLoaiXe': 'LX001'
    }
    
    demo_lt = {
        'maLichTrinh': 'LT-DEMO',
        'diemDi': 'TP.HCM', 
        'diemDen': 'Đà Lạt',
        'gioDi': '08:00',
        'ngayDi': '2024-11-25'
    }
    
    return render_template('user/booking.html', xe=demo_xe, lich_trinh=demo_lt)

@user_bp.route('/booking/<lich_trinh_id>')
def booking(lich_trinh_id):
    # Try finding by maLichTrinh first, then by ObjectId
    lt = mongo.db.LichTrinh.find_one({'maLichTrinh': lich_trinh_id})
    if not lt:
        # Fallback to ObjectId lookup for backward compatibility
        try:
            lt = mongo.db.LichTrinh.find_one({'_id': get_object_id(lich_trinh_id)})
        except:
            pass
    
    if not lt:
        flash('Lịch trình không tồn tại')
        return redirect(url_for('user.index'))
        
    xe = mongo.db.XeKhach.find_one({'maXeKhach': lt.get('maXe')})
    if not xe:
        flash('Không tìm thấy thông tin xe')
        return redirect(url_for('user.index'))
    
    # Find route information
    tuyen_duong = mongo.db.TuyenDuong.find_one({'_id': ObjectId(lt.get('maTuyen'))})
    
    # Find seats for this trip using maLichTrinh - FIXED SCHEMA
    ghe_list = list(mongo.db.Ghe.find({'maLichTrinh': lt['maLichTrinh']}))
    
    # Find booked seats for this lich trinh
    booked_tickets = list(mongo.db.VeXe.find({'maLichTrinh': lt['maLichTrinh']}))
    
    # Debug log
    print(f"Booking for trip {lt['maLichTrinh']}: Found {len(ghe_list)} seats, {len(booked_tickets)} bookings")
    booked_seat_ids = [t.get('maGhe') for t in booked_tickets]

    for ghe in ghe_list:
        ghe['is_booked'] = ghe.get('maGhe') in booked_seat_ids
    
    # Calculate available seats
    total_seats = len(ghe_list)
    booked_seats_count = len(booked_tickets)
    available_seats = total_seats - booked_seats_count
    
    # Get vehicle type info
    loai_xe = mongo.db.LoaiXe.find_one({'maLoaiXe': xe.get('maLoai', xe.get('loaiXe'))})
    
    # Get price information from GiaVe table
    gia_ve = None
    vehicle_type = xe.get('maLoai', xe.get('loaiXe'))
    
    # First try to find price by route + vehicle type
    if tuyen_duong:
        route_code = tuyen_duong.get('maTuyenDuong')
        # Try different route patterns
        route_patterns = [route_code, f"{lt.get('diemDi')}-{lt.get('diemDen')}", 'VPQ1-VPDL']
        
        for pattern in route_patterns:
            gia_ve = mongo.db.GiaVe.find_one({
                'tuyen': pattern,
                'maLoaiXe': vehicle_type
            })
            if gia_ve:
                break
    
    # If no route-specific price, find by vehicle type with preference for 450,000 for VIP30
    if not gia_ve:
        if vehicle_type == 'VIP30':
            # For VIP30, prefer 450,000 price
            gia_ve = mongo.db.GiaVe.find_one({
                'maLoaiXe': vehicle_type,
                'giaVe': 450000
            })
        
        # If still no specific price found, get any price for this vehicle type
        if not gia_ve:
            gia_ve = mongo.db.GiaVe.find_one({
                'maLoaiXe': vehicle_type
            })
    
    # Set price from giaVe column
    if gia_ve:
        lt['giaVe'] = gia_ve.get('giaVe', 0)
    else:
        # Default price if no price found
        lt['giaVe'] = 290000
    
    # Calculate travel time (estimate based on route)
    if tuyen_duong:
        do_dai = tuyen_duong.get('doDai', 0)
        # Estimate time based on distance (average 60km/h)
        thoi_gian_di = f"{int(do_dai/60)} giờ {int((do_dai%60)*60/60)} phút" if do_dai > 0 else "8 giờ"
        lt['thoiGianDi'] = thoi_gian_di
    
    # Add vehicle info
    xe['soGhe'] = available_seats
    xe['ten'] = loai_xe.get('tenLoaiXe', 'Limousine') if loai_xe else 'Limousine'
        
    return render_template('user/booking.html', 
                          lich_trinh=lt, 
                          xe=xe, 
                          ghe_list=ghe_list,
                          tuyen_duong=tuyen_duong,
                          available_seats=available_seats,
                          total_seats=total_seats)

@user_bp.route('/profile')
def profile():
    """Trang thông tin cá nhân khách hàng"""
    if 'customer_id' not in session:
        flash('Vui lòng đăng nhập để xem thông tin cá nhân', 'warning')
        return redirect(url_for('auth.login'))
    
    # Lấy thông tin khách hàng
    customer = mongo.db.KhachHang.find_one({'_id': get_object_id(session['customer_id'])})
    if not customer:
        flash('Không tìm thấy thông tin khách hàng', 'error')
        return redirect(url_for('user.index'))
    
    return render_template('user/profile.html', customer=customer, datetime=datetime)

@user_bp.route('/my-tickets')
def my_tickets():
    """Trang vé đã đặt của khách hàng"""
    if 'customer_id' not in session:
        flash('Vui lòng đăng nhập để xem vé đã đặt', 'warning')
        return redirect(url_for('auth.login'))
    
    customer = mongo.db.KhachHang.find_one({'_id': get_object_id(session['customer_id'])})
    if not customer:
        flash('Không tìm thấy thông tin khách hàng', 'error')
        return redirect(url_for('user.index'))
    
    # Lấy danh sách vé đã đặt - support cả schema cũ và mới
    customer_id_str = str(session['customer_id'])
    customer_ma_khach = customer.get('maKhach')
    
    # Tìm vé theo cả 2 cách: maKhach (string) và maKhachHang (ObjectId)
    query = {'$or': []}
    if customer_ma_khach:
        query['$or'].append({'maKhach': customer_ma_khach})
    query['$or'].append({'maKhachHang': customer_id_str})
    query['$or'].append({'maKhachHang': get_object_id(customer_id_str)})
    
    tickets = list(mongo.db.VeXe.find(query).sort([('ngayThem', -1), ('ngayDat', -1)]))
    
    # Enrich với thông tin lịch trình và xe
    for ticket in tickets:
        # Thông tin lịch trình
        lt = mongo.db.LichTrinh.find_one({'maLichTrinh': ticket.get('maLichTrinh')})
        if lt:
            ticket['lich_trinh'] = lt
            
            # Thông tin xe
            xe = mongo.db.XeKhach.find_one({'maXeKhach': lt.get('maXe')})
            ticket['xe_info'] = xe if xe else {}
        
        # Thông tin ghế
        ghe = mongo.db.Ghe.find_one({'maGhe': ticket.get('maGhe')})
        ticket['ghe_info'] = ghe if ghe else {}
        
        # Thông tin giá vé
        gia_ve = mongo.db.GiaVe.find_one({'maGiaVe': ticket.get('maGiaVe')})
        ticket['gia_ve_info'] = gia_ve if gia_ve else {}
    
    return render_template('user/my_tickets.html', tickets=tickets, customer=customer)

@user_bp.route('/trip-history')
def trip_history():
    """Lịch sử chuyến đi của khách hàng"""
    if 'customer_id' not in session:
        flash('Vui lòng đăng nhập để xem lịch sử chuyến đi', 'warning')
        return redirect(url_for('auth.login'))
    
    customer = mongo.db.KhachHang.find_one({'_id': get_object_id(session['customer_id'])})
    if not customer:
        flash('Không tìm thấy thông tin khách hàng', 'error')
        return redirect(url_for('user.index'))
    
    # Lấy lịch sử chuyến đi (vé đã hoàn thành) - support cả schema cũ và mới
    customer_id_str = str(session['customer_id'])
    customer_ma_khach = customer.get('maKhach')
    
    # Tìm vé hoàn thành theo cả 2 schema
    customer_query = []
    if customer_ma_khach:
        customer_query.append({'maKhach': customer_ma_khach})
    customer_query.append({'maKhachHang': customer_id_str})
    
    query = {
        '$and': [
            {'$or': customer_query},
            {'$or': [
                {'tinhTrang': {'$in': ['Đã thanh toán', 'Đã hoàn thành']}},
                {'trangThai': {'$in': ['DaDat', 'DaThanhToan']}}
            ]}
        ]
    }
    
    history_tickets = list(mongo.db.VeXe.find(query).sort([('ngayThem', -1), ('ngayDat', -1)]))
    
    # Enrich với thông tin chi tiết
    for ticket in history_tickets:
        lt = mongo.db.LichTrinh.find_one({'maLichTrinh': ticket.get('maLichTrinh')})
        if lt:
            ticket['lich_trinh'] = lt
            xe = mongo.db.XeKhach.find_one({'maXeKhach': lt.get('maXe')})
            ticket['xe_info'] = xe if xe else {}
        
        ghe = mongo.db.Ghe.find_one({'maGhe': ticket.get('maGhe')})
        ticket['ghe_info'] = ghe if ghe else {}
    
    return render_template('user/trip_history.html', history_tickets=history_tickets, customer=customer)

@user_bp.route('/profile/update', methods=['POST'])
def update_profile():
    """Cập nhật thông tin cá nhân khách hàng"""
    if 'customer_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        update_data = {
            'ten': request.form.get('ten'),
            'dienThoai': request.form.get('dienThoai'),
            'email': request.form.get('email'),
            'diaChi': request.form.get('diaChi'),
            'soCmnd': request.form.get('soCmnd')
        }
        
        # Remove empty fields
        update_data = {k: v for k, v in update_data.items() if v}
        
        if update_data:
            mongo.db.KhachHang.update_one(
                {'_id': get_object_id(session['customer_id'])},
                {'$set': update_data}
            )
            flash('Cập nhật thông tin thành công!', 'success')
        
        return redirect(url_for('user.profile'))
        
    except Exception as e:
        flash(f'Lỗi cập nhật thông tin: {str(e)}', 'error')
        return redirect(url_for('user.profile'))

@user_bp.route('/api/seats/<lich_trinh_id>')
def get_seats_api(lich_trinh_id):
    """API để lấy thông tin ghế cho seat map - sử dụng sơ đồ từ SoDoGhe"""
    try:
        # Tìm lịch trình
        lt = mongo.db.LichTrinh.find_one({'_id': get_object_id(lich_trinh_id)})
        if not lt:
            return jsonify({'error': 'Lịch trình không tồn tại'}), 404
        
        # Tìm thông tin xe (optional)
        xe = mongo.db.XeKhach.find_one({'maXeKhach': lt.get('maXe')})
        
        # Tìm sơ đồ ghế theo loại xe hoặc default
        if xe and xe.get('maLoai'):
            loai_xe = xe.get('maLoai')
            seat_layout = mongo.db.SoDoGhe.find_one({'maLoaiXe': loai_xe})
        else:
            # Nếu không tìm thấy xe hoặc loại xe, dùng layout mặc định
            seat_layout = None
        
        if not seat_layout or not seat_layout.get('danhSachGhe'):
            # Fallback to 40-seat layout
            seat_layout = mongo.db.SoDoGhe.find_one({'maSoDo': 'SD_LT40'})
        
        if not seat_layout:
            return jsonify({'error': 'Không tìm thấy sơ đồ ghế'}), 404
        
        # Lấy danh sách vé đã đặt
        booked_tickets = list(mongo.db.VeXe.find({'maLichTrinh': lt['maLichTrinh']}))
        booked_seat_numbers = [t.get('maGhe') for t in booked_tickets]
        
        # Lấy thông tin khách hàng đã đặt
        customer_info = {}
        for ticket in booked_tickets:
            # Support both old and new customer schemas
            customer = None
            if ticket.get('maKhach'):
                customer = mongo.db.KhachHang.find_one({'maKhach': ticket.get('maKhach')})
            elif ticket.get('maKhachHang'):
                customer = mongo.db.KhachHang.find_one({'_id': get_object_id(ticket.get('maKhachHang'))})
            
            if customer:
                customer_info[ticket.get('maGhe')] = {
                    'customerName': customer.get('ten', 'N/A'),
                    'customerPhone': customer.get('dienThoai', 'N/A'),
                    'bookingDate': (ticket.get('ngayThem') or ticket.get('ngayDat') or datetime.now()).strftime('%Y-%m-%d'),
                    'ticketStatus': ticket.get('tinhTrang') or ticket.get('trangThai', 'Chưa xác định')
                }
        
        # Tạo seat map từ sơ đồ thực
        seat_map = {}
        danh_sach_ghe = seat_layout.get('danhSachGhe', [])
        
        for seat_info in danh_sach_ghe:
            seat_number = seat_info.get('soGhe')
            seat_type = seat_info.get('loaiGhe', 'Ghe')
            seat_floor = int(seat_info.get('tang', 1))
            
            if seat_number in booked_seat_numbers:
                seat_map[seat_number] = {
                    'status': 'occupied',
                    'seatType': seat_type,
                    'floor': seat_floor,
                    **customer_info.get(seat_number, {})
                }
            else:
                seat_map[seat_number] = {
                    'status': 'available',
                    'seatType': seat_type,
                    'floor': seat_floor
                }
        
        return jsonify({
            'status': 'success',
            'seats': seat_map,
            'layout_info': {
                'name': seat_layout.get('tenSoDo'),
                'code': seat_layout.get('maSoDo'),
                'floors': int(seat_layout.get('soTang', 1)),
                'total_seats': len(danh_sach_ghe)
            },
            'trip_info': {
                'maLichTrinh': lt['maLichTrinh'],
                'diemDi': lt.get('diemDi'),
                'diemDen': lt.get('diemDen'),
                'ngayDi': lt['ngayDi'].strftime('%Y-%m-%d'),
                'gioDi': lt.get('gioDi')
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@user_bp.route('/booking/confirm', methods=['POST'])
def confirm_booking():
    # Check if customer logged in
    if 'customer_id' not in session:
        flash('Vui lòng đăng nhập để đặt vé', 'warning')
        return redirect(url_for('auth.login'))
    
    lich_trinh_id = request.form.get('lich_trinh_id')
    selected_seats = request.form.get('selected_seats', '')
    
    # Validate selected seats
    if not selected_seats or selected_seats.strip() == '':
        flash('Vui lòng chọn ít nhất 1 ghế!', 'error')
        return redirect(request.referrer or url_for('user.index'))
    
    # Parse selected seats
    seat_list = [seat.strip() for seat in selected_seats.split(',') if seat.strip()]
    
    # Check seat limit
    if len(seat_list) > 5:
        flash('Chỉ được phép đặt tối đa 5 vé cho một đơn hàng!', 'error')
        return redirect(request.referrer or url_for('user.index'))
    
    # Get current customer info
    customer = mongo.db.KhachHang.find_one({'_id': get_object_id(session['customer_id'])})
    if not customer:
        flash('Không tìm thấy thông tin khách hàng', 'error')
        return redirect(url_for('user.index'))
    
    # Get lich trinh info  
    lt = mongo.db.LichTrinh.find_one({'_id': get_object_id(lich_trinh_id)})
    if not lt:
        flash('Không tìm thấy lịch trình', 'error')
        return redirect(url_for('user.index'))
    
    # Check if any seat is already booked
    for seat in seat_list:
        existing_ticket = mongo.db.VeXe.find_one({
            'maLichTrinh': lt['maLichTrinh'],
            'maGhe': seat
        })
        if existing_ticket:
            flash(f'Ghế {seat} đã được đặt, vui lòng chọn ghế khác!', 'error')
            return redirect(request.referrer or url_for('user.index'))
    
    # Get pricing info
    gia_ve = mongo.db.GiaVe.find_one({
        'tuyen': f"{lt.get('diemDi')}-{lt.get('diemDen')}"
    })
    
    # Generate booking batch ID
    import time
    batch_id = f"DV{int(time.time())}"
    
    # Create multiple tickets
    tickets_created = []
    try:
        for i, seat in enumerate(seat_list):
            ticket_id = f"VX{int(time.time())}_{i+1}"
            
            ve_data = {
                'maVe': ticket_id,
                'maLichTrinh': lt['maLichTrinh'],
                'maGhe': seat,
                'maGiaVe': gia_ve.get('maGiaVe') if gia_ve else None,
                'maKhach': customer.get('maKhach'),  # Old schema compatibility
                'maKhachHang': str(session['customer_id']),  # New schema
                'maDatVe': batch_id,  # Same batch ID for all tickets in this booking
                'ngayThem': datetime.now(),
                'ngayDat': datetime.now(),
                'nguoiThem': customer.get('maKhach'),
                'tinhTrang': 'Chờ thanh toán',  # Old schema
                'trangThai': 'DaDat'  # New schema
            }
            
            result = mongo.db.VeXe.insert_one(ve_data)
            if result.inserted_id:
                tickets_created.append(ticket_id)
            else:
                raise Exception(f"Không thể tạo vé cho ghế {seat}")
        
        # Success message
        seat_text = ', '.join(seat_list)
        flash(f'Đặt vé thành công! {len(tickets_created)} vé cho các ghế: {seat_text}', 'success')
        return redirect(url_for('user.my_tickets'))
        
    except Exception as e:
        # If there's an error, try to clean up any created tickets
        if tickets_created:
            mongo.db.VeXe.delete_many({'maVe': {'$in': tickets_created}})
        
        flash(f'Lỗi đặt vé: {str(e)}', 'error')
        return redirect(request.referrer or url_for('user.index'))

@user_bp.route('/routes')
def routes():
    """Hiển thị tất cả tuyến đường và chuyến xe khả dụng"""
    try:
        # Lấy tất cả tuyến đường
        tuyen_duong = list(mongo.db.TuyenDuong.find({}).sort('tenTuyenDuong', 1))
        
        routes_with_trips = []
        for tuyen in tuyen_duong:
            # Tìm các chuyến xe cho tuyến này - chỉ lấy chuyến khả dụng
            current_time = datetime.now()
            today = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            
            trips_query = {
                '$or': [
                    {'diemDi': tuyen.get('diemDau'), 'diemDen': tuyen.get('diemCuoi')},
                    {'diemDi': tuyen.get('diemCuoi'), 'diemDen': tuyen.get('diemDau')}  # Chiều ngược lại
                ],
                '$and': [
                    # Chỉ lấy chuyến từ hôm nay trở đi
                    {'ngayDi': {'$gte': today}},
                    # Trạng thái phù hợp: hôm nay là 'Đang chạy', tương lai là 'Sắp chạy'
                    {'$or': [
                        {'ngayDi': {'$gte': today, '$lt': today + timedelta(days=1)}, 'tinhTrang': 'Đang chạy'},
                        {'ngayDi': {'$gte': today + timedelta(days=1)}, 'tinhTrang': 'Sắp chạy'}
                    ]}
                ]
            }
            
            trips = list(mongo.db.LichTrinh.find(trips_query).sort('ngayDi', 1).limit(10))
            
            # Enrich trip data
            for trip in trips:
                # Thông tin xe
                xe = mongo.db.XeKhach.find_one({'maXeKhach': trip.get('maXe')})
                trip['xe_info'] = xe if xe else {}
                
                # Giá vé - tìm theo nhiều cách
                gia_ve = mongo.db.GiaVe.find_one({
                    '$or': [
                        {'tuyen': tuyen.get('maTuyenDuong')},
                        {'maTuyenDuong': tuyen.get('maTuyenDuong')},
                        {'maHangXe': xe.get('maHang'), 'maLoaiXe': xe.get('maLoai')} if xe else {}
                    ],
                    'tinhTrang': {'$in': ['Hoạt động', 'Đang áp dụng']}
                }) if xe else None
                
                # Fallback giá VIP30 nếu không tìm thấy
                if not gia_ve and xe and xe.get('maLoai') == 'VIP30':
                    trip['gia_ve'] = 450000
                else:
                    trip['gia_ve'] = gia_ve.get('giaVe', 0) if gia_ve else 0
                
                # Số ghế còn trống
                booked_seats = mongo.db.VeXe.count_documents({'maLichTrinh': trip.get('maLichTrinh')})
                total_seats = mongo.db.Ghe.count_documents({'maLichTrinh': trip.get('maLichTrinh')})
                trip['ghe_trong'] = max(0, total_seats - booked_seats)
                trip['total_seats'] = total_seats
            
            if trips:  # Chỉ thêm tuyến có chuyến xe
                routes_with_trips.append({
                    'tuyen': tuyen,
                    'trips': trips
                })
        
        return render_template('user/routes.html', routes_with_trips=routes_with_trips)
        
    except Exception as e:
        print(f"Error in routes(): {e}")
        flash('Có lỗi khi tải danh sách tuyến đường')
        return redirect(url_for('user.index'))

@user_bp.route('/news')
def news():
    tin_tuc = list(mongo.db.TinTuc.find())
    return render_template('user/news.html', tin_tuc=tin_tuc)

@user_bp.route('/news/<news_id>')
def news_detail(news_id):
    tin = mongo.db.TinTuc.find_one({'_id': get_object_id(news_id)})
    return render_template('user/news_detail.html', tin=tin)
