import sys
from collections import defaultdict

# Add app to path to import content
sys.path.append(r"e:\Gambit")
from app.design.content import MASTER_BEATS, normalize_choice

counts = defaultdict(int)

for beat in MASTER_BEATS:
    for raw_choice in beat.get("choices", []):
        choice = normalize_choice(raw_choice)
        lanes = choice.get("lanes", {})
        for lane, weight in lanes.items():
            counts[lane] += weight

print("Total Lane Weight Points in MASTER_BEATS:")
for lane, weight in sorted(counts.items(), key=lambda x: x[1], reverse=True):
    print(f"{lane}: {weight}")
