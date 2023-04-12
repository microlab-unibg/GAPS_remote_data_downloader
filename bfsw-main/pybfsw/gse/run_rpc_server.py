from pybfsw.gse.gsequery import rpc_server
from argparse import ArgumentParser

p = ArgumentParser()
p.add_argument(
    "--bind_addr",
    default="127.0.0.1",
    help="IP address to bind RPC server to, default is 127.0.0.1",
)
p.add_argument(
    "--port", default="44555", help="port to bind RPC server to, default is 44555"
)
p.add_argument(
    "--db_file_path",
    help="path to sqlite db file to serve. if none specified, $GSE_DB_PATH is used",
)
args = p.parse_args()

rpc_server(args.bind_addr, args.port, db_file_path=args.db_file_path)
