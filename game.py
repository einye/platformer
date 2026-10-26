"""
Platformer Game Extension
Extends the basic platformer with:
- Main Menu, Game, and Game Over states
- Animated Player Character
- Enemies with simple AI and Directional Flipping
- 3 Levels
"""
import arcade
import os

# --- Constants ---
WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080
WINDOW_TITLE = "Platformer Extended"

# Scaling
TILE_SCALING = 0.5
COIN_SCALING = 0.5
CHARACTER_SCALING = 0.5

# Physics
PLAYER_MOVEMENT_SPEED = 5
PLAYER_JUMP_SPEED = 20
GRAVITY = 1

# Game Logic
PLAYER_START_X = 64
PLAYER_START_Y = 128
PLAYER_HEALTH = 100
ENEMY_DAMAGE = 25
TOTAL_LEVELS = 3

# Assets
PLAYER_IMAGE_PATH = ":resources:images/animated_characters/female_adventurer/"
ENEMY_IMAGE_PATH = ":resources:images/animated_characters/zombie/"

def load_texture_pair(filename):
    """ Load a texture pair for flipping (Right/Left) """
    tex = arcade.load_texture(filename)
    return [tex, tex.flip_horizontally()]

class PlayerCharacter(arcade.Sprite):
    """ Player Sprite with Animation """
    def __init__(self):
        super().__init__()
        self.scale = CHARACTER_SCALING
        self.health = PLAYER_HEALTH
        self.is_on_ladder = False

        self.idle_texture_pair = load_texture_pair(f"{PLAYER_IMAGE_PATH}femaleAdventurer_idle.png")
        self.jump_texture_pair = load_texture_pair(f"{PLAYER_IMAGE_PATH}femaleAdventurer_jump.png")
        self.fall_texture_pair = load_texture_pair(f"{PLAYER_IMAGE_PATH}femaleAdventurer_fall.png")

        self.walk_textures = []
        for i in range(8):
            self.walk_textures.append(load_texture_pair(f"{PLAYER_IMAGE_PATH}femaleAdventurer_walk{i}.png"))

        self.texture = self.idle_texture_pair[0]
        self.character_face_direction = 0  # 0 for right, 1 for left
        self.cur_texture = 0

    def update_animation(self, delta_time: float = 1 / 60):
        if self.change_x < 0 and self.character_face_direction == 0:
            self.character_face_direction = 1
        elif self.change_x > 0 and self.character_face_direction == 1:
            self.character_face_direction = 0

        if self.change_y > 0 and not self.is_on_ladder:
            self.texture = self.jump_texture_pair[self.character_face_direction]
            return
        elif self.change_y < 0 and not self.is_on_ladder:
            self.texture = self.fall_texture_pair[self.character_face_direction]
            return

        if self.change_x == 0:
            self.texture = self.idle_texture_pair[self.character_face_direction]
            return

        self.cur_texture += 1
        if self.cur_texture > 7 * 5:
            self.cur_texture = 0
        self.texture = self.walk_textures[self.cur_texture // 5][self.character_face_direction]

class Enemy(arcade.Sprite):
    """ Patrolling enemy that flips based on movement direction """
    def __init__(self, center_x, center_y):
        super().__init__(scale=CHARACTER_SCALING)
        self.textures = load_texture_pair(f"{ENEMY_IMAGE_PATH}zombie_idle.png")
        self.texture = self.textures[0]
        
        self.center_x = center_x
        self.center_y = center_y
        self.change_x = 2
        self.boundary_left = center_x - 100
        self.boundary_right = center_x + 100

    def update(self, delta_time: float = 1/60):
        self.center_x += self.change_x
        self.texture = self.textures[0] if self.change_x > 0 else self.textures[1]

        if self.center_x < self.boundary_left or self.center_x > self.boundary_right:
            self.change_x *= -1

class MainMenu(arcade.View):
    def on_show_view(self):
        self.window.background_color = arcade.color.DARK_BLUE_GRAY

    def on_draw(self):
        self.clear()
        arcade.Text("Platformer Adventure", WINDOW_WIDTH/2, WINDOW_HEIGHT/2 + 50, arcade.color.WHITE, 50, anchor_x="center").draw()
        arcade.Text("Press ENTER to Start", WINDOW_WIDTH/2, WINDOW_HEIGHT/2, arcade.color.WHITE, 20, anchor_x="center").draw()

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ENTER:
            game_view = GameView()
            game_view.setup()
            self.window.show_view(game_view)

class GameOverView(arcade.View):
    def __init__(self, message, score):
        super().__init__()
        self.message = message
        self.score = score

    def on_show_view(self):
        self.window.background_color = arcade.color.BLACK

    def on_draw(self):
        self.clear()
        arcade.Text(self.message, WINDOW_WIDTH/2, WINDOW_HEIGHT/2 + 50, arcade.color.WHITE, 50, anchor_x="center").draw()
        arcade.Text(f"Final Score: {self.score}", WINDOW_WIDTH/2, WINDOW_HEIGHT/2 - 20, arcade.color.WHITE, 30, anchor_x="center").draw()
        arcade.Text("Press ENTER to Restart", WINDOW_WIDTH/2, WINDOW_HEIGHT/2 - 80, arcade.color.GRAY, 20, anchor_x="center").draw()

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ENTER:
            self.window.show_view(MainMenu())

class GameView(arcade.View):
    def __init__(self):
        super().__init__()
        self.scene = self.player_sprite = self.physics_engine = None
        self.camera = self.gui_camera = None
        self.score = 0
        self.level = 1
        self.collect_coin_sound = arcade.load_sound(":resources:sounds/coin1.wav")
        self.jump_sound = arcade.load_sound(":resources:sounds/jump1.wav")
        self.gameover_sound = arcade.load_sound(":resources:sounds/gameover1.wav")
        self.hit_sound = arcade.load_sound(":resources:sounds/hit1.wav")

    def setup(self):
        self.camera = arcade.Camera2D()
        self.gui_camera = arcade.Camera2D()
        map_name = f":resources:tiled_maps/map2_level_{self.level}.json"
        if self.level > 2: map_name = ":resources:tiled_maps/map2_level_1.json"
            
        layer_options = {"Platforms": {"use_spatial_hash": True}, "Coins": {"use_spatial_hash": True}, "Don't Touch": {"use_spatial_hash": True}}
        self.tile_map = arcade.load_tilemap(map_name, TILE_SCALING, layer_options)
        self.scene = arcade.Scene.from_tilemap(self.tile_map)
        self.end_of_map = self.tile_map.width * self.tile_map.tile_width * TILE_SCALING

        self.player_sprite = PlayerCharacter()
        self.player_sprite.center_x, self.player_sprite.center_y = PLAYER_START_X, PLAYER_START_Y
        self.scene.add_sprite("Player", self.player_sprite)
        self.setup_enemies()

        self.physics_engine = arcade.PhysicsEnginePlatformer(self.player_sprite, walls=self.scene["Platforms"], gravity_constant=GRAVITY)
        self.window.background_color = arcade.color.CORNFLOWER_BLUE

    def setup_enemies(self):
        """ Dynamically set enemy positions based on level to prevent floating """
        enemy_layer = arcade.SpriteList()
        self.scene.add_sprite_list("Enemies", False, enemy_layer)
        
        # Adjust Y and X coordinates specifically for Level 2's lower platforms
        if self.level == 2:
            ground_y = 90 
            positions = [(450, ground_y), (1100, ground_y), (2200, ground_y)]
        else:
            ground_y = 225 
            positions = [(500, ground_y), (1000, ground_y), (2000, ground_y)]
            if self.level == 3:
                positions.extend([(800, ground_y), (1500, 300), (2200, ground_y)])
        
        for pos in positions:
            if pos[0] < self.end_of_map:
                self.scene.add_sprite("Enemies", Enemy(pos[0], pos[1]))

    def on_draw(self):
        self.clear()
        self.camera.use()
        self.scene.draw()
        self.gui_camera.use()
        arcade.Text(f"Score: {self.score}", 10, WINDOW_HEIGHT - 30, arcade.color.WHITE, 18).draw()
        arcade.Text(f"Health: {self.player_sprite.health}%", 10, WINDOW_HEIGHT - 60, arcade.color.RED, 18).draw()
        arcade.Text(f"Level: {self.level}", WINDOW_WIDTH - 100, WINDOW_HEIGHT - 30, arcade.color.YELLOW, 18).draw()

    def on_update(self, delta_time):
        self.physics_engine.update()
        self.player_sprite.update_animation(delta_time)
        self.scene.update(delta_time, ["Enemies"])

        # Collisions
        if arcade.check_for_collision_with_list(self.player_sprite, self.scene["Coins"]):
            for coin in arcade.check_for_collision_with_list(self.player_sprite, self.scene["Coins"]):
                coin.remove_from_sprite_lists()
                arcade.play_sound(self.collect_coin_sound)
                self.score += 75

        enemy_hits = arcade.check_for_collision_with_list(self.player_sprite, self.scene["Enemies"])
        for enemy in enemy_hits:
            if self.player_sprite.health > 0:
                self.player_sprite.health -= ENEMY_DAMAGE
                arcade.play_sound(self.hit_sound)
                self.player_sprite.change_x = -5 if self.player_sprite.center_x < enemy.center_x else 5
                if self.player_sprite.health <= 0: self.game_over(False)

        if arcade.check_for_collision_with_list(self.player_sprite, self.scene["Don't Touch"]) or self.player_sprite.center_y < -100:
             self.game_over(False)

        if self.player_sprite.center_x >= self.end_of_map:
            self.level += 1
            if self.level > TOTAL_LEVELS: self.game_over(True)
            else: self.setup()

        self.camera.position = self.player_sprite.position

    def game_over(self, win):
        if not win: arcade.play_sound(self.gameover_sound)
        self.window.show_view(GameOverView("YOU WIN!" if win else "GAME OVER", self.score))

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ESCAPE: self.window.show_view(MainMenu())
        if (key == arcade.key.UP or key == arcade.key.W) and self.physics_engine.can_jump():
            self.player_sprite.change_y = PLAYER_JUMP_SPEED
            arcade.play_sound(self.jump_sound)
        if key == arcade.key.LEFT or key == arcade.key.A: self.player_sprite.change_x = -PLAYER_MOVEMENT_SPEED
        elif key == arcade.key.RIGHT or key == arcade.key.D: self.player_sprite.change_x = PLAYER_MOVEMENT_SPEED

    def on_key_release(self, key, modifiers):
        if key in [arcade.key.LEFT, arcade.key.A, arcade.key.RIGHT, arcade.key.D]: self.player_sprite.change_x = 0

def main():
    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE)
    window.show_view(MainMenu())
    arcade.run()

if __name__ == "__main__":
    main()