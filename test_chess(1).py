import chess
import json
import random

valeur_piece = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 100000} # car ça bug si on fait inf - inf

class IA_Echecs:
    def __init__(self):
        self.board = chess.Board()

    def score_board(self):
        """Calcule le score pour le joueur blanc, puis inverse si on cherche pour le joueur noir"""
        score = 0
        for piece_type in valeur_piece.keys():
            score += len(self.board.pieces(piece_type, chess.WHITE)) * valeur_piece[piece_type]
            score -= len(self.board.pieces(piece_type, chess.BLACK)) * valeur_piece[piece_type]
        nb_coups = len(list(self.board.legal_moves))
        self.board.push(chess.Move.null()) # on fait un mouvement nul pour passer au tour de l'adversaire et calculer le nombre de coups possibles pour lui
        nb_coups_adversaire = len(list(self.board.legal_moves))
        self.board.pop() # on revient à la position d'origine
        score += 0.3 * (nb_coups - nb_coups_adversaire) # on valorise les mouvements qui augmentent le nombre de coups possibles pour l'IA et diminuent ceux de l'adversaire
        
        cases_centre = [chess.E4, chess.D4, chess.E5, chess.D5]
        for case in cases_centre:
            piece = self.board.piece_at(case)
            if piece is not None:
                if piece.color == chess.WHITE:
                    score += 1.5 * valeur_piece[piece.piece_type] # on valorise les pièces au centre
                else:
                    score -= 1.5 * valeur_piece[piece.piece_type]

        if self.board.turn:
            return score
        else:
            return -score

    def minimax(self, profondeur, isMaxTurn, a = float('-inf'), b = float('inf')): 
        if self.board.is_checkmate():
            # si c'est le tour du joueur Max, alors c'est lui qui a perdu
            if isMaxTurn:
                return float('-inf')
            else:
                return float('inf')
        elif self.board.is_game_over():
            return 0  # Match nul
        elif profondeur == 0:
            return self.score_board() # car on push les mouvements temporairement (mais c'est supprimé après l'appel de fonction)
        elif isMaxTurn:
            score_max = float('-inf')
            for move in self.board.legal_moves:
                self.board.push(move)
                dispo = self.get_board_disposition()
                if dispo[0] in self.donnees_partie["historique_coups"] or dispo[1] in self.donnees_partie["historique_coups"]: # on ne prend que les coups qui n'ont pas encore été joués dans cette partie (pour éviter de tourner en rond)
                    self.board.pop()
                    continue
                if dispo[0] in self.donnees_partie["historique_coups"] or dispo[1] in self.donnees_partie["historique_coups"]: 
                    tmp = self.choisir_move_connu(dispo[0], dispo[1])
                    if tmp[0]: 
                        score_max = float('inf') # si on connaît un coup connu intéressant, on le joue forcément (car c'est le meilleur coup possible)
                else:
                    score = self.minimax(profondeur - 1, False, a, b)
                    score_max = max(score_max, score)
                self.board.pop()
                a = max(a, score_max)
                if b <= a:
                    break  # Coupure alpha-beta
            return score_max
        else: # on considère que le joueur Min peut jouer n'importe quel coup (on ne sait pas ce qu'il va faire), donc on n'en élimine aucun d'avance
            score_min = float('inf')
            for move in self.board.legal_moves:
                self.board.push(move)
                score = self.minimax(profondeur - 1, True, a, b)
                self.board.pop()
                score_min = min(score_min, score)
                b = min(b, score_min)
                if b <= a:
                    break  # Coupure alpha-beta
            return score_min

    def choisir_move_connu(self, dispoW, dispoB): # renvoie un booléen (coup connu intéressant trouvé ou non) et le coup à jouer (ou None)
        dic_coups = {}
        if dispoW in self.historique and dispoB in self.historique: # si les deux sont dans l'historique, on choisit celui qui a le meilleur score moyen sur le plus de parties
            for move in self.historique[dispoW]:
                if self.board.parse_san(move) in self.board.legal_moves:
                    self.board.push_san(move)
                    dispo = self.get_board_disposition()
                    if dispo[0] in self.donnees_partie["historique_coups"] or dispo[1] in self.donnees_partie["historique_coups"]: # on ne prend que les coups qui n'ont pas encore été joués dans cette partie (pour éviter de tourner en rond)
                        self.board.pop()
                        continue
                    self.board.pop() 
                    dic_coups[move] = self.historique[dispoW][move][0] * 0.8 +  self.historique[dispoW][move][1] * 0.2 
            for move in self.historique[dispoB]:
                if self.board.parse_san(move) in self.board.legal_moves:
                    self.board.push_san(move)
                    dispo = self.get_board_disposition()
                    if dispo[0] in self.donnees_partie["historique_coups"] or dispo[1] in self.donnees_partie["historique_coups"]: 
                        self.board.pop()
                        continue
                    self.board.pop() 
                    dic_coups[move] = self.historique[dispoB][move][0] * 0.8 +  self.historique[dispoB][move][1] * 0.2
        else:
            if dispoW in self.historique:
                dispo = dispoW
            else:
                dispo = dispoB
            
            for move in self.historique[dispo]:
                moveMOVE = chess.Move.from_uci(move) # on convertit le mouvement de str à move pour pouvoir vérifier s'il est légal ou pas
                if moveMOVE in self.board.legal_moves:
                    dic_coups[move] = self.historique[dispo][move][0] * 0.8 +  self.historique[dispo][move][1] * 0.2

        best_move = (None, float("-inf")) # (mouvement, résultat moyen)
        nb_moves = 0
        for move in dic_coups:
            nb_moves += 1
            if dic_coups[move] > best_move[1]:
                best_move = (move, dic_coups[move])
        if best_move[1] > 0.5 or nb_moves == len(list(self.board.legal_moves)):
            # si le meilleur coup a un score moyen supérieur à 0.5, on le joue ou si l'IA connaît déjà tous les coups possibles, donc c'est vraiment le meilleur coup
            return (True, self.board.parse_san(best_move[0])) # passe du str au move
        
        return (False, None) # aucun coup connu n'a l'air intéressant

    def choisir_deplacement(self):
        dispoW, dispoB = self.get_board_disposition() # disposition du plateau pour les blancs et les noirs (pour avoir deux fois plus de chances de le connaître dans l'historique)
        if dispoW in self.historique or dispoB in self.historique:
            a = self.choisir_move_connu(dispoW, dispoB)
            if a[0]: 
                return a[1], dispoW

        # si on ne connaît pas la disposition, ou qu'aucun coup connu n'a l'air intéressant, on fait minimax
        best_moves = []  # liste des meilleurs coups (pour gérer les égalités)
        best_score = float("-inf")
        for move in self.board.legal_moves:
            if dispoW in self.historique:
                if str(move) in self.historique[dispoW]: # on ne peut pas faire "and" car sinon ça va bugué car historique[dispoW] peut ne pas exister
                    continue # on ne teste pas les mouvements déjà connus (car on a déjà vu qu'ils n'étaient pas intéressants)
            if dispoB in self.historique:
                if str(move) in self.historique[dispoB]:
                    continue
            self.board.push(move)
            dispo = self.get_board_disposition()
            if dispo[0] in self.donnees_partie["historique_coups"] or dispo[1] in self.donnees_partie["historique_coups"]: # on ne prend que les coups qui n'ont pas encore été joués dans cette partie (pour éviter de tourner en rond)
                self.board.pop()
                continue
            score = self.minimax(3, False)
            self.board.pop()
            if score > best_score:
                best_score = score
                best_moves = [move]
            elif score == best_score:
                best_moves.append(move)

        if len(best_moves) == 0:
            print(dispoW)
            return (random.choice(list(self.board.legal_moves)), dispoW) # si jamais il n'y a aucun coup possible (ce qui ne devrait pas arriver), on en choisit un au hasard pour éviter de faire planter

        return random.choice(best_moves), dispoW

    def get_board_disposition(self):
        dispoW = ""
        dispoB = [[None for _ in range(8)] for _ in range(8)]
        # Pour la dispoB (black), on inverse les couleurs puis on fait une symétrie centrale (même disposition mais du côté des noirs/blancs)
        for ligne in range(7, -1, -1):
            for colonne in range(8):
                piece = self.board.piece_at(chess.square(colonne, ligne))
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


    def jouer(self):
        # Début de la partie : récupère l'historique des parties et crée un dictionnaire pour la nouvelle partie
        with open('donnees.json', 'r') as fichier:
            self.historique = json.load(fichier)
        self.donnees_partie = {"couleur":"white", "historique_coups":{}, "resultat":None}
        # historique_coups : {"disposition_plateau(str)": "mouvement(str)"}
        # disposition_plateau (ex : début) : "rnbqkbnr,pppppppp,        ,        ,        ,        ,PPPPPPPP,RNBQKBNR"
        # (espace = case vide)

        # On décide qui commence
        ai_color = random.choice([True, False]) # True = l'IA est blanc ; False = l'IA est noir
        print("L'IA joue les " + ("blancs." if ai_color else "noirs."))

        while not self.board.is_game_over():
            #print(board.turn)
            move, dispo = self.choisir_deplacement()
            self.board.push(move)
            print(move)
            
            """if self.board.turn == ai_color: # si c'est le tour de l'IA
                print("\nAI's turn...")
                move, dispo = self.choisir_deplacement()
                self.board.push(move)
                print(move)
            else:
                dispo = self.get_board_disposition()[0]
                while True:
                    move = input("\nUn mouvement (ex : e5e3) : ")
                    try:
                        self.board.push_san(move)
                        break
                    except ValueError:
                        print("C'est invalide, réessayer.")"""

            # Met à jour l'historique des coups
            if dispo not in self.donnees_partie["historique_coups"]: # première fois que cette disposition apparaît
                self.donnees_partie["historique_coups"][dispo] = [str(move)]
            elif str(move) not in self.donnees_partie["historique_coups"][dispo]: # si la disposition est déjà apparue mais pas avec ce coup
                self.donnees_partie["historique_coups"][dispo].append(str(move))
            # si la disposition est déjà apparue avec ce coup, on ne l'ajoute pas à l'historique des coups
        
        # Game over
        #print(board)
        print("game over")
        # On enregistre le résultat pour l'IA
        if self.board.is_checkmate():
            if ai_color != self.board.turn: # si ce n'est pas le tour de l'IA, donc l'IA a gagné
                self.donnees_partie["resultat"] = 1
            elif ai_color == self.board.turn: # si c'est le tour de l'IA, donc l'IA a perdu
                self.donnees_partie["resultat"] = -1
        else: # match nul
            self.donnees_partie["resultat"] = 0
        print(ai_color, self.donnees_partie["resultat"])
        print(self.board)
        # Mise à jour de l'historique des parties
        dic_coups = self.donnees_partie["historique_coups"]
        for i in range(len(dic_coups)):
            disposition = list(dic_coups.keys())[i]
            if disposition not in self.historique:
                res = {}
            else:
                res = self.historique[disposition]
                
            for move in dic_coups[disposition]:
                # Pour savoir quel est le meilleur coup à faire, même si ce n'est pas l'IA qui a joué ce coup 
                # (donc on fait comme si c'était l'IA qui l'avait fait)
                # ça permet d'enregistrer plus rapidement le maximum de dispositions possibles
                if (i%2 == 1 and ai_color) or (i%2 == 0 and not ai_color): # coup de l'adversaire
                    resultat = -1 * self.donnees_partie["resultat"]
                else: # coup de l'IA
                    resultat = self.donnees_partie["resultat"]
                
                if move not in res:
                    res[move] = (resultat, 1) # (moyenne de résultat, nombre de fois joué)
                else:
                    nv_moyenne = (res[move][0]*res[move][1] + resultat) / (res[move][1] + 1)
                    res[move] = (nv_moyenne, res[move][1] + 1)
            self.historique[disposition] = res

        # Fin de la partie : met à jour l'historique et le sauvegarde dans le fichier JSON
        with open("donnees.json", "w") as fichier:
            # on veut un saut à la ligne entre chaque disposition mais pas entre chaque coup
            json.dump(self.historique, fichier, indent=4, separators=(",", ": "))

        self.board.reset() # on réinitialise le plateau pour la prochaine partie

ia = IA_Echecs()
for i in range(10000):
    print("------------------- Partie " + str(i+1) + " ------------------")
    ia.jouer()
