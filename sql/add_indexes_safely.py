#!/usr/bin/env python3
"""
Script to safely add MySQL indexes using pt-online-schema-change tool
Avoids long table locks, suitable for production environments
"""

import argparse
import logging
import subprocess
import sys
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("db-index-manager")

# Index definitions
INDEXES = {
    "app": [
        {"name": "idx_status", "columns": ["status"], "comment": "Index on app table status field, optimizes queries by status"},
        {"name": "idx_is_hot_status", "columns": ["is_hot", "status"], "comment": "Optimizes queries for hot and active apps"},
        {"name": "idx_is_public_status", "columns": ["is_public", "status"], "comment": "Optimizes queries for public and active apps"},
    ],
    # Can add index definitions for other tables
}

def check_prerequisites():
    """Check if necessary tools are installed"""
    try:
        result = subprocess.run(
            ["which", "pt-online-schema-change"],
            capture_output=True, text=True, check=False
        )
        if result.returncode != 0:
            logger.error("pt-online-schema-change tool not found, please install Percona Toolkit first")
            logger.info("You can install it with the following commands:")
            logger.info("  brew install percona-toolkit  # macOS")
            logger.info("  apt-get install percona-toolkit  # Debian/Ubuntu")
            logger.info("  yum install percona-toolkit  # RHEL/CentOS")
            return False
        return True
    except Exception as e:
        logger.error(f"Error checking prerequisites: {str(e)}")
        return False

def get_existing_indexes(db_config: Dict[str, Any], table: str) -> List[str]:
    """Get existing indexes on the table"""
    try:
        cmd = [
            "mysql",
            f"--host={db_config['host']}",
            f"--port={db_config['port']}",
            f"--user={db_config['user']}",
            f"--password={db_config['password']}",
            db_config['database'],
            "-e", f"SHOW INDEX FROM {table}"
        ]
        
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True
        )
        
        # Parse output to get index names
        lines = result.stdout.strip().split('\n')[1:]  # Skip header line
        indexes = set()
        for line in lines:
            parts = line.split('\t')
            if len(parts) >= 3:
                indexes.add(parts[2])  # Index name is in the 3rd column
        
        return list(indexes)
    except Exception as e:
        logger.error(f"Error getting existing indexes for table {table}: {str(e)}")
        return []

def add_index_safely(db_config: Dict[str, Any], table: str, index_def: Dict[str, Any]) -> bool:
    """Safely add index using pt-online-schema-change"""
    index_name = index_def["name"]
    columns = ", ".join(index_def["columns"])
    
    # Build pt-online-schema-change command
    cmd = [
        "pt-online-schema-change",
        f"h={db_config['host']}",
        f"P={db_config['port']}",
        f"u={db_config['user']}",
        f"p={db_config['password']}",
        f"D={db_config['database']}",
        f"t={table}",
        "--alter", f"ADD INDEX {index_name} ({columns})",
        "--execute",
        "--no-drop-old-table",  # Keep old table for rollback
        "--max-load", "Threads_running=50",  # Limit load
        "--critical-load", "Threads_running=100",
        "--chunk-size", "1000",  # Number of rows to process at once
        "--chunk-time", "0.5",  # Pause time between chunks
        "--set-vars", "innodb_lock_wait_timeout=50",
        "--progress", "time,30",  # Show progress every 30 seconds
        "--recursion-method", "none",  # Avoid recursive triggers
        "--check-interval", "1",  # Check interval
        "--max-lag", "10",  # Maximum replication lag
    ]
    
    try:
        logger.info(f"Starting to add index {index_name} ({columns}) to table {table}...")
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1
        )
        
        # Output progress in real-time
        for line in process.stdout:
            line = line.strip()
            if line:
                logger.info(line)
        
        # Wait for process to complete
        process.wait()
        
        if process.returncode == 0:
            logger.info(f"Successfully added index {index_name} to table {table}")
            return True
        else:
            stderr = process.stderr.read()
            logger.error(f"Failed to add index {index_name} to table {table}: {stderr}")
            return False
    except Exception as e:
        logger.error(f"Error executing pt-online-schema-change: {str(e)}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Safely add MySQL indexes")
    parser.add_argument("--host", default="localhost", help="MySQL host")
    parser.add_argument("--port", type=int, default=3306, help="MySQL port")
    parser.add_argument("--user", required=True, help="MySQL username")
    parser.add_argument("--password", required=True, help="MySQL password")
    parser.add_argument("--database", required=True, help="Database name")
    parser.add_argument("--table", help="Table to add indexes to, if not specified all tables will be processed")
    parser.add_argument("--dry-run", action="store_true", help="Only show operations that would be executed, don't actually execute them")
    
    args = parser.parse_args()
    
    # Check prerequisites
    if not check_prerequisites():
        sys.exit(1)
    
    db_config = {
        "host": args.host,
        "port": args.port,
        "user": args.user,
        "password": args.password,
        "database": args.database
    }
    
    # Determine tables to process
    tables_to_process = [args.table] if args.table else list(INDEXES.keys())
    
    for table in tables_to_process:
        if table not in INDEXES:
            logger.warning(f"No indexes defined for table {table}, skipping")
            continue
        
        logger.info(f"Processing table {table}...")
        
        # Get existing indexes
        existing_indexes = get_existing_indexes(db_config, table)
        logger.info(f"Existing indexes on table {table}: {', '.join(existing_indexes)}")
        
        # Add missing indexes
        for index_def in INDEXES[table]:
            index_name = index_def["name"]
            
            if index_name in existing_indexes:
                logger.info(f"Index {index_name} already exists on table {table}, skipping")
                continue
            
            if args.dry_run:
                columns = ", ".join(index_def["columns"])
                logger.info(f"[DRY RUN] Would add index {index_name} ({columns}) to table {table}")
            else:
                add_index_safely(db_config, table, index_def)
    
    logger.info("Index addition operations completed")

if __name__ == "__main__":
    main() 