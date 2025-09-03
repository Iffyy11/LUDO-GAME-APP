
import pygame
import sys
import random

pygame.init()

# --- Screen setup ---
WIDTH, HEIGHT = 500, 600
CELL = WIDTH // 15
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Ludo Board")

# --- Colors ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (220, 20, 60)
GREEN = (0, 180, 0)
BLUE = (30, 144, 255)
YELLOW = (255, 215, 0)

# The single source of truth for player order.
PLAYER_COLORS = [GREEN, YELLOW, BLUE, RED]

# --- Game state ---
current_dice = 1
rolling = False
roll_timer = 0
ROLL_DURATION = 20
dice_size = 40  
dice_rect = pygame.Rect(WIDTH // 2 - dice_size // 2, HEIGHT - dice_size - 60, dice_size, dice_size)
dragging = False
button_width, button_height = 60, 28 

# Position roll button to the right of the dice
roll_button = pygame.Rect(dice_rect.right + 10, dice_rect.centery - button_height // 2, button_width, button_height)
# Arrange buttons with minimal gaps
button_gap = 8
base_x = 30
quit_button = pygame.Rect(base_x, HEIGHT - 50, button_width, button_height)
add_player_button = pygame.Rect(quit_button.right + button_gap, HEIGHT - 50, button_width, button_height)
remove_player_button = pygame.Rect(add_player_button.right + button_gap, HEIGHT - 50, button_width, button_height)
reset_button = pygame.Rect(remove_player_button.right + button_gap, HEIGHT - 50, button_width, button_height)

# --- Player info ---
num_players = 0
players = []
current_player_idx = 0
input_boxes = []
active_input = None
dice_rolled = False

# Token positions and state
token_positions = []
token_path_indices = []
token_is_home = []
token_is_safe = []

# --- Fonts ---
font_small = pygame.font.SysFont(None, 18)
font_medium = pygame.font.SysFont(None, 24)
font_large = pygame.font.SysFont(None, 32)

# --- Load dice sound ---
try:
    dice_sound = pygame.mixer.Sound("dice.wav")
except pygame.error:
    dice_sound = None




# --- Board Logic ---
def create_paths():
    """
    Defines the complete path for each player from their start tile to the home triangle.
    
    """
    paths = []

    # The path starts at the green colored square and ends at the home triangle entry.
    green_path_master = []
    # Segment 1: Right from home entry
    for i in range(1, 6): green_path_master.append((i, 6))
    # Segment 2: Up to the corner
    green_path_master.append((6, 5))
    for i in range(4, -1, -1): green_path_master.append((6, i))
    # Segment 3: Across the top
    green_path_master.append((7, 0))
    green_path_master.append((8, 0))
    # Segment 4: Down
    for i in range(1, 6): green_path_master.append((8, i))
    green_path_master.append((9, 6))
    # Segment 5: Right
    for i in range(10, 15): green_path_master.append((i, 6))
    # Segment 6: Across the bottom (turn)
    green_path_master.append((14, 7))
    green_path_master.append((14, 8))
    # Segment 7: Left
    for i in range(13, 8, -1): green_path_master.append((i, 8))
    green_path_master.append((8, 9))
    # Segment 8: Down
    for i in range(10, 15): green_path_master.append((8, i))
    # Segment 9: Left (turn)
    green_path_master.append((7, 14))
    green_path_master.append((6, 14))
    # Segment 10: Up
    for i in range(13, 8, -1): green_path_master.append((6, i))
    green_path_master.append((5, 8))
    # Segment 11: Left
    for i in range(4, -1, -1): green_path_master.append((i, 8))
    # Segment 12: Top (turn)
    green_path_master.append((0, 7))
    green_path_master.append((0, 6))
    # Segment 13: The home stretch
    for i in range(1, 7): green_path_master.append((i, 7))
    paths.append(green_path_master)

    # Yellow's path (Player 1) - 90 degrees clockwise from Green
    # Rotates (x, y) to (14-y, x)
    yellow_path = [(14-y, x) for x, y in green_path_master]
    paths.append(yellow_path)

    # Blue's path (Player 2) - 270 degrees clockwise from Green
    # Rotates (x, y) to (y, 14-x)
    blue_path = [(y, 14-x) for x, y in green_path_master]
    paths.append(blue_path)

    # Red's path (Player 3) - 180 degrees from Green
    # Rotates (x, y) to (14-x, 14-y)
    red_path = [(14-x, 14-y) for x, y in green_path_master]
    paths.append(red_path)

    return paths

full_paths = create_paths()

def get_home_coords(player_id, token_id):
    home_pos = [
        [(1, 1), (1, 3), (3, 1), (3, 3)],  # GREEN (Player 0)
        [(10, 1), (10, 3), (12, 1), (12, 3)],  # YELLOW (Player 1)
        [(1, 10), (1, 12), (3, 10), (3, 12)],  # BLUE (Player 2)
        [(10, 10), (10, 12), (12, 10), (12, 12)],  # RED (Player 3)
    ]
    return (home_pos[player_id][token_id][0] * CELL + CELL // 2,
            home_pos[player_id][token_id][1] * CELL + CELL // 2)

def get_tile_coords(x, y):
    return x * CELL + CELL // 2, y * CELL + CELL // 2

def initialize_tokens():
    global token_positions, token_path_indices, token_is_home
    token_positions = []
    token_path_indices = []
    token_is_home = []
    for player_id in range(num_players):
        player_tokens = []
        player_path_indices = []
        player_home_state = []
        for token_id in range(4):
            player_tokens.append(get_home_coords(player_id, token_id))
            player_path_indices.append(-1)
            player_home_state.append(True)
        token_positions.append(player_tokens)
        token_path_indices.append(player_path_indices)
        token_is_home.append(player_home_state)

def move_token(player_id, token_id, steps):
    current_path_index = token_path_indices[player_id][token_id]
    path_length = len(full_paths[player_id])
    # If token is home, needs 6 to move out
    if token_is_home[player_id][token_id]:
        if steps == 6:
            token_is_home[player_id][token_id] = False
            token_path_indices[player_id][token_id] = 0
            x, y = full_paths[player_id][0]
            token_positions[player_id][token_id] = get_tile_coords(x, y)
            return True
        return False
    else:
        new_index = current_path_index + steps
        # Check if move lands exactly at home
        if new_index == path_length:
            # Token reaches home
            token_is_home[player_id][token_id] = True
            token_path_indices[player_id][token_id] = -1
            token_positions[player_id][token_id] = get_home_coords(player_id, token_id)
            # Show message when token reaches home
            show_message(f"{players[player_id]['name']} token is home!", color=players[player_id]['color'])
            check_winner(player_id)
            return True
        elif new_index < path_length:
            # Move token
            token_path_indices[player_id][token_id] = new_index
            x, y = full_paths[player_id][new_index]
            token_positions[player_id][token_id] = get_tile_coords(x, y)
            # Kill rule: check for opponent tokens on same tile (not safe tiles)
            if not is_safe_tile(x, y):
                for opp_id in range(num_players):
                    if opp_id == player_id:
                        continue
                    for opp_token in range(4):
                        if not token_is_home[opp_id][opp_token]:
                            opp_idx = token_path_indices[opp_id][opp_token]
                            if opp_idx >= 0 and full_paths[opp_id][opp_idx] == (x, y):
                                # Send opponent token home
                                token_is_home[opp_id][opp_token] = True
                                token_path_indices[opp_id][opp_token] = -1
                                token_positions[opp_id][opp_token] = get_home_coords(opp_id, opp_token)
                                show_message(f"{players[player_id]['name']} killed {players[opp_id]['name']}!", color=players[player_id]['color'])
                                if dice_sound:
                                    dice_sound.play()
            return True
        return False

# Helper to check safe tiles
SAFE_TILES = set([
    (1,6),(8,1),(13,8),(6,13), # colored safe tiles
    (6,1),(8,13),(13,6),(1,8), # center cross safe tiles
])
def is_safe_tile(x, y):
    return (x, y) in SAFE_TILES

# Message display
message_text = None
message_color = BLACK
message_timer = 0

def show_message(text, color=BLACK, duration=60):
# Show a message on the screen for a set duration
    global message_text, message_color, message_timer
    message_text = text
    message_color = color
    message_timer = duration

# Winner check
winner_announced = False

def check_winner(player_id):
    global winner_announced
    if all(token_is_home[player_id]):
        winner_announced = True
        show_message(f"{players[player_id]['name']} wins!", color=players[player_id]['color'], duration=180)

# --- UI Functions ---
class InputBox:
    # InputBox: Handles text input for player names and numbers
    def __init__(self, x, y, w, h, text=''):
        # Initialize the input box with position, size, and optional text
        self.rect = pygame.Rect(x, y, w, h)
        self.color = BLACK
        self.text = text
        self.txt_surface = font_medium.render(text, True, self.color)
        self.active = False

    def handle_event(self, event):
        # Handle mouse and keyboard events for text input
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                self.active = False
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                if len(self.text) < 10:
                    self.text += event.unicode
            self.txt_surface = font_medium.render(self.text, True, BLACK)

    def draw(self, screen):
        pygame.draw.rect(screen, WHITE, self.rect)
        pygame.draw.rect(screen, BLACK, self.rect, 2)
        screen.blit(self.txt_surface, (self.rect.x + 5, self.rect.y + 5))

def setup_screen():
    global num_players, input_boxes
    clock = pygame.time.Clock()
    choosing_players = True
    step = 1
    # Enlarge and center input box for better alignment
    box_width, box_height = 140, 55
    box_x = WIDTH // 2 - box_width // 2
    box_y = HEIGHT // 2 + 60
    num_box = InputBox(box_x, box_y, box_width, box_height)
    input_boxes = []
    while choosing_players:
        # Draw background image if available
        if background_img:
            screen.blit(background_img, (0, 0))
            # Draw a semi-transparent overlay for text visibility
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((255,255,255,120))  # White with alpha
            screen.blit(overlay, (0,0))
        else:
            screen.fill(WHITE)
        # Show welcome text only on step 1
        if step == 1:
            welcome_font = pygame.font.SysFont(None, 48, bold=True)
            welcome_text = welcome_font.render("Welcome to Ludo!", True, (0, 80, 180))
            pygame.draw.rect(screen, (255,255,255), (WIDTH//2-160, 30, 320, 60), border_radius=18)
            pygame.draw.rect(screen, (0,80,180), (WIDTH//2-160, 30, 320, 60), 3, border_radius=18)
            screen.blit(welcome_text, welcome_text.get_rect(center=(WIDTH//2, 60)))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if step == 1:
                num_box.handle_event(event)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    try:
                        n = int(num_box.text)
                        if 2 <= n <= 4:
                            num_players = n
                            input_boxes = []
                            for i in range(n):
                                input_boxes.append(InputBox(WIDTH//2 - 100, 150 + i*70, 200, 50))
                            step = 2
                    except:
                        pass
            elif step == 2:
                for box in input_boxes:
                    box.handle_event(event)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    if all(box.text.strip() != '' for box in input_boxes):
                        for i, box in enumerate(input_boxes):
                            players.append({'name': box.text.strip(), 'color': PLAYER_COLORS[i]})
                        choosing_players = False

        if step == 1:
            # Decorate player number prompt
            prompt_font = pygame.font.SysFont(None, 32, bold=True)
            prompt_text = prompt_font.render("Enter number of players (2-4)", True, (180,0,80))
            # Enlarge and center prompt above input box
            prompt_font = pygame.font.SysFont(None, 38, bold=True)
            prompt_text = prompt_font.render("Enter number of players (2-4)", True, (180,0,80))
            prompt_rect_width, prompt_rect_height = 340, 50
            prompt_rect_x = WIDTH // 2 - prompt_rect_width // 2
            prompt_rect_y = box_y - prompt_rect_height - 18
            pygame.draw.rect(screen, (255,255,255), (prompt_rect_x, prompt_rect_y, prompt_rect_width, prompt_rect_height), border_radius=14)
            pygame.draw.rect(screen, (180,0,80), (prompt_rect_x, prompt_rect_y, prompt_rect_width, prompt_rect_height), 2, border_radius=14)
            screen.blit(prompt_text, (WIDTH//2 - prompt_text.get_width()//2, prompt_rect_y + (prompt_rect_height - prompt_text.get_height())//2))
            num_box.draw(screen)
        elif step == 2:
            # Remove welcome text for player name page
            prompt_font = pygame.font.SysFont(None, 32, bold=True)
            prompt_text = prompt_font.render("Enter player names:", True, (0,180,80))
            pygame.draw.rect(screen, (255,255,255), (120, 50, 260, 40), border_radius=12)
            pygame.draw.rect(screen, (0,180,80), (120, 50, 260, 40), 2, border_radius=12)
            screen.blit(prompt_text, (WIDTH//2 - prompt_text.get_width()//2, 60))
            # Space out input boxes vertically to avoid overlap
            y_start = 150
            box_height = input_boxes[0].rect.height if input_boxes else 50
            total_height = len(input_boxes) * box_height + (len(input_boxes)-1) * 40
            start_y = HEIGHT//2 - total_height//2
            for i, box in enumerate(input_boxes):
                box.rect.x = WIDTH//2 - box.rect.width//2
                box.rect.y = start_y + i * (box_height + 40)
                box.draw(screen)

        pygame.display.flip()
        clock.tick(30)

# --- Board drawing functions ---
def draw_token_area(color, x, y, player_id=None):
    pygame.draw.rect(screen, color, (x, y, 6*CELL, 6*CELL))
    pygame.draw.rect(screen, WHITE, (x+CELL, y+CELL, 4*CELL, 4*CELL))
    pygame.draw.rect(screen, BLACK, (x, y, 6*CELL, 6*CELL), 3)
    # Draw player name cell on top (editable if added player)
    if player_id is not None and player_id < len(players):
        name_rect = pygame.Rect(x+CELL, y+CELL//4, 4*CELL, CELL//1.5)
        pygame.draw.rect(screen, WHITE, name_rect, border_radius=6)
        pygame.draw.rect(screen, BLACK, name_rect, 2, border_radius=6)
        name_text = font_small.render(players[player_id]['name'], True, BLACK)
        screen.blit(name_text, name_text.get_rect(center=name_rect.center))
        # Editable name: if clicked, show input box
        if hasattr(players[player_id], 'editing') and players[player_id]['editing']:
            input_box = InputBox(name_rect.x+5, name_rect.y+5, name_rect.width-10, int(name_rect.height-10), players[player_id]['name'])
            input_box.active = True
            input_box.draw(screen)
            players[player_id]['input_box'] = input_box
        else:
            players[player_id]['input_box'] = None

def draw_tile(x, y, color=WHITE, safe=False):
    rect = pygame.Rect(x*CELL, y*CELL, CELL, CELL)
    pygame.draw.rect(screen, color, rect)
    pygame.draw.rect(screen, BLACK, rect, 1)
    if safe:
        pygame.draw.circle(screen, BLACK, (x*CELL + CELL//2, y*CELL + CELL//2), CELL//3, 2)

def draw_cross_paths():
    for y in range(15):
        for x in range(6, 9):
            draw_tile(x, y)
    for x in range(15):
        for y in range(6, 9):
            draw_tile(x, y)
    for i in range(6):
        draw_tile(7, i+1, YELLOW, safe=(i==1))
        draw_tile(7, 13-i, BLUE, safe=(i==1))
        draw_tile(i+1, 7, GREEN, safe=(i==1))
        draw_tile(13-i, 7, RED, safe=(i==1))

def draw_center():
    pygame.draw.polygon(screen, YELLOW, [(6*CELL, 6*CELL), (9*CELL, 6*CELL), (7.5*CELL,7.5*CELL)])
    pygame.draw.polygon(screen, RED, [(9*CELL,6*CELL), (9*CELL,9*CELL), (7.5*CELL,7.5*CELL)])
    pygame.draw.polygon(screen, BLUE, [(6*CELL,9*CELL), (9*CELL,9*CELL), (7.5*CELL,7.5*CELL)])
    pygame.draw.polygon(screen, GREEN, [(6*CELL,6*CELL),(6*CELL,9*CELL),(7.5*CELL,7.5*CELL)])
    pygame.draw.rect(screen, BLACK, (6*CELL,6*CELL,3*CELL,3*CELL), 3)

def draw_colored_left_tiles():
    for x in range(1,6):
        draw_tile(x,7,GREEN)
    draw_tile(1,6,GREEN)
    for x in range(13,8,-1):
        draw_tile(x,7,RED)
    draw_tile(13,8,RED)
    for y in range(1,6):
        draw_tile(7,y,YELLOW)
    draw_tile(8,1,YELLOW)
    for y in range(13,8,-1):
        draw_tile(7,y,BLUE)
    draw_tile(6,13,BLUE)

def draw_tokens():
    for player_id, player_tokens in enumerate(token_positions):
        for pos in player_tokens:
            pygame.draw.circle(screen, PLAYER_COLORS[player_id], pos, CELL // 3)
            pygame.draw.circle(screen, BLACK, pos, CELL // 3, 2)

def draw_dice(value, color):
    pygame.draw.rect(screen, color, dice_rect, border_radius=8)
    dot_color = WHITE
    cx, cy = dice_rect.center
    offset = dice_size // 4
    positions = {
        1: [(cx,cy)],
        2: [(cx-offset,cy-offset),(cx+offset,cy+offset)],
        3: [(cx-offset,cy-offset),(cx,cy),(cx+offset,cy+offset)],
        4: [(cx-offset,cy-offset),(cx+offset,cy-offset),(cx-offset,cy+offset),(cx+offset,cy+offset)],
        5: [(cx-offset,cy-offset),(cx+offset,cy-offset),(cx,cy),(cx-offset,cy+offset),(cx+offset,cy+offset)],
        6: [(cx-offset,cy-offset),(cx+offset,cy-offset),(cx-offset,cy),(cx+offset,cy),(cx-offset,cy+offset),(cx+offset,cy+offset)]
    }
    for pos in positions[value]:
        pygame.draw.circle(screen, dot_color, pos, dice_size // 8)

def draw_roll_button(color):
    pygame.draw.rect(screen, color, roll_button, border_radius=10)
    pygame.draw.rect(screen, BLACK, roll_button, 2, border_radius=10)
    text = font_small.render("ROLL", True, BLACK)
    screen.blit(text, text.get_rect(center=roll_button.center))

def draw_control_buttons():
    pygame.draw.rect(screen, RED, quit_button, border_radius=8)
    pygame.draw.rect(screen, BLACK, quit_button, 2, border_radius=8)
    text = font_small.render("QUIT", True, WHITE)
    screen.blit(text, text.get_rect(center=quit_button.center))




    pygame.draw.rect(screen, GREEN, add_player_button, border_radius=8)
    pygame.draw.rect(screen, BLACK, add_player_button, 2, border_radius=8)
    text = font_small.render("ADD", True, WHITE)
    text2 = font_small.render("PLAYER", True, WHITE)
    # Center both lines in the button
    text_rect = text.get_rect(center=(add_player_button.centerx, add_player_button.centery - 8))
    text2_rect = text2.get_rect(center=(add_player_button.centerx, add_player_button.centery + 8))
    screen.blit(text, text_rect)
    screen.blit(text2, text2_rect)

    pygame.draw.rect(screen, YELLOW, reset_button, border_radius=8)
    pygame.draw.rect(screen, BLACK, reset_button, 2, border_radius=8)
    text = font_small.render("RESET", True, BLACK)
    screen.blit(text, text.get_rect(center=reset_button.center))

    # Draw remove player button
    pygame.draw.rect(screen, RED, remove_player_button, border_radius=8)
    pygame.draw.rect(screen, BLACK, remove_player_button, 2, border_radius=8)
    text = font_small.render("REMOVE", True, WHITE)
    text2 = font_small.render("PLAYER", True, WHITE)
    text_rect = text.get_rect(center=(remove_player_button.centerx, remove_player_button.centery - 8))
    text2_rect = text2.get_rect(center=(remove_player_button.centerx, remove_player_button.centery + 8))
    screen.blit(text, text_rect)
    screen.blit(text2, text2_rect)

def draw_board():
    screen.fill(WHITE)
    draw_token_area(GREEN,0,0,player_id=0)
    draw_token_area(YELLOW,9*CELL,0,player_id=1)
    draw_token_area(BLUE,0,9*CELL,player_id=2)
    draw_token_area(RED,9*CELL,9*CELL,player_id=3)
    draw_cross_paths()
    draw_colored_left_tiles()
    draw_center()
    if players:
        draw_dice(current_dice, players[current_player_idx]['color'])
        if not rolling and not dice_rolled:
            draw_roll_button(players[current_player_idx]['color'])
    draw_tokens()
    draw_control_buttons()
    # Draw message if any
    if message_text and message_timer > 0:
        msg = font_large.render(message_text, True, message_color)
        screen.blit(msg, msg.get_rect(center=(WIDTH//2, HEIGHT//2)))

# --- Main loop ---
def main_game():
    global current_dice, rolling, roll_timer, current_player_idx, dragging, dice_rect, roll_button, dice_rolled, message_timer, winner_announced, num_players
    clock = pygame.time.Clock()
    initialize_tokens()

    def restart_game():
# Restart the game to initial state
        global current_player_idx, current_dice, rolling, roll_timer, dice_rolled
        current_player_idx = 0
        current_dice = 1
        rolling = False
        roll_timer = 0
        dice_rolled = False
        initialize_tokens()

    def reset_game():
# Reset the game and return to player selection
        global num_players, players, current_player_idx, current_dice, rolling, roll_timer, dice_rolled
        num_players = 0
        players.clear()
        current_player_idx = 0
        current_dice = 1
        rolling = False
        roll_timer = 0
        dice_rolled = False
        initialize_tokens()
        setup_screen()
        restart_game()

    def add_player():
# Add a new player to the game (max 4)
        global num_players
        if num_players < 4:
            name = f"Player {num_players+1}"
            players.append({'name': name, 'color': PLAYER_COLORS[num_players]})
            num_players += 1
            initialize_tokens()

    def remove_player():
# Remove the last player (min 2)
# Setup the initial screen for player selection
# Main game loop and event handling
        global num_players, current_player_idx
        if num_players > 2:
            players.pop()
            num_players -= 1
            if current_player_idx >= num_players:
                current_player_idx = 0
            initialize_tokens()

    def quit_game():
        pygame.quit()
        sys.exit()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if quit_button.collidepoint(event.pos):
                    quit_game()
                
                elif reset_button.collidepoint(event.pos):
                    reset_game()
                elif add_player_button.collidepoint(event.pos):
                    if num_players < 4:
                        add_player()
                elif remove_player_button.collidepoint(event.pos):
                    remove_player()
                elif roll_button.collidepoint(event.pos) and not rolling and not dice_rolled:
                    rolling = True
                    roll_timer = ROLL_DURATION
                    if dice_sound:
                        dice_sound.play()
                elif dice_rect.collidepoint(event.pos):
                    dragging = True
                    mouse_x, mouse_y = event.pos
                    offset_x = dice_rect.x - mouse_x
                    offset_y = dice_rect.y - mouse_y
                elif dice_rolled:
                    player_tokens = token_positions[current_player_idx]
                    for i, pos in enumerate(player_tokens):
                        distance = ((event.pos[0] - pos[0]) ** 2 + (event.pos[1] - pos[1]) ** 2) ** 0.5
                        if distance < CELL // 3:
                            moved = move_token(current_player_idx, i, current_dice)
                            if moved:
                                dice_rolled = False
                                if current_dice != 6:
                                    current_player_idx = (current_player_idx + 1) % num_players
                                break

            elif event.type == pygame.MOUSEBUTTONUP:
                dragging = False
            elif event.type == pygame.MOUSEMOTION and dragging:
                mouse_x, mouse_y = event.pos
                dice_rect.x = mouse_x + offset_x
                dice_rect.y = mouse_y + offset_y

        if rolling:
            current_dice = random.randint(1,6)
            roll_timer -= 1
            if roll_timer <= 0:
                rolling = False
                dice_rolled = True
                # Fix: ensure can_move_any_token is defined
                if 'can_move_any_token' in globals() and not can_move_any_token(current_player_idx, current_dice):
                    dice_rolled = False
                    if current_dice != 6:
                        current_player_idx = (current_player_idx + 1) % num_players
        # Message timer update
        if message_timer > 0:
            message_timer -= 1
            if message_timer == 0:
                global message_text
                message_text = None
        draw_board()
        pygame.display.flip()
        clock.tick(30)

def can_move_any_token(player_id, dice_roll):
    # Can move out of home with 6
    if dice_roll == 6 and any(token_is_home[player_id]):
        return True
    for i in range(4):
        if not token_is_home[player_id][i]:
            current_path_index = token_path_indices[player_id][i]
            path_length = len(full_paths[player_id])
            # Can move if not exceeding path
            if current_path_index + dice_roll <= path_length:
                return True
    return False

if __name__ == "__main__":
# Entry point: start the game
    # Background image setup
    background_img = None
    try:
        img = pygame.image.load("background.jpg")
        img_rect = img.get_rect()
        scale_w = WIDTH / img_rect.width
        scale_h = HEIGHT / img_rect.height
        scale = max(scale_w, scale_h)
        new_size = (int(img_rect.width * scale), int(img_rect.height * scale))
        img = pygame.transform.smoothscale(img, new_size)
        x_offset = (img.get_width() - WIDTH) // 2
        y_offset = (img.get_height() - HEIGHT) // 2
        background_img = img.subsurface((x_offset, y_offset, WIDTH, HEIGHT)).copy()
    except Exception:
        background_img = None

    setup_screen()
    main_game()