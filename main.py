import datetime
import os
import time
import threading
import psutil
import subprocess
import mysql.connector
from mysql.connector import Error

DATABASE_NAME = None
DATABASE_USER = None
DATABASE_PASSWORD = None
HOST = None

CPU_PERCENTAGE_MAX = None
MEMORY_PERCENTAGE_MAX = None
DISK_USAGE_MAX = None
NOTIFY_WHEN_DOWN = None

kill_threads = False
config_folder = 'config'


def load_database_data():
    global DATABASE_NAME, DATABASE_USER, DATABASE_PASSWORD, HOST
    config_folder = 'config'
    database_conf = open(f'{config_folder}/database.conf')

    line = database_conf.readline().split('=')
    while line[0] != '':

        if line[0] == 'database_name':
            DATABASE_NAME = line[1].strip().replace('\n', '')

        elif line[0] == 'database_user':
            DATABASE_USER = line[1].strip().replace('\n', '')

        elif line[0] == 'database_password':
            DATABASE_PASSWORD = line[1].strip().replace('\n', '')

        elif line[0] == 'host':
            HOST = line[1].strip().replace('\n', '')

        line = database_conf.readline().split('=')

    database_conf.close()

    if DATABASE_NAME is None \
            or DATABASE_USER is None \
            or DATABASE_PASSWORD is None:

        return False

    else:
        return True


def load_threshold_data():
    global CPU_PERCENTAGE_MAX, MEMORY_PERCENTAGE_MAX, DISK_USAGE_MAX, NOTIFY_WHEN_DOWN, config_folder

    threshold_conf = open(f'{config_folder}/threshold.conf')

    line = threshold_conf.readline().split('=')
    while line[0] != '':

        if line[0] == 'cpu_percentage_max':
            CPU_PERCENTAGE_MAX = float(line[1].strip().replace('\n', ''))

        elif line[0] == 'memory_percentage_max':
            MEMORY_PERCENTAGE_MAX = float(line[1].strip().replace('\n', ''))

        elif line[0] == 'disk_usage_max':
            DISK_USAGE_MAX = float(line[1].strip().replace('\n', ''))

        elif line[0] == 'notify_when_down':
            NOTIFY_WHEN_DOWN = bool(line[1].strip().replace('\n', ''))

        line = threshold_conf.readline().split('=')

    threshold_conf.close()

    if \
            CPU_PERCENTAGE_MAX is None \
                    or MEMORY_PERCENTAGE_MAX is None \
                    or DISK_USAGE_MAX is None \
                    or NOTIFY_WHEN_DOWN is None:

        return False

    else:
        return True


def change_threshold_data(attribute: str, new_value: float or bool):
    global config_folder
    lines = None
    with open(f'{config_folder}/threshold.conf', 'r') as file:
        lines = file.readlines()
        for line in lines:
            if line.__contains__(attribute):
                lines.remove(line)
                lines.append(f'\n{attribute}={new_value}')

    with open(f'{config_folder}/threshold.conf', 'w') as file:
        file.writelines(lines)


def write_log(target: str):
    logs_file_path = 'logs'
    date_obj = datetime.datetime.now()
    day = f'{date_obj.day}-{date_obj.month}-{date_obj.year}'

    if target == 'cpu':
        with open(f'{logs_file_path}/{day}.txt', 'a') as f:
            f.write(
                f'{date_obj.hour}:{date_obj.minute}:{date_obj.second} - CPU threshold of {CPU_PERCENTAGE_MAX}% of usage exceeded\n'
                f'CPU usage on timestamp: {psutil.cpu_percent()}%\n')
            f.close()

    if target == 'memory':
        with open(f'{logs_file_path}/{day}.txt', 'a') as f:
            f.write(
                f'{date_obj.hour}:{date_obj.minute}:{date_obj.second} - Memory threshold of {MEMORY_PERCENTAGE_MAX}% of usage exceeded\n'
                f'Memory usage on timestamp: {psutil.virtual_memory().percent} %\n')
            f.close()

    if target == 'disk':
        with open(f'{logs_file_path}/{day}.txt', 'a') as f:
            f.write(
                f'{date_obj.hour}:{date_obj.minute}:{date_obj.second} - Disk threshold of {DISK_USAGE_MAX}% of usage exceeded\n'
                f'Disk usage on timestamp: {psutil.disk_usage("/").percent} %\n')
            f.close()

    if NOTIFY_WHEN_DOWN:
        if target == 'down':
            with open(f'{logs_file_path}/{day}.txt', 'a') as f:
                f.write(f'{date_obj.hour}:{date_obj.minute}:{date_obj.second} - Webserver offline\n')
                f.close()


def get_memory_usage():
    return float(psutil.virtual_memory().percent)


def get_cpu_usage():
    return float(psutil.cpu_percent())


def get_storage_use():
    return psutil.disk_usage('/').percent


def get_webserver_status():
    terminal_output = subprocess.run(['service', 'apache2', 'status'], stdout=subprocess.PIPE).stdout.decode('utf-8')
    for line in terminal_output.split('\n'):
        if line.__contains__('active (running)'):
            return True

    return False


def get_database_stats():
    connection = None
    load_database_data()

    try:
        print('-----------------------------')
        print('Connecting to MySQL Server...')
        connection = mysql.connector.connect(
            host=HOST,
            database=DATABASE_NAME,
            user=DATABASE_USER,
            password=DATABASE_PASSWORD
        )

        if connection.is_connected():
            print('Connection established \n\n')
            cursor = connection.cursor()

            cursor.execute('show tables;')
            tables = cursor.fetchall()
            tables = list(map(lambda x: x[0], tables))

            print(f'There is {len(tables)} tables in Wordpress database\n')

            for i in range(len(tables)):
                cursor.execute(f'select count(*) from {tables[i]}')
                entries = list(map(lambda x: x[0], cursor.fetchmany(1)))

                print(f'{i + 1}. {tables[i]} -> {entries[0]} entries')

    except Error as e:
        print('Error found when trying connect to database')
        print(e)

    finally:
        if connection.is_connected():
            connection.close()
        print('-----------------------------')

        input()
        cls()
        live_monitor()


def process():
    global CPU_PERCENTAGE_MAX, MEMORY_PERCENTAGE_MAX, DISK_USAGE_MAX, NOTIFY_WHEN_DOWN, kill_threads
    load_threshold_data()

    while True:
        if get_cpu_usage() >= CPU_PERCENTAGE_MAX and get_cpu_usage() > 0:
            write_log('cpu')

        if get_memory_usage() >= MEMORY_PERCENTAGE_MAX:
            write_log('memory')

        if get_storage_use() >= DISK_USAGE_MAX:
            write_log('disk')

        if get_webserver_status() is False:
            write_log('down')

        if kill_threads:
            break

        time.sleep(0.25)


def live_monitor():
    print('0. Back()\n')
    print('1. CPU')
    print('2. Memory')
    print('3. Storage')
    print('4. Webserver')
    print('5. Database\n')
    option = input('Select an option: ')
    print('\n')

    if option == '0':
        cls()
        main_screen()

    elif option == '1':
        print('------------------------')
        print(f'CPU usage: {get_cpu_usage()} %')
        print('------------------------')
        time.sleep(2)
        cls()
        live_monitor()

    elif option == '2':
        print('------------------------')
        print(f'Memory usage: {get_memory_usage()} %')
        print('------------------------')
        time.sleep(2)
        cls()
        live_monitor()

    elif option == '3':
        print('------------------------')
        print(f'Disk usage: {get_storage_use()} %')
        print('------------------------')
        time.sleep(2)
        cls()
        live_monitor()

    elif option == '4':
        print('------------------------')

        if get_webserver_status():
            print('Active (running)')
        else:
            print('Inactive (stopped)')

        print('------------------------')
        time.sleep(2)
        cls()
        live_monitor()

    elif option == '5':
        get_database_stats()

    else:
        print('Invalid option')
        time.sleep(2)
        cls()
        live_monitor()


def threshold_config():
    global CPU_PERCENTAGE_MAX, MEMORY_PERCENTAGE_MAX, DISK_USAGE_MAX, NOTIFY_WHEN_DOWN
    cls()

    print('Current thresholds: \n')
    print(f'1. CPU_PERCENTAGE_MAX: {CPU_PERCENTAGE_MAX} %')
    print(f'2. MEMORY_PERCENTAGE_MAX: {MEMORY_PERCENTAGE_MAX} %')
    print(f'3. DISK_USAGE_MAX: {DISK_USAGE_MAX} %')
    print(f'4. NOTIFY_WHEN_DOWN: {NOTIFY_WHEN_DOWN}')
    print('\n')
    choice = input('e -> edit or b -> back: ')

    if choice.lower() == 'e':
        print('\n')
        print('-----------------------')
        choice = input('Choose the threshold: ')
        new_value = input('\t New value: ')
        print('-----------------------')

        if choice == '1':
            CPU_PERCENTAGE_MAX = float(new_value)
            change_threshold_data('cpu_percentage_max', CPU_PERCENTAGE_MAX)
            time.sleep(1)
            threshold_config()

        elif choice == '2':
            MEMORY_PERCENTAGE_MAX = float(new_value)
            change_threshold_data('memory_percentage_max', MEMORY_PERCENTAGE_MAX)
            time.sleep(1)
            threshold_config()

        elif choice == '3':
            DISK_USAGE_MAX = float(new_value)
            change_threshold_data('disk_usage_max', DISK_USAGE_MAX)
            time.sleep(1)
            threshold_config()

        elif choice == '4':
            if new_value.lower() == 'true':
                NOTIFY_WHEN_DOWN = True
                change_threshold_data('notify_when_down', NOTIFY_WHEN_DOWN)
                time.sleep(1)
                threshold_config()

            elif new_value.lower() == 'false':
                NOTIFY_WHEN_DOWN = False
                change_threshold_data('notify_when_down', NOTIFY_WHEN_DOWN)
                time.sleep(1)
                threshold_config()

            else:
                print('\n Invalid value')
                time.sleep(1)
                threshold_config()

        else:
            print('\n Invalid option')
            time.sleep(1)
            threshold_config()

    elif choice.lower() == 'b':
        cls()
        main_screen()

    else:
        print('\n Invalid option')
        time.sleep(1)
        threshold_config()


def main_screen():
    global kill_threads

    print("Apache Server Monitor is running\n")
    print('0. Exit()\n')
    print('1. Live monitor')
    print('2. Threshold configuration')
    option = input('Choose: ')

    if option == '0':
        kill_threads = True

    elif option == '1':
        cls()
        live_monitor()

    elif option == '2':
        cls()
        threshold_config()

    else:
        print('Invalid option')
        time.sleep(2)
        cls()
        main_screen()


def cls():
    os.system('clear')


cli = threading.Thread(name='cli', target=main_screen)
monitor = threading.Thread(name='monitor', target=process)

cli.start()
monitor.start()
