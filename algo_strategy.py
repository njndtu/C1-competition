import gamelib
import random
import math
import warnings
from sys import maxsize
import json
from tower_defense import *


"""
Most of the algo code you write will be in this file unless you create new
modules yourself. Start by modifying the 'on_turn' function.

Advanced strategy tips: 

  - You can analyze action frames by modifying on_action_frame function

  - The GameState.map object can be manually manipulated to create hypothetical 
  board states. Though, we recommended making a copy of the map to preserve 
  the actual current map state.
"""

class AlgoStrategy(gamelib.AlgoCore):

    global RUNWAY, ARENA_SIZE, HALF_ARENA, LEFTHOME, RIGHTHOME,FUNNEL, GREATWALL, ENTRANCE, FARM
    '''
    Constants:

    RUNWAY : never place units here, leave this space open. Represents the two paths our mobile units can potentially go on. RUNWAY[0/1] provides left and right side respectively from bottom to start. Is a zig zag. Up left Up left. Only coordinates in RUNWAY that can be blocked are RUNWAY[0][-1] and RUNWAY[1][-1] is if we decide to attack. 

    LEFT/RIGHTHOME : ground origins for left side and right side respeciverly.

    FARM : Region to place factories, 4 coordinates representing bottom right, top right, bottom left, top left




    LEFT/RIGHT_FUNNEL : regions for left and right funnels respecively.
         - [0,13], [1,12], [2,11], [3,10] : walls must exist at all times
         - [3,13], [4,13] : potentials walls. These will spawn if heavy firepower
         - [4,12] helper turret
         - [3,10], will originaly be wall, whenever this wall drops below (?) % percent help. swap to turret

    
    LEFT/RIGHT_ENTRANCE : Another wall and turret strucutre, its a slanted wall. Gives the coordinates for where the turrets should be. 
         - [11,9] aka the hole. will be left open. For interceptors to patrol walls. (?) On attack formation if needed will plug to allow more coordinated attacks

    
    LEFT/RIGHT_WALL : Simple wall and turret structure
    
5
    '''
    RUNWAY = [[5,9],[13,1],[13,0],[5,8]] # must be kept empty
    
    ARENA_SIZE = 28
    HALF_ARENA = int(ARENA_SIZE / 2)

    LEFTHOME = [13,0]
    RIGHTHOME = [14,0]
    
    FARM = [[13,2],[13,6],[11,4],[11,8]]
    
    
    FUNNEL =  [ [4,13], [4,9], [0,13] ] # top right, bottom right, top left

    
    GREATWALL = [[5,13],[8,13],[8,12],[5,12]]
    
    ENTRANCE = [[9,11],[13,7]]
    

    
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        """ 
        Read in config and perform any initial setup here 
        """
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global WALL, FACTORY, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP
        WALL = config["unitInformation"][0]["shorthand"]
        FACTORY = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        MP = 1
        SP = 0
        # This is a good place to do initial setup
        self.scored_on_locations = []

        self.farm = self.init_farmland()
        self.wall_left, self.wall_right = self.init_wall()
        self.funnel_left, self.funnel_right = self.init_funnel()
        self.entrance_left, self.entrance_right = self.init_entrance()
        

        
        self.left = SideDefense(Wall(self.wall_left), Entrance(self.entrance_left), Funnel(self.funnel_left),config )
        self.right = SideDefense(Wall(self.wall_right,True), Entrance(self.wall_right, True), Funnel(self.funnel_right, True),config)


    def init_farmland(self):
        coords = []
        cur = FARM[0]
        width = abs(FARM[2][0] - FARM[0][0]) +1
        height = abs(FARM[1][1] - FARM[0][1]) + 1

        for y in range(height):
            for x in range(width):
                to_add = [ cur[0]-(x), cur[1]+(y)+x ]
                coords.append(to_add)
                #mirror returns a list of coords
                coords += (gamelib.mirror(to_add))
                
        return coords
                
    def init_funnel(self):
        coords = [[],[]]
        for i in range(5):
            for j in range(5-i):
                to_add = [FUNNEL[0][0]-i ,FUNNEL[0][1]-j]
                coords[0].append(to_add)
                coords[1] += (gamelib.mirror(to_add))

        return coords


    def init_wall(self):
        coords = [[],[]]
        for i in range(4):
            for j in range(2):
                to_add = [GREATWALL[0][0]+i, GREATWALL[0][1]-j]
                coords[0].append(to_add)
                coords[1]+= (gamelib.mirror(to_add))
        
        return coords
    
    def init_entrance(self):
        coords = [[],[]]

        for i in range(5):
            to_add = [ENTRANCE[0][0]+i,ENTRANCE[0][1]-i]
            to_add2 = [to_add[0],to_add[1]+1]
            coords[0] += [to_add,to_add2]
            coords[1] += gamelib.mirror([to_add,to_add2])

        return coords
        
        

    def on_turn(self, turn_state):
        """
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True)  #Comment or remove this line to enable warnings.

        
        if game_state.turn_number <= 2:
            # initial set up
            self.starting_setup(game_state, game_state.turn_number)

        else:
            self.tower_defense_loop(game_state)
       

        game_state.submit_turn()


    '''
Our core strategy is to play tower defense. The two "paths" in our tower defense will be along the left 
and right sides of our map. We seek to funnel all enemy forces to these two paths. Our defenses will be in 3 particular spots. The two corners and the middle. The middle defenses is to mainly prevent enemy from taking advantage of breaking through the middle when pathing to the two funnels. 

We will hard code turns 0,1,2,3 
- 0. 4 walls for each funnel, 2 upgraded turrets for wall [6,12]. One will get a wall. Build factory. 2 3 interceptors
- 1. Fill up turret without wall. 3 3 interceptors
- 2. upgrade factory. 3 3 interceptors
- 3. two turrets+two walls, [11,9]. two walls, [13,8],  1 1 interceptor, 4 stack scout
- 4. start loop
    
    
    


Stats to track, region health absolute/%. 




Apart from maintaining defenses, our win condition is to get an economic lead and launch an all or nothing attack. To do this we need to have more factories (upgraded) than the enemy. These factories will be placed in the FARM. 

    '''




    # initial allocation of resources of start of game. Start with 30 SP and 5MP_points.
    # 4 WALL for each ENTRANCE, 1 TURRET (upgraded) on each FUNNEL , FACTORY in back
    # 4*2 + 6*2 + 9 + 1 = 30
    
    
    def starting_setup(self, game_state, turn ):


        ## Defense
        if turn == 0:
            wall_coords = [[0,13], [1,12], [2,11], [3,10] ]

            # for the other hole
            wall_coords = wall_coords[:3]
            
            wall_coords += gamelib.mirror(wall_coords)

            turret_coords = [[5,12]]
            turret_coords += gamelib.mirror(turret_coords)

            interceptor_coords = [[7,6]]
            
            
            interceptor_coords += gamelib.mirror(interceptor_coords)
            # should always succeed
            game_state.attempt_spawn(WALL,wall_coords)
            game_state.attempt_spawn(TURRET,turret_coords)
            game_state.attempt_upgrade(turret_coords)

            game_state.attempt_spawn(INTERCEPTOR, interceptor_coords,2)
            game_state.attempt_spawn(INTERCEPTOR, interceptor_coords[0], 1 )

            game_state.attempt_spawn(WALL, [turret_coords[0][0],turret_coords[0][1]+1])

            # for the turret in hole scenrario
            game_state.attempt_spawn(WALL, gamelib.mirror([turret_coords[0][0],turret_coords[0][1]+1]))
            
            self.add_factory(game_state, 9)

            # to update information
            # i need a function for left and right, that basically just updates its units 
            
            
            self.left.end_turn(game_state)
            self.right.end_turn(game_state)
        
        elif turn == 1:

            SP_points = game_state.get_resource(0,0)
            
            game_state.attempt_spawn(WALL,gamelib.mirror([5,13]))

            # possible sp after other wall 4- 9
            if SP_points == 4: 
                pass # wait for next sp
            elif SP_points == 9:
                self.add_factory(game_state, 9)
            else:
                # make sure i have 4 sp left. 
                can_spend = SP_points - 4
                # 5,6,7,8 - 4 = 1,2,3,4
                if can_spend == 1:
                    # add a wall
                    game_state.attempt_spawn(WALL,(13,8) )
                elif can_spend == 2:
                    # add 2 walls
                    game_state.attempt_spawn(WALL,(13,8) )
                    game_state.attempt_spawn(WALL , gamelib.mirror([13,8]) )

                else:
                    # add wall with turret
                    game_state.attempt_spawn(WALL,(13,8) )
                    game_state.attempt_spawn(TURRET,(13,7) )

                
            
            # interceptors. Have 6 MP_points now
            game_state.attempt_spawn(INTERCEPTOR, [7,6], 3)
            game_state.attempt_spawn(INTERCEPTOR, gamelib.mirror([7,6]), 3)

            # to update information
            self.left.end_turn(game_state)
            self.right.end_turn(game_state)

        elif turn == 2:
            SP_points = game_state.get_resource(0,0)

            if SP_points == 9:
                self.add_factory(game_state,9)
                game_state.attempt_spawn(INTERCEPTOR, [7,6], 3)
                game_state.attempt_spawn(INTERCEPTOR, gamelib.mirror([7,6]), 3)

                self.left.end_turn(game_state)
                self.right.end_turn(game_state)
            else:
                # less than
                self.tower_defense_loop(game_state)

                
        
    # need to figure out any "pre w"
    
    # manages all SP_points, MP_points usage

    # can activate final_form mode by checking in begingging
    def tower_defense_loop(self,game_state):
        #
        gamelib.debug_write("TURN :", game_state.turn_number, "Resources : ", game_state.get_resources(0))
      

        # basically unless otherwise specified then SP able to spend is this much
        
        SP_points = game_state.get_resource(0,0)
      
        MP_points = game_state.get_resource(1,0)

        # always run this first to update states and data vlaues
        self.left.update(game_state)
        self.right.update(game_state)

        # need to call prior to adding any new units. Otherwise inaccurate readings
        self.left.query_damage()
        self.right.query_damage()
        ld = self.left.total_damage(1)
        rd = self.left.total_damage(1)
 
        self.left.get_repairs()
        self.right.get_repairs()

       
        
        if SP_points >= self.left.get_repair_cost() + self.right.get_repair_cost():
            # can repair all
            for i in self.left.repair_queue + self.right.repair_queue:
                game_state.attempt_spawn(TURRET if i[1] == 0 else WALL, i[0])

            SP_points = game_state.get_resource(0,0)
            self.left.update_units(game_state)
            self.right.update_units(game_state)
            
            # now factory or reinforce. As of now its build as many factories

            # add logic later if needed
            self.add_factory(game_state, SP_points)


            SP_points = game_state.get_resource(0,0)
            self.reinforce(game_state, SP_points)
            

        else:
            # we are in deep trouble here
            # flip a coin

            # can change later 0 or 1, 
            repair_queue = gamelib.ticket_maker([[self.left.repair_queue, ld ],[self.right.repair_queue, rd]])

            for i in repair_queue:
                gamelib.debug_write("REPAIRING", i[0])
                if not game_state.attempt_spawn(TURRET if i[1] == 0 else WALL, i[0]):
                    break
                    
            

    
        SP_points = game_state.get_resource(0,0)

        # if turn is even, and we have less than 9 sp save fo
        # can i force SP to get save by manually removing SP points


        # now I made my repairs
        
        
        gamelib.debug_write("SP LEFT for farm",SP_points)


        #gamelib.debug_write(11,game_state.get_resource(0,0))
        #if game_state.turn_number == 3:
         #   quit()

        # can modify frequency here
        if game_state.turn_number % 2 == 0 and int(SP_points/9) < 1:
            game_state.to_save = 4
        else:
            game_state.to_save = 0
            
        self.add_factory(game_state, min(game_state.get_resource(0,0),2*9) )

        
        
        SP_points = game_state.get_allowance()
        gamelib.debug_write("allowance", SP_points)
        

        
        self.reinforce(game_state, SP_points)
        
        
        

        # MP_points allocation now........
        #offense or defense

        self.air_support(game_state)

        
        self.left.end_turn(game_state)
        self.right.end_turn(game_state)

        
        return False



    # add offensive manuevers
    # anti air manuever : launching interceptors
    # bomber manuever : this will need the other hole 
    # attack manuever
    
    def air_support(self,game_state):
        MP_points = int(game_state.get_resource(1,0))


        # can use 
        if MP_points >= 30:
            self.all_in(game_state,self.easier_side(game_state), MP_points)
        #elif MP_points >= 12 and random.randint(0,9) < 5:
         #   self.bb_middle(game_state, MP_points)
        else:
            self.aa_middle(game_state,MP_points)
      
        
    # anti air middle 
    def aa_middle(self,game_state,MP_points):
        startLeft = int(MP_points/2)
        startRight = MP_points - startLeft

        if 2 * 2 <= startLeft:
            game_state.attempt_spawn(INTERCEPTOR,LEFTHOME, 2)
            startLeft-=2
        if 2*2 <= startRight:
            game_state.attempt_spawn(INTERCEPTOR,RIGHTHOME,2)
            startRight-=2
        
        game_state.attempt_spawn(INTERCEPTOR, [7,6], startLeft)
        game_state.attempt_spawn(INTERCEPTOR, gamelib.mirror([7,6]), startRight)

    # bomber sweep
    def bb_middle(self, game_state,MP_points):
        # must contain stuff from 4,12 to 8,12 and mirrored to launch correctly
        total = int(MP_points/3)
        startLeft = int(total/2)
        startRight = total - startLeft
        game_state.attempt_spawn(DEMOLISHER, self.left.funnel.air_support_9_11, startLeft)
        game_state.attempt_spawn(DEMOLISHER, self.right.funnel.air_support_9_11, startRight)
        

    def all_in(self,game_state, side, MP_points):
        # if side == 0, attack left other wise attack right
        # bust thru whatever is blocking the funnel
        # need a way to determine combination of units

        
        # simple way
        game_state.attempt_spawn(SCOUT,RIGHTHOME if side else LEFTHOME, int(MP_points))
        

    # find easier side
    def easier_side(self,game_state):
        peak_region = [[4,11],[3,11],[3,12],[2,12],[2,13],[1,13]]
        
        return 1 if random.randint(0,1) == 1 else 0

        
   # how to determine what to reinforce
   # again would be useful to decide which side needs more
   # in general first decide if i need to reinforce middle left or right side.
   # Each reinforce will focus on one side.
   # since we are spending all on factories.
   # 1-8 possible spendings

   # reinforce
   # decides who to give the SP_points to
   
   # indivudal modules decides if to upgrade turret or to make new turret
   # upgrade turret -> turret + upgrade -> upgrade wall -> turret+wall. 
   # 
   # the goal of reinforce is to achieve final form.
   # final form is essentially that v wall wiht holes plucked
   #  
   
    def reinforce(self, game_state, SP_points):
        if SP_points == 0:
            return
        # current possible SP_points 0-8.
        # while loop, get ordering on place to apply reinforce, loop thru until no more SP_points

        # most damaged section
        # give sp to most damaged section
        # get all damaged sections and sort them
        left_sections = self.left.damage_taken
        right_sections = self.right.damage_taken


        # formula should take in as input absolute damage, relative damage, distance to FM, % to FM
        
        all_sections = list(left_sections.items())+list(right_sections.items())
        random.shuffle(all_sections)
        # second 1 idx uses absolute
        priority = sorted(all_sections, key = lambda x: -x[1][0])

        # try reinforce all
        for i in priority:
            i[0].reinforce(game_state, game_state.get_allowance())

        return

    
    # SP_points indicates the amount allocate for factories
    
    def add_factory(self, game_state, SP_points):
        # basically checks the farm. Again mirrors.
        upgradable, empty = self.examine_farm(game_state)
        # always upgrade before building new
        to_add = int(SP_points / 9)
        gamelib.debug_write("factory", to_add,upgradable,empty)
        game_state.attempt_upgrade(upgradable[:min(to_add, len(upgradable))])
        to_add -= min(to_add, len(upgradable))
        game_state.attempt_spawn(FACTORY, empty[:min(to_add, len(empty))])
        
        
        


    # returns two lists, existing farms to upgrade and empty spots for farm
    # order of items in list is order to plant a factory
    def examine_farm(self, game_state):
        upgradable = []
        empty = []
        for coord in self.farm:
            cur  = game_state.contains_stationary_unit(coord)
            if not cur:
                empty.append(coord)
            else:
                if not cur.upgraded:
                    upgradable.append(coord)
                    
        
        
        return [upgradable, empty]
           
    def farm_final_form_progress(self,game_state):
        return 



        

    
    
    def starter_strategy(self, game_state):
        """
        For defense we will use a spread out layout and some interceptors early on.
        We will place turrets near locations the opponent managed to score on.
        For offense we will use long range demolishers if they place stationary units near the enemy's front.
        If there are no stationary units to attack in the front, we will send Scouts to try and score quickly.
        """
        # First, place basic defenses
        self.build_defences(game_state)
        # Now build reactive defenses based on where the enemy scored
        self.build_reactive_defense(game_state)

        # If the turn is less than 5, stall with interceptors and wait to see enemy's base
        if game_state.turn_number < 5:
            self.stall_with_interceptors(game_state)
        else:
            # Now let's analyze the enemy base to see where their defenses are concentrated.
            # If they have many units in the front we can build a line for our demolishers to attack them at long range.
            if self.detect_enemy_unit(game_state, unit_type=None, valid_x=None, valid_y=[14, 15]) > 10:
                self.demolisher_line_strategy(game_state)
            else:
                # They don't have many units in the front so lets figure out their least defended area and send Scouts there.

                # Only spawn Scouts every other turn
                # Sending more at once is better since attacks can only hit a single scout at a time
                if game_state.turn_number % 2 == 1:
                    # To simplify we will just check sending them from back left and right
                    scout_spawn_location_options = [[13, 0], [14, 0]]
                    best_location = self.least_damage_spawn_location(game_state, scout_spawn_location_options)
                    game_state.attempt_spawn(SCOUT, best_location, 1000)

                # Lastly, if we have spare SP_points, let's build some Factories to generate more resources
                factory_locations = [[13, 2], [14, 2], [13, 3], [14, 3]]
                game_state.attempt_spawn(FACTORY, factory_locations)

    def build_defences(self, game_state):
        """
        Build basic defenses using hardcoded locations.
        Remember to defend corners and avoid placing units in the front where enemy demolishers can attack them.
        """
        # Useful tool for setting up your base locations: https://www.kevinbai.design/terminal-map-maker
        # More community tools available at: https://terminal.c1games.com/rules#Download

        # Place turrets that attack enemy units
        turret_locations = [[0, 13], [27, 13], [8, 11], [19, 11], [13, 11], [14, 11]]
        # attempt_spawn will try to spawn units if we have resources, and will check if a blocking unit is already there
        game_state.attempt_spawn(TURRET, turret_locations)
        
        # Place walls in front of turrets to soak up damage for them
        wall_locations = [[8, 12], [19, 12]]
        game_state.attempt_spawn(WALL, wall_locations)
        # upgrade walls so they soak more damage
        game_state.attempt_upgrade(wall_locations)

    def build_reactive_defense(self, game_state):
        """
        This function builds reactive defenses based on where the enemy scored on us from.
        We can track where the opponent scored by looking at events in action frames 
        as shown in the on_action_frame function
        """
        for location in self.scored_on_locations:
            # Build turret one space above so that it doesn't block our own edge spawn locations
            build_location = [location[0], location[1]+1]
            game_state.attempt_spawn(TURRET, build_location)

    def stall_with_interceptors(self, game_state):
        """
        Send out interceptors at random locations to defend our base from enemy moving units.
        """
        # We can spawn moving units on our edges so a list of all our edge locations
        friendly_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
        
        # Remove locations that are blocked by our own structures 
        # since we can't deploy units there.
        deploy_locations = self.filter_blocked_locations(friendly_edges, game_state)
        
        # While we have remaining MP_points to spend lets send out interceptors randomly.
        while game_state.get_resource(MP_points) >= game_state.type_cost(INTERCEPTOR)[MP_points] and len(deploy_locations) > 0:
            # Choose a random deploy location.
            deploy_index = random.randint(0, len(deploy_locations) - 1)
            deploy_location = deploy_locations[deploy_index]
            
            game_state.attempt_spawn(INTERCEPTOR, deploy_location)
            """
            We don't have to remove the location since multiple mobile 
            units can occupy the same space.
            """

    def demolisher_line_strategy(self, game_state):
        """
        Build a line of the cheapest stationary unit so our demolisher can attack from long range.
        """
        # First let's figure out the cheapest unit
        # We could just check the game rules, but this demonstrates how to use the GameUnit class
        stationary_units = [WALL, TURRET, FACTORY]
        cheapest_unit = WALL
        for unit in stationary_units:
            unit_class = gamelib.GameUnit(unit, game_state.config)
            if unit_class.cost[game_state.MP_points] < gamelib.GameUnit(cheapest_unit, game_state.config).cost[game_state.MP_points]:
                cheapest_unit = unit

        # Now let's build out a line of stationary units. This will prevent our demolisher from running into the enemy base.
        # Instead they will stay at the perfect distance to attack the front two rows of the enemy base.
        for x in range(27, 5, -1):
            game_state.attempt_spawn(cheapest_unit, [x, 11])

        # Now spawn demolishers next to the line
        # By asking attempt_spawn to spawn 1000 units, it will essentially spawn as many as we have resources for
        game_state.attempt_spawn(DEMOLISHER, [24, 10], 1000)

    def least_damage_spawn_location(self, game_state, location_options):
        """
        This function will help us guess which location is the safest to spawn moving units from.
        It gets the path the unit will take then checks locations on that path to 
        estimate the path's damage risk.
        """
        damages = []
        # Get the damage estimate each path will take
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            damage = 0
            for path_location in path:
                # Get number of enemy turrets that can attack each location and multiply by turret damage
                damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(TURRET, game_state.config).damage_i
            damages.append(damage)
        
        # Now just return the location that takes the least damage
        return location_options[damages.index(min(damages))]

    def detect_enemy_unit(self, game_state, unit_type=None, valid_x = None, valid_y = None):
        total_units = 0
        for location in game_state.game_map:
            if game_state.contains_stationary_unit(location):
                for unit in game_state.game_map[location]:
                    if unit.player_index == 1 and (unit_type is None or unit.unit_type == unit_type) and (valid_x is None or location[0] in valid_x) and (valid_y is None or location[1] in valid_y):
                        total_units += 1
        return total_units
        
    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered

    def on_action_frame(self, turn_string):
        """
        This is the action frame of the game. This function could be called 
        hundreds of times per turn and could slow the algo down so avoid putting slow code here.
        Processing the action frames is complicated so we only suggest it if you have time and experience.
        Full doc on format of a game frame at in json-docs.html in the root of the Starterkit.
        """
        # Let's record at what position we get scored on
        state = json.loads(turn_string)
        events = state["events"]
        breaches = events["breach"]
        for breach in breaches:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            # When parsing the frame data directly, 
            # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
            if not unit_owner_self:
                gamelib.debug_write("Got scored on at: {}".format(location))
                self.scored_on_locations.append(location)
                gamelib.debug_write("All locations: {}".format(self.scored_on_locations))


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
