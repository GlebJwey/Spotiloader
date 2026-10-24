slist = [1, 2, 3, 2, 1]
print(reversed(slist[len(slist) // 2:]))
print(slist[:len(slist) // 2] == slist[len(slist) // 2:].reverse())