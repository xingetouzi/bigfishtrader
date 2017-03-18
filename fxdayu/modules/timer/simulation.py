from fxdayu.context import ContextMixin
from fxdayu.event import EVENTS, TimeEvent, ScheduleEvent, ExitEvent
from fxdayu.utils.api_support import api_method


class TimeSimulation(ContextMixin):
    def __init__(self, context, environment, data, engine):
        super(TimeSimulation, self).__init__(context, environment, data)
        self.engine = engine
        self._ahead = []
        self._behind = []

    def link_context(self):
        self.environment['time_schedule'] = self.time_schedule

    @api_method
    def time_schedule(self, func, time_rule, ahead=True):
        if ahead:
            self._ahead.append((func, time_rule))
        else:
            self._behind.append((func, time_rule))

    def put_ahead(self):
        head = 'ahead'
        count = 0
        for func, time_rule in self._ahead:
            topic = head + str(count)
            self.put_ruled(func, time_rule, topic)
            count += 1

    def put_ruled(self, func, time_rule, topic):
        for time_ in self.data.all_time:
            if time_rule(time_):
                self.engine.put(ScheduleEvent(time_, topic))

        def schedule(event, kwargs=None):
            func(self.context, self.data)

        self.engine.register(schedule, EVENTS.SCHEDULE, topic)

    def put_behind(self):
        head = 'behind'
        count = 0
        for func, time_rule in self._behind:
            topic = head + str(count)
            self.put_ruled(func, time_rule, topic)
            count += 1

    def put_main(self):
        for time_ in self.data.all_time:
            self.engine.put(TimeEvent(time_, "bar.open"))
            self.engine.put(TimeEvent(time_, "bar.close"))
        self.engine.put(ExitEvent())

    def put_time(self):
        self.put_ahead()
        self.put_main()
        self.put_behind()
