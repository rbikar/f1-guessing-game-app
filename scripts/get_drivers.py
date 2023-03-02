import requests
import json


API = "https://ergast.com/api/f1/2023"


def get_drivers():
    url = API + "/drivers.json"
    requests.get()


"""
"Drivers":[{"driverId":"alonso","permanentNumber":"14","code":"ALO","url":"http:\/\/en.wikipedia.org\/wiki\/Fernando_Alonso","givenName":"Fernando","familyName":"Alonso","dateOfBirth":"1981-07-29","nationality":"Spanish"},

"""
