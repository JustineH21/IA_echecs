import chess
import json
import random

valeur_piece = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 100000} # car ça bug si on fait inf - inf

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

def minimax(board, profondeur, isMaxTurn, historique, donnees_partie, a = float('-inf'), b = float('inf')): 
    if board.is_checkmate():
        # si c'est le tour du joueur Max, alors c'est lui qui a perdu
        if isMaxTurn:
            return float('-inf')
        else:
            return float('inf')
    elif board.is_game_over():
        return 0  # Match nul
    elif profondeur == 0:
        return score_board(board, board.turn) # car on push les mouvements temporairement (mais c'est supprimé après l'appel de fonction)
    elif isMaxTurn:
        score_max = float('-inf')
        for move in board.legal_moves:
            board.push(move)
            dispo = get_board_disposition(board)
            if dispo[0] in donnees_partie["historique_coups"] or dispo[1] in donnees_partie["historique_coups"]: # on ne prend que les coups qui n'ont pas encore été joués dans cette partie (pour éviter de tourner en rond)
                board.pop()
                continue
            if dispo[0] in donnees_partie["historique_coups"] or dispo[1] in donnees_partie["historique_coups"]: 
                temp = choisir_move_connu(board, historique, dispo[0], dispo[1], donnees_partie["historique_coups"])
                if temp[0]: 
                    score_max = float('inf') # si on connaît un coup connu intéressant, on le joue forcément (car c'est le meilleur coup possible)
            else:
                score = minimax(board, profondeur - 1, False, historique, donnees_partie)
                score_max = max(score_max, score)
            board.pop()
            a = max(a, score_max)
            if b <= a:
                break  # Coupure alpha-beta
        return score_max
    else: # on considère que le joueur Min peut jouer n'importe quel coup (on ne sait pas ce qu'il va faire), donc on n'en élimine aucun d'avance
        score_min = float('inf')
        for move in board.legal_moves:
            board.push(move)
            score = minimax(board, profondeur - 1, True, historique, donnees_partie)
            board.pop()
            score_min = min(score_min, score)
            b = min(b, score_min)
            if b <= a:
                break  # Coupure alpha-beta
        return score_min

def choisir_move_connu(board, historique, dispoW, dispoB, donnees_partie): # renvoie un booléen (coup connu intéressant trouvé ou non) et le coup à jouer (ou None)
    if dispoW in historique and dispoB in historique: # si les deux sont dans l'historique, on choisit celui qui a le meilleur score moyen sur le plus de parties
        dic_coups = {}
        for move in historique[dispoW]:
            if board.parse_san(move) in board.legal_moves:
                board.push_san(move)
                dispo = get_board_disposition(board)
                if dispo[0] in donnees_partie or dispo[1] in donnees_partie: # on ne prend que les coups qui n'ont pas encore été joués dans cette partie (pour éviter de tourner en rond)
                    board.pop()
                    continue
                board.pop() 
                dic_coups[move] = historique[dispoW][move][0] * 0.8 +  historique[dispoW][move][1] * 0.2 
        for move in historique[dispoB]:
            if board.parse_san(move) in board.legal_moves:
                board.push_san(move)
                dispo = get_board_disposition(board)
                if dispo[0] in donnees_partie or dispo[1] in donnees_partie: 
                    board.pop()
                    continue
                board.pop() 
                dic_coups[move] = historique[dispoB][move][0] * 0.8 +  historique[dispoB][move][1] * 0.2
    else:
        if dispoW in historique:
            dispo = dispoW
        else:
            dispo = dispoB
        
        for move in historique[dispo]:
            if board.parse_san(move) in board.legal_moves:
                dic_coups[move] = historique[dispo][move][0] * 0.8 +  historique[dispo][move][1] * 0.2

    best_move = (None, float("-inf")) # (mouvement, résultat moyen)
    nb_moves = 0
    for move in dic_coups:
        nb_moves += 1
        if dic_coups[move][0] > best_move[1]:
            best_move = (move, dic_coups[move][0])
    if best_move[1] > 0.5 or nb_moves == len(list(board.legal_moves)):
        # si le meilleur coup a un score moyen supérieur à 0.5, on le joue ou si l'IA connaît déjà tous les coups possibles, donc c'est vraiment le meilleur coup
        return (True, board.parse_san(best_move[0])) # passe du str au move
    
    return (False, None) # aucun coup connu n'a l'air intéressant

def choisir_deplacement(board, donnees_partie, historique):
    dispoW, dispoB = get_board_disposition(board) # disposition du plateau pour les blancs et les noirs (pour avoir deux fois plus de chances de le connaître dans l'historique)
    if dispoW in historique or dispoB in historique:
        a = choisir_move_connu(board, historique, dispoW, dispoB, donnees_partie["historique_coups"])
        if a[0]: 
            return a[1], dispoW

    # si on ne connaît pas la disposition, ou qu'aucun coup connu n'a l'air intéressant, on fait minimax
    best_move = (None, float("-inf"))
    for move in board.legal_moves:
        if dispoW in historique or dispoB in historique:
            if str(move) in historique[dispoW] or str(move) in historique[dispoB]: # on ne peut pas faire "and" car sinon ça va bugué car historique[dispoW] peut ne pas exister
                continue # on ne teste pas les mouvements déjà connus (car on a déjà vu qu'ils n'étaient pas intéressants)
        board.push(move)
        dispo = get_board_disposition(board)
        if dispo[0] in donnees_partie["historique_coups"] or dispo[1] in donnees_partie["historique_coups"]: # on ne prend que les coups qui n'ont pas encore été joués dans cette partie (pour éviter de tourner en rond)
            board.pop()
            continue
        score = minimax(board, 3, False, historique, donnees_partie)
        board.pop()
        if score > best_move[1]:
            best_move = (move, score)

    if best_move[0] is None:
        print(dispoW)
        return (random.choice(list(board.legal_moves)), dispoW) # si jamais il n'y a aucun coup possible (ce qui ne devrait pas arriver), on en choisit un au hasard pour éviter de faire planter

    return best_move[0], dispoW

def get_board_disposition(board):
    dispoW = ""
    dispoB = [[None for _ in range(8)] for _ in range(8)]
    # Pour la dispoB (black), on inverse les couleurs puis on fait une symétrie centrale (même disposition mais du côté des noirs/blancs)
    for ligne in range(7, -1, -1):
        for colonne in range(8):
            piece = board.piece_at(chess.square(colonne, ligne))
            if piece is None:
                dispoW += " "
            else:
                dispoW += piece.symbol()
            
                if piece.symbol().islower(): # on inverse la majuscule/minuscule (= on inverse les couleurs)
                    piece = piece.symbol().upper()
                else:
                    piece = piece.symbol().lower()

                dispoB[7-ligne][7-colonne] = piece # symétrie centrale

        dispoW += ","
    # on transforme la liste dispoB en str
    dispoB_str = ""
    dispoB.reverse() # pour que ce soit dans le même ordre que dispoW
    for ligne in dispoB:
        for piece in ligne:
            if piece is None:
                dispoB_str += " "
            else:
                dispoB_str += piece
        dispoB_str += ","

    # on enlève la dernière virgule
    dispoW = dispoW[:-1]
    dispoB_str = dispoB_str[:-1] 
    
    return dispoW, dispoB_str


def jouer(board):
    # Début de la partie : récupère l'historique des parties et crée un dictionnaire pour la nouvelle partie
    with open('donnees.json', 'r') as fichier:
        historique = json.load(fichier)
    donnees_partie = {"couleur":"white", "historique_coups":{}, "resultat":None}
    # historique_coups : {"disposition_plateau(str)": "mouvement(str)"}
    # disposition_plateau (ex : début) : "rnbqkbnr,pppppppp,        ,        ,        ,        ,PPPPPPPP,RNBQKBNR"
    # (espace = case vide)

    # On décide qui commence
    ai_color = random.choice([True, False]) # True = l'IA est blanc ; False = l'IA est noir
    print("L'IA joue les " + ("blancs." if ai_color else "noirs."))

    while not board.is_game_over():
        print(board.turn)
        move, dispo = choisir_deplacement(board, donnees_partie, historique)
        board.push(move)
        print(move)
        """
        if board.turn == ai_color: # si c'est le tour de l'IA
            print("\nAI's turn...")
            move, dispo = choisir_deplacement(board, donnees_partie, historique)
            board.push(move)
            print(move)
        else:
            dispo = get_board_disposition(board)
            while True:
                move = input("\nUn mouvement (ex : e5e3) : ")
                try:
                    board.push_san(move)
                    break
                except ValueError:
                    print("C'est invalide, réessayer.")"""

        # Met à jour l'historique des coups
        if dispo not in donnees_partie["historique_coups"]: # première fois que cette disposition apparaît
            donnees_partie["historique_coups"][dispo] = [str(move)]
        elif str(move) not in donnees_partie["historique_coups"][dispo]: # si la disposition est déjà apparue mais pas avec ce coup
            donnees_partie["historique_coups"][dispo].append(str(move))
        # si la disposition est déjà apparue avec ce coup, on ne l'ajoute pas à l'historique des coups
    
    # Game over
    print(board)
    # On enregistre le résultat pour l'IA
    if board.is_checkmate():
        if ai_color != board.turn: # si ce n'est pas le tour de l'IA, donc l'IA a gagné
            donnees_partie["resultat"] = 1
        elif ai_color == board.turn: # si c'est le tour de l'IA, donc l'IA a perdu
            donnees_partie["resultat"] = -1
    else: # match nul
        donnees_partie["resultat"] = 0
    print(donnees_partie["resultat"])

    # Mise à jour de l'historique des parties
    dic_coups = donnees_partie["historique_coups"]
    for i in range(len(dic_coups)):
        disposition = list(dic_coups.keys())[i]
        if disposition not in historique:
            res = {}
        else:
            res = historique[disposition]
            
        for move in dic_coups[disposition]:
            # Pour savoir quel est le meilleur coup à faire, même si ce n'est pas l'IA qui a joué ce coup 
            # (donc on fait comme si c'était l'IA qui l'avait fait)
            # ça permet d'enregistrer plus rapidement le maximum de dispositions possibles
            if i%2 == 1: # coup de l'adversaire
                resultat = -1 * donnees_partie["resultat"]
            else: # coup de l'IA
                resultat = donnees_partie["resultat"]
            
            if move not in res:
                res[move] = (resultat, 1) # (moyenne de résultat, nombre de fois joué)
            else:
                nv_moyenne = (res[move][0]*res[move][1] + resultat) / (res[move][1] + 1)
                res[move] = (nv_moyenne, res[move][1] + 1)
        historique[disposition] = res

    # Fin de la partie : met à jour l'historique et le sauvegarde dans le fichier JSON
    with open("donnees.json", "w") as fichier:
        json.dump(historique, fichier, indent=4)

for _ in range(1000):
    jouer(board)
    board.reset()