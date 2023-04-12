import numpy as np
from pybfsw.gse.parameter import Parameter, ParameterBank


def pdu_power(x):
    return x

def pdu_temp(x):
    voltage = (x * 2.5) / 4096.0
    temp = ((voltage - 0.750) / 0.10) + 25.0
    return temp


def pdu_voltage(x):
    sc = 32.0 / 65536.0
    return x * sc


def pdu_current(x):
    sc = 0.1 / (0.01 * 65536.0)
    return sc * x


def pdu_power_acc(x):
    PwrFSR = 3.2 / 0.01  # 3.2V^2 / 0.01 Ohms = 320 Watts (eq 4-5)
    return (x / 2**28) * (
        PwrFSR / 1024.0
    )  # this is an energy, (Watts / sampling rate)


def asic_temp(x):
    # returns deg C
    Gsh = 5.0
    Vt = 0.9 - (x - 1024) * 0.00172 / Gsh
    return (1.0256 - Vt) / 0.0056


def asic_leak(x, R):
    return ((1024 - x) * 0.00176) / (5.14 * 10 * R)


def asic_leak_warm(x):
    # returns nA
    return asic_leak(x, 3600) * 1e9


def asic_leak_cold(x):
    # returns nA
    return asic_leak(x, 1950000) * 1e9

def cooling_current(x):
    return (5*x/4096-1.25)*0.1650/4.1/0.02

def cooling_board_temp(x):
    return (5*x/4096)*100-273.2

def cooling_fpga_v(x):
    return 40*x/4096

def cooling_fpga_i(x):
    return 3*x/4096

def cooling_fpga_p(x):
    return (5*x/4096)*23.199-5.8304

def cooling_rtd(x):
    #r = 1+2.9093e-3*x-5.775e-7*x*x
    return x
    #NOTE talk to alex

# <<< conversion functions


def make_parameter_bank():

    parameters = []

    for i in range(3):
        for j in range(8):
            # name = f"@pdu{i}_v{j}"
            p = Parameter(
                f"@pdu{i}_v{j}",
                "pdu",
                "vbus_avg{j}",
                where=f"pduid={i}",
                converter=pdu_voltage,
                units="volts",
                comment=f"average voltage for pdu {i} channel {j}",
            )
            parameters.append(p)
            p = Parameter(
                f"@pdu{i}_v{j}_inst",
                "pdu",
                "vbus{j}",
                where=f"pduid={i}",
                converter=pdu_voltage,
                units="volts",
                comment=f"instantaneous voltage for pdu {i} channel {j}",
            )
            parameters.append(p)
            p = Parameter(
                f"@pdu{i}_i{j}",
                "pdu",
                "vsense_avg{j}",
                where=f"pduid={i}",
                converter=pdu_current,
                units="amps",
                comment=f"average current for pdu {i} channel {j}",
            )
            parameters.append(p)
            p = Parameter(
                f"@pdu{i}_i{j}_inst",
                "pdu",
                "vsense{j}",
                where=f"pduid={i}",
                converter=pdu_current,
                units="amps",
                comment=f"instantaneous current for pdu {i} channel {j}",
            )
            parameters.append(p)
            p = Parameter(
                f"@pdu{i}_temp{j}",
                "pdu",
                "temp{j}",
                where=f"pduid={i}",
                converter=pdu_temp,
                units="degC",
                comment=f"load switch temperature on pdu {i} channel {j}",
            )
            parameters.append(p)
            p = Parameter(
                f"@pdu{i}_pow{j}_inst",
                "pdu",
                "vpower{j}",
                where=f"pduid={i}",
                converter=pdu_power,
                units="W",
                comment=f"instantaneus power on pdu {i} channel {j}",
            )
            parameters.append(p)
            p = Parameter(
                f"@pdu{i}_pow{j}_acc",
                "pdu",
                "vpower_acc{j}",
                where=f"pduid={i}",
                converter=pdu_power,
                units="W",
                comment="accumulated power on pdu {i} channel {j}",
            )
            parameters.append(p)

    ###############TRACKER COUNTERS###############

    for l in range(10):

        p = Parameter(
            f"@elapsedtime_l{l}",
            "gfptrackercounters",
            "elapsedtime",
            where=f"sysid={128+l}",
        )
        parameters.append(p)
        p = Parameter(
            f"@busytime_l{l}", "gfptrackercounters", "busytime", where=f"sysid={128+l}"
        )
        parameters.append(p)
        p = Parameter(
            f"@busycount_l{l}",
            "gfptrackercounters",
            "busycount",
            where=f"sysid={128+l}",
        )
        parameters.append(p)
        p = Parameter(
            f"@lvsyncerrors_l{l}",
            "gfptrackercounters",
            "lvsyncerrors",
            where=f"sysid={128+l}",
        )
        parameters.append(p)
        p = Parameter(
            f"@hvsyncerrors_l{l}",
            "gfptrackercounters",
            "hvsyncerrors",
            where=f"sysid={128+l}",
        )
        parameters.append(p)
        p = Parameter(
            f"@lvpacketsizeerrors_l{l}",
            "gfptrackercounters",
            "lvpacketsizeerrors",
            where=f"sysid={128+l}",
        )
        parameters.append(p)
        p = Parameter(
            f"@hvpacketsizeerrors_l{l}",
            "gfptrackercounters",
            "hvpacketsizeerrors",
            where=f"sysid={128+l}",
        )
        parameters.append(p)
        p = Parameter(
            f"@lvbackplaneactivity_l{l}",
            "gfptrackercounters",
            "lvbackplaneactivity",
            where=f"sysid={128+l}",
        )
        parameters.append(p)
        p = Parameter(
            f"@hvbackplaneactivity_l{l}",
            "gfptrackercounters",
            "hvbackplaneactivity",
            where=f"sysid={128+l}",
        )
        parameters.append(p)
        p = Parameter(
            f"@lvwordsvalid_l{l}",
            "gfptrackercounters",
            "lvwordsvalid",
            where=f"sysid={128+l}",
        )
        parameters.append(p)
        p = Parameter(
            f"@hvwordsvalid_l{l}",
            "gfptrackercounters",
            "hvwordsvalid",
            where=f"sysid={128+l}",
        )
        parameters.append(p)
        p = Parameter(
            f"@toftriggers_l{l}",
            "gfptrackercounters",
            "toftriggers",
            where=f"sysid={128+l}",
        )
        parameters.append(p)
        p = Parameter(
            f"@reboots_l{l}", "gfptrackercounters", "reboots", where=f"sysid={128+l}"
        )
        parameters.append(p)

    # setup ASIC temperature and leakage current parameters

    for row in range(6):
        for mod in range(6):
            p = Parameter(
                f"@asictemp_r{row}m{mod}",
                "gfptrackertempleak",
                f"templeak_r{row%3}m{mod}",
                where=f"rowoffset={(row//3)*3}",
                converter=asic_temp,
                units="deg C",
                comment=f"ASIC temperature for row {row} mod {mod}",
            )
            parameters.append(p)
            p = Parameter(
                f"@asicleakcold_r{row}m{mod}",
                "gfptrackertempleak",
                f"templeak_r{row%3}m{mod}",
                where=f"rowoffset={(row//3)*3}",
                converter=asic_leak_cold,
                units="nA",
                comment=f"ASIC leakage current (cold) for row {row} mod {mod}",
            )
            parameters.append(p)
            p = Parameter(
                f"@asicleakwarm_r{row}m{mod}",
                "gfptrackertempleak",
                f"templeak_r{row%3}m{mod}",
                where=f"rowoffset={(row//3)*3}",
                converter=asic_leak_warm,
                units="nA",
                comment=f"ASIC leakage current (warm) for row {row} mod {mod}",
            )
            parameters.append(p)

    for pdu_id in (0, 1, 2):
        for ch in range(8):
            p = Parameter(
                f"@vbus_pdu{pdu_id}ch{ch}",
                "pdu_hkp",
                f"vbus_avg{ch}",
                where=f"pdu_id = {pdu_id}",
                converter=pdu_voltage,
                units="V",
                low_range=23,
                high_range=25,
                low_alarm=0,
                high_alarm=100,  # NOTE - want to add a physically motivated value here
            )
            parameters.append(p)
            p = Parameter(
                f"@vbus_inst_pdu{pdu_id}ch{ch}",
                "pdu_hkp",
                f"vbus{ch}",
                where=f"pdu_id = {pdu_id}",
                converter=pdu_voltage,
                units="V",
            )
            parameters.append(p)
            p = Parameter(
                f"@ibus_pdu{pdu_id}ch{ch}",
                "pdu_hkp",
                f"vsense_avg{ch}",
                where=f"pdu_id = {pdu_id}",
                converter=pdu_current,
                units="A",
                low_range=0,
                high_range=30,
                low_alarm=-1,
                high_alarm=50,  # NOTE - add physically motivated value here
            )
            parameters.append(p)
            p = Parameter(
                f"@ibus_inst_pdu{pdu_id}ch{ch}",
                "pdu_hkp",
                f"vsense{ch}",
                where=f"pdu_id = {pdu_id}",
                converter=pdu_current,
                units="A",
            )
            parameters.append(p)
            p = Parameter(
                f"@power_pdu{pdu_id}ch{ch}",
                "pdu_hkp",
                f"vpower{ch}",
                where=f"pdu_id = {pdu_id}",
                converter=pdu_power,
                units="W",
            )
            parameters.append(p)
            p = Parameter(
                f"@power_acc_pdu{pdu_id}ch{ch}",
                "pdu_hkp",
                f"vpower_acc{ch}",
                where=f"pdu_id = {pdu_id}",
                converter=pdu_power_acc,
                units="J",
                low_range=0,
                high_range=100000,  # NOTE - add physically motivated values
                low_alarm=0,
                high_alarm=1000000,  #
            )
            parameters.append(p)
            p = Parameter(
                f"@temp_pdu{pdu_id}ch{ch}",
                "pdu_hkp",
                f"temp{ch}",
                where=f"pdu_id = {pdu_id}",
                converter=pdu_temp,
                units="deg C",
                low_range=-50,
                high_range=40,
                low_alarm=-60,
                high_alarm=50,  # NOTE all of these need physically motivated values
            )
            parameters.append(p)
        for hkp_par in [
            "gcutime",
            "rowid",
            "counter",
            "pdu_count",
            "acc_count_pac0",
            "acc_count_pac1",
        ]:
            p = Parameter(
                f"@{hkp_par}_pdu{pdu_id}",
                "pdu_hkp",
                f"{hkp_par}",
                where=f"pdu_id = {pdu_id}",
                low_range=0,
                high_range=float("inf"),
                units="",
            )
            parameters.append(p)
        p = Parameter(
            f"@length_pdu{pdu_id}",
            "pdu_hkp",
            "length",
            where=f"pdu_id = {pdu_id}",
            low_range=218,
            high_range=218,
            units="",
        )
        parameters.append(p)
        p = Parameter(
            f"@error_pdu{pdu_id}",
            "pdu_hkp",
            "error",
            where=f"pdu_id = {pdu_id}",
            low_range=0,
            high_range=0,
            low_alarm=0,
            high_alarm=0,
            units="",
        )
        parameters.append(p)
        p = Parameter(
            f"@gsemode_pdu{pdu_id}",
            "pdu_hkp",
            "gsemode",
            where=f"pdu_id = {pdu_id}",
            low_range=1,
            high_range=1,
            units="",
        )
        parameters.append(p)
        p = Parameter(
            f"@vbat_pdu{pdu_id}",
            "pdu_hkp",
            "vbat",
            where=f"pdu_id = {pdu_id}",
            converter=pdu_voltage,
            units="V",
            low_range=29,
            high_range=31,
            low_alarm=25,
            high_alarm=35,  # NOTE make physically motivated value here
        )
        parameters.append(p)


    # HVPS / lvps crate parameters
    for crate_id in [0,1]:
        for card_id in [1,2,3,4,5,6,7,8,9,10]:

            # hkp paramters: no conversions, no warnings
            for crate_hkp_par in ["rhv_voltage", "rhv_current","main_status","board_status","conn_status_a","conn_status_b","conn_status_c","version","flags","rowid","gsemode","gcutime","length","counter","crate","card"]:
                p = Parameter(
                    f"@crate{crate_id}_card{card_id}_{crate_hkp_par}",
                    "tracker_power",
                    crate_hkp_par,
                    where=f"((crate = {crate_id}) and  (card = {card_id}))",
                    )
                parameters.append(p)

            for conn in ["a","b","c"]:
                # lv parameters (one per row, three each per card)
                #for lv_params in ["asic_ana","asic_dig","asic_cal","if"]:
                for params, numf in zip(["d3","d2","a3","a2"],[8,8,3,8]):
                    p = Parameter(
                        f"@crate{crate_id}_card{card_id}_lv_{params}v{numf}_{conn}",
                        "tracker_power",
                        f"lv_{params}v{numf}_{conn}",# NOTE update per alex
                        where=f"((crate = {crate_id}) and  (card = {card_id}))",
                        units="mV",
                    )
                    parameters.append(p)

                    p = Parameter(
                        f"@crate{crate_id}_card{card_id}_lv_{params}i{numf}_{conn}",
                        "tracker_power",
                        f"lv_{params}i{numf}_{conn}", # NOTE update per ALEX
                        where=f"((crate = {crate_id}) and  (card = {card_id}))",
                        units="nA",
                    )
                    parameters.append(p)

            # hv params
            for module in range(1,19):
                for unit, thing in zip(["mV","nA"],["hv_voltage","hv_current"]):
                    p = Parameter(
                        f"@crate{crate_id}_card{card_id}_{thing}{module}",
                        "tracker_power",
                        f"{thing}_{module}",
                        where=f"((crate = {crate_id}) and  (card = {card_id}))",
                        units=unit, # check 
                        )
                    parameters.append(p)

            # temperatures
            for temp_id in ['hv_tmp1', 'hv_tmp2', 'mcu_tmp', 'conn_tmp_a', 'mcu_tmp_a', 'conn_tmp_b', 'mcu_tmp_b', 'conn_tmp_c', 'mcu_tmp_c']:
                p = Parameter(
                    f"@crate{crate_id}_card{card_id}_{temp_id}",
                    "tracker_power",
                    temp_id, # NOTE check with Alex
                    where=f"((crate = {crate_id}) and  (card = {card_id}))",
                    units="C", # check this 
                    )
                parameters.append(p)

    # flight cooling system housekeeping parameters and data 

    # rtd temps
    for rtd_id in range(64):
        p = Parameter(
            f"@cooling_rtd_{rtd_id}",
            "cooling",
            f"rtd_{rtd_id}",
            units="C",
            )
        parameters.append(p)

    # unit-less housekeeping vars
    for hkp in ['rowid', 'gsemode', 'gcutime', 'counter', 'length', 'frame_counter', 'status_1', 
                'status_2', 'rx_byte_num', 'rx_cmd_num', 'last_cmd', 'blob']:
        p = Parameter(
            f"@cooling_{hkp}",
            "cooling",
            hkp,
            converter=cooling_rtd,
            )
        parameters.append(p)

    # voltage
    p = Parameter(
        "@cooling_fpga_board_v_in",
        "cooling",
        "fpga_board_v_in",
        converter=cooling_fpga_v,
        units = "V",
        )
    parameters.append(p)

    # current
    p = Parameter(
        "@cooling_fpga_board_i_in",
        "cooling",
        "fpga_board_i_in",
        converter=cooling_fpga_i,
        units = "A"
        )
    parameters.append(p)

    # pressure
    p = Parameter(
        "@cooling_fpga_board_p",
        "cooling",
        "fpga_board_p",
        converter=cooling_fpga_p,
        units = "kPa",
        )
    parameters.append(p)

    # currents 
    for hkp in ['sh_current', 'rh_current']:
        p = Parameter(
            f"@cooling_{hkp}",
            "cooling",
            hkp,
            converter=cooling_current,
            units="A", # ??? not specified
            )
        parameters.append(p)

    # temperatures with conversion (5*Y/4096)*100 – 273.2 [deg-C] # NOTE needs conversion
    for hkp in ['pw_board1_t', 'pw_board2_t','fpga_board_t']:
        p = Parameter(
            f"@cooling_{hkp}",
            "cooling",
            hkp,
            converter=cooling_board_temp,
            units="C",
            )
        parameters.append(p)

    # temperatures with conversion like rtds NOTE needs conversion
    for hkp in ['rsv_t', 'rh_on', 'rh_off']:
        p = Parameter(
            f"@cooling_{hkp}",
            "cooling",
            hkp,
            converter=cooling_rtd,
            units="C",
            )
        parameters.append(p)

    # time in seconds seconds 
    for hkp in ['sh1_time_left', 'sh2_time_left', 'sh3_time_left']:
        p = Parameter(
            f"@cooling_{hkp}",
            "cooling",
            hkp,
            units="s",
            )
        parameters.append(p)


    return ParameterBank(par = parameters)
