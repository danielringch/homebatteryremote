import asyncio, croniter, datetime, traceback, logging

class Triggers:
    class __bundle:
        def __init__(self, name, func, interval):
            self.cron = interval
            self.name = name
            self.func = func
            self.iter = croniter.croniter(interval, datetime.datetime.now())
            self.next = self.iter.get_next(datetime.datetime)

    def __init__(self):
        self.__jobs = []

    def add(self, name, interval, callback):
        self.__jobs.append(self.__bundle(name, callback, interval))

    def start(self):
        asyncio.create_task(self.__run())

    async def __run(self):
        while True:
            sleep_time = await self.__tick()
            await asyncio.sleep(sleep_time)
    
    async def __tick(self):
        time = datetime.datetime.now()
        for job in self.__jobs:
            diff = (job.next - time).total_seconds()
            if diff < 0:
                await self.__try_run(job)
                job.next = job.iter.get_next(datetime.datetime)

        next_run = 5
        for job in self.__jobs:
            diff = max(0, (job.next - time).total_seconds())
            if diff < next_run:
                next_run = diff
        return round(next_run) + 1

    async def __try_run(self, job):
        try:
            job.func()
        except Exception as e:
            trace = traceback.format_exc()
            message = f'Trigger {job.name} failed:\n{repr(e)}\n{trace}'
            logging.error(message)

    @staticmethod
    def get_current_quarter_hour():
        return Triggers.truncate_timestamp(datetime.datetime.now())

    @staticmethod
    def truncate_timestamp(timestamp: datetime.datetime):
        last_quarter = (timestamp.minute // 15) * 15
        return timestamp.replace(minute=last_quarter, second=0, microsecond=0)

triggers = Triggers()
