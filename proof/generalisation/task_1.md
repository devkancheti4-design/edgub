### P05
```python
def f(x):
    t8 = -1
    for i in range(1, 7):
        t8 = (t8 * x + i) % 40
    return t8
```
examples (input -> correct output):
  f(0) == 6, f(3) == 32, f(7) == 4, f(12) == 34, f(25) == 6, f(41) == 22

### P06
```python
def f(x):
    s7 = [i for i in range(7) if (x + i) % 3 == 0]
    return len(s7) * -7 + x % 3
```
examples (input -> correct output):
  f(0) == 21, f(3) == 21, f(7) == 15, f(12) == 21, f(25) == 15, f(41) == 16

### P07
```python
def f(x):
    t8 = x
    for i in range(4):
        t8 = t8 * (i * 9)
    return t8 % 8
```
examples (input -> correct output):
  f(0) == 6, f(3) == 1, f(7) == 5, f(12) == 2, f(25) == 7, f(41) == 7

### P08
```python
def f(x):
    p1 = min(x, 27)
    p1 = p1 + max(x + 27, 7)
    return p1 * 4
```
examples (input -> correct output):
  f(0) == 28, f(3) == 40, f(7) == 56, f(12) == 76, f(25) == 128, f(41) == 164

### P09
```python
def f(x):
    u3 = x * 5 % 3
    if u3 > 25:
        u3 = u3 - 25
    return u3
```
examples (input -> correct output):
  f(0) == 3, f(3) == 18, f(7) == 13, f(12) == 38, f(25) == 103, f(41) == 183
