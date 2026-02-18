import pyglet
from pyglet.window import key, mouse
from pyglet.gl import *
import math
import random

# Game constants
TICKS_PER_SEC = 60
SECTOR_n = 16
BLOCK_n = 0.5

# Block types with their texture coordinates
BLOCK = {
    'GRASS': ((1, 0), (1, 0), (1, 0)),
    'WATER': ((0, 1), (0, 1), (0, 1)),
    'STONE': ((2, 1), (2, 1), (2, 1)),
    'DIRT':  ((2, 0), (2, 0), (2, 0)),
    'SAND':  ((1, 1), (1, 1), (1, 1)),
    'WOOD':  ((1, 2), (1, 2), (1, 2))
}

# Direction vectors for faces
FACE_VECTORS = [
    ( 1, 0, 0),  # Right
    ( 0, 1, 0),  # Top
    ( 0, 0, 1),  # Front
    ( 0, 0,-1),  # Back
    ( 0,-1, 0),  # Bottom
    (-1, 0, 0),  # Left
]

class Block:
    def create_vertices(x, y, z, n):
        """Generate cube vertices for a block"""
        return [
            x+n, y-n, z+n, x+n, y-n, z-n, x+n, y+n, z-n, x+n, y+n, z+n,  # Right
            x-n, y-n, z-n, x-n, y-n, z+n, x-n, y+n, z+n, x-n, y+n, z-n,  # Left
            x-n, y+n, z-n, x-n, y+n, z+n, x+n, y+n, z+n, x+n, y+n, z-n,  # Top
            x-n, y-n, z-n, x+n, y-n, z-n, x+n, y-n, z+n, x-n, y-n, z+n,  # Bottom
            x-n, y-n, z+n, x+n, y-n, z+n, x+n, y+n, z+n, x-n, y+n, z+n,  # Front
            x-n, y-n, z-n, x-n, y+n, z-n, x+n, y+n, z-n, x+n, y-n, z-n,  # Back
        ]
    
    @staticmethod
    def get_texture_coords(block_type):
        """Get texture coordinates for a block type"""
        top, bottom, side = BLOCK.get(block_type, BLOCK['STONE'])
        
        def tex_coord(x, y, n=4):
            """Convert texture grid coordinates to UV coordinates"""
            m = 1.0 / n
            return (x * m, y * m, x * m + m, y * m + m)
        
        coords = []
        coords.extend(tex_coord(*top))     # Top face
        coords.extend(tex_coord(*bottom))  # Bottom face
        for _ in range(4):  # 4 side faces
            coords.extend(tex_coord(*side))
        return coords

class World:
    def __init__(self):
        self.batch = pyglet.graphics.Batch()
        self.blocks = {}
        self.visible_blocks = {}
        self.sectors = {}
        self.build_world()
    
    def build_world(self):
        """Generate initial world terrain"""
        # Create ground
        n = 30
        for x in range(-n, n + 1):
            for z in range(-n, n + 1):
                self.add_block((x, -1, z), 'GRASS')
                self.add_block((x, -2, z), 'STONE')
        
        # Create some hills
        for _ in range(20):
            center_x = random.randint(-n + 5, n - 5)
            center_z = random.randint(-n + 5, n - 5)
            height = random.randint(2, 5)
            radius = random.randint(3, 6)
            
            for y in range(height):
                for dx in range(-radius, radius + 1):
                    for dz in range(-radius, radius + 1):
                        if dx*dx + dz*dz <= radius*radius:
                            self.add_block((center_x + dx, y, center_z + dz), 
                                         random.choice(['GRASS', 'STONE', 'SAND']))
    
    def add_block(self, position, block_type):
        """Add a block to the world"""
        x, y, z = position
        if position in self.blocks:
            return
        
        self.blocks[position] = block_type
        
        # Check if block is visible (has at least one exposed face)
        if self.is_visible(position):
            self.make_visible(position)
    
    def remove_block(self, position):
        """Remove a block from the world"""
        if position in self.blocks:
            del self.blocks[position]
            if position in self.visible_blocks:
                self.make_hidden(position)
    
    def is_visible(self, position):
        """Check if a block has any exposed faces"""
        x, y, z = position
        for dx, dy, dz in FACE_VECTORS:
            if (x + dx, y + dy, z + dz) not in self.blocks:
                return True
        return False
    
    def make_visible(self, position):
        """Add block to visible batch"""
        if position in self.visible_blocks:
            return
        
        block_type = self.blocks[position]
        vertices = Block.create_vertices(*position)
        tex_coords = Block.get_texture_coords(block_type)
        
        self.visible_blocks[position] = self.batch.add(
            24, GL_QUADS, None,
            ('v3f/static', vertices),
            ('t2f/static', tex_coords)
        )
    
    def make_hidden(self, position):
        """Remove block from visible batch"""
        if position in self.visible_blocks:
            self.visible_blocks[position].delete()
            del self.visible_blocks[position]
    
    def raycast(self, start, direction, max_distance=10):
        """Cast a ray and return hit position and adjacent empty position"""
        step_n = 0.1
        current_pos = list(start)
        
        for _ in range(int(max_distance / step_n)):
            block_pos = (
                int(round(current_pos[0])),
                int(round(current_pos[1])),
                int(round(current_pos[2]))
            )
            
            if block_pos in self.blocks:
                # Find which face we hit by checking previous position
                prev_pos = (
                    int(round(current_pos[0] - direction[0] * step_n)),
                    int(round(current_pos[1] - direction[1] * step_n)),
                    int(round(current_pos[2] - direction[2] * step_n))
                )
                return block_pos, prev_pos
            
            current_pos[0] += direction[0] * step_n
            current_pos[1] += direction[1] * step_n
            current_pos[2] += direction[2] * step_n
        
        return None, None

class Player:
    def __init__(self, position=(0, 0, 0)):
        self.position = list(position)
        self.rotation = [0, 0]  # [yaw, pitch]
        self.velocity = [0, 0, 0]
        self.on_ground = False
        self.flying = False
        
    def get_view_direction(self):
        """Calculate view direction vector from rotation"""
        yaw, pitch = math.radians(self.rotation[0]), math.radians(self.rotation[1])
        
        dx = math.cos(yaw) * math.cos(pitch)
        dy = math.sin(pitch)
        dz = math.sin(yaw) * math.cos(pitch)
        
        length = math.sqrt(dx*dx + dy*dy + dz*dz)
        if length > 0:
            return (dx/length, dy/length, dz/length)
        return (0, 0, 1)
    
    def get_movement_vector(self, strafe):
        """Calculate movement vector based on strafe inputs"""
        if strafe[0] == 0 and strafe[1] == 0:
            return (0, 0, 0)
        
        yaw = math.radians(self.rotation[0])
        dx = math.cos(yaw) * strafe[0] + math.sin(yaw) * strafe[1]
        dz = math.sin(yaw) * strafe[0] - math.cos(yaw) * strafe[1]
        
        length = math.sqrt(dx*dx + dz*dz)
        if length > 0:
            dx /= length
            dz /= length
        
        return (dx, 0, dz)

class GameWindow(pyglet.window.Window):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.world = World()
        self.player = Player()
        
        self.strafe = [0, 0]  # [forward/back, left/right]
        self.mouse_locked = True
        self.set_exclusive_mouse(True)
        
        # Setup OpenGL
        self.setup_gl()
        
        # Create crosshair
        self.crosshair = self.create_crosshair()
        
        # Create info label
        self.info_label = pyglet.text.Label(
            'WASD: Move, SPACE: Jump, TAB: Fly, LMB: Break, RMB: Place, ESC: Menu',
            font_name='Arial', font_n=12,
            x=10, y=10, color=(255, 255, 255, 255)
        )
        
        # Schedule update
        pyglet.clock.schedule_interval(self.update, 1.0/TICKS_PER_SEC)
    
    def setup_gl(self):
        """Configure OpenGL settings"""
        glClearColor(0.5, 0.7, 1.0, 1)  # Sky blue
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_CULL_FACE)
        
        # Enable texture
        glEnable(GL_TEXTURE_2D)
        self.texture = self.load_texture('texture.png')
    
    def load_texture(self, filename):
        """Load and configure texture"""
        try:
            image = pyglet.image.load(filename)
            texture = image.get_texture()
            
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
            
            return texture
        except:
            print(f"Could not load texture: {filename}")
            return None
    
    def create_crosshair(self):
        """Create crosshair for aiming"""
        x, y = self.width // 2, self.height // 2
        n = 10
        
        return pyglet.graphics.vertex_list(4,
            ('v2i', (x-n, y, x+n, y, x, y-n, x, y+n))
        )
    
    def on_mouse_press(self, x, y, button, modifiers):
        """Handle mouse clicks for block interaction"""
        if not self.mouse_locked:
            self.set_exclusive_mouse(True)
            self.mouse_locked = True
            return
        
        direction = self.player.get_view_direction()
        hit_pos, adjacent_pos = self.world.raycast(self.player.position, direction)
        
        if button == mouse.LEFT and hit_pos:
            self.world.remove_block(hit_pos)
        elif button == mouse.RIGHT and adjacent_pos:
            self.world.add_block(adjacent_pos, 'BRICK')
    
    def on_mouse_motion(self, x, y, dx, dy):
        """Handle mouse look"""
        if self.mouse_locked:
            sensitivity = 0.15
            self.player.rotation[0] += dx * sensitivity
            self.player.rotation[1] -= dy * sensitivity
            self.player.rotation[1] = max(-90, min(90, self.player.rotation[1]))
    
    def on_key_press(self, symbol, modifiers):
        """Handle key presses"""
        if symbol == key.W: self.strafe[0] -= 1
        elif symbol == key.S: self.strafe[0] += 1
        elif symbol == key.A: self.strafe[1] -= 1
        elif symbol == key.D: self.strafe[1] += 1
        elif symbol == key.SPACE:
            if self.player.on_ground or self.player.flying:
                self.player.velocity[1] = 0.15
        elif symbol == key.TAB:
            self.player.flying = not self.player.flying
        elif symbol == key.ESCAPE:
            self.set_exclusive_mouse(False)
            self.mouse_locked = False
    
    def on_key_release(self, symbol, modifiers):
        """Handle key releases"""
        if symbol == key.W: self.strafe[0] += 1
        elif symbol == key.S: self.strafe[0] -= 1
        elif symbol == key.A: self.strafe[1] += 1
        elif symbol == key.D: self.strafe[1] -= 1
    
    def update(self, dt):
        """Update game state"""
        # Apply movement
        move_vec = self.player.get_movement_vector(self.strafe)
        
        # Apply gravity if not flying
        if not self.player.flying:
            self.player.velocity[1] -= 0.01  # Gravity
            self.player.velocity[1] = max(self.player.velocity[1], -0.5)  # Terminal velocity
        
        # Update position with simple collision
        new_pos = [
            self.player.position[0] + move_vec[0] * dt * 5,
            self.player.position[1] + self.player.velocity[1],
            self.player.position[2] + move_vec[2] * dt * 5
        ]
        
        # Simple collision with ground
        ground_level = -1
        if new_pos[1] < ground_level:
            new_pos[1] = ground_level
            self.player.velocity[1] = 0
            self.player.on_ground = True
        else:
            self.player.on_ground = False
        
        # Keep player in bounds
        world_n = 30
        new_pos[0] = max(-world_n, min(world_n, new_pos[0]))
        new_pos[2] = max(-world_n, min(world_n, new_pos[2]))
        
        self.player.position = new_pos
    
    def set_3d_projection(self):
        """Set up 3D projection matrix"""
        width, height = self.get_n()
        glViewport(0, 0, width, height)
        
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(70, width/height, 0.1, 100)
        
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        # Apply player rotation and position
        glRotatef(self.player.rotation[1], 1, 0, 0)
        glRotatef(self.player.rotation[0], 0, 1, 0)
        glTranslatef(-self.player.position[0], -self.player.position[1], -self.player.position[2])
    
    def set_2d_projection(self):
        """Set up 2D projection for UI"""
        width, height = self.get_n()
        
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, width, 0, height, -1, 1)
        
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glDisable(GL_DEPTH_TEST)
    
    def on_draw(self):
        """Render the game"""
        self.clear()
        
        # Draw 3D world
        self.set_3d_projection()
        if self.texture:
            glBindTexture(GL_TEXTURE_2D, self.texture.id)
        self.world.batch.draw()
        
        # Draw 2D overlay
        self.set_2d_projection()
        
        # Draw crosshair
        if self.mouse_locked:
            glColor3f(1, 1, 1)
            self.crosshair.draw(GL_LINES)
        
        # Draw info
        self.info_label.draw()
        
        # Draw position info
        pos_text = f"Position: {self.player.position[0]:.1f}, {self.player.position[1]:.1f}, {self.player.position[2]:.1f}"
        pos_label = pyglet.text.Label(
            pos_text, font_name='Arial', font_n=12,
            x=10, y=self.height - 20, color=(255, 255, 255, 255)
        )
        pos_label.draw()
        
        # Draw mode info
        mode = "FLYING" if self.player.flying else "WALKING"
        mode_label = pyglet.text.Label(
            f"Mode: {mode}", font_name='Arial', font_n=12,
            x=self.width - 100, y=self.height - 20, color=(255, 255, 255, 255)
        )
        mode_label.draw()

def main():
    """Main entry point"""
    window = GameWindow(width=2560, height=1440, caption='Minecraft Clone', resizable=True)
    pyglet.app.run()

if __name__ == '__main__':
    main()
