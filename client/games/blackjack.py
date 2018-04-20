#!/usr/bin/env python
# vim: sw=4 ai expandtab
# Blackjack game
# Copyright 2018, Mitch Patenaude

import logging
import random
import sys

def mk_print_list(l, conjunction='and'):
    '''Makes a list of elements with of the form "a, b, c <conjucntion> d"'''

    if len(l) == 0:
        return ''
    if len(l) == 1:
        return str(l[0])
    else:
        return '{0} {1} {2}'.format(', '.join([str(w) for w in l[:-1]]), conjunction, l[-1])

class Card(object):
    suits = ['clubs', 'hearts', 'diamonds', 'spades']

    def __init__(self, rank, suit):
        if rank < 1 or rank > 13:
            raise ValueError('Bad rank {0}'.format(rank))
        self._rank = rank
        if suit not in self.suits:
            raise ValueError('Unknown suit {0}'.format(suit))
        self.suit = suit

    @property
    def rank(self):
        if self._rank == 1:
            return 'ace'
        elif self._rank == 11:
            return 'jack'
        elif self._rank == 12:
            return 'queen'
        elif self._rank == 13:
            return 'king'
        else:
            return str(self._rank)

    def __str__(self):
        return '{0} {1} of {2}'.format('an' if self._rank in [1, 8] else 'a', self.rank, self.suit)

    def __repr__(self):
        return '{0}({1}, {2})'.format(self.__class__.__name__, self._rank, repr(self.suit))

class Deck(object):
    def __init__(self):
        self.cards = []
        for suit in Card.suits:
            for rank in range(1,14):
                self.cards.append(Card(rank, suit))
        self.index = 0

    def shuffle(self):
        self.index = 0
        random.shuffle(self.cards)

    def deal(self):
        if self.index >= len(self.cards):
            raise StopIteration()
        card = self.cards[self.index]
        self.index += 1
        return card

    def cardsLeft(self):
        return len(self.cards) - self.index

    def __iter__(self):
        for card in self.cards:
            yield card

class Hand(list):
    def __init__(self, bet, *args, **kwargs):
        super(Hand, self).__init__(*args, **kwargs)
        self.bet = bet

    def __str__(self):
        if len(self) == 0:
            return 'an empty hand'
        else:
            return mk_print_list(self)

def _count(hand):
    aces = 0
    count = 0
    for card in hand:
        if card._rank == 1:
            aces += 1
            count += 11
        elif card._rank >= 10:
            count += 10
        else:
            count += card._rank
    for x in range(aces):
        if count > 21:
            count -= 10
    return count

class InsufficientFunds(Exception):
    pass

class Bank(object):
    def __init__(self, num, initial_balance=100):
        self.balances = [initial_balance for _ in range(num+1)]

    def withdraw(self, player, amount):
        if self.balances[player] < amount:
            raise InsufficientFunds('Insufficient funds')
        self.balances[player] -= amount

    def deposit(self, player, amount):
        self.balances[player] += amount

    def balance(self, player):
        return self.balances[player]


class Dealer(object):
    def __init__(self, num_players, initial_balance=100, min_bet=10):
        self.deck = Deck()
        self.deck.shuffle()
        self.num_players = num_players
        self.initial_balance = initial_balance
        self.min_bet = min_bet
        self.bank = Bank(num_players + 1, initial_balance)
        self.bank.deposit(0, 99*initial_balance) # house has lots of money
        self.hands = {}

    def deal(self, min_bet=10):
        # hand #0 is the dealer
        num_hands = self.num_players + 1
        if (num_hands * 4) > self.deck.cardsLeft():
            self.deck.shuffle()
        self.hands = {}
        for player in range(num_hands):
            if self.bank.balance(player) >= self.min_bet:
                self.bank.withdraw(player, self.min_bet)
                self.bank.deposit(0, self.min_bet)
                self.hands[player] = [Hand(self.min_bet)]

        for c in range(2):
            for h in self.hands.keys():
                self.hands[h][0].append(self.deck.deal())

    def players(self):
        return sorted(list(filter(lambda x: x != 0, self.hands.keys())))

    def hand(self, player, hand=0):
        return self.hands[player][hand]

    def num_hands(self, player):
        return len(self.hands[player])

    def count(self, player, hand=0):
        return _count(self.hand(player, hand));

    def hit(self, player, hand=0):
        new_card = self.deck.deal()
        self.hands[player][hand].append(new_card)
        return new_card, self.count(player, hand)

    def split(self, player, hand):
        self.bank.withdraw(player, self.hands[player][hand].bet)
        self.bank.deposit(0, self.hands[player][hand].bet)
        new_hand = Hand(self.hands[player][hand].bet)
        new_hand.append(self.hands[player][hand][1])
        self.hands[player][hand][1] = self.deck.deal()
        self.hands[player].append(new_hand)
        self.hit(player, -1)

def read_line():
    return sys.stdin.readline()

def myprint(str):
    print(str)

def read_int(low_limit=None, high_limit=None, input_func=read_line, output_func=myprint):
    retval = None
    while retval is None:
        val = input_func().strip().lower()
        try:
            retval = int(val)
            if low_limit is not None and retval < low_limit:
                output_func('Too low, Please choose a number of {0} or greater'.format(low_limit))
                retval = None
            elif high_limit is not None and retval > high_limit:
                output_func('Too high, Please choose a number of {0} or less'.format(high_limit))
                retval = None
        except ValueError:
            output_func('{0} isn\'t a number.'.format(val))
    return retval

def read_answer(valid, input_func=read_line, output_func=myprint):
    retval = None
    while retval is None:
        retval = input_func().strip().lower()
        if retval in valid:
            return retval
        matches = list(filter(lambda x: x.startswith(retval), valid))
        if len(matches) > 1:
            output_func('{0} is ambiguous, could match {1}'.format(retval, mk_print_list(matches, 'or')))
            retval = None
        elif len(matches) == 0:
            output_func('{0} isn\'t one of {1}'.format(retval,mk_print_list(valid, 'or')))
            retval = None
    return matches[0]

ordinal = {1: 'first', 2: 'second', 3: 'third', 4: 'fourth'}

def play(input_func=read_line, output_func=myprint):
    '''
plays a game of blackjack with up to 10 players.
Pass input_func and output_func with appropriate vectors for other implementations.
    '''

    output_func('How many players?')
    n = read_int(low_limit=1, high_limit=10, input_func=input_func, output_func=output_func)
    dealer = Dealer(n)
    output_func('Everybody starts with ${0}.  Standard bet is ${1}'.format(dealer.initial_balance, dealer.min_bet))

    keep_playing = 'yes'
    while keep_playing == 'yes':
        dealer.deal(n)
        players = dealer.players()
        if not players:
            output_func('Everybody is broke!')
            break
        output_func('Dealer has a face down card and {0}'.format(str(dealer.hand(0)[1])))
        for player in range(1, n+1):
            if player not in players:
                output_func('Player {0} has insufficient funds to play this round'.format(player))
                continue
            hand_num = 0
            while hand_num < dealer.num_hands(player):
                count = dealer.count(player, hand_num)
                output_func('{0}layer {1} has {2} with a count of {3}'.format(
                    '{0} hand of p'.format(ordinal[hand_num +1].capitalize()) if hand_num > 0 else 'P',
                    player,
                    dealer.hand(player, hand_num),
                    count))
                done = False
                while not done:
                    options = ['hit', 'stand']
                    if len(dealer.hand(player, hand_num)) == 2:
                        options.append('double')
                        if dealer.hand(player, hand_num)[0].rank == dealer.hand(player, hand_num)[1].rank:
                            options.append('split')
                    if count < 21:
                        output_func('{0}?'.format(mk_print_list(options, 'or')))
                        ans = read_answer(options, input_func=input_func, output_func=output_func)
                        if ans == 'split':
                            try:
                                dealer.split(player, hand_num)
                                count = dealer.count(player, hand_num)
                                output_func('{0} hand of player {1} now has {2} with a count of {3}'.format(
                                    ordinal[hand_num + 1].capitalize(),
                                    player,
                                    dealer.hand(player, hand_num),
                                    count))
                            except InsufficientFunds:
                                output_func('Player {0} doesn\'t have sufficient funds to double the bet'.format(player))
                            continue
                        elif ans == 'double':
                            try:
                                dealer.bank.withdraw(player, dealer.hand(player, hand_num).bet)
                                dealer.bank.deposit(0, dealer.hand(player, hand_num).bet)
                                dealer.hand(player, hand_num).bet *= 2
                                card, count = dealer.hit(player, hand_num)
                                output_func('Player {0} doubles down and gets {1} for a count of {2}'.format(player, card, count))
                                done = True
                            except InsufficientFunds:
                                output_func('Player {0} doesn\'t have the cash for that!'.format(player))
                                continue
                        elif ans == 'hit':
                            card, count = dealer.hit(player, hand_num)
                            output_func('Player {0} got {1} for a count of {2}'.format(player, card, count))
                        else:
                            output_func('Player {0} standing at {1}'.format(player, count))
                            done = True
                    if count == 21:
                        if len(dealer.hand(player, hand_num)) == 2:
                            output_func('Blackjack!')
                        elif not done: # deal with the edge case where they've just doubled down
                            output_func('Player {0} standing at 21'.format(player))
                        done = True
                    if count > 21:
                        output_func('Busted!')
                        done = True
                hand_num += 1
                output_func('')


        dealer_count = dealer.count(0)
        output_func('Dealer reveals {0} which gives a count of {1}'.format(dealer.hand(0)[0], dealer_count))
        while dealer_count < 17:
            card, dealer_count = dealer.hit(0)
            output_func('Dealer is dealt {0} for a count of {1}'.format(card, dealer_count))

        winners = []
        pushers = []

        if dealer_count > 21:
            output_func('Dealer busted!')
            for player in players:
                if dealer.num_hands(player) == 1:
                    if dealer.count(player) <= 21:
                        winners.append(player)
                        if dealer.count(player) == 21 and len(dealer.hand(player)) == 2:
                            dealer.bank.deposit(player, 2.5*dealer.hand(player).bet)
                            dealer.bank.withdraw(0, 2.5*dealer.hand(player).bet)
                        else:
                            dealer.bank.deposit(player, 2*dealer.hand(player).bet)
                            dealer.bank.withdraw(0, 2*dealer.hand(player).bet)
                else:
                    for hand_num in range(dealer.num_hands(player)):
                        if dealer.count(player, hand_num) <= 21:
                            winners.append('{0} {1} hand'.format(player, ordinal[hand_num + 1]))
                            if dealer.count(player, hand_num) == 21 and len(dealer.hand(player, hand_num)) == 2:
                                dealer.bank.withdraw(0, 2.5*dealer.hand(player, hand_num).bet)
                                dealer.bank.deposit(player, 2.5*dealer.hand(player, hand_num).bet)
                            else: 
                                dealer.bank.withdraw(0, 2*dealer.hand(player, hand_num).bet)
                                dealer.bank.deposit(player, 2*dealer.hand(player, hand_num).bet)
        else:
            output_func('Dealer standing at {0}'.format(dealer_count))
            for player in players:
                if dealer.num_hands(player) == 1:
                    c = dealer.count(player)
                    if c <= 21 and c > dealer_count:
                        winners.append(player)
                        if c == 21 and len(dealer.hand(player)) == 2:
                            dealer.bank.withdraw(0, 2.5*dealer.hand(player).bet)
                            dealer.bank.deposit(player, 2.5*dealer.hand(player).bet)
                        else:
                            dealer.bank.withdraw(0, 2*dealer.hand(player).bet)
                            dealer.bank.deposit(player, 2*dealer.hand(player).bet)
                    elif c == dealer_count:
                        pushers.append(player)
                        dealer.bank.withdraw(0, dealer.hand(player).bet)
                        dealer.bank.deposit(player, dealer.hand(player).bet)
                else:
                    for hand_num in range(dealer.num_hands(player)):
                        c = dealer.count(player, hand_num)
                        if  c <= 21 and c > dealer_count:
                            winners.append('{0} {1} hand'.format(player, ordinal[hand_num + 1]))
                            if c == 21 and len(dealer.hand(player, hand_num)) == 2:
                                dealer.bank.withdraw(0, 2.5*dealer.hand(player, hand_num).bet)
                                dealer.bank.deposit(player, 2.5*dealer.hand(player, hand_num).bet)
                            else:
                                dealer.bank.withdraw(0, 2*dealer.hand(player, hand_num).bet)
                                dealer.bank.deposit(player, 2*dealer.hand(player, hand_num).bet)
                        elif c == dealer_count:
                            pushers.append('{0} {1} hand'.format(player, ordinal[hand_num + 1]))
                            dealer.bank.withdraw(0, dealer.hand(player, hand_num).bet)
                            dealer.bank.deposit(player, dealer.hand(player, hand_num).bet)


        if not winners and not pushers:
            output_func('All players lost')
        else:
            if len(winners) == 1:
                output_func('Player {0} won!'.format(winners[0]))
            elif len(winners) > 1:
                output_func('Players {0} won!'.format(mk_print_list(winners)))
            if len(pushers) == 1:
                output_func('Player {0} pushed.'.format(pushers[0]))
            elif len(pushers) > 1:
                output_func('Players {0} pushed.'.format(mk_print_list(pushers)))

        output_func("Play again?")
        keep_playing = read_answer(['yes', 'no', 'quit'], input_func=input_func, output_func=output_func)
    house_net = dealer.bank.balance(0) - dealer.initial_balance*100

    if abs(house_net) > 0.01:
        output_func('House is {0} ${1:.2f}'.format('down' if house_net < 0 else 'up', abs(house_net)))
    else:
        output_func('House broke even')

    for player in range(1, n+1):
        output_func('Player {0} has a balance of ${1:.2f}'.format(player, dealer.bank.balance(player)))


if __name__ == '__main__':
    play()
