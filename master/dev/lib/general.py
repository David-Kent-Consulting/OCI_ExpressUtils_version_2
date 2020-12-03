from time import sleep

def warning_beep(number_of_beeps):
    my_count = 0
    while my_count < int(number_of_beeps):
        print("WARNING! WARNING! WARNING! WARNING! WARNING! WARNING! WARNING! WARNING! WARNING! WARNING!")
        print("\a")
        sleep(1)
        my_count += 1