# test.py
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
h = "$2b$12$8RCiUeY8acc4bwnHbhJWq.gAl8FpN.hiKMi3WQX7cn51Wc7Poeafy"
print(pwd_context.verify("Admin1234!", h))