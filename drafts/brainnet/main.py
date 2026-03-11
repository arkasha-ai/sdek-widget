#!/usr/bin/env python3
"""BrainNet — Brain-inspired multi-agent AI system.

Usage:
    python main.py [--device cuda|cpu] [--redis redis://localhost:6379]
"""

import asyncio
import argparse
import logging
import sys
import signal

from brainnet.orchestrator import BrainNetOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("brainnet.main")


async def interactive_loop(orchestrator: BrainNetOrchestrator):
    """Interactive chat loop."""
    print("\n" + "=" * 60)
    print("  BrainNet v0.1.0 — Brain-inspired Multi-Agent AI")
    print("  Type 'quit' to exit, 'stats' for pipeline stats")
    print("=" * 60 + "\n")

    while True:
        try:
            # Read input (async-friendly)
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(None, lambda: input("You: ").strip())

            if not text:
                continue
            if text.lower() in ("quit", "exit", "q"):
                break
            if text.lower() == "stats":
                stats = orchestrator.get_stats()
                print(f"\n📊 Pipeline Stats:")
                print(f"  Total requests: {stats['total_requests']}")
                print(f"  Cache hit rate: {stats['cache_hit_rate']:.1%}")
                print(f"  Conflict rate:  {stats['conflict_rate']:.1%}")
                print(f"  Avg time:       {stats['avg_time_ms']:.0f}ms\n")
                continue

            # Process through BrainNet
            response = await orchestrator.process(text)
            print(f"\nBrainNet: {response}\n")

        except EOFError:
            break
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error processing input: {e}", exc_info=True)
            print(f"\n⚠️ Error: {e}\n")


async def main():
    parser = argparse.ArgumentParser(description="BrainNet — Brain-inspired AI")
    parser.add_argument("--device", default="cuda", help="Device (cuda/cpu)")
    parser.add_argument("--redis", default="redis://localhost:6379", help="Redis URL")
    parser.add_argument("--l1-model", default=None, help="L1/L3 model path")
    parser.add_argument("--l2-model", default=None, help="L2 model path")
    args = parser.parse_args()

    orchestrator = BrainNetOrchestrator(
        device=args.device,
        redis_url=args.redis,
        l1_model=args.l1_model,
        l2_model=args.l2_model,
    )

    try:
        await orchestrator.initialize()
        print("\n✅ BrainNet запущен")
        await interactive_loop(orchestrator)
    finally:
        await orchestrator.shutdown()
        print("\n👋 BrainNet остановлен")


if __name__ == "__main__":
    asyncio.run(main())
