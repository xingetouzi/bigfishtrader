import pandas as pd
import pytz
from dateutil.parser import parse
import codecs

if __name__ == "__main__":
    filename = "oanda_windows.log"
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
                print(last_tick_end_local)
            elif "generated" in content:
                tick_end_local.append(last_tick_end_local)
                tick_start_local.append(last_tick_start_local)
                local_ts = parse(dts).replace(tzinfo=tz)
                order_generated.append(local_ts)
                print(local_ts)
            elif "sent" in content:
                local_ts = parse(dts).replace(tzinfo=tz)
                order_sent.append(local_ts)
            elif "placed":
                exchange_ts = parse(line.split("at ")[-1]).replace(tzinfo=tz)
                local_ts = parse(dts).replace(tzinfo=tz)
                order_placed.append(local_ts)
                place_timestamp.append(exchange_ts)
            elif "filled":
                exchange_ts = parse(line.split("at ")[-1]).replace(tzinfo=tz)
                local_ts = parse(dts).replace(tzinfo=tz)
                order_filled.append(local_ts)
                fill_timestamp.append(exchange_ts)
    result = pd.DataFrame({
        "tick_start": tick_start_local,
        "tick_end": tick_end_local,
        "tick_timestamp": tick_timestamp,
        "order_generated": order_generated,
        "order_sent": order_sent,
        "order_placed": order_placed,
        "order_filled": order_filled,
        "placing_timestamp": place_timestamp,
        "filling_timestamp": fill_timestamp,
    }, columns=["tick_start", "tick_end", "tick_timestamp",
                "order_generated", "order_sent", "order_placed",
                "order_filled", "placing_timestamp", "filling_timestamp"])
    print(result)
