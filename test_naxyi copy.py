slist = {'a': 'sois', 'b': 'sosi'}
with open('test.txt', 'w') as f:
    f.write('\n'.join(slist.values()))
    f.write('\n'.join(slist.values()))
    f.write('\n'.join(slist.values()))