import tkinter as tk
import math
import time
import random

# --- CONFIGURATION ---
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 700
GRID_SIZE = 16
BUILDING_COUNT = 25
TREE_COUNT = 20          # Vegetation obstacles
CAR_COUNT = 10           # Moving ground traffic
BIRD_COUNT = 8           # Bio-hazards

class Vector3:
    def __init__(self, x, y, z):
        self.x, self.y, self.z = x, y, z

class LidarSim:
    def __init__(self, root):
        self.root = root
        self.root.title("AETHER: Ultimate City Simulation (Traffic + Vegetation + Physics)")
        self.canvas = tk.Canvas(root, width=WINDOW_WIDTH, height=WINDOW_HEIGHT, bg="black")
        self.canvas.pack()
        
        # Camera
        self.angle = 0.6
        self.scale = 20
        self.center_x = WINDOW_WIDTH / 2
        self.center_y = WINDOW_HEIGHT / 2 + 180
        
        # Environment Generation
        self.buildings = []
        self.trees = []
        self.cars = []
        self.birds = []
        
        self.generate_world()
        
        # Environmental Physics
        self.wind_dir = Vector3(1, 0, 0)
        self.wind_speed = 0.0
        self.last_wind_update = time.time()
        
        # Drone State
        self.drone_pos = Vector3(0, -60, 0) 
        self.drone_target = None
        self.temp_waypoint = None 
        self.state = "IDLE" 
        self.battery = 100.0
        
        # UI
        self.hud_label = self.canvas.create_text(50, 50, text="SYSTEM INITIALIZED", fill="#00ff00", font=("Courier", 12), anchor="nw")
        self.alert_label = self.canvas.create_text(WINDOW_WIDTH/2, 80, text="", fill="red", font=("Courier", 14, "bold"), anchor="n")
        
        # Inputs
        root.bind("<Left>", lambda e: self.rotate(-0.1))
        root.bind("<Right>", lambda e: self.rotate(0.1))
        self.canvas.bind("<Button-1>", self.handle_click)
        
        self.animate()

    def generate_world(self):
        # 1. Buildings
        for _ in range(BUILDING_COUNT):
            x = random.randint(-GRID_SIZE, GRID_SIZE) * 2
            z = random.randint(-GRID_SIZE, GRID_SIZE) * 2
            height = random.randint(5, 14)
            self.buildings.append({'x': x, 'z': z, 'w': 1.6, 'd': 1.6, 'h': height, 'type': 'bldg'})

        # 2. Trees (Vegetation)
        for _ in range(TREE_COUNT):
            x = random.randint(-GRID_SIZE, GRID_SIZE) * 2
            z = random.randint(-GRID_SIZE, GRID_SIZE) * 2
            # Ensure trees don't spawn inside buildings
            collision = False
            for b in self.buildings:
                if abs(b['x'] - x) < 2 and abs(b['z'] - z) < 2: collision = True
            
            if not collision:
                height = random.randint(2, 5) # Trees are shorter
                self.trees.append({'x': x, 'z': z, 'w': 0.8, 'd': 0.8, 'h': height, 'type': 'tree'})

        # 3. Cars (Traffic)
        for _ in range(CAR_COUNT):
            # Cars spawn on grid lines (roads)
            axis = random.choice(['x', 'z'])
            x = random.randint(-GRID_SIZE, GRID_SIZE) * 2
            z = random.randint(-GRID_SIZE, GRID_SIZE) * 2
            speed = random.choice([-0.3, 0.3])
            self.cars.append({'x': x, 'z': z, 'axis': axis, 'speed': speed})

        # 4. Birds
        for _ in range(BIRD_COUNT):
            pos = Vector3(random.randint(-30, 30), random.randint(-15, -5), random.randint(-30, 30))
            vel = Vector3(random.uniform(-0.4, 0.4), random.uniform(-0.05, 0.05), random.uniform(-0.4, 0.4))
            self.birds.append({'pos': pos, 'vel': vel})

    def rotate(self, delta):
        self.angle += delta

    def project(self, x, y, z):
        rx = x * math.cos(self.angle) - z * math.sin(self.angle)
        rz = x * math.sin(self.angle) + z * math.cos(self.angle)
        screen_x = self.center_x + (rx * self.scale)
        screen_y = self.center_y + (y * self.scale) - (rz * self.scale * 0.5)
        return screen_x, screen_y

    def handle_click(self, event):
        mx, my = event.x, event.y
        closest_dist = float('inf')
        closest_idx = -1
        
        for i, b in enumerate(self.buildings):
            bx, by = self.project(b['x'], 0, b['z'])
            dist = math.sqrt((bx - mx)**2 + (by - my)**2)
            if dist < 60 and dist < closest_dist:
                closest_dist = dist
                closest_idx = i
        
        if closest_idx != -1:
            target_b = self.buildings[closest_idx]
            self.drone_target = Vector3(target_b['x'], -target_b['h'] - 2.5, target_b['z'])
            self.temp_waypoint = None
            self.state = "MOVING"
            self.canvas.itemconfig(self.hud_label, text=f"NAVIGATING TO BLDG #{closest_idx}")

    def check_obstacle_collision(self, next_pos):
        # Checks collisions with BOTH Buildings and Trees
        radius = 0.8
        
        # Check Buildings & Trees
        for obj in self.buildings + self.trees:
            if (obj['x'] - obj['w'] - radius < next_pos.x < obj['x'] + obj['w'] + radius) and \
               (obj['z'] - obj['d'] - radius < next_pos.z < obj['z'] + obj['d'] + radius):
                
                roof_y = -obj['h']
                if next_pos.y > roof_y: 
                    return obj 
        return None

    def update_physics(self):
        # 1. Update Wind
        if time.time() - self.last_wind_update > 3:
            self.wind_speed = random.uniform(0.0, 0.2)
            self.wind_dir.x = math.sin(time.time())
            self.wind_dir.z = math.cos(time.time())
            self.last_wind_update = time.time()

        # 2. Update Birds & Alert
        closest_bird_dist = 999
        for bird in self.birds:
            bird['pos'].x += bird['vel'].x; bird['pos'].y += bird['vel'].y; bird['pos'].z += bird['vel'].z
            if abs(bird['pos'].x) > GRID_SIZE*3: bird['vel'].x *= -1
            if abs(bird['pos'].z) > GRID_SIZE*3: bird['vel'].z *= -1
            
            dx = bird['pos'].x - self.drone_pos.x
            dy = bird['pos'].y - self.drone_pos.y
            dz = bird['pos'].z - self.drone_pos.z
            dist = math.sqrt(dx*dx + dy*dy + dz*dz)
            if dist < closest_bird_dist: closest_bird_dist = dist
            if dist < 1.5: # Collision bump
                self.drone_pos.x -= dx * 0.2
                self.drone_pos.z -= dz * 0.2

        if closest_bird_dist < 4.0: self.canvas.itemconfig(self.alert_label, text="⚠️ BIO-HAZARD (BIRD) NEARBY")
        else: self.canvas.itemconfig(self.alert_label, text="")

        # 3. Update Cars (Traffic)
        for car in self.cars:
            if car['axis'] == 'x':
                car['x'] += car['speed']
                if car['x'] > GRID_SIZE*2: car['x'] = -GRID_SIZE*2
                if car['x'] < -GRID_SIZE*2: car['x'] = GRID_SIZE*2
            else:
                car['z'] += car['speed']
                if car['z'] > GRID_SIZE*2: car['z'] = -GRID_SIZE*2
                if car['z'] < -GRID_SIZE*2: car['z'] = GRID_SIZE*2

    def update_navigation(self):
        if not self.drone_target: return

        active_target = self.temp_waypoint if self.temp_waypoint else self.drone_target
        dx, dy, dz = active_target.x - self.drone_pos.x, active_target.y - self.drone_pos.y, active_target.z - self.drone_pos.z
        dist = math.sqrt(dx*dx + dy*dy + dz*dz)
        
        if dist < 0.5:
            if self.temp_waypoint:
                self.temp_waypoint = None
            else:
                self.drone_target = None
                self.canvas.itemconfig(self.hud_label, text="STATUS: DELIVERED")
            return

        vx, vy, vz = dx/dist * 0.4, dy/dist * 0.4, dz/dist * 0.4
        vx += self.wind_dir.x * self.wind_speed; vz += self.wind_dir.z * self.wind_speed

        next_pos = Vector3(self.drone_pos.x + vx*8, self.drone_pos.y + vy*8, self.drone_pos.z + vz*8)
        obstacle = self.check_obstacle_collision(next_pos)
        
        if obstacle and not self.temp_waypoint:
            roof_height = -obstacle['h']
            self.state = "AVOIDING OBSTACLE"
            self.canvas.itemconfig(self.hud_label, text=f"OBSTACLE ({obstacle['type'].upper()}) DETECTED: CLIMBING")
            self.temp_waypoint = Vector3(obstacle['x'], roof_height - 3, obstacle['z'])
        else:
            self.drone_pos.x += vx; self.drone_pos.y += vy; self.drone_pos.z += vz
            self.battery -= 0.01

    def draw_cube(self, x, z, w, d, h, color):
        y_b, y_t = 0, -h
        pts = [self.project(x-w, y_b, z-d), self.project(x+w, y_b, z-d), 
               self.project(x+w, y_b, z+d), self.project(x-w, y_b, z+d),
               self.project(x-w, y_t, z-d), self.project(x+w, y_t, z-d), 
               self.project(x+w, y_t, z+d), self.project(x-w, y_t, z+d)]
        edges = [(0,1), (1,2), (2,3), (3,0), (4,5), (5,6), (6,7), (7,4), (0,4), (1,5), (2,6), (3,7)]
        for s, e in edges: self.canvas.create_line(pts[s][0], pts[s][1], pts[e][0], pts[e][1], fill=color)

    def draw_pyramid(self, x, z, h, color): # For Trees
        w = 1.0
        top = self.project(x, -h, z)
        base = [self.project(x-w, 0, z-w), self.project(x+w, 0, z-w), 
                self.project(x+w, 0, z+w), self.project(x-w, 0, z+w)]
        for b in base: self.canvas.create_line(b[0], b[1], top[0], top[1], fill=color) # Sides
        for i in range(4): self.canvas.create_line(base[i][0], base[i][1], base[(i+1)%4][0], base[(i+1)%4][1], fill=color) # Base

    def draw_car(self, x, z, color):
        w, l = 0.5, 0.8 # Width, Length
        self.draw_cube(x, z, w, l, 0.5, color)

    def draw_bird(self, bird):
        x, y, z = bird['pos'].x, bird['pos'].y, bird['pos'].z
        p = self.project(x, y, z)
        wing = 3 if int(time.time()*15)%2==0 else 6
        self.canvas.create_line(p[0]-wing, p[1], p[0]+wing, p[1], fill="orange", width=2)
        self.canvas.create_line(p[0], p[1]-2, p[0], p[1]+2, fill="yellow", width=2)

    def animate(self):
        self.canvas.delete("all")
        self.update_physics()
        self.update_navigation()
        
        # Wind Lines
        for i in range(10):
             off = (time.time()*20 + i*40) % WINDOW_WIDTH
             sy = (WINDOW_HEIGHT/2) + math.sin(off/50)*30
             if self.wind_speed > 0.05: self.canvas.create_line(off, sy, off+30, sy, fill="#333", dash=(2,4))

        # Grid
        gr = GRID_SIZE + 2
        for i in range(-gr, gr+1):
            p1, p2 = self.project(i*2, 0, -gr*2), self.project(i*2, 0, gr*2)
            self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill="#222")
            p3, p4 = self.project(-gr*2, 0, i*2), self.project(gr*2, 0, i*2)
            self.canvas.create_line(p3[0], p3[1], p4[0], p4[1], fill="#222")

        # Render World Objects
        for b in self.buildings: self.draw_cube(b['x'], b['z'], b['w'], b['d'], b['h'], "#0066ff") # Blue Bldgs
        for t in self.trees: self.draw_pyramid(t['x'], t['z'], t['h'], "#00ff66") # Green Trees
        for c in self.cars: self.draw_car(c['x'], c['z'], "#ff00ff") # Magenta Cars
        for b in self.birds: self.draw_bird(b) # Yellow Birds

        # Drone & UI
        self.draw_cube(self.drone_pos.x, self.drone_pos.z, 0.6, 0.6, 0.6, "#ff0000")
        d_scr = self.project(self.drone_pos.x, self.drone_pos.y, self.drone_pos.z)
        g_scr = self.project(self.drone_pos.x, 0, self.drone_pos.z)
        self.canvas.create_line(d_scr[0], d_scr[1], g_scr[0], g_scr[1], fill="red", dash=(2,2))
        
        hud_txt = f"ALT: {abs(int(self.drone_pos.y))}m | BAT: {int(self.battery)}% | WIND: {int(self.wind_speed*100)} km/h"
        self.canvas.create_text(WINDOW_WIDTH-20, 30, text=hud_txt, fill="cyan", font=("Arial", 10), anchor="e")

        self.root.after(30, self.animate)

if __name__ == "__main__":
    root = tk.Tk()
    sim = LidarSim(root)
    root.mainloop()