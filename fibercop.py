from http import client
from urllib import request
from bs4 import BeautifulSoup
from colorama import Fore, Style, init, deinit
from os.path import exists as file_exists
import os
import requests
import re
import json
import datetime
import bigdatacloudapi
import io

init()
current_time = datetime.datetime.now()
URL = 'https://www.fibercop.it/cantieri-in-corso/'
LOGS_DIR = './logs/'
cantieri_regex = r"\bFFCantieri =\s+(.*)$"
cantieri_string = ''

vecchi_cantieri = []
cantieri = []
cantieri_chiusi = []
cantieri_nati = []

api_key = ''

with open("api_file.bin", encoding="utf-8") as binary_file:
    # Read the whole file at once
    api_key = str(binary_file.read())

class Cantiere:
    def __init__(self, lat, lng):
        self.lat = lat
        self.lng = lng
    def __eq__(self, other):
        if((self.lng == other.lng) and (self.lat == other.lat)):
            return True
        else:
            return False

# The following function is used to pretty print text
def print_colored(s, color):
    print(f'{color}{s}{Style.RESET_ALL}')

def fetch_cantieri(url):
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")
    script = re.sub('\s+',' ',str(soup.find('script')))
    matches = re.finditer(cantieri_regex, script, re.MULTILINE)

    for _, match in enumerate(matches, start=1):
        cantieri_string = match.group(1)[9:-15]

    cantieri_string = re.sub(r"lat", "\"lat\"", cantieri_string)
    cantieri_string = re.sub(r"lng", "\"lng\"", cantieri_string)
    cantieri_string = '[' + cantieri_string + ']'

    for item in json.loads(cantieri_string):
        cantiere = Cantiere(item['lat'], item['lng'])
        cantieri.append(cantiere)
    
    print("Cantieri have been successfully fetched.")

def read_logged_cantieri(path):
    print('Reading from log ', path)
    f = open(path, 'r')
    lines = f.readlines()
    for line in lines:
        coordinates = line.split(' ')
        lat = (coordinates[0])[4:]
        lng = (coordinates[1])[4:-1]
        vecchi_cantieri.append(Cantiere(float(lat), float(lng)))
    f.close()

def check_still_open():
    for vecchio_cantiere in vecchi_cantieri:
        if not vecchio_cantiere in cantieri:
            # cantiere chiuso
            cantieri_chiusi.append(vecchio_cantiere)
            print_colored("- lat:{} lng:{}".format(str(vecchio_cantiere.lat), str(vecchio_cantiere.lng)), Fore.RED)
            reverse_geocoding(vecchio_cantiere)

def check_new_opened():
    for nuovo_cantiere in cantieri:
        if not nuovo_cantiere in vecchi_cantieri:
            # cantiere nuovo
            cantieri_nati.append(nuovo_cantiere)
            print_colored("+ lat:{} lng:{}".format(str(nuovo_cantiere.lat), str(nuovo_cantiere.lng)), Fore.GREEN)
            reverse_geocoding(nuovo_cantiere)

def get_last_log(logs):
    print('Getting last log...')
    if len(logs) > 1: #the folder is not empty. 1 is used to avoid .DS_Store
        return (LOGS_DIR + logs[len(logs)-1])
    else:
        log_name = LOGS_DIR + '{}.txt'.format(str(current_time)[:10])
        print("Haven't found any logs. Generating a blank file called " + log_name)
        return log_name

def log_results_to_file(path):
    f = open(path, 'a')
    for cantiere in cantieri:
        cantiere_string = 'lat:{} lng:{}'.format(str(cantiere.lat), str(cantiere.lng))
        f.write('{}\n'.format(cantiere_string))
    print('Created log file to path: ' + path)

def reverse_geocoding(coordinates):
    response = requests.get("https://api.bigdatacloud.net/data/reverse-geocode-client?latitude={}&longitude={}&localityLanguage=it".format(coordinates.lat, coordinates.lng)).json()
    print(response['city'], ' - ', response['locality'])

def main():

    init()

    logs = os.listdir(LOGS_DIR)
    logs.sort()

    fetch_cantieri(URL)
    last_log = get_last_log(logs) 
    if file_exists(last_log):
        read_logged_cantieri(last_log)
    check_still_open()
    check_new_opened()
    
    # print(logs)
    output_path = LOGS_DIR + '{}.txt'.format(str(current_time)[:10])

    if file_exists(output_path):
        # o si chiama data.txt, o si chiama data_n.txt
        if len(logs[len(logs)-1]) == 14:
            log_results_to_file(LOGS_DIR + '{}_1.txt'.format(str(current_time)[:10]))
        elif len(logs[len(logs)-1]) == 16:
            counter = int(last_log[-5:-4]) # better implementation is possible with regex
            if counter == 9:
                print_colored("Error: you've reached the maximum number of runs for today. Come back tomorrow.", Fore.RED)
                exit(0)
            log_results_to_file(LOGS_DIR + '{}_{}.txt'.format(str(current_time)[:10], counter+1))
        else:
            print("ERROR: Can't log to file.")
    else:
        # create it
        log_results_to_file(output_path)

    print('\n')
    deinit()

if __name__ == "__main__":
    main()