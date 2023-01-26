#from makia_v2 import config
#from makia_v2.common.global_parameters import parameters
import requests
import json
import os


from upload import upload_info
base_url = "https://health.api.makia.ml"


base_standard = "http://localhost:3003"




def upload_information(information):
    headers = {
        "Authorization": 'hans',
        "Content-Type": "application/json"
    }

    entry_url = base_standard + "/makia/entries"
    response = requests.post(entry_url, data=json.dumps(information), headers=headers)
    return response


def upload_files(vehicle_id, up_files, delete_source=True):
    print("TRY UPLOAD STEP 1 " + str(vehicle_id))
    resp = None
    try:
        media_url = base_standard + "/makia/entries/" + str(vehicle_id) + "/images"

        payload = {}
        files = {}

        print("Upload", up_files)

        for up_file in up_files:
            files[up_file["identification"]] = (
            os.path.basename(up_file["path"]), open(up_file["path"], 'rb'), up_file["filetype"])

        header = {"Authorization": 0 }
        resp = requests.request("POST", media_url, headers=header, data=payload, files=files)
        print("TRY UPLOAD STEP FINISHED " + str(vehicle_id))


    finally:
        if delete_source:
            for up_file in up_files:
                try:
                    os.remove(up_file["path"])
                except:
                    pass
    return resp




upload_files(0, 0, False)
