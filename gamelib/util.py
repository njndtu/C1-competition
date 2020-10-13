import sys
import random

BANNER_TEXT = "---------------- Starting Your Algo --------------------"


def get_command():
    """Gets input from stdin

    """
    try:
        ret = sys.stdin.readline()
    except EOFError:
        # Game parent process terminated so exit
        debug_write("Got EOF, parent game process must have died, exiting for cleanup")
        exit()
    if ret == "":
        # Happens if parent game process dies, so exit for cleanup, 
        # Don't change or starter-algo process won't exit even though the game has closed
        debug_write("Got EOF, parent game process must have died, exiting for cleanup")
        exit()
    return ret

def send_command(cmd):
    """Sends your turn to standard output.
    Should usually only be called by 'GameState.submit_turn()'

    """
    sys.stdout.write(cmd.strip() + "\n")
    sys.stdout.flush()

def debug_write(*msg):
    """Prints a message to the games debug output

    Args:
        msg: The message to output

    """
    #Printing to STDERR is okay and printed out by the game but doesn't effect turns.
    sys.stderr.write(", ".join(map(str, msg)).strip() + "\n")
    sys.stderr.flush()


# given x,y coordinate returns coordinates as reflected across line thru x= 13.5
# when using, note it is returning a list of coords even if single coord in list
def mirror(coords):
    if type(coords[0]) == int:
        coords = [coords]
    
    mirrored_coords = []
    for coord in coords:
        mirrored_coords.append( [ int( 13.5 + (13.5 - coord[0])) ,coord[1] ]  )
        
    return mirrored_coords


# gives list with entries being
# a  list with entries being the [ list of (coord, 0/1) , % ]  
# returns the indices of each list. Tells me the order to look at
def ticket_maker(input_list):
    to_keep = []
    final = []
    for i in input_list:
        if len(i[0]) > 0:
            to_keep.append(i)

    if len(to_keep) == 0:
        # no repairs needed
        return final

    norm_factor = 0
    for i in to_keep:
        norm_factor += i[1]
    if norm_factor == 0:
        # that means they are all equal
        for i in input_list:
            final+= [j for j in i[0]]
        random.shuffle(final)
        return final
        
    tickets = []

    # we are assuming that percentage will always exceed the number of actual repairs needed
    for idx,i in enumerate(to_keep):
        tickets += [idx for i in range(int(200*i[1]/norm_factor))]

    random.shuffle(tickets)
    need = [len(i[0]) for i in to_keep]


    # (coords, 0/1, turrets or walls)
    for i in tickets:
        if need[i] > 0:
            final.append(to_keep[i][0][ len(to_keep[i][0]) - need[i] ])
            need[i]-=1
        else:
            continue

    return final
