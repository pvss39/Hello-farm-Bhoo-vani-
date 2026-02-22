"""
Test the full satellite notification loop with NDVI image + advisory.
Clears today's notification record for Athota Road Polam so it re-fires.
"""
import sys
import os

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from src.database import FarmDatabase

db = FarmDatabase()
db.init_database()

plots = db.get_all_plots()
print(f"Plots in DB: {len(plots)}")
for p in plots:
    has_boundary = bool(p.get("boundary_coords"))
    print(f"  [{p['id']}] {p['name_english']}  lat={p['center_latitude']:.5f} lon={p['center_longitude']:.5f}  boundary={has_boundary}")

# Clear today's satellite notification for Athota Road Polam so it re-triggers
import sqlite3
conn = sqlite3.connect(db.db_path)
conn.execute("""
    DELETE FROM satellite_notifications
    WHERE plot_id IN (
        SELECT id FROM plots WHERE name_english = 'Athota Road Polam'
    )
""")
conn.commit()
conn.close()
print("\nCleared satellite_notifications for Athota Road Polam — will re-trigger now.\n")

# Run the satellite check (pulls all plots from DB automatically)
from server import check_satellite_updates
check_satellite_updates()
