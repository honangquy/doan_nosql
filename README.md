# 🚌 Hệ Thống Quản Lý Xe Khách

Hệ thống quản lý xe khách toàn diện với **Role-Based Access Control (RBAC)** được xây dựng bằng Flask và MongoDB.

## 🎯 Tính Năng Chính

### 🛡️ Hệ Thống Phân Quyền (RBAC)
- **4 cấp độ vai trò**: ADMIN → QLVH → QLKT → QLNS/CSKH
- **70+ quyền hạn** được cấu hình chi tiết
- **Bảo vệ routes** với kiểm tra vai trò tự động
- **Giao diện quản lý phân quyền** trực quan

### 🔐 Quản Lý Mật Khẩu
- **Tài khoản Admin**: Quản lý mật khẩu cho nhân viên
- **Tài khoản Khách Hàng**: Hệ thống đăng nhập khách hàng
- **Bảo mật**: Mật khẩu được mã hóa và ẩn hiển thị
- **Validation**: Xác thực mật khẩu đa tầng

### 🎨 Giao Diện Responsive
- **Bootstrap 5**: Thiết kế hiện đại, responsive
- **Mobile-friendly**: Tối ưu cho mọi thiết bị
- **UI/UX**: Giao diện trực quan, dễ sử dụng

### 📊 Quản Lý Nghiệp Vụ
- **Quản lý xe khách**: Thêm, sửa, xóa phương tiện
- **Quản lý tuyến đường**: Định tuyến và lịch trình
- **Bán vé**: Hệ thống đặt vé trực tuyến
- **Sơ đồ ghế**: Quản lý ghế ngồi theo xe
- **Báo cáo**: Thống kê doanh thu và vận hành

## 🏗️ Kiến Trúc Hệ Thống

### Technology Stack
- **Backend**: Flask (Python 3.8+)
- **Database**: MongoDB
- **Frontend**: Bootstrap 5, jQuery
- **Authentication**: Session-based với RBAC

### Cấu Trúc Project
```
doan_nosql/
├── 📁 app/                    # Ứng dụng Flask chính
│   ├── 📁 routes/            # Route handlers
│   │   ├── admin.py          # Routes quản trị
│   │   ├── auth.py           # Authentication
│   │   └── user.py           # Routes người dùng
│   ├── 📁 static/            # CSS, JavaScript, Images
│   ├── 📁 templates/         # Jinja2 templates
│   ├── __init__.py           # Flask app factory
│   ├── permissions.py        # RBAC system
│   └── utils.py              # Utilities
├── 📄 config.py              # Cấu hình hệ thống
├── 📄 requirements.txt       # Python dependencies
├── 📄 run.py                 # Entry point
├── 📄 create_admin.py        # Tạo tài khoản admin
└── 📄 create_user_demo.py    # Tạo dữ liệu demo
```

## 🚀 Cài Đặt và Chạy

### 1. Yêu Cầu Hệ Thống
```bash
# Python 3.8+
python --version

# MongoDB Community Server
mongo --version
```

### 2. Clone Repository
```bash
git clone <repository-url>
cd doan_nosql
```

### 3. Cài Đặt Dependencies
```bash
pip install -r requirements.txt
```

### 4. Cấu Hình MongoDB
Đảm bảo MongoDB đang chạy và có database `quanly_xekhach`:
```bash
# Khởi động MongoDB
net start MongoDB

# Kết nối và kiểm tra
mongo mongodb://localhost:27017/quanly_xekhach
```

### 5. Tạo Tài Khoản Admin
```bash
python create_admin.py
```

### 6. Tạo Dữ Liệu Demo (Tùy chọn)
```bash
python create_user_demo.py
```

### 7. Chạy Ứng Dụng
```bash
python run.py
```

Truy cập: http://127.0.0.1:5000

## 👥 Hệ Thống Phân Quyền

### Roles và Permissions

| Role | Mô Tả | Quyền Hạn |
|------|--------|-----------|
| **ADMIN** | Quản trị viên hệ thống | Toàn quyền (*) |
| **QLVH** | Quản lý vận hành | Quản lý xe, tuyến đường, lịch trình |
| **QLKT** | Quản lý kinh tế | Quản lý vé, giá vé, báo cáo |
| **QLNS** | Quản lý nhân sự | Quản lý nhân viên, báo cáo |
| **CSKH** | Chăm sóc khách hàng | Quản lý khách hàng, bán vé |

### Truy Cập Admin Panel
- **URL**: `/admin`
- **Tài khoản mặc định**: 
  - Username: `admin`
  - Password: `123`

## 📊 Database Schema

### Collections Chính
- **TaiKhoan**: Tài khoản hệ thống (admin, nhân viên)
- **KhachHang**: Tài khoản khách hàng
- **XeKhach**: Thông tin phương tiện
- **TuyenDuong**: Tuyến đường vận hành
- **LichTrinh**: Lịch trình chạy xe
- **VeXe**: Vé xe đã bán
- **Ghe**: Sơ đồ ghế ngồi

### Relationships
```
XeKhach → LichTrinh → Ghe → VeXe → KhachHang
TuyenDuong → LichTrinh
GiaVe → TuyenDuong
```

## 🔐 Bảo Mật

### Features
- **Mật khẩu mã hóa**: Hỗ trợ cả plain text và hashed
- **Session management**: Quản lý phiên đăng nhập
- **Route protection**: Bảo vệ theo vai trò
- **Input validation**: Kiểm tra dữ liệu đầu vào
- **XSS protection**: Bảo vệ khỏi tấn công XSS

### Best Practices
- Đổi mật khẩu admin mặc định
- Sử dụng HTTPS trong production
- Backup database định kỳ
- Monitor logs và truy cập

## 🛠️ Phát Triển

### Thêm Role Mới
1. Cập nhật `app/permissions.py`:
```python
PERMISSIONS = {
    'NEW_ROLE': ['permission1', 'permission2'],
    # ...
}
```

2. Thêm vào database `LoaiTaiKhoan`

### Thêm Collection Mới
1. Cập nhật `SCHEMAS` trong `app/routes/admin.py`
2. Tạo template tương ứng nếu cần

### Testing
```bash
# Kiểm tra kết nối database
python -c "from pymongo import MongoClient; print(MongoClient().list_database_names())"

# Test authentication
python -c "from app import create_app; app = create_app(); print('App created successfully!')"
```

## 📝 API Documentation

### Authentication Endpoints
```
POST /auth/login          # Đăng nhập
POST /auth/logout         # Đăng xuất
GET  /auth/register       # Form đăng ký khách hàng
POST /auth/register       # Xử lý đăng ký
```

### Admin Endpoints
```
GET  /admin/dashboard           # Dashboard quản trị
GET  /admin/permissions         # Quản lý phân quyền
GET  /admin/<collection>        # Danh sách collection
GET  /admin/<collection>/add    # Form thêm mới
POST /admin/<collection>/add    # Xử lý thêm mới
GET  /admin/<collection>/edit/<id>  # Form sửa
POST /admin/<collection>/edit/<id> # Xử lý sửa
POST /admin/<collection>/delete/<id> # Xóa
```

### User Endpoints
```
GET  /                    # Trang chủ
GET  /routes              # Tìm tuyến đường
GET  /booking/<trip_id>   # Đặt vé
POST /booking/confirm     # Xác nhận đặt vé
```

## 🐛 Troubleshooting

### Lỗi Thường Gặp

#### MongoDB Connection Error
```bash
# Kiểm tra MongoDB đang chạy
net start MongoDB

# Kiểm tra database tồn tại
mongo --eval "show dbs"
```

#### Import Error
```bash
# Cài đặt lại dependencies
pip install -r requirements.txt --upgrade
```

#### Permission Denied
```bash
# Kiểm tra role trong database
mongo quanly_xekhach --eval "db.LoaiTaiKhoan.find()"
```

### Debug Mode
```python
# Trong config.py
DEBUG = True
FLASK_ENV = 'development'
```

## 📞 Hỗ Trợ

### Documentation
- `RBAC_IMPLEMENTATION_COMPLETE.md` - Chi tiết hệ thống RBAC
- `PROJECT_CLEANUP_SUMMARY.md` - Tóm tắt dọn dẹp project

### Contact
- **Developer**: GitHub Copilot Assistant
- **Framework**: Flask + MongoDB + Bootstrap 5
- **Version**: 1.0.0

## 📄 License

MIT License - Tự do sử dụng cho mục đích học tập và thương mại.

## 🙏 Credits

- **Flask**: Web framework
- **MongoDB**: NoSQL database
- **Bootstrap**: UI framework
- **Chart.js**: Data visualization
- **jQuery**: JavaScript utilities

---

**🚀 Ready for Production!** - Hệ thống hoàn chỉnh với RBAC, quản lý mật khẩu và giao diện responsive.