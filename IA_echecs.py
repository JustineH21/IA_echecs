import chess
import json
import random
import time
import bonus_malus as bm

valeur_piece = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 100000} # car ça bug si on fait inf - inf
PIECE_TABLES = bm.PIECE_TABLES
KING_MID_TABLE = bm.KING_MID_TABLE
KING_END_TABLE = bm.KING_END_TABLE

class IA_Echecs:
    def __init__(self):
        self.board = chess.Board()
        self.transpo = {} #- Si cette position a déjà été évaluée auparavant : on réutilise directement le score
                                                                            #  on évite de recalculer tout le sous-arbre
        self.killer_moves = {} #Coups efficaces gardés en mémoire pour explorer moins de possibilités inutiles  
        self.start_time = 0
        self.max_time = 5  # seconde par mouvement

    def get_valeur_positionnelle(self, piece, case):
        """Renvoie valeur positionnelle d'une pièce sur une case donnée"""
        if piece.piece_type == chess.KING:# On utilise une table différente selon la phase de jeu
            nb_pions = len(self.board.pieces(chess.PAWN, chess.WHITE)) + len(self.board.pieces(chess.PAWN, chess.BLACK))
            if nb_pions > 8:  
                table = KING_MID_TABLE  # Milieu de partie
            else:
                table = KING_END_TABLE    # Fin de partie
        else:
            table = PIECE_TABLES.get(piece.piece_type, [0] * 64)
        if piece.color == chess.BLACK: #inverser si piece noire
            case = 63 - case
        if table:
            return table[case]
        else:
            return 0
            
    def score_board(self):
        """Calcule le score pour le joueur blanc, puis inverse si on cherche pour le joueur noir."""
        materiel_blanc = sum(len(self.board.pieces(pt, chess.WHITE)) * valeur_piece[pt] for pt in valeur_piece)
        materiel_noir = sum(len(self.board.pieces(pt, chess.BLACK)) * valeur_piece[pt] for pt in valeur_piece)
        score = materiel_blanc - materiel_noir

        # Bonus d'ouverture (en 15 coups)
        if self.board.fullmove_number < 15:
            score += 0.15 * (
                len(self.board.pieces(chess.KNIGHT, chess.WHITE)) +
                len(self.board.pieces(chess.BISHOP, chess.WHITE))
            )
            score -= 0.15 * (
                len(self.board.pieces(chess.KNIGHT, chess.BLACK)) +
                len(self.board.pieces(chess.BISHOP, chess.BLACK))
            )
        
        # On ne met pas un elif, au cas où il y a moins de 8 pions mais que c'est encore l'ouverture (si on a perdu beaucoup de pions très vite)
        if len(self.board.pieces(chess.PAWN, chess.WHITE)) + len(self.board.pieces(chess.PAWN, chess.BLACK)) <= 8:
            # En fin de partie, le roi devient actif et va plus vers le centre
            case_roi_blanc = self.board.king(chess.WHITE)
            case_roi_noir = self.board.king(chess.BLACK)
        
            # Distance entre les rois (plus ils sont proches, plus l'attaque est facile)
            distance_rois = chess.square_distance(case_roi_blanc, case_roi_noir)
            
            score += (8 - distance_rois) * 2
        
        for square in chess.SQUARES:
            piece = self.board.piece_at(square)
            if piece is not None:
                psq_value = self.get_valeur_positionnelle(piece, square)
                if piece.color == chess.WHITE:
                    score += psq_value
                else:
                    score -= psq_value

        # Nombre de coups possibles
        nb_coups = len(list(self.board.legal_moves))
        if nb_coups > 0:  # seulement si la position n'est pas bloquée
            self.board.push(chess.Move.null())# on fait un mouvement nul pour passer au tour de l'adversaire et calculer le nombre de coups possibles pour lui
            nb_coups_adversaire = len(list(self.board.legal_moves))
            self.board.pop()# on revient à la position d'origine
            score += 0.3 * (nb_coups - nb_coups_adversaire)# on valorise les mouvements qui augmentent le nombre de coups possibles pour l'IA et diminuent ceux de l'adversaire
        
        # Vérifie penalité/bonus liés au fait d'être en échec
        if self.board.is_check():
            if self.board.turn:
                score -= 2
            else:
                score += 2
        
        if self.board.turn:
            return score
        else:
            return -score

    def coup_valeur(self, move):
        """Calcule une valeur initiale pour un coup, utilisée pour trier les coups dans minimax."""
        score = 0
        if self.board.is_capture(move):
            # la valeur du coup est basée sur les pièces capturées
            captured_piece = self.board.piece_at(move.to_square)
            if captured_piece:
                score += valeur_piece[captured_piece.piece_type] * 10
        if move.promotion:
            score += 20
        if self.board.gives_check(move):
            score += 5
        return score

    def quiescence(self, alpha, beta, depth=0):
        """Permet de détecter les positions dangereuses, en continuant le Minimax, mais seulement pour les coups de capture (diminue la complexité)
        Utile par exemple : je gagne une dame, sauf qu’au coup suivant, on me met echec ou mange une piece => ce n'est peut-être pas un bon coup"""
        
        if depth > 5:  # Limite de profondeur pour éviter les recherches trop longues
            return self.score_board()

        # time check
        if time.time() - self.start_time > self.max_time:
            return self.score_board()
        
        stand_pat = self.score_board()
        
        if stand_pat >= beta:
            return beta
        if alpha < stand_pat:
            alpha = stand_pat
        
        
        captures = [move for move in self.board.legal_moves if self.board.is_capture(move)]
        captures.sort(key=self.coup_valeur, reverse=True)
        
        for move in captures:
            self.board.push(move)
            score = -self.quiescence(-beta, -alpha, depth + 1)
            self.board.pop()
            
            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
        
        return alpha

    def minimax(self, profondeur, isMaxTurn, a = float('-inf'), b = float('inf')): 
        """Calcule le score d'une position en utilisant l'algorithme Minimax avec élagage alpha-beta pour réduire la complexité."""
        # time check
        if time.time() - self.start_time > self.max_time:
            return self.score_board()
        
        key = (self.board._transposition_key(), profondeur, isMaxTurn)
        if key in self.transpo:
            return self.transpo[key]
        
       
        if self.board.is_checkmate():
            return float('-inf') if isMaxTurn else float('inf')
        elif self.board.is_game_over():
            return 0  # Partie nulle
        elif profondeur == 0:
            # on fait une quiescience plutôt que de renvoyer directement le score
            score = self.quiescence(a, b)
            self.transpo[key] = score
            return score
        
     
        moves = list(self.board.legal_moves)
        moves.sort(key=self.coup_valeur, reverse=True) # Puisqu'il y a une limite de temps, on commence par les meilleurs
        
        
        killer_key = (self.board._transposition_key(), profondeur)
        if killer_key in self.killer_moves:
            killer = self.killer_moves[killer_key]
            if killer in moves:
                moves.remove(killer)
                moves.insert(0, killer)
        
        if isMaxTurn:
            score_max = float('-inf')
            for i, move in enumerate(moves):
                self.board.push(move)
                score = self.minimax(profondeur - 1, False, a, b)
                self.board.pop()
                
                score_max = max(score_max, score)
                a = max(a, score_max)
                
                if a >= b and i > 0:  
                    self.killer_moves[killer_key] = move
                    break
            
            self.transpo[key] = score_max
            return score_max
        
        else:
            score_min = float('inf')
            for i, move in enumerate(moves):
                self.board.push(move)
                score = self.minimax(profondeur - 1, True, a, b)
                self.board.pop()
                
                score_min = min(score_min, score)
                b = min(b, score_min)
                
                if b <= a:
                    break
            
            self.transpo[key] = score_min
            return score_min

    def choisir_move_connu(self, dispoW, dispoB): # renvoie un booléen (coup connu intéressant trouvé ou non) et le coup à jouer (ou None)
        """Choisit un coup parmi ceux connu : on choisit celui avec la meilleure moyenne de résultat sur un maximum de parties"""
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
                moveMOVE = self.board.parse_san(move) # on convertit le mouvement de str à move pour pouvoir vérifier s'il est légal ou pas
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

    def move_priority(self, move, dispoW, dispoB):
        """Calcule la priorité d'un coup. On valorise les coups connus avec de bons résultats"""
        priority = 0
        if dispoW in self.historique:
            dispo = dispoW  
        else:
            dispo = dispoB
        if dispo in self.historique:
            if str(move) in self.historique[dispo]:
                priority += self.historique[dispo][str(move)][0] * 100
        priority += self.coup_valeur(move)
        return priority

    def choisir_deplacement(self):
        """Choisit le coup à jouer pour l'IA : soit un coup connu dans l'historique, soit le meilleur coup trouvé par minimax."""
        dispoW, dispoB = self.get_board_disposition()# disposition du plateau pour les blancs et les noirs
        
        if dispoW in self.historique or dispoB in self.historique:
            a = self.choisir_move_connu(dispoW, dispoB)
            if a[0]:
                return a[1], dispoW
        
        self.start_time = time.time()
        # si on ne connaît pas la disposition, ou qu'aucun coup connu n'a l'air intéressant, on fait minimax
        max_depth = 6  
        
        if self.board.fullmove_number < 10: # ça permet de faire une meilleure ouverture
            self.max_time = 3
        elif self.board.fullmove_number < 30:
            self.max_time = 5
        else:
            self.max_time = 4
        
        best_moves = []
        for current_depth in range(max_depth):
            # on va de plus en plus profond, pour la gestion du temps
            best_moves_at_depth = []
            best_score_at_depth = float("-inf")
            moves_to_search = list(self.board.legal_moves)
            moves_to_search.sort(key=lambda move: self.move_priority(move, dispoW, dispoB), reverse=True)
            
            for move in moves_to_search:
                if dispoW in self.historique:
                    if str(move) in self.historique[dispoW]:
                        if self.historique[dispoW][str(move)][0] < -0.5 and len([m for m in self.historique[dispoW].values() if m[0] > 0]) > 0:
                            continue
                
                if dispoB in self.historique:
                    if str(move) in self.historique[dispoB]:
                        if self.historique[dispoB][str(move)][0] < -0.5 and len([m for m in self.historique[dispoB].values() if m[0] > 0]) > 0:
                            continue
                
                dispo = self.get_board_disposition()
                if dispo[0] in self.donnees_partie["historique_coups"] or dispo[1] in self.donnees_partie["historique_coups"]:
                    continue
                
                self.board.push(move)
                score = self.minimax(current_depth, False)
                self.board.pop()
                
                if score > best_score_at_depth:
                    best_score_at_depth = score
                    best_moves_at_depth = [move]
                elif score == best_score_at_depth:
                    best_moves_at_depth.append(move)
                
              
                if time.time() - self.start_time > self.max_time:
                    break
            
            best_moves = best_moves_at_depth

            if time.time() - self.start_time > self.max_time:
                break
        
        if not best_moves:
            # au cas où aucun coup n'a été choisi (ce qui ne devrait pas arriver)
            best_moves = list(self.board.legal_moves)
        
        return random.choice(best_moves), dispoW

    def get_board_disposition(self):
        """Renvoie la disposition du plateau pour les blancs, et la même du côté des noirs (pour avoir deux fois plus de chances de la connaître dans l'historique) de type STR"""
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

    def entrainement(self):
        """Lance une partie d'entraînement contre elle-même, met à jour l'historique de ses donnees"""
        # Début de la partie : récupère l'historique des parties et crée un dictionnaire pour la nouvelle partie
        try:
            with open('donnees.json', 'r') as fichier:
                self.historique = json.load(fichier)
        except FileNotFoundError:
            self.historique = {}
        
        self.donnees_partie = {"couleur": "white", "historique_coups": {}, "resultat": None}
        
        ai_color = random.choice([True, False])
        print("L'IA joue les " + ("blancs." if ai_color else "noirs."))
        
        while not self.board.is_game_over():
            move, dispo = self.choisir_deplacement()
            self.board.push(move)
            print(f"Move: {move}")
           
            if dispo not in self.donnees_partie["historique_coups"]:
                self.donnees_partie["historique_coups"][dispo] = [str(move)]
            elif str(move) not in self.donnees_partie["historique_coups"][dispo]:
                self.donnees_partie["historique_coups"][dispo].append(str(move))

        
        print("Game over")
        if self.board.is_checkmate():
            if ai_color != self.board.turn:
                self.donnees_partie["resultat"] = 1
            else:
                self.donnees_partie["resultat"] = -1
        else:
            self.donnees_partie["resultat"] = 0
        
        print(f"AI Color: {ai_color}, Result: {self.donnees_partie['resultat']}")
        print(self.board)
        
        
        dic_coups = self.donnees_partie["historique_coups"]
        for i, disposition in enumerate(dic_coups.keys()):
            if disposition not in self.historique:
                self.historique[disposition] = {}
            
            res = self.historique[disposition]
            
            for move in dic_coups[disposition]:
                if (i % 2 == 1 and ai_color) or (i % 2 == 0 and not ai_color):
                    resultat = -1 * self.donnees_partie["resultat"]
                else:
                    resultat = self.donnees_partie["resultat"]
                
                if move not in res:
                    res[move] = (resultat, 1)
                else:
                    nv_moyenne = (res[move][0] * res[move][1] + resultat) / (res[move][1] + 1)
                    res[move] = (nv_moyenne, res[move][1] + 1)
            
            self.historique[disposition] = res
        
        try:
            with open("donnees.json", "w") as fichier:
                json.dump(self.historique, fichier, indent=4, separators=(",", ": "))
        except:
            # si jamais le fichier n'existe pas, on le crée
            with open("donnees.json", "x") as fichier:
                json.dump(self.historique, fichier, indent=4, separators=(",", ": "))
            
        self.transpo.clear()
        self.killer_moves.clear()
        self.board.reset()

if __name__ == "__main__":
    ia = IA_Echecs()
    
    i = 0
    while True:
        print(f"\n{'='*50}\nPartie {i+1}\n{'='*50}")
        ia.entrainement()
        i += 1