import click
import subprocess
import pygame
import button
import math
import random
import os
import itertools
from pygame.locals import *


LETTERS = [chr(x) for x in range(ord('A'), ord('Z')+1)]


class RenderedSymbols:
    def __init__(self):
        self.db = {}

    def add(self, letter, surface):
        self.db[letter] = surface

    def get(self, letter):
        return self.db[letter]


rendered_symbols = RenderedSymbols()


class Reel():
    def __init__(self, machine, idx, symbols=LETTERS, default=0):
        # Position assumes the center of a slot
        self.idx = idx
        self.machine = machine
        self.symbols = symbols    

        # The position is an index in the list of symbols. If it
        # is not a natural number, it means: the reel is in-between 
        # symbols.
        self.position = default

    def layout(self, machine_rect):        
        width = machine_rect.width / float(self.machine.num_reels)
        reel_rect = pygame.Rect(self.idx * width, 0, width, machine_rect.height)
        self.rect = reel_rect

    def norm_idx(self, idx):
        while idx >= len(self.symbols):
            idx = idx - len(self.symbols)
        while idx < 0:
            idx = len(self.symbols) + idx
        return idx

    def get_symbol_index(self, symbol):
        if isinstance(symbol, (float,)):
            symbol_idx = int(symbol * len(self.symbols))
            symbol = self.symbols[symbol_idx]
        return self.symbols.index(symbol)

    def count_from_to(self, start, end):
        start = self.norm_idx(start)
        end = self.norm_idx(end)
        if end > start:
            return end - start
        else:
            return len(self.symbols) - start + end

    def draw(self, target):
        current_symbol_idx = int(round(self.position))
        remainder = self.position - current_symbol_idx

        # We have to draw the current position, and a certain amount before/after
        # If the position is 10, we draw 9 10 11
        # If the position is 10.6, we draw 10, 11, 12
        num_before_after = 1        
        symbols_to_draw = [self.norm_idx(x) for x in range(current_symbol_idx-num_before_after, current_symbol_idx+num_before_after+1)]
        
        # eg. will be: -2, -1, 0, 1, 2
        shift = list(range(-(len(symbols_to_draw)/2), len(symbols_to_draw)/2 + 1))

        for shift, symbol_idx in zip(shift, symbols_to_draw):
            letter_surface = rendered_symbols.get(self.symbols[symbol_idx])
            font_rect = letter_surface.get_rect()
            font_rect.centerx = self.rect.centerx

            font_rect.top = (
                # Center in the middle of our target rect
                self.rect.height / 2 
                # Center each symbol at the rect center
                - self.machine.symbol_height / 2 
                # Which symbol 
                + shift * self.machine.symbol_height
                # How far long we are to the next one
                - remainder * self.machine.symbol_height
            )
            
            target.blit(letter_surface, font_rect)


class SlotMachine(object):

    def __init__(self, symbol_height, symbol_width, speed=9):
        self.symbol_width = symbol_width
        self.symbol_height = symbol_height
        self.reels = []
        self.speed = speed

    @property
    def num_reels(self):
        return len(self.reels)

    def add_reel(self, symbols=None):
        if not symbols:
            symbols = LETTERS

        self.reels.append(Reel(
            self, 
            self.num_reels, 
            symbols=symbols))

    def layout(self, screen_rect):
        machine_height = self.symbol_height * 1
        machine_width = self.symbol_width * self.num_reels
        
        # Center the slot machine in the frame
        machine_rect = pygame.Rect(0, 0, machine_width, machine_height)
        machine_rect.center = screen_rect.center
        self.rect = machine_rect
        self.surface = pygame.Surface((machine_rect.width, machine_rect.height))

        for reel in self.reels:
            reel.layout(self.rect)

    @property
    def is_spinning(self):
        return sum(self.desired_spin_distances) > 0

    def set_to(self, targets):
        self.targets = [
            self.reels[idx].symbols.index(target) 
            for idx, target in enumerate(targets)]

        for reel, target_idx in zip(self.reels, self.targets):
            reel.position = target_idx

        self.desired_spin_distances = [0] * self.num_reels

    def spin_to(self, targets, durations):
        if self.is_spinning:
            print('already spinning')
            return

        # stop at "targets". stop in the given order, and with the given durations in between.
        self.targets = [
            self.reels[idx].get_symbol_index(target) 
            for idx, target in enumerate(targets)]

        # pre-calculate how far every reel has to spin
        total_slots_to_spin = []
        for idx, d in enumerate(durations):
            by_speed = self.speed * d
            extra_to_target = self.reels[idx].count_from_to(self.reels[idx].position + by_speed, self.targets[idx])
            # print('now', self.reels[idx].position)
            # print('after speed', self.reels[idx].norm_idx(self.reels[idx].position + by_speed))
            # print('desired', self.targets[idx])
            # print('extra', extra_to_target)

            total_slots_to_spin.append(by_speed + extra_to_target)
        print(total_slots_to_spin)
        self.desired_spin_distances = total_slots_to_spin    

    def update(self, time):
        for idx, reel in enumerate(self.reels):
            max_allowed = self.desired_spin_distances[idx]
            to_spin = min(max_allowed, self.speed * time)

            reel.position += to_spin

            reel.position = reel.norm_idx(reel.position)
            self.desired_spin_distances[idx] -= to_spin

    def draw(self, target):
        self.surface.fill((255,255,255))

        for reel in self.reels:
            # we could use clamp here
            reel.draw(self.surface)

        target.blit(self.surface, self.rect)


def create_letters(font):
    # Create all the letters
    letters = []
    for x in itertools.chain(LETTERS,  ['#']):
        surface = font.render(x, 1, (10, 10, 10))
        letters.append(surface)
        rendered_symbols.add(x, surface)

    # Find the maximum letter size
    max_width = max_height = None
    for letter in letters:
        width, height = letter.get_size()
        max_width = max(max_width, width)
        max_height = max(max_width, height)

    return max_width, max_height


@click.command()
@click.option('--fullscreen', is_flag=True)
@click.option('--fps', is_flag=True)
@click.option('--size')
@click.option('--threshold', type=float)
@click.option('--picfile', default=os.path.join(os.path.dirname(__file__), 'trump800.jpg'))
@click.option('--printer-mac', default="C4:30:18:35:13:FA")
def main(fullscreen=False, fps=False, size=None, picfile=None, printer_mac=None, threshold=0.15):
    print('- Picfile: %s' % picfile)
    assert os.path.exists(picfile)

    # Initialise screen
    pygame.init()
    flags = 0
    if fullscreen:
        flags |= pygame.FULLSCREEN
    pygame.mouse.set_visible(False)
    screen = pygame.display.set_mode((1920, 1080), flags)
    pygame.display.set_caption('#MAGA Machine')

    # Fill background
    background = pygame.Surface(screen.get_size())
    background = background.convert()
    background.fill((255, 255, 255))    
    
    font = pygame.font.Font("./bender_bold.ttf", size or 220)
    fontSmall = pygame.font.Font(None, 13)

    symbol_width, symbol_height = create_letters(font)
    padding = 0.1
    symbol_width = int(symbol_width + padding * symbol_width)

    machine = SlotMachine(symbol_height, symbol_width)
    machine.add_reel(symbols=LETTERS + ['#'])
    machine.add_reel()
    machine.add_reel()
    machine.add_reel()
    machine.add_reel()
    machine.set_to('#MAGA')
    machine.layout(background.get_rect())

    def sendprint():
        if not printer_mac:
            print('Skip printing, no mac')
            return

        pp = subprocess.Popen(["obexftp", "--nopath", "--noconn", "--uuid", "none", "--bluetooth", printer_mac,  "--channel", "4", "-p", picfile])
        #message =  pp.communicate()

    def spin():
        if machine.is_spinning:
            print('already spinning')
            return

        r = random.random()
        print('Dice is ', r, 'threshold is', threshold)
        if r < threshold:
           target = 'G'
           sendprint()
        else:
            target = random.random()

        machine.spin_to(
                        ['#', 'M', 'A', target, 'A'],
                        [4,   5.5,    7,  10,      8]
                    )

    # Event loop
    clock = pygame.time.Clock()
    while True:
        elapsed_ms = clock.tick(120)
        elapsed_s = elapsed_ms / 1000.0        

        # HANDLE EVENTS
        if button.query():
            spin()
        for event in pygame.event.get():
            if event.type == QUIT:
                return

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return

                if event.key == pygame.K_DOWN:
                    spin()

        # TICK ALL OBJECTS
        machine.update(elapsed_s)

        # DRAW        
        screen.blit(background, (0, 0))
        machine.draw(screen)

        if fps:
            screen.blit(fontSmall.render('FPS: %s' % clock.get_fps(), 1, (10, 10, 10)), pygame.Rect(0, 0, 0, 0))

        
        pygame.display.flip()


if __name__ == '__main__': 
    button.setup()
    try:
        main()
    finally:
        button.cleanup()
