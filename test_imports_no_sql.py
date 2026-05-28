import sys
import traceback

print("Testing non-SQLAlchemy imports...")

try:
    print("1. Importing jinja2...")
    import jinja2
    print("   Success")
    
    print("2. Importing passlib...")
    import passlib
    print("   Success")
    
    print("3. Importing passlib.context...")
    from passlib.context import CryptContext
    print("   Success")
    
    print("4. Importing itsdangerous...")
    import itsdangerous
    print("   Success")
    
    print("5. Importing fastapi...")
    import fastapi
    print("   Success")
    
    print("6. Importing uvicorn...")
    import uvicorn
    print("   Success")
    
    print("All other libraries imported successfully!")
    
except Exception as e:
    traceback.print_exc()
    sys.exit(1)
