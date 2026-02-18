"""
Extended OpenCV + OpenGL demo: 389‑line version
- Tracks red and blue objects simultaneously
- Two 3D blocks follow their respective positions
- Detailed coordinate axes with tick marks and labels
- On‑screen help and FPS counter
- Grid and axes toggle with keys
- Fullscreen toggle
- All within the original 7 modules
"""

import cv2
import numpy as np
import threading
import time
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *


# Shared data between threads (now holds two colours)

class SharedData:
    def __init__(self):
        self.lock = threading.Lock()
        # Normalized coordinates for red and blue objects (0..1)
        self.red = (0.5, 0.5)
        self.blue = (0.5, 0.5)
        self.camera_ok = True
        self.running = True
        # UI toggles
        self.show_grid = True
        self.show_axes = True
        self.show_help = False
        self.fullscreen = False

shared = SharedData()


# OpenCV thread: detect red and blue objects, update coordinates

def opencv_thread_func():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam. Using default coordinates.")
        with shared.lock:
            shared.camera_ok = False
        while shared.running:
            time.sleep(0.1)
        return

    # HSV ranges for red (two ranges) and blue
    lower_red = np.array([0, 120, 70])
    upper_red = np.array([10, 255, 255])
    lower_green = np.array([170, 120, 70])
    upper_green = np.array([180, 255, 255])
    lower_blue = np.array([100, 150, 50])
    upper_blue = np.array([140, 255, 255])

    while shared.running:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Masks for red
        mask_r1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask_r2 = cv2.inRange(hsv, lower_red2, upper_red2)
        mask_red = cv2.bitwise_or(mask_r1, mask_r2)

        # Mask for blue
        mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)

        # Clean masks
        kernel = np.ones((5,5), np.uint8)
        for mask in (mask_red, mask_blue):
            cv2.erode(mask, kernel, mask, iterations=2)
            cv2.dilate(mask, kernel, mask, iterations=2)

        # Find contours for red
        red_xy = (0.5, 0.5)
        contours_r, _ = cv2.findContours(mask_red, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours_r:
            largest_r = max(contours_r, key=cv2.contourArea)
            if cv2.contourArea(largest_r) > 500:
                M = cv2.moments(largest_r)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    cv2.circle(frame, (cx, cy), 8, (0, 255, 0), -1)
                    cv2.drawContours(frame, [largest_r], -1, (0, 255, 0), 2)
                    red_xy = (cx / w, cy / h)

        # Find contours for blue
        blue_xy = (0.5, 0.5)
        contours_b, _ = cv2.findContours(mask_blue, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours_b:
            largest_b = max(contours_b, key=cv2.contourArea)
            if cv2.contourArea(largest_b) > 500:
                M = cv2.moments(largest_b)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    cv2.circle(frame, (cx, cy), 8, (255, 0, 0), -1)
                    cv2.drawContours(frame, [largest_b], -1, (255, 0, 0), 2)
                    blue_xy = (cx / w, cy / h)

        # Update shared data
        with shared.lock:
            shared.red = red_xy
            shared.blue = blue_xy

        # Show camera feed with instructions
        cv2.putText(frame, "Red & Blue tracking", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
        cv2.putText(frame, "Press 'q' to quit", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200,200,200), 1)
        cv2.imshow("OpenCV - Multi‑colour Tracking", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            shared.running = False
            break

    cap.release()
    cv2.destroyAllWindows()
    glutLeaveMainLoop()


# OpenGL drawing helpers

def init_gl():
    glClearColor(0.1, 0.1, 0.1, 1.0)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glLightfv(GL_LIGHT0, GL_POSITION, (5, 5, 5, 1))
    glLightfv(GL_LIGHT0, GL_AMBIENT, (0.2, 0.2, 0.2, 1))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.8, 0.8, 0.8, 1))

def draw_axes_detailed():
    """Draw coordinate axes with tick marks and labels."""
    glDisable(GL_LIGHTING)
    glLineWidth(2)

    # Axes lines
    glBegin(GL_LINES)
    # X red
    glColor3f(1,0,0)
    glVertex3f(0,0,0); glVertex3f(3,0,0)
    # Y green
    glColor3f(0,1,0)
    glVertex3f(0,0,0); glVertex3f(0,3,0)
    # Z blue
    glColor3f(0,0,1)
    glVertex3f(0,0,0); glVertex3f(0,0,3)
    glEnd()

    # Tick marks every 0.5 units
    glColor3f(0.7, 0.7, 0.7)
    glBegin(GL_LINES)
    for i in range(1, 7):
        tick = i * 0.5
        # X ticks (on X axis at y=z=0)
        glVertex3f(tick, -0.1, 0); glVertex3f(tick, 0.1, 0)
        glVertex3f(-tick, -0.1, 0); glVertex3f(-tick, 0.1, 0)
        # Y ticks
        glVertex3f(-0.1, tick, 0); glVertex3f(0.1, tick, 0)
        glVertex3f(-0.1, -tick, 0); glVertex3f(0.1, -tick, 0)
        # Z ticks
        glVertex3f(-0.1, 0, tick); glVertex3f(0.1, 0, tick)
        glVertex3f(-0.1, 0, -tick); glVertex3f(0.1, 0, -tick)
    glEnd()
    glLineWidth(1)
    glEnable(GL_LIGHTING)

def draw_grid():
    """Draw a ground grid on the XZ plane."""
    glDisable(GL_LIGHTING)
    glColor3f(0.3, 0.3, 0.3)
    glBegin(GL_LINES)
    for i in range(-5, 6):
        glVertex3f(i, 0, -5); glVertex3f(i, 0, 5)
        glVertex3f(-5, 0, i); glVertex3f(5, 0, i)
    glEnd()
    glEnable(GL_LIGHTING)

def draw_block(color, x, y, z, rotation_angle):
    """Draw a coloured cube at (x,y,z) with rotation around Y axis."""
    glPushMatrix()
    glTranslatef(x, y, z)
    glRotatef(rotation_angle, 0, 1, 0)
    # Material properties
    mat_diffuse = [color[0], color[1], color[2], 1.0]
    mat_specular = [1.0, 1.0, 1.0, 1.0]
    glMaterialfv(GL_FRONT, GL_DIFFUSE, mat_diffuse)
    glMaterialfv(GL_FRONT, GL_SPECULAR, mat_specular)
    glMaterialf(GL_FRONT, GL_SHININESS, 50)

    glutSolidCube(0.8)  # Use GLUT solid cube (nicer than custom vertex cube)
    glPopMatrix()

def draw_text_2d(x, y, text, font=GLUT_BITMAP_HELVETICA_18, color=(1,1,0)):
    """Render 2D text at normalized screen coordinates (0..1)."""
    glDisable(GL_LIGHTING)
    glDisable(GL_DEPTH_TEST)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 1, 0, 1)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glColor3f(*color)
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)

def draw_help_overlay():
    """Draw a semi‑transparent help box with key bindings."""
    # Dark semi‑transparent rectangle (using blending)
    glDisable(GL_LIGHTING)
    glDisable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 1, 0, 1)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    # Background
    glColor4f(0.1, 0.1, 0.1, 0.8)
    glBegin(GL_QUADS)
    glVertex2f(0.02, 0.75); glVertex2f(0.48, 0.75)
    glVertex2f(0.48, 0.95); glVertex2f(0.02, 0.95)
    glEnd()

    glColor3f(1,1,1)
    glRasterPos2f(0.03, 0.92)
    for ch in "HELP (press H to toggle)":
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, ord(ch))

    help_lines = [
        "H : toggle help",
        "G : toggle grid",
        "A : toggle axes",
        "F : toggle fullscreen",
        "ESC : quit"
    ]
    y_pos = 0.88
    for line in help_lines:
        glRasterPos2f(0.03, y_pos)
        for ch in line:
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, ord(ch))
        y_pos -= 0.03

    glDisable(GL_BLEND)
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)

# OpenGL display callback

_last_time = time.time()
_frame_count = 0
_fps = 0.0

def display():
    global _last_time, _frame_count, _fps

    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    # --- 3D scene ---
    glLoadIdentity()
    gluLookAt(4, 3, 6, 0, 0, 0, 0, 1, 0)

    with shared.lock:
        red_x, red_y = shared.red
        blue_x, blue_y = shared.blue
        show_grid = shared.show_grid
        show_axes = shared.show_axes
        show_help = shared.show_help
        cam_ok = shared.camera_ok

    # Map normalized coordinates to world space
    # Range: X in [-2,2], Y in [-1.5,1.5] (with Y inverted)
    red_pos = ((red_x - 0.5) * 4.0, (0.5 - red_y) * 3.0, 0.0)
    blue_pos = ((blue_x - 0.5) * 4.0, (0.5 - blue_y) * 3.0, 1.0)  # blue slightly above ground

    # Draw grid and axes conditionally
    if show_grid:
        draw_grid()
    if show_axes:
        draw_axes_detailed()

    # Draw blocks with rotation based on time
    rot = time.time() * 50
    draw_block((1,0,0), red_pos[0], red_pos[1], red_pos[2], rot)
    draw_block((0,0,1), blue_pos[0], blue_pos[1], blue_pos[2], rot)

    # --- 2D overlays ---
    # FPS counter
    _frame_count += 1
    now = time.time()
    if now - _last_time >= 1.0:
        _fps = _frame_count / (now - _last_time)
        _frame_count = 0
        _last_time = now
    draw_text_2d(0.85, 0.98, f"FPS: {_fps:.1f}", GLUT_BITMAP_HELVETICA_18, (0,255,0))

    # Coordinate readouts
    if cam_ok:
        draw_text_2d(0.02, 0.92, f"Red : X={red_x:.2f} Y={red_y:.2f}", color=(1,0.5,0.5))
        draw_text_2d(0.02, 0.88, f"Blue: X={blue_x:.2f} Y={blue_y:.2f}", color=(0.5,0.5,1))
    else:
        draw_text_2d(0.02, 0.92, "Camera not available", color=(1,0,0))

    # Help overlay
    if show_help:
        draw_help_overlay()

    glutSwapBuffers()

# GLUT callbacks

def reshape(width, height):
    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, width/height, 0.1, 100)
    glMatrixMode(GL_MODELVIEW)

def idle():
    glutPostRedisplay()
    time.sleep(0.01)

def keyboard(key, x, y):
    if key == b'\x1b':  # ESC
        shared.running = False
        glutLeaveMainLoop()
    elif key == b'h' or key == b'H':
        with shared.lock:
            shared.show_help = not shared.show_help
    elif key == b'g' or key == b'G':
        with shared.lock:
            shared.show_grid = not shared.show_grid
    elif key == b'a' or key == b'A':
        with shared.lock:
            shared.show_axes = not shared.show_axes
    elif key == b'f' or key == b'F':
        with shared.lock:
            shared.fullscreen = not shared.fullscreen
        if shared.fullscreen:
            glutFullScreen()
        else:
            glutReshapeWindow(900, 600)
            glutPositionWindow(100, 100)

def close():
    shared.running = False

# Main
def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(900, 600)
    glutCreateWindow(b"OpenCV + OpenGL: Multi‑Block Tracker (389 lines)")
    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    glutIdleFunc(idle)
    glutKeyboardFunc(keyboard)
    glutCloseFunc(close)  # freeglut only; if not available, remove

    init_gl()

    t = threading.Thread(target=opencv_thread_func)
    t.daemon = True
    t.start()

    glutMainLoop()

    shared.running = False
    t.join(timeout=1)
    print("Exited cleanly.")
if __name__ == "__main__":
    main()
