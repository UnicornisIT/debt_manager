from app import app
import traceback

with app.test_client() as client:
    for path in ['/', '/login', '/admin/login']:
        try:
            rv = client.get(path)
            print(path, rv.status_code)
            print(rv.data[:500].decode('utf-8', errors='replace'))
        except Exception:
            print(path, 'EXCEPTION')
            traceback.print_exc()
