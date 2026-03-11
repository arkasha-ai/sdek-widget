"""Integration test — full pipeline (requires GPU and Redis)."""

import asyncio
import logging
from brainnet.orchestrator import BrainNetOrchestrator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")


async def test_full_pipeline():
    """Test the complete BrainNet pipeline."""
    print("\n🧠 Starting BrainNet integration test...\n")

    orchestrator = BrainNetOrchestrator(device="cuda")

    try:
        await orchestrator.initialize()
        print("✅ Initialization complete\n")

        # Test 1: Greeting
        print("--- Test 1: Greeting ---")
        response = await orchestrator.process("Привет!")
        print(f"Input:  Привет!")
        print(f"Output: {response}")
        assert len(response) > 0
        print("✅ Greeting test passed\n")

        # Test 2: Question
        print("--- Test 2: Question ---")
        response = await orchestrator.process("Что такое Python?")
        print(f"Input:  Что такое Python?")
        print(f"Output: {response}")
        assert len(response) > 0
        print("✅ Question test passed\n")

        # Test 3: Cache hit (repeat)
        print("--- Test 3: Cache hit ---")
        response = await orchestrator.process("Привет!")
        print(f"Input:  Привет! (repeat)")
        print(f"Output: {response}")
        stats = orchestrator.get_stats()
        print(f"Cache hits: {stats['cache_hits']}")
        assert stats["cache_hits"] >= 1
        print("✅ Cache hit test passed\n")

        # Test 4: Stats
        print("--- Test 4: Stats ---")
        stats = orchestrator.get_stats()
        print(f"Stats: {stats}")
        assert stats["total_requests"] == 3
        print("✅ Stats test passed\n")

        print("🎉 All integration tests passed!")

    finally:
        await orchestrator.shutdown()


if __name__ == "__main__":
    asyncio.run(test_full_pipeline())
