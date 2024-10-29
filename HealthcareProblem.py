# Specific problem configs (for the Healthcare Problem)

from datetime import datetime, timedelta

events = {
    "Admission": {
        "capacity": [
            {
                "capacity": float("inf"),
                "days": [0, 1, 2, 3, 4, 5, 6],
                "start_hour": 0,
                "end_hour": 24,
            }
        ],
        "dependencies": [],
        "bookings": [],
        "active_bookings": [],
    },
    "Intake": {
        "capacity": [
            {
                "capacity": 4,
                "days": [0, 1, 2, 3, 4],
                "start_hour": 8,
                "end_hour": 17,
            },
            {
                "capacity": 0,
                "days": [0, 1, 2, 3, 4, 5, 6],
                "start_hour": 0,
                "end_hour": 24,
            },
        ],
        "dependencies": ["Admission"],
        "bookings": [],
        "active_bookings": [],
    },
    "ER_Treatment": {
        "capacity": [
            {
                "capacity": 9,
                "days": [0, 1, 2, 3, 4, 5, 6],
                "start_hour": 0,
                "end_hour": 24,
            }
        ],
        "dependencies": ["Admission"],
        "bookings": [],
        "active_bookings": [],
    },
    "Surgery": {
        "capacity": [
            {
                "capacity": 5,
                "days": [0, 1, 2, 3, 4],
                "start_hour": 8,
                "end_hour": 17,
            },
            {
                "capacity": 1,
                "days": [0, 1, 2, 3, 4, 5, 6],
                "start_hour": 0,
                "end_hour": 24,
            },
        ],
        "dependencies": ["Admission", "Intake", "ER_Treatment"],
        "bookings": [],
        "active_bookings": [],
    },
    "Nursing_A": {
        "capacity": [
            {
                "capacity": 30,
                "days": [0, 1, 2, 3, 4, 5, 6],
                "start_hour": 0,
                "end_hour": 24,
            }
        ],
        "dependencies": ["Admission", "Intake", "ER_Treatment", "Surgery"],
        "bookings": [],
        "active_bookings": [],
    },
    "Nursing_B": {
        "capacity": [
            {
                "capacity": 40,
                "days": [0, 1, 2, 3, 4, 5, 6],
                "start_hour": 0,
                "end_hour": 24,
            }
        ],
        "dependencies": ["Admission", "Intake", "ER_Treatment", "Surgery"],
        "bookings": [],
        "active_bookings": [],
    },
    "Releasing": {
        "capacity": [
            {
                "capacity": float("inf"),
                "days": [0, 1, 2, 3, 4, 5, 6],
                "start_hour": 0,
                "end_hour": 24,
            }
        ],
        "dependencies": [],
        "bookings": [],
        "active_bookings": [],
    },
}
