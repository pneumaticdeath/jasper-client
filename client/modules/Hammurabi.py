# vim: ai sw=4 expandtab:
import logging
import os
import re
from client import jasperpath
from client.utils import text2int
from client.games.hammurabi import Hammurabi

def mk_upper(l):
    return [w.upper() for w in l]

WORDS = [ 'PLAY', 'HAMMURABI'  ]
INSTANCE_WORDS = [
    'YES',
    'NO',
    'QUIT',
    'NONE', 
    'ALL',
] + mk_upper(text2int.units) + mk_upper(text2int.tens) + mk_upper(text2int.scales)

PRIORITY = 50

def get_number(prompt, mic, all_value=None):
    retval = None
    while retval is None:
        print(prompt)
        mic.say(prompt)
        heard = ''
        while not heard:
            heard = mic.activeListen()
        if heard == 'NONE':
            return 0
        elif heard == 'ALL' and all_value is not None:
            return all_value
        try:
            retval = text2int.text2int(heard)
            if 'NO' == get_yes_no('I heard {0}, is that right?'.format(retval), mic):
                retval = None
        except ValueError as e:
            print(e)
            mic.say('I didn\'t understand that number')
    return retval

def get_yes_no(prompt, mic):
    print(prompt)
    mic.say(prompt)
    answer = ''
    while answer not in ['YES', 'NO']:
        answer = mic.activeListen()
        if answer not in ['YES', 'NO']:
            print('Didn\'t like {0}'.format(answer))
            mic.say('That wasn\'t a yes or no.')
            mic.say(prompt)
    return answer

def handle(text, mic, profile):
    """
    Plays a game of Hammurabi
    """
     
    logging.info('Starting the Hammurabi module')

    Hammurabi.reign = 5
    mic.say('Welcome to Hammurabi\'s Babylon.  You will reign for {0} years.'.format(Hammurabi.reign))

    game = Hammurabi()
    
    last_year = 0
    while game.year <= game.reign and not game.overthrown:
        if last_year != game.year:
            print(game.status())
            mic.say(game.status())
            last_year = game.year
        else:
            print('Try again...')
            mic.say('Let\'s try that again!')

        print('Feed?')
        people_fed = get_number('How many people do you want to feed?', mic, game.population)
        feed = people_fed*game.food_per_person

        print('Plant?')
        plant = get_number('How many acres would you like to plant?', mic, min(game.acreage, game.population*game.acres_per_person))

        print('Real estate?')
        land = int((game.grain-feed-plant*game.seed_per_acre)/game.land_price)
        if land < 0: land -= 1 # stupid rouding errors
        action = 'are able to buy at most' if land > 0 else 'will need to sell at least'
        print('Default land is {0}'.format(land))
        mic.say('Given that, you {0} {1} acres of land'.format(action, abs(land)))
        answer = get_yes_no('Is that what you\'d like to do?', mic)
        if answer == 'NO':
            print('Buy land?')
            land_bought = get_number('How many acres of land do you wish to buy?', mic)
            if land_bought == 0:
                print('Sell land?')
                land_sold = get_number('How many acres of land do you wish to sell?', mic)
                land = -land_sold
            else:
                land = land_bought

        print('Sanity Check...')
        land_plantable = min(game.acreage + land, game.population*game.acres_per_person)
        if plant > land_plantable:
            print('Not enough land..')
            mic.say('But you can plant at most {0} acres.'.format(land_plantable))
            answer = get_yes_no('Is that what you\'d like to do?', mic)
            if answer == 'YES':
                plant = land_plantable

        print('land: {0}, feed: {1}, plant: {2}'.format(land, feed, plant))
        try:
            game.run(land, feed, plant)
        except ValueError as e:
            print(str(e))
            mic.say(str(e))
    print(game.status())
    mic.say(game.status())

    logging.info('Leaving Hammurabi module')

def isValid(text):
    """
    Responds to the phrase "Play Hammurabi"
    """

    return bool(re.search(r'\bhammurabi\b', text, re.IGNORECASE))
