import pyglet
from pyglet.window import key, mouse
from pyglet.gl import *
import math
import random
import noise
import numpy as np
from collections import defaultdict

# Constants
TICKS_PER_SEC = 60
CHUNK_s = 16
RENDER_DISTANCE = 4
s = size

class StableDiffusionWorld:
    """World generation using noise patterns inspired by Stable Diffusion"""
    
    def __init__(self, seed=None):
        self.seed = seed if seed else random.randint(0, 10000)
        self.blocks = {}
        self.visible_blocks = {}
        self.chunks = {}
        self.batch = pyglet.graphics.Batch()
        
        # Noise parameters for different terrain features
        self.terrain_scale = 0.1
        self.mountain_scale = 0.05
        self.cave_scale = 0.2
        self.biome_scale = 0.02
        
        # Initialize texture generator
        self.texture_cache = {}
        self.generate_base_textures()
        
    def generate_base_textures(self):
        """Generate procedural textures for blocks"""
        # Simple color-based textures for now
        self.textures = {
            'grass': (0.2, 0.8, 0.3),
            'dirt': (0.5, 0.4, 0.2),
            'stone': (0.6, 0.6, 0.6),
            'sand': (0.9, 0.8, 0.5),
            'water': (0.2, 0.5, 0.9),
            'wood': (0.6, 0.4, 0.2),
            'leaves': (0.3, 0.7, 0.3),
            'snow': (0.95, 0.95, 0.95),
            'bedrock': (0.2, 0.2, 0.2)
        }
    
    def get_block_color(self, block_type):
        """Get RGB color for a block type"""
        return self.textures.get(block_type, (1, 1, 1))
    
    def sample_latent_space(self, x, y, z):
        """Sample from a pseudo-latent space using multiple noise functions"""
        # Base terrain
        height = noise.pnoise2(
            x * self.terrain_scale,
            z * self.terrain_scale,
            octaves=4,
            persistence=0.5,
            lacunarity=2.0,
            repeatx=1024,
            repeaty=1024,
            base=self.seed
        )
        
        # Mountains
        mountains = noise.pnoise2(
            x * self.mountain_scale,
            z * self.mountain_scale,
            octaves=6,
            persistence=0.5,
            lacunarity=2.2,
            base=self.seed + 1000
        )
        
        # Biome variation
        biome = noise.pnoise2(
            x * self.biome_scale,
            z * self.biome_scale,
            octaves=2,
            persistence=0.8,
            base=self.seed + 2000
        )
        
        # Cave structure
        cave = noise.pnoise3(
            x * self.cave_scale,
            y * self.cave_scale,
            z * self.cave_scale,
            octaves=3,
            persistence=0.6,
            base=self.seed + 3000
        )
        
        return height, mountains, biome, cave
    
    def get_block_type(self, x, y, z):
        """Determine block type based on noise samples"""
        height, mountains, biome, cave = self.sample_latent_space(x, y, z)
        
        # Calculate surface height
        surface_height = int((height + 1) * 10 + (mountains + 1) * 20)
        
        # Determine biome
        if biome > 0.3:
            biome_type = 'desert'
        elif biome > 0:
            biome_type = 'plains'
        elif biome > -0.3:
            biome_type = 'forest'
        else:
            biome_type = 'snow'
        
        # Generate block based on position
        if y < 0:
            return 'bedrock'
        elif y == 0:
            return 'bedrock'
        elif y < surface_height - 5:
            # Underground
            if cave > 0.2:
                return None  # Air (cave)
            else:
                return 'stone'
        elif y < surface_height - 1:
            return 'dirt'
        elif y == surface_height - 1:
            # Surface
            if biome_type == 'desert':
                return 'sand'
            elif biome_type == 'snow':
                return 'snow'
            else:
                return 'grass'
        elif y == surface_height:
            # Above surface
            if biome_type == 'forest' and random.random() > 0.7:
                # Generate trees
                if self.should_generate_tree(x, y, z):
                    return 'wood'
            return None
        else:
            return None
    
    def should_generate_tree(self, x, y, z):
        """Check if a tree should be generated at this position"""
        # Check surrounding area
        for dx in [-2, -1, 0, 1, 2]:
            for dz in [-2, -1, 0, 1, 2]:
                if dx == 0 and dz == 0:
                    continue
                if (x + dx, y, z + dz) in self.blocks:
                    return False
        return True
    
    def generate_chunk(self, cx, cz):
        """Generate all blocks in a chunk"""
        chunk_key = (cx, cz)
        if chunk_key in self.chunks:
            return
        
        chunk_blocks = []
        for x in range(cx * CHUNK_s, (cx + 1) * CHUNK_s):
            for z in range(cz * CHUNK_s, (cz + 1) * CHUNK_s):
                # Get surface height
                height, mountains, biome, cave = self.sample_latent_space(x, 0, z)
                surface_height = int((height + 1) * 10 + (mountains + 1) * 20)
                
                # Generate column of blocks
                for y in range(64):  # Generate up to y=64
                    block_type = self.get_block_type(x, y, z)
                    if block_type:
                        pos = (x, y, z)
                        self.blocks[pos] = block_type
                        chunk_blocks.append(pos)
                        
                        # Generate tree on grass
                        if block_type == 'grass' and random.random() > 0.95:
                            self.generate_tree(x, y + 1, z)
        
        self.chunks[chunk_key] = chunk_blocks
        
        # Generate water at sea level
        for x in range(cx * CHUNK_s, (cx + 1) * CHUNK_s):
            for z in range(cz * CHUNK_s, (cz + 1) * CHUNK_s):
                for y in range(10, 15):  # Water layer
                    pos = (x, y, z)
                    if pos not in self.blocks:
                        self.blocks[pos] = 'water'
                        chunk_blocks.append(pos)
    
    def generate_tree(self, x, y, z):
        """Generate a simple tree"""
        # Trunk
        trunk_height = random.randint(4, 6)
        for dy in range(trunk_height):
            self.blocks[(x, y + dy, z)] = 'wood'
        
        # Leaves
        top_y = y + trunk_height
        leaf_radius = 2
        for dx in range(-leaf_radius, leaf_radius + 1):
            for dy in range(-1, 2):
                for dz in range(-leaf_radius, leaf_radius + 1):
                    dist = math.sqrt(dx*dx + dy*dy + dz*dz)
                    if dist <= leaf_radius and random.random() > 0.3:
                        pos = (x + dx, top_y + dy, z + dz)
                        if pos not in self.blocks:
                            self.blocks[pos] = 'leaves'
    
    def get_chunk_key(self, x, z):
        """Convert world coordinates to chunk coordinates"""
        return (x // CHUNK_s, z // CHUNK_s)
    
    def update_visible_chunks(self, player_pos):
        """Update which chunks are visible based on player position"""
        px, py, pz = player_pos
        current_chunk = self.get_chunk_key(px, pz)
        
        # Generate chunks in render distance
        for dx in range(-RENDER_DISTANCE, RENDER_DISTANCE + 1):
            for dz in range(-RENDER_DISTANCE, RENDER_DISTANCE + 1):
                chunk_x = current_chunk[0] + dx
                chunk_z = current_chunk[1] + dz
                self.generate_chunk(chunk_x, chunk_z)
    
    def create_cube_vertices(self, x, y, z, block_type):
        """Create vertices for a cube"""
        s = 0.5
        color = self.get_block_color(block_type)
        
        # Define cube vertices
        vertices = []
        colors = []
        
        # Front face
        vertices.extend([x-s, y-s, z+s, x+s, y-s, z+s, 
                         x+s, y+s, z+s, x-s, y+s, z+s])
        colors.extend(color * 4)
        
        # Back face
        vertices.extend([x-s, y-s, z-s, x-s, y+s, z-s,
                         x+s, y+s, z-s, x+s, y-s, z-s])
        colors.extend(color * 4)
        
        # Right face
        vertices.extend([x+s, y-s, z-s, x+s, y+s, z-s,
                         x+s, y+s, z+s, x+s, y-s, z+s])
        colors.extend(color * 4)
        
        # Left face
        vertices.extend([x-s, y-s, z-s, x-s, y-s, z+s,
                         x-s, y+s, z+s, x-s, y+s, z-s])
        colors.extend(color * 4)
        
        # Top face
        vertices.extend([x-s, y+s, z-s, x-s, y+s, z+s,
                         x+s, y+s, z+s, x+s, y+s, z-s])
        colors.extend(color * 4)
        
        # Bottom face
        vertices.extend([x-s, y-s, z-s, x+s, y-s, z-s,
                         x+s, y-s, z+s, x-s, y-s, z+s])
        colors.extend(color * 4)
        
        return vertices, colors
    
    def rebuild_batch(self, player_pos):
        """Rebuild the graphics batch with visible blocks"""
        self.batch = pyglet.graphics.Batch()
        self.visible_blocks = {}
        
        px, py, pz = player_pos
        render_sq = RENDER_DISTANCE * CHUNK_s
        
        # Add visible blocks to batch
        for (x, y, z), block_type in list(self.blocks.items()):
            # Check if block is within render distance
            if abs(x - px) < render_sq and abs(z - pz) < render_sq:
                # Check if block is exposed (has at least one neighbor missing)
                if self.is_exposed((x, y, z)):
                    vertices, colors = self.create_cube_vertices(x, y, z, block_type)
                    self.visible_blocks[(x, y, z)] = self.batch.add(
                        24, GL_QUADS, None,
                        ('v3f/static', vertices),
                        ('c3f/static', colors)
                    )

    def is_exposed(self, pos):
        """Check if a block has at least one face exposed to air"""
        x, y, z = pos
        neighbors = [
            (x+1, y, z), (x-1, y, z),
            (x, y+1, z), (x, y-1, z),
            (x, y, z+1), (x, y, z-1)
        ]
        
        for neighbor in neighbors:
            if neighbor not in self.blocks:
                return True
        return False
    
    def add_block(self, pos, block_type='stone'):
        """Add a block at the given position"""
        self.blocks[pos] = block_type
        
    def remove_block(self, pos):
        """Remove a block at the given position"""
        if pos in self.blocks:
            del self.blocks[pos]

class Player:
    def __init__(self, position=(0, 20, 0)):
        self.position = list(position)
        self.rotation = [0, 0]  # yaw, pitch
        self.velocity = [0, 0, 0]
        self.on_ground = False
        self.flying = False
        
    def get_view_vector(self):
        """Get normalized view direction vector"""
        yaw, pitch = math.radians(self.rotation[0]), math.radians(self.rotation[1])
        
        x = math.cos(yaw) * math.cos(pitch)
        y = math.sin(pitch)
        z = math.sin(yaw) * math.cos(pitch)
        
        length = math.sqrt(x*x + y*y + z*z)
        if length > 0:
            return (x/length, y/length, z/length)
        return (0, 0, 1)
    
    def get_movement_vector(self, strafe):
        """Calculate movement vector from strafe inputs"""
        if strafe == [0, 0]:
            return (0, 0, 0)
        
        yaw = math.radians(self.rotation[0])
        dx = math.cos(yaw) * strafe[0] + math.sin(yaw) * strafe[1]
        dz = math.sin(yaw) * strafe[0] - math.cos(yaw) * strafe[1]
        
        length = math.sqrt(dx*dx + dz*dz)
        if length > 0:
            dx /= length
            dz /= length
            
        return (dx, 0, dz)

class StableCraftWindow(pyglet.window.Window):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.world = StableDiffusionWorld()
        self.player = Player()
        
        # Generate initial world
        self.world.update_visible_chunks(self.player.position)
        self.world.rebuild_batch(self.player.position)
        
        # Game state
        self.strafe = [0, 0]  # forward/back, left/right
        self.mouse_locked = True
        self.selected_block = 'stone'
        
        # Setup OpenGL
        self.setup_opengl()
        
        # Create crosshair
        self.crosshair = self.create_crosshair()
        
        # Create UI labels
        self.create_ui()
        
        # Schedule updates
        pyglet.clock.schedule_interval(self.update, 1.0/TICKS_PER_SEC)
        
        # Lock mouse
        self.set_exclusive_mouse(True)
    
    def setup_opengl(self):
        """Configure OpenGL settings"""
        glClearColor(0.6, 0.8, 1.0, 1)  # Sky blue
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_CULL_FACE)
        glCullFace(GL_BACK)
        
        # Enable lighting (simple)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        
        # Light position
        glLightfv(GL_LIGHT0, GL_POSITION, (GLfloat * 4)(100, 100, 100, 1))
        glLightfv(GL_LIGHT0, GL_AMBIENT, (GLfloat * 4)(0.2, 0.2, 0.2, 1))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (GLfloat * 4)(0.8, 0.8, 0.8, 1))
    
    def create_crosshair(self):
        """Create aiming crosshair"""
        x, y = self.width // 2, self.height // 2
        s = 10
        
        return pyglet.graphics.vertex_list(4,
            ('v2i', (x-s, y, x+s, y, x, y-s, x, y+s))
        )
    
    def create_ui(self):
        """Create UI elements"""
        self.info_label = pyglet.text.Label(
            'StableCraft - Procedural World Generation',
            font_name='Arial', font_s=14,
            x=10, y=self.height - 20,
            color=(255, 255, 255, 255)
        )
        
        self.position_label = pyglet.text.Label(
            '',
            font_name='Arial', font_s=12,
            x=10, y=self.height - 40,
            color=(255, 255, 255, 255)
        )
        
        self.controls_label = pyglet.text.Label(
            'WASD: Move | SPACE: Jump | LMB: Break | RMB: Place | TAB: Fly | ESC: Menu',
            font_name='Arial', font_s=11,
            x=10, y=10,
            color=(200, 200, 200, 255)
        )
    
    def raycast(self, start, direction, max_distance=10):
        """Cast a ray to find intersected block"""
        step = 0.1
        current = list(start)
        
        for _ in range(int(max_distance / step)):
            # Check current block
            block_pos = (
                int(round(current[0])),
                int(round(current[1])),
                int(round(current[2]))
            )
            
            if block_pos in self.world.blocks:
                # Find adjacent empty position
                prev_pos = (
                    int(round(current[0] - direction[0] * step)),
                    int(round(current[1] - direction[1] * step)),
                    int(round(current[2] - direction[2] * step))
                )
                return block_pos, prev_pos
            
            current[0] += direction[0] * step
            current[1] += direction[1] * step
            current[2] += direction[2] * step
        
        return None, None
    
    def on_mouse_press(self, x, y, button, modifiers):
        """Handle mouse clicks for block interaction"""
        if not self.mouse_locked:
            self.set_exclusive_mouse(True)
            self.mouse_locked = True
            return
        
        direction = self.player.get_view_vector()
        hit_pos, adjacent_pos = self.raycast(self.player.position, direction)
        
        if button == mouse.LEFT and hit_pos:
            self.world.remove_block(hit_pos)
            self.world.rebuild_batch(self.player.position)
        elif button == mouse.RIGHT and adjacent_pos:
            self.world.add_block(adjacent_pos, self.selected_block)
            self.world.rebuild_batch(self.player.position)
    
    def on_mouse_motion(self, x, y, dx, dy):
        """Handle mouse look"""
        if self.mouse_locked:
            sensitivity = 0.2
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
        elif symbol == key.R:
            # Regenerate world with new seed
            self.world = StableDiffusionWorld()
            self.world.update_visible_chunks(self.player.position)
            self.world.rebuild_batch(self.player.position)
    
    def on_key_release(self, symbol, modifiers):
        """Handle key releases"""
        if symbol == key.W: self.strafe[0] += 1
        elif symbol == key.S: self.strafe[0] -= 1
        elif symbol == key.A: self.strafe[1] += 1
        elif symbol == key.D: self.strafe[1] -= 1
    
    def update(self, dt):
        """Update game state"""
        # Update player movement
        move_vec = self.player.get_movement_vector(self.strafe)
        
        # Apply gravity if not flying
        if not self.player.flying:
            self.player.velocity[1] -= 0.02  # Gravity
            self.player.velocity[1] = max(self.player.velocity[1], -0.5)
        else:
            if self.strafe[0] < 0:  # W key
                self.player.velocity[1] = 0.1
            elif self.strafe[0] > 0:  # S key
                self.player.velocity[1] = -0.1
            else:
                self.player.velocity[1] = 0
        
        # Update position
        speed = 8 if self.player.flying else 5
        self.player.position[0] += move_vec[0] * dt * speed
        self.player.position[1] += self.player.velocity[1]
        self.player.position[2] += move_vec[2] * dt * speed
        
        # Simple ground collision
        ground_y = 0
        for y in range(int(self.player.position[1]) - 2, int(self.player.position[1]) + 2):
            test_pos = (int(self.player.position[0]), y, int(self.player.position[2]))
            if test_pos in self.world.blocks:
                ground_y = y + 1.5
                break
        
        if self.player.position[1] < ground_y:
            self.player.position[1] = ground_y
            self.player.velocity[1] = 0
            self.player.on_ground = True
        else:
            self.player.on_ground = False
        
        # Update visible chunks
        self.world.update_visible_chunks(self.player.position)
        
        # Update UI
        self.position_label.text = f"Position: ({self.player.position[0]:.1f}, {self.player.position[1]:.1f}, {self.player.position[2]:.1f}) | Blocks: {len(self.world.blocks)}"
    
    def set_3d_projection(self):
        """Set up 3D projection matrix"""
        width, height = self.get_s()
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
        width, height = self.get_s()
        
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, width, 0, height, -1, 1)
        
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)
    
    def draw_selection_cube(self):
        """Draw wireframe cube around selected block"""
        direction = self.player.get_view_vector()
        hit_pos, adjacent_pos = self.raycast(self.player.position, direction)
        
        if hit_pos:
            x, y, z = hit_pos
            s = 0.52
            
            # Define cube edges
            vertices = [
                (x-s, y-s, z-s), (x+s, y-s, z-s),
                (x+s, y-s, z-s), (x+s, y-s, z+s),
                (x+s, y-s, z+s), (x-s, y-s, z+s),
                (x-s, y-s, z+s), (x-s, y-s, z-s),
                
                (x-s, y+s, z-s), (x+s, y+s, z-s),
                (x+s, y+s, z-s), (x+s, y+s, z+s),
                (x+s, y+s, z+s), (x-s, y+s, z+s),
                (x-s, y+s, z+s), (x-s, y+s, z-s),
                
                (x-s, y-s, z-s), (x-s, y+s, z-s),
                (x+s, y-s, z-s), (x+s, y+s, z-s),
                (x+s, y-s, z+s), (x+s, y+s, z+s),
                (x-s, y-s, z+s), (x-s, y+s, z+s)
            ]
            
            # Flatten vertices
            flat_vertices = []
            for v in vertices:
                flat_vertices.extend(v)
            
            # Draw wireframe
            glColor3f(1, 1, 1)
            glLineWidth(2)
            pyglet.graphics.draw(len(vertices), GL_LINES,
                               ('v3f/static', flat_vertices))
    
    def on_draw(self):
        """Render the game"""
        self.clear()
        
        # Draw 3D world
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        self.set_3d_projection()
        
        # Draw world
        self.world.batch.draw()
        
        # Draw selection cube
        self.draw_selection_cube()
        
        # Draw 2D UI
        self.set_2d_projection()
        
        # Draw crosshair
        if self.mouse_locked:
            glColor3f(1, 1, 1)
            self.crosshair.draw(GL_LINES)
        
        # Draw labels
        self.info_label.draw()
        self.position_label.draw()
        self.controls_label.draw()

def main():
    """Main entry point"""
    window = StableCraftWindow(
        width=1200,
        height=800,
        caption='StableCraft - Procedural Minecraft Clone',
        resizable=True
    )
    
    # Set window icon
    try:
        icon = pyglet.image.load('DeepSeek.png')
        window.set_icon(icon)
    except:
        pass
    pyglet.app.run()

if __name__ == '__main__':

    main()
