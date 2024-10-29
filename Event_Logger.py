import csv, os, threading
from datetime import datetime, timedelta


class Logger:
    def __init__(self, log_file):
        self.log_file = log_file
        self.lock = threading.Lock()
        self.start_time = datetime(2018, 1, 1)  # Baseline for simulation

        # clear old log file
        if os.path.exists(self.log_file):
            os.remove(self.log_file)

        with open(self.log_file, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    "ID",
                    "Event_Type",
                    "Arrival_Time",
                    "Start_Time",
                    "End_Time",
                    "Metadata",
                ]
            )

    def log_event(
        self, id, event_type, arrival_time, start_time, end_time, metadata=None
    ):
        with self.lock:
            with open(self.log_file, mode="a", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(
                    [
                        id,
                        event_type,
                        self.start_time + timedelta(minutes=arrival_time),
                        self.start_time + timedelta(minutes=start_time),
                        self.start_time + timedelta(minutes=end_time),
                        metadata,
                    ]
                )


def sort_log_by_arrival_time(log_file):
    with open(log_file, mode="r", newline="") as file:
        reader = csv.DictReader(file)
        log_data = list(reader)

    sorted_log_data = sorted(
        log_data,
        key=lambda row: datetime.strptime(row["Arrival_Time"], "%Y-%m-%d %H:%M:%S"),
    )

    with open(log_file, mode="w", newline="") as file:
        fieldnames = [
            "ID",
            "Event_Type",
            "Arrival_Time",
            "Start_Time",
            "End_Time",
            "Metadata",
        ]
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(sorted_log_data)

    print(f"Log-Datei {log_file} wurde erfolgreich nach Arrival_Time sortiert.")


# sort_log_by_arrival_time("log.csv")
