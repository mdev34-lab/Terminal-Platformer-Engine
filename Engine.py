import time
import threading
from dataclasses import dataclass
from lib.terminal_graphics import Terminal, ScreenData, Coords
from lib.sprites import Sprites
from lib.parameters import MagicNumbers
import keyboard

class Ground():
    def __init__(self, screen: ScreenData, width: int, pos: Coords):
        super().__init__() # I don't know why this is here, but it's behavior looks good to me
        self.width = width
        self.pos = pos
        self.xpos = pos.xpos # xpos short for X position
        self.ypos = pos.ypos # ypos short for Y position
        self.screen = screen

    def place_ground(self, xpos: int, ypos: int):
        """Place a ground block in each coordinate.

        Args:
            xpos (int): The x position of the ground block.
            ypos (int): The y position of the ground block.
        
        Returns:
            None"""
        # Place a ground block in each coordinate, reads as the following:
        # For each number in the range of the width:                        <--+
        #   Place a ground block in coordnates:                                | number
        #       X = Ground's root x position + the number from the for loop ---+
        for number in range(self.width):
            Terminal.place_sprite(
                self.screen,
                Sprites.GROUND_SPRITE,
                Coords(xpos + number, ypos)
            )
    
    def get_collision_coords(self):
        """
        Get the coordinates for collision detection with the ground.
        
        Returns:
            List[Coords]: A list of coordinates representing the ground.
        """
        # Initialize an empty list to hold the collision coordinates
        collision_coords = []
        
        # Iterate over the range of the width
        for number in range(self.width):
            # Calculate the x coordinate for each number and add it to the list
            # The x coordinate is the ground's root x position plus the number
            collision_coords.append(Coords(self.xpos + number, self.ypos))
        
        # Return the list of collision coordinates
        return collision_coords
    
    def render(self):
        # Place ground tiles on the screen
        self.place_ground(self.xpos, self.ypos)
        collision_coords = self.get_collision_coords()
        
        return self.screen, collision_coords

# Please note that refactoring the other classes to inherit from another thing may be
# bad for the program length, despite doing the exact same thing.
class Coin(): # Also known as the Mother of All Objects
    def __init__(self, screen: ScreenData, pos: Coords):
        # Initialize the position of the coin
        self.pos = pos
        # Initialize the position of the coin one row above the current position
        self.secondary_pos = Coords(pos.xpos, pos.ypos - 1)
        # Initialize the screen to render the coin on
        self.screen = screen
        # Initialize a flag to indicate if the coin is hidden
        self.hide = False
        # Initialize a flag to indicate if the coin has been broken
        self.broken = False
        # Initialize a flag to indicate if the coin has been updated
        self.updated = False
        # Initialize a flag to indicate if the coin has been killed
        self.killed = False

    def hide_coin(self): self.hide = True
    # R.I.P __del__() dunder method, didn't even get used in the 1st place

    def render(self, previous_pos: Coords = None):
        # Determine the sprite to render based on the hide flag
        sprite_to_render = Sprites.COIN_SPRITE if not self.hide else ' '
        # Place the sprite on the screen at the current position
        Terminal.place_sprite(self.screen, sprite_to_render, self.pos)
        # Return the updated screen data
        return self.screen

class Powerup(Coin):
    def render(self, previous_pos: Coords = None):
        # Determine the sprite to render based on the hide flag
        if self.hide: sprite_to_render = Sprites.HIT_POWERUP_BLOCK_SPRITE # Hide block has been hit
        else: sprite_to_render = Sprites.POWERUP_BLOCK_SPRITE # Hide block has not been hit
        # If hide flag is in an unknown state
        if sprite_to_render is None: sprite_to_render = Sprites.UNKNOWN_BLOCK_SPRITE # This should never happen but just in case
        
        # Render the sprite on the screen at the current position
        Terminal.place_sprite(self.screen, sprite_to_render, self.pos)
        # Return the updated screen data
        return self.screen
    
class StompableEnemy(Coin):
    def __init__(self, screen: ScreenData, pos: Coords):
        # Call the __init__ method of the parent class (Coin)
        # Pass in the screen and position arguments
        super().__init__(screen, pos)
        # Set the killed flag to False
        self.killed = False
        
        # Create a tuple of Coords objects representing the enemy's sides
        # These Coords objects are one space to the left and right of the enemy's current position
        
        # Create a Coords object representing the enemy's secondary position
        # This is the enemy's position one row above its current position
        self.secondary_pos = Coords(pos.xpos, pos.ypos - 1)
        
        # Store the previous position of the enemy
        self.previous_pos = pos

    def move_towards_player(self, player_pos: Coords):
        if self.killed: return  # Do not move if the enemy is killed

        new_xpos = self.calculate_new_xpos(player_pos) # Calculate the new position of the enemy
        new_ypos = self.pos.ypos

        self.previous_pos = self.pos
        self.pos = Coords(new_xpos, new_ypos)
        self.sidepos = self.get_side_positions(self.pos)
        self.secondary_pos = Coords(new_xpos, new_ypos - 1)
    
    def render(self):
        # Determine the sprite to render based on the hide/kill flags
        sprite_to_use = Sprites.ENEMY1_SPRITE if (not self.hide) or (not self.killed) else ' '

        # Render the enemy on the screen at its current position
        Terminal.place_sprite(self.screen, sprite_to_use, self.pos)
        
        # If the enemy has moved to a new position, clear its previous position
        if self.previous_pos != self.pos:
            Terminal.place_sprite(self.screen, ' ', self.previous_pos)
        # If the enemy is hidden or killed, clear its current position
        if self.hide or self.killed: Terminal.place_sprite(self.screen, ' ', self.pos)
                
        # Return the updated screen data
        return self.screen
    
    def get_side_positions(self, pos: Coords):
        sidepos = (
            Coords(pos.xpos - 1, pos.ypos),  # Left side
            Coords(pos.xpos + 1, pos.ypos),  # Right side
        )
        return sidepos
    
    def calculate_new_xpos(self, player_pos: Coords):
        # Calculate the new position of the enemy
        # If the enemy is on the left side of the player, move it to the right
        # If the enemy is on the right side of the player, move it to the left
        # If the enemy is already at the player's position, keep its position
        new_xpos = self.pos.xpos
        if self.pos.xpos < player_pos.xpos:
            new_xpos += 1
        elif self.pos.xpos > player_pos.xpos:
            new_xpos -= 1
        return new_xpos
    
class Fireball(Coin):
    def __init__(self, screen: ScreenData, pos: Coords, direction: int, enemies: tuple[StompableEnemy]):
        # Initialize the Fireball object with the necessary parameters
        super().__init__(screen, pos)
        # Store the direction of the fireball
        self.direction = direction 
        # Set the hit flag to False
        self.hit = False
        # Initialize old position as None
        self.old_pos = None 
        # Store the enemies that the fireball can collide with
        self.enemies = enemies

    def render(self, previous_pos: Coords = None):
        # Render the fireball on the screen at its current position
        Terminal.place_sprite(self.screen, Sprites.FIREBALL_RIGHT_SPRITE if self.direction == 1 else Sprites.FIREBALL_LEFT_SPRITE, self.pos)
        
        # If the fireball has hit something, clear its position
        if self.hit: Terminal.place_sprite(self.screen, ' ', self.pos)

        # If the fireball has moved to a new position, clear its previous position
        elif self.old_pos and self.pos != self.old_pos:
            Terminal.place_sprite(self.screen, ' ', self.old_pos)
            Terminal.place_sprite(self.screen, Sprites.FIREBALL_RIGHT_SPRITE if self.direction == 1 else Sprites.FIREBALL_LEFT_SPRITE, self.pos)

        # If the fireball is at its old position, clear its position
        elif self.pos == self.old_pos:
            Terminal.place_sprite(self.screen, ' ', self.pos)

        # If the fireball is at the edge of the screen, clear its position
        if self.pos.xpos == 0:
            Terminal.place_sprite(self.screen, ' ', self.pos)
        if self.pos.xpos == (MagicNumbers.GROUND_WIDTH - 1):
            Terminal.place_sprite(self.screen, ' ', self.pos)

        # Check for collisions with enemies
        for enemy in self.enemies:
            for pos in enemy.sidepos:
                if (pos == self.pos) and (not enemy.killed):
                    self.hit = True
                    enemy.killed = True
                    Terminal.place_sprite(self.screen, ' ', enemy.pos)
                    Terminal.place_sprite(self.screen, ' ', pos)
        
        new_screen = {Coords(5, 1): f'Last fireball position: {self.pos.xpos}, {self.pos.ypos}'}
        self.screen.update(new_screen)
        return self.screen

    def next_pos(self):
        new_xpos = self.pos.xpos + self.direction  # Move the fireball based on its direction
        new_ypos = self.pos.ypos

        # Store the old position before updating to the new position
        self.old_pos = self.pos

        self.pos = Coords(new_xpos, new_ypos)  # Create a new Coords instance with the updated position
        self.secondary_pos = Coords(new_xpos, new_ypos - 1)  # Update secondary position accordingly

        return self.ground_border_collision_check()
    
    def ground_border_collision_check(self):
        if self.pos.xpos >= (MagicNumbers.GROUND_WIDTH) or self.pos.xpos < 0:
            self.screen[self.old_pos] = ' '  # Clear the character on the old position
            return True  # Indicate collision with ground border
        return False

class Brick(Coin):
    def render(self, previous_pos: Coords = None):
        """
        Render the brick on the screen at its current position.
        """
        # If the brick is not hidden, render it
        if not self.hide:
            Terminal.place_sprite(self.screen, Sprites.BRICK_SPRITE, self.pos)
        # If the brick is hidden or broken, clear its position
        elif self.hide or self.broken:
            # If the brick has not been updated yet, clear its position
            if not self.updated:
                Terminal.place_sprite(self.screen, ' ', self.pos)
                self.updated = True
        # Return the updated screen data
        return self.screen

class Player():
    def __init__(
            self, 
            screen: ScreenData, 
            pos: Coords, 
            ground: Ground, 
            powerups: tuple[Powerup], 
            fireballs: list[Fireball],
            bricks: tuple[Brick],
            enemies: tuple[StompableEnemy], 
        ):
        self.pos = pos
        self.velocity_y = 0
        self.screen = screen
        self.ground = ground
        self.grounded = False
        self.ground_coords = ground.render()[1]
        self.powerups = powerups
        self.fireballs = fireballs
        self.bricks = bricks
        self.enemies = enemies  
        self.direction = Player.Right

        self.power_coords, self.brick_coords, self.enemy_coords = [], [], [] 
        for powerup in self.powerups: self.power_coords.append(powerup.pos)
        for brick in self.bricks: self.brick_coords.append(brick.pos)
        for enemy in self.enemies: self.enemy_coords.append(enemy.pos)  

        self.coins_collected: int = 0
        self.powerstate = MagicNumbers.STARTING_POWERSTATE
        self.fire_cooldown = 0

    class Left: pass
    class Right: pass
    class GameOverException(Exception): pass
    
    def apply_gravity(self):
        if not self.grounded:
            if self.velocity_y < 1:  
                self.velocity_y += 1
    
    def jump(self):
        if self.grounded:
            self.velocity_y = -3  
            self.grounded = False
    
    def move(self, dx: int):
        if dx < 0: self.direction = Player.Left
        elif dx > 0: self.direction = Player.Right
        new_xpos = self.pos.xpos + dx
        if new_xpos < 0:
            new_xpos = 0
        self.pos = Coords(new_xpos, self.pos.ypos)

    def shoot(self):
        if (self.fire_cooldown == 0) and self.powerstate == 2:
            direction = 1 if self.direction == Player.Right else -1  
            new_fireball = Fireball(self.screen, Coords(self.pos.xpos + direction, self.pos.ypos), direction, self.enemies)
            self.fireballs.append(new_fireball)
            self.fire_cooldown = 0
    
    def update_fireballs(self, coins: tuple[Coin]):
        for fireball in self.fireballs[:]:  
            collided = fireball.next_pos()
            if collided:  
                fireball.hit = True
                self.fireballs.remove(fireball)  
            else:
                for coin in coins:
                    if fireball.pos == coin.pos and not coin.hide:
                        coin.hide_coin()
                        self.coins_collected += 1
                        self.fireballs.remove(fireball)  
                        break  

                for enemy in self.enemies:
                    if fireball.pos == enemy.pos and not enemy.killed:
                        enemy.killed = True
                        self.screen[enemy.pos] = ' '
                        self.screen[enemy.sidepos[0]] = ' '
                        enemy.hide_coin()
                        self.fireballs.remove(fireball)  
                        break  
    
    def update_position(self):
        new_ypos = self.pos.ypos + self.velocity_y

        ground_collision = Coords(self.pos.xpos, new_ypos) in self.ground_coords
        powerup_collision = Coords(self.pos.xpos, new_ypos) in self.power_coords
        brick_collision = Coords(self.pos.xpos, new_ypos) in self.brick_coords

        if powerup_collision:
            for id, powcoord in enumerate(self.power_coords):
                if powcoord == Coords(self.pos.xpos, new_ypos):
                    new_ypos = self.pos.ypos + 1
                    self.velocity_y = 0
                    if (not self.powerups[id].hide) and (self.powerstate < 2):
                        self.powerstate += 1
                    self.powerups[id].hide_coin()
        elif brick_collision:
            for id, brkcoord in enumerate(self.brick_coords):
                if brkcoord == Coords(self.pos.xpos, new_ypos):
                    if not self.bricks[id].broken:
                        new_ypos = self.pos.ypos + 1
                        self.velocity_y = 0
                    if self.powerstate >= 1:
                        self.bricks[id].hide_coin()
                        self.bricks[id].broken = True
        elif ground_collision:
            new_ypos = self.ground.pos.ypos - 1
            self.velocity_y = 0
            self.grounded = True
        
        else:
            self.grounded = False

        if self.powerstate == -1:
            raise Player.GameOverException
        
        self.pos = Coords(self.pos.xpos, new_ypos)
    
    def render(self, previous_pos: Coords):
        if previous_pos and previous_pos != self.pos:
            self.screen[previous_pos] = ' '

        if self.powerstate == 0: sprite = Sprites.NORMAL_PLAYER_SPRITE
        elif self.powerstate == 1: sprite = Sprites.SUPER_PLAYER_SPRITE
        elif self.powerstate == 2: sprite = Sprites.FIREBALL_PLAYER_SPRITE
        else: sprite = 'P'
        new_screen: ScreenData = {
            self.pos: sprite,  
            Coords(0, 0): str(self.coins_collected),
            Coords(0, 1): str(self.powerstate),
            Coords(0, 2): 'Left ' if self.direction == Player.Left else 'Right',
            Coords(5, 0): f"X Position: {self.pos.xpos}, Line: {self.pos.ypos}",
        }
        self.screen.update(new_screen)
        return self.screen
    
    def coin_check(self, coins: tuple[Coin], powerups: tuple[Powerup]):
        for coin in coins:
            if (self.pos == coin.pos) and not coin.hide:
                self.coins_collected += 1
                coin.hide_coin()
            else:
                continue
    
    def enemy_check(self, enemies: tuple[StompableEnemy]):
        for enemy in enemies:
            if (self.pos == enemy.secondary_pos) and (not enemy.killed):
                enemy.killed = True
                enemy.hide_coin()
                self.velocity_y = -3  
                self.grounded = False  

            if (self.pos == enemy.pos) and not enemy.killed:
                if not self.powerstate == 0:
                    self.pos = Coords(self.pos.xpos - 4 if (self.direction == Player.Right) else 4, self.pos.ypos)
                self.powerstate -= 1 if self.powerstate >= -1 else 0
                self.screen.update({enemy.pos: Sprites.ENEMY1_SPRITE})
            else:
                continue

def main():
    screen: ScreenData = {}

    level_ground = Ground(screen, MagicNumbers.GROUND_WIDTH, Coords(0, 10))
    screen.update(level_ground.render()[0])

    coins: tuple = (
        Coin(screen, Coords(10, 7)),
        Coin(screen, Coords(15, 7)),
    )
    powerups: tuple = (
        Powerup(screen, Coords(20, 6)),
        Powerup(screen, Coords(24, 6)),
    )
    bricks: tuple = (
        Brick(screen, Coords(30, 6)),
        Brick(screen, Coords(19, 6)),
        Brick(screen, Coords(21, 6)),
        Brick(screen, Coords(22, 6)),
        Brick(screen, Coords(23, 6)),
        Brick(screen, Coords(25, 6)),
    )
    enemies = (
        StompableEnemy(screen, Coords(35, 9)),
    )
    fireballs: list[Fireball] = []

    player = Player(screen, Coords(10, 2), level_ground, powerups, fireballs, bricks, enemies)
    previous_pos = player.pos

    Terminal.clear()
    Terminal.hide_cursor()
    stop_thread = False

    def input_thread():
        DELAY = 0.025

        nonlocal stop_thread
        while not stop_thread:
            if keyboard.is_pressed('a'):
                player.move(-1)
                time.sleep(DELAY)
            if keyboard.is_pressed('d'):
                player.move(1)
                time.sleep(DELAY)
            if keyboard.is_pressed('space'):
                player.jump()
                time.sleep(DELAY)
            if keyboard.is_pressed('f'):
                player.shoot()
                time.sleep(DELAY)
            if keyboard.is_pressed('q'):
                stop_thread = True
            time.sleep(0.05)

    thread = threading.Thread(target=input_thread)
    thread.start()

    try:
        while not stop_thread:
            player.coin_check(coins, powerups)
            player.apply_gravity()
            player.update_position()
            player.update_fireballs(coins)
            player.enemy_check(enemies)

            # Move enemies towards the player
            for enemy in enemies:
                enemy.move_towards_player(player.pos)

            # Render all objects
            screen.clear()
            level_ground.render()
            for coin in coins:
                coin.render()
            for powerup in powerups:
                powerup.render()
            for brick in bricks:
                brick.render()
            for enemy in enemies:
                enemy.render()
            for fireball in fireballs:
                fireball.render()
            player.render(previous_pos)

            previous_pos = player.pos
            Terminal.update_screen(screen)
            time.sleep(0.1)
    finally:
        stop_thread = True
        thread.join()

if __name__ == '__main__':
    try:
        main()
    except Player.GameOverException:
        Terminal.clear()
        Terminal.show_cursor()
        Terminal.move_cursor(0, 0)
        print("Game Over! See you again later!")
        exit()
    except KeyboardInterrupt:
        Terminal.clear()
        Terminal.show_cursor()
        Terminal.move_cursor(0, 0)
        print("Thanks for playing!")
        exit()
