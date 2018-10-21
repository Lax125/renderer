import copy

class A:
  a = 3
  def __init__(self):
    pass
  def get_a(self):
    return self.a

obj0 = A()
obj0.a = 5

obj1 = copy.copy(obj0)
obj1.a = 7
print(obj0.get_a(), obj1.get_a())

print(
  str
  .join(", ", ["A", "B", "SEE?"])
  .lower()
)
