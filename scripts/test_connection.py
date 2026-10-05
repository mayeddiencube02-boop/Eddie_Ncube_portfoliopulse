import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.environ["NEON_DATABASE_URL"])
cur = conn.cursor()
cur.execute("select version();")
print(cur.fetchone()[0])
conn.close()
