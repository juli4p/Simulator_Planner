import random
import numpy as np
from datetime import datetime, timedelta


class GeneticPlanner:
    def __init__(self):
        # patients with assigend timeslot
        self.scheduled_patients = []

    def plan(self, cid, current_time, info, resources):
        # - cid: Patient ID
        # - current_time: current simulation time in hours since time 0
        # - info: patient diagnosis
        # - resources:cinfo about current hospital resources

        # Returns:
        # - planned_time: The planned arrival time for the patient

        self.scheduled_patients = [
            p for p in self.scheduled_patients if p["arrival_time"] > current_time
        ]

        # add current resources to scheduled_patients
        for res in resources:
            if res["cid"] not in [p["cid"] for p in self.scheduled_patients]:
                self.scheduled_patients.append(
                    {
                        "cid": res["cid"],
                        "arrival_time": res["start"],
                        "info": res["info"],
                        "tasks": [res["task"]],
                        "start_times": [res["start"]],
                    }
                )

        # initial population of arrival times
        population_size = 50
        generations = 20
        mutation_rate = 0.1
        population = self.generate_initial_population(current_time, population_size)

        # Run genetic algorithm
        for _ in range(generations):
            # Evaluate fitness
            fitness_scores = []
            for arrival_time in population:
                penalty = self.compute_penalty(
                    arrival_time, current_time, info, resources, self.scheduled_patients
                )
                fitness_scores.append(-penalty)  # aim: minimize penalty

            selected = self.selection(population, fitness_scores)
            offspring = self.crossover(selected, population_size)
            population = self.mutation(offspring, current_time, mutation_rate)

        # chose the best arrival time from the final population
        best_arrival_time = min(
            population,
            key=lambda at: self.compute_penalty(
                at, current_time, info, resources, self.scheduled_patients
            ),
        )

        # update scheduled_patients
        patient_schedule = self.simulate_patient_path(
            best_arrival_time, current_time, info, self.scheduled_patients
        )
        self.scheduled_patients.append(
            {
                "cid": cid,
                "arrival_time": best_arrival_time,
                "info": info,
                "tasks": patient_schedule["tasks"],
                "start_times": patient_schedule["start_times"],
                "durations": patient_schedule["durations"],
            }
        )

        return best_arrival_time

    def generate_initial_population(self, current_time, population_size):
        # Generate initial population of arrival times within constraints.
        population = []
        for _ in range(population_size):
            arrival_time = self.generate_random_arrival_time(current_time)
            population.append(arrival_time)
        return population

    def generate_random_arrival_time(self, current_time):
        # Generate a random arrival time within allowed constraints.
        # Time constraints
        min_time = current_time + 24  # At least 24 hours after current time
        max_time = current_time + 7 * 24  # No more than 7 days after current time

        # Generate random time within min_time and max_time during working hours
        while True:
            random_time = random.uniform(min_time, max_time)
            if self.is_working_hour(random_time):
                return random_time

    def is_working_hour(self, time_in_hours):
        # Check if the given time falls within working hours (Mon-Fri, 8:00-17:00).
        # Convert hours since time 0 to datetime
        base_time = datetime(2018, 1, 1)
        current_datetime = base_time + timedelta(hours=time_in_hours)

        # Check if it's a weekday
        if current_datetime.weekday() >= 5:
            return False

        # Check if it's within working hours
        if 8 <= current_datetime.hour < 17:
            return True
        return False

    def simulate_patient_path(
        self, arrival_time, current_time, info, scheduled_patients
    ):
        # Simulate the patient's path and schedule their resource usage.
        # Initialize patient schedule
        patient_schedule = {"tasks": [], "start_times": [], "durations": []}

        # Start with intake
        intake_duration = np.random.normal(1, 1 / 8)
        intake_start_time = self.find_next_available_time(
            "intake", arrival_time, intake_duration, scheduled_patients
        )
        if intake_start_time is None:
            patient_schedule["tasks"].append("intake")
            patient_schedule["start_times"].append(None)
            patient_schedule["durations"].append(intake_duration)
            return patient_schedule
        patient_schedule["tasks"].append("intake")
        patient_schedule["start_times"].append(intake_start_time)
        patient_schedule["durations"].append(intake_duration)

        # Update scheduled_patients with intake
        scheduled_patients.append(
            {
                "cid": "temp_intake",
                "arrival_time": intake_start_time,
                "tasks": ["intake"],
                "start_times": [intake_start_time],
                "durations": [intake_duration],
                "info": info,
            }
        )

        # Determine if patient needs surgery and/or nursing
        diagnosis = info["diagnosis"]
        needs_surgery = diagnosis in ["A2", "A3", "A4", "B3", "B4"]
        needs_nursing = diagnosis in ["A1", "A2", "A3", "A4", "B1", "B2", "B3", "B4"]

        # Schedule surgery if needed
        if needs_surgery:
            surgery_duration = self.get_surgery_duration(diagnosis)
            earliest_surgery_time = intake_start_time + intake_duration
            surgery_start_time = self.find_next_available_time(
                "surgery", earliest_surgery_time, surgery_duration, scheduled_patients
            )
            if surgery_start_time is None:
                patient_schedule["tasks"].append("surgery")
                patient_schedule["start_times"].append(None)
                patient_schedule["durations"].append(surgery_duration)
                return patient_schedule
            patient_schedule["tasks"].append("surgery")
            patient_schedule["start_times"].append(surgery_start_time)
            patient_schedule["durations"].append(surgery_duration)

            # Update scheduled_patients with surgery
            scheduled_patients.append(
                {
                    "cid": "temp_surgery",
                    "arrival_time": surgery_start_time,
                    "tasks": ["surgery"],
                    "start_times": [surgery_start_time],
                    "durations": [surgery_duration],
                    "info": info,
                }
            )

        # Schedule nursing if needed
        if needs_nursing:
            nursing_duration = self.get_nursing_duration(diagnosis)
            # Nursing starts after surgery if surgery is needed
            nursing_start_time = intake_start_time + intake_duration
            if needs_surgery:
                nursing_start_time = surgery_start_time + surgery_duration
            nursing_start_time = self.find_next_available_time(
                "nursing",
                nursing_start_time,
                nursing_duration,
                scheduled_patients,
                info,
            )
            if nursing_start_time is None:
                patient_schedule["tasks"].append("nursing")
                patient_schedule["start_times"].append(None)
                patient_schedule["durations"].append(nursing_duration)
                return patient_schedule
            patient_schedule["tasks"].append("nursing")
            patient_schedule["start_times"].append(nursing_start_time)
            patient_schedule["durations"].append(nursing_duration)

            # Update scheduled_patients with nursing
            scheduled_patients.append(
                {
                    "cid": "temp_nursing",
                    "arrival_time": nursing_start_time,
                    "tasks": ["nursing"],
                    "start_times": [nursing_start_time],
                    "durations": [nursing_duration],
                    "info": info,
                }
            )

        return patient_schedule

    def compute_penalty(
        self, arrival_time, current_time, info, resources, scheduled_patients
    ):
        # Compute the penalty for a given arrival time.
        penalty = 0

        # Simulate patient's path
        patient_schedule = self.simulate_patient_path(
            arrival_time, current_time, info, scheduled_patients.copy()
        )

        # Penalty if arrival_time exceeds 7 days
        if arrival_time - current_time > 7 * 24:
            penalty += 1000  # Large penalty for exceeding 7 days

        # Penalty for sending patient home (if resources are not available)
        if None in patient_schedule["start_times"]:
            penalty += 500  # Penalty for sending patient home

        # Penalty for late treatment
        # For patients who need surgery or nursing, we prefer earlier times
        if patient_schedule["start_times"][-1] is not None:
            total_treatment_time = patient_schedule["start_times"][-1] - arrival_time
            penalty += total_treatment_time  # Penalize longer waiting times

        # Consider ER patients
        # Estimate future ER patient arrivals and reserve capacity accordingly
        expected_er_patients = 1  # Average rate per hour
        er_penalty = (
            expected_er_patients * 10
        )  # Arbitrary penalty for potential ER conflicts
        penalty += er_penalty

        # You can include more detailed penalties based on resource constraints, overlapping schedules, etc.

        return penalty

    def selection(self, population, fitness_scores):
        # Select individuals based on fitness scores.
        # Convert fitness scores to probabilities
        total_fitness = sum(fitness_scores)

        # Handle the case where total_fitness is zero
        if total_fitness == 0:
            probabilities = [1 / len(fitness_scores) for _ in fitness_scores]
        else:
            probabilities = [f / total_fitness for f in fitness_scores]

        # Ensure probabilities are positive
        min_prob = min(probabilities)
        if min_prob < 0:
            probabilities = [p - min_prob + 1e-6 for p in probabilities]

        # Normalize probabilities
        total_prob = sum(probabilities)
        probabilities = [p / total_prob for p in probabilities]

        # Select individuals based on probabilities
        selected = np.random.choice(
            population, size=len(population) // 2, p=probabilities, replace=False
        )
        return selected.tolist()

    def crossover(self, selected, population_size):
        # Perform crossover between selected individuals to create offspring.
        offspring = []
        while len(offspring) < population_size:
            parent1, parent2 = random.sample(selected, 2)
            child = (parent1 + parent2) / 2  # Simple average crossover
            # Ensure child is within allowed time constraints and working hours
            min_time = min(parent1, parent2)
            max_time = max(parent1, parent2)
            child = max(min(child, max_time), min_time)
            if self.is_working_hour(child):
                offspring.append(child)
            else:
                # Adjust child to next working hour
                child = self.skip_to_next_working_hour(child)
                offspring.append(child)
        return offspring

    def mutation(self, offspring, current_time, mutation_rate):
        # Perform mutation on offspring.
        mutated_offspring = []
        for arrival_time in offspring:
            if random.random() < mutation_rate:
                # Mutate by adding a small random value
                arrival_time += random.uniform(-4, 4)  # Mutate by up to 4 hours
                # Ensure arrival_time stays within constraints
                min_time = current_time + 24
                max_time = current_time + 7 * 24
                if arrival_time < min_time:
                    arrival_time = min_time
                if arrival_time > max_time:
                    arrival_time = max_time
                # Ensure arrival_time is within working hours
                while not self.is_working_hour(arrival_time):
                    arrival_time += 1  # Move forward by 1 hour
            mutated_offspring.append(arrival_time)
        return mutated_offspring

    def find_next_available_time(
        self,
        resource_type,
        earliest_start_time,
        duration,
        scheduled_patients,
        info=None,
    ):
        # Find the next available time slot for a resource.
        # Get resource capacities
        if resource_type == "intake":
            capacity = 4  # 4 Intakes
            working_hours_only = True
        elif resource_type == "surgery":
            # 5 surgeries during working hours, 1 outside
            capacity_day = 5
            capacity_night = 1
            working_hours_only = False
        elif resource_type == "nursing":
            # 30 beds for Type A, 40 beds for Type B
            if info and info["diagnosis"].startswith("A"):
                capacity = 30
            else:
                capacity = 40
            working_hours_only = False
        else:
            return None  # Unknown resource type

        # Check for the next available time slot
        time = earliest_start_time
        max_search_time = earliest_start_time + 7 * 24  # Do not search beyond 7 days

        while time < max_search_time:
            # Check if resource is available at this time
            if resource_type == "surgery":
                capacity = (
                    capacity_day if self.is_working_hour(time) else capacity_night
                )
            count = self.count_resource_usage(resource_type, time, scheduled_patients)
            if count < capacity:
                return time
            time += 1  # Move to next hour
            if working_hours_only and not self.is_working_hour(time):
                # Skip to next working hour
                time = self.skip_to_next_working_hour(time)
            # Prevent infinite loop
            if time - earliest_start_time > 7 * 24:
                return None  # Could not find available slot within 7 days
        return None  # No available slot found

    def count_resource_usage(self, resource_type, time, scheduled_patients):
        # Count how many resources of a given type are in use at a specific time.
        count = 0
        for patient in scheduled_patients:
            for task, start_time, duration in zip(
                patient.get("tasks", []),
                patient.get("start_times", []),
                patient.get("durations", []),
            ):
                if task == resource_type and start_time is not None:
                    if start_time <= time < start_time + duration:
                        count += 1
        return count

    def get_task_duration(self, task, info):
        # Get the duration of a task based on diagnosis.
        if task == "intake":
            return np.random.normal(1, 1 / 8)
        elif task == "surgery":
            return self.get_surgery_duration(info["diagnosis"])
        elif task == "nursing":
            return self.get_nursing_duration(info["diagnosis"])
        return 0

    def get_surgery_duration(self, diagnosis):
        # Get surgery duration based on diagnosis.
        durations = {
            "A2": np.random.normal(1, 1 / 4),
            "A3": np.random.normal(2, 1 / 2),
            "A4": np.random.normal(4, 1 / 2),
            "B3": np.random.normal(4, 1 / 2),
            "B4": np.random.normal(4, 1),
        }
        return durations.get(diagnosis, 0)

    def get_nursing_duration(self, diagnosis):
        # Get nursing duration based on diagnosis.
        durations = {
            "A1": np.random.normal(4, 1 / 2),
            "A2": np.random.normal(8, 2),
            "A3": np.random.normal(16, 2),
            "A4": np.random.normal(16, 2),
            "B1": np.random.normal(8, 2),
            "B2": np.random.normal(16, 2),
            "B3": np.random.normal(16, 4),
            "B4": np.random.normal(16, 4),
        }
        return durations.get(diagnosis, 0)

    def skip_to_next_working_hour(self, time_in_hours):
        # Skip to the next working hour.
        while not self.is_working_hour(time_in_hours):
            time_in_hours += 1  # Move forward by 1 hour
        return time_in_hours


# Example Simulation results:
# --------------------------------
# Die Simulation hat 929.86 Sekunden gedauert.
# Es wurden 8760 Stunden simuliert.
# Folgende Scores wurden erzielt:
# {'er_treatment_score': 299.8870711518277, 'sent_home_score': 0.0, 'processed_score': 1650.1454264854276}
# --------------------------------
# Die Simulation hat 962.03 Sekunden gedauert.
# Es wurden 8760 Stunden simuliert.
# Folgende Scores wurden erzielt:
# {'er_treatment_score': 307.35557638901435, 'sent_home_score': 0.0, 'processed_score': 1670.4426629487627}
# --------------------------------
# Die Simulation hat 968.74 Sekunden gedauert.
# Es wurden 8760 Stunden simuliert.
# Folgende Scores wurden erzielt:
# {'er_treatment_score': 256.6641952094976, 'sent_home_score': 0.0, 'processed_score': 1689.2919836161498}
