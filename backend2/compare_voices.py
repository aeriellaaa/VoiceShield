"""
compare_voices.py
Runs the real recorded voice and its AI-cloned counterpart through
Backend 1's real detection model, and prints a side-by-side comparison.
Uses the whole file as a single clip (not the streaming chunker) since
these are short, pre-recorded samples rather than a live call.
"""

import asyncio
from model_client import score_chunk


async def analyze(label: str, filepath: str):
    with open(filepath, "rb") as f:
        audio_bytes = f.read()
    result = await score_chunk(audio_bytes, filename=filepath)
    return {
        "label": label,
        "file": filepath,
        "decision": result["decision"],
        "fused_score": result["fused_score"],
        "explanation": result["explanation"],
        "branch_scores": result.get("branch_scores", {}),
    }


def print_result(r):
    print(f"\n{'=' * 50}")
    print(f"  {r['label']}  ({r['file']})")
    print(f"{'=' * 50}")
    print(f"  Decision:      {r['decision'].upper()}")
    print(f"  Fused score:   {r['fused_score']:.4f}  ({r['fused_score']*100:.1f}%)")
    print(f"  Explanation:   {r['explanation']}")
    branches = r["branch_scores"]
    if branches and any(v is not None for v in branches.values()):
        print(f"  Branch weights:")
        for k, v in branches.items():
            if v is not None:
                print(f"    {k:12s} {v*100:.1f}%")


async def main():
    real = await analyze("REAL VOICE 2", "real_voice2_clean.wav")
    cloned = await analyze("AI-CLONED VOICE 2", "cloned_voice2_clean.wav")
    print_result(real)
    print_result(cloned)

    print(f"\n{'=' * 50}")
    print("  SUMMARY")
    print(f"{'=' * 50}")
    print(f"  Real voice   -> {real['decision']:15s} ({real['fused_score']*100:.1f}% clone-likelihood)")
    print(f"  Cloned voice -> {cloned['decision']:15s} ({cloned['fused_score']*100:.1f}% clone-likelihood)")
    gap = abs(cloned['fused_score'] - real['fused_score']) * 100
    print(f"\n  Score separation: {gap:.1f} percentage points")


asyncio.run(main())