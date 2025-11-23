# Copilot Instructions - Bus Management System

## Architecture Overview

This is a **Flask + MongoDB bus management system** with Vietnamese domain model. The app uses a 3-tier architecture:
- **Frontend**: Bootstrap 5 templates with Vietnamese UI labels
- **Backend**: Flask with Blueprint routing (`user`, `admin`, `auth`)
- **Database**: MongoDB with Vietnamese collection/field names

## Database Configuration - CRITICAL

**Database Name**: `quanly_xekhach` (NOT `qly_bus`)
**Connection**: `mongodb://localhost:27017/quanly_xekhach`

**IMPORTANT**: Always verify database name before operations. Use this command to check:
```python
from pymongo import MongoClient
client = MongoClient('mongodb://localhost:27017/')
print("Available databases:", client.list_database_names())
# Should show 'quanly_xekhach' with actual data
```

## Key Collections & Schema Pattern

**Critical**: Database uses Vietnamese field names with actual structure:

### Core Collections (22 total):
```python
# Authentication
TaiKhoan: ten, matKhau, maLoai  # 37 documents
LoaiTaiKhoan: maLoai, tenLoai   # 10 documents

# Business Management - ACTUAL SCHEMA
XeKhach: maXeKhach, ten, bienSo, hangSanXuat, maLoai, maHang, tuyen, mau, tinhTrang, ngayThem, moTa  # 49 documents
TuyenDuong: maTuyenDuong, tenTuyenDuong, diemDau, diemCuoi, doDai, thoiGianDi  # 51 documents
LichTrinh: maLichTrinh, maXe, diemDi, diemDen, gioDi, ngayDi, tramDung, tenTaiXe, tenPhuXe, tinhTrang, ngayThem, moTa  # 50 documents

# Customer & Booking System
KhachHang: maKhach, ten, dienThoai, diaChi, email, soCmnd, moTa  # 50 documents
VeXe: maVe, maLichTrinh, maGhe, maGiaVe, maKhach, maDatVe, ngayThem, nguoiThem, tinhTrang  # 99 documents
Ghe: maGhe, maLichTrinh, soGhe, tinhTrang, moTa  # 1,719 documents

# Pricing & Revenue
GiaVe: maGiaVe, maTuyenDuong, giaVe, phuThu, ngayApDung, ngayKetThuc, moTa  # 53 documents
ThanhToan: maThanhToan, maVe, soTien, phuongThuc, ngayThanhToan, tinhTrang  # 50 documents

# Reference Data
DiaDiem: maDiaDiem, tenDiaDiem, tinhThanh  # 49 documents
TinhThanh: maTinhThanh, tenTinhThanh, mien  # 34 documents
TramDung: maTramDung, tenTramDung, diaChi, maTinhThanh  # 30 documents
LoaiXe: maLoaiXe, tenLoaiXe, soGhe, moTa  # 49 documents
HangXe: maHangXe, tenHangXe, quocGia  # 50 documents

# System & Content
NhanVien: maNhanVien, ten, chucVu, dienThoai, email  # 25 documents
LoaiNhanVien: maLoaiNV, tenLoai, moTa  # 20 documents
TinTuc: maTinTuc, tieuDe, noiDung, ngayDang, tacGia, maLoaiTinTuc  # 50 documents
LoaiTinTuc: maLoaiTinTuc, tenLoai  # 30 documents
BaoCao: maBaoCao, tenBaoCao, ngayTao, noiDung  # 50 documents
DaiLy: maDaiLy, tenDaiLy, diaChi, dienThoai, email  # 25 documents
SoDoGhe: maSoDo, tenSoDo, soCot, soHang, moTa  # 19 documents
```

### Relationship Mapping for Seat Management:
```python
# Seat-map relationships (CRITICAL for seat management)
XeKhach.maXeKhach -> LichTrinh.maXe -> Ghe.maLichTrinh
VeXe.maGhe + VeXe.maKhach -> KhachHang.maKhach (for customer info)
VeXe.ngayThem (booking date), KhachHang.dienThoai (phone number)
```

## Authentication System

**Multi-format password support**: Plain text OR hashed (`hashed_password_123` format)
```python
# Login logic handles both formats
if stored_password == password:  # Plain text
    password_match = True
elif stored_password == f'hashed_password_{password}':  # Hashed format
    password_match = True
```

**Role-based access**: `session['role']` must be `'ADMIN'` for admin routes. Uses `@admin_bp.before_request` decorator.

## Dynamic CRUD System

Admin panel uses **schema-driven CRUD** in `app/routes/admin.py`:
```python
SCHEMAS = {
    'TuyenDuong': {
        'fields': ['maTuyenDuong', 'tenTuyenDuong', 'diemDau', 'diemCuoi'],
        'label': 'Tuyến Đường'
    }
}
```

**Generic routes**: `/<collection_name>`, `/<collection_name>/add`, `/<collection_name>/edit/<item_id>`  
**Templates**: `crud_list.html` and `crud_form.html` dynamically render based on schema

## Development Workflow

**Start server**: `python run.py` (runs on http://127.0.0.1:5000)

**Test authentication**: `python test_auth_system.py` - validates database schema alignment  
**Test admin flow**: `python test_auth_flow.py` - comprehensive HTTP testing  
**Test all features**: `python test_admin_comprehensive.py` - full CRUD + dashboard testing  
**Test database schema**: `python test_complete_customer_info.py` - validates seat-map with customer data

**Admin credentials**: username=`admin`, password=`123` (maps to `hashed_password_123` in DB)

## Common Errors & Solutions

### 1. Database Connection Errors
```python
# ERROR: Empty collections or wrong database
Available databases: ['admin', 'local']  # Missing quanly_xekhach

# SOLUTION: Check MongoDB is running and database exists
mongo --eval "show dbs"  # Should show quanly_xekhach
```

### 2. Missing Customer Information
```python
# ERROR: Only seat status, no customer details
seat_data[seat_num] = {'status': 'occupied', 'description': ''}

# SOLUTION: Join VeXe + KhachHang collections
bookings = mongo.db.VeXe.find({'maLichTrinh': {'$in': schedule_codes}})
customers = mongo.db.KhachHang.find({'maKhach': {'$in': customer_codes}})
# Include: customerName, customerPhone, bookingDate, ticketStatus
```

### 3. JavaScript Reference Errors
```python
# ERROR: ReferenceError: bookings is not defined
bookings.forEach(booking => { ... })

# SOLUTION: Add null checks
if (bookings && Array.isArray(bookings)) {
    bookings.forEach(booking => { ... })
}
```

### 4. API Data Structure Issues
```python
# ERROR: Missing required fields in API response
{'status': 'success', 'seats': {...}}

# SOLUTION: Include all required fields
{
    'status': 'success', 
    'seats': {
        'A01': {
            'customerName': 'Nguyễn Văn A',
            'customerPhone': '0909123456', 
            'bookingDate': '2025-11-22',
            'ticketStatus': 'Đã thanh toán',
            'originalStatus': 'Đã bán'
        }
    }
}
```

## Template Architecture

**Admin layout inheritance**:
- `templates/admin/layout.html` - modern Bootstrap 5 base
- `templates/admin/sidebar.html` - navigation component  
- `templates/admin/dashboard_new.html` - Chart.js dashboard
- `templates/admin/crud_*.html` - generic CRUD templates

**Vietnamese UI**: All labels, flash messages, form fields use Vietnamese text

## Actual Status Values - CRITICAL FOR UI

### Trip Status (LichTrinh.tinhTrang):
```python
# ACTUAL values from database:
'Đã hoàn thành'  # Completed trips
'Đã hủy'         # Cancelled trips  
'Đang chạy'      # Currently running
'Sắp chạy'       # Scheduled to run
```

### Ticket Status (VeXe.tinhTrang):
```python
# ACTUAL values from database:
'Chờ thanh toán'  # Pending payment
'Đã thanh toán'   # Paid
'Đã hủy'          # Cancelled
```

### Vehicle Status (XeKhach.tinhTrang):
```python
# ACTUAL values from database:
'Sẵn sàng'       # Ready/Available
'Đang sửa'       # Under maintenance
```

### CSS Status Classes for Templates:
```css
.status-da-hoan-thanh { background: #d1e7dd; color: #0f5132; }  /* Đã hoàn thành */
.status-da-huy { background: #f8d7da; color: #721c24; }         /* Đã hủy */
.status-dang-chay { background: #d4edda; color: #155724; }      /* Đang chạy */
.status-sap-chay { background: #cce5ff; color: #004085; }       /* Sắp chạy */
.status-da-thanh-toan { background: #d1e7dd; color: #0f5132; } /* Đã thanh toán */
.status-cho-thanh-toan { background: #fff3cd; color: #856404; }/* Chờ thanh toán */
.status-san-sang { background: #d1e7dd; color: #0f5132; }      /* Sẵn sàng */
.status-dang-sua { background: #fff3cd; color: #856404; }      /* Đang sửa */
```

### Template Status Display Usage:
```html
<!-- Import helper function in route -->
from app.utils import vietnamese_to_css_class
render_template('template.html', vietnamese_to_css_class=vietnamese_to_css_class)

<!-- Use in template -->
<span class="status-badge status-{{ vietnamese_to_css_class(trip.tinhTrang) }}">
    {{ trip.tinhTrang }}
</span>
```

## Database Access Patterns - CRITICAL FIXES

### Common Database Errors to Avoid:

1. **Wrong Database Name**: 
   - ❌ `qly_bus` (empty/non-existent)
   - ✅ `quanly_xekhach` (actual database with data)

2. **Missing Collection Relationships**:
   ```python
   # WRONG: Only checking Ghe collection
   seats = mongo.db.Ghe.find({'maXe': vehicle_id})
   
   # CORRECT: Multi-collection lookup for complete data
   schedules = mongo.db.LichTrinh.find({'maXe': vehicle_id})
   schedule_codes = [s['maLichTrinh'] for s in schedules]
   seats = mongo.db.Ghe.find({'maLichTrinh': {'$in': schedule_codes}})
   bookings = mongo.db.VeXe.find({'maLichTrinh': {'$in': schedule_codes}})
   customers = mongo.db.KhachHang.find({'maKhach': {'$in': customer_codes}})
   ```

3. **Field Name Mismatches**:
   ```python
   # Common correct field names
   VeXe: maVe, maLichTrinh, maGhe, maKhach, ngayThem, tinhTrang
   KhachHang: maKhach, ten, dienThoai, diaChi, email
   Ghe: maGhe, maLichTrinh, soGhe, tinhTrang, moTa
   XeKhach: maXeKhach, ten, bienSo, loaiXe, tinhTrang
   ```

### Database Verification Commands:
```python
# Always run this first to verify database
client = MongoClient('mongodb://localhost:27017/')
db = client['quanly_xekhach']
print("Collections:", db.list_collection_names())
print("Sample docs:", db.VeXe.find_one(), db.KhachHang.find_one())
```

## MongoDB Utilities

**ObjectId handling**: Use `get_object_id()` from `app.utils` for safe ObjectId conversion  
**JSON serialization**: Use `parse_json()` to convert ObjectId to string for templates  
**Database connection**: Always use `quanly_xekhach` database name

## Testing Patterns

**Database inspection**: Tests validate actual DB schema vs code expectations  
**HTTP flow testing**: Uses `requests.Session()` to maintain login state  
**Comprehensive coverage**: Tests dashboard stats, CRUD operations, form submissions  
**Schema validation**: Always verify collections exist and have data before operations

## Schema Verification - ALWAYS CHECK FIRST

**CRITICAL**: Always verify database schema before writing code. Use this verification script:

```python
from pymongo import MongoClient
client = MongoClient('mongodb://localhost:27017/')
db = client['quanly_xekhach']

# Check actual field names
trip = db.LichTrinh.find_one({})
vehicle = db.XeKhach.find_one({})
booking = db.VeXe.find_one({})

print("LichTrinh fields:", list(trip.keys()) if trip else "None")
print("XeKhach fields:", list(vehicle.keys()) if vehicle else "None")
print("VeXe fields:", list(booking.keys()) if booking else "None")

# Check actual status values
trip_statuses = db.LichTrinh.distinct('tinhTrang')
print("Trip statuses:", trip_statuses)
client.close()
```

### Common Schema Mistakes to Avoid:
- ❌ Using `status` instead of `tinhTrang`
- ❌ Using `name` instead of `ten`
- ❌ Using `id` instead of `maLichTrinh`/`maXeKhach`/`maKhach`
- ❌ Assuming English field names

## Development Guidelines - Updated

When working with this codebase:
1. **Always verify database name**: Use `quanly_xekhach`, not `qly_bus` luôn kiểm tra các cột và các bảng trước khi viết các lệnh truy vấn
2. **Check collection relationships**: Multi-table joins required for complete data
3. **Use Vietnamese field names**: Match exact field names from schema above
4. **Test database connections**: Verify collections have data before development
5. **Validate API responses**: Include customer phone, booking date, ticket status
6. **Use proper collection lookup**: XeKhach -> LichTrinh -> Ghe -> VeXe -> KhachHang
7. **Handle empty collections**: Always check document count before operations
8. **Test with real data**: Use vehicles X001, X002, X005 which have booking data