import pygame

pygame.init()
displayHeight = 600
displayWidth = 800
gravity = 9.8
Vy = 5.0
Vx = -3.0
isDragging = False
prevMousePosition = pygame.mouse.get_pos()
screen = pygame.display.set_mode((displayWidth, displayHeight))
ballPositionX = displayWidth / 2
ballPositionY = displayHeight / 2
ball = pygame.draw.circle(screen, pygame.Color("#CC0A0A"), (ballPositionX, ballPositionY), 20)
bgColor = pygame.Color("#FFFFFF")
screen.fill(bgColor)
clock = pygame.time.Clock()
dt = 0
running = True

while running:
    dt = clock.tick(60) / 1000
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Calculate squared distance
            distance_sq = (event.pos[0] - ballPositionX)**2 + (event.pos[1] - ballPositionY)**2
            
            # Check if distance is less than radius squared (20*20 = 400)
            if distance_sq <= 400:
                isDragging = True
                prevMousePosition = pygame.mouse.get_pos()
        if event.type == pygame.MOUSEMOTION and isDragging == True:
            # 1. Update ball position to current mouse position (simpler for drag)
                ballPositionX = event.pos[0]
                ballPositionY = event.pos[1]
            # 2. Update the "memory" for the NEXT FRAME's toss velocity calculation
                prevMousePosition = event.pos    
                Vx = 0 # Ensure no physics movement
                Vy = 0
        if event.type == pygame.MOUSEBUTTONUP and isDragging == True:
            currentMousePosition = pygame.mouse.get_pos()
            tossFactor = 5
            Deltax = currentMousePosition[0] - prevMousePosition[0]
            Deltay = currentMousePosition[1] - prevMousePosition[1]
            Vx = tossFactor * Deltax / (dt)
            Vy = tossFactor * Deltay / (dt)
            isDragging = False

    if isDragging is not True:
        Vy = Vy + gravity * (dt)
        ballPositionX = ballPositionX + Vx * (dt)
        # Check and handle Left/Right Walls
        if ballPositionX + 20 > displayWidth:
            ballPositionX = displayWidth - 20 # Correct position
            Vx = -Vx * 0.8 # Reverse and dampen velocity
        elif ballPositionX - 20 < 0:
            ballPositionX = 20 # Correct position
            Vx = -Vx * 0.8 # Reverse and dampen velocity
        ballPositionY = ballPositionY + Vy * (dt)
        if ballPositionY + 20 > displayHeight:
            ballPositionY = displayHeight - 20 # Correct position
            Vy = -Vy * 0.8 # Reverse and dampen velocity
        elif ballPositionY - 20 < 0:
            ballPositionY = 20 # Correct position
            Vy = -Vy * 0.8 # Reverse and dampen velocity

        screen.fill(bgColor)
        ball = pygame.draw.circle(screen, pygame.Color("#CC0A0A"), (ballPositionX, ballPositionY), 20)
        pygame.display.update()

