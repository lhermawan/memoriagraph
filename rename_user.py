from server import driver

# Ganti nama 'User' menjadi 'Maskii'
query = """
MATCH (u:Entity {name: 'User'})
SET u.name = 'Maskii'
RETURN u.name as new_name
"""
with driver.session() as session:
    res = session.run(query).single()
    if res:
        print(f"Berhasil mengubah nama node menjadi: {res['new_name']}")
    else:
        print("Node 'User' tidak ditemukan, mungkin sudah diubah.")
