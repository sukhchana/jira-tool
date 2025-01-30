#!/usr/bin/env python3
import sqlite3
import argparse
from tabulate import tabulate
from pathlib import Path
import sys

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from config.database import DATABASE

def print_table(conn, table_name):
    """Print contents of a table in a formatted way"""
    cursor = conn.cursor()
    
    # Get column names
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    
    # Get data
    cursor.execute(f"SELECT * FROM {table_name} ORDER BY created_at DESC")
    rows = cursor.fetchall()
    
    if not rows:
        print(f"\nNo records found in {table_name}")
        return
    
    print(f"\n{table_name.upper()} TABLE:")
    print(tabulate(rows, headers=columns, tablefmt="grid"))

def print_execution_details(conn, execution_id):
    """Print detailed information about a specific execution"""
    cursor = conn.cursor()
    
    # Get execution record
    cursor.execute("""
        SELECT * FROM executions 
        WHERE execution_id = ?
    """, (execution_id,))
    execution_row = cursor.fetchone()
    
    if not execution_row:
        print(f"\nNo execution found with ID: {execution_id}")
        return
    
    # Get column names for execution
    cursor.execute("PRAGMA table_info(executions)")
    execution_columns = [row[1] for row in cursor.fetchall()]
    
    print("\nEXECUTION DETAILS:")
    print(tabulate([execution_row], headers=execution_columns, tablefmt="grid"))
    
    # Get revision history
    cursor.execute("""
        SELECT * FROM revisions 
        WHERE execution_id = ? 
        ORDER BY created_at DESC
    """, (execution_id,))
    revision_rows = cursor.fetchall()
    
    if revision_rows:
        # Get column names for revisions
        cursor.execute("PRAGMA table_info(revisions)")
        revision_columns = [row[1] for row in cursor.fetchall()]
        
        print("\nREVISION HISTORY:")
        print(tabulate(revision_rows, headers=revision_columns, tablefmt="grid"))
    else:
        print("\nNo revisions found for this execution")

def main():
    parser = argparse.ArgumentParser(description="Inspect SQLite database")
    parser.add_argument(
        "--table", 
        choices=["executions", "revisions", "all"],
        default="all",
        help="Which table to inspect"
    )
    parser.add_argument(
        "--execution-id",
        help="Show details for specific execution ID"
    )
    
    args = parser.parse_args()
    
    try:
        with sqlite3.connect(DATABASE["sqlite"]["path"]) as conn:
            if args.execution_id:
                print_execution_details(conn, args.execution_id)
            else:
                if args.table in ["all", "executions"]:
                    print_table(conn, "executions")
                
                if args.table in ["all", "revisions"]:
                    print_table(conn, "revisions")
                    
    except sqlite3.OperationalError as e:
        print(f"Error accessing database: {e}")
        print(f"Database path: {DATABASE['sqlite']['path']}")
        sys.exit(1)

if __name__ == "__main__":
    main() 