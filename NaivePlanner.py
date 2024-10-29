from datetime import datetime, timedelta


class NaivePlanner:
    def __init__(self, simulation_start):
        self.simulation_start = simulation_start

    def plan(self, arrival_time):
        arrival_datetime = self.simulation_start + timedelta(minutes=arrival_time)
        replanned_datetime = arrival_datetime + timedelta(hours=24)  # next day

        # make sure its a working day and working hours
        while replanned_datetime.weekday() >= 5 or not (
            8 <= replanned_datetime.hour < 17
        ):
            # move to the start of the next day at 8:00
            replanned_datetime += timedelta(days=1)
            replanned_datetime = replanned_datetime.replace(hour=8, minute=0)

        # calculate minutes from simulation start to the adjusted replanned time
        replanned_time = int(
            (replanned_datetime - self.simulation_start).total_seconds() // 60
        )
        return replanned_time
