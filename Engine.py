import time
import threading
from dataclasses import dataclass
from lib.terminal_graphics import Terminal, ScreenData, Coords
from lib.sprites import Sprites
import keyboard

GROUND_WIDTH = 80

class Ground():
    def __init__(self, screen: ScreenData, width: int, pos: Coords):
        super().__init__()
        self.width = width
        self.sprite = Sprites.GROUND_SPRITE * self.width
        self.pos = pos
        self.xpos = pos.xpos
        self.ypos = pos.ypos
        self.screen = screen
    
    def render(self):
        for i in range(self.width):
            self.screen[Coords(self.xpos + i, self.ypos)] = Sprites.GROUND_SPRITE
        collision_coords = [Coords(self.xpos + i, self.ypos) for i in range(self.width)]
        return self.screen, collision_coords

class Coin():
    def __init__(self, screen: ScreenData, pos: Coords):
        self.pos = pos
        self.secondary_pos = Coords(pos.xpos, pos.ypos - 1)
        self.screen = screen
        self.hide = False
        self.broken = False
        self.updated = False
        self.killed = False

    def hide_coin(self):
        self.hide = True

    def __del__(self):
        if not self.updated:
            self.screen[self.pos] = ' '  # Clear the coin's position from the screen
            self.updated = True
            self.broken, self.killed = True, True
        else: pass

    def render(self, previous_pos: Coords = None):
        new_screen: ScreenData = {
            self.pos: Sprites.COIN_SPRITE if not self.hide else ' '  # 'C' represents the coin
        }
        self.screen.update(new_screen)
        return self.screen

class Powerup(Coin):
    def render(self, previous_pos: Coords = None):
        new_screen: ScreenData = {
            self.pos: Sprites.POWERUP_BLOCK_SPRITE if not self.hide else Sprites.HIT_POWERUP_BLOCK_SPRITE  # '?' represents the powerup block
        }
        self.screen.update(new_screen)
        return self.screen
    
class StompableEnemy(Coin):
    def __init__(self, screen: ScreenData, pos: Coords):
        super().__init__(screen, pos)
        self.killed = False
        self.sidepos = (
            Coords(pos.xpos - 1, pos.ypos),
            Coords(pos.xpos + 1, pos.ypos),
        )
        self.secondary_pos = Coords(pos.xpos, pos.ypos - 1)
        self.previous_pos = pos

    def move_towards_player(self, player_pos: Coords):
        if self.killed:
            return  # Do not move if the enemy is killed

        new_xpos = self.pos.xpos
        if self.pos.xpos < player_pos.xpos:
            new_xpos += 1
        elif self.pos.xpos > player_pos.xpos:
            new_xpos -= 1
        
        new_ypos = self.pos.ypos
        self.previous_pos = self.pos
        self.pos = Coords(new_xpos, new_ypos)
        self.sidepos = (
            Coords(new_xpos - 1, new_ypos),
            Coords(new_xpos + 1, new_ypos),
        )
        self.secondary_pos = Coords(new_xpos, new_ypos - 1)
    
    def render(self, previous_pos: Coords = None):
        new_screen: ScreenData = {}

        if not self.hide:
            new_screen[self.pos] = Sprites.ENEMY1_SPRITE
            if self.previous_pos != self.pos:
                new_screen[self.previous_pos] = ' '  # Clear the previous position
        elif self.hide or self.killed:
            if not self.updated:
                new_screen[self.pos] = ' '
                self.updated = True
        self.screen.update(new_screen)
        return self.screen
    
class Fireball(Coin):
    def __init__(self, screen: ScreenData, pos: Coords, direction: int, enemies: tuple[StompableEnemy]):
        super().__init__(screen, pos)
        self.direction = direction  # Store the direction of the fireball
        self.creation_time = time.time()  # Record the creation time of the fireball
        self.hit = False
        self.old_pos = None  # Initialize old position as None
        self.enemies = enemies

    def render(self, previous_pos: Coords = None):
        new_screen: ScreenData = {}
        if self.hit:
            new_screen[self.pos] = ' '
        elif not self.old_pos:
            new_screen[self.pos] = Sprites.FIREBALL_RIGHT_SPRITE if self.direction == 1 else Sprites.FIREBALL_LEFT_SPRITE  # Render the fireball at its current position
        elif self.pos != self.old_pos:
            new_screen[self.pos] = Sprites.FIREBALL_RIGHT_SPRITE if self.direction == 1 else Sprites.FIREBALL_LEFT_SPRITE  # Render the fireball at its new position
            new_screen[self.old_pos] = ' '  # Clear the fireball's previous position
        if self.pos == self.old_pos: new_screen[self.pos] = ' '  # Clear the fireball's current position
        if self.pos.xpos == 0: new_screen[self.pos] = ' '
        if self.pos.xpos == (GROUND_WIDTH - 1): new_screen[self.pos] = ' '
        for enemy in self.enemies:
            for pos in enemy.sidepos:
                if (pos == self.pos) and (not enemy.killed):
                    self.hit = True
                    new_screen[pos] = ' '
        
        new_screen[Coords(5, 1)] = f'Last fireball position: {self.pos.xpos}, {self.pos.ypos}'
        self.screen.update(new_screen)
        return self.screen

    def next_pos(self):
        new_xpos = self.pos.xpos + self.direction  # Move the fireball based on its direction
        new_ypos = self.pos.ypos

        # Store the old position before updating to the new position
        self.old_pos = self.pos

        self.pos = Coords(new_xpos, new_ypos)  # Create a new Coords instance with the updated position
        self.secondary_pos = Coords(new_xpos, new_ypos - 1)  # Update secondary position accordingly

        # Check collision with ground border
        if self.pos.xpos >= (GROUND_WIDTH) or self.pos.xpos < 0:
            self.screen[self.old_pos] = ' '  # Clear the character on the old position
            return True  # Indicate collision with ground border
        return False  # Indicate no collision

    def check_lifetime(self):
        # Check if the fireball has existed for more than 3 seconds
        return time.time() - self.creation_time > 3

class Brick(Coin):
    def render(self, previous_pos: Coords = None):
        new_screen: ScreenData = {}
        if not self.hide:
            new_screen: ScreenData = {
                self.pos: Sprites.BRICK_SPRITE
            }
        elif self.hide or self.broken:
            if not self.updated:
                new_screen: ScreenData = {
                    self.pos: ' '
                }
                self.updated = True
        self.screen.update(new_screen)
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
        self.powerstate = 0
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
                    self.powerstate += 1 if not self.powerups[id].hide else 0
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

    level_ground = Ground(screen, GROUND_WIDTH, Coords(0, 10))
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
