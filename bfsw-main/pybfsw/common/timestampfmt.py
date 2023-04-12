from argparse import ArgumentParser
import time

p = ArgumentParser()
p.add_argument('unix_time',type=float,help='unix timestamp, like 1640221291.747211')

args = p.parse_args()

s = time.strftime('%y/%m/%d-%H:%M:%S UTC',time.gmtime(args.unix_time))
print(s)
