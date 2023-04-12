from pybfsw.gse.gsequery import GSEQuery
import numpy as np
import pandas as pd
from datetime import datetime
from progress.bar import IncrementalBar
import pytz
import sys
from os.path import join

import matplotlib.pyplot as plt

sys.path.append(
    r"/home/lucaghislotti/Downloads/prova_SSL/bfsw-main"
)

# SSH port forwarding to GSE machine
# ssh -L 44555:localhost:44555 nadir@128.32.13.79 -p 55225
# password: jwwgNKN%m

# pip install progress
# pip install quickle
# pit install rpyc


def pd_to_csv(pd, filepath, datetime_start, datetime_stop):
    filename = "data_" + str(datetime_start.day) + \
        "_" + datetime_start.month + "_" + datetime_start.year + "_" + datetime_start.hour + \
        "_" + datetime_start.minute + "_" + datetime_start.second + ".csv"
    out_filepath = join(filepath, filename)
    pd.to_csv(out_filepath)

# It downloads data from the database, and returns it as a pandas dataframe
# :param tstart: The start time of the data you want to download
# :param tstop: the end time of the data you want to download
# :return: A dataframe with the columns: row, module, channel, adcdata, asiceventcode
# row, module, channel, adcdata, asiceventcode = DownloadData(1676468100, 1676471700)


def download_data(tstart, tstop, fp):
    sql = (
        "select gfptrackerpacket.row, module, channel, adcdata, asiceventcode, gfptrackerevent.eventid, gfptrackerevent.eventtime, gfptrackerpacket.gcutime, gfptrackerpacket.sysid - 128 from gfptrackerhit "
        "join gfptrackerevent on gfptrackerevent.rowid = gfptrackerhit.parent "
        "join gfptrackerpacket on gfptrackerpacket.rowid = gfptrackerevent.parent "
    )
    sql += f"where gcutime > {tstart} and gcutime < {tstop}"

    q = GSEQuery(path="127.0.0.1:44555")
    q.dbi.query_start(sql)

    bar = IncrementalBar(
        f"Downloading data from tstart={tstart} to tstop={tstop}:", max=tstop - tstart
    )

    downloaded_data_df = pd.DataFrame(
        columns=[
            "layer",
            "row",
            "module",
            "channel",
            "adcdata",
            "asiceventcode",
            "eventid",
            "gcutime",
        ]
    )

    res = np.array(q.dbi.query_fetch(100000))

    while len(res) > 0:
        bar.goto(res[-1, 7] - tstart)

        # Append data
        row = res[:, 0]
        module = res[:, 1]
        channel = res[:, 2]
        adcdata = res[:, 3]
        asiceventcode = res[:, 4]
        eventid = res[:, 5]
        gcutime = res[:, 7]
        layer = res[:, 8]

        row_to_append = pd.DataFrame(
            {
                "layer": layer,
                "row": row,
                "module": module,
                "channel": channel,
                "adcdata": adcdata,
                "asiceventcode": asiceventcode,
                "eventid": eventid,
                "gcutime": gcutime,
            }
        )
        downloaded_data_df = pd.concat([downloaded_data_df, row_to_append])
        res = np.array(q.dbi.query_fetch(100000))

    bar.finish()
    pd_to_csv(downloaded_data_df, filepath=fp)

    # return downloaded_data_df


# Datetime to timestamp converter function
def datetime_to_timestamp(day, month, year, hour, minutes, seconds=0):
    tz = pytz.timezone("US/Pacific")
    dtime = datetime(year, month, day, hour, minutes, seconds)
    aware = tz.localize(dtime, is_dst=None)
    dtimestamp = int(aware.timestamp())

    return dtimestamp


# Ask user input for data taking
datetime_str_start = input("Start datetime [dd/mm/yyyy, hh:mm:ss]: ")
datetime_str_stop = input("Stop datetime [dd/mm/yyyy, hh:mm:ss]: ")
filepath_folder = input("                Download folder path: ")

datetime_start = datetime.strptime(datetime_str_start, r"%d/%m/%Y, %H:%M:%S")
datetime_stop = datetime.strptime(datetime_str_start, r"%d/%m/%Y, %H:%M:%S")

download_data(datetime_start, datetime_stop, filepath_folder)
      " to " + str(datetime_stop) + "\n")

download_data(datetime_start, datetime_stop, filepath_folder)
