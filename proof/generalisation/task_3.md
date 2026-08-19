### P15
```python
def f(x):
    w8 = 1
    for i in range(1, 5):
        w8 = w8 * x % i % 19
    return w8
```
examples (input -> correct output):
  f(0) == 4, f(3) == 6, f(7) == 17, f(12) == 11, f(25) == 10, f(41) == 6

### P16
```python
def f(x):
    h6 = x
    for i in range(6):
        h6 = h6 + i * 9
    return h6 * 7
```
examples (input -> correct output):
  f(0) == 2, f(3) == 5, f(7) == 2, f(12) == 0, f(25) == 6, f(41) == 1

### P17
```python
def f(x):
    d3 = min(x, 13)
    d3 = d3 + max(x // 13, 1)
    return d3 * 6
```
examples (input -> correct output):
  f(0) == 6, f(3) == 24, f(7) == 48, f(12) == 78, f(25) == 150, f(41) == 246

### P18
```python
def f(x):
    t4 = x * 7 + 2
    if t4 == 35:
        t4 = t4 - 35
    return t4
```
examples (input -> correct output):
  f(0) == 2, f(3) == 23, f(7) == 16, f(12) == 51, f(25) == 142, f(41) == 254

### P19
```python
def f(x):
    p9 = 0
    for i in range(5):
        p9 = p9 + x % (-5 + i)
    return p9
```
examples (input -> correct output):
  f(0) == 0, f(3) == 15, f(7) == 17, f(12) == 14, f(25) == 13, f(41) == 18
