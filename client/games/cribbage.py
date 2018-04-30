#!/usr/bin/env python
# vim: sw=4 ai expandtab
# Cribbage game
# Copyright 2018, Mitch Patenaude

import cards
import logging
import random
import sys
from utils import mk_print_list

class Hand(list):
    def __str__(self):
        if len(self) == 0:
            return 'an empty hand'
        else:
            return mk_print_list(self)

    def discard(self, card):
        for i, hand_card in enumerate(self):
            if hand_card == card:
                del self[i]
                return card
        return None

class GameOver(Exception):
    pass

class Player(object):
    def __init__(self, winning_score=121):
        self.winning_score = winning_score
        self.reset()

    def reset(self):
        self.score = 0
        self.hand = Hand()

    def scores(self, amount):
        self.score += amount
        if self.score >= self.winning_score:
            raise GameOver()

class AIPlayer(Player):
    pass

def sublists(input_list, size):
    if not input_list or size <= 0:
        return [[],]
    if size >= len(input_list):
        return [input_list,]
    ret_list = []
    for index in xrange(len(input_list)-size+1):
        for sublist in sublists(input_list[index+1:], size-1):
            ret_list.append( input_list[index:index+1] + sublist )
    return ret_list

_n_kind_score = {2: 2, 3: 6, 4: 12}

card_names = {
    'ace': 'ace',
    '2': 'deuce',
    '3': 'three',
    '4': 'four',
    '5': 'five',
    '6': 'six',
    '7': 'seven',
    '8': 'eight',
    '9': 'nine',
    '10': 'ten',
    'jack': 'jack',
    'queen': 'queen',
    'king': 'king',
}

def is_run(cardlist):
    'Is the list a run'
    cardlist.sort(key=lambda x: x._rank)
    for idx in range(len(cardlist) - 1):
        if cardlist[idx]._rank + 1 != cardlist[idx+1]._rank:
            return False
    return True

def card_value(card):
    if card._rank >= 10:
        return 10 
    else:
        return card._rank

def sum_cards(cardlist):
    card_sum = 0
    for card in cardlist:
        card_sum += card_value(card)
    return card_sum

def count_hand(hand, crib_card, is_crib=False):
    msgs = []
    count = 0

    # Check for 15s
    num_15s = 0
    for sublist_size in range(5, 1, -1):
        for sublist in sublists([crib_card] + hand, sublist_size):
            if sum_cards(sublist) == 15:
                num_15s += 1
    if num_15s > 0:
        count += 2*num_15s
        msgs.append(('{} fifteen{}'.format(num_15s, '' if num_15s == 1 else 's'), None, 2*num_15s))

    # Check for flush
    suits = set()
    for card in hand:
        suits.add(card.suit)
    if len(suits) == 1:
        if crib_card.suit in suits:
            count += 5
            msgs.append(('flush royal', crib_card.suit, 5))
        elif not is_crib:
            count += 4
            msgs.append(('flush', suits.pop(), 4))

    # Check for <n> of a kind
    n_kind_exclusion = set()
    for sublist_size in range(4, 1, -1):
        for sublist in sublists([crib_card] + hand, sublist_size):
            subset = frozenset(sublist)
            if subset in n_kind_exclusion:
                continue
            rankset = set()
            for card in subset:
                rankset.add(card.rank)
            if len(rankset) == 1:
                score =  _n_kind_score[sublist_size]
                count += score
                if sublist_size == 2:
                    msgs.append(('pair', card_names[str(rankset.pop())] + 's', 2))
                else:
                    msgs.append(('{} of a kind'.format(sublist_size), card_names[str(rankset.pop())] + 's', score))
                    # Now prevent subsets 
                    for size_prime in range(sublist_size-1, 1, -1):
                        for sublist_prime in sublists(sublist, size_prime):
                            n_kind_exclusion.add(frozenset(sublist_prime))

    # Check for runs of <n>
    run_found = False
    run_exclusions = set()
    for sublist_size in range(5, 2, -1):
        for sublist in sublists([crib_card] + hand, sublist_size):
            sublist.sort(key=lambda x: x._rank)
            if tuple(sublist) in run_exclusions:
                continue
            if is_run(sublist):
                count += sublist_size
                msgs.append(('run of {}'.format(sublist_size), '{} to {}'.format(card_names[sublist[0].rank],card_names[sublist[-1].rank]), sublist_size))
                if sublist_size > 3:
                    for x in range(3,sublist_size):
                        for y in range(sublist_size-x+1):
                            run_exclusions.add(tuple(sublist[y:y+x]))

    # Check for nobs
    if crib_card.rank != 'jack':
        for card in hand:
            if card.rank == 'jack' and card.suit == crib_card.suit:
                count += 1
                msgs.append(('nobs', None, 1))
                break

    return count, msgs

class Cribbage(object):
    def __init__(self):
        self.player = Player()
        self.ai = AIPlayer()
        self.crib_card = None
        self.crib = Hand()
        self.pegging_stack = []
        self.deck = cards.Deck()
        self.deck.shuffle()

    def chooseFirstCrib(self):
        player_card = None
        while player_card is None:
            player_card = self.deck.deal()
            ai_card = self.deck.deal()
            if player_card.rank == ai_card.rank:
                player_card = None
        self.players_crib = player_card._rank < ai_card._rank
        return player_card, ai_card

    def dealHands(self):
        self.player.hand = Hand()
        self.ai.hand = Hand()
        self.crib = Hand()
        self.crib_card = None
        self.deck.shuffle()
        for _ in xrange(6):
            self.player.hand.append(self.deck.deal())
            self.ai.hand.append(self.deck.deal())

    def pickCribCard(self):
        self.crib_card = self.deck.deal()
        return self.crib_card

    def switchCrib(self):
        self.players_crib = not self.players_crib

def pick_best_discards(hand, my_crib, discards=None, best_score=-100, sample_size=10, full_deck=cards.Deck()):
    deck = filter(lambda x: x not in hand, full_deck.cards)
    sample_crib_cards = random.sample(deck, sample_size+2)
    crib_extras = sample_crib_cards[sample_size:]
    sample_cirb_cards = sample_crib_cards[:sample_size]
    for card1, card2 in sublists(hand, 2):
        new_score=0
        for tmp_crib in sample_crib_cards:
            tmp_hand = Hand(hand[:])
            tmp_hand.discard(card1)
            tmp_hand.discard(card2)
            score, msgs = count_hand(tmp_hand, tmp_crib, False)
            crib_score, msgs = count_hand(Hand([card1, card2] + crib_extras), tmp_crib, True)
            if my_crib:
                new_score += score + crib_score
            else:
                new_score += score - crib_score
        if new_score > best_score:
            discards = [card1, card2]
            best_score = new_score
    return discards
            

if __name__ == '__main__':

    def dump(hand, crib_card, is_crib=False):
        print(str(hand))
        s, m = count_hand(hand, crib_card, is_crib)
        print('Score: {}'.format(s))
        for x, y, z in m:
            if y is not None:
                print('{} of {} for {}'.format(x, y, z))
            else:
                print('{} for {}'.format(x, z))
        return s


    game = Cribbage()

    player_card, ai_card = game.chooseFirstCrib()
    print('Player cuts a {} and computer cuts a {}'.format(player_card, ai_card))

    try:
        hand_num = 0
        while game.player.score < 121 and game.ai.score < 121:
            hand_num += 1
            print('')
            print('Hand #{}'.format(hand_num))

            print('It\'s {}\'s crib.'.format('player' if game.players_crib else 'computer'))
            if game.players_crib:
                crib_player = game.player
                noncrib_player = game.ai
            else:
                crib_player = game.ai
                noncrib_player = game.ai

            game.dealHands()
            print('You got {:s}'.format(game.player.hand))

            # player_discards = random.sample(game.player.hand, 2)
            player_discards = pick_best_discards(game.player.hand, game.players_crib)

            ai_discards = pick_best_discards(game.ai.hand, not game.players_crib)

            print('You discarded {} and {}'.format(player_discards[0], player_discards[1]))
            for card in player_discards:
                game.crib.append(game.player.hand.discard(card))
            print('Leaving you with {}'.format(game.player.hand))

            for card in ai_discards:
                game.crib.append(game.ai.hand.discard(card))

            print('')
            game.pickCribCard()
            print('crib card: {:s}'.format(game.crib_card))
            if game.crib_card.rank == 'jack':
                crib_player.scores(2)
                print('{} scores 2 for his heels'.format('Player' if game.players_crib else 'Computer'))

            print('')
            if game.players_crib:
                print('Computer hand:')
                ai_score = dump(game.ai.hand, game.crib_card, False)
                game.ai.scores(ai_score)
                print('')
                print('Player hand:')
                player_score = dump(game.player.hand, game.crib_card, False)
                game.player.scores(player_score)
            else:
                print('Player hand:')
                player_score = dump(game.player.hand, game.crib_card, False)
                game.player.scores(player_score)
                print('')
                print('Computer hand:')
                ai_score = dump(game.ai.hand, game.crib_card, False)
                game.ai.scores(ai_score)
            print('')
            print('Crib:')
            crib_score = dump(game.crib, game.crib_card, True)
            crib_player.scores(crib_score)

            game.switchCrib()

            print('')
            print('Scores: player {} computer {}'.format(game.player.score, game.ai.score))

    except GameOver:
        pass

    print('Final scores: player {} computer {}'.format(game.player.score, game.ai.score))

    if game.player.score == game.ai.score:
        # impossible
        print('Tie')
    elif game.player.score > game.ai.score:
        print('Player wins')
        if game.ai.score < 61:
            print('Double Skunk!')
        elif game.ai.score < 91:
            print('Skunk!')
    else:
        print('Computer wins')
        if game.player.score < 61:
            print('Double Skunk!')
        elif game.player.score < 91:
            print('Skunk!')
