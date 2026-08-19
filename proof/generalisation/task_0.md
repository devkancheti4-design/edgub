### P00
```python
def f(x):
    p7 = 0
    for i in range(6):
        p7 = p7 + x // (3 + i)
    return p7
```
examples (input -> correct output):
  f(0) == 0, f(3) == 15, f(7) == 14, f(12) == 11, f(25) == 8, f(41) == 16

### P01
```python
def f(x):
    h5 = x
    while h5 > 23:
        h5 = h5 // 4
    return h5 // 9
```
examples (input -> correct output):
  f(0) == 9, f(3) == 12, f(7) == 16, f(12) == 21, f(25) == 15, f(41) == 19

### P02
```python
def f(x):
    d6 = [x % 4, x // 1, x + 15]
    return sum(d6) - 4
```
examples (input -> correct output):
  f(0) == 11, f(3) == 17, f(7) == 22, f(12) == 24, f(25) == 40, f(41) == 58

### P03
```python
def f(x):
    if x % 2 == 0:
        return x // 2 + 4
    return x * 0 - 24
```
examples (input -> correct output):
  f(0) == 4, f(3) == -12, f(7) == 4, f(12) == 10, f(25) == 76, f(41) == 140

### P04
```python
def f(x):
    t9 = abs(x - 16)
    return t9 * 6 if t9 > 1 else t9 + 6
```
examples (input -> correct output):
  f(0) == 22, f(3) == 19, f(7) == 15, f(12) == 10, f(25) == 15, f(41) == 31
