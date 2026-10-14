import flask
import global_variables as globals
from queue import Queue


maxsizeQueue = 20
packetQueues = Queue(maxsize=maxsizeQueue)
for i in range(20):
    i += 1
    packetQueues.put(i)



print(packetQueues.queue)

for i in range(20//2):
    packetQueues.get()  # Remove the oldest data to make space for new data

print(packetQueues.queue)
    