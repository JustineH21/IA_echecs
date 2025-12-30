import chess
import json
import random

valeur_piece = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 100000} # car ça bug si on fait inf - inf

class Noeud():
    def __init__(self,val = None):
        # None pour la racine
        self.val = val
        self.coups_possibles_apres = {}
    
    def ajouter_coup(self, move, score):
        self.coups_possibles_apres[move] = Noeud(score)

board = chess.Board()

def score_board(board, joueur_blanc:bool):
    score = 0
    for piece_type in valeur_piece.keys():
        score += len(board.pieces(piece_type, chess.WHITE)) * valeur_piece[piece_type]
        score -= len(board.pieces(piece_type, chess.BLACK)) * valeur_piece[piece_type]
    if joueur_blanc:
        return score
    else:
        return -score

def calculer_score(board, move):
    if board.is_capture(move):
        piece_capturee = board.piece_at(move.to_square)
        if piece_capturee:
            valeur_piece = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: float('inf')}
            score = valeur_piece[piece_capturee.piece_type]
        else: # Prise en passant
            score = 1 # Valeur du pion
    else:
        score = 0 # Rien n'est capturé
    return score

def minimax(board, profondeur, isMaxTurn, a = float('-inf'), b = float('inf')): # MINIMAX
    if board.is_checkmate():
        if board.turn == chess.WHITE:
            return float('-inf')  # Échec et mat pour les blancs
        else:
            return float('inf')  # Échec et mat pour les noirs
    elif board.is_game_over():
        return 0  # Match nul
    elif profondeur == 0:
        return score_board(board, board.turn) # car on push les mouvements temporairement (mais c'est supprimé après l'appel de fonction)
    elif isMaxTurn:
        score_max = float('-inf')
        for move in board.legal_moves:
            board.push(move)
            score = minimax(board, profondeur - 1, False)
            board.pop()
            score_max = max(score_max, score)
            a = max(a, score_max)
            if b <= a:
                break  # Coupure alpha-beta
        return score_max
    else:
        score_min = float('inf')
        for move in board.legal_moves:
            board.push(move)
            score = minimax(board, profondeur - 1, True)
            board.pop()
            score_min = min(score_min, score)
            b = min(b, score_min)
            if b <= a:
                break  # Coupure alpha-beta
        return score_min

def choisir_deplacement(board, donnees_partie): # AI_color = True si blanc, False si noir
    best_score = float("-inf")
    best_move = None

    for move in board.legal_moves:
        if str(move) in donnees_partie["historique_coups"]:
            break
        else:
            board.push(move)
            score = minimax(board, 3, False)
            board.pop()
            if score > best_score:
                best_score = score
                best_move = move
            elif score == best_score:
                best_move = random.choice([best_move, move]) # Choisir aléatoirement entre les deux mouvements égaux

    return best_move

def jouer(board):
    # Début de la partie : récupère l'historique des parties et crée un dictionnaire pour la nouvelle partie
    with open('Untitled.json', 'r') as fichier:
        historique = json.load(fichier)
    donnees_partie = {"couleur":"white", "historique_coups":[], "resultat":None, "score":0}

    # On décide qui commence
    ai_color = random.choice([True, False]) # True = l'IA est blanc ; False = l'IA est noir
    print("L'IA joue les " + ("blancs." if ai_color else "noirs."))

    while not board.is_game_over():
        if board.turn == ai_color: # si c'est le tour de l'IA
            print("\nAI's turn...")
            move = choisir_deplacement(board, donnees_partie)
            board.push(move)
            print(move)
            donnees_partie["historique_coups"].append(str(move))
            donnees_partie["score"] += calculer_score(board, move)
        else:
            while True:
                move = input("\nUn mouvement (ex : e5e3) : ")
                try:
                    board.push_san(move)
                    break
                except ValueError:
                    print("C'est invalide, réessayer.")
    
    # Game over
    print(board)
    winner = None
    if board.is_checkmate():
        if board.turn:
            print("Les noirs ont gagné.")
        else:
            print("Les blancs ont gagné.")
    elif board.is_game_over():
        print("Match nul")

    """i = 0
    while not board.is_game_over() and i < 10:
        choix = choisir_deplacement(board)
        board.push(choix[0])
        donnees_partie["historique_coups"].append(str(choix[0]))
        donnees_partie["score"] += choix[1]
        i += 1"""

    # Fin de la partie : met à jour l'historique et le sauvegarde dans le fichier JSON
    with open("Untitled.json", "w") as fichier:
        a = "partie"+str(len(historique)+1)
        historique[a] = donnees_partie
        json.dump(historique, fichier, indent=4)

jouer(board)
