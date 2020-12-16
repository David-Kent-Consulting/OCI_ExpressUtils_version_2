from time import sleep

class GetInputOptions:
    '''
    Method parses an argument list for arguments and their respective
    inputs. Input options with data input items minus the pre-options
    inputs must be a mod return value of 0 in order for
    self.argument_list_with_input to populate. If you populate and
    get a length of 0, then the input list is uneven. Your calling
    program logic must handle this condition.

    Pass to this method an argument vector of data inputes to the CLI to
    instiate the data as in:
        my_arg_list = GetInputOptions(sys.argv)

    To extract the argument list with data inputs, do something like th following:
        my_arg_list.populate_input_options(5)
    This will perform a mod calculation, verify the result = 0, and only if equal
    to 0 will it then populate self.argument_list_with_input.

    To get an input option's data input, do something like:
    my_input = my_arg_list.return_input_option_data("--DISPLAY-NAME")
    The method will search for the option in the list, and then return the next
    item, which should be the user's input.
    
    To get the options passed in sys.argv that 
    '''
    def __init__(self, my_list):
        self.my_list = my_list
        self.argument_list_with_input = []
        
    def populate_input_options(self, start_position):
                
        if (len(self.my_list) - (start_position + 1)) % 2:
            cntr = start_position
            while cntr < len(self.my_list):
                self.argument_list_with_input.append(self.my_list[cntr])
                self.argument_list_with_input.append(self.my_list[cntr+1])
                cntr += 2
    
    def return_input_option_data(self, my_option):
        count = len(self.argument_list_with_input)
        cntr = 0
        while cntr < count:
            if self.argument_list_with_input[cntr] == my_option:
                return self.argument_list_with_input[cntr+1]
            cntr += 2

def warning_beep(number_of_beeps):
    my_count = 0
    while my_count < int(number_of_beeps):
        print("WARNING! WARNING! WARNING! WARNING! WARNING! WARNING! WARNING! WARNING! WARNING! WARNING!")
        print("\a")
        sleep(1)
        my_count += 1

# end function warning_beep()