"""Check the order of regions to see if deepcopy is working."""
import copy
from joi_companion.core.world_regions import get_regions

regions1 = get_regions()
print("First call to get_regions():")
print(f"  ID: {id(regions1)}")
print(f"  Keys: {list(regions1.keys())}")

regions2 = get_regions()
print("\nSecond call to get_regions():")
print(f"  ID: {id(regions2)}")
print(f"  Keys: {list(regions2.keys())}")

print(f"\nAre they the same object? {regions1 is regions2}")

# Now test deepcopy
copy1 = copy.deepcopy(regions1)
copy2 = copy.deepcopy(regions1)

print(f"\nDeep copy 1 ID: {id(copy1)}")
print(f"Deep copy 2 ID: {id(copy2)}")
print(f"Are copies the same object? {copy1 is copy2}")
print(f"Are copies equal? {copy1 == copy2}")

# Check individual regions
for region_id in sorted(regions1.keys()):
    print(f"\n{region_id}:")
    print(f"  Original ID: {id(regions1[region_id])}")
    print(f"  Copy1 region ID: {id(copy1[region_id])}")
    print(f"  Copy2 region ID: {id(copy2[region_id])}")
    print(f"  Are copy1 and copy2 regions the same object? {copy1[region_id] is copy2[region_id]}")
