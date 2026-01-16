# Testing Guide for Integrated Features

## Overview
This guide provides instructions for testing the newly integrated features from `scratches/another_test`.

## Manual Testing (When wx/UI is available)

### Testing Point Caching

```python
from harness_designer.geometry.point import Point
from harness_designer.wrappers.decimal import Decimal

# Test 1: Create points with same db_id
p1 = Point(Decimal(1.0), Decimal(2.0), Decimal(3.0), db_id=100)
p2 = Point(Decimal(99.0), Decimal(99.0), Decimal(99.0), db_id=100)

# Verify they are the same instance
assert p1 is p2, "Points with same db_id should return same instance"
print("✓ Point caching works")

# Test 2: Verify coordinates are preserved
assert p1.x == Decimal(1.0), "Original coordinates should be preserved"
print("✓ Coordinates preserved in cached point")
```

### Testing Callback System

```python
from harness_designer.geometry.point import Point
from harness_designer.wrappers.decimal import Decimal

# Test 1: Basic callback
calls = []
def callback(pt):
    calls.append(pt)

p = Point(Decimal(0.0), Decimal(0.0), Decimal(0.0), db_id=200)
p.bind(callback)
p.x = Decimal(10.0)

assert len(calls) == 1, "Callback should be called once"
print("✓ Basic callback works")

# Test 2: Context manager batching
calls.clear()
with p:
    p.x = Decimal(20.0)
    p.y = Decimal(30.0)
    assert len(calls) == 0, "Callbacks should be suppressed in context"

assert len(calls) == 1, "Callback should fire once after context"
print("✓ Context manager batching works")

# Test 3: Duplicate prevention
calls.clear()
p.bind(callback)  # Bind again
p.x = Decimal(40.0)
assert len(calls) == 1, "Should only call once despite multiple bindings"
print("✓ Duplicate prevention works")

# Test 4: Unbind
calls.clear()
p.unbind(callback)
p.x = Decimal(50.0)
assert len(calls) == 0, "Should not call after unbind"
print("✓ Unbind works")
```

### Testing Wire/Bundle Layout Synchronization

```python
from harness_designer.objects.objects3d.wire_layout import WireLayout
from harness_designer.objects.objects3d.bundle_layout import BundleLayout
from harness_designer.wrappers.decimal import Decimal

# Assuming you have editor3d and db objects set up
wire_layout = WireLayout(editor3d, wire_layout_db_obj)
bundle_layout = BundleLayout(editor3d, bundle_layout_db_obj)

# Get initial position
initial_x = wire_layout._center.x

# Bind wire layout to bundle layout
wire_layout.bind_to_bundle_layout_point(bundle_layout.point)

# Move bundle layout
bundle_layout.point.x = Decimal(100.0)

# Verify wire layout followed
assert wire_layout._center.x == Decimal(100.0), "Wire layout should follow bundle layout"
print("✓ Wire layout synchronization works")

# Unbind
wire_layout.unbind_from_bundle_layout_point()

# Move bundle layout again
bundle_layout.point.x = Decimal(200.0)

# Verify wire layout didn't follow
assert wire_layout._center.x == Decimal(100.0), "Wire layout should not follow after unbind"
print("✓ Unbind from bundle layout works")
```

### Testing Bundle/Wire Relationship

```python
from harness_designer.objects.objects3d.bundle import Bundle
from harness_designer.objects.objects3d.wire import Wire

# Create bundle and wire
bundle = Bundle(editor3d, bundle_db_obj)
wire = Wire(editor3d, wire_db_obj)

# Initially wire should be visible
assert wire.is_visible, "Wire should be visible initially"

# Add wire to bundle
bundle.add_wire(wire)

# Wire should be hidden and reference bundle
assert not wire.is_visible, "Wire should be hidden when bundled"
assert wire.bundle is bundle, "Wire should reference its bundle"
assert bundle.wire_count == 1, "Bundle should track wire"
print("✓ Adding wire to bundle works")

# Remove wire from bundle
bundle.remove_wire(wire)

# Wire should be visible again
assert wire.is_visible, "Wire should be visible when unbundled"
assert bundle.wire_count == 0, "Bundle should not track wire"
print("✓ Removing wire from bundle works")
```

## Integration Testing Checklist

When the full application can run, test these scenarios:

### Point Caching Tests
- [ ] Create two points with same db_id, verify same instance returned
- [ ] Verify WeakValueDictionary allows garbage collection
- [ ] Check that cached points maintain original coordinates
- [ ] Test point creation without db_id (should create new instances)

### Callback Tests
- [ ] Bind callback to point, verify it fires on coordinate change
- [ ] Use context manager to batch updates, verify single callback
- [ ] Bind same callback multiple times, verify only fires once
- [ ] Unbind callback, verify it stops firing
- [ ] Delete object with bound callback, verify weak reference cleanup

### Layout Synchronization Tests
- [ ] Bind wire layout to bundle layout point
- [ ] Move bundle layout, verify wire layout follows
- [ ] Unbind wire layout, verify it stops following
- [ ] Delete bundle layout, verify wire layout cleans up properly
- [ ] Test with multiple wire layouts bound to same bundle layout

### Bundle/Wire Tests
- [ ] Add wire to bundle, verify wire becomes invisible
- [ ] Remove wire from bundle, verify wire becomes visible
- [ ] Delete bundle with wires, verify wires become visible
- [ ] Add multiple wires to bundle, verify all tracked
- [ ] Delete wire in bundle, verify bundle cleans up reference

### Memory Management Tests
- [ ] Create and delete many points with db_id, verify no memory leak
- [ ] Create and delete many callbacks, verify weak references cleaned up
- [ ] Create and delete bundles with wires, verify proper cleanup
- [ ] Monitor WeakValueDictionary size during operations

## Performance Tests

### Point Cache Performance
```python
import time
from harness_designer.geometry.point import Point
from harness_designer.wrappers.decimal import Decimal

# Test cache lookup speed
start = time.time()
for i in range(1000):
    p = Point(Decimal(0.0), Decimal(0.0), Decimal(0.0), db_id=1000)
end = time.time()

print(f"1000 cached lookups: {(end-start)*1000:.2f}ms")
# Should be very fast (typically < 1ms)
```

### Callback Performance
```python
import time
from harness_designer.geometry.point import Point
from harness_designer.wrappers.decimal import Decimal

def dummy_callback(pt):
    pass

p = Point(Decimal(0.0), Decimal(0.0), Decimal(0.0), db_id=2000)

# Bind many callbacks
for i in range(100):
    p.bind(dummy_callback)

# Test callback execution time
start = time.time()
for i in range(100):
    p.x = Decimal(float(i))
end = time.time()

print(f"100 updates with 100 callbacks: {(end-start)*1000:.2f}ms")
# Should handle duplicate prevention efficiently
```

## Known Limitations

1. **wx dependency**: Full integration tests require wx (wxPython) to be installed
2. **Database objects**: Testing layout synchronization requires database objects
3. **Editor context**: Testing 3D objects requires editor3d context

## Debugging Tips

### Enable callback debugging
```python
# Add to Point class temporarily
def __do_callbacks(self):
    print(f"Point {self.db_id} firing {len(self.__callbacks)} callbacks")
    # ... rest of method
```

### Check cache contents
```python
from harness_designer.geometry.point import PointMeta
print(f"Cached points: {len(PointMeta._instances)}")
for db_id in PointMeta._instances:
    print(f"  db_id={db_id}")
```

### Monitor weak references
```python
import gc
gc.collect()  # Force garbage collection
print(f"Cached points after GC: {len(PointMeta._instances)}")
```

## Reporting Issues

When reporting issues with the integrated features, please include:
1. Python version
2. Steps to reproduce
3. Expected vs actual behavior
4. Whether it's related to:
   - Point caching
   - Callback system
   - Layout synchronization
   - Bundle/wire relationships
5. Memory usage observations (if relevant)
