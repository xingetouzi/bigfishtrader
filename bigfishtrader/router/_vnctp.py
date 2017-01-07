from ctpgateway.eventEngine import EventEngine
from ctpgateway.myGateway import MyCtpGateway, TradeAccount
from eventType import EVENT_LOG, EVENT_POSITION, EVENT_ACCOUNT, EVENT_ERROR


def print_log(event):
    log = event.dict_['data']
    print(':'.join([log.logTime, log.logContent]))


def print_error(event):
    error = event.dict_['data']
    print("%s: %s" % (error.errorTime,
                      " ".join([str(error.errorID),
                                error.errorMsg,
                                str(error.requestID),
                                error.additionalInfo])))


def print_data(event):
    position = event.dict_["data"].to_dict()
    print(position)


class VnCtpRouter(object):
    def __init__(self, event_queue):
        self._event_queue = event_queue()
        self._event_engine = EventEngine()
        account = TradeAccount("068709", "520lmj", "SIMNOW")
        eventEngine = EventEngine()
        eventEngine.register(EVENT_LOG, print_log)
        eventEngine.register(EVENT_ERROR, print_error)
        eventEngine.register(EVENT_POSITION, print_data)
        eventEngine.register(EVENT_ACCOUNT, print_data)
        # eventEngine.register(EVENT_TIMER, print_time)
        eventEngine.start()
        gateway = MyCtpGateway(eventEngine)
        gateway.set_account(account)
        gateway.qryEnabled = False
        gateway.connect()
