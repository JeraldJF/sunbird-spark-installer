#!/usr/bin/env python3
"""
Cassandra to YugabyteDB Migration using PySpark

IMPORTANT: Two DIFFERENT hosts required
- cassandra_source.host → Reads FROM Cassandra (port 9042)
- yugabyte_ycql.host → Writes TO YugabyteDB (port 9043)

If hosts are the same, migrations will fail!
See HOST_CONFIGURATION.md for setup details.

Features:
- High-performance bulk migration for multiple keyspaces
- Reads all tables from Cassandra keyspaces dynamically
- Parallel distributed processing using Spark
- Writes to YugabyteDB YCQL (Cassandra-compatible API)
- Optimized for large datasets
"""

import sys
import logging
from datetime import datetime
from pyspark.sql import SparkSession
from pyspark.sql.functions import col
import json
from cassandra.cluster import Cluster, BatchStatement
from cassandra import ProtocolVersion

# ============================
# Configuration
# ============================
CONFIG = {
    # Cassandra Source Connection (READ FROM)
    "cassandra_source": {
        "host": "{{ .Values.cassandra.host }}",
        "port": {{ .Values.cassandra.port }},
        "keyspaces": {{ .Values.cassandra.keyspaces | toJson }},
        "tables": None,
        "username": {{ if .Values.cassandra.username }}"{{ .Values.cassandra.username }}"{{ else }}None{{ end }},
        "password": {{ if .Values.cassandra.password }}"{{ .Values.cassandra.password }}"{{ else }}None{{ end }},
    },
    # YugabyteDB Target (YCQL - Cassandra Compatible) (WRITE TO)
    "yugabyte_ycql": {
        "host": "{{ .Values.yugabyte.host }}",
        "port": {{ .Values.yugabyte.port }},
        "username": {{ if .Values.yugabyte.username }}"{{ .Values.yugabyte.username }}"{{ else }}None{{ end }},
        "password": {{ if .Values.yugabyte.password }}"{{ .Values.yugabyte.password }}"{{ else }}None{{ end }},
    },
    # Spark Configuration (optimized for bulk migration)
    "spark": {
        "executor_memory": "4g",
        "driver_memory": "2g",
        "executor_cores": 4,
        "num_executors": 4,
        "cassandra_partitions": 64,
        "rdd_read_timeout": "300000",
    },
}

# ============================
# Logging Setup
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
# Spark Session Setup
# ============================
def create_spark_session():
    """Create and configure Spark session optimized for bulk migration"""
    spark = SparkSession.builder \
        .appName("CassandraToYugabyteDB-BulkMigration") \
        .config("spark.executor.memory", CONFIG["spark"]["executor_memory"]) \
        .config("spark.driver.memory", CONFIG["spark"]["driver_memory"]) \
        .config("spark.executor.cores", str(CONFIG["spark"]["executor_cores"])) \
        .config("spark.sql.shuffle.partitions", "256") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .config("spark.cassandra.connection.host", CONFIG["cassandra_source"]["host"]) \
        .config("spark.cassandra.connection.port", str(CONFIG["cassandra_source"]["port"])) \
        .config("spark.cassandra.read.timeout_ms", CONFIG["spark"]["rdd_read_timeout"]) \
        .config("spark.cassandra.write.consistency", "ONE") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")
    return spark

# ============================
# Get Tables from Cassandra
# ============================
def get_keyspace_tables(spark, keyspace):
    """Fetch all tables from a specific keyspace using cassandra-driver"""
    try:
        # Check if tables manually specified
        if CONFIG["cassandra_source"].get("tables"):
            tables = CONFIG["cassandra_source"]["tables"]
            logger.info(f"  Using manually specified tables: {', '.join(tables)}")
            return tables

        logger.info(f"  Auto-discovering tables in keyspace: {keyspace}")

        # Use cassandra-driver to query system tables (avoids Spark routing issues)
        try:
            cassandra_host = CONFIG["cassandra_source"]["host"]
            cassandra_port = CONFIG["cassandra_source"]["port"]

            cluster = Cluster([cassandra_host], port=cassandra_port, protocol_version=4)
            session = cluster.connect()

            tables = []

            # Try Cassandra 3.11 system.schema_columnfamilies first (old version)
            try:
                result = session.execute(
                    f"SELECT columnfamily_name FROM system.schema_columnfamilies WHERE keyspace_name = '{keyspace}'"
                )
                tables = [row.columnfamily_name for row in result]

                if tables:
                    logger.info(f"  Found {len(tables)} table(s) via system.schema_columnfamilies: {', '.join(tables)}")
                    session.shutdown()
                    cluster.shutdown()
                    return tables

            except Exception as e1:
                logger.info(f"  system.schema_columnfamilies not available: {str(e1)[:60]}")

            # Try Cassandra 4.0+ system_schema.tables (new version)
            try:
                result = session.execute(
                    f"SELECT table_name FROM system_schema.tables WHERE keyspace_name = '{keyspace}'"
                )
                tables = [row.table_name for row in result]

                if tables:
                    logger.info(f"  Found {len(tables)} table(s) via system_schema.tables: {', '.join(tables)}")
                    session.shutdown()
                    cluster.shutdown()
                    return tables

            except Exception as e2:
                logger.info(f"  system_schema.tables not available: {str(e2)[:60]}")

            session.shutdown()
            cluster.shutdown()

            if not tables:
                logger.warning(f"  No tables found in keyspace {keyspace}")

            return tables

        except Exception as e:
            logger.error(f"  Failed to connect to Cassandra for auto-discovery: {str(e)[:80]}")
            return []

    except Exception as e:
        logger.error(f"  Error fetching tables from {keyspace}: {str(e)}")
        return []

# ============================
# Verify Counts Before/After Migration
# ============================
def get_cassandra_count(keyspace, table_name):
    """Get row count from Cassandra using cassandra-driver"""
    try:
        cassandra_host = CONFIG["cassandra_source"]["host"]
        cassandra_port = CONFIG["cassandra_source"]["port"]

        cluster = Cluster([cassandra_host], port=cassandra_port, protocol_version=4)
        session = cluster.connect(keyspace)

        result = session.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = result[0][0] if result else 0

        session.shutdown()
        cluster.shutdown()
        return count
    except Exception as e:
        logger.warning(f"      Failed to get Cassandra count: {str(e)[:60]}")
        return None

def get_yugabyte_count(keyspace, table_name):
    """Get row count from YugabyteDB using cassandra-driver"""
    try:
        yb_host = CONFIG["yugabyte_ycql"]["host"]
        yb_port = CONFIG["yugabyte_ycql"]["port"]

        cluster = Cluster([yb_host], port=yb_port, protocol_version=4)
        session = cluster.connect(keyspace)

        result = session.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = result[0][0] if result else 0

        session.shutdown()
        cluster.shutdown()
        return count
    except Exception as e:
        logger.warning(f"      Failed to get YugabyteDB count: {str(e)[:60]}")
        return None

# ============================
# Direct Stream from Cassandra to YugabyteDB
# ============================
def stream_cassandra_to_yugabyte(keyspace, table_name):
    """Stream data directly from Cassandra to YugabyteDB using cassandra-driver"""
    try:
        # Source: Cassandra
        cassandra_host = CONFIG["cassandra_source"]["host"]
        cassandra_port = CONFIG["cassandra_source"]["port"]

        cass_cluster = Cluster([cassandra_host], port=cassandra_port, protocol_version=4)
        cass_session = cass_cluster.connect(keyspace)

        # Target: YugabyteDB
        yb_host = CONFIG["yugabyte_ycql"]["host"]
        yb_port = CONFIG["yugabyte_ycql"]["port"]

        yb_cluster = Cluster([yb_host], port=yb_port, protocol_version=4)
        yb_session = yb_cluster.connect(keyspace)

        # Read from Cassandra
        result = cass_session.execute(f"SELECT * FROM {table_name}")
        rows = result.all()
        row_count = len(rows)

        if row_count == 0:
            logger.info(f"      Read {row_count} rows (empty table)")
            cass_session.shutdown()
            cass_cluster.shutdown()
            yb_session.shutdown()
            yb_cluster.shutdown()
            return row_count

        # Get column names for INSERT
        column_names = result.column_names
        columns_str = ", ".join(column_names)
        placeholders = ", ".join(["?" for _ in column_names])
        insert_query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"

        # Prepare statement for batch writes
        prepared_stmt = yb_session.prepare(insert_query)

        # Stream rows directly to YugabyteDB
        batch_size = 100
        batch = []
        for row in rows:
            batch.append(prepared_stmt.bind(row))

            # Write in batches
            if len(batch) >= batch_size:
                batch_stmt = BatchStatement()
                for stmt in batch:
                    batch_stmt.add(stmt)
                yb_session.execute(batch_stmt)
                batch = []

        # Write remaining rows
        if batch:
            batch_stmt = BatchStatement()
            for stmt in batch:
                batch_stmt.add(stmt)
            yb_session.execute(batch_stmt)

        cass_session.shutdown()
        cass_cluster.shutdown()
        yb_session.shutdown()
        yb_cluster.shutdown()

        logger.info(f"      Streamed {row_count:,} rows")
        return row_count

    except Exception as e:
        logger.error(f"      Failed to stream: {str(e)[:80]}")
        import traceback
        logger.error(f"      Stack trace: {traceback.format_exc()[:200]}")
        return 0

# ============================
# Get Table Schema from Cassandra
# ============================
def get_table_schema_from_cassandra(keyspace, table_name):
    """Read column definitions and primary key from Cassandra to build CREATE TABLE"""
    cassandra_host = CONFIG["cassandra_source"]["host"]
    cassandra_port = CONFIG["cassandra_source"]["port"]

    cluster = Cluster([cassandra_host], port=cassandra_port, protocol_version=4)
    session = cluster.connect()

    # Get columns with their types and kind (partition_key, clustering, regular)
    rows = session.execute(
        f"SELECT column_name, type, kind, position FROM system_schema.columns "
        f"WHERE keyspace_name = '{keyspace}' AND table_name = '{table_name}'"
    )
    columns = list(rows)

    session.shutdown()
    cluster.shutdown()

    if not columns:
        return None

    # Separate by kind
    partition_keys = sorted([c for c in columns if c.kind == 'partition_key'], key=lambda c: c.position)
    clustering_cols = sorted([c for c in columns if c.kind == 'clustering'], key=lambda c: c.position)
    regular_cols = [c for c in columns if c.kind not in ('partition_key', 'clustering')]

    # Build column definitions
    col_defs = []
    for c in partition_keys + clustering_cols + regular_cols:
        col_defs.append(f"{c.column_name} {c.type}")

    # Build PRIMARY KEY clause
    pk_cols = [c.column_name for c in partition_keys]
    ck_cols = [c.column_name for c in clustering_cols]

    if len(pk_cols) == 1 and not ck_cols:
        primary_key = f"PRIMARY KEY ({pk_cols[0]})"
    elif not ck_cols:
        primary_key = f"PRIMARY KEY (({', '.join(pk_cols)}))"
    else:
        primary_key = f"PRIMARY KEY (({', '.join(pk_cols)}), {', '.join(ck_cols)})"

    create_stmt = (
        f"CREATE TABLE IF NOT EXISTS {keyspace}.{table_name} "
        f"({', '.join(col_defs)}, {primary_key})"
    )
    return create_stmt


# ============================
# Check/Create YugabyteDB Schema
# ============================
def ensure_yugabyte_schema(keyspace, table_name):
    """Verify keyspace and table exist on YugabyteDB, create if missing"""
    try:
        yb_host = CONFIG["yugabyte_ycql"]["host"]
        yb_port = CONFIG["yugabyte_ycql"]["port"]

        cluster = Cluster([yb_host], port=yb_port, protocol_version=4)
        session = cluster.connect()

        # Check if keyspace exists, create if missing
        try:
            session.execute(f"SELECT keyspace_name FROM system.schema_keyspaces WHERE keyspace_name = '{keyspace}'")
            logger.info(f"      Keyspace '{keyspace}' exists on YugabyteDB")
        except:
            logger.warning(f"      Keyspace '{keyspace}' NOT found, creating...")
            replication_str = "{'class': 'SimpleStrategy', 'replication_factor': 1}"
            session.execute(f"CREATE KEYSPACE IF NOT EXISTS {keyspace} WITH REPLICATION = {replication_str}")
            logger.info(f"      ✓ Created keyspace '{keyspace}'")

        # Check if table exists, create from Cassandra schema if missing
        try:
            session.execute(f"SELECT COUNT(*) FROM {keyspace}.{table_name}")
            logger.info(f"      Table '{keyspace}.{table_name}' exists on YugabyteDB")
        except:
            logger.warning(f"      Table '{keyspace}.{table_name}' NOT found, auto-creating from Cassandra schema...")
            create_stmt = get_table_schema_from_cassandra(keyspace, table_name)
            if create_stmt:
                logger.info(f"      DDL: {create_stmt}")
                session.execute(create_stmt)
                logger.info(f"      ✓ Created table '{keyspace}.{table_name}' on YugabyteDB")
            else:
                logger.error(f"      ✗ Could not read schema from Cassandra for {keyspace}.{table_name}")
                session.shutdown()
                cluster.shutdown()
                return False

        session.shutdown()
        cluster.shutdown()
        return True

    except Exception as e:
        logger.warning(f"      Failed to verify YugabyteDB schema: {str(e)[:80]}")
        return False

# ============================
# Main Migration Process
# ============================
def migrate_all(spark):
    """Main migration function for all keyspaces"""
    start_time = datetime.now()
    logger.info("=" * 80)
    logger.info("Cassandra → YugabyteDB Bulk Migration (Production)")
    logger.info("=" * 80)
    logger.info(f"\nConnecting to:")
    logger.info(f"  Source: Cassandra at {CONFIG['cassandra_source']['host']}:{CONFIG['cassandra_source']['port']}")
    logger.info(f"  Target: YugabyteDB at {CONFIG['yugabyte_ycql']['host']}:{CONFIG['yugabyte_ycql']['port']}\n")

    keyspaces = CONFIG["cassandra_source"]["keyspaces"]
    migration_stats = {
        "start_time": start_time.isoformat(),
        "keyspaces": {}
    }

    total_tables = 0
    total_rows = 0
    total_success = 0
    total_failed = 0

    # Migrate each keyspace
    for ks_idx, keyspace in enumerate(keyspaces, 1):
        logger.info(f"\n[{ks_idx}/{len(keyspaces)}] Keyspace: {keyspace}")

        # Get tables in this keyspace
        tables = get_keyspace_tables(spark, keyspace)
        if not tables:
            logger.warning(f"  No tables found in {keyspace}, skipping")
            migration_stats["keyspaces"][keyspace] = {"tables": 0, "success": 0, "failed": 0, "rows": 0}
            continue

        ks_stats = {"tables": 0, "success": 0, "failed": 0, "rows": 0, "table_details": {}}

        # Migrate each table in keyspace
        for tbl_idx, table_name in enumerate(tables, 1):
            logger.info(f"    [{tbl_idx}/{len(tables)}] {table_name}")

            try:
                # Verify Cassandra count BEFORE migration
                cassandra_count_before = get_cassandra_count(keyspace, table_name)
                if cassandra_count_before is not None:
                    logger.info(f"      [BEFORE] Cassandra count: {cassandra_count_before:,} rows")
                else:
                    logger.warning(f"      [BEFORE] Could not verify Cassandra count")

                # Verify YugabyteDB schema before streaming
                ensure_yugabyte_schema(keyspace, table_name)

                # Direct stream from Cassandra to YugabyteDB
                row_count = stream_cassandra_to_yugabyte(keyspace, table_name)

                if row_count > 0 or cassandra_count_before == 0:
                    # Verify YugabyteDB count AFTER migration
                    yugabyte_count_after = get_yugabyte_count(keyspace, table_name)
                    if yugabyte_count_after is not None:
                        logger.info(f"      [AFTER] YugabyteDB count: {yugabyte_count_after:,} rows")
                        if yugabyte_count_after == cassandra_count_before:
                            logger.info(f"      ✓ Row counts match! Migration verified.")
                        else:
                            logger.warning(f"      ⚠ Row count mismatch! Cassandra: {cassandra_count_before}, YugabyteDB: {yugabyte_count_after}")
                    else:
                        logger.warning(f"      [AFTER] Could not verify YugabyteDB count")

                    ks_stats["success"] += 1
                    ks_stats["rows"] += row_count
                    total_rows += row_count
                    total_success += 1
                    ks_stats["table_details"][table_name] = {
                        "status": "SUCCESS",
                        "rows": row_count,
                        "cassandra_before": cassandra_count_before,
                        "yugabyte_after": yugabyte_count_after
                    }
                else:
                    ks_stats["failed"] += 1
                    ks_stats["table_details"][table_name] = {
                        "status": "FAILED",
                        "rows": row_count,
                        "cassandra_before": cassandra_count_before
                    }
                    total_failed += 1

            except Exception as e:
                logger.error(f"      Error: {str(e)[:80]}")
                ks_stats["failed"] += 1
                ks_stats["table_details"][table_name] = {"status": "FAILED"}
                total_failed += 1

        ks_stats["tables"] = len(tables)
        migration_stats["keyspaces"][keyspace] = ks_stats
        total_tables += len(tables)

    # Final Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    logger.info("\n" + "=" * 80)
    logger.info("MIGRATION COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Keyspaces: {len(keyspaces)}")
    logger.info(f"Total Tables: {total_tables}")
    logger.info(f"Successful: {total_success}")
    logger.info(f"Failed: {total_failed}")
    logger.info(f"Total Rows Migrated: {total_rows:,}")
    logger.info(f"Duration: {duration:.2f}s ({duration/60:.1f}m)")
    if duration > 0:
        logger.info(f"Throughput: {total_rows/duration:.0f} rows/sec")
    logger.info("=" * 80)

    # Save report
    migration_stats["end_time"] = end_time.isoformat()
    migration_stats["duration_seconds"] = duration
    migration_stats["total_tables"] = total_tables
    migration_stats["total_rows"] = total_rows
    migration_stats["total_success"] = total_success
    migration_stats["total_failed"] = total_failed

    with open('/var/log/migration/migration_report.json', 'w') as f:
        json.dump(migration_stats, f, indent=2)

    return total_failed == 0

# ============================
# Entry Point
# ============================
if __name__ == "__main__":
    try:
        success = migrate_all(None)
        sys.exit(0 if success else 1)

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)
