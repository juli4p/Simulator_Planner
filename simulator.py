from bottle import Bottle, request, response, run
from datetime import datetime, timedelta
from Event_Logger import Logger
from NaivePlanner import NaivePlanner

# from GeneticPlanner import GeneticPlanner
import sys, threading, time, json, requests
import HealthcareProblem

# server configs
app = Bottle()

# general configs
events = {}
waiting_requests = []
lock = threading.Lock()
next_id = 1
known_ids = set()
last_StartEvent = 0
logger = Logger("log.csv")
SIMULATION_END = None
SIMULATION_START = datetime(2018, 1, 1)

# case specific configs
events = HealthcareProblem.events
start_event = "Admission"  # chronological order only secured for this event
replanned_requests = []


@app.post("/incoming_event")
def book_event():
    with lock:
        global next_id
        # id is a positive int (everything else gets treated as new and is assigned an id)
        id = request.forms.get("ID")
        try:
            id = int(id) if id is not None and int(id) > 0 else None
        except (ValueError, TypeError):
            id = None
        if id is None:
            id = next_id
            next_id += 1

        event_type = request.forms.get("Event_Type")
        arrival_time = int(float(request.forms.get("Arrival_Time")))
        duration = int(float(request.forms.get("Duration")))
        metadata = request.forms.get("Metadata")  # for problem specific data
        cpee_callback = request.headers.get("Cpee-Callback")

        if arrival_time > SIMULATION_END:
            response.status = 400  # Bad Request
            return {
                "error": f"Arrival time {arrival_time} exceeds simulation end time of {SIMULATION_END}"
            }

        req = {
            "id": id,
            "event_type": event_type,
            "arrival_time": arrival_time,
            "duration": duration,
            "metadata": metadata,
            "cpee_callback": cpee_callback,
        }

        (can_process, start_time) = can_process_request(req)
        if can_process:
            return process_request(req, False, start_time)
        else:
            if event_type != start_event:
                waiting_requests.append(req)
            response.headers["Cpee-Callback"] = "true"
            return


@app.post("/plan_patient")
def replan_patient():
    planner = NaivePlanner(SIMULATION_START)
    # g_planner = GeneticPlanner()
    id = request.forms.get("ID")
    arrival_time = int(float(request.forms.get("Arrival_Time")))
    metadata = request.forms.get("Metadata")  # Für spezifische Problem-Daten
    replanned_time = planner.plan(arrival_time)
    # current_state = get_simulation_state(replanned_time)
    # replanned_time = g_planner.plan(id, arrival_time, metadata, {"diagnosis": metadata}, current_state)

    base_url = "https://cpee.org/flow/start/url/"
    data = {
        "behavior": "fork_running",
        "url": "https://cpee.org/hub/server/Teaching.dir/Prak.dir/Challengers.dir/Julian_Simon.dir/Main.xml",
        "init": f'{{"patient_id":"{id}","patient_type":"{metadata}","time_now":"{replanned_time}"}}',
    }
    try:
        response = requests.post(base_url, data=data)
        response_json = response.json()
        print(
            f"Patient {id} replanned to timeslot: {replanned_time} at CPEE: {response_json.get('CPEE-INSTANCE')} - Status Code: {response.status_code}"
        )
    except Exception as e:
        print(f"Error in replanning for patient {id}: {e}")
    return {"replanned_time": replanned_time}


def get_capacity(event, start_time):
    current_datetime = SIMULATION_START + timedelta(minutes=start_time)
    weekday = current_datetime.weekday()
    hour = current_datetime.hour
    for rule in event["capacity"]:
        if weekday in rule["days"] and rule["start_hour"] <= hour < rule["end_hour"]:
            return rule["capacity"]
    return 0


# Check whether any event can still influence the current event -> if not, the current event can be processed
# if event can be processed, return (True, Start_Time)
def can_process_request(req):
    global last_StartEvent
    global known_ids
    global start_event
    req_id = req["id"]
    event_type = req["event_type"]
    arrival_time = req["arrival_time"]
    dependencies = events[event_type]["dependencies"]

    # ---------cause of planner---------#
    if event_type == start_event and req_id in known_ids:
        replanned_requests.append(req)
        return (False, None)
    if event_type == start_event and req_id not in known_ids:
        replanned_requests.sort(key=lambda x: x["arrival_time"])
        for replanned_req in replanned_requests:
            if replanned_req["arrival_time"] < arrival_time:
                process_request(replanned_req, True, replanned_req["arrival_time"])
                replanned_requests.remove(replanned_req)
    # ---------cause of planner---------#

    for waiting_req in waiting_requests:
        if (
            waiting_req["event_type"] == event_type
            and waiting_req["arrival_time"] < arrival_time
            and waiting_req["id"] != req_id
        ):
            return (False, None)

    # no dependencies (in our case Admission, Releasing)
    if not dependencies and req_id not in known_ids:
        return (True, arrival_time)

    # check whether totally new requests might still arrive (that could be prioticized higher)
    if last_StartEvent < arrival_time:
        return (False, None)

    # Check whether any dependency ends earlier and might still need to be proptized
    for dep_event in dependencies:
        dep_bookings = events[dep_event]["active_bookings"]
        for dep_booking in dep_bookings:
            if dep_booking["id"] == req_id:
                continue
            if dep_booking["end_time"] < arrival_time:
                return (False, None)

    # Calculate start time, check whether start time is still in the allowed time frame -> no events could still arrive before start time
    event = events[event_type]
    bookings = event["bookings"]
    start_time = arrival_time
    while True:
        capacity = get_capacity(event, start_time)
        if capacity == 0:
            start_time += 1
            continue
        overlapping_bookings = [
            b
            for b in bookings
            if not (
                b["end_time"] < start_time
                or b["start_time"] > start_time + req["duration"]
            )
        ]
        if len(overlapping_bookings) < capacity:
            break
        start_time = min(b["end_time"] for b in overlapping_bookings) + 1
    if last_StartEvent < start_time:
        return (False, None)

    ###-----------------------------------------Case specific (Priorizize EM Patients)-----------------------------------------###
    for waiting_req in waiting_requests:
        if (
            "EM" in (waiting_req["metadata"] or "")
            and waiting_req["event_type"] == event_type
            and waiting_req["arrival_time"] < start_time
            and req_id != waiting_req["id"]
        ):
            process_request(waiting_req, True, start_time)
            waiting_requests.remove(waiting_req)
            return (False, None)
    ###-----------------------------------------Case specific (Priorizize EM Patients)-----------------------------------------###

    # event may be processed for start_time
    return (True, start_time)


def process_request(req, async_response, start_time):
    global last_StartEvent
    global start_event

    event_type = req["event_type"]
    arrival_time = req["arrival_time"]
    duration = req["duration"]
    id = req["id"]
    metadata = req["metadata"]
    cpee_callback = req["cpee_callback"]

    event = events[event_type]
    bookings = event["bookings"]
    active_bookings = event["active_bookings"]

    end_time = start_time + duration

    booking = {
        "id": id,
        "event_type": event_type,
        "start_time": start_time,
        "end_time": end_time,
        "arrival_time": arrival_time,
        "duration": duration,
        "metadata": metadata,
    }

    bookings.append(booking)
    active_bookings.append(booking)

    # delete old booking for id (only from active bookings)
    for event_name, event_data in events.items():
        if event_name != event_type:
            other_bookings = event_data["active_bookings"]
            event_data["active_bookings"] = [b for b in other_bookings if b["id"] != id]

    logger.log_event(id, event_type, arrival_time, start_time, end_time, metadata)
    response_data = {
        "id": id,
        "arrival_time": arrival_time,
        "start_time": start_time,
        "end_time": end_time,
    }

    if event_type == start_event:
        if (
            id not in known_ids
        ):  # replanned requests arent necessarily in the right order
            last_StartEvent = arrival_time
            known_ids.add(id)
        if not "EM" in (metadata or ""):
            response_data = handle_HCProblem_logic(
                req
            )  # case specific: send home or not

    if async_response:
        headers = {"Content-Type": "application/json"}
        requests.put(cpee_callback, data=json.dumps(response_data), headers=headers)
    else:
        return response_data


def process_waiting_requests():
    global waiting_requests
    while True:
        with lock:
            waiting_requests = sorted(waiting_requests, key=lambda x: x["arrival_time"])
            index = 0
            while index < len(waiting_requests):
                req = waiting_requests[index]
                (can_process, start_time) = can_process_request(req)
                if can_process:
                    process_request(req, True, start_time)
                    waiting_requests.remove(req)
                else:
                    index += 1
        time.sleep(0.5)


def handle_HCProblem_logic(req):

    def check_traffic(event_type, arrival_time):
        global waiting_requests
        capacity = get_capacity(events[event_type], arrival_time)
        active_bs = [
            b
            for b in events[event_type]["bookings"]
            if b["start_time"] <= arrival_time < b["end_time"]
        ]
        waiting_rs = [
            r
            for r in waiting_requests
            if r["event_type"] == event_type and r["arrival_time"] <= arrival_time
        ]
        total_requests = len(active_bs) + len(waiting_rs)
        return total_requests, capacity

    arrival_time = req["arrival_time"]
    id = req["id"]

    total_intake_requests, intake_capacity = check_traffic("Intake", arrival_time)
    if total_intake_requests >= intake_capacity:
        print(f"Sending patient {id} home due to intake capacity")
        return {"send_home": True, "id": id}

    event_types = ["Surgery", "Nursing_A", "Nursing_B"]
    excess_requests = 0

    for event_type in event_types:
        total_requests, capacity = check_traffic(event_type, arrival_time)
        if total_requests > capacity:
            excess_requests += total_requests - capacity
    if excess_requests > 2:
        print(f"Sending patient {id} home due to excess requests: {excess_requests}")
        return {"send_home": True, "id": id}
    return {"send_home": False, "id": id}


if __name__ == "__main__":
    threading.Thread(target=process_waiting_requests, daemon=True).start()
    if len(sys.argv) < 2:
        print("Bitte geben Sie die Simulationsdauer in Minuten an.")
        sys.exit(1)
    SIMULATION_END = int(sys.argv[1])
    run(app, host="::1", port=57874)


def get_simulation_state(time):
    state = []
    for event_type, event_data in events.items():
        for booking in event_data["bookings"]:
            if booking["start_time"] < time and booking["end_time"] >= time:
                state.append(
                    {
                        "cid": booking["id"],
                        "task": event_type,
                        "start": booking["start_time"],
                        "info": {"diagnosis": booking["metadata"]},
                        "wait": False,
                    }
                )
        for booking in event_data["active_bookings"]:
            if booking["start_time"] > time:
                state.append(
                    {
                        "cid": booking["id"],
                        "task": event_type,
                        "start": booking["arrival_time"],
                        "info": {"diagnosis": booking["metadata"]},
                        "wait": True,
                    }
                )
    for req in waiting_requests:
        if req["start_time"] < time and booking["end_time"] >= time:
            state.append(
                {
                    "cid": req["id"],
                    "task": req["event_type"],
                    "start": req["arrival_time"],
                    "info": {"diagnosis": req["metadata"]},
                    "wait": False,
                }
            )
        elif booking["start_time"] > time:
            state.append(
                {
                    "cid": req["id"],
                    "task": req["event_type"],
                    "start": req["arrival_time"],
                    "info": {"diagnosis": req["metadata"]},
                    "wait": True,
                }
            )
    return json.dumps(state, indent=4)
