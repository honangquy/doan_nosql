from app import create_app
from app import mongo

app = create_app()

with app.app_context():
    try:
        # Create admin account
        admin_account = {
            'username': 'admin',
            'password': '123456',  # In production, should be hashed
            'role': 'admin',
            'hoTen': 'Administrator',
            'ngayThem': mongo.db.TaiKhoan.find().count() + 1
        }
        
        # Check if admin already exists
        existing = mongo.db.TaiKhoan.find_one({'username': 'admin'})
        if not existing:
            result = mongo.db.TaiKhoan.insert_one(admin_account)
            print(f"Admin account created with ID: {result.inserted_id}")
            print("Username: admin")
            print("Password: 123456")
        else:
            print("Admin account already exists")
            print("Username: admin")
            print("Password: 123456")
            
    except Exception as e:
        print(f"Error: {e}")