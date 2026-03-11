# 3D-BrickBreaker

### Overview

3D-BrickBreaker is a Python-based 3D implementation of the classic brick-breaking arcade game. This application was developed as a final project for a Computer Graphics course. It uses the OpenGL library to render a bounded 3D environment where players control a paddle to deflect a ball and destroy arranged layers of bricks.

### Features

* **Progressive Difficulty:** Includes three distinct levels featuring increasingly complex brick layouts and faster ball speeds.
* **Variable Brick Durability:** Bricks have different health points (1, 3, or 5 hits), requiring multiple deflections to destroy and yielding different point values.
* **Dual Camera Modes:** Players can switch between a standard fixed 3D perspective and a First-Person Camera (FPC) attached to the moving paddle.
* **Collision Detection:** Implements AABB-to-Sphere collision detection, calculating penetration depth to accurately reflect the ball off the paddle, walls, and bricks.
* **Real-time HUD:** Displays current score, active level, remaining lives, and the current camera mode.

### How to Play

Use your keyboard to control the paddle and manage the game state.

* **Spacebar:** Start the game from the pre-game screen.
* **Arrow Keys:** Move the paddle along the X and Y axes (Up, Down, Left, Right).
* **F:** Toggle between the Standard and First-Person Camera modes.
* **P:** Pause and unpause the game.
* **R:** Restart the game after winning or losing.
* **C:** Cheat key to instantly destroy remaining bricks and advance to the next level.

### How to Run

To run this game on your system, you cannot run the Python file in isolation.

1. Download and extract the entire project zip file.
2. Ensure that the included `OpenGL` folder and all associated files remain in the exact same directory structure as the extracted archive.
3. Run the main script (`game-file.py`) using Python.
