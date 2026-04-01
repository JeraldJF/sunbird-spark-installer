#!/usr/bin/env python3
"""
Neo4j to JanusGraph CSV-based Migration
1. Reads nodes and relationships from Neo4j → writes to CSV
2. Reads CSV → imports into JanusGraph via HTTP REST API
No gremlinpython, no serialization issues
"""

import sys
import csv
import json
import logging
import os
from datetime import datetime
from neo4j import GraphDatabase
from gremlin_python.driver import client as gremlin_client
from gremlin_python.driver.serializer import GraphSONMessageSerializer

# ============================
# Configuration
# ============================
CONFIG = {
    "neo4j": {
        "host": "{{ .Values.neo4j.host }}",
        "port": {{ .Values.neo4j.port }},
        "username": "{{ .Values.neo4j.username }}",
        "password": "{{ .Values.neo4j.password }}",
        "database": "{{ .Values.neo4j.database }}",
        "nodeLabels": {{ .Values.neo4j.nodeLabels | toJson }},
        "relationships": {{ .Values.neo4j.relationships | toJson }},
    },
    "janusgraph": {
        "host": "{{ .Values.janusgraph.service }}.{{ .Values.janusgraph.namespace }}.svc.cluster.local",
        "port": {{ .Values.janusgraph.port }},
    },
}

NODES_CSV = "/tmp/migration/nodes.csv"
RELS_CSV  = "/tmp/migration/relationships.csv"

# ============================
# Logging
# ============================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler('/var/log/migration/migration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# ============================
# Connect to Neo4j
# ============================
def connect_neo4j():
    uri = f"bolt://{CONFIG['neo4j']['host']}:{CONFIG['neo4j']['port']}"
    auth = (CONFIG['neo4j']['username'], CONFIG['neo4j']['password']) if CONFIG['neo4j']['password'] else None
    driver = GraphDatabase.driver(uri, auth=auth)
    logger.info(f"  Connected to Neo4j at {uri}")
    return driver


# ============================
# Connect to JanusGraph (WebSocket + GraphSON v1 serializer)
# ============================
def connect_janusgraph():
    host = CONFIG['janusgraph']['host']
    port = CONFIG['janusgraph']['port']
    url = f"ws://{host}:{port}/gremlin"
    gc = gremlin_client.Client(url, 'g', message_serializer=GraphSONMessageSerializer())
    logger.info(f"  Connected to JanusGraph at {url}")
    return gc


def gremlin_query(gc, query):
    result = gc.submit(query, {})
    return result.all().result()


# ============================
# Step 1: Export Neo4j → CSV
# ============================
def export_neo4j_to_csv(neo4j_driver):
    logger.info("\n--- Exporting Neo4j data to CSV ---")
    os.makedirs("/tmp/migration", exist_ok=True)

    node_labels = CONFIG['neo4j']['nodeLabels']
    rel_types   = CONFIG['neo4j']['relationships']
    total_nodes = 0
    total_rels  = 0

    with neo4j_driver.session(database=CONFIG['neo4j']['database']) as session:

        # Export nodes
        with open(NODES_CSV, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['node_id', 'label', 'props_json'])
            for label in node_labels:
                result = session.run(f"MATCH (n:{label}) RETURN id(n) AS node_id, labels(n) AS labels, n")
                for record in result:
                    node_obj = record['n']
                    props = {}
                    for key in node_obj.keys():
                        val = node_obj[key]
                        if isinstance(val, bool):
                            props[key] = val
                        elif isinstance(val, int):
                            props[key] = int(val)
                        elif isinstance(val, float):
                            props[key] = float(val)
                        else:
                            props[key] = str(val)
                    writer.writerow([int(record['node_id']), label, json.dumps(props)])
                    total_nodes += 1
        logger.info(f"  Exported {total_nodes} nodes to {NODES_CSV}")

        # Export relationships
        with open(RELS_CSV, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['from_id', 'rel_type', 'to_id', 'props_json'])
            for rel_type in rel_types:
                result = session.run(
                    f"MATCH (a)-[r:{rel_type}]->(b) "
                    f"RETURN id(a) AS from_id, id(b) AS to_id, type(r) AS rel_type, properties(r) AS props"
                )
                for record in result:
                    writer.writerow([
                        int(record['from_id']),
                        record['rel_type'],
                        int(record['to_id']),
                        json.dumps(dict(record['props']))
                    ])
                    total_rels += 1
        logger.info(f"  Exported {total_rels} relationships to {RELS_CSV}")

    return total_nodes, total_rels


# ============================
# Step 2: Import CSV → JanusGraph
# ============================
def import_csv_to_janusgraph(gc):
    logger.info("\n--- Importing CSV data into JanusGraph ---")

    # Drop existing nodes for these labels to avoid duplicates from previous runs
    node_labels = CONFIG['neo4j']['nodeLabels']
    rel_types   = CONFIG['neo4j']['relationships']
    for label in node_labels:
        gremlin_query(gc, f"g.V().hasLabel('{label}').drop().iterate()")
        logger.info(f"  Dropped existing '{label}' vertices from JanusGraph")
    for rel_type in rel_types:
        gremlin_query(gc, f"g.E().hasLabel('{rel_type}').drop().iterate()")
        logger.info(f"  Dropped existing '{rel_type}' edges from JanusGraph")

    total_nodes = 0
    total_rels  = 0
    failed_nodes = 0
    failed_rels  = 0

    # Import nodes
    with open(NODES_CSV, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            node_id = row['node_id']
            label   = row['label']
            props   = json.loads(row['props_json'])

            try:
                prop_str = f".property('neo4j_id', {node_id})"
                for key, value in props.items():
                    safe_key = key.replace("'", "\\'")
                    if isinstance(value, str):
                        safe_val = value.replace("'", "\\'").replace("\\", "\\\\")
                        prop_str += f".property('{safe_key}', '{safe_val}')"
                    elif isinstance(value, bool):
                        prop_str += f".property('{safe_key}', {str(value).lower()})"
                    else:
                        prop_str += f".property('{safe_key}', {value})"

                query = f"g.addV('{label}'){prop_str}.iterate()"
                gremlin_query(gc, query)
                total_nodes += 1

                if total_nodes % 100 == 0:
                    logger.info(f"  Imported {total_nodes} nodes...")

            except Exception as e:
                logger.error(f"  Failed to add node {node_id}: {e}")
                failed_nodes += 1

    logger.info(f"  ✓ Imported {total_nodes} nodes ({failed_nodes} failed)")

    # Import relationships
    with open(RELS_CSV, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            from_id  = row['from_id']
            to_id    = row['to_id']
            rel_type = row['rel_type']

            try:
                query = (
                    f"g.V().has('neo4j_id', {from_id}).as('a')"
                    f".V().has('neo4j_id', {to_id}).as('b')"
                    f".addE('{rel_type}').from('a').to('b').iterate()"
                )
                gremlin_query(gc, query)
                total_rels += 1

            except Exception as e:
                logger.error(f"  Failed to add edge {from_id}-[{rel_type}]->{to_id}: {e}")
                failed_rels += 1

    logger.info(f"  ✓ Imported {total_rels} relationships ({failed_rels} failed)")
    return total_nodes, total_rels


# ============================
# Step 3: Verify counts
# ============================
def verify_migration(neo4j_driver, gc):
    logger.info("\n--- Verification ---")
    node_labels = CONFIG['neo4j']['nodeLabels']
    rel_types   = CONFIG['neo4j']['relationships']

    neo4j_nodes = 0
    neo4j_rels  = 0

    with neo4j_driver.session(database=CONFIG['neo4j']['database']) as session:
        for label in node_labels:
            c = session.run(f"MATCH (n:{label}) RETURN count(n) AS c").single()['c']
            neo4j_nodes += c
        for rel_type in rel_types:
            c = session.run(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) AS c").single()['c']
            neo4j_rels += c

    jg_nodes = 0
    jg_rels  = 0
    for label in node_labels:
        result = gremlin_query(gc, f"g.V().hasLabel('{label}').count()")
        jg_nodes += result[0] if result else 0

    for rel_type in rel_types:
        result = gremlin_query(gc, f"g.E().hasLabel('{rel_type}').count()")
        jg_rels += result[0] if result else 0

    nodes_match = neo4j_nodes == jg_nodes
    rels_match  = neo4j_rels  == jg_rels

    logger.info(f"  Nodes — Neo4j: {neo4j_nodes} | JanusGraph: {jg_nodes} {'✓ MATCH' if nodes_match else '✗ MISMATCH'}")
    logger.info(f"  Edges — Neo4j: {neo4j_rels}  | JanusGraph: {jg_rels}  {'✓ MATCH' if rels_match  else '✗ MISMATCH'}")

    return nodes_match and rels_match


# ============================
# Main
# ============================
def main():
    start = datetime.now()
    logger.info("=" * 60)
    logger.info("Neo4j → JanusGraph CSV Migration")
    logger.info("=" * 60)
    logger.info(f"Source: Neo4j      {CONFIG['neo4j']['host']}:{CONFIG['neo4j']['port']}")
    logger.info(f"Target: JanusGraph {CONFIG['janusgraph']['host']}:{CONFIG['janusgraph']['port']}")

    neo4j_driver = connect_neo4j()
    gc = connect_janusgraph()

    # Step 1: Export
    export_nodes, export_rels = export_neo4j_to_csv(neo4j_driver)

    # Step 2: Import
    import_nodes, import_rels = import_csv_to_janusgraph(gc)

    # Step 3: Verify
    success = verify_migration(neo4j_driver, gc)

    duration = (datetime.now() - start).total_seconds()
    logger.info("\n" + "=" * 60)
    logger.info("MIGRATION COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Exported  nodes        : {export_nodes}")
    logger.info(f"Imported  nodes        : {import_nodes}")
    logger.info(f"Exported  relationships: {export_rels}")
    logger.info(f"Imported  relationships: {import_rels}")
    logger.info(f"Duration               : {duration:.2f}s")
    logger.info(f"Status                 : {'SUCCESS ✓' if success else 'COMPLETED WITH MISMATCHES ⚠'}")
    logger.info("=" * 60)

    neo4j_driver.close()
    gc.close()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
