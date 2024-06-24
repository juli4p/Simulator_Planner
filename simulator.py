from bottle import Bottle, request, response
import uuid, logging, random, heapq, threading, requests, time, json


class Event:
    def __init__(
        self,
        event_type: str,
        event_start_time: float,
        event_end_time: float,
        patient_id: str,
        patient_type: str,
        callback_url: str,
        cpee_instance: str = None,
    ):
        self.event_type = event_type
        self.event_start_time = event_start_time
        self.event_end_time = event_end_time
        self.patient_id = patient_id
        self.patient_type = patient_type
        self.callback_url = callback_url
        self.cpee_instance = cpee_instance

    def __repr__(self):
        return (
            f"Event(event_type={self.event_type}, "
            f"event_start_time={self.event_start_time}, "
            f"event_end_time={self.event_end_time}, "
            f"patient_id={self.patient_id}, "
            f"patient_type={self.patient_type})"
        )


class TimePriorityQueue:
    def __init__(self):
        self._queue = []
        self._index = 0

    def push(self, item, priority):
        heapq.heappush(self._queue, (priority, self._index, item))
        self._index += 1

    def pop(self, return_priority=False):
        priority, index, item = heapq.heappop(self._queue)
        if return_priority:
            return item, priority
        return item

    def print_queue(self):
        print("Current event queue:")
        for priority, index, item in self._queue:
            print(f"Priority: {priority}, Index: {index}, Event: {item}")


# queue additionaly prioritizes EM events
class EMTimePriorityQueue(TimePriorityQueue):
    def push(self, item, priority):
        if "EM" in item.patient_type:
            priority = (0, item.event_start_time)
        else:
            priority = (1, item.event_start_time)
        super().push(item, priority)

    def pop(self, return_priority=False):
        priority, index, item = heapq.heappop(self._queue)
        if return_priority:
            return item, priority[1]
        return item


app = Bottle()
resources_available = {
    "Intake": 4,
    "Surgery": 5,
    "Nursing A": 30,
    "Nursing B": 40,
    "EM": 9,
}
resources_max = {"Intake": 4, "Surgery": 5, "Nursing A": 30, "Nursing B": 40, "EM": 9}
# only neccesery for Intake and Surgery
resources_busy = {"Intake": 0, "Surgery": 0}

# current time in hours
time_now = 0.0
# queues for stations
event_queue = TimePriorityQueue()
er_queue = TimePriorityQueue()
surgery_queue = EMTimePriorityQueue()
nursing_queue_A = EMTimePriorityQueue()
nursing_queue_B = EMTimePriorityQueue()

# check whether time in hours lies between 8 and 17 and is a weekday
is_working_hour = lambda h: 0 <= (h // 24) % 7 < 5 and 8 <= h % 24 < 17


@app.route("/incoming_event", method="POST")
def incoming_event():
    try:
        event_type = request.forms.get("event_type", None)
        # time of arrival of patient at station
        event_start_time = round(float(request.forms.get("event_start_time", -1)), 2)
        # initiate end time with -1, will be set when event is processed
        event_end_time = -1.0
        patient_id = request.forms.get("patient_id", None)
        patient_type = request.forms.get("patient_type", None)
        callback_url = request.headers.get("Cpee-Callback", None)
        cpee_instance = request.headers.get("Cpee-Instance", None)

        if any(
            x is None
            for x in [
                patient_id,
                patient_type,
                event_start_time,
                event_end_time,
                callback_url,
            ]
        ):
            response.status = 400
            return {
                "error": "Missing patient_id / patient_type / arrival_time in the request."
            }

        valid_types = ["A1", "A2", "A3", "A4", "B1", "B2", "B3", "B4", "EM"]
        if not any(type in patient_type for type in valid_types):
            return {"error": "Patient_type / diagnosis is not valid."}

        # add event to event queue and answer later when event is processed
        event_queue.push(
            Event(
                event_type,
                event_start_time,
                event_end_time,
                patient_id,
                patient_type,
                callback_url,
                cpee_instance,
            ),
            event_start_time,
        )
        response.headers["CPEE-CALLBACK"] = "true"
        return response

    except Exception as e:
        response.status = 500
        return {"error": f"Server error: {str(e)}"}


def run_while_loop():
    global time_now
    
    # TODO set desired sleep time
    # works better with higher values but also causes slower simulation
    # also depends on current workload of the cpee server
    # 1s = very good
    # should be good for 0.5s and more
    sleep_duration = 0.5
    
    # TODO set desired simualtion time
    # handle events in order until simulation time is reached (8760 hours = 1 year)
    while time_now < 8760.0:

        time.sleep(sleep_duration)

        current_event = None
        json_data = {"error": "No event occurred yet"}
        # true for events that trigger a response to cpee
        send_response = False

        # get next chronological event, if none available, wait for 1 second
        if len(event_queue._queue) > 0:
            # startung task events trigger on start time finishing task events on end time -> get priority
            current_event, event_priority = event_queue.pop(return_priority=True)
        else:
            time.sleep(1)
            continue

        # set time to event time that is currently handled
        time_diff = time_now - event_priority
        if time_diff >= 0:
            print(f"INFO: time_now was set from {time_now} to {event_priority}.")
            if time_diff > 1:
                # if this gets triggered sleep_duration is too low 
                print(f"ERROR: Big time difference of {time_diff}")
        time_now = event_priority

        # check whether current time is a working hour (mo-fr 8-17)
        if is_working_hour(time_now) == True:
            resources_max["Intake"] = 4
            resources_max["Surgery"] = 5
            resources_available["Intake"] = 4 - resources_busy["Intake"]
            resources_available["Surgery"] = 5 - resources_busy["Surgery"]
        else:
            resources_max["Intake"] = 0
            resources_max["Surgery"] = 1
            resources_available["Intake"] = 0
            resources_available["Surgery"] = 1 - resources_busy["Surgery"]

        # EVENT: PATIENT_ADMISSION
        if current_event.event_type == "patient_admission":

            # check whether intake is available
            if (
                resources_available.get("Intake", 0) > 0
                and len(surgery_queue._queue)
                + len(nursing_queue_A._queue)
                + len(nursing_queue_B._queue)
                < 2
            ):
                treatment_feasible = True
            else:
                treatment_feasible = False

            # er patients always get treated / queued for er treatment
            if "EM" in current_event.patient_type:
                treatment_feasible = True

            if treatment_feasible and "EM" not in current_event.patient_type:
                # already decrease intake ressources for non er patients (since there is no intake queue)
                if resources_available.get("Intake", 0) > 0:
                    resources_available["Intake"] -= 1
                    resources_busy["Intake"] += 1

            # check whether id exists, else create one
            if current_event.patient_id == "nicht vergeben":
                current_event.patient_id = str(uuid.uuid4())

            send_response = True
            json_data = {
                "patient_id": current_event.patient_id,
                "current_time": time_now,
                "treatment_feasible": treatment_feasible,
            }

        # REPLAN_PATIENT
        elif current_event.event_type == "replan_patient":
            # spawn new cpee instance, with arrival time in 1 day (24 hours)
            try:
                # replan in 26h to avoid infinite 0 intakes loop
                response = requests.post(
                    "https://cpee.org/flow/start/url/",
                    data={
                        "behavior": "fork_running",
                        "url": "https://cpee.org/hub/server/Teaching.dir/Prak.dir/Challengers.dir/Julian_Simon.dir/Main.xml",
                        "init": f'{{"arrival_time":"{time_now+26}","patient_type":"{current_event.patient_type}","patient_id":"{current_event.patient_id}","log":"Replanned_"}}',
                    },
                )
                cpee_inst = response.json().get("CPEE-INSTANCE")
                print(
                    f"Patient: {current_event.patient_id} replanned at CPEE-Instance: , {cpee_inst}"
                )
            except Exception as e:
                print(f"An error occurred: {str(e)}")

            # inform waiting cpee when intake was finished
            send_response = True
            json_data = {
                "current_time": time_now,
                "cpee_inst": cpee_inst,
            }

        # EVENT: INTAKE
        elif current_event.event_type == "intake":
            # check whether intake is available already happens at admission -> create intake finished event
            t_intake_finished = round(time_now + random.normalvariate(1, 0.125), 2)
            event_queue.push(
                Event(
                    "intake_finished",
                    time_now,
                    t_intake_finished,
                    current_event.patient_id,
                    current_event.patient_type,
                    current_event.callback_url,
                ),
                t_intake_finished,
            )

        # EVENT: INTAKE_FINISHED
        elif current_event.event_type == "intake_finished":

            # inform waiting cpee when intake was finished
            send_response = True
            json_data = {
                "intake_start": current_event.event_start_time,
                "intake_end": time_now,
            }

            # no need to check for waiting patients cause they would not be admitted if intake is full
            if resources_available.get("Intake", 0) < resources_max.get("Intake", 0):
                resources_available["Intake"] += 1
            # decrease busy intake resources also if max is reached
            if resources_busy.get("Intake", 0) > 0:
                resources_busy["Intake"] -= 1

        # ER_TREATMENT
        elif current_event.event_type == "er_treatment":
            # calc er duration
            t_er_finished = round(time_now + random.normalvariate(2, 0.5), 2)
            er_event = Event(
                "er_treatment_finished",
                time_now,
                t_er_finished,
                current_event.patient_id,
                current_event.patient_type,
                current_event.callback_url,
            )

            # check availability
            if resources_available.get("EM", 0) > 0:
                resources_available["EM"] -= 1
                event_queue.push(er_event, t_er_finished)
            # else queue patient
            else:
                # prioitize by arrival time in queue
                er_queue.push(er_event, current_event.event_start_time)

        # EVENT: ER_TREATMENT_FINISHED
        elif current_event.event_type == "er_treatment_finished":

            # check for further diagnosis (50% prob) and add type if true
            # no diagnosis => phantom pain => type stays as "EM"
            further_treatment_types = ["A1", "A2", "A3", "A4", "B1", "B2", "B3", "B4"]
            if random.random() < 0.5:
                current_event.patient_type = f"{current_event.patient_type}-{random.choice(further_treatment_types)}"

            # inform waiting cpee when er_treatment was finished, update patient_type
            send_response = True
            json_data = {
                "er_start": current_event.event_start_time,
                "er_end": time_now,
                "patient_type": current_event.patient_type,
            }

            # check whether someone is waiting for er_treatment, if yes let him in
            if len(er_queue._queue) > 0:
                waiting_er = er_queue.pop()
                waiting_er_end_time = round(
                    time_now
                    + (waiting_er.event_end_time - waiting_er.event_start_time),
                    2,
                )
                event_queue.push(
                    Event(
                        "er_treatment_finished",
                        time_now,
                        waiting_er_end_time,
                        waiting_er.patient_id,
                        waiting_er.patient_type,
                        waiting_er.callback_url,
                    ),
                    waiting_er_end_time,
                )
            # else release ressource
            else:
                if resources_available.get("EM", 0) < resources_max.get("EM", 0):
                    resources_available["EM"] += 1

        # EVENT: NURSING
        elif current_event.event_type == "nursing":

            # time needed for nursing, depending on patient_type
            if "A1" in current_event.patient_type:
                nursing_duration = random.normalvariate(4, 0.5)
            elif (
                "A2" in current_event.patient_type or "B1" in current_event.patient_type
            ):
                nursing_duration = random.normalvariate(8, 2)
            elif (
                "B3" in current_event.patient_type or "B4" in current_event.patient_type
            ):
                nursing_duration = random.normalvariate(16, 4)
            else:
                nursing_duration = random.normalvariate(16, 2)

            t_nursing_finished = round(time_now + nursing_duration, 2)

            nursing_event = Event(
                "nursing_finished",
                time_now,
                t_nursing_finished,
                current_event.patient_id,
                current_event.patient_type,
                current_event.callback_url,
            )

            # check availability for type A patients
            if "A" in current_event.patient_type:
                if resources_available.get("Nursing A", 0) > 0:
                    resources_available["Nursing A"] -= 1
                    event_queue.push(nursing_event, t_nursing_finished)
                # else queue patient
                else:
                    # prioitize by arrival time in queue (ER patients first)
                    nursing_queue_A.push(nursing_event, current_event.event_start_time)

            # check availability for type B patients
            elif "B" in current_event.patient_type:
                if resources_available.get("Nursing B", 0) > 0:
                    resources_available["Nursing B"] -= 1
                    event_queue.push(nursing_event, t_nursing_finished)
                # else queue patient
                else:
                    # prioitize by arrival time in queue (ER patients first)
                    nursing_queue_B.push(nursing_event, current_event.event_start_time)

            else:
                print("ERROR: Nursing should only be called for A or B patients")

        # NURSING_FINISHED
        elif current_event.event_type == "nursing_finished":

            # complications during nursing
            complications_nursing = False
            # calc nursing complications
            if (
                "A1" in current_event.patient_type
                or "A2" in current_event.patient_type
                or "B2" in current_event.patient_type
            ):
                nursing_complication_prob = 0.01
            elif "B1" in current_event.patient_type:
                nursing_complication_prob = 0.001
            else:
                nursing_complication_prob = 0.02
            if random.random() < nursing_complication_prob:
                complications_nursing = True

            # inform waiting cpee when nursing was finished, whether complications occured
            send_response = True
            json_data = {
                "nursing_start": current_event.event_start_time,
                "nursing_end": time_now,
                "complications_nursing": complications_nursing,
            }

            # check whether someone is waiting for nursing A, if yes let him in
            if "A" in current_event.patient_type:
                if len(nursing_queue_A._queue) > 0:
                    waiting_nursing_A = nursing_queue_A.pop()
                    waiting_nursing_A_end_time = round(
                        time_now
                        + (
                            waiting_nursing_A.event_end_time
                            - waiting_nursing_A.event_start_time
                        ),
                        2,
                    )
                    event_queue.push(
                        Event(
                            "nursing_finished",
                            time_now,
                            waiting_nursing_A_end_time,
                            waiting_nursing_A.patient_id,
                            waiting_nursing_A.patient_type,
                            waiting_nursing_A.callback_url,
                        ),
                        waiting_nursing_A_end_time,
                    )
                # else release ressource
                else:
                    if resources_available.get("Nursing A", 0) < resources_max.get(
                        "Nursing A", 0
                    ):
                        resources_available["Nursing A"] += 1

            # same for type B
            elif "B" in current_event.patient_type:
                if len(nursing_queue_B._queue) > 0:
                    waiting_nursing_B = nursing_queue_B.pop()
                    waiting_nursing_B_end_time = round(
                        time_now
                        + (
                            waiting_nursing_B.event_end_time
                            - waiting_nursing_B.event_start_time
                        ),
                        2,
                    )
                    event_queue.push(
                        Event(
                            "nursing_finished",
                            time_now,
                            waiting_nursing_B_end_time,
                            waiting_nursing_B.patient_id,
                            waiting_nursing_B.patient_type,
                            waiting_nursing_B.callback_url,
                        ),
                        waiting_nursing_B_end_time,
                    )
                # else release ressource
                else:
                    if resources_available.get("Nursing B", 0) < resources_max.get(
                        "Nursing B", 0
                    ):
                        resources_available["Nursing B"] += 1
            else:
                print("ERROR: Nursing should only be called for A or B patients")

        # EVENT: SURGERY
        elif current_event.event_type == "surgery":

            # time needed for surgery, depending on patient_type
            if "A2" in current_event.patient_type:
                surgery_duration = random.normalvariate(1, 0.25)
            elif "A3" in current_event.patient_type:
                surgery_duration = random.normalvariate(2, 0.5)
            elif "B4" in current_event.patient_type:
                surgery_duration = random.normalvariate(4, 1)
            else:
                surgery_duration = random.normalvariate(4, 0.5)

            t_surgery_finished = round(time_now + surgery_duration, 2)

            surgery_event = Event(
                "surgery_finished",
                time_now,
                t_surgery_finished,
                current_event.patient_id,
                current_event.patient_type,
                current_event.callback_url,
            )

            # check whether surgery is available
            if resources_available.get("Surgery", 0) > 0:
                resources_available["Surgery"] -= 1
                resources_busy["Surgery"] += 1
                event_queue.push(surgery_event, t_surgery_finished)
            # else queue patient
            else:
                # prioitize by arrival time in queue (ER patients first)
                surgery_queue.push(surgery_event, current_event.event_start_time)

        # SURGERY_FINISHED
        elif current_event.event_type == "surgery_finished":

            # complications during surgery
            complications_surgery = False
            # all surgerys 2% chance of complications, only A2 = 1%
            if "A2" in current_event.patient_type:
                surgery_complication_prob = 0.01
            else:
                surgery_complication_prob = 0.02
            if random.random() < surgery_complication_prob:
                complications_surgery = True

            # inform waiting cpee when surgery was finished, whether complications occured
            send_response = True
            json_data = {
                "surgery_start": current_event.event_start_time,
                "surgery_end": time_now,
                "complications_surgery": complications_surgery,
            }

            # check whether someone is waiting for surgery, if yes let him in
            if len(surgery_queue._queue) > 0:
                waiting_surgery = surgery_queue.pop()
                waiting_surgery_end_time = round(
                    time_now
                    + (
                        waiting_surgery.event_end_time
                        - waiting_surgery.event_start_time
                    ),
                    2,
                )
                event_queue.push(
                    Event(
                        "surgery_finished",
                        time_now,
                        waiting_surgery_end_time,
                        waiting_surgery.patient_id,
                        waiting_surgery.patient_type,
                        waiting_surgery.callback_url,
                    ),
                    waiting_surgery_end_time,
                )
            # else release ressource
            else:
                if resources_available.get("Surgery", 0) < resources_max.get(
                    "Surgery", 0
                ):
                    resources_available["Surgery"] += 1
                    if resources_busy.get("Surgery", 0) > 0:
                        resources_busy["Surgery"] -= 1
                    else:
                        print("ERROR: There should be busy surgery resources")

        # send response to callback url, depending on event that happened
        if send_response == True:
            try:
                response = requests.put(current_event.callback_url, json=json_data)
                # Testing only
                print(
                    f"Arbeitswoche: {is_working_hour(time_now) == True}\nRessource_available: {resources_available}\nRessources_max: {resources_max} \nResources_busy: {resources_busy}\nCpee-Instance: {current_event.cpee_instance}"
                )
            except requests.exceptions.RequestException as e:
                print(f"An error occurred: {str(e)}")


if __name__ == "__main__":
    t = threading.Thread(target=run_while_loop)
    t.start()
    app.run(host="::1", port=57874, debug=True)
