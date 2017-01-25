import pandas as pd
import numpy as np
import pytz
from dateutil.parser import parse
import codecs

if __name__ == "__main__":
    filename = "oanda_linux.log"
    tz = pytz.timezone("Asia/Shanghai")
    tick_start_local = []
    tick_end_local = []
    tick_timestamp = []
    order_generated = []
    order_sent = []
    order_placed = []
    place_timestamp = []
    order_filled = []
    fill_timestamp = []
    last_tick_start_local = None
    last_tick_end_local = None
    last_tick_exchange = None
    with codecs.open(filename, "r", encoding="utf-8") as f:
        for line in f.readlines():
            line = line.replace("\n", "")
            sects = [sect for sect in line.split(" ") if sect]
            dts, _ = sects[0:2]
            content = " ".join(sects[2:])
            if "Get ticker" in content:
                exchange_ts = parse(line.split("=")[-1]).replace(tzinfo=tz)
                local_ts = parse(dts).replace(tzinfo=tz)
                last_tick_start_local = local_ts
                last_tick_exchange = exchange_ts
            elif "Finish handle ticker" in content:
                local_ts = parse(dts).replace(tzinfo=tz)
                last_tick_end_local = local_ts
            elif "generated" in content:
                tick_end_local.append(last_tick_end_local)
                tick_start_local.append(last_tick_start_local)
                tick_timestamp.append(last_tick_exchange)
                local_ts = parse(dts).replace(tzinfo=tz)
                order_generated.append(local_ts)
            elif "sent" in content:
                local_ts = parse(dts).replace(tzinfo=tz)
                order_sent.append(local_ts)
            elif "placed" in content:
                exchange_ts = parse(line.split("at ")[-1]).replace(tzinfo=tz)
                local_ts = parse(dts).replace(tzinfo=tz)
                order_placed.append(local_ts)
                place_timestamp.append(exchange_ts)
            elif "filled" in content:
                exchange_ts = parse(line.split("at ")[-1]).replace(tzinfo=tz)
                local_ts = parse(dts).replace(tzinfo=tz)
                order_filled.append(local_ts)
                fill_timestamp.append(exchange_ts)

    dct = {
        "tick_start": tick_start_local,
        "tick_end": tick_end_local,
        "tick_timestamp": tick_timestamp,
        "order_generated": order_generated,
        "order_sent": order_sent,
        "order_placed": order_placed,
        "order_filled": order_filled,
        "placing_timestamp": place_timestamp,
        "filling_timestamp": fill_timestamp,
    }
    print([(key, len(l)) for key, l in dct.items()])
    result = pd.DataFrame(dct, columns=["tick_start", "tick_end", "tick_timestamp",
                                        "order_generated", "order_sent", "order_placed",
                                        "order_filled", "placing_timestamp", "filling_timestamp"])
    print(result)
    result.to_csv("result.csv")
    delta = pd.DataFrame()
    delta["d1"] = result["tick_end"] - result["tick_start"]
    delta["d2"] = result["order_generated"] - result["tick_end"]
    delta["d3"] = result["order_sent"] - result["order_generated"]
    delta["d4"] = result["order_filled"] - result["order_sent"]
    # delta["tick_to_placing"] = result["placing_timestamp"] - result["tick_timestamp"]
    # delta["tick_to_filling"] = result["filling_timestamp"] - result["tick_timestamp"]
    delta = pd.DataFrame(delta.values.astype(float), columns=["d1", "d2", "d3", "d4"])
    temp = delta.copy()
    delta.index = delta.index.astype(str)
    delta = delta.append(pd.Series(temp.apply(np.mean, axis=0), name="mean"))
    delta = delta.append(pd.Series(temp.apply(np.max, axis=0), name="max"))
    delta = delta.append(pd.Series(temp.apply(np.std, axis=0), name="std"))
    delta.to_csv("delta.csv")
