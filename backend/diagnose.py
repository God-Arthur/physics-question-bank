#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, '/home/redaunt/physics/backend')

try:
    from app import create_app
    print("✓ 应用创建成功")
    
    app = create_app()
    print("✓ 应用初始化成功")
    
    # 测试路由
    with app.test_client() as client:
        # 测试登录
        response = client.post('/api/auth/login', 
                              json={'username': 'admin', 'password': 'admin123'})
        print(f"✓ 登录接口状态: {response.status_code}")
        if response.status_code == 200:
            data = response.get_json()
            print(f"✓ 登录成功，token: {data.get('access_token', '无')[:20]}...")
        else:
            print(f"✗ 登录失败: {response.get_json()}")
            
except Exception as e:
    print(f"✗ 错误: {e}")
    import traceback
    traceback.print_exc()
