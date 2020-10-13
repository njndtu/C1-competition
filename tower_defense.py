# declares the various parts of our defense in forms of classes
import gamelib
import random

class DefenseStructures():
    global HOLE, HOLE2
    HOLE = [11,9]  # this whole is for interceptors to get to middle
    HOLE2 = [9,11] # need a hole for demolishers to do a sweep
    HOLE2 = HOLE # ignore HOLE 2 for now
    
    
    def __init__(self,coords,mirror = False):
        self.region = [tuple(coord) for coord in coords] # will store coords the DS will be able to modify
        self.units = dict() # maps each coord in region to copy of unit
        for coord in self.region:
            self.units[coord] = False
        
        self.old_abs_HP = 0
        self.cur_abs_HP = 0

        self.mirror = mirror # if True then is on the right side

        # gives coord and action. 0 = turret, 1 upgrade turret, 2 wall, 3 upgrade wall
        self.priorities = []

        # cost to replace previously destoryed items
        self.repair_cost = 0

        self.to_repair = []
        
        # stuff to reinforce
        
        self.to_reinforce = []

        
        self.final_form = False



    # updates units information. Updates cur_abs_HP. Need to upgrade old_abs_HP end of turn via calling end turn. Also newly added units in this turn are not yet included. Call this in the beggining of turn 
    def update(self,game_state):
        self.repair_cost = 0
        self.to_repair = []
        
        for coord in self.region:
            self.update_unit(coord, game_state.contains_stationary_unit(coord) )

        # sort to_repair by putting walls first
        sorted(self.to_repair,key = lambda x:-x[1])

    def end_turn(self,game_state):
        self.update_units(game_state)
        self.old_abs_HP = self.cur_abs_HP
            

    # updates general health. updates repair cost, add repair units
    def update_unit(self,coord, new_info):

        if not new_info:
            # nothing here anymore
            
            if not self.units[coord]:
                # nothing was here prior, so nothing should be here anyways
                pass
            else:
                # destroyed
                self.cur_abs_HP -= self.units[coord].health
                self.repair_cost += self.units[coord].cost[0]
                # 0 for turrets 1 for walls
                # (coords, (0/1))
                self.to_repair.append([coord, 0 if self.units[coord].max_health in [100,200] else 1] )
                
        else:
            if not self.units[coord]:
                # added new unit, this should neve rhappen
                a = 1
                
            # complete fine or damaged 
            else:
                self.cur_abs_HP -= (self.units[coord].health - new_info.health)
                self.units[coord] = new_info
            
    # checks regions, call this after spawning structures. 
    
    def update_units(self,game_state):
        for coord in self.region:
            new_info = game_state.contains_stationary_unit(coord)
            if new_info:
                # somethings here
                if not self.units[coord]:
                    # something wasnt here before
                    self.cur_abs_HP += new_info.health
                else:
                    # upgraded   
                     self.cur_abs_HP += abs(self.units[coord].health - new_info.health)

                self.units[coord] = new_info

                
    # returns absolute health, and percent health lost
    def damage_taken(self):
        return [self.old_abs_HP - self.cur_abs_HP , (self.old_abs_HP - self.cur_abs_HP) / (self.old_abs_HP) if self.old_abs_HP > 0 else 0  ]


    
    # implement logic for creating new things. .... hard code it

    

# the length 4 walls
# [5,12] upgraded is the one we begin with
# reinforce options. 

class Wall(DefenseStructures):
    # End goal : Entire wall is lined with upgraded turret and upgraded walls

    def __init__(self, coords, mirror=False):
        super().__init__(coords, mirror)

        # slots that should and can have turrets
        self.turret_slots = [[5+i,12] for i in range(4)] # whenever building new turret append to this. Order of uprading turret is decided in this order too
        if mirror:
            self.turret_slots = gamelib.mirror(self.turret_slots)



            
    # what to add to get to FM
    def reinforce(self, game_state, SP_points):
            
        # upgrade turret -> upgrade wall -> turret + wall
        random.shuffle(self.turret_slots)

        for i in self.turret_slots:
            
            empty_wall = True
            wall_upgradable = False
            wall =  game_state.contains_stationary_unit([i[0],i[1]+1])
            if wall:
                empty_wall = False
                wall_upgradable = not wall.upgraded

                
            empty_turret = True
            turret_upgradable = False
            turret = game_state.contains_stationary_unit(i)

            if turret:
                empty_turret = False
                turret_upgradable = not turret.upgraded

            if turret_upgradable and SP_points >= 4:
                game_state.attempt_upgrade(i)

            SP_points = game_state.get_allowance()

            if wall_upgradable and SP_points >= 2:
                game_state.attempt_upgrade([i[0],i[1]+1])

            SP_points = game_state.get_allowance()

            if empty_turret and empty_wall and SP_points >= 3:
                game_state.attempt_spawn(WALL,[i[0],i[1]+1])
                game_state.attempt_spawn(TURRET, i)
            
            SP_points = game_state.get_allowance()

            
    def check_final_form(self):
        return False


# the "5" length turret. " " because it is slanted down to the middle
# turret priority [9,11], [12,8], [10,10],[13,7]

# [11,9] is the hole. Hole gets plucked once attack coordination occurs
# attack mode is when we pluck this hole. 

# when building turrets, will always accompany a wall in front. So 3 total. turret+wall+upgrade is priority


class Entrance(DefenseStructures):
    # End goal : All turrets upgraded along with walls. Minus the hole

    def __init__(self, coords, mirror=False):
        super().__init__(coords, mirror)

          # slots that should and can have turrets
        self.turret_slots = [[9+i,11-i] for i in range(5)] # whenever building new turret append to this. Order of uprading turret is decided in this order too
        if mirror:
            self.turret_slots = gamelib.mirror(self.turret_slots)

# what to add to get to FM
    def reinforce(self, game_state, SP_points):
        # upgrade turret -> upgrade wall -> turret + wall
        random.shuffle(self.turret_slots)

        for i in self.turret_slots:
            if not self.final_form and i in [HOLE, gamelib.mirror(HOLE)[0]]:
                continue
            empty_wall = True
            wall_upgradable = False
            wall =  game_state.contains_stationary_unit([i[0],i[1]+1])
            if wall:
                empty_wall = False
                wall_upgradable = not wall.upgraded

                
            empty_turret = True
            turret_upgradable = False
            turret = game_state.contains_stationary_unit(i)

            if turret:
                empty_turret = False
                turret_upgradable = not turret.upgraded

            if turret_upgradable and SP_points >= 4:
                game_state.attempt_upgrade(i)

            SP_points = game_state.get_allowance()

            if wall_upgradable and SP_points >= 2:
                game_state.attempt_upgrade([i[0],i[1]+1])

            SP_points = game_state.get_allowance()

            if empty_turret and empty_wall and SP_points >= 3:
                game_state.attempt_spawn(WALL,[i[0],i[1]+1])
                game_state.attempt_spawn(TURRET, i)
            
            SP_points = game_state.get_allowance()
            
    def check_final_form(self):
        return False
            
# funnel

class Funnel(DefenseStructures):
    # End goal: All walls upgraded, with both possible turret spots spawned and them upgraded

    def __init__(self, coords, mirror=False):
        super().__init__(coords, mirror)
        self.turret_slots = [[4,12],[3,10]]
        self.air_support_9_11 = [3,10]
        

        # wall length
        WALL_LENGTH = 3
        # 3: should leave 3 10 open for divebomb
        
        
        self.wall_vip = [[0+i,13-i] for i in range(WALL_LENGTH)]
        self.optional_wall = [3,13]

        if self.mirror:
            self.turret_slots = gamelib.mirror(self.turret_slots)
            self.wall_vip = gamelib.mirror(self.wall_vip)
            self.optional_wall = gamelib.mirror(self.optional_wall)[0]
            self.air_support_9_11 = gamelib.mirror(self.air_support_9_11)[0]


# fix this part 
    def reinforce(self,game_state, SP_points):
        # for the funnel
        # always upgrade walls , if top 2 walls is upgraded, then try to add helper turret + wall
        
        # stuff should always be rebuilt
        for i in self.wall_vip[:3]:
            wall = game_state.contains_stationary_unit(i)
            if not wall and game_state.get_allowance() >= 1:
                game_state.attempt_spawn(WALL, i)
            
            if wall and not wall.upgraded and game_state.get_allowance() >= 2:
                game_state.attempt_upgrade(i)

        # add turret and or wall

        turret1 = game_state.contains_stationary_unit(self.turret_slots[0])

        if not turret1:
            # turret isnt here
            # check if wall absent
            turret1 = [self.turret_slots[0][0], self.turret_slots[0][1]]
            wall = game_state.contains_stationary_unit(turret1)
            if wall:
                # there is wall
                wall_upgradable = not wall.upgraded
                
                if game_state.get_allowance() and wall_upgradable >= 6+2 :
                    # turret + upgrade
                    game_state.attempt_spawn(TURRET, [turret1[0], turret1[1]])
                    game_state.attempt_upgrade([turret1[0],turret1[1]])
                    game_State.attempt_upgrade([wall.x,wall.y])
                
                elif game_state.get_allowance() >= 6 :
                    # turret + upgrade
                    game_state.attempt_spawn(TURRET, [turret1[0], turret1[1]])
                    game_state.attempt_upgrade([turret1[0],turret1[1]])
                elif game_state.get_allowance() >= 2+2:
                    game_state.attempt_spawn(TURRET,[turret1[0],turret1[1] ])
                    game_state.attempt_upgrade([wall.x,wall.y])
                    
                elif game_state.get_allowance() >=  2:
                    # turret
                    game_state.attempt_spawn(TURRET, [turret1[0], turret1[1]])
                    
            else:
                 # no wall   
                if game_state.get_allowance() >= 6+1:
                    # wall + upgraded turret
                    game_state.attempt_spawn(TURRET,[turret1[0],turret1[1]])
                    game_state.attempt_upgrade([turret1[0],turret1[1]])
                    game_state.attempt_spawn(WALL, [turret1[0],turret1[1]+1])

                elif game_state.get_allowance() >=  2+1:
                    # wall+turret
                    game_state.attempt_spawn(TURRET,[turret1[0],turret1[1]])
                    game_state.attempt_spawn(WALL, [turret1[0],turret1[1]+1])
        else:
            #try to upgrade turret, turret is here            
            if not turret1.upgraded and game_state.get_allowance() >= 4:
                game_state.attempt_upgrade([turret1.x,turret1.y])
                    
        # optional wall
        wall = game_state.contains_stationary_unit(self.optional_wall)

        if not wall:
            # no wall
            if game_state.get_allowance() >= 2:
                game_state.attempt_spawn(WALL,self.optional_wall)
                game_state.attempt_upgrade(self.optional_wall)
            elif game_state.get_allowance() >= 1:
                game_state.attempt_spawn(WALL, self.optional_wall)
        else:
            if not wall.upgraded and game_state.get_allowance() >= 2:
                game_state.attempt_upgrade(self.optional_wall)
                       

class SideDefense():


    def __init__(self,wall,entrance,funnel,config):
        self.wall = wall
        self.entrance = entrance
        self.funnel = funnel
        # these store the things

        # if trying to repair go here
        self.repair_queue = []
        self.damage_taken = dict()

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

    # need a function to let know DS's know newly added structures. end_turn will call this

    def update_units(self,game_state):
        self.wall.update_units(game_state)
        self.entrance.update_units(game_state)
        self.funnel.update_units(game_state)
        
    def update(self,game_state):
        self.wall.update(game_state)
        self.entrance.update(game_state)
        self.funnel.update(game_state)

        

    def end_turn(self, game_state):
        self.wall.end_turn( game_state)
        self.entrance.end_turn(game_state)
        self.funnel.end_turn(game_state)

    def get_repair_cost(self):
        # gets total cost of repairs
        return self.wall.repair_cost + self.entrance.repair_cost + self.funnel.repair_cost 

    # can only call once
    def query_damage(self,i = 1):
        self.damage_taken = dict()
        stuff = [self.wall,self.entrance,self.funnel]
        for i in stuff:
            self.damage_taken[i] = i.damage_taken()

   
    # can implement strat for tearing down almost destroyed stuff. 
    
    # makes a queue for repairs
    def get_repairs(self):
       # gamelib.debug_write(self.damage_taken)
        wall_delta = self.damage_taken[self.wall][1]
        entrance_delta = self.damage_taken[self.entrance][1]
        funnel_delta = self.damage_taken[self.funnel][1]

        
        # wall, entrance and funnel will all output a list of repairs that could be made

        w = self.wall.to_repair
        e = self.entrance.to_repair
        f = self.funnel.to_repair

        self.repair_queue = []
        
        repair_queue = [[w,wall_delta] ,[e, entrance_delta],[f,funnel_delta]]
        self.repair_queue = gamelib.ticket_maker(repair_queue)
        
            

    def total_damage(self,i):
        return self.damage_taken[self.wall][i]+self.damage_taken[self.entrance][i]+self.damage_taken[self.funnel][i]
            
