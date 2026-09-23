from neo4j import GraphDatabase
import time

driver_local = GraphDatabase.driver('neo4j://127.0.0.1:7687', auth=('neo4j', 'Hermawan8789#'))
driver_remote = GraphDatabase.driver('neo4j://127.0.0.1:9687', auth=('neo4j', 'maskiisecret'))

def migrate():
    # Tunggu DB remote siap
    for _ in range(30):
        try:
            driver_remote.verify_connectivity()
            print("Remote DB is ready!")
            break
        except Exception as e:
            print("Waiting for remote DB...")
            time.sleep(2)
            
    nodes = []
    edges = []
    with driver_local.session() as s_local:
        res_nodes = s_local.run("MATCH (n) RETURN labels(n)[0] as label, properties(n) as props")
        for r in res_nodes:
            nodes.append({'label': r['label'], 'props': r['props']})
            
        res_edges = s_local.run("MATCH (a)-[r]->(b) RETURN a.name as source, type(r) as type, properties(r) as props, b.name as target")
        for r in res_edges:
            edges.append({'source': r['source'], 'type': r['type'], 'props': r['props'], 'target': r['target']})
            
    print(f"Read {len(nodes)} nodes and {len(edges)} edges from local DB.")
    
    with driver_remote.session() as s_remote:
        # Create Nodes
        for n in nodes:
            label = n['label']
            props = n['props']
            set_items = []
            for k in props.keys():
                set_items.append(f"x.`{k}` = $props.`{k}`")
            set_clause = ", ".join(set_items)
            
            s_remote.run(f"MERGE (x:`{label}` {{name: $name}}) SET {set_clause}", name=props.get('name'), props=props)
            
        # Create Edges
        for e in edges:
            s_remote.run(f"""
                MATCH (a {{name: $source}})
                MATCH (b {{name: $target}})
                MERGE (a)-[r:`{e['type']}`]->(b)
                SET r = $props
            """, source=e['source'], target=e['target'], props=e['props'])

    print("Migration complete!")

if __name__ == "__main__":
    migrate()
