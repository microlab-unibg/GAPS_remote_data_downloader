import numpy as np
from pybfsw.gse.parameter import parameter_from_string, ParameterBank, Parameter
from os.path import expandvars, expanduser
from quickle import dumps, loads
from sqlite3 import connect
import rpyc

# TODO: implement some limiting behavior, to prevent issuing some massive query that hangs the system
# TODO: make sure current where clause handling can handle more than one predicate


def get_db_path():
    env = "$GSE_DB_PATH"
    ret = expanduser(expandvars(env))
    if ret != env:
        return ret
    else:
        return None


def get_project_name():
    env = "$GSE_PROJECT"
    ret = expandvars(env)
    if ret != env:
        return ret.lower()
    else:
        return None


class DBInterface:
    def __init__(self, path=None):
        if path is None:
            path = get_db_path()
        servers = {"local": "127.0.0.1:44555"}
        if path in servers:
            path = servers[path]
        if len(path.split(":")) == 2:
            self.remote = True
            host, port = path.split(":")
            self.connection = rpyc.connect(host, int(port))
        else:
            self.remote = False
            full_path = f"file:{path}?mode=ro"
            self.connection = connect(full_path, uri=True, timeout=2)
        self.path = path
        self.cursor = None

    def query(self, sql):
        if self.remote:
            data = self.connection.root.query(sql)
            return loads(data)
        else:
            return self.connection.execute(sql).fetchall()

    def query_start(self, sql):
        if self.remote:
            self.connection.root.query_start(sql)
        else:
            self.cursor = self.connection.execute(sql)

    def query_fetch(self,n):
        if self.remote:
            data = self.connection.root.query_fetch(n)
            return loads(data)
        else:
            return self.cursor.fetchmany(n)

class DBInterfaceRemote(rpyc.Service):
    def __init__(self, *args, **kwargs):
        self.db_file_path = kwargs["db_file_path"]
        self.cursor = None

    def on_connect(self, conn):
        path = self.db_file_path
        if path is None:
            path = get_db_path()
        full_path = f"file:{path}?mode=ro"
        from sqlite3 import connect

        self.connection = connect(full_path, uri=True, timeout=2)

    def exposed_query(self, sql):
        results = self.connection.execute(sql).fetchall()
        data = dumps(results)
        print("query: ", sql)
        print("transmitting ", len(data), " bytes")
        return data

    def exposed_query_start(self, sql):
        self.cursor = self.connection.execute(sql)

    def exposed_query_fetch(self,n):
        if n > 1000000:
            raise ValueError("fetch size is too large, use n < 1,000,000")
        if self.cursor is None:
            raise RuntimeError("you must call query_start before calling query_fetch")
        return dumps(self.cursor.fetchmany(n))




def rpc_server(host, port, db_file_path=None):

    service = rpyc.utils.helpers.classpartial(
        DBInterfaceRemote, db_file_path=db_file_path
    )
    t = rpyc.utils.server.ThreadedServer(
        service, port=port, hostname=host, protocol_config={"allow_public_attrs": True}
    )
    t.start()


class ParameterGroups:
    def __init__(self, parameters, parameter_bank=None):
        self.groups = {}
        for parameter in parameters:
            if isinstance(parameter, Parameter):
                pass
            else:
                assert isinstance(parameter, str)
                if parameter.startswith("@"):
                    parameter = parameter_bank.get(parameter)
                else:
                    parameter = parameter_from_string(parameter)
            tup = (
                parameter.table,
                parameter.where,
            )  # consider problems with where clauses that are semantically the same but don't compare equal as str
            if tup in self.groups:
                self.groups[tup].append(parameter)
            else:
                self.groups[tup] = [parameter]


class GSEQuery:
    def __init__(self, path=None, project=None):
        if project is None:
            project = get_project_name()
        if project is None:
            project = "none"
            self.parameter_bank = ParameterBank([])
        else:
            if project == "gaps":
                from pybfsw.payloads.gaps.parameters import make_parameter_bank

                self.parameter_bank = make_parameter_bank()
            else:
                raise ValueError(
                    f"unknown project {project}, cannot load parameter bank"
                )

        self.dbi = DBInterface(path=path)
        self.project = project

    def get_project_and_path(self):
        return (self.project, self.dbi.path)

    def time_query3(self, name, ti, tf):

        """
        name is either a parameter name starting with @ or a colon seperated parameter specification.
        ti and tf define the time window to search
        if data is found, a 3-tuple is returned: (time vector, converted Y vector, parameter instance)
        if data is not found, None is returned
        this method can raise a number of exceptions
        """

        if name[0] == "@":
            par = self.parameter_bank.get(name)
        else:
            par = parameter_from_string(name)

        ti = float(ti)
        tf = float(tf)
        if par.where:
            sql = f"select gcutime,{par.column} from {par.table} where (gcutime >= {ti}) and (gcutime <= {tf}) and {par.where} order by gcutime"
        else:
            sql = f"select gcutime,{par.column} from {par.table} where (gcutime >= {ti}) and (gcutime <= {tf}) order by gcutime"
        data = self.dbi.query(sql)
        if data:
            data = np.array(data)
            times = data[:, 0]
            y = data[:, 1]
            Y = par.convert(y)
            return (times, Y, par)
        else:
            return None

    def tracker_query1(self, t1, t2):
        """
        get tracker data between two times.  not meant to be used in real time mode!

        return a list of tracker hit tuples between times t1 and t2.
        t1 and t2 are unix times (for example from time.time())
        the tuples look like:
        (layer,row,module,channel,adcdata,asiceventcode)
        right now, layer is the sysid byte from the tracker event packet header
        """
        t1 = float(t1)
        t2 = float(t2)
        sql = (
            "select gfptrackerpacket.sysid,gfptrackerhit.row,gfptrackerhit.module,gfptrackerhit.channel,gfptrackerhit.adcdata,gfptrackerhit.asiceventcode,gfptrackerpacket.rowid,gfptrackerpacket.gcutime "
            "from gfptrackerhit "
            "join gfptrackerevent on gfptrackerhit.parent = gfptrackerevent.rowid "
            "join gfptrackerpacket on gfptrackerevent.parent = gfptrackerpacket.rowid "
            f"where gfptrackerpacket.gcutime > {t1} and gfptrackerpacket.gcutime <= {t2}"
        )
        data = self.dbi.query(sql)
        if data:
            return data
        else:
            return None

    def tracker_query2(self, lastptr=None):
        """
        get latest tracker data.  this is meant for real time use.

        this method returns a 2-tuple.  The first item is the result set
        and the second item is a special \"pointer\" tuple that points to the last row
        in the tracker table, and is meant to be used with the next
        call of tracker_query2.

        example usage:

        res,lastptr = gsequery.tracker_query2()   #do this at init time.  res will be None.
        res,lastptr = gsequery.tracker_query2(lastptr=lastptr)   #now res will contain the new data since the last call
        res,lastptr = gsequery.tracker_query2(lastptr=lastptr)   #keep doing this to get the data since the last call

        another example usage:

        res,lastptr = gsequery.tracker_query2()   #do this at init time.  res will be None.
        gcutime_start = lastptr[1] #store the gcutime from the first call
        res,lastptr = gsequery.tracker_query2(lastptr=(lasptr[0],gcutime_start)) #res will contain new data since the last call

        The difference between the two approaches is in how they handle a corner case where a new row (with greater rowid) has
        gcutime that is not monotonically increasing.  This could happen if packets are received out of order which can plausibly
        happen with the telemetry streams.  If there is a new row since the last call but with a gcutime that is less than the gcutime
        returned in lastptr from the previous call, the first approach will not return the row and the second approach will.  The reason
        is that the second approach only checks that the row has a gcutime that is greater than the first gcutime read from the DB
        at init time.  The second approach is therefore more robust.

        this method can raise a number of exceptions.
        """

        if lastptr is not None:
            sql = (
                "select gfptrackerpacket.sysid, gfptrackerhit.row, gfptrackerhit.module, gfptrackerhit.channel, gfptrackerhit.adcdata, gfptrackerhit.asiceventcode,"
                "gfptrackerpacket.rowid, gfptrackerpacket.gcutime "
                "from gfptrackerhit "
                "join gfptrackerevent on gfptrackerhit.parent = gfptrackerevent.rowid "
                "join gfptrackerpacket on gfptrackerevent.parent = gfptrackerpacket.rowid "
                f"where gfptrackerpacket.rowid > {lastptr[0]} and gfptrackerpacket.gcutime >= {lastptr[1]} "
                "order by gfptrackerpacket.rowid asc"
            )
            data = self.dbi.query(sql)
            if data:
                return data, (data[-1][-2], data[-1][-1])
            else:
                return None, lastptr
        else:
            # find last row
            sql = (
                "select rowid,gcutime from gfptrackerpacket order by rowid desc limit 1"
            )
            data = self.dbi.query(sql)
            if data:
                rowid, gcutime = data[0]
                return None, (rowid, gcutime)
            else:
                # this will happen if the table is empty
                return None, None

    def tracker_query3(self, sysid, row, module, channel, lastptr=None):
        """
        get latest tracker data for one specific channel.  this is meant for real time use.

        this method returns a 2-tuple.  The first item is the result set
        and the second item is a special \"pointer\" tuple that points to the last row
        in the tracker table, and is meant to be used with the next
        call of tracker_query2.

        example usage:

        res,lastptr = gsequery.tracker_query2()   #do this at init time.  res will be None. Same result if using tracker_query3(sysid, row, module, channel)
        res,lastptr = gsequery.tracker_query3(sysid, row, module, channel, lastptr=lastptr)   #now res will contain the new data since the last call
        res,lastptr = gsequery.tracker_query3(sysid, row, module, channel, lastptr=lastptr)   #keep doing this to get the data since the last call

        another example usage:

        res,lastptr = gsequery.tracker_query2()   #do this at init time.  res will be None. Same result if using tracker_query3(sysid, row, module, channel)
        gcutime_start = lastptr[1] #store the gcutime from the first call
        res,lastptr = gsequery.tracker_query3(sysid, row, module, channel, lastptr=(lasptr[0],gcutime_start)) #res will contain new data since the last call

        The difference between the two approaches is in how they handle a corner case where a new row (with greater rowid) has
        gcutime that is not monotonically increasing.  This could happen if packets are received out of order which can plausibly
        happen with the telemetry streams.  If there is a new row since the last call but with a gcutime that is less than the gcutime
        returned in lastptr from the previous call, the first approach will not return the row and the second approach will.  The reason
        is that the second approach only checks that the row has a gcutime that is greater than the first gcutime read from the DB
        at init time.  The second approach is therefore more robust.

        this method can raise a number of exceptions.
        """

        if lastptr is not None:
            sql = (
                "select gfptrackerpacket.sysid, gfptrackerhit.row, gfptrackerhit.module, gfptrackerhit.channel, gfptrackerhit.adcdata, gfptrackerhit.asiceventcode,"
                "gfptrackerpacket.rowid, gfptrackerpacket.gcutime "
                "from gfptrackerhit "
                "join gfptrackerevent on gfptrackerhit.parent = gfptrackerevent.rowid "
                "join gfptrackerpacket on gfptrackerevent.parent = gfptrackerpacket.rowid "
                f"where gfptrackerpacket.rowid > {lastptr[0]} and gfptrackerpacket.gcutime >= {lastptr[1]} "
                f"and gfptrackerpacket.sysid = {sysid} and gfptrackerhit.row = {row} and gfptrackerhit.module = {module} and gfptrackerhit.channel = {channel} "
                "order by gfptrackerpacket.rowid asc"
            )
            data = self.dbi.query(sql)
            if data:
                return data, (data[-1][-2], data[-1][-1])
            else:
                return None, lastptr
        else:
            # find last row
            sql = (
                "select rowid,gcutime from gfptrackerpacket order by rowid desc limit 1"
            )
            data = self.dbi.query(sql)
            if data:
                rowid, gcutime = data[0]
                return None, (rowid, gcutime)
            else:
                # this will happen if the table is empty
                return None, None

    def time_query1(self, name, ti, tf):

        try:
            if name[0] == "@":
                par = self.parameter_bank.get(name)
            else:
                par = parameter_from_string(name)
        except Exception as e:
            print("name lookup failed: ")
            return None

        try:
            ti = float(ti)
            tf = float(tf)
            if par.where:
                sql = f"select {par.column} from {par.table} where (gcutime >= {ti}) and (gcutime <= {tf}) and {par.where}"
            else:
                sql = f"select gcutime,{par.column} from {par.table} where (gcutime >= {ti}) and (gcutime <= {tf})"
            data = self.dbi.query(sql)
            data = np.array(data)
            times = data[:, 0]
            y = data[:, 1]
            Y, units = par.converter(y)
            return (times, Y, units)
        except Exception as e:
            print("exception while querying DB: ", e)
            return None

    def time_query2(self, names, ti, tf):
        """
        names is an iterable of parameter names.  i.e. ['@labjack_temp_c','pdu0:vbus1']
        ti and tf are the times to search for.  ti < tf.
        Returns a dict where the keys are the names (from the input iterable), and the values are tuples (time,values,units)
        where t is the timestamps, Y is the numpy array of the converted values, and units is a units string

        queries are organized by table, so if user asks for multiple columns, then the table is only queried once
        """
        ti = float(ti)
        tf = float(tf)

        # organize queries by table
        table_map = {}
        for name in names:
            if name[0] == "@":
                table, column = self.alias_map[name].split(":")
            else:
                sp = name.split(":")
                if len(sp) == 2:
                    table, column = sp
                    where = None
                elif len(sp) == 3:
                    table, column, where = sp
                else:
                    print(f"skipping incorrectly formatted name {name}")
                    continue
            tup = (column, name, where)
            if table in table_map:
                table_map[table].append(tup)
            else:
                table_map[table] = [tup]

        res_map = {}
        for table in table_map:
            cols = f"gcutime," + ",".join([col for col, name in table_map[table]])
            sql = (
                f"select {cols} from {table} where gcutime >= {ti} and gcutime <= {tf}"
            )
            data = self.dbi.query(sql)
            data = np.array(data)
            times = data[:, 0]
            i = 1
            for col, name in table_map[table]:
                # look up and apply converter
                # return units too
                y = data[:, i]
                i += 1
                if name in self.converter_map:
                    Y, units = self.converter_map[name](y)
                else:
                    Y, units = y, "raw"
                res_map[name] = (times, Y, units)

        return res_map

    def get_column_names(self, table):
        sql = f"pragma table_info({table})"
        res = self.dbi.query(sql)
        return [t[1] for t in res]

    def get_latest_rows(self, table, limit=1, lastptr=None):

        """
        get the latest rows from a table

        example usage:
        _,last = gsequery.get_latest_rows('mytable') #first call to get pointer to latest row
        data,last = gsequery.get_latest_rows('mytable',n=4,lastptr=last) #returns latest 4 rows
        time.sleep(10)
        data,last = gsequery.get_latest_rows('mytable',n=4,lastptr=last) #returns latest 4 rows
        """

        if lastptr is not None:
            sql = f"select *,rowid,gcutime from {table} where rowid > {lastptr[0]} and gcutime >= {lastptr[1]} order by rowid desc limit {limit}"
            res = self.dbi.query(sql)
            if res:
                return res, (
                    res[0][-2],
                    res[0][-1],
                )  # typical case, first row is latest row, since sql query is descending order
            else:
                return None, lastptr  # no new data
        else:
            sql = f"select rowid,gcutime from {table} order by rowid desc limit 1"
            res = self.dbi.query(sql)
            if res:
                return None, res  # typical case
            else:
                return None, None  # db is empty

    def get_latest_n_rows(self, table, n):

        sql = f"select *,rowid,gcutime from {table} where rowid > (select max(rowid)-{n} from {table})"
        res = self.dbi.query(sql)
        if res:
            return res
        else:
            return None

    def get_rows1(self, table, t1, t2):

        """
        get rows from table between times t1 and t2
        """

        t1 = float(t1)
        t2 = float(t2)
        sql = f"select * from {table} where gcutime >= {t1} and gcutime <= {t2}"
        res = self.dbi.query(sql)
        if res:
            return res
        else:
            return None

    def get_table_names(self):
        sql = "select name from sqlite_master where type='table' and name not like 'sqlite_%';"
        names = self.dbi.query(sql)
        return [n[0] for n in names]

    def get_parameter_bank(self):
        return self.parameter_bank

    def get_latest_time(self, table):
        sql = f"select gcutime from {table} order by gcutime desc limit 1"
        res = self.dbi.query(sql)
        return res[0][0]

    def get_latest_value(self, name):
        if name[0] == "@":
            par = self.parameter_bank.get(name)
        else:
            par = parameter_from_string(name)
        sql = f"select gcutime,{par.column} from {par.table} where gcutime >= (select max(gcutime) from {par.table}) limit 1"
        data = self.dbi.query(sql)
        if data:
            return data[0][0], par.convert(data[0][1]), par
        else:
            return None

    def make_parameter_groups(self, parameters):
        return ParameterGroups(parameters, parameter_bank=self.parameter_bank)

    def get_latest_value_groups(self, parameter_group: ParameterGroups):
        results = {}
        for query_info, parameters in parameter_group.groups.items():
            table, where = query_info
            columns = [parameter.column for parameter in parameters]
            if where is None:
                sql = f"select gcutime,{','.join(columns)} from {table} where gcutime >= (select max(gcutime) from {table}) limit 1"
            else:
                sql = f"select gcutime,{','.join(columns)} from {table} where gcutime >= (select max(gcutime) from {table}) and {where} limit 1"
            res = self.dbi.query(sql)
            if res:
                res = res[0]
                gcutime = res[0]
                for i, parameter in enumerate(parameters):
                    results[parameter.name] = (
                        gcutime,
                        parameter.convert(res[i + 1]),
                        parameter,
                    )
            else:
                for parameter in parameters:
                    results[parameter.name] = None

        return results
