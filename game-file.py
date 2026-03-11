from math import sqrt
import time
import random

from OpenGL.GL import (
    glColor3f, glMatrixMode, glPushMatrix, glLoadIdentity, glPopMatrix,
    glRasterPos2f, glTranslatef, glBegin,
    glVertex3f, glEnd, glClear, glViewport, glClearColor, glEnable,
    glDepthFunc,
    GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT, GL_DEPTH_TEST, GL_LESS,
    GL_MODELVIEW, GL_PROJECTION,
    GL_QUADS
)
from OpenGL.GLU import (
    gluOrtho2D, gluNewQuadric, gluSphere, gluPerspective, gluLookAt
)
from OpenGL.GLUT import (
    glutBitmapCharacter,  glutPostRedisplay, glutInit,
    glutInitDisplayMode, glutInitWindowSize, glutInitWindowPosition,
    glutCreateWindow, glutDisplayFunc, glutKeyboardFunc, glutSpecialFunc,
    glutMouseFunc, glutIdleFunc, glutMainLoop, glutSwapBuffers,
    glutKeyboardUpFunc, glutSpecialUpFunc,
    GLUT_DOUBLE, GLUT_RGB, GLUT_DEPTH,
    GLUT_KEY_LEFT, GLUT_KEY_RIGHT, GLUT_KEY_UP, GLUT_KEY_DOWN,
    GLUT_BITMAP_8_BY_13
)

windowW, windowH = 1000, 720
aspect = windowW / windowH

roomW, roomH, roomD = 36.0, 24.0, 46.0
halfW, halfH, halfD = roomW/2, roomH/2, roomD/2
frontZ, backZ = halfD, -halfD

paddleW, paddleH, paddleD = 8.0, 3.0, 1.0
paddleSpeed = 26.0

ballR = 0.7
levelSpeeds = {1: 15.0, 2: 25.0, 3: 40.0}

brickW, brickH, brickD = 3.2, 1.8, 1.0
gridCols, gridRows = 5, 3
brickGapX, brickGapY = 0.8, 0.8

scoreValues = {1: 10, 3: 30, 5: 50}

statePre = 'pregame'
stateRun = 'running'
statePause = 'paused'
stateTrans = 'transition'
stateOver = 'gameover'
stateWin = 'win'
cheat = False
camMode = 'normal'

class Vec3:
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x, self.y, self.z = float(x), float(y), float(z)

    def set(self, x, y, z):
        self.x, self.y, self.z = float(x), float(y), float(z)

    def copy(self):
        return Vec3(self.x, self.y, self.z)

    def addScaled(self, v, s):
        self.x += v.x * s
        self.y += v.y * s
        self.z += v.z * s

    def length(self):
        return sqrt(self.x**2 + self.y**2 + self.z**2)

    def normalize(self):
        L = self.length()
        if L > 1e-8:
            self.x, self.y, self.z = self.x/L, self.y/L, self.z/L
        return self


class Ball:
    def __init__(self):
        self.pos = Vec3(0, 0, frontZ - 4.0)
        self.vel = Vec3(0, 0, -1).normalize()
        self.speed = levelSpeeds[1]


class Paddle:
    def __init__(self):
        self.pos = Vec3(0.0, 0.0, frontZ - paddleD*0.5 - 0.02)


class Brick:
    def __init__(self, cx, cy, cz, hp):
        self.cx, self.cy, self.cz = float(cx), float(cy), float(cz)
        self.hp = self.maxHp = hp
        self.alive = True
quadric = None
ball = Ball()
paddle = Paddle()
bricks = []
level = 1
score = 0
lives = 3
state = statePre
transText = ''
transTimer = 0.0
lastTime = time.time()
keysDown = set()

def arrangeLayer(zCenter, hpLayout):
    global bricks

    # starting from top left 
    startX = -((gridCols-1)*(brickW+brickGapX))/2.0
    startY = -((gridRows-1)*(brickH+brickGapY))/2.0
    idx = 0
    for r in range(gridRows):  # 3 rows 
        for c in range(gridCols):  # 5 columns 
            cx = startX + c*(brickW+brickGapX)
            cy = startY + r*(brickH+brickGapY)
            hp = hpLayout[idx]
            idx += 1
            bricks.append(Brick(cx, cy, zCenter, hp))

def setupLevel(n): # n is level number 
    global bricks, ball, paddle, level
    level = n
    bricks = []
    zFar = -halfD + 10.0 
    zNear = zFar + 4.0
    if n == 1:
        arrangeLayer(zFar, [1]*15)
    elif n == 2:
        layout = [3,1,1,3,1,1,3,1,1,3,1,3,1,1,3]
        arrangeLayer(zFar, layout)
    elif n == 3:
        layer1 = [5,3,1,3,5,3,1,5,1,3,5,3,1,3,5]
        layer2 = [1,3,5,3,1,5,3,1,3,5,1,5,3,5,1]
        arrangeLayer(zNear, layer1)
        arrangeLayer(zFar, layer2)
    paddle = Paddle()
    ball = Ball()
    ball.speed = levelSpeeds[n]
    initX = random.uniform(-0.6, 0.6)
    initY= random.uniform(-0.4, 0.4)
    ball.vel = Vec3(initX, initY, -1.0).normalize()


# used to keep paddle within bnds and for accurate CD
def capVal(val, minVal, maxVal):  # val = 23, ragne (7-19) so capped at upper limit or 19
    return max(minVal, min(maxVal, val))

def reflectComp(axis, vel):
    # for reversing coordinates
    if axis == 'x':
        vel.x = -vel.x
    elif axis == 'y':
        vel.y = -vel.y
    else:
        vel.z = -vel.z

# h = half size, c = ball's coordinates, b= brick or paddle's , q = closets points to check collision
def sphereAabbColl(cx, cy, cz, r, bx, by, bz, hx, hy, hz):
    qx = capVal(cx, bx-hx, bx+hx)
    qy = capVal(cy, by-hy, by+hy)
    qz = capVal(cz, bz-hz, bz+hz)
    dx, dy, dz = cx - qx, cy - qy, cz - qz
    dist2 = dx*dx + dy*dy + dz*dz
    if dist2 > r*r:  #checking if the distance is greateer than radius, if yes: collided 
        return (False, None)
    # if ball collided, checks which dir
    # penetration depth of x, y, z
    px = (hx + r) -abs(cx - bx)
    py = (hy + r)- abs(cy - by)
    pz = (hz + r) -  abs(cz - bz)
    minP = min(px, py, pz)
    if minP == px:
        return (True, 'x')
    elif minP == py:
        return (True, 'y')
    else:
        return (True, 'z')

def update(deltaT):
    global state, score, level, transText, transTimer, cheat, lives
    if state != stateRun:
        return
    # movifn the ball by scaling the vector 
    ball.pos.addScaled(ball.vel, ball.speed * deltaT)


    # wall collision
    if ball.pos.x - ballR <= -halfW: #hit left wall
        ball.pos.x = -halfW + ballR
        ball.vel.x = abs(ball.vel.x) # reversing direction
    elif ball.pos.x + ballR >= halfW: #hit right wall
        ball.pos.x = halfW - ballR
        ball.vel.x = -abs(ball.vel.x)
    if ball.pos.y - ballR <= -halfH: 
        ball.pos.y = -halfH + ballR
        ball.vel.y = abs(ball.vel.y)
    elif ball.pos.y + ballR >= halfH:
        ball.pos.y = halfH - ballR
        ball.vel.y = -abs(ball.vel.y)
    # z is being checked for the back wall only
    if ball.pos.z - ballR <= backZ:
        ball.pos.z = backZ + ballR
        ball.vel.z = abs(ball.vel.z)
    
    # checkng paddle collisions
    frontPlaneZ = frontZ
    paddleZ = paddle.pos.z
    if ball.pos.z + ballR >= paddleZ - paddleD/2:
        hit, axis = sphereAabbColl(
            ball.pos.x, ball.pos.y, ball.pos.z, ballR,
            paddle.pos.x, paddle.pos.y, paddle.pos.z,
            paddleW/2, paddleH/2, paddleD/2
        )
        if hit:
            offsetX = (ball.pos.x - paddle.pos.x) / (paddleW/2)
            offsetY = (ball.pos.y - paddle.pos.y) / (paddleH/2)
            ball.vel.z = -abs(ball.vel.z)
            ball.vel.x += 0.45* offsetX  # slight tweak in direction  
            ball.vel.y += 0.35* offsetY
            ball.vel.normalize()   # normalizing is donw for unit vector 
            ball.pos.z = paddle.pos.z - paddleD/2 - ballR - 0.02
        else:
            if ball.pos.z - ballR >= frontPlaneZ:  # ball slips out the front wall 
                lives -= 1
                if lives <= 0:
                    state = stateOver
                else:
                    # randomizing ball's posiiton
                    ball.pos = Vec3(0, 0, frontZ - 4.0)
                    ball.vel = Vec3(random.uniform(-0.6, 0.6), random.uniform(-0.4, 0.4), -1.0).normalize()
                return
            
    # checkign brick collison
    hasBeenHit = False # to check whether tha brick;s been hit (for strng brcks)
    toRemove = []
    for b in bricks:
        if not b.alive:
            continue
        hit, axis = sphereAabbColl(
            ball.pos.x, ball.pos.y, ball.pos.z, ballR,
            b.cx, b.cy, b.cz,
            brickW/2, brickH/2, brickD/2
        )
        if hit:
            if b.maxHp == 1:
                b.alive = False
                toRemove.append(b)
                score += scoreValues[1]  #level based scoring
            else:
                if not hasBeenHit and axis is not None:
                    reflectComp(axis, ball.vel)
                    ball.vel.normalize()
                    hasBeenHit = True
                b.hp -= 1 # reducing health point
                if b.hp <= 0:
                    b.alive = False
                    toRemove.append(b)
                    score += scoreValues[b.maxHp]
    # removing broken brcks
    if toRemove:
        for b in toRemove:
            if b in bricks:
                bricks.remove(b)

    # checks if all bricks been broken
    if all(not b.alive for b in bricks) or cheat:
        if cheat:
            cheat = False
        if level < 3:
            state = stateTrans
            transText = f"Level {level+1} Begins"
            transTimer = 2.0
        else:
            state = stateWin

def setupCam():
    if camMode == "fpc":
        setupFpCam()
    else:
        glViewport(0, 0, windowW, windowH)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(75.0, aspect, 0.1, 200.0)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        camX, camY, camZ = 15.0, 8.0, frontZ + 25.0
        gluLookAt(camX, camY, camZ, -2.0, 0.0, 0.0, 0.0, 1.0, 0.0)

def setupFpCam():
    glViewport(0, 0, windowW, windowH)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(90.0, aspect, 0.1, 200.0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    camOffsetZ = -paddleD/2 - 1.5
    camX = paddle.pos.x
    camY = paddle.pos.y + 0.5
    camZ = paddle.pos.z + camOffsetZ
    targetX = paddle.pos.x
    targetY = 0.0
    targetZ = -halfD + 15.0
    gluLookAt(camX, camY, camZ, targetX, targetY, targetZ, 0.0, 1.0, 0.0)

def drawBox(cx, cy, cz, hx, hy, hz):
    x0, x1 = cx - hx, cx + hx
    y0, y1 = cy - hy, cy + hy
    z0, z1 = cz - hz, cz + hz
    glBegin(GL_QUADS)
    glVertex3f(x0,y0,z1); glVertex3f(x1,y0,z1); glVertex3f(x1,y1,z1); glVertex3f(x0,y1,z1)
    glVertex3f(x1,y0,z0); glVertex3f(x0,y0,z0); glVertex3f(x0,y1,z0); glVertex3f(x1,y1,z0)
    glVertex3f(x0,y0,z0); glVertex3f(x0,y0,z1); glVertex3f(x0,y1,z1); glVertex3f(x0,y1,z0)
    glVertex3f(x1,y0,z1); glVertex3f(x1,y0,z0); glVertex3f(x1,y1,z0); glVertex3f(x1,y1,z1)
    glVertex3f(x0,y0,z0); glVertex3f(x1,y0,z0); glVertex3f(x1,y0,z1); glVertex3f(x0,y0,z1)
    glVertex3f(x0,y1,z1); glVertex3f(x1,y1,z1); glVertex3f(x1,y1,z0); glVertex3f(x0,y1,z0)
    glEnd()

def drawRoom():
    x0, x1 = -halfW, halfW
    y0, y1 = -halfH, halfH
    z0, z1 = backZ, frontZ
    glBegin(GL_QUADS)
    glColor3f(0.5, 0.8, 0.8)
    glVertex3f(x0,y0,z0); glVertex3f(x1,y0,z0); glVertex3f(x1,y1,z0); glVertex3f(x0,y1,z0)
    glColor3f(0.8, 0.3, 0.3)
    glVertex3f(x0,y0,z0); glVertex3f(x0,y0,z1); glVertex3f(x0,y1,z1); glVertex3f(x0,y1,z0)
    glColor3f(0.8, 0.3, 0.3)
    glVertex3f(x1,y0,z1); glVertex3f(x1,y0,z0); glVertex3f(x1,y1,z0); glVertex3f(x1,y1,z1)
    glColor3f(0.5, 0.5, 0.5)
    glVertex3f(x0,y0,z0); glVertex3f(x1,y0,z0); glVertex3f(x1,y0,z1); glVertex3f(x0,y0,z1)
    glColor3f(0.5, 0.5, 0.5)
    glVertex3f(x0,y1,z1); glVertex3f(x1,y1,z1); glVertex3f(x1,y1,z0); glVertex3f(x0,y1,z0)
    glEnd()

def drawBrick(b: Brick):
    if b.maxHp == 1:
        baseR, baseG, baseB = 0.2, 0.8, 0.3
    elif b.maxHp == 3:
        baseR, baseG, baseB = 0.98, 0.6, 0.15
    else:
        baseR, baseG, baseB = 0.9, 0.2, 0.2
    x0, x1 = b.cx - brickW/2, b.cx + brickW/2
    y0, y1 = b.cy - brickH/2, b.cy + brickH/2
    z0, z1 = b.cz - brickD/2, b.cz + brickD/2
    glBegin(GL_QUADS)
    glColor3f(baseR * 1.0, baseG * 1.0, baseB * 1.0)
    glVertex3f(x0,y0,z1); glVertex3f(x1,y0,z1); glVertex3f(x1,y1,z1); glVertex3f(x0,y1,z1)
    glColor3f(baseR * 0.4, baseG * 0.4, baseB * 0.4)
    glVertex3f(x1,y0,z0); glVertex3f(x0,y0,z0); glVertex3f(x0,y1,z0); glVertex3f(x1,y1,z0)
    glColor3f(baseR * 0.6, baseG * 0.6, baseB * 0.6)
    glVertex3f(x0,y0,z0); glVertex3f(x0,y0,z1); glVertex3f(x0,y1,z1); glVertex3f(x0,y1,z0)
    glColor3f(baseR * 0.6, baseG * 0.6, baseB * 0.6)
    glVertex3f(x1,y0,z1); glVertex3f(x1,y0,z0); glVertex3f(x1,y1,z0); glVertex3f(x1,y1,z1)
    glColor3f(baseR * 0.5, baseG * 0.5, baseB * 0.5)
    glVertex3f(x0,y0,z0); glVertex3f(x1,y0,z0); glVertex3f(x1,y0,z1); glVertex3f(x0,y0,z1)
    glColor3f(baseR * 0.9, baseG * 0.9, baseB * 0.9)
    glVertex3f(x0,y1,z1); glVertex3f(x1,y1,z1); glVertex3f(x1,y1,z0); glVertex3f(x0,y1,z0)
    glEnd()

def drawPaddle():
    glColor3f(0.3, 0.6, 1.0)
    drawBox(paddle.pos.x, paddle.pos.y, paddle.pos.z, paddleW/2, paddleH/2, paddleD/2)

def drawBall():
    glColor3f(1.0, 1.0, 1.0)
    glPushMatrix()
    glTranslatef(ball.pos.x, ball.pos.y, ball.pos.z)
    gluSphere(quadric, ballR, 20, 16)
    glPopMatrix()

def drawText(x, y, text):
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, windowW, 0, windowH)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(GLUT_BITMAP_8_BY_13, ord(ch))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def drawHud():
    drawText(12, windowH - 24, f"Score: {score}")
    drawText(12, windowH - 44, f"Level {level}")
    drawText(12, windowH - 64, f"Lives: {lives}")
    drawText(12, windowH - 84, f"Camera: {camMode.upper()}")
    if state == statePre:
        drawText(windowW/2 - 90, windowH/2 + 10, "Press Space to Start")
    elif state == statePause:
        drawText(windowW/2 - 30, windowH/2, "Paused")
    elif state == stateTrans:
        drawText(windowW/2 - 60, windowH/2, transText)
    elif state == stateOver:
        drawText(windowW/2 - 40, windowH/2 + 10, "Game Over")
        drawText(windowW/2 - 80, windowH/2 - 12, "Press R to Restart")
    elif state == stateWin:
        drawText(windowW/2 - 40, windowH/2 + 10, "You Win!")
        drawText(windowW/2 - 80, windowH/2 - 12, "Press R to Restart")

def drawShapes():
    drawRoom()
    for b in bricks:
        if b.alive:
            drawBrick(b)
    drawBall()
    drawPaddle()

def keyListener(key, x, y):
    global state, level, score, cheat, lives, camMode
    if key in (b'p', b'P'):
        if state == stateRun:
            state = statePause
        elif state == statePause:
            state = stateRun
    elif key == b' ':
        if state == statePre:
            state = stateRun
    elif key in (b'r', b'R'):
        if state in (stateOver, stateWin):
            level = 1
            score = 0
            lives = 3
            setupLevel(level)
            state = statePre
    elif key in (b'c', b'C'):
        cheat = True
    elif key in (b'f', b'F'):
        camMode = 'fpc' if camMode == 'normal' else 'normal'
    keysDown.add(key)

def keyUpListener(key, x, y):
    if key in keysDown:
        keysDown.remove(key)

def specialKeyListener(key, x, y):
    keysDown.add(key)

def specialKeyUpListener(key, x, y):
    if key in keysDown:
        keysDown.remove(key)

def mouseListener(button, stateBtn, x, y):
    pass

def idle():
    global lastTime, state, transTimer, level
    now = time.time()
    dt = min(0.033, max(0.0, now - lastTime)) # delta time
    lastTime = now
    if state == stateTrans:
        transTimer -= dt
        if transTimer <= 0.0:
            setupLevel(level + 1)
            state = stateRun
    elif state == stateRun:
        if GLUT_KEY_LEFT in keysDown:
            paddle.pos.x -= paddleSpeed*dt
        if GLUT_KEY_RIGHT in keysDown:
            paddle.pos.x += paddleSpeed*dt
        if GLUT_KEY_UP in keysDown:
            paddle.pos.y += paddleSpeed*dt
        if GLUT_KEY_DOWN in keysDown:
            paddle.pos.y -= paddleSpeed*dt
        paddle.pos.x = capVal(paddle.pos.x, -halfW + paddleW/2, halfW - paddleW/2)
        paddle.pos.y = capVal(paddle.pos.y, -halfH + paddleH/2, halfH - paddleH/2)
        update(dt)
    glutPostRedisplay()

def showScreen():
    glClearColor(0.02, 0.02, 0.04, 1.0)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    setupCam()
    drawShapes()
    drawHud()
    glutSwapBuffers()

def main():
    global quadric
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(windowW, windowH)
    glutInitWindowPosition(80, 40)
    glutCreateWindow(b"3D Brick Breaker")
    glEnable(GL_DEPTH_TEST)
    glDepthFunc(GL_LESS)
    quadric = gluNewQuadric()
    setupLevel(1)
    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyListener)
    glutKeyboardUpFunc(keyUpListener)
    glutSpecialFunc(specialKeyListener)
    glutSpecialUpFunc(specialKeyUpListener)
    glutMouseFunc(mouseListener)
    glutIdleFunc(idle)
    glutMainLoop()

if __name__ == '__main__':
    main()
