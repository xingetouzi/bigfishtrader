import pandas as pd
import numpy as np
import pytz
from dateutil.parser import parse
import codecs

COUNT_PLACED = False

if __name__ == "__main__":
    filename = "ib_windows.log"
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
    tick_start_local_stash = []
    tick_end_local_stash = []
    tick_timestamp_stash = []
    order_generated_stash = []
    order_sent_stash = []
    order_placed_stash = []
    place_timestamp_stash = []
    order_filled_stash = []
    fill_timestamp_stash = []

    count = 0
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
                tick_end_local_stash.append(last_tick_end_local)
                tick_start_local_stash.append(last_tick_start_local)
                tick_timestamp_stash.append(last_tick_exchange)
                local_ts = parse(dts).replace(tzinfo=tz)
                order_generated_stash.append(local_ts)
            elif "sent" in content:
                local_ts = parse(dts).replace(tzinfo=tz)
                order_sent_stash.append(local_ts)
            elif "placed" in content:
                count += 1
                if count == 2:
                    exchange_ts = parse(line.split("at ")[-1]).replace(tzinfo=tz)
                    local_ts = parse(dts).replace(tzinfo=tz)
                    order_placed_stash.append(local_ts)
                    place_timestamp_stash.append(exchange_ts)
                    count = 0
            elif "filled" in content:
                exchange_ts = parse(line.split("at ")[-1]).replace(tzinfo=tz)
                local_ts = parse(dts).replace(tzinfo=tz)
                order_filled_stash.append(local_ts)
                fill_timestamp_stash.append(exchange_ts)
                # place_timestamp.append(place_timestamp_stash.pop(0))
                tick_end_local.append(tick_end_local_stash.pop(0))
                tick_start_local.append(tick_start_local_stash.pop(0))
                tick_timestamp.append(tick_timestamp_stash.pop(0))
                order_generated.append(order_generated_stash.pop(0))
                order_sent.append(order_sent_stash.pop(0))
                order_filled.append(order_filled_stash.pop(0))
                fill_timestamp.append(fill_timestamp_stash.pop(0))


    dct = {
        "tick_start": tick_start_local,
        "tick_end": tick_end_local,
        "tick_timestamp": tick_timestamp,
        "order_generated": order_generated,
        "order_sent": order_sent,
        "order_filled": order_filled,
        "filling_timestamp": fill_timestamp,
    }
    if COUNT_PLACED:
        dct["placing_timestamp"] = place_timestamp
        dct["order_placed"] = order_filled
    print([(key, len(l)) for key, l in dct.items()])
    if COUNT_PLACED:
        result = pd.DataFrame(dct, columns=["tick_start", "tick_end", "tick_timestamp",
                                            "order_generated", "order_sent", "order_placed",
                                            "order_filled", "placing_timestamp", "filling_timestamp"])
    else:
        result = pd.DataFrame(dct, columns=["tick_start", "tick_end", "tick_timestamp",
                                            "order_generated", "order_sent", "order_filled",
                                            "placing_timestamp", "filling_timestamp"])
    print(result)
    result.to_csv("result.csv")
    delta = pd.DataFrame()
    delta["d0"] = result["tick_start"] - result["tick_timestamp"]
    delta["d1"] = result["tick_end"] - result["tick_start"]
    delta["d2"] = result["order_generated"] - result["tick_end"]
    delta["d3"] = result["order_sent"] - result["order_generated"]
    if COUNT_PLACED:
        delta["d4"] = result["order_placed"] - result["order_sent"]
    delta["d5"] = result["order_filled"] - result["order_sent"]
    # delta["tick_to_placing"] = result["placing_timestamp"] - result["tick_timestamp"]
    # delta["tick_to_filling"] = result["filling_timestamp"] - result["tick_timestamp"]
    if COUNT_PLACED:
        columns = ["d0", "d1", "d2", "d3", "d4", "d5"]
    else:
        columns = ["d0", "d1", "d2", "d3", "d5"]
    delta = pd.DataFrame(delta[columns].values.astype(float), columns=columns)
    temp = delta.copy()
    delta.index = delta.index.astype(str)
    delta = delta.append(pd.Series(temp.apply(np.mean, axis=0), name="mean"))
    delta = delta.append(pd.Series(temp.apply(np.max, axis=0), name="max"))
    delta = delta.append(pd.Series(temp.apply(np.std, axis=0), name="std"))
    delta.to_csv("delta.csv")
