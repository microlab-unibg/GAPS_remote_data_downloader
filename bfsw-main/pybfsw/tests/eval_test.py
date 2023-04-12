import numpy as np
from argparse import ArgumentParser

p = ArgumentParser()
p.add_argument('string')
args = p.parse_args()

y = np.arange(0,100,1)

chars = "01234567890~%^&*()-+/.eybx "
for c in args.string:
    if c not in chars:
        raise ValueError

yy = eval(args.string)
print(yy)
