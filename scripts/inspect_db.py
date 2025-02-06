#!/usr/bin/env python3
import argparse
from tabulate import tabulate
from pathlib import Path
import sys
import asyncio
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from config.mongodb import MongoDBConnection
from models.mongodb_models import (
    ExecutionModel,
    RevisionModel,
    ProposedTicketModel,
    ProposalCounterModel
)

async def print_collection(db, collection_name):
    """Print contents of a collection in a formatted way"""
    cursor = db[collection_name].find().sort("created_at", -1)
    
    documents = []
    async for doc in cursor:
        # Convert datetime objects to strings for display
        for key, value in doc.items():
            if isinstance(value, datetime):
                doc[key] = value.isoformat()
        documents.append(doc)
    
    if not documents:
        print(f"\nNo records found in {collection_name}")
        return
    
    # Get all unique keys from all documents
    headers = set()
    for doc in documents:
        headers.update(doc.keys())
    headers = sorted(list(headers))
    
    # Convert documents to rows
    rows = []
    for doc in documents:
        row = []
        for header in headers:
            row.append(doc.get(header, ""))
        rows.append(row)
    
    print(f"\n{collection_name.upper()} COLLECTION:")
    print(tabulate(rows, headers=headers, tablefmt="grid"))

async def print_execution_details(db, execution_id):
    """Print detailed information about a specific execution"""
    # Get execution record
    execution_doc = await db.executions.find_one({"execution_id": execution_id})
    
    if not execution_doc:
        print(f"\nNo execution found with ID: {execution_id}")
        return
    
    # Convert datetime objects to strings
    for key, value in execution_doc.items():
        if isinstance(value, datetime):
            execution_doc[key] = value.isoformat()
    
    print("\nEXECUTION DETAILS:")
    print(tabulate([execution_doc], headers=execution_doc.keys(), tablefmt="grid"))
    
    # Get revision history
    cursor = db.revisions.find(
        {"execution_id": execution_id}
    ).sort("created_at", -1)
    
    revisions = []
    async for doc in cursor:
        # Convert datetime objects to strings
        for key, value in doc.items():
            if isinstance(value, datetime):
                doc[key] = value.isoformat()
        revisions.append(doc)
    
    if revisions:
        # Get all unique keys from all revisions
        headers = set()
        for doc in revisions:
            headers.update(doc.keys())
        headers = sorted(list(headers))
        
        # Convert documents to rows
        rows = []
        for doc in revisions:
            row = []
            for header in headers:
                row.append(doc.get(header, ""))
            rows.append(row)
        
        print("\nREVISION HISTORY:")
        print(tabulate(rows, headers=headers, tablefmt="grid"))
    else:
        print("\nNo revisions found for this execution")

async def main():
    parser = argparse.ArgumentParser(description="Inspect MongoDB database")
    parser.add_argument(
        "--collection", 
        choices=["executions", "revisions", "proposed_tickets", "proposal_counters", "all"],
        default="all",
        help="Which collection to inspect"
    )
    parser.add_argument(
        "--execution-id",
        help="Show details for specific execution ID"
    )
    
    args = parser.parse_args()
    
    try:
        db = MongoDBConnection()
        await db.connect()
        
        if args.execution_id:
            await print_execution_details(db.db, args.execution_id)
        else:
            collections = []
            if args.collection == "all":
                collections = [
                    "executions",
                    "revisions",
                    "proposed_tickets",
                    "proposal_counters"
                ]
            else:
                collections = [args.collection]
            
            for collection in collections:
                await print_collection(db.db, collection)
                
        await db.close()
            
    except Exception as e:
        print(f"Error accessing database: {e}")
        print(f"Database connection string: {db.db.client.address if db.db else 'Not connected'}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 