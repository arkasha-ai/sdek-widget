#!/usr/bin/env python3
"""Check GPU availability and VRAM."""

import torch


def main():
    print("🔍 GPU Check")
    print(f"  PyTorch version: {torch.__version__}")
    print(f"  CUDA available:  {torch.cuda.is_available()}")

    if torch.cuda.is_available():
        print(f"  CUDA version:    {torch.version.cuda}")
        print(f"  GPU count:       {torch.cuda.device_count()}")

        for i in range(torch.cuda.device_count()):
            props = torch.cuda.get_device_properties(i)
            total = props.total_memory / 1024**3
            reserved = torch.cuda.memory_reserved(i) / 1024**3
            allocated = torch.cuda.memory_allocated(i) / 1024**3
            free = total - reserved

            print(f"\n  GPU {i}: {props.name}")
            print(f"    Total VRAM:     {total:.1f} GB")
            print(f"    Reserved:       {reserved:.1f} GB")
            print(f"    Allocated:      {allocated:.1f} GB")
            print(f"    Free (approx):  {free:.1f} GB")
    else:
        print("  ⚠️ No CUDA GPU available!")


if __name__ == "__main__":
    main()
