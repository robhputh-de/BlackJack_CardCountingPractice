#blackjack.py
# Blackjack — PyQt5 + Qt Designer (.ui file)
# Author: Rob Puth (full rewrite with Double Down & Split)
#
# ARCHITECTURE:
#   Deck        — 5-deck shoe, shuffle, draw, Hi-Lo count
#   Hand        — cards, score, soft/hard ace, bust, blackjack, pair detection
#   Player      — cash, bet, hand(s), split/double state machine
#   BlackjackUI — Qt wiring, game flow, all UI updates
#
# QT DESIGNER WIDGET NAMES REQUIRED:
#   Labels  : dealercard1..5, player{1-4}card{1-5}
#             player{1-4}MSG, player{1-4}score
#             CountLabel, CountLabel1
#   Inputs  : NumPlayer, player{1-4}bet
#   Buttons : ShuffleCards, StartGame
#             HitMeP{1-4}, StayP{1-4}
#             DoubleP{1-4}, SplitP{1-4}   <-- NEW: add these in Qt Designer
#
# SPLIT UI NOTE:
#   After a split, Hand 1 uses card slots 0-1, Hand 2 uses slots 3-4.
#   Slot 2 is hidden as a visual divider between the two split hands.
"""
NOTE: Card Counting Techniqure:
Lower Card 2 to 6 = +1
Mid Card 7 to 9   = 0
A, Jack, queen and king = -1
Number of deck = 5
"""

import sys
import os
import random
import re

from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox, QLabel, QPushButton
from PyQt5.QtGui import QPixmap
from PyQt5 import uic
from PyQt5.QtCore import Qt

from expiry import check_expiry
check_expiry()   # shows dialog and exits if expired

if hasattr(Qt, 'AA_EnableHighDpiScaling'):
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------
CARD_IMAGE_DIR = os.path.join(os.path.dirname(__file__), "Images\\")
BACK_CARD      = "bicycle_blue"


def card_image_path(name: str) -> str:
    return os.path.join(CARD_IMAGE_DIR, f"{name}.png")


# ---------------------------------------------------------------------------
# DECK
# ---------------------------------------------------------------------------
class Deck:
    SUITS             = ["hearts", "clubs", "spades", "diamonds"]
    VALUES            = [str(v) for v in range(2, 11)] + ["jack", "queen", "king", "ace"]
    NUM_DECKS         = 5
    RESHUFFLE_AT      = 10

    def __init__(self):
        self._shoe: list[str] = []
        self.shuffle()

    def shuffle(self):
        single     = [f"{v}_of_{s}" for s in self.SUITS for v in self.VALUES]
        self._shoe = single * self.NUM_DECKS
        random.shuffle(self._shoe)
        #print(f"[Deck] Shuffled — {len(self._shoe)} cards\nCards:{self._shoe}")
        print(f"[Deck] Shuffled — {len(self._shoe)}")

    def draw(self) -> str:
        if len(self._shoe) < self.RESHUFFLE_AT:
            print("[Deck] Low — reshuffling")
            self.shuffle()
        return self._shoe.pop()

    @staticmethod
    def value(card: str) -> int:
        if "ace" in card: return 11
        if any(f in card for f in ("jack", "queen", "king")): return 10
        nums = re.findall(r'\d+', card)
        return int(nums[0]) if nums else 0

    @staticmethod
    def hi_lo_delta(card: str) -> int:
        v = Deck.value(card)
        if v <= 6:  return  1
        if v >= 10: return -1
        return 0


# ---------------------------------------------------------------------------
# HAND
# ---------------------------------------------------------------------------
class Hand:
    def __init__(self):
        self.cards:  list[str] = []
        self._score: int = 0
        self._aces:  int = 0
        """
        NOTE: Card Counting Techniqure:
        Lower Card 2 to 6 = +1
        Mid Card 7 to 9   = 0
        A, Jack, queen and king = -1
        Number of deck = 5
        """

    def add_card(self, card: str):
        self.cards.append(card)
        self._score += Deck.value(card)
        if "ace" in card:
            self._aces += 1
        # Soft -> hard when busting
        while self._score > 21 and self._aces > 0:
            self._score -= 10
            self._aces  -= 1

    @property
    def score(self) -> int:
        return self._score

    @property
    def is_bust(self) -> bool:
        return self._score > 21

    @property
    def is_blackjack(self) -> bool:
        return self._score == 21 and len(self.cards) == 2

    @property
    def is_pair(self) -> bool:
        return (len(self.cards) == 2 and
                Deck.value(self.cards[0]) == Deck.value(self.cards[1]))

    def reset(self):
        self.cards.clear()
        self._score = 0
        self._aces  = 0


# ---------------------------------------------------------------------------
# PLAYER  —  state machine for one seat
# ---------------------------------------------------------------------------
class Player:
    STARTING_CASH = 200
    DEFAULT_BET   = 0

    def __init__(self, index: int):
        self.index = index
        self.cash  = self.STARTING_CASH
        self.cash_prev  = self.cash 
        self.bet   = self.DEFAULT_BET
        self.hand  = Hand()
        self.hand2 = Hand()         # populated after split
        self.split       = False
        self.active_hand = 1        # 1 or 2
        self.hand1_done  = False
        self.hand2_done  = False
        self.doubled     = False

    # ---- properties --------------------------------------------------------

    def current_hand(self) -> Hand:
        return self.hand2 if (self.split and self.active_hand == 2) else self.hand

    @property
    def turn_complete(self) -> bool:
        if self.split:
            return self.hand1_done and self.hand2_done
        return self.hand1_done

    @property
    def can_double(self) -> bool:
        return (len(self.current_hand().cards) == 2 and
                self.cash >= self.bet and
                not self.doubled)

    @property
    def can_split(self) -> bool:
        return (not self.split and
                self.hand.is_pair and
                self.cash >= self.bet)

    # ---- actions -----------------------------------------------------------

    def place_bet(self, amount: int) -> bool:
        if amount <= 0 or amount > self.cash:
            return False
        self.cash -= amount
        self.bet   = amount
        return True

    def do_double(self, card: str):
        self.bet    *= 2
        self.cash   -= self.bet
        self.doubled = True
        self.current_hand().add_card(card)

    def do_split(self, card1: str, card2: str):
        """
        Split pair: Hand 1 keeps first card + gets card1.
                    Hand 2 gets second card + card2.
        Extra bet deducted from cash.
        """
        orig1 = self.hand.cards[0]
        orig2 = self.hand.cards[1]

        self.hand.reset()
        self.hand2.reset()

        self.hand.add_card(orig1)
        self.hand.add_card(card1)

        self.hand2.add_card(orig2)
        self.hand2.add_card(card2)

        self.cash        -= self.bet
        self.split        = True
        #self.bet = 0
        self.active_hand  = 1

    def stand_current(self):
        if self.split and self.active_hand == 1 and not self.hand1_done:
            self.hand1_done  = True
            self.active_hand = 2
        else:
            self.hand1_done = True
            self.hand2_done = True

    def bust_current(self):
        if self.split and self.active_hand == 1 and not self.hand1_done:
            self.hand1_done  = True
            self.active_hand = 2
        else:
            self.hand1_done = True
            self.hand2_done = True

    def reset_round(self):
        self.hand.reset()
        self.hand2.reset()
        self.split       = False
        self.active_hand = 1
        self.hand1_done  = False
        self.hand2_done  = False
        self.doubled     = False


# ---------------------------------------------------------------------------
# MAIN WINDOW
# ---------------------------------------------------------------------------
class BlackjackUI(QMainWindow):

    MAX_PLAYERS    = 4
    MAX_HAND_CARDS = 5

    def __init__(self):
        super().__init__()
        uic.loadUi("blackjackF.ui", self)
        self.setWindowTitle("Blackjack")

        self.deck        = Deck()
        self.num_players = 1
        self.players     = [Player(i) for i in range(1, self.MAX_PLAYERS + 1)]
        self.dealer_hand = Hand()
        self.dealer_hole = ""
        self.hi_lo_count = 0
        self.prev_count   =  self.hi_lo_count
        self.game_active = False
        self.player_place_bet  = False 
        self.not_shuffle       = True 
        self.btn_pressed = [False, False, False, False] 
        self._drag_start_position = None
        self.dealer_payout, self.game_num = 0, 0


        # ---- Widget grids --------------------------------------------------
        from PyQt5.QtWidgets import QLabel, QLineEdit, QPushButton

        self._dealer_labels = [
            self.findChild(QLabel, f"dealercard{i+1}")
            for i in range(self.MAX_HAND_CARDS)
        ]
        self._player_labels = [
            [self.findChild(QLabel, f"player{p+1}card{i+1}")
             for i in range(self.MAX_HAND_CARDS)]
            for p in range(self.MAX_PLAYERS)
        ]
        #print (f"Player label: {self._player_labels}")
        self._cash_labels   = [self.findChild(QLabel,    f"player{p+1}cash")   for p in range(self.MAX_PLAYERS)]
        self._msg_labels   = [self.findChild(QLabel,    f"player{p+1}MSG")   for p in range(self.MAX_PLAYERS)]
        self._score_labels = [self.findChild(QLabel,    f"player{p+1}score") for p in range(self.MAX_PLAYERS)]
        self._bet_inputs   = [self.findChild(QLineEdit, f"player{p+1}bet")   for p in range(self.MAX_PLAYERS)]
        self._btn_hit      = [self.findChild(QPushButton, f"HitMeP{p+1}")   for p in range(self.MAX_PLAYERS)]
        self._btn_stay     = [self.findChild(QPushButton, f"StayP{p+1}")    for p in range(self.MAX_PLAYERS)]
        self._btn_double   = [self.findChild(QPushButton, f"DoubleP{p+1}")  for p in range(self.MAX_PLAYERS)]
        self._btn_split    = [self.findChild(QPushButton, f"SplitP{p+1}")   for p in range(self.MAX_PLAYERS)]
        self._btn_split     = [self.findChild(QPushButton, f"player{p+1}split")    for p in range(self.MAX_PLAYERS)]
        self._btn_double     = [self.findChild(QPushButton, f"player{p+1}double")    for p in range(self.MAX_PLAYERS)]
        self._player_cash_btn= [self.findChild(QLineEdit, f"player{p+1}btnCash")   for p in range(self.MAX_PLAYERS)]

        self.count_label        = self.findChild(QLabel,    "CountLabel")
        self.dealer_score_label = self.findChild(QLabel,    "CountLabel1")
        self.len_shoe           = self.findChild(QLabel, "numCard")
        self.Dealer_PayOutLabel =self.findChild(QLabel, "DealerPayOut")
        self.num_player_input   = self.findChild(QLineEdit, "NumPlayer")
        self.num_player_input.setText(str(self.num_players))
        self.num_deck_input     = self.findChild(QLineEdit, "NumDeck")
        self.num_deck_input.setText(str(Deck.NUM_DECKS))
 
        btn_shuffle = self.findChild(QPushButton, "ShuffleCards")
        btn_start   = self.findChild(QPushButton, "StartGame")

        # Initial Help screen 
        self.helpLabel  = self.findChild(QLabel, "helplabel")
        self.helpLabel.hide() 
        self.toggleButton   = self.findChild(QPushButton, "HelpButton")
        self.toggleButton.clicked.connect(self.toggle_help)

        # Initial Count Label 
        self.countLabel  = self.findChild(QLabel, "countlabel")
        self.countLabel.show()
        self.count_label.show()
        global cntlabel, cntbtn, cntHideText, cntShowText 
        cntlabel = self.countLabel
        cntHideText = "Hide Count"
        cntShowText = "Show Count"
        self.CountButton   = self.findChild(QPushButton, "CountBtn")
        cntbtn = self.CountButton 
        self.CountButton.clicked.connect(self.toggle_label)

        # ---- Signals -------------------------------------------------------
        if self.num_player_input:
            self.num_player_input.returnPressed.connect(self._on_num_players)
            for p in range(self.MAX_PLAYERS):
                if self._bet_inputs[p]:
                    self._bet_inputs[p].setText(f"{Player.DEFAULT_BET}")
        if self.num_deck_input:
            self.num_deck_input.returnPressed.connect(self._on_num_decks)

        for p in range(self.MAX_PLAYERS):
            if self._bet_inputs[p]:
                if not self.game_active and not self.btn_pressed[p]:  
                    #self._bet_inputs[p].returnPressed.connect(lambda _, i=p: self._on_bet_entered(i))
                    self._bet_inputs[p].returnPressed.connect(lambda i=p: self._on_bet_entered(i))
            if self._btn_hit[p]:
                self._btn_hit[p].clicked.connect(lambda _, i=p: self._on_hit(i))
            if self._btn_stay[p]:
                self._btn_stay[p].clicked.connect(lambda _, i=p: self._on_stay(i))
            if self._btn_double[p]:
                self._btn_double[p].clicked.connect(lambda _, i=p: self._on_double(i))
            if self._btn_split[p]:
                self._btn_split[p].clicked.connect(lambda _, i=p: self._on_split(i))

        if btn_shuffle: btn_shuffle.clicked.connect(self._on_shuffle)
        if btn_start:   btn_start.clicked.connect(self._on_start_game)

        self._hide_all_cards()
        self._refresh_cash_displays()
        self._set_action_buttons(False)

    # -----------------------------------------------------------------------
    # UI helpers
    # -----------------------------------------------------------------------

    def toggle_help(self):
        # setHidden(True) hides, setHidden(False) shows
        if self.helpLabel.isHidden():
            self.helpLabel.show()
            self.toggleButton.setText("Hide Help")
        else:
            self.helpLabel.hide()
            self.toggleButton.setText("Show Help")

    def toggle_label(self):
        # setHidden(True) hides, setHidden(False) shows
        if cntlabel.isHidden():
            cntlabel.show()
            self.count_label.show()
            cntbtn.setText(cntHideText)
        else:
            cntlabel.hide()
            self.count_label.hide()
            cntbtn.setText(cntShowText)


    def _hide_all_cards(self):
        for lbl in self._dealer_labels:
            if lbl: lbl.hide()
        for row in self._player_labels:
            for lbl in row:
                if lbl: lbl.hide()

    def _load_pixmap(self, name: str) -> QPixmap:
        px = QPixmap(card_image_path(name))
        if px.isNull():
            print(f"[Warning] Missing: {name}")
        return px

    def _show_card(self, labels: list, slot: int, name: str):
        if slot < len(labels) and labels[slot]:
            labels[slot].setPixmap(self._load_pixmap(name))
            labels[slot].show()
            #print (f"Label: {labels[slot]}")

    def _set_player_msg(self, p: int, text: str):
        if self._msg_labels[p]: self._msg_labels[p].setText(text)

    def _set_player_cash(self, p: int, text: str):
        if self._cash_labels[p]: self._cash_labels[p].setText(text)
        
    def _set_player_score(self, p: int, score: int):
        if self._score_labels[p]: self._score_labels[p].setText(f"Score: {score}")

    def _refresh_cash_displays(self):
        for p, player in enumerate(self.players):
            self._set_player_cash(p, f"Cash: ${player.cash}")
            
    def _reset_bet (self):
         for p, player in enumerate(self.players):
            if self._bet_inputs[p]:
                self._bet_inputs[p].setText(f"{Player.DEFAULT_BET}")
                self.btn_pressed[p] = False  

    def _update_count(self, card: str):
        #self.prev_count = self.hi_lo_count
        self.hi_lo_count += Deck.hi_lo_delta(card)
        if self.count_label:
            self.count_label.setText(f"Count: {self.hi_lo_count}\nPrvCount: {self.prev_count} ")
            #self.count_label.setText(f"Count: {self.hi_lo_count} ")
    
    def _update_DPayOut (self):
        self.Dealer_PayOutLabel.setText(f"${self.dealer_payout}\n Game#{self.game_num}") 

    def _set_action_buttons(self, enabled: bool, p_idx: int = -1):
        """
        Enable/disable action buttons for all players or just one.
        Double and Split are enabled only when game rules allow.
        """
        targets = range(self.MAX_PLAYERS) if p_idx < 0 else [p_idx]
        for p in targets:
            active = enabled and (p < self.num_players)
            player = self.players[p]
            for btn in (self._btn_hit[p], self._btn_stay[p]):
                if btn: btn.setEnabled(active)
            if self._btn_double[p]:
                self._btn_double[p].setEnabled(active and player.can_double)
            if self._btn_split[p]:
                self._btn_split[p].setEnabled(active and player.can_split)

    def _next_slot(self, player: Player, hand: Hand) -> int:
        """
        Card label slot for the next card drawn, accounting for split layout.
        Hand 1: slots 0, 1, 2
        Hand 2: slots 3, 4   (slot 2 is the visual gap)
        """
        if player.split and player.active_hand == 2:
            return 3 + (len(hand.cards) - 1)
        return len(hand.cards) - 1

    # -----------------------------------------------------------------------
    # Slots — actions
    # -----------------------------------------------------------------------

    def _on_num_players(self):
        try:
            n = int(self.num_player_input.text())
            if 1 <= n <= self.MAX_PLAYERS:
                self.num_players = n
                print(f"[Game] Players: {n}")
            else:
                QMessageBox.warning(self, "Invalid", f"Enter 1 to {self.MAX_PLAYERS}.")
        except ValueError:
            QMessageBox.warning(self, "Invalid", "Please enter a valid number.")
    def _on_num_decks(self):
        #number of deck should be 6 or less
        try : 
            n = int(self.num_deck_input.text())
            if 1 <= n <= 6 :
                Deck.NUM_DECKS = n
                print (f"Num of Decks: {Deck.NUM_DECKS}")
            else:
                QMessageBox.warning(self, "Invalid", f"Enter 1 to 6.")
        except ValueError:
            QMessageBox.warning(self, "Invalid", "Please enter a valid number.")

    def _on_bet_entered(self, p: int):
        player = self.players[p]
        inp    = self._bet_inputs[p]
        self.player_place_bet = True 
        if not inp: return
        try:
            amount = int(inp.text())
            if amount < 5 :
                QMessageBox.warning(self, "Invalid Bet!", f"Minimum Bet must be $5–${player.cash}\nPress Play again to change bet.")
                return 
            if player.place_bet(amount) and not self.btn_pressed [p]:
                self._set_player_cash(p, f"Cash: ${player.cash}")
                print (f"Player: {p+1} bet: ${amount}")
                self.btn_pressed [p]= True 
            else:
                QMessageBox.warning(self, "Invalid Bet or bet has already entered", f"Bet must be $1–${player.cash}\nPress Play again to change bet.")
                return
        except ValueError:
            QMessageBox.warning(self, "Invalid", "Enter a numeric bet.")

    def _on_shuffle(self):
        self.deck.shuffle()
        self.hi_lo_count = 0
        self.not_shuffle = False
        if self.count_label: self.count_label.setText("Count: 0")
        if self.len_shoe : self.len_shoe.setText(f"NumCards:{len(self.deck._shoe)}")
        self._hide_all_cards()
        self._set_action_buttons(False)
        self.game_active = False

    def _on_start_game(self):
        if not self.deck._shoe or self.not_shuffle :
            QMessageBox.information(self, "Shuffle first", "Please shuffle the deck first.")
            return
        if not self.player_place_bet :
            QMessageBox.information(self, "Place bet first", "Please place your bet first.")
            return
        self._start_round()

    def _on_hit(self, p: int):
        if not self.game_active: return
        player = self.players[p]
        if player.turn_complete: return
        hand = player.current_hand()
        if len(hand.cards) >= self.MAX_HAND_CARDS: return

        card = self.deck.draw()
        if self.len_shoe : self.len_shoe.setText(f"NumCards:{len(self.deck._shoe)}")
        hand.add_card(card)
        self._update_count(card)
        self._show_card(self._player_labels[p], self._next_slot(player, hand), card)
        self._set_player_score(p, hand.score)
        self._set_action_buttons(True, p)   # refreshes double/split eligibility

        if hand.is_bust:
            self._set_player_msg(p, "BUST! ")
            player.bust_current()
            if player.split and not player.turn_complete:
                self._set_player_msg(p, f"Hand 1 bust — play Hand 2")
                self._set_player_score(p, player.hand2.score)
                self._set_action_buttons(True, p)
            else:
                self._check_all_done()
        elif hand.score == 21:
            self._on_stay(p)
        self._check_all_done()

    def _on_stay(self, p: int):
        if not self.game_active: return
        player = self.players[p]
        if player.turn_complete: return
        score = player.current_hand().score
        player.stand_current()

        if player.split and not player.turn_complete:
            self._set_player_msg(p, f"Hand 1 stands ({score}) — play Hand 2")
            self._set_player_score(p, player.hand2.score)
            self._set_action_buttons(True, p)
        else:
            self._set_player_msg(p, f"Standing — {score}")
            self._check_all_done()
        if player.turn_complete or not player.can_double: return 
            #if p >= self.MAX_PLAYERS:
                #self._run_dealer()
        #this line below may never get executed but just in case
        #if p == self.MAX_PLAYERS:
            #self._run_dealer()
        #self._check_all_done()

    def _on_double(self, p: int):
        if not self.game_active: return
        player = self.players[p]
        if player.turn_complete or not player.can_double: return

        card = self.deck.draw()
        if self.len_shoe : self.len_shoe.setText(f"NumCards:{len(self.deck._shoe)}")
        player.do_double(card)
        self._update_count(card)
        hand = player.current_hand()
        self._show_card(self._player_labels[p], self._next_slot(player, hand), card)
        self._set_player_score(p, hand.score)
        self._set_player_msg(p, f"Doubled — Score: {hand.score}  Total Bet: ${player.bet}")

        # Double always ends the turn
        player.stand_current()
        self._set_action_buttons(False, p)
        #if p >= self.MAX_PLAYERS:
            #self._run_dealer()
        self._check_all_done()

    def _on_split(self, p: int):
        if not self.game_active: return
        player = self.players[p]
        if player.turn_complete or not player.can_split: return

        card1 = self.deck.draw()
        if self.len_shoe : self.len_shoe.setText(f"NumCards:{len(self.deck._shoe)}")
        card2 = self.deck.draw()
        if self.len_shoe : self.len_shoe.setText(f"NumCards:{len(self.deck._shoe)}")
        self._update_count(card1)
        self._update_count(card2)

        player.do_split(card1, card2)

        labels = self._player_labels[p]
        # Hand 1: slots 0 and 1
        self._show_card(labels, 0, player.hand.cards[0])
        self._show_card(labels, 1, player.hand.cards[1])
        # Visual gap: hide slot 2
        if labels[2]: labels[2].hide()
        # Hand 2: slots 3 and 4
        self._show_card(labels, 3, player.hand2.cards[0])
        self._show_card(labels, 4, player.hand2.cards[1])

        self._set_player_score(p, player.hand.score)
        self._set_player_msg(
            p, f"Split!  Hand 1: {player.hand.score}  |  Hand 2: {player.hand2.score}")
        self._set_action_buttons(True, p)
        self._check_all_done()

    # -----------------------------------------------------------------------
    # Round flow
    # -----------------------------------------------------------------------

    def _start_round(self):
        self.game_active = True
        self.setWindowTitle("Blackjack — 21")
        self.game_num +=1
        for player in self.players[:self.num_players]:
            player.reset_round()
        self.dealer_hand = Hand()
        self.dealer_hole = ""

        self._hide_all_cards()
        self._refresh_cash_displays()
        self._update_DPayOut()

        # Deal 2 cards per player
        for p in range(self.num_players):
            player = self.players[p]
            self._set_player_msg(p, "")
            for c in range(2):
                card = self.deck.draw()
                if self.len_shoe : self.len_shoe.setText(f"NumCards:{len(self.deck._shoe)}")
                player.hand.add_card(card)
                self._update_count(card)
                self._show_card(self._player_labels[p], c, card)
            self._set_player_score(p, player.hand.score)
            if player.hand.is_blackjack:
                self._set_player_msg(p, "BLKJACK!")
                self._refresh_cash_displays()
                player.stand_current()

        # Dealer: hole (hidden) + visible
        self.dealer_hole = self.deck.draw()
        if self.len_shoe : self.len_shoe.setText(f"NumCards:{len(self.deck._shoe)}")
        #self._update_count(self.dealer_hole)  #Don't count the hidden card
        self._show_card(self._dealer_labels, 0, BACK_CARD)

        visible = self.deck.draw()
        if self.len_shoe : self.len_shoe.setText(f"NumCards:{len(self.deck._shoe)}")
        self.dealer_hand.add_card(visible)
        self._update_count(visible)
        self._show_card(self._dealer_labels, 1, visible)
        if self.dealer_score_label:
            self.dealer_score_label.setText(f"Dealer: {self.dealer_hand.score} + ?")

        self._set_action_buttons(True)
        self._check_all_done()

    def _check_all_done(self):
        if all(self.players[p].turn_complete for p in range(self.num_players)):
            self._set_action_buttons(False)
            self._run_dealer()

    def _run_dealer(self):
        # Reveal hole card
        self.dealer_hand.add_card(self.dealer_hole)
        if self._dealer_labels[0]:
            self._dealer_labels[0].setPixmap(self._load_pixmap(self.dealer_hole))
            self._dealer_labels[0].show()
            self._update_count(self.dealer_hole) #Count when card is revealed 
        if self.dealer_score_label:
            self.dealer_score_label.setText(f"Dealer: {self.dealer_hand.score}")

        # Draw to 17+
        slot = 2
        while self.dealer_hand.score < 17 and slot < self.MAX_HAND_CARDS:
            card = self.deck.draw()
            if self.len_shoe : self.len_shoe.setText(f"NumCards:{len(self.deck._shoe)}")
            self.dealer_hand.add_card(card)
            self._update_count(card)
            self._show_card(self._dealer_labels, slot, card)
            if self.dealer_score_label:
                self.dealer_score_label.setText(f"Dealer: {self.dealer_hand.score}")
            slot += 1

        self._resolve_round()
        self._refresh_cash_displays()
        self._reset_bet ()
        self._update_DPayOut()
        self.player_place_bet = False 
        self.prev_count = self.hi_lo_count #Set current count to prev at the end of each game
        QMessageBox.information(self,"Press play for next round!", "Blackjack — Round over. Play again or shuffle.") 

    def _resolve_round(self):
        ds          = self.dealer_hand.score
        dealer_bust = self.dealer_hand.is_bust

        for p in range(self.num_players):
            player = self.players[p]
            #player.cash_prev =  player.cash 
            if player.split:
                # Settle both hands independently
                msg1 = self._settle_hand(player, player.hand,  player.bet, dealer_bust, ds)
                msg2 = self._settle_hand(player, player.hand2, player.bet, dealer_bust, ds)
                self._set_player_msg(p, f"H1: {msg1}  |  H2: {msg2}  Cash: ${player.cash}")
            elif player.doubled :
                #player.bet += player.bet
                msg = self._settle_hand(player, player.hand,  player.bet, dealer_bust, ds)
                self._set_player_msg(p, f"{msg}")
            else:
                msg = self._settle_hand(player, player.hand, player.bet, dealer_bust, ds)
                #self._set_player_msg(p, f"{msg}: ${player.bet}")
                self._set_player_msg(p, f"{msg}")
                
        self._refresh_cash_displays()

        if player.cash <= 0:
            self._set_player_msg(p, "Out of chips!")

        self.game_active = False
        """for p in range(self.num_players):
            player = self.players[p]
            player.cash_prev =  player.cash """
        [setattr(p, 'cash_prev', p.cash) for p in self.players]
        text = ("Blackjack — Round over. Play again or shuffle.")
        self.setWindowTitle(text)
        #QMessageBox.information(self,"Press play for next round!", text)

    def _settle_hand(self, player: Player, hand: Hand,
                     bet: int, dealer_bust: bool, ds: int) -> str:
        """
        Settle one hand vs. dealer. Adjusts player.cash in place.
        Returns a short result string.
        """
        #self.btn_pressed [p]= False
        ps = hand.score
        player.cash = player.cash_prev
        if hand.is_bust:
            player.cash -= bet 
            self.dealer_payout -= bet 
            return "BUST"
        elif hand.is_blackjack:
            win = int(bet * 1.5)
            #player.cash += bet + win
            player.cash += win
            self.dealer_payout += bet + win
            return f"BLKJACK+${win}"
        elif dealer_bust:
            player.cash += bet
            self.dealer_payout += bet
            return f"WIN +${bet}"
        elif ps > ds:
            player.cash += bet 
            self.dealer_payout += bet
            return f"WIN +${bet}"
        elif ps == ds:
            return "PUSH"
        else:
            player.cash -= bet 
            self.dealer_payout -= bet
            return f"LOSE -${bet}"


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app    = QApplication(sys.argv)
    window = BlackjackUI()
    window.show()
    sys.exit(app.exec_())
    