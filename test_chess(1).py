import chess
import random
import json

board = chess.Board()
"""
i = 0
while i < 100:
    choix = list(board.legal_moves)[0]
    #print(choix)
    board.push(choix)
    i+=1

print(board.is_check())
print(board)"""

def choisir_deplacement(deplacements, historique):
    

def jouer():
    donnees_partie = {"couleur":None, "coups_blancs":[], "coups_noirs":[], "resultat":None, "score":0}
    with open('Untitled-1.json', 'r', encoding='utf-8') as fichier:
        historique = json.load(fichier)
    
    deplacements = board.legal_moves
    choix = choisir_deplacement(deplacements, historique)
    board.push(choix)
    donnees_partie["coups_blancs"].append(choix)

    # rajoute les données de la partie au fichier json
    with open('Untitled-1.json', 'w') as fichier:
        a = "partie"+str(len(historique)+1)
        historique[a] = donnees_partie
        for partie in historique:
            print(partie)
        json.dump(historique, fichier, indent=4)

jouer()