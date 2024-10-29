import requests, sys, random, datetime
import numpy as np

base_url = "https://cpee.org/flow/start/url/"
init_data = {
    "behavior": "fork_running",
    "url": "https://cpee.org/hub/server/Teaching.dir/Prak.dir/Challengers.dir/Julian_Simon.dir/Main.xml",
}

if len(sys.argv) < 2:
    print("Bitte geben Sie die Simulationsdauer in Minuten an.")
    sys.exit(1)
simulation_end_time = int(sys.argv[1])


def minutes_to_datetime(minutes):
    return datetime.datetime(2018, 1, 1) + datetime.timedelta(minutes=minutes)


def is_working_hours(arrival_time):
    dt = minutes_to_datetime(arrival_time)
    return dt.weekday() < 5 and 8 <= dt.hour < 17  # Monday=0, Sunday=6


patient_types_A = ["A1", "A2", "A3", "A4"]
patient_probabilities_A = [0.5, 0.25, 0.125, 0.125]

patient_types_B = ["B1", "B2", "B3", "B4"]
patient_probabilities_B = [0.5, 0.25, 0.125, 0.125]


def get_random_patient_type(category):
    if category == "A":
        return random.choices(patient_types_A, weights=patient_probabilities_A, k=1)[0]
    elif category == "B":
        return random.choices(patient_types_B, weights=patient_probabilities_B, k=1)[0]
    elif category == "EM":
        return "EM"
    else:
        raise ValueError("Invalid patient category")


def get_patients(patient_category):
    arrival_time = 0
    patients = []

    while True:
        patient_type = get_random_patient_type(patient_category)

        if patient_category == "A" or patient_category == "B":
            arrival_time += int(round(random.uniform(0, 60)))
            while not is_working_hours(arrival_time):
                arrival_time += 10
        elif patient_category == "EM":
            arrival_time += int(round(np.random.exponential(scale=60)))
        else:
            raise ValueError("Invalid patient category")

        if arrival_time > simulation_end_time:
            break

        patients.append((patient_type, arrival_time))
    return patients


arriving_patients = get_patients("A") + get_patients("B") + get_patients("EM")
arriving_patients.sort(key=lambda x: x[1])

print("Sending requests...")
for patient in arriving_patients:
    data = {
        **init_data,
        "init": f'{{"patient_type":"{patient[0]}","time_now":"{patient[1]}"}}',
    }
    try:
        response = requests.post(base_url, data=data)
        response_json = response.json()
        print(
            f"Request for CPEE: {response_json.get('CPEE-INSTANCE')} - Status Code: {response.status_code} - Time: {patient[1]} - Type: {patient[0]}"
        )
    except Exception as e:
        print(f"Error in request for patient {patient}: {e}")
print("All requests sent.")
