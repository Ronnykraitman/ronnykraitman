import random
import sys
import time
import heapq
from typing import List, Dict, Any, Union

# Try to import crewai. If not installed, provide a dummy mock for demonstration purposes
# so the code doesn't crash immediately if the user runs it without the library.
try:
    from crewai import Agent, Task, Crew, Process
    from crewai.tools import tool
except ImportError:
    print("CRITICAL: 'crewai' library not found. Please install it using: pip install crewai")
    sys.exit(1)

# =================================================================================================
# GAME ENGINE & LOGIC
# =================================================================================================

class ClueGameEngine:
    def __init__(self):
        self.suspects = ["Miss Scarlet", "Colonel Mustard", "Mrs. Peacock", "Professor Plum", "Mr. Green", "Mrs. White"]
        self.weapons = ["Candlestick", "Dagger", "Lead Pipe", "Revolver", "Rope", "Wrench"]
        self.rooms = ["Kitchen", "Ballroom", "Conservatory", "Dining Room", "Lounge", "Hall", "Study", "Library", "Billiard Room"]

        # Weighted Graph for distances
        # Normal hallways = ~4-6 steps. Secret passages = 1 step.
        self.room_connections = {
            "Kitchen":      {"Ballroom": 6, "Dining Room": 6, "Study": 1}, # Secret passage to Study
            "Ballroom":     {"Kitchen": 6, "Conservatory": 6, "Billiard Room": 6},
            "Conservatory": {"Ballroom": 6, "Lounge": 1, "Library": 6},    # Secret passage to Lounge
            "Dining Room":  {"Kitchen": 6, "Lounge": 6, "Hall": 6},
            "Lounge":       {"Dining Room": 6, "Hall": 6, "Conservatory": 1}, # Secret passage to Conservatory
            "Hall":         {"Dining Room": 6, "Lounge": 6, "Study": 6},
            "Study":        {"Hall": 6, "Library": 6, "Kitchen": 1},       # Secret passage to Kitchen
            "Library":      {"Study": 6, "Billiard Room": 6, "Conservatory": 6},
            "Billiard Room":{"Library": 6, "Ballroom": 6, "Hall": 8}
        }

        # Pre-compute all-pairs shortest paths using Dijkstra
        self.distances = self._compute_all_distances()

        self.truth = {}
        # Player dict structure:
        # {'name': str, 'is_ai': bool, 'hand': [], 'loc': str, 'eliminated': False, 'memory': {card: showed_by}, 'agent': Obj}
        self.players = []
        self.turn_index = 0
        self.current_dice_roll = 0
        self.game_over = False
        self.winner = None
        self.logs = [] # Shared memory logs for agents

    def _compute_all_distances(self):
        """Helper to calculate static numeric distance between each room to the other."""
        dist_map = {r: {r2: float('inf') for r2 in self.rooms} for r in self.rooms}

        for start_node in self.rooms:
            dist_map[start_node][start_node] = 0
            queue = [(0, start_node)]

            while queue:
                current_dist, u = heapq.heappop(queue)

                if current_dist > dist_map[start_node][u]:
                    continue

                # Check neighbors
                neighbors = self.room_connections.get(u, {})
                for v, weight in neighbors.items():
                    distance = current_dist + weight
                    if distance < dist_map[start_node][v]:
                        dist_map[start_node][v] = distance
                        heapq.heappush(queue, (distance, v))
        return dist_map

    def setup_game(self, human_character_name: str):
        # 1. Select Truth
        truth_suspect = random.choice(self.suspects)
        truth_weapon = random.choice(self.weapons)
        truth_room = random.choice(self.rooms)
        self.truth = {"Suspect": truth_suspect, "Weapon": truth_weapon, "Room": truth_room}

        # Remove truth from deck
        deck = (
                [c for c in self.suspects if c != truth_suspect] +
                [c for c in self.weapons if c != truth_weapon] +
                [c for c in self.rooms if c != truth_room]
        )
        random.shuffle(deck)

        # 2. Setup Players
        self.players = []

        # 2a. Human Player
        self.players.append({
            "name": human_character_name,
            "is_ai": False,
            "hand": [],
            "loc": "Lounge",
            "eliminated": False,
            "memory": {},
            "agent": None
        })

        # 2b. AI Players (Pick 3 random characters excluding the human's choice)
        remaining_suspects = [s for s in self.suspects if s != human_character_name]
        ai_names = random.sample(remaining_suspects, 3)

        for name in ai_names:
            self.players.append({
                "name": name,
                "is_ai": True,
                "hand": [],
                "loc": "Lounge",
                "eliminated": False,
                "memory": {},
                "agent": None
            })

        # 3. Deal Cards
        # Each player gets exactly 4 cards. Remaining cards are left unused (known only to manager).
        for _ in range(4):
            for player in self.players:
                if deck:
                    card = deck.pop()
                    player["hand"].append(card)
                    # Add own hand to memory immediately
                    player["memory"][card] = "Self"

        # Remaining cards in 'deck' are ignored/unused.

        print(f"\n--- GAME SETUP COMPLETE ---")
        print(f"The Game Manager has hidden the cards in the envelope.")
        print(f"You are playing as {human_character_name}.")
        print(f"Your opponents are: {', '.join(ai_names)}")

    def get_player_by_name(self, name: str):
        for p in self.players:
            if p["name"] == name:
                return p
        return None

    def start_turn(self):
        """Rolls dice for the current turn."""
        d1 = random.randint(1, 6)
        d2 = random.randint(1, 6)
        self.current_dice_roll = d1 + d2
        return self.current_dice_roll

    def get_reachable_rooms(self, current_room: str, roll: int) -> List[str]:
        """Returns list of rooms reachable within 'roll' steps."""
        reachable = []
        if current_room not in self.distances:
            return []

        for room, dist in self.distances[current_room].items():
            if room != current_room and dist <= roll:
                reachable.append(room)
        return reachable

    def move_player(self, player_name: str, destination: str):
        p = self.get_player_by_name(player_name)
        if not p: return "Player not found."

        current_room = p["loc"]

        # Check distance validity
        dist = self.distances[current_room].get(destination, float('inf'))

        if dist <= self.current_dice_roll:
            p["loc"] = destination
            return f"{player_name} moved from {current_room} to {destination} (Distance: {dist}, Roll: {self.current_dice_roll})."
        else:
            # Fallback for AI hallucination: Stay put or random valid
            valid_moves = self.get_reachable_rooms(current_room, self.current_dice_roll)
            if valid_moves:
                fallback = random.choice(valid_moves)
                p["loc"] = fallback
                return f"Invalid move ({destination} is {dist} steps away, roll was {self.current_dice_roll}). Moved to {fallback} instead."
            else:
                # If no valid moves, stay put is the only valid option
                return f"No rooms reachable with roll {self.current_dice_roll}. {player_name} stays in {current_room}."

    def _validate_vocabulary(self, suspect: str, weapon: str, room: str) -> Union[bool, str]:
        """Checks if terms exist in the official game lists."""
        if suspect not in self.suspects:
            return f"Error: '{suspect}' is not a valid suspect. Valid options: {', '.join(self.suspects)}"
        if weapon not in self.weapons:
            return f"Error: '{weapon}' is not a valid weapon. Valid options: {', '.join(self.weapons)}"
        if room not in self.rooms:
            return f"Error: '{room}' is not a valid room. Valid options: {', '.join(self.rooms)}"
        return True

    def handle_suggestion(self, suggester_name: str, suspect: str, weapon: str, room: str):
        # Strict Vocabulary Check
        validation = self._validate_vocabulary(suspect, weapon, room)
        if validation is not True:
            return validation

        # Move suspect to room
        suspect_player = self.get_player_by_name(suspect)
        if suspect_player:
            suspect_player["loc"] = room

        print(f"\n[SUGGESTION] {suggester_name} suggests: It was {suspect} with the {weapon} in the {room}.")

        # Check clockwise for refutations
        suggester_idx = next(i for i, p in enumerate(self.players) if p["name"] == suggester_name)
        suggester_player = self.players[suggester_idx]

        for i in range(1, len(self.players)):
            check_idx = (suggester_idx + i) % len(self.players)
            checker = self.players[check_idx]

            # Find matching cards
            matches = [c for c in checker["hand"] if c in [suspect, weapon, room]]

            if matches:
                shown_card = None

                # If checker is Human, ask which to show
                if not checker["is_ai"]:
                    print(f"\n>> {checker['name']}, you have conflicting evidence: {matches}")
                    print(">> Which card do you want to show secretly?")
                    for idx, card in enumerate(matches):
                        print(f"   {idx + 1}. {card}")
                    choice = input(">> Enter number: ")
                    try:
                        shown_card = matches[int(choice)-1]
                    except:
                        shown_card = matches[0]
                else:
                    # If checker is AI, pick random match
                    shown_card = random.choice(matches)

                # UPDATE MEMORY OF SUGGESTER
                suggester_player["memory"][shown_card] = checker["name"]

                if suggester_player["is_ai"]:
                    return f"{checker['name']} showed you a card privately: {shown_card}"
                else:
                    return f"{checker['name']} whispers and shows you: {shown_card}"

        return "No one could refute your suggestion."

    def handle_accusation(self, accuser_name: str, suspect: str, weapon: str, room: str):
        # Strict Vocabulary Check
        validation = self._validate_vocabulary(suspect, weapon, room)
        if validation is not True:
            return validation

        print(f"\n!!! [ACCUSATION] !!! {accuser_name} accuses {suspect} with the {weapon} in the {room}!")

        is_correct = (
                suspect == self.truth["Suspect"] and
                weapon == self.truth["Weapon"] and
                room == self.truth["Room"]
        )

        if is_correct:
            self.game_over = True
            self.winner = accuser_name
            return f"CORRECT! {accuser_name} has solved the murder! The game is over."
        else:
            p = self.get_player_by_name(accuser_name)
            p["eliminated"] = True
            return f"WRONG! {accuser_name} has been eliminated. The truth remains hidden."

# Initialize Global Game Engine
game = ClueGameEngine()

# =================================================================================================
# CREW AI TOOLS
# =================================================================================================

class ClueTools:

    @tool("Consult Notebook")
    def consult_notebook(player_name: str):
        """
        Returns the list of cards known to the player (both their own hand and cards shown by others).
        Use this to determine which cards are safe (not the murder weapon/suspect/room).
        """
        p = game.get_player_by_name(player_name)
        if p:
            mem = p.get("memory", {})
            if not mem:
                return "Your notebook is empty."
            lines = [f"- {card} (Source: {who})" for card, who in mem.items()]
            return "--- CONFIDENTIAL NOTEBOOK ---\n" + "\n".join(lines)
        return "Error: Player not found."

    @tool("Look at Hand")
    def look_at_hand(player_name: str):
        """Useful to see the cards currently held by the player."""
        p = game.get_player_by_name(player_name)
        if p:
            return f"Your hand contains: {', '.join(p['hand'])}"
        return "Error: Player not found."

    @tool("Get Current Location and Moves")
    def get_moves(player_name: str):
        """
        Returns current room, the current dice roll, and list of accessible rooms within that distance.
        The dice have already been rolled for the turn.
        """
        p = game.get_player_by_name(player_name)
        if p:
            current = p["loc"]
            roll = game.current_dice_roll
            moves = game.get_reachable_rooms(current, roll)
            return f"You are in the {current}. You rolled a {roll}. You can move to: {', '.join(moves)}."
        return "Error"

    @tool("Move Player")
    def move(player_name: str, room_name: str):
        """Moves the player to a connected room. Must be in the list of valid moves."""
        return game.move_player(player_name, room_name)

    @tool("Make Suggestion")
    def suggest(player_name: str, suspect: str, weapon: str, room: str):
        """
        Make a suggestion.
        IMPORTANT: 'room' MUST be the room the player is currently in.
        Returns the result of the suggestion (e.g., if someone showed a card).
        """
        p = game.get_player_by_name(player_name)
        if p["loc"] != room:
            # Auto-correction for AI logic
            return f"Invalid suggestion: You must suggest the room you are currently in ({p['loc']})."

        result = game.handle_suggestion(player_name, suspect, weapon, room)
        game.logs.append(f"{player_name} suggested {suspect}, {weapon}, {room}. Result: {result}")
        return result

    @tool("Make Accusation")
    def accuse(player_name: str, suspect: str, weapon: str, room: str):
        """
        Make a FINAL accusation.
        Only use this if you are 100% sure of the Room, Suspect, and Weapon.
        If you are wrong, you lose.
        """
        result = game.handle_accusation(player_name, suspect, weapon, room)
        game.logs.append(result)
        return result

# =================================================================================================
# MAIN EXECUTION
# =================================================================================================

def run_clue_game():
    print("Welcome to Clue AI!")

    # Select Character
    print("\n--- CHARACTER SELECTION ---")
    for i, name in enumerate(game.suspects):
        print(f"{i+1}. {name}")

    choice = -1
    while choice < 0 or choice >= len(game.suspects):
        try:
            choice = int(input("Choose your character (Enter number): ")) - 1
        except ValueError:
            pass

    human_name = game.suspects[choice]

    game.setup_game(human_name)

    # --- Create Agents ---

    # Common configuration for agents
    agents_map = {}

    # Helper to stringify lists for prompts
    valid_suspects_str = ", ".join(game.suspects)
    valid_weapons_str = ", ".join(game.weapons)
    valid_rooms_str = ", ".join(game.rooms)

    for p in game.players:
        if p["is_ai"]:
            # Backstory generation based on logs
            agent = Agent(
                role=f"{p['name']} (Clue Player)",
                goal="Deduce the Murderer, Weapon, and Room before anyone else.",
                backstory=(
                    f"You are {p['name']}. You are playing Clue. "
                    "You are competitive and smart. "
                    "You maintain a detailed Notebook of all cards you have seen. "
                    "You NEVER guess a card that is already in your Notebook. "
                    "You try to narrow down the possibilities.\n"
                    "IMPORTANT: You must ONLY use the following terms. Do not use synonyms (e.g. use 'Dagger' not 'Knife').\n"
                    f"Valid Suspects: {valid_suspects_str}\n"
                    f"Valid Weapons: {valid_weapons_str}\n"
                    f"Valid Rooms: {valid_rooms_str}"
                ),
                tools=[
                    ClueTools.consult_notebook,
                    ClueTools.get_moves,
                    ClueTools.move,
                    ClueTools.suggest,
                    ClueTools.accuse
                ],
                verbose=True,
                allow_delegation=False,
                llm="gpt-4o-mini" # Or any other available model
            )
            p["agent"] = agent
            agents_map[p["name"]] = agent

    # Manager Agent (Optional, mostly for flavor in this architecture)
    manager = Agent(
        role="Game Manager",
        goal="Ensure the game flows smoothly.",
        backstory="I am the mansion's butler. I know the truth, but I will never tell.",
        allow_delegation=False
    )

    # --- Game Loop ---

    print("\n--- THE GAME BEGINS ---")

    while not game.game_over:

        active_players = [p for p in game.players if not p["eliminated"]]
        if len(active_players) == 0:
            print("All players eliminated! The House wins.")
            break

        current_player = game.players[game.turn_index]

        if current_player["eliminated"]:
            game.turn_index = (game.turn_index + 1) % len(game.players)
            continue

        print(f"\n>>> TURN: {current_player['name']}")

        # Roll Dice for the turn
        roll = game.start_turn()
        print(f"   [Dice Roll]: {roll}")

        if current_player["is_ai"]:
            # AI TURN LOGIC
            agent = current_player["agent"]

            # We construct a specific task for the turn to ensure it follows game rules
            turn_description = (
                f"It is your turn, {current_player['name']}. "
                f"1. Check your known cards using 'Consult Notebook'. "
                f"2. You rolled a {roll}. Check your moves using 'Get Current Location'. "
                f"3. If you have valid moves, use 'Move Player' to go to a new room. If NO moves are listed, stay put. "
                f"4. If you are in a room (even if you didn't move), make a 'Make Suggestion' about a Suspect and Weapon in that room. "
                f"   (Do NOT suggest cards that appear in your Notebook!). "
                f"5. If you are ABSOLUTELY CERTAIN (your Notebook eliminates almost all possibilities), use 'Make Accusation'. "
                f"   OTHERWISE, stop. Your turn ends after the suggestion."
            )

            task = Task(
                description=turn_description,
                agent=agent,
                expected_output="A summary of the actions taken (Move, Suggestion, and Result)."
            )

            # Create a mini-crew for this single turn to execute it
            turn_crew = Crew(
                agents=[agent],
                tasks=[task],
                verbose=False
            )

            try:
                result = turn_crew.kickoff()
                print(f"AI Thought Process Complete.")
            except Exception as e:
                print(f"AI Error: {e}")
                # Fallback simple AI move if LLM fails
                moves = game.get_reachable_rooms(current_player["loc"], roll)
                if moves:
                    dest = random.choice(moves)
                    move_result = game.move_player(current_player["name"], dest)
                    print(f"(Fallback) {move_result}")
                    s_suspect = random.choice(game.suspects)
                    s_weapon = random.choice(game.weapons)
                    game.handle_suggestion(current_player["name"], s_suspect, s_weapon, dest)
                else:
                    print("(Fallback) No moves possible.")

        else:
            # HUMAN TURN LOGIC
            print(f"You are in the {current_player['loc']}.")
            # Show notebook snippet
            print(f"Notebook: You know {len(current_player['memory'])} cards.")

            # 1. Move
            moves = game.get_reachable_rooms(current_player["loc"], roll)
            if not moves:
                print(f"No rooms reachable with a roll of {roll}. You are stuck in {current_player['loc']}.")
            else:
                print(f"Possible moves (Distances <= {roll}): {moves}")
                dest = input("Where do you want to go? (Type exact name or press Enter to stay): ")

                if dest in moves:
                    game.move_player(current_player["name"], dest)
                elif dest == "":
                    print("Staying put.")
                else:
                    print("Invalid move. Staying put.")

            # 2. Action
            print("\nActions: [1] Suggest  [2] Accuse  [3] View Notebook  [4] Pass")
            action = input("Choose action: ")

            if action == "1":
                print(f"Current Room: {current_player['loc']}")
                s_suspect = input("Suspect: ")
                s_weapon = input("Weapon: ")
                res = game.handle_suggestion(current_player["name"], s_suspect, s_weapon, current_player["loc"])
                print(f"RESULT: {res}")

            elif action == "2":
                print("WARNING: This is the end game.")
                a_room = input("Room: ")
                a_suspect = input("Suspect: ")
                a_weapon = input("Weapon: ")
                res = game.handle_accusation(current_player["name"], a_suspect, a_weapon, a_room)
                print(res)
                if game.game_over: break

            elif action == "3":
                print("\n--- YOUR NOTEBOOK ---")
                for c, who in current_player['memory'].items():
                    print(f"- {c} (Shown by {who})")
                print("---------------------")

            else:
                print("Passing turn.")

        if game.game_over:
            break

        # Next player
        game.turn_index = (game.turn_index + 1) % len(game.players)
        time.sleep(1) # Pace the game slightly

    print("\n--- GAME OVER ---")
    print(f"The Truth was: {game.truth}")
    if game.winner:
        print(f"Winner: {game.winner}")
    else:
        print("No winner today.")

if __name__ == "__main__":
    run_clue_game()