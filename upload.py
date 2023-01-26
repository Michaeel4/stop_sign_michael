import json
import requests


from vehicle import Vehicle

base_url = "http://localhost:3003"



'''
Based on the existing backend solution, there are several different parameters in the database
'''
#vehicle = Vehicle(id, 0, "forward", 0, 0, 27, 0, 0, 0, 1)


def upload_info(vehicle):

    print("Uploading information")
    entry_url = base_url + "/makia/entries"

    data = {'timestamp': vehicle.timestamp, 'locationID': 0, 'direction': 'forward ',
        'category': vehicle.category, 'stoppedForMs': 0, 'avgVelocity': vehicle.speed,
            'minVelocity': 0, 'stoppedDistance':0, 'convoyIndex':0, 'convoyType':vehicle.convoyType}
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    requests.post(entry_url, data=json.dumps(data), headers=headers)










