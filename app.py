import os
import requests
import json
from flask import Flask, render_template, request, jsonify


app = Flask(__name__)

# --- RapidAPI Configuration ---
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "YOUR_RAPIDAPI_KEY")
RAPIDAPI_HOST = os.environ.get("RAPIDAPI_HOST", "YOUR_RAPIDAPI_HOST")
RAPIDAPI_URL = os.environ.get("RAPIDAPI_URL", "https://tic-tac-toe-ai.p.rapidapi.com/move")

RAPIDAPI_HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": RAPIDAPI_HOST,
    "Content-Type": "application/json"
}

# --- Game State ---
game_state = {
    'board': [['', '', ''], ['', '', ''], ['', '', '']],
    'current_player': 'X',
    'game_over': False,
    'winner': None,
    'scores': {'X': 0, 'O': 0, 'draw': 0},
    'mode': 'player-vs-player'
}

# --- Helper Functions ---
def check_win(board):
    for row in board:
        if row[0] == row[1] == row[2] != '':
            return row[0]
    for col in range(3):
        if board[0][col] == board[1][col] == board[2][col] != '':
            return board[0][col]
    if board[0][0] == board[1][1] == board[2][2] != '':
        return board[0][0]
    if board[0][2] == board[1][1] == board[2][0] != '':
        return board[0][2]
    return None

def check_draw(board):
    for row in board:
        for cell in row:
            if cell == '':
                return False
    return True

def local_ai_move(board, player_symbol):
    empty_cells = []
    for r in range(3):
        for c in range(3):
            if board[r][c] == '':
                empty_cells.append((r, c))

    if not empty_cells:
        return None, None

    # Check for winning move
    for r, c in empty_cells:
        temp_board = [row[:] for row in board]
        temp_board[r][c] = player_symbol
        if check_win(temp_board) == player_symbol:
            return r, c

    # Check for blocking move
    opponent_symbol = 'X' if player_symbol == 'O' else 'O'
    for r, c in empty_cells:
        temp_board = [row[:] for row in board]
        temp_board[r][c] = opponent_symbol
        if check_win(temp_board) == opponent_symbol:
            return r, c

    # Take center if available
    if (1, 1) in empty_cells:
        return 1, 1

    # Take corners if available
    corners = [(0, 0), (0, 2), (2, 0), (2, 2)]
    for r, c in corners:
        if (r, c) in empty_cells:
            return r, c

    return empty_cells[0]


def get_ai_move(board, player_symbol):
    if RAPIDAPI_KEY != "YOUR_RAPIDAPI_KEY" and RAPIDAPI_HOST != "YOUR_RAPIDAPI_HOST":
        try:
            print(f"Attempting to call RapidAPI: {RAPIDAPI_URL}")
            payload = {"board": board, "player": player_symbol}
            response = requests.post(RAPIDAPI_URL, headers=RAPIDAPI_HEADERS, json=payload, timeout=5)
            response.raise_for_status()
            api_response = response.json()
            print(f"RapidAPI Response: {api_response}")

            if 'move' in api_response and isinstance(api_response['move'], list) and len(api_response['move']) == 2:
                row, col = api_response['move'][0], api_response['move'][1]
                if 0 <= row < 3 and 0 <= col < 3 and board[row][col] == '':
                    return row, col
                else:
                    print(f"RapidAPI returned an invalid move: {row},{col}. Falling back to local AI...")
                    return local_ai_move(board, player_symbol)
            else:
                print("RapidAPI response malformed. Falling back to local AI...")
                return local_ai_move(board, player_symbol)
        except requests.exceptions.RequestException as e:
            print(f"Error connecting to RapidAPI: {e}. Falling back to local AI...")
            return local_ai_move(board, player_symbol)
        except Exception as e:
            print(f"Unexpected error with RapidAPI: {e}. Falling back to local AI...")
            return local_ai_move(board, player_symbol)
    else:
        print("RapidAPI credentials not set. Using local AI...")
        return local_ai_move(board, player_symbol)


# --- Flask Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/game_state', methods=['GET'])
def get_game_state():
    return jsonify(game_state)

@app.route('/make_move', methods=['POST'])
def make_move():
    global game_state
    data = request.get_json()
    row, col = data['row'], data['col']
    player = data['player']

    if game_state['game_over'] or game_state['board'][row][col] != '' or game_state['current_player'] != player:
        return jsonify({'success': False, 'message': 'Invalid move'})

    game_state['board'][row][col] = player

    winner = check_win(game_state['board'])
    if winner:
        game_state['game_over'] = True
        game_state['winner'] = winner
        game_state['scores'][winner] += 1
        return jsonify({'success': True, 'game_state': game_state, 'message': f'{winner} wins!'})

    if check_draw(game_state['board']):
        game_state['game_over'] = True
        game_state['winner'] = 'draw'
        game_state['scores']['draw'] += 1
        return jsonify({'success': True, 'game_state': game_state, 'message': "It's a draw!"})

    game_state['current_player'] = 'O' if player == 'X' else 'X'

    if game_state['mode'] == 'player-vs-ai' and game_state['current_player'] == 'O':
        ai_row, ai_col = get_ai_move(game_state['board'], 'O')
        if ai_row is not None and ai_col is not None:
            game_state['board'][ai_row][ai_col] = 'O'

            winner = check_win(game_state['board'])
            if winner:
                game_state['game_over'] = True
                game_state['winner'] = winner
                game_state['scores'][winner] += 1
                return jsonify({'success': True, 'game_state': game_state, 'message': f'{winner} wins!'})

            if check_draw(game_state['board']):
                game_state['game_over'] = True
                game_state['winner'] = 'draw'
                game_state['scores']['draw'] += 1
                return jsonify({'success': True, 'game_state': game_state, 'message': "It's a draw!"})

            game_state['current_player'] = 'X'

    return jsonify({'success': True, 'game_state': game_state})

@app.route('/reset_game', methods=['POST'])
def reset_game():
    global game_state
    game_state['board'] = [['', '', ''], ['', '', ''], ['', '', '']]
    game_state['current_player'] = 'X'
    game_state['game_over'] = False
    game_state['winner'] = None
    return jsonify({'success': True, 'game_state': game_state})

@app.route('/set_mode', methods=['POST'])
def set_mode():
    global game_state
    data = request.get_json()
    new_mode = data.get('mode')
    if new_mode in ['player-vs-player', 'player-vs-ai']:
        game_state['mode'] = new_mode
        game_state['board'] = [['', '', ''], ['', '', ''], ['', '', '']]
        game_state['current_player'] = 'X'
        game_state['game_over'] = False
        game_state['winner'] = None
        print(f"Game mode set to: {new_mode}")
        return jsonify({'success': True, 'game_state': game_state})
    return jsonify({'success': False, 'message': 'Invalid game mode'})

@app.route('/reset_scores', methods=['POST'])
def reset_scores():
    global game_state
    game_state['scores'] = {'X': 0, 'O': 0, 'draw': 0}
    return jsonify({'success': True, 'game_state': game_state})


# --- Start Ngrok Tunnel ---
def start_ngrok():
    NGROK_AUTH_TOKEN = os.environ.get("NGROK_AUTH_TOKEN")
    if not NGROK_AUTH_TOKEN:
        print("NGROK_AUTH_TOKEN not found in environment variables.")
        print("Set it in Colab Secrets or as an environment variable.")
        print("Get your authtoken from: https://dashboard.ngrok.com/get-started/your-authtoken")
        return None

    ngrok.set_auth_token(NGROK_AUTH_TOKEN)
    public_url = ngrok.connect(5000).public_url
    print(f"* ngrok tunnel URL: {public_url}")
    print(f"* Running on {public_url}/")
    return public_url


if __name__ == '__main__':
    start_ngrok()
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )