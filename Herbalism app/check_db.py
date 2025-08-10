import sqlite3

conn = sqlite3.connect("herbalism.db")
cursor = conn.cursor()
cursor.execute("SELECT name FROM herbs ORDER BY name")
herbs = cursor.fetchall()
conn.close()

print("Herbs in database:")
for herb in herbs:
    print(herb[0])

if any("horsetail" in herb[0].lower() for herb in herbs):
    print("\n'horsetail' found in the database.")
else:
    print("\n'horsetail' NOT found in the database.")

