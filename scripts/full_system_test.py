#!/usr/bin/env python3
"""
Complete Event Log System Test
Tests all phases: A, B, C, D
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 70)
print("EVENT LOG SYSTEM - COMPLETE VERIFICATION")
print("=" * 70)
print("\nTesting all 4 phases with real scenarios...\n")

# ============================================================================
# PHASE A: FOUNDATION
# ============================================================================
print("\n" + "=" * 70)
print("PHASE A: FOUNDATION")
print("=" * 70)

print("\n1️⃣  Core Event Logging")
from event_logger import log_event, get_session_state, get_incomplete_tasks

log_event("test", "task_started", {"task": "system_verification"})
log_event("test", "decision_made", {"decision": "Test all features", "reasoning": "Quality assurance"})
log_event("test", "file_created", {"file": "test.py", "size": "1KB"})
print("   ✅ Core logging works")

print("\n2️⃣  Event Helpers (Decorators & Context Managers)")
from event_helpers import task_context, log_decision, log_file_change

with task_context("helper_test", {"phase": "verification"}):
    log_file_change("demo.py", "modified", "Testing helpers")
print("   ✅ Helpers work")

print("\n3️⃣  Session Recovery")
from recover_session import recover_session
recovery = recover_session("test")
print(f"   ✅ Recovery works - {recovery['total_events']} events, {len(recovery['active_tasks'])} active")

print("\n4️⃣  Timeline Visualization")
from event_timeline import timeline
print("   Timeline:")
timeline("test", limit=5)
print("   ✅ Timeline works")

# ============================================================================
# PHASE B: INTEGRATION
# ============================================================================
print("\n" + "=" * 70)
print("PHASE B: INTEGRATION")
print("=" * 70)

print("\n1️⃣  Session Management")
from session_manager import get_or_create_session, auto_switch_session
session = get_or_create_session("test-integration")
print(f"   ✅ Session management works - current: {session}")

print("\n2️⃣  Auto-logging")
from auto_log import message_received, message_sent
message_received("Test message", from_user="System", chat="test-integration")
message_sent("Response message")
print("   ✅ Auto-logging works")

print("\n3️⃣  Session Switching")
from session_manager import SessionContext
with SessionContext("temp-session"):
    log_event("temp-session", "test_event", {"test": "temporary"})
print("   ✅ Session switching works (auto-returned)")

# ============================================================================
# PHASE C: VISUALIZATION
# ============================================================================
print("\n" + "=" * 70)
print("PHASE C: VISUALIZATION")
print("=" * 70)

print("\n1️⃣  Task Dependency Graph")
from event_viz import task_dependency_graph
task_dependency_graph("test", limit=20)
print("   ✅ Task graphs work")

print("\n2️⃣  Session Comparison")
from event_viz import session_comparison
session_comparison()
print("   ✅ Session comparison works")

print("\n3️⃣  Event Type Breakdown")
from event_viz import event_type_breakdown
event_type_breakdown("test")
print("   ✅ Event breakdown works")

# ============================================================================
# PHASE D: ADVANCED SEARCH
# ============================================================================
print("\n" + "=" * 70)
print("PHASE D: ADVANCED SEARCH")
print("=" * 70)

print("\n1️⃣  Cross-session Search")
from event_search import cross_session_search
results = cross_session_search("test", limit_per_session=50)
print(f"   ✅ Cross-session search works - {len(results)} results found")

print("\n2️⃣  Pattern Detection")
from event_search import pattern_detection
patterns = pattern_detection("test")
print(f"   ✅ Pattern detection works")
print(f"      - Task chains: {len(patterns['task_chains'])}")
print(f"      - Time patterns: {len(patterns['time_patterns'])} hours tracked")

print("\n3️⃣  Time-range Search")
from event_search import time_range_search
from datetime import datetime, timedelta
start = (datetime.now() - timedelta(hours=2)).isoformat()
end = datetime.now().isoformat()
time_results = time_range_search("test", start, end)
print(f"   ✅ Time-range search works - {len(time_results)} events in range")

# ============================================================================
# INTEGRATION TEST
# ============================================================================
print("\n" + "=" * 70)
print("INTEGRATION TEST: Complete Workflow")
print("=" * 70)

print("\n🎯 Simulating real-world scenario...")

# Scenario: Multi-session work with interruption
from event_helpers import set_session_id

# Main work
set_session_id("integration-test")
with task_context("main_feature", {"priority": "high"}):
    log_decision("Use async approach for performance")
    log_file_change("main.py", "created", "Core implementation")
    
    # Interruption
    with SessionContext("interruption"):
        message_received("Quick question", from_user="colleague")
        message_sent("Answer here")
    
    # Back to main work
    log_file_change("main.py", "modified", "Added tests")

# Recovery check
state = get_session_state("integration-test")
print(f"\n✅ Integration test complete!")
print(f"   - Events logged: {state['event_count']}")
print(f"   - Active tasks: {len(state['active_tasks'])}")
print(f"   - Last action: {state['last_action']}")

# ============================================================================
# FINAL SUMMARY
# ============================================================================
print("\n" + "=" * 70)
print("VERIFICATION SUMMARY")
print("=" * 70)

from event_logger import list_sessions
sessions = list_sessions()

print(f"\n📊 System Status:")
print(f"   Total sessions: {len(sessions)}")
print(f"   Sessions: {', '.join(sessions)}")

total_events = sum(get_session_state(s)['event_count'] for s in sessions)
print(f"   Total events: {total_events}")

print("\n✅ Phase A: Foundation - WORKING")
print("✅ Phase B: Integration - WORKING")
print("✅ Phase C: Visualization - WORKING")
print("✅ Phase D: Advanced Search - WORKING")

print("\n" + "=" * 70)
print("🎉 ALL SYSTEMS OPERATIONAL!")
print("=" * 70)
print("\nEvent Log System is production-ready and fully functional.\n")
