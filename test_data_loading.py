#!/usr/bin/env python
"""
Quick test script to verify data loading is working properly.
Run this after starting the server to test data loading.
"""
import logging
from app.services.loader import load_all
from app.core.cache import cache
from app.vectorstore.policy_index import build_all_indexes

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

print("\n" + "="*60)
print("TESTING DATA LOADING")
print("="*60)

# Load data
print("\n1. Loading data...")
load_all()

print("\n2. Checking loaded states...")
for state_name, state_data in cache["states"].items():
    parks_count = len(state_data.get("parks", []))
    plots_count = len(state_data.get("plots", []))
    pois_count = len(state_data.get("pois", []))
    policies_count = len(state_data.get("policy_chunks", []))
    
    print(f"\n   State: {state_name}")
    print(f"   - Parks: {parks_count}")
    print(f"   - Plots: {plots_count}")
    print(f"   - POIs: {pois_count}")
    print(f"   - Policies: {policies_count}")
    
    if parks_count > 0:
        print(f"   Sample park: {state_data['parks'][0].get('park_name', 'Unknown')}")
    
    if plots_count > 0:
        print(f"   Sample plot: Plot #{state_data['plots'][0].get('plot_number', '?')}")

print("\n3. Building vector indexes...")
build_all_indexes()

print("\n" + "="*60)
print("DATA LOADING TEST COMPLETE")
print("="*60 + "\n")
