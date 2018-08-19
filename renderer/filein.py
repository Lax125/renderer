def get_offcontents(fn):
  with open(fn, "r") as f:
    chars = f.read()
    f.close()
  lines = chars.split("\n")
  contents = []
  for l in lines:
    if len(l) == 0:
      continue
    words = l.split()
    if words[0] == "OFF":
      continue
    if words[0][0] == "#":
      continue
    contents.append(words)
  return contents
