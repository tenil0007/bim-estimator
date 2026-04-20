import sys
import traceback

print("Starting import test")
try:
    import app.main
    print("app.main imported OK")
except Exception as e:
    traceback.print_exc()
