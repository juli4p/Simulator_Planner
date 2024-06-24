# cpee_simulator
Simulator for Supportive Process Automation and Worker Assistance
(see https://sites.google.com/view/bpo2024/competition)

The CPEE model can be found at:
https://cpee.org/hub/?stage=development&dir=Teaching.dir/Prak.dir/Challengers.dir/Julian_Simon.dir/



The CPEE model requires the following attributes when creating new instances:

1. "patient_type" with possible values: "A1", "A2", "A3", "A4", "B1", "B2", "B3", "B4", "EM" 
2. "arrival_time": time in hours with 2 decimal places indicating the patient's arrival at the hospital (the simulation starts at "0" which is 0 am Monday morning)

CPEE model attribute explanations:
1. current_time: current time for specific instance
2. arrival_time: time of arrival of the patient
3. admission_time: time of admission of the patient
4. patient_type: type and diagnosis of patient
5. patient_id: unique id of patient
6. treatment_feasible: is treatment feasible or replan neccesary?
7. complications_nursing: did complications arise during nursing
8. complications_surgery: did complications arise during surgery
9. x_queue: time when patient enters queue for task x (the queue might be empty so the patient will be treated immediately)
10. x_start: time when the treatment at task x begins for the patient
11. x_end: time when the treatment at task x ends for the patient
12. log: log of tasks the instance went through
13. replanned_cpee_instance: in case of replan: new cpee instance that is created for the patient 

Notes:
1. If complications arise during surgery / nursing, the patient will queue again and receive further treatment according to their type and diagnosis.
2. Assumption: if an er patient does not receive a further diagnosis after their treatment, they did not suffer from an illness => phantom pain => only patients that remain as "EM" only, suffer from phantom pain and will not go through surgery and or nursing.
3. The simulator is reliant on the fact that all patients / instances get spawned in quick succesion (depending on the amount and delays a sleep timer can be increased /  decreased).
4. Furthermore patients / instances have to be created in chronological order (increasing arrival time)
5. The repository includes the simulator.py (which can be run on the lehre server), as well as a python program that can be used to spawn patients (arrival time, types, etc can be configured).

Usage of simulator:
1. run simulator.py (on the lehre server)
2. create and run instances of the cpee model (to create many instances in quick succession you can use spawn_patients.py)



created by Julian Simon
if you have any questions feel free to reach out to me via julian.simon@tum.de or discord 
