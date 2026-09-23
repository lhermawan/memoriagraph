from server import driver

query = """
MATCH (u:Entity {name: 'User'})
MATCH (m:Entity {name: 'Maskii'})
RETURN id(u) as u_id, id(m) as m_id
"""
with driver.session() as session:
    res = session.run(query).single()
    if res:
        print(f"Both exist. User: {res['u_id']}, Maskii: {res['m_id']}")
    else:
        print("Only one or neither exists.")
        res2 = session.run("MATCH (n:Entity) WHERE n.name IN ['User', 'Maskii'] RETURN n.name as name")
        print([r['name'] for r in res2])
