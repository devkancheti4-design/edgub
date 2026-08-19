### P10
```python
def f(x):
    r4 = 0
    return r4
```
examples (input -> correct output):
  f(0) == 0, f(3) == 6, f(7) == 14, f(12) == 5, f(25) == 12, f(41) == 6

### P11
```python
def f(x):
    p3 = x
    while p3 > 22:
        p3 = p3 // -4
    return p3 + 7
```
examples (input -> correct output):
  f(0) == 7, f(3) == 10, f(7) == 14, f(12) == 19, f(25) == 13, f(41) == 17

### P12
```python
def f(x):
    a2 = [x * 5, x // 1, x + 39]
    return sum(a2) - 5
```
examples (input -> correct output):
  f(0) == 34, f(3) == 43, f(7) == 50, f(12) == 60, f(25) == 84, f(41) == 117

### P13
```python
def f(x):
    if x % 3 == 0:
        return x // 3 + 3
    return x // 3 - 17
```
examples (input -> correct output):
  f(0) == 3, f(3) == 4, f(7) == 4, f(12) == 7, f(25) == 58, f(41) == 106

### P14
```python
def f(x):
    h3 = abs(x - 26)
    return h3 * -4 if h3 < 5 else h3 + 4
```
examples (input -> correct output):
  f(0) == 30, f(3) == 27, f(7) == 23, f(12) == 18, f(25) == 4, f(41) == 19
