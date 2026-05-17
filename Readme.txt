For better readable format, please see "Blackjack Rules and Beginner Card Counting Guide.docx"
Blackjack Rules and Beginner Card Counting Guide
Disclaimer

This project was created for educational and entertainment purposes only.
It was written during my spare time as a way to stay mentally active and continue practicing Python and Qt5 UI development skills during a long period of unemployment.

This game is NOT intended for gambling or financial gain.
Please play responsibly and understand that gambling always carries risk.

Basic Blackjack Rules
Goal of the Game

The objective of Blackjack is to beat the dealer by getting a hand value closer to 21 without going over 21 ("busting").

Card Values
Card	Value
2 - 10	Face value
J, Q, K	10
Ace	1 or 11

Example:

Ace + King = 21 (Blackjack)
Ace + 6 = 7 or 17
Gameplay Overview
Each player receives two cards.
Dealer also receives two cards:
One face up
One face down
Player chooses actions:
Hit → take another card
Stand → keep current hand
Double Down → double bet and receive one final card
Split → split identical cards into two hands
Note: On Split, first and second card positions are used for the first player's split hand and 3rd and 4th are used for player's 2nd hand.  Please watch message and scores. 
Dealer reveals hidden card after player finishes.
Dealer usually must:
Hit on 16 or less
Stand on 17 or higher
Closest hand to 21 wins.
Blackjack Payouts
Result	Typical Payout
Normal Win	1:1
Blackjack	3:2
Tie (Push)	Bet returned
Bust	Lose bet
Important Strategy Concepts
Dealer Weak Cards

Dealer is considered weak when showing:

4
5
6

In these situations, many players stand more often because the dealer has a higher chance of busting.

Basic Strategy Examples
Your Hand	Dealer Card	Suggested Action
16	10	Hit
12	4	Stand
Ace + 7	6	Double Down
8 + 8	Any	Split
10 + 10	Any	Usually Stand

Basic strategy significantly improves long-term odds compared to random play.

Introduction to Card Counting
What Is Card Counting?

Card counting is a technique used to estimate whether the remaining deck favors:
the player
or the dealer

It does NOT guarantee winning.

It only provides a small statistical advantage under certain conditions.

Simple Hi-Lo Counting System
Count Values
Card	Count Value
2 - 6	+1
7 - 9	0
10, J, Q, K, Ace	-1
How It Works
High Cards Favor the Player

A deck rich in:

10s
Face cards
Aces

improves chances of:

Blackjack payouts
Strong player hands
Dealer busts
Low Cards Favor the Dealer

A deck rich in small cards helps the dealer complete hands safely.

Running Count Example

Suppose these cards appear:

5 → +1
King → -1
3 → +1
8 → 0
Ace → -1

Running Count:
+1 -1 +1 +0 -1 = 0

A positive count generally favors the player.

True Count (Advanced)

In multi-deck games:

True Count = Running Count / Remaining Decks

Example:

Running Count = +8
4 decks remaining

True Count = +2

Advanced players use the True Count instead of only the Running Count.

Important Reality Check

Card counting:

is NOT illegal in most places
does NOT guarantee profit
requires excellent concentration
only provides a small mathematical edge

Casinos may still refuse service to skilled counters.

Most casual players lose money over time regardless of strategy.

About This Project

This Blackjack project was built using:

Python
PyQt5 / Qt Designer

The purpose of this project is:

software practice
UI development learning
keeping the mind active
personal entertainment

Enjoy the game and play responsibly.


Feedback and Bug Reports:

If you find bugs or have suggestions for improvements, please send your feedback to:
blackjackcountingpractice@gmail.com
