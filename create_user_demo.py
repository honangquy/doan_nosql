from app import create_app, mongo

app = create_app()

with app.app_context():
    # Tạo tài khoản user demo
    user_demo = {
        'username': 'user1',
        'password': 'password',
        'role': 'user',
        'email': 'user1@example.com',
        'created_at': '2024-01-01'
    }
    
    # Check if user already exists
    existing_user = mongo.db.TaiKhoan.find_one({'username': 'user1'})
    if not existing_user:
        mongo.db.TaiKhoan.insert_one(user_demo)
        print("✅ User demo account created: user1/password")
    else:
        print("ℹ️ User demo account already exists")
    
    # List all accounts
    accounts = list(mongo.db.TaiKhoan.find())
    print(f"\n📋 Total accounts: {len(accounts)}")
    for acc in accounts:
        print(f"   - {acc['username']} ({acc.get('role', 'unknown')})")