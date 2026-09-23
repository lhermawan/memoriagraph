from server import driver, add_entity, add_relation

# Tambahkan/Update Entitas
add_entity('Lucky Hermawan Roza', 'Identity', 'Nama Asli dari Maskii')
add_entity('Security Researcher', 'Role', 'Peneliti Keamanan Siber')
add_entity('Fullstack Developer', 'Role', 'Pengembang Fullstack')
add_entity('Cybersecurity', 'Domain', 'Keamanan Siber')
add_entity('SAMS', 'Featured_Project', 'System Absensi Manajemen Shift (Multi-tenant)')

# Tech Stack Baru (Dev & Security)
techs = ['Next.js', 'React', 'Prisma', 'PostgreSQL', 'TailwindCSS', 'Docker', 'OWASP ZAP', 'Nuclei', 'Semgrep', 'Kali Linux']
for t in techs:
    add_entity(t, 'Technology', 'Alat / Stack yang digunakan Maskii')

with driver.session() as session:
    # Set properti di node Maskii
    session.run('''
        MATCH (m:Entity {name: 'Maskii'})
        SET m.fullName = 'Lucky Hermawan Roza',
            m.email = 'luckyhermawanroza@gmail.com',
            m.linkedin = 'luckyhermawanroza',
            m.instagram = 'luckyhrmwnroza'
    ''')
    
    # Hubungkan Identitas
    session.run('''
        MATCH (m:Entity {name: 'Maskii'})
        MATCH (id:Entity {name: 'Lucky Hermawan Roza'})
        MATCH (r1:Entity {name: 'Security Researcher'})
        MATCH (r2:Entity {name: 'Fullstack Developer'})
        MATCH (d:Entity {name: 'Cybersecurity'})
        MERGE (m)-[:NAMA_ASLI]->(id)
        MERGE (m)-[:MEMILIKI_PERAN]->(r1)
        MERGE (m)-[:MEMILIKI_PERAN]->(r2)
        MERGE (m)-[:FOKUS_PADA]->(d)
    ''')
    
    # Hubungkan Tech Stack
    for t in techs:
        session.run('''
            MATCH (m:Entity {name: 'Maskii'})
            MATCH (t:Entity {name: $tech})
            MERGE (m)-[:MENGUASAI_TOOL]->(t)
        ''', tech=t)

print('Berhasil menyuntikkan profil GitHub baru ke dalam MemoriaGraph!')
